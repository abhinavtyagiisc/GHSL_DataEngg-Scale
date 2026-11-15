"""Validate and clip all pilot rasters, staging independent tables for Spark joins."""
import argparse
from contextlib import ExitStack
import json
import math
from pathlib import Path
import sys

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds, bounds as window_bounds
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]
POP=ROOT.parent/'population'
sys.path.insert(0,str(POP/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
from prepare import validate_alignment, zipped_raster
from multitile_population import load_area, digest, table_digest, SMOD_CLASSES
from download_sources import sources


def read_aligned(src, ref, extent, resolution):
    if resolution==100:
        validate_alignment(src,ref)
    elif src.crs!=ref.crs or tuple(src.transform)[:6]!=tuple(ref.transform)[:6] or (src.width,src.height)!=(ref.width,ref.height):
        raise ValueError('Settlement epochs have different grids')
    if src.count!=1 or src.nodata is None:
        raise ValueError('Expected one band and explicit NoData')
    if not box(*src.bounds).covers(box(*extent)):
        raise ValueError('Source does not cover the full shared pilot window')
    w=from_bounds(*extent,src.transform)
    if any(abs(v-round(v))>1e-6 for v in (w.col_off,w.row_off,w.width,w.height)):
        raise ValueError('Non-integer raster window; resampling is forbidden')
    w=Window(*(round(v) for v in (w.col_off,w.row_off,w.width,w.height)))
    arr=src.read(1,window=w,masked=True)
    return arr,src.window_transform(w)


def validate_values(values,valid,product):
    if np.any(~np.isfinite(values[valid])) or np.any(values[valid]<0):
        raise ValueError(f'{product}: negative or nonfinite value')
    if product.startswith('BUILT') and np.any(values[valid]>10000):
        raise ValueError('Built-up surface exceeds the 100 m cell area')
    if product=='SMOD' and np.any(~np.isin(values[valid],list(SMOD_CLASSES))):
        raise ValueError('Invalid settlement class')


def write_table(table,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    pq.write_table(table,path,compression='snappy')
    if table_digest(table)!=table_digest(pq.ParquetFile(path).read()):
        raise ValueError('Staging Parquet round-trip mismatch')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'data/prepared')
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    cfg=json.loads((ROOT/'config/pilot.json').read_text())
    if (cfg['release'],cfg['population_version'],cfg['built_version'],cfg['settlement_version'])!=('R2023A','V1_0','V1_0','V2_0'):
        raise ValueError('Unsupported product release/version')
    manifest=json.loads((ROOT/'reports/download_manifest_full.json').read_text())
    expected={(s['product'],s['year']) for s in sources(cfg)}
    if {(m['product'],m['year']) for m in manifest}!=expected or len(manifest)!=len(expected):
        raise ValueError('Source inventory is incomplete or duplicated')
    paths={}
    for m in manifest:
        p=POP/m['path']
        if digest(p)!=m['sha256']:raise ValueError('Source checksum changed')
        paths[m['product'],m['year']]=p
    # The pilot must be inside the retained India mask; it is not a municipal boundary.
    india=json.loads((POP/'data/raw/boundaries/geoBoundaries-IND-ADM0.geojson').read_text())
    if not unary_union([shape(f['geometry']) for f in india['features']]).covers(box(*cfg['bbox_wgs84'])):
        raise ValueError('Pilot is not entirely inside the retained India boundary')
    area,_=load_area({'bbox_wgs84':cfg['bbox_wgs84']})
    grid=json.loads((ROOT/'config/grid_contract.json').read_text())
    args.output.mkdir(parents=True)
    (args.output/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
    (args.output/'grid_contract.json').write_text(json.dumps(grid,indent=2)+'\n')
    reports=[]
    with rasterio.open(zipped_raster(paths['SMOD',cfg['reference_epoch']])) as ref:
        w=from_bounds(*area.bounds,ref.transform)
        r0,c0=math.floor(w.row_off),math.floor(w.col_off)
        r1,c1=math.ceil(w.row_off+w.height),math.ceil(w.col_off+w.width)
        cw=Window(c0,r0,c1-c0,r1-r0)
        extent=window_bounds(cw,ref.transform)
        for year in cfg['epochs']:
            arrays={};transforms={};metadata={}
            with ExitStack() as stack:
                for product in ('POP','BUILT_S','BUILT_S_NRES','SMOD'):
                    src=stack.enter_context(rasterio.open(zipped_raster(paths[product,year])))
                    resolution=1000 if product=='SMOD' else 100
                    arr,affine=read_aligned(src,ref,extent,resolution)
                    arrays[product]=arr;transforms[product]=affine
                    metadata[product]=dict(crs=str(src.crs),dtype=src.dtypes[0],nodata=src.nodata,
                                           source_transform=list(src.transform)[:6],source_shape=[src.height,src.width])
            affine=transforms['POP'];arr=arrays['POP']
            if any(transforms[p]!=affine or arrays[p].shape!=arr.shape for p in ('BUILT_S','BUILT_S_NRES')):
                raise ValueError('Fine products do not share exact clipped pixel boundaries')
            inside=geometry_mask([mapping(area)],arr.shape,affine,invert=True)
            rows,cols=np.where(inside)
            global_r=round((grid['origin_y']-affine.f)/100)+rows
            global_c=round((affine.c-grid['origin_x'])/100)+cols
            fine_keys={'year':pa.array(np.full(len(rows),year),type=pa.int32()),
                       'source_row':pa.array(global_r,type=pa.int32()),'source_col':pa.array(global_c,type=pa.int32())}
            fine_values={};valids={};stats={}
            for product in ('POP','BUILT_S','BUILT_S_NRES'):
                a=arrays[product];valid=inside & ~np.ma.getmaskarray(a)
                values=np.asarray(a.data,dtype='float64')
                validate_values(values,valid,product)
                fine_values[product]=pa.array(values[rows,cols],mask=~valid[rows,cols],type=pa.float64())
                valids[product]=valid
                stats[product]=dict(valid_pixels=int(valid.sum()),nodata_pixels=int((inside & ~valid).sum()),total=float(values[valid].sum()))
            both=valids['BUILT_S'] & valids['BUILT_S_NRES']
            if np.any(arrays['BUILT_S_NRES'].data[both]>arrays['BUILT_S'].data[both]):
                raise ValueError('Non-residential built-up area exceeds total built-up area')
            for product in arrays:
                a=arrays[product]
                valid=~np.ma.getmaskarray(a)
                if product=='SMOD':
                    coarse_inside=inside.reshape(inside.shape[0]//10,10,inside.shape[1]//10,10).any(axis=(1,3))
                    valid &= coarse_inside
                else:valid &= inside
                out=args.output/'rasters'/product/f'{year}.tif';out.parent.mkdir(parents=True,exist_ok=True)
                with rasterio.open(out,'w',driver='GTiff',height=a.shape[0],width=a.shape[1],count=1,
                                   dtype=a.dtype,crs=ref.crs,transform=transforms[product],nodata=metadata[product]['nodata'],
                                   compress='deflate',tiled=True) as dst:
                    dst.write(np.where(valid,a.data,metadata[product]['nodata']).astype(a.dtype),1)
            write_table(pa.table({**fine_keys,'population':fine_values['POP']}),args.output/'tables/population'/f'{year}.parquet')
            write_table(pa.table({**fine_keys,'built_surface_m2':fine_values['BUILT_S'],
                                  'built_surface_nres_m2':fine_values['BUILT_S_NRES']}),args.output/'tables/built_up'/f'{year}.parquet')
            sr,sc=np.where(coarse_inside)
            sa=arrays['SMOD'];sv=~np.ma.getmaskarray(sa) & coarse_inside
            validate_values(sa.data,sv,'SMOD')
            parent_r=round((grid['origin_y']-transforms['SMOD'].f)/1000)+sr
            parent_c=round((transforms['SMOD'].c-grid['origin_x'])/1000)+sc
            settlement=pa.table({'year':pa.array(np.full(len(sr),year),type=pa.int32()),
                'parent_row':pa.array(parent_r,type=pa.int32()),'parent_col':pa.array(parent_c,type=pa.int32()),
                'settlement_class':pa.array(sa.data[sr,sc],mask=~sv[sr,sc],type=pa.int32())})
            write_table(settlement,args.output/'tables/settlement'/f'{year}.parquet')
            report=dict(year=year,fine_rows=len(rows),coarse_rows=len(sr),products=stats,
                        settlement_valid_cells=int(sv.sum()),settlement_codes=sorted(int(x) for x in np.unique(sa.data[sv])),
                        native_metadata=metadata)
            reports.append(report);print(json.dumps(report),flush=True)
    if len({(r['fine_rows'],r['coarse_rows']) for r in reports})!=1:raise ValueError('Epoch footprints changed')
    (args.output/'raster_validation.json').write_text(json.dumps({'status':'PASS','epochs':reports},indent=2)+'\n')
    (args.output/'_SUCCESS').write_text('PASS\n')


if __name__=='__main__':main()
