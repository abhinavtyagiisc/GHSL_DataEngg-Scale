"""Windowed native-100m handoff and conservative 1km rollup on one shared grid.

Plan without downloads; execute explicitly into a new output directory. Country masks
are supplied as WGS84 GeoJSON. Cached official JRC archives are shared with the pilot.
"""
import argparse
from contextlib import ExitStack
import fcntl
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from pyproj import Transformer
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds
from shapely.geometry import box, mapping, shape
from shapely.ops import transform, unary_union

from prepare_population_rasters import validate_alignment, zipped_raster

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from download_population_tiles import BASE, download

EPOCHS = list(range(1975, 2031, 5))
SMOD_CLASSES = {10, 11, 12, 13, 21, 22, 23, 30}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_area(cfg):
    if ('boundary' in cfg) == ('bbox_wgs84' in cfg):
        raise ValueError('Specify exactly one boundary or bbox_wgs84')
    provenance = {}
    if 'boundary' in cfg:
        path = ROOT / cfg['boundary']
        data = json.loads(path.read_text())
        if data.get('crs'):
            crs_name = data['crs'].get('properties', {}).get('name', '')
            if crs_name not in ('urn:ogc:def:crs:OGC:1.3:CRS84', 'EPSG:4326', 'urn:ogc:def:crs:EPSG::4326'):
                raise ValueError('Boundary must use WGS84 longitude/latitude')
        features = data['features'] if data['type'] == 'FeatureCollection' else [data]
        geometries = [shape(f['geometry'] if f['type'] == 'Feature' else f) for f in features]
        if not geometries or any(g.geom_type not in ('Polygon', 'MultiPolygon') or not g.is_valid for g in geometries):
            raise ValueError('Boundary must contain valid polygons')
        area = unary_union(geometries)
        provenance = {'path': str(path), 'sha256': digest(path)}
    else:
        west, south, east, north = cfg['bbox_wgs84']
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise ValueError('Invalid WGS84 bounding box')
        area = box(west, south, east, north)
    if area.is_empty or not area.is_valid:
        raise ValueError('Empty or invalid area')
    west, south, east, north = area.bounds
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError('Boundary coordinates are not WGS84 longitude/latitude')
    project = Transformer.from_crs('EPSG:4326', 'ESRI:54009', always_xy=True)
    projected = transform(project.transform, area.segmentize(0.01))
    if not projected.is_valid:
        raise ValueError('Invalid projected boundary')
    return projected, provenance


def tile_bounds(tile, grid):
    r, c = (int(v[1:]) for v in tile.split('_'))
    x = grid['origin_x'] + (c - 1) * 1_000_000
    y = grid['origin_y'] - (r - 1) * 1_000_000
    return x, y - 1_000_000, x + 1_000_000, y


def tiles_for_area(area, grid):
    west, south, east, north = area.bounds
    c0 = math.floor((west - grid['origin_x']) / 1_000_000) + 1
    c1 = math.ceil((east - grid['origin_x']) / 1_000_000)
    r0 = math.floor((grid['origin_y'] - north) / 1_000_000) + 1
    r1 = math.ceil((grid['origin_y'] - south) / 1_000_000)
    tiles = []
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            tile = f'R{r}_C{c}'
            if area.intersection(box(*tile_bounds(tile, grid))).area > 0:
                tiles.append(tile)
    return tiles


def source_item(product, year, tile):
    resolution, version, version_dir, folder = (100, 'V1_0', 'V1-0', 'downloads') if product == 'POP' else (1000, 'V2_0', 'V2-0', 'reference')
    stem = f'GHS_{product}_E{year}_GLOBE_R2023A_54009_{resolution}'
    filename = f'{stem}_{version}_{tile}.zip'
    return (f'{BASE}/GHS_{product}_GLOBE_R2023A/{stem}/{version_dir}/tiles/{filename}', ROOT / 'data/raw' / folder / filename)


def make_plan(cfg):
    if (cfg['release'], cfg['population_version'], cfg['reference_version']) != ('R2023A', 'V1_0', 'V2_0'):
        raise ValueError('Supported release: R2023A POP V1_0 / SMOD V2_0')
    epochs = cfg['epochs']
    if not epochs or epochs != sorted(set(epochs)) or any(y not in EPOCHS for y in epochs):
        raise ValueError('Epochs must be unique ascending GHSL five-year epochs')
    settlement_epochs = cfg.get('settlement_epochs', [])
    if cfg['reference_epoch'] not in EPOCHS:
        raise ValueError('Invalid reference epoch')
    if len(set(settlement_epochs)) != len(settlement_epochs) or not set(settlement_epochs) <= set(epochs):
        raise ValueError('Settlement epochs must be unique and included in population epochs')
    grid = json.loads((ROOT / 'config/grid_contract.json').read_text())
    grid = {k: grid[k] for k in ('crs', 'crs_wkt', 'origin_x', 'origin_y', 'grid_id')}
    fine_id = 'ghsl_r2023a_54009_100_' + hashlib.sha256(json.dumps([grid['crs'], 100, grid['origin_x'], grid['origin_y']]).encode()).hexdigest()[:12]
    grid['fine_grid_id'] = fine_id
    area, boundary = load_area(cfg)
    tiles = tiles_for_area(area, grid)
    sources = []
    for tile in tiles:
        for product, years in [('POP', epochs), ('SMOD', sorted(set(settlement_epochs) | {cfg['reference_epoch']}))]:
            for year in years:
                url, path = source_item(product, year, tile)
                sources.append(dict(product=product, year=year, tile=tile, url=url, path=str(path.relative_to(ROOT)), cached=path.exists()))
    plan = dict(name=cfg['name'], config=cfg, grid=grid, boundary=boundary, tiles=tiles,
                approximate_cells_per_epoch=round(area.area / 10_000),
                approximate_cell_year_rows=round(area.area / 10_000) * len(epochs),
                sources=sources, masking='100 m cell centre inside shared area; no boundary extrapolation',
                settlement_semantics='Parent 1 km category inherited at 100 m, matching year only; not a new classification')
    return plan, area


def validate_tile(src, tile, grid, resolution):
    from rasterio.crs import CRS
    if src.crs != CRS.from_string(grid['crs']):
        raise ValueError('Unexpected tile CRS')
    west, south, east, north = tile_bounds(tile, grid)
    expected = (resolution, 0, west, 0, -resolution, north)
    if not np.allclose(tuple(src.transform)[:6], expected, atol=1e-7, rtol=0):
        raise ValueError(f'Tile {tile} does not match global origin/transform')
    if src.width != 1_000_000 // resolution or src.height != 1_000_000 // resolution or src.count != 1:
        raise ValueError('Unexpected tile shape/bands')


def aligned_windows(area, src, block_pixels):
    if block_pixels < 10 or block_pixels % 10:
        raise ValueError('block_pixels must be a positive multiple of 10')
    clipped = area.intersection(box(*src.bounds))
    if clipped.is_empty:
        return
    w = from_bounds(*clipped.bounds, src.transform)
    c0 = max(0, math.floor(w.col_off / 10) * 10)
    r0 = max(0, math.floor(w.row_off / 10) * 10)
    c1 = min(src.width, math.ceil((w.col_off + w.width) / 10) * 10)
    r1 = min(src.height, math.ceil((w.row_off + w.height) / 10) * 10)
    for row in range(r0, r1, block_pixels):
        for col in range(c0, c1, block_pixels):
            yield Window(col, row, min(block_pixels, c1-col), min(block_pixels, r1-row))


def build_tables(values, valid, inside, row0, col0, grid, settlement=None, settlement_valid=None):
    """Native counts stay unchanged; disjoint aligned blocks produce unique parent rows."""
    if row0 % 10 or col0 % 10 or any(n % 10 for n in values.shape):
        raise ValueError('Blocks must align to 1 km cells')
    valid = valid & inside
    if np.any(~np.isfinite(values[valid])) or np.any(values[valid] < 0):
        raise ValueError('Negative or nonfinite population')
    if settlement is not None and np.any(~np.isin(settlement[settlement_valid], list(SMOD_CLASSES))):
        raise ValueError('Unknown SMOD classification code')
    rows, cols = np.where(inside)
    rr, cc = (rows + row0).astype('int32'), (cols + col0).astype('int32')
    parent_r, parent_c = rr // 10, cc // 10
    if settlement is None:
        classes = np.zeros(len(rows), dtype='int16')
        class_valid = np.zeros(len(rows), dtype=bool)
    else:
        classes = settlement[rows//10, cols//10].astype('int16')
        class_valid = settlement_valid[rows//10, cols//10]
    fine = pa.table({
        'grid_id': pa.array([grid['fine_grid_id']] * len(rows)),
        'cell_id': pa.array([f'{r}_{c}' for r,c in zip(rr,cc)]),
        'grid_row': rr, 'grid_col': cc,
        'parent_grid_id': pa.array([grid['grid_id']] * len(rows)),
        'parent_cell_id': pa.array([f'{r}_{c}' for r,c in zip(parent_r,parent_c)]),
        'population': pa.array(values[rows,cols], mask=~valid[rows,cols], type=pa.float64()),
        'settlement_class': pa.array(classes, mask=~class_valid, type=pa.int16()),
    })
    h,w = values.shape
    def reduce(a):
        return a.reshape(h//10, 10, w//10, 10).sum(axis=(1,3))
    expected, known = reduce(inside), reduce(valid)
    totals = reduce(np.where(valid, values, 0.0))
    cr, cc = np.where(expected > 0)
    gr, gc = (cr + row0//10).astype('int32'), (cc + col0//10).astype('int32')
    coarse = pa.table({
        'grid_id': pa.array([grid['grid_id']] * len(cr)),
        'cell_id': pa.array([f'{r}_{c}' for r,c in zip(gr,gc)]),
        'grid_row': gr, 'grid_col': gc,
        'population': pa.array(totals[cr,cc], mask=known[cr,cc] == 0, type=pa.float64()),
        'valid_pixel_count': known[cr,cc].astype('int32'),
        'expected_pixel_count': expected[cr,cc].astype('int32'),
        'coverage_fraction': known[cr,cc] / expected[cr,cc],
        'aoi_fraction': expected[cr,cc] / 100.0,
        'is_complete': known[cr,cc] == expected[cr,cc],
        'settlement_class': pa.array(np.zeros(len(cr), dtype='int16') if settlement is None else settlement[cr,cc].astype('int16'),
            mask=np.ones(len(cr), dtype=bool) if settlement is None else ~settlement_valid[cr,cc]),
    })
    return fine, coarse


def table_digest(table):
    """Canonical values + validity, independent of Arrow null buffer contents."""
    h = hashlib.sha256()
    for name in table.column_names:
        col = table[name].combine_chunks()
        h.update(name.encode())
        h.update(col.is_valid().to_numpy(zero_copy_only=False).tobytes())
        if pa.types.is_string(col.type):
            for value in col.to_pylist():
                value = (value or '').encode()
                h.update(len(value).to_bytes(4, 'little')); h.update(value)
        else:
            h.update(pc.fill_null(col, False if pa.types.is_boolean(col.type) else 0).to_numpy(zero_copy_only=False).tobytes())
    return h.hexdigest()


def process_pair(pop_path, ref_path, smod_path, tile, year, area, grid, out, block_pixels):
    paths = {kind: out/kind/f'epoch_type={"historical" if year <= 2020 else "projection"}'/f'year={year}'/f'{tile}.parquet'
             for kind in ('population_100m', 'population_1km')}
    for p in paths.values():
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() or p.with_suffix('.part').exists():
            raise FileExistsError(p)
    stats = dict(year=year, tile=tile, fine_rows=0, coarse_rows=0, valid_pixels=0,
                 population=0.0, settlement_known_pixels=0, boundary_cells=0, row_groups=0)
    hashes = {k: [] for k in paths}
    with ExitStack() as stack:
        src = stack.enter_context(rasterio.open(zipped_raster(pop_path)))
        ref = stack.enter_context(rasterio.open(zipped_raster(ref_path)))
        validate_alignment(src, ref)
        validate_tile(src, tile, grid, 100)
        validate_tile(ref, tile, grid, 1000)
        if src.nodata != -200 or not src.dtypes[0].startswith('float'):
            raise ValueError('Unexpected population dtype/NoData')
        smod = stack.enter_context(rasterio.open(zipped_raster(smod_path))) if smod_path else None
        if smod:
            validate_tile(smod, tile, grid, 1000)
        writers = {}
        tile_r, tile_c = (int(v[1:]) for v in tile.split('_'))
        for window in aligned_windows(area, src, block_pixels):
            affine = src.window_transform(window)
            inside = geometry_mask([mapping(area)], (int(window.height), int(window.width)), affine, invert=True)
            if not inside.any():
                continue
            arr = src.read(1, window=window, masked=True)
            values = np.asarray(arr.data, dtype='float64')
            valid = ~np.ma.getmaskarray(arr)
            classes = class_valid = None
            if smod:
                cw = Window(window.col_off//10, window.row_off//10, window.width//10, window.height//10)
                sa = smod.read(1, window=cw, masked=True)
                classes, class_valid = sa.data, ~np.ma.getmaskarray(sa)
            tables = build_tables(values, valid, inside, (tile_r-1)*10000+int(window.row_off),
                                  (tile_c-1)*10000+int(window.col_off), grid, classes, class_valid)
            for kind, table in zip(paths, tables):
                if kind not in writers:
                    writers[kind] = stack.enter_context(pq.ParquetWriter(paths[kind].with_suffix('.part'), table.schema, compression='snappy'))
                writers[kind].write_table(table, row_group_size=len(table))
                hashes[kind].append(table_digest(table))
            fine, coarse = tables
            stats['fine_rows'] += len(fine)
            stats['coarse_rows'] += len(coarse)
            stats['valid_pixels'] += len(fine) - fine['population'].null_count
            stats['settlement_known_pixels'] += len(fine) - fine['settlement_class'].null_count
            stats['boundary_cells'] += int(pc.sum(pc.cast(pc.less(coarse['aoi_fraction'],1.0), pa.int64())).as_py())
            total = float(values[valid & inside].sum())
            if not math.isclose(total, pc.sum(coarse['population']).as_py() or 0.0, rel_tol=1e-10, abs_tol=1e-5):
                raise ValueError('Population conservation failure')
            stats['population'] += total
            stats['row_groups'] += 1
    for kind, path in paths.items():
        if not hashes[kind]:
            continue
        pf = pq.ParquetFile(path.with_suffix('.part'))
        if pf.num_row_groups != len(hashes[kind]):
            raise ValueError('Parquet row-group count changed')
        for index, expected in enumerate(hashes[kind]):
            if table_digest(pf.read_row_group(index)) != expected:
                raise ValueError('Parquet round-trip content changed')
        path.with_suffix('.part').replace(path)
    stats['settlement_epoch'] = year if smod_path else None
    stats['files'] = {str(p.relative_to(out)): digest(p) for p in paths.values() if p.exists()}
    stats['status'] = 'PASS'
    return stats


def execute(plan, area, out, allow_download, block_pixels, resume=False):
    if out.exists() and not resume:
        raise FileExistsError(f'Choose a new run directory: {out}')
    if resume and not out.is_dir():
        raise FileNotFoundError('Resume requires an existing incomplete run')
    if block_pixels < 10 or block_pixels % 10:
        raise ValueError('block_pixels must be a positive multiple of 10')
    missing = [s['path'] for s in plan['sources'] if not (ROOT/s['path']).exists()]
    if missing and not allow_download:
        raise FileNotFoundError(f'{len(missing)} source archives missing; use --download. First: {missing[0]}')
    out.mkdir(parents=True, exist_ok=resume)
    # OS releases the lock if the process exits or is interrupted; no stale PID logic.
    with (out/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return execute_locked(plan, area, out, block_pixels, resume)


def execute_locked(plan, area, out, block_pixels, resume):
    reports = []
    if resume:
        if (out/'_SUCCESS').exists():
            raise ValueError('Run is already complete')
        saved = json.loads((out/'plan.json').read_text())
        for key in ('config', 'grid', 'boundary', 'tiles'):
            if saved[key] != plan[key]:
                raise ValueError(f'Resume configuration changed: {key}')
        if saved.get('processor_sha256') != digest(__file__):
            raise ValueError('Processor changed; use a new output directory')
        if (out/'progress.json').exists():
            reports = json.loads((out/'progress.json').read_text())
            for report in reports:
                for relative, expected in report['files'].items():
                    if digest(out/relative) != expected:
                        raise ValueError('Completed output changed; cannot resume')
    else:
        plan['processor_sha256'] = digest(__file__)
        (out/'plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    (out/'RUNNING').write_text('Incomplete until validation.json and _SUCCESS exist.\n')
    manifests = {r['path']:r for r in json.loads((out/'download_manifest.json').read_text())} if resume and (out/'download_manifest.json').exists() else {}
    previous = {path:r['sha256'] for path,r in manifests.items()}
    start = time.monotonic()
    try:
        # Validate each archive once, keeping source provenance even after interruption.
        for source in plan['sources']:
            record = download((source['url'], ROOT/source['path']))
            if record['path'] in previous and record['sha256'] != previous[record['path']]:
                raise ValueError('Source archive changed; cannot resume')
            manifests[record['path']] = record
            checkpoint = out/'download_manifest.json.tmp'
            checkpoint.write_text(json.dumps(list(manifests.values()), indent=2)+'\n')
            checkpoint.replace(out/'download_manifest.json')
        for tile in plan['tiles']:
            for year in plan['config']['epochs']:
                if any(r['tile']==tile and r['year']==year for r in reports):
                    continue
                if resume:
                    # Preserve uncheckpointed files before recomputing the interrupted pair.
                    for kind in ('population_100m','population_1km'):
                        relative = Path(kind)/f'epoch_type={"historical" if year<=2020 else "projection"}'/f'year={year}'/f'{tile}.parquet'
                        for path in (out/relative, (out/relative).with_suffix('.part')):
                            if path.exists():
                                target = out/'incomplete'/str(time.time_ns())/path.relative_to(out)
                                target.parent.mkdir(parents=True)
                                path.rename(target)
                pop = source_item('POP', year, tile)[1]
                ref = source_item('SMOD', plan['config']['reference_epoch'], tile)[1]
                smod = source_item('SMOD', year, tile)[1] if year in plan['config'].get('settlement_epochs', []) else None
                report = process_pair(pop, ref, smod, tile, year, area, plan['grid'], out, block_pixels)
                reports.append(report)
                checkpoint = out/'progress.json.tmp'
                checkpoint.write_text(json.dumps(reports, indent=2)+'\n')
                checkpoint.replace(out/'progress.json')
                print(json.dumps(report), flush=True)
        # Every epoch must have the same centre-mask footprint, tile by tile.
        for tile in plan['tiles']:
            counts = {(r['fine_rows'],r['coarse_rows']) for r in reports if r['tile']==tile}
            if len(counts) != 1:
                raise ValueError('Epoch footprints differ')
        result = dict(status='PASS', name=plan['name'], tile_epochs=reports,
                      fine_rows=sum(r['fine_rows'] for r in reports), coarse_rows=sum(r['coarse_rows'] for r in reports),
                      elapsed_seconds=round(time.monotonic()-start,2),
                      elapsed_scope='This execution attempt; excludes earlier interrupted attempts',
                      execution='Local windowed Rasterio/Arrow; not a Spark or distributed execution',
                      validation='Exact every-column Parquet round trip, source conservation, native alignment, disjoint windows/tiles, epoch footprints',
                      limitations='Inherited parent settlement category; built-up not joined; country coverage follows the supplied boundary')
        (out/'validation.json').write_text(json.dumps(result, indent=2)+'\n')
        (out/'_SUCCESS').write_text('PASS\n')
        (out/'RUNNING').unlink()
        if (out/'FAILED.json').exists():
            (out/'FAILED.json').rename(out/f'failure_before_resume_{time.time_ns()}.json')
    except Exception as exc:
        (out/'FAILED.json').write_text(json.dumps({'error':str(exc), 'completed_tile_epochs':len(reports)}, indent=2)+'\n')
        raise
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--plan', type=Path, help='Save a source inventory; no downloads or processing without --output')
    parser.add_argument('--output', type=Path, help='New run directory; existing directories are never overwritten')
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--resume', action='store_true', help='Resume an incomplete run after verifying config, source and output hashes')
    parser.add_argument('--block-pixels', type=int, default=1000)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    plan, area = make_plan(cfg)
    if args.plan:
        with args.plan.open('x') as stream:
            stream.write(json.dumps(plan, indent=2)+'\n')
    print(json.dumps({k:plan[k] for k in ('name','tiles','approximate_cells_per_epoch','approximate_cell_year_rows')},indent=2), flush=True)
    if args.output:
        execute(plan, area, args.output, args.download, args.block_pixels, args.resume)


if __name__ == '__main__':
    main()
