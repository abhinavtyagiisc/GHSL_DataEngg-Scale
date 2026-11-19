"""Bounded three-product preparation and checkpointed tile-year Spark execution."""
import argparse
from contextlib import ExitStack
import fcntl
import json
import math
from pathlib import Path
import shutil
import sys
import time
import tempfile

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds, bounds
from shapely.geometry import box, mapping

from prepare_inputs import validate_values
from multitile_population import (load_area, tiles_for_area, tile_bounds, validate_tile,
                                  aligned_windows, digest)
from prepare_population_rasters import zipped_raster
from download_sources import sources, download
from spark_integrate import pipeline

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
PRODUCTS = ('POP', 'BUILT_S', 'BUILT_S_NRES', 'SMOD')


def save(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def validate_source(src, tile, grid, resolution):
    """Allow cropped extents, but require exact native alignment within nominal tile."""
    from rasterio.crs import CRS
    t = src.transform
    if src.crs != CRS.from_string(grid['crs']) or src.count != 1 or src.nodata is None:
        raise ValueError('Source CRS/bands/NoData invalid')
    if not np.allclose([t.a, t.b, t.d, t.e], [resolution, 0, 0, -resolution], atol=1e-7, rtol=0):
        raise ValueError('Source resolution/rotation invalid')
    offsets = ((t.c-grid['origin_x'])/resolution, (grid['origin_y']-t.f)/resolution)
    if any(abs(v-round(v)) > 1e-7 for v in offsets):
        raise ValueError('Source origin is not aligned')
    if not box(*tile_bounds(tile, grid)).covers(box(*src.bounds)):
        raise ValueError('Source extends outside nominal tile')


def read_window(src, extent, resolution):
    w = from_bounds(*extent, src.transform)
    if any(abs(v-round(v)) > 1e-6 for v in (w.col_off,w.row_off,w.width,w.height)):
        raise ValueError('Noninteger read window')
    w = Window(*(round(v) for v in (w.col_off,w.row_off,w.width,w.height)))
    # Outside cropped extent is missing, never inferred zero or extrapolated.
    return src.read(1, window=w, boundless=True, masked=True)


def prepare_pair(paths, tile, year, area, grid, out, block_pixels=1000):
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    report = dict(year=year, tile=tile, fine_rows=0, coarse_rows=0, blocks=0,
                  products={p:dict(valid_pixels=0,nodata_pixels=0,total=0.0) for p in PRODUCTS[:3]})
    with ExitStack() as stack:
        rasters = {p:stack.enter_context(rasterio.open(zipped_raster(paths[p]))) for p in PRODUCTS}
        for p, src in rasters.items():
            validate_source(src,tile,grid,1000 if p=='SMOD' else 100)
        # POP establishes full nominal tile geometry; built-up/SMOD may be cropped.
        ref = rasters['POP']
        validate_tile(ref,tile,grid,100)
        report['native_metadata'] = {p:dict(shape=[s.height,s.width],transform=list(s.transform)[:6],nodata=s.nodata)
                                     for p,s in rasters.items()}
        writers = {}
        for w in aligned_windows(area,ref,block_pixels):
            affine = ref.window_transform(w)
            inside = geometry_mask([mapping(area)], (int(w.height),int(w.width)), affine, invert=True)
            if not inside.any():
                continue
            extent = bounds(w,ref.transform)
            arrays = {p:read_window(s,extent,1000 if p=='SMOD' else 100) for p,s in rasters.items()}
            rows,cols = np.where(inside)
            rr = (round((grid['origin_y']-affine.f)/100)+rows).astype('int32')
            cc = (round((affine.c-grid['origin_x'])/100)+cols).astype('int32')
            keys = dict(year=pa.array(np.full(len(rows),year),type=pa.int32()),source_row=rr,source_col=cc)
            values = {};valids = {}
            for p in PRODUCTS[:3]:
                a = arrays[p];valid = inside & ~np.ma.getmaskarray(a)
                validate_values(a.data,valid,p)
                values[p] = pa.array(a.data[rows,cols], mask=~valid[rows,cols],type=pa.float64())
                valids[p] = valid
                stats = report['products'][p]
                stats['valid_pixels'] += int(valid.sum())
                stats['nodata_pixels'] += int((inside & ~valid).sum())
                stats['total'] += float(np.asarray(a.data,dtype='float64')[valid].sum())
            both = valids['BUILT_S'] & valids['BUILT_S_NRES']
            if np.any(arrays['BUILT_S_NRES'].data[both] > arrays['BUILT_S'].data[both]):
                raise ValueError('NRES exceeds total built surface')
            coarse_inside = inside.reshape(inside.shape[0]//10,10,inside.shape[1]//10,10).any(axis=(1,3))
            sr,sc = np.where(coarse_inside)
            a = arrays['SMOD'];valid = coarse_inside & ~np.ma.getmaskarray(a)
            validate_values(a.data,valid,'SMOD')
            tables = {
                'population':pa.table({**keys,'population':values['POP']}),
                'built_up':pa.table({**keys,'built_surface_m2':values['BUILT_S'],'built_surface_nres_m2':values['BUILT_S_NRES']}),
                'settlement':pa.table(dict(year=pa.array(np.full(len(sr),year),type=pa.int32()),
                    parent_row=(round((grid['origin_y']-affine.f)/1000)+sr).astype('int32'),
                    parent_col=(round((affine.c-grid['origin_x'])/1000)+sc).astype('int32'),
                    settlement_class=pa.array(a.data[sr,sc],mask=~valid[sr,sc],type=pa.int32())))}
            for name,table in tables.items():
                path = out/'tables'/name/'part.parquet'
                if name not in writers:
                    path.parent.mkdir(parents=True)
                    writers[name] = stack.enter_context(pq.ParquetWriter(path,table.schema,compression='snappy'))
                writers[name].write_table(table)
            report['fine_rows'] += len(rows);report['coarse_rows'] += len(sr);report['blocks'] += 1
    if not report['fine_rows']:
        raise ValueError('Tile intersection has no included cell centres')
    # Independently read every staged row group and recover counts/totals.
    for name,columns in [('population',{'population':'POP'}),('built_up',{'built_surface_m2':'BUILT_S','built_surface_nres_m2':'BUILT_S_NRES'})]:
        pf = pq.ParquetFile(out/'tables'/name/'part.parquet')
        if pf.metadata.num_rows != report['fine_rows']:
            raise ValueError('Staging row count mismatch')
        for column,product in columns.items():
            count = 0;total = 0.0
            for batch in pf.iter_batches(columns=[column]):
                a = batch.column(0);count += len(a)-a.null_count
                total += sum(v for v in a.to_pylist() if v is not None)
            expected = report['products'][product]
            if count != expected['valid_pixels'] or not math.isclose(total,expected['total'],rel_tol=1e-10,abs_tol=1e-5):
                raise ValueError('Staging conservation mismatch')
    save(out/'config.json',dict(epochs=[year],scope=f'Three-product tile-year {tile}/{year}; supplied area mask'))
    save(out/'grid_contract.json',grid)
    save(out/'raster_validation.json',dict(status='PASS',epochs=[report]))
    (out/'_SUCCESS').write_text('PASS\n')
    return report


def publish_curated(source, destination):
    """Validate off-workspace Spark output, then publish a verified directory."""
    source,destination=Path(source),Path(destination)
    pending=destination.with_name(destination.name+'.publishing')
    if destination.exists() or pending.exists():raise FileExistsError(destination)
    if not (source/'_INTEGRATION_SUCCESS').exists():raise ValueError('Unvalidated Spark output')
    expected={str(p.relative_to(source)):digest(p) for p in source.rglob('*') if p.is_file()}
    for p in source.rglob('*.parquet'):
        if p.stat().st_size==0:raise ValueError('Zero-byte source Parquet')
        pq.ParquetFile(p).metadata
    shutil.copytree(source,pending)
    for rel,sha in expected.items():
        if digest(pending/rel)!=sha:raise ValueError('Publication checksum mismatch')
    pending.rename(destination)
    for rel,sha in expected.items():
        if digest(destination/rel)!=sha:raise ValueError('Published output changed')
    return dict(files=len(expected),checks='source Parquet footers and every copied/published file SHA256',storage='Spark temporary-directory output; verified atomic directory publication')


def fingerprints():
    files = [Path(__file__),ROOT/'src/prepare_inputs.py',ROOT/'src/spark_integrate.py',
             ROOT/'scripts/download_sources.py',PROJECT/'population/src/multitile_population.py',
             PROJECT/'population/src/prepare_population_rasters.py',PROJECT/'population/src/spark_population.py',
             PROJECT/'population/scripts/download_population_tiles.py']
    return {str(p.relative_to(PROJECT)):digest(p) for p in files}


def execute(cfg, out, resume=False, allow_download=False, max_pairs=None, block_pixels=1000, reserve_gb=20, defer_empty=False):
    if block_pixels < 10 or block_pixels % 10 or reserve_gb < 1 or (max_pairs is not None and max_pairs < 0):
        raise ValueError('Invalid block size, disk reserve or pair limit')
    versions = ('release','population_version','built_version','settlement_version')
    if tuple(cfg.get(k) for k in versions) != ('R2023A','V1_0','V1_0','V2_0'):
        raise ValueError('Unsupported product release/version')
    grid = json.loads((ROOT/'config/grid_contract.json').read_text())
    area,boundary = load_area(cfg)
    epochs = cfg['epochs']
    if not epochs or epochs != sorted(set(epochs)) or not set(epochs)<=set(range(1975,2031,5)):
        raise ValueError('Invalid epochs')
    tiles = tiles_for_area(area,grid)
    identity = dict(config=cfg,grid=grid,boundary=boundary,tiles=tiles,code=fingerprints(),block_pixels=block_pixels)
    out = Path(out)
    if out.exists() and not resume:raise FileExistsError(out)
    if resume and not out.exists():raise FileNotFoundError(out)
    out.mkdir(parents=True,exist_ok=True)
    with (out/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (out/'_SUCCESS').exists():raise ValueError('Run already complete')
        if resume:
            if json.loads((out/'identity.json').read_text()) != identity:raise ValueError('Resume identity changed')
        else:save(out/'identity.json',identity)
        progress = json.loads((out/'progress.json').read_text()) if (out/'progress.json').exists() else []
        expected_pairs = {(tile,year) for tile in tiles for year in epochs}
        completed_pairs = [(r['tile'],r['year']) for r in progress]
        if len(set(completed_pairs)) != len(completed_pairs) or not set(completed_pairs) <= expected_pairs:
            raise ValueError('Invalid checkpoint pair inventory')
        for record in progress:
            for path,sha in record['files'].items():
                if digest(out/path)!=sha:raise ValueError('Completed output changed')
            for path,sha in record['inputs'].items():
                if digest(PROJECT/path)!=sha:raise ValueError('Completed source changed')
            staging = out/'pairs'/f"{record['tile']}_{record['year']}"/'prepared/tables'
            if staging.exists():shutil.rmtree(staging)
        processed = 0
        deferred_path = out/'deferred.json'
        deferred = json.loads(deferred_path.read_text()) if deferred_path.exists() else []
        if defer_empty and not deferred_path.exists():
            deferred = [dict(tile='R8_C27',year=y,status='DEFERRED',reason='User requested postponement after all-NoData failure') for y in epochs if 'R8_C27' in tiles]
            save(deferred_path,deferred)
        def is_deferred(tile,year):
            return any(d['tile']==tile and d['year']==year for d in deferred)
        for retry_pass in ([False,True] if defer_empty else [False]):
            schedule = ([(d['tile'],d['year']) for d in deferred if d['status']=='DEFERRED'] if retry_pass else
                        [(t,y) for t in tiles for y in epochs if not (defer_empty and is_deferred(t,y))])
            for tile,year in schedule:
                if any(r['tile']==tile and r['year']==year for r in progress):continue
                if max_pairs is not None and processed>=max_pairs:return progress
                if shutil.disk_usage(out).free < reserve_gb*1e9:raise ValueError('Free disk below reserve')
                pair = out/'pairs'/f'{tile}_{year}'
                if pair.exists():
                    saved = out/'incomplete'/f'{tile}_{year}_{time.time_ns()}'
                    saved.parent.mkdir(exist_ok=True);pair.rename(saved)
                pair.mkdir(parents=True)
                paths = {};manifest = []
                for item in sources(dict(tile=tile,epochs=[year])):
                    p = item['path']
                    if retry_pass:
                        # Fresh, separately retained archive: never overwrite original evidence.
                        p = p.parent/'deferred_retries'/f'{tile}_{year}_{time.time_ns()}'/p.name
                    if not p.exists() and not allow_download:raise FileNotFoundError(f'{p}; use --download')
                    record = download((item['url'],p))
                    manifest.append(dict(product=item['product'],**record))
                    paths[item['product']] = p
                save(pair/'sources.json',manifest)
                prep = pair/'prepared'
                stats = prepare_pair(paths,tile,year,area,grid,prep,block_pixels)
                scratch=Path(tempfile.mkdtemp(prefix='ghsl-national-'))
                save(pair/'scratch_execution.json',dict(path=str(scratch),status='RUNNING'))
                # Keep scratch on failure for diagnosis/reuse; remove only after verified publication.
                try:
                    pipeline(prep,str(prep/'tables'),str(scratch/'curated'),pair/'spark_validation.json','local[2]')
                except ValueError as exc:
                    if not defer_empty or str(exc) != 'An epoch has no valid analytical cells':
                        raise
                    entry = next((d for d in deferred if d['tile']==tile and d['year']==year),None)
                    if entry is None:
                        entry=dict(tile=tile,year=year);deferred.append(entry)
                    entry.update(status='UNRESOLVED' if retry_pass else 'DEFERRED',reason=str(exc),
                                 refreshed_sources=retry_pass,evidence=str(pair),preparation=stats)
                    save(deferred_path,deferred)
                    save(pair/'scratch_execution.json',dict(path=str(scratch),status=entry['status'],reason=str(exc)))
                    print(json.dumps(dict(tile=tile,year=year,status=entry['status'])),flush=True)
                    continue
                publication=publish_curated(scratch/'curated',pair/'curated')
                result=json.loads((pair/'spark_validation.json').read_text())
                result.update(execution_output=result.get('output'),output=str(pair/'curated'),publication=publication)
                save(pair/'spark_validation.json',result)
                save(pair/'scratch_execution.json',dict(path=str(scratch),status='PUBLISHED',publication=publication))
                shutil.rmtree(scratch)
                files = {str(p.relative_to(out)):digest(p) for p in pair.rglob('*') if p.is_file() and 'tables' not in p.parts}
                record = dict(tile=tile,year=year,preparation=stats,files=files,
                              inputs={str(p.relative_to(PROJECT)):digest(p) for p in paths.values()})
                progress.append(record);save(out/'progress.json',progress)
                # Only generated staging tables of this validated pair are removed.
                shutil.rmtree(prep/'tables')
                if retry_pass:
                    next(d for d in deferred if d['tile']==tile and d['year']==year).update(status='RESOLVED',refreshed_sources=True)
                    save(deferred_path,deferred)
                processed += 1
                print(json.dumps(dict(completed=len(progress),planned=len(tiles)*len(epochs),tile=tile,year=year)),flush=True)
        if len(progress) != len(expected_pairs):
            save(out/'deferred_validation.json',dict(status='INCOMPLETE',completed=len(progress),planned=len(expected_pairs),deferred=deferred))
            raise ValueError('Deferred tile-years remain unresolved after fresh-source retry; see deferred.json')
        for tile in tiles:
            if len({(r['preparation']['fine_rows'],r['preparation']['coarse_rows']) for r in progress if r['tile']==tile}) != 1:
                raise ValueError('Epoch masks changed')
        save(out/'validation.json',dict(status='PASS',tile_years=len(progress),scope=cfg['name'],
            execution='Windowed local raster staging; Spark local[2] per tile-year; no HDFS copy',
            limitations='Cross-year common-valid masks and national temporal/district analysis require separate validation'))
        (out/'_SUCCESS').write_text('PASS\n')
    return progress


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--resume',action='store_true');p.add_argument('--download',action='store_true')
    p.add_argument('--max-pairs',type=int);p.add_argument('--block-pixels',type=int,default=1000)
    p.add_argument('--reserve-gb',type=float,default=20)
    p.add_argument('--defer-empty',action='store_true')
    a=p.parse_args()
    execute(json.loads(a.config.read_text()),a.output,a.resume,a.download,a.max_pairs,a.block_pixels,a.reserve_gb,a.defer_empty)
