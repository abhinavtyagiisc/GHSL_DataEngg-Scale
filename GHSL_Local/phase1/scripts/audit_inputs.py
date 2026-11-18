"""Re-audit all pilot products and independently retrieve their actual HDFS zones."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile
import numpy as np
import pyarrow.parquet as pq
import rasterio

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'analysis/scripts'));from progress_log import update
sys.path.insert(0,str(PROJECT/'population/scripts'));import hdfs


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def logged(command,path,timeout=900):
    update(' '.join(map(str,command)),'STARTED',f'Phase-1 audit output: `{path.relative_to(PROJECT)}`.')
    start=time.monotonic()
    with path.open('x') as f:r=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
    update(' '.join(map(str,command)),'PASS' if r.returncode==0 else 'FAILED',f'Output: `{path.relative_to(PROJECT)}`. Elapsed {time.monotonic()-start:.2f} seconds.')
    if r.returncode:raise RuntimeError(f'Command failed; inspect {path}')
    return time.monotonic()-start


def main(out):
    out=Path(out).resolve()
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    start=time.monotonic();manifest=json.loads((PROJECT/'integration/reports/download_manifest_full.json').read_text())
    epochs=list(range(1975,2031,5));products=['POP','BUILT_S','BUILT_S_NRES','SMOD']
    if {(r['product'],r['year']) for r in manifest}!={(p,y) for p in products for y in epochs} or len(manifest)!=48:raise ValueError('Missing/duplicate source archive')
    checks=[]
    for r in manifest:
        path=PROJECT/'population'/r['path']
        if digest(path)!=r['sha256']:raise ValueError('Cached source SHA changed')
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None:raise ValueError('ZIP CRC failed')
        checks.append(dict(product=r['product'],year=r['year'],sha256=r['sha256'],bytes=path.stat().st_size))
    archive_seconds=time.monotonic()-start
    prep=PROJECT/'integration/data/prepared'
    validation=json.loads((prep/'raster_validation.json').read_text())
    if validation['status']!='PASS' or not (prep/'_SUCCESS').exists():raise ValueError('Prepared inputs incomplete')
    raster_checks=[]
    for r in validation['epochs']:
        year=r['year'];masks=[];transforms=[]
        for product in products:
            with rasterio.open(prep/'rasters'/product/f'{year}.tif') as src:
                if src.nodata is None or src.count!=1:raise ValueError('Invalid raster NoData/band count')
                if str(src.crs) not in ('ESRI:54009','ESRI:54009'):raise ValueError('Unexpected raster CRS')
                a=src.read(1,masked=True);valid=~np.ma.getmaskarray(a)
                resolution=1000 if product=='SMOD' else 100
                if not np.allclose([src.transform.a,src.transform.b,src.transform.d,src.transform.e],[resolution,0,0,-resolution]):raise ValueError('Raster resolution/rotation mismatch')
                if product=='SMOD':
                    if not set(np.unique(a.data[valid]))<={10,11,12,13,21,22,23,30}:raise ValueError('Invalid settlement code')
                    if int(valid.sum())!=r['settlement_valid_cells']:raise ValueError('Settlement coverage mismatch')
                else:
                    stats=r['products'][product]
                    if int(valid.sum())!=stats['valid_pixels'] or not math.isclose(float(a.data[valid].astype('float64').sum()),stats['total'],rel_tol=1e-10,abs_tol=1e-5):raise ValueError('Raster totals changed')
                    masks.append(valid);transforms.append(src.transform)
                raster_checks.append(dict(product=product,year=year,valid_pixels=int(valid.sum()),resolution_m=resolution))
        if not all(np.array_equal(masks[0],m) for m in masks[1:]) or len(set(transforms))!=1:raise ValueError('Fine-product masks/grids differ')
        for name,fields in [('population',{'population':'POP'}),('built_up',{'built_surface_m2':'BUILT_S','built_surface_nres_m2':'BUILT_S_NRES'})]:
            table=pq.read_table(prep/'tables'/name/f'{year}.parquet')
            if len(table)!=r['fine_rows']:raise ValueError('Staging row count mismatch')
            for col,product in fields.items():
                values=table[col].to_numpy()
                if not math.isclose(float(np.nansum(values)),r['products'][product]['total'],rel_tol=1e-10,abs_tol=1e-5):raise ValueError('Staging totals mismatch')
    update('Audit all 48 source archives, 48 prepared rasters and fine-product staging totals','PASS','Verified source SHA256/ZIP CRC, product/year inventory, CRS, resolutions, masks, settlement codes and conservation from existing saved inputs.')
    runtime=PROJECT/'population/runtime'
    if any((runtime/f'{kind}.pid').exists() for kind in ('namenode','datanode')):raise RuntimeError('Existing HDFS PID files; inspect before taking ownership')
    hdfs_root='/ghsl/weeks1_5/bengaluru_run1'
    retrieved=out/'retrieved';retrieved.mkdir()
    transfer=[];started=False
    try:
        started=True
        logged([sys.executable,str(PROJECT/'population/scripts/hdfs.py'),'start'],out/'hdfs_start.log',180)
        logged(hdfs.command('dfsadmin','-report'),out/'hdfs_cluster.txt')
        logged(hdfs.command('fsck',hdfs_root,'-files','-blocks'),out/'hdfs_health.txt')
        if 'HEALTHY' not in (out/'hdfs_health.txt').read_text():raise ValueError('HDFS is not healthy')
        for zone in ('raw','cleaned','curated'):
            seconds=logged(hdfs.command('dfs','-get',hdfs_root+'/'+zone,str(retrieved/zone)),out/f'hdfs_get_{zone}.log',1800)
            size=sum(p.stat().st_size for p in (retrieved/zone).rglob('*') if p.is_file() and not p.name.startswith('.'))
            transfer.append(dict(zone=zone,bytes=size,wall_seconds=seconds,decimal_MB_per_second=size/seconds/1e6))
        for r in manifest:
            name=Path(r['path']).name
            if digest(retrieved/'raw'/r['product']/name)!=r['sha256']:raise ValueError('HDFS raw SHA mismatch')
        compared=0
        for source,target in [(prep,retrieved/'cleaned'),(PROJECT/'integration/data/curated/grid_year',retrieved/'curated/grid_year')]:
            for path in source.rglob('*'):
                if path.is_file() and not path.name.startswith('.'):
                    other=target/path.relative_to(source)
                    if digest(other)!=digest(path):raise ValueError('HDFS/local content mismatch: '+str(other))
                    compared+=1
        if not (retrieved/'curated/grid_year/_INTEGRATION_SUCCESS').exists():raise ValueError('Missing curated success marker')
        result=dict(status='PASS',epochs=epochs,historical_epochs=epochs[:10],test_epochs=epochs[10:],source_archives=checks,
                    source_bytes=sum(r['bytes'] for r in checks),source_audit_seconds=archive_seconds,raster_checks=raster_checks,
                    hdfs_root=hdfs_root,hdfs_compared_prepared_curated_files=compared,hdfs_transfer=transfer,
                    hdfs_replication=1,method='Reused validated official JRC inputs; independently retrieved HDFS zones and compared every non-hidden prepared/curated file and all raw archive hashes',
                    elapsed_seconds=time.monotonic()-start)
        (out/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
        # These are new disposable verification copies; originals and HDFS remain intact.
        shutil.rmtree(retrieved)
    finally:
        if started:logged([sys.executable,str(PROJECT/'population/scripts/hdfs.py'),'stop'],out/'hdfs_stop.log',120)
    (out/'_SUCCESS').write_text('PASS\n')
    update('Complete all-product source/HDFS phase-1 audit','PASS',f'Actual HDFS retrieval and byte-level comparisons passed. Evidence: `{out.relative_to(PROJECT)}/validation.json`. Verification-only copies removed; original data preserved.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    try:main(a.output)
    except Exception as exc:update('Phase-1 source/HDFS audit','FAILED',str(exc));raise
