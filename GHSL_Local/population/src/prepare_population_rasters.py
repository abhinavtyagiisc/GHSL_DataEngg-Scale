"""Validate native rasters and stage 100 m cell records for Spark; no resampling."""
import hashlib
import json
import math
from pathlib import Path
import zipfile
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds, bounds as window_bounds
from shapely.geometry import box, mapping
from shapely.ops import transform as transform_geometry
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]

def zipped_raster(path):
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith('.tif')]
    if len(names) != 1:
        raise ValueError(f'Expected one GeoTIFF in {path}: {names}')
    return f'/vsizip/{path.resolve()}/{names[0]}'

def validate_alignment(source, reference):
    if source.crs != reference.crs:
        raise ValueError('Population and reference CRS differ')
    a, b = source.transform, reference.transform
    if (a.a, a.e, a.b, a.d) != (100, -100, 0, 0):
        raise ValueError('Population must be a north-up native 100 m grid')
    if (b.a, b.e, b.b, b.d) != (1000, -1000, 0, 0):
        raise ValueError('Reference must be a north-up 1 km grid')
    if not all(abs(v-round(v)) < 1e-7 for v in ((b.c-a.c)/100, (b.f-a.f)/100)):
        raise ValueError('Population and settlement pixel boundaries are misaligned')

def main():
    cfg = json.loads((ROOT/'config/pilot.json').read_text())
    if (cfg['release'],cfg['population_version'],cfg['reference_version'])!=('R2023A','V1_0','V2_0'):
        raise ValueError('This pipeline supports R2023A POP V1_0 / SMOD V2_0 only')
    out = ROOT/'data/cleaned/population_100m'
    out.mkdir(parents=True, exist_ok=True)
    ref_zip = ROOT/'data/raw/reference'/f'GHS_SMOD_E{cfg["reference_epoch"]}_GLOBE_R2023A_54009_1000_V2_0_{cfg["tile"]}.zip'
    ref_path = ROOT/'data/raw/reference/settlement_grid_reference.tif'
    with rasterio.open(zipped_raster(ref_zip)) as ref:
        with rasterio.open(ref_path, 'w', **ref.profile) as dst:
            dst.write(ref.read())
        projection = Transformer.from_crs('EPSG:4326', ref.crs, always_xy=True)
        polygon = transform_geometry(projection.transform, box(*cfg['bbox_wgs84']).segmentize(0.01))
        if not box(*ref.bounds).covers(polygon):
            raise ValueError('Pilot crosses the configured tile; add multi-tile ingestion before proceeding')
        w = from_bounds(*polygon.bounds, ref.transform)
        c0, r0 = math.floor(w.col_off), math.floor(w.row_off)
        c1, r1 = math.ceil(w.col_off+w.width), math.ceil(w.row_off+w.height)
        coarse = Window(c0, r0, c1-c0, r1-r0)
        extent = window_bounds(coarse, ref.transform)
        # Derive global origin from the official tile numbering, not a guessed grid.
        tile_row, tile_col = [int(s[1:]) for s in cfg['tile'].split('_')]
        origin_x = ref.transform.c - (tile_col-1)*ref.width*1000
        origin_y = ref.transform.f + (tile_row-1)*ref.height*1000
        grid = dict(crs=ref.crs.to_string(), crs_wkt=ref.crs.to_wkt(), resolution_m=1000,
                    origin_x=origin_x, origin_y=origin_y, reference=str(ref_path.relative_to(ROOT)),
                    pilot_bounds_mollweide=list(extent), bbox_wgs84=cfg['bbox_wgs84'],
                    masking='100 m pixel centre within densified WGS84 pilot rectangle',
                    reference_transform=list(ref.transform)[:6])
        grid['grid_id'] = 'ghsl_r2023a_54009_1000_' + hashlib.sha256(
            json.dumps([grid['crs'], 1000, origin_x, origin_y]).encode()).hexdigest()[:12]
        (ROOT/'config/grid_contract.json').write_text(json.dumps(grid, indent=2)+'\n')
        reports=[]
        for year in cfg['epochs']:
            archive = ROOT/'data/raw/downloads'/f'GHS_POP_E{year}_GLOBE_R2023A_54009_100_V1_0_{cfg["tile"]}.zip'
            with rasterio.open(zipped_raster(archive)) as src:
                validate_alignment(src, ref)
                if src.count != 1 or src.nodata != -200 or not src.dtypes[0].startswith('float'):
                    raise ValueError(f'Unexpected source band/type/NoData for {year}')
                fine = from_bounds(*extent, src.transform).round_offsets().round_lengths()
                arr = src.read(1, window=fine, masked=True)
                affine = src.window_transform(fine)
                inside = geometry_mask([mapping(polygon)], arr.shape, affine, invert=True)
                values = np.asarray(arr.data, dtype=np.float64)
                valid = inside & ~np.ma.getmaskarray(arr)
                if np.any(~np.isfinite(values[valid])) or np.any(values[valid] < 0):
                    raise ValueError(f'Invalid population values in {year}')
                clean = np.where(valid, values, -200).astype('float32')
                clip_path=ROOT/f'data/cleaned/GHS_POP_{year}_bengaluru_100m.tif'
                profile = dict(driver='GTiff', height=arr.shape[0], width=arr.shape[1], count=1,
                               dtype='float32', crs=src.crs, transform=affine, nodata=-200,
                               compress='deflate', tiled=True, blockxsize=256, blockysize=256)
                with rasterio.open(clip_path, 'w', **profile) as dst:
                    dst.write(clean, 1)
                    dst.update_tags(source=archive.name, epoch=str(year), grid_id=grid['grid_id'])
                rows, cols = np.where(inside)
                global_row100 = np.rint((origin_y-affine.f)/100).astype('int64')+rows
                global_col100 = np.rint((affine.c-origin_x)/100).astype('int64')+cols
                table = pa.table({
                    'year': pa.array(np.full(len(rows), year), type=pa.int32()),
                    'source_row': pa.array(global_row100, type=pa.int32()),
                    'source_col': pa.array(global_col100, type=pa.int32()),
                    'grid_row': pa.array(global_row100//10, type=pa.int32()),
                    'grid_col': pa.array(global_col100//10, type=pa.int32()),
                    'population_100m': pa.array(values[rows,cols], mask=~valid[rows,cols], type=pa.float64())})
                pq.write_table(table, out/f'population_{year}.parquet', compression='snappy', row_group_size=100000)
                report=dict(year=year, epoch_type='historical' if year<=2020 else 'projection',
                            inside_pixels=int(inside.sum()), valid_pixels=int(valid.sum()),
                            nodata_pixels=int((inside & ~valid).sum()), zero_pixels=int((valid & (values==0)).sum()),
                            source_total=float(values[valid].sum(dtype=np.float64)),
                            min_population=float(values[valid].min()), max_population=float(values[valid].max()),
                            crs=str(src.crs), transform=list(affine)[:6], width=arr.shape[1], height=arr.shape[0])
                reports.append(report)
                print(f'{year}: {report["valid_pixels"]:,} valid pixels; population={report["source_total"]:,.3f}', flush=True)
    if len({(r['inside_pixels'],tuple(r['transform']),r['width'],r['height']) for r in reports}) != 1:
        raise ValueError('Epoch grids or footprints differ')
    (ROOT/'reports/raster_validation.json').write_text(json.dumps(reports, indent=2)+'\n')

if __name__ == '__main__':
    main()
