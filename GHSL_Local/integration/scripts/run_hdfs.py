"""Execute the complete three-product pilot on isolated local HDFS and stop services."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
POP=ROOT.parent/'population'
sys.path.insert(0,str(POP/'scripts'))
import hdfs


def logged(name,command,timeout=900):
    print(name,flush=True)
    with (ROOT/'reports'/name).open('x') as stream:
        subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=timeout)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hdfs-root',default='/ghsl/weeks1_5/bengaluru_run1')
    parser.add_argument('--local-output',type=Path,default=ROOT/'data/curated/grid_year')
    args=parser.parse_args()
    if args.local_output.exists() or (ROOT/'reports/spark_hdfs_validation.json').exists():
        raise FileExistsError('Completed/local output already exists; preserve it and use a distinct run')
    if not (ROOT/'data/prepared/_SUCCESS').exists():raise ValueError('Raster preparation is incomplete')
    if any((POP/'runtime'/f'{kind}.pid').exists() for kind in ('namenode','datanode')):
        raise RuntimeError('HDFS has existing PID files; inspect running service ownership before using this orchestrator')
    bundle=ROOT/'data/raw_bundle'
    if bundle.exists():raise FileExistsError(bundle)
    bundle.mkdir(parents=True)
    manifest=json.loads((ROOT/'reports/download_manifest_full.json').read_text())
    for item in manifest:
        source=POP/item['path'];dest=bundle/item['product']/source.name
        dest.parent.mkdir(parents=True,exist_ok=True)
        with source.open('rb') as f:
            if hashlib.file_digest(f,'sha256').hexdigest()!=item['sha256']:raise ValueError('Source changed before HDFS stage')
        os.link(source,dest)
    (bundle/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    started=time.monotonic()
    try:
        logged('hdfs_start.log',[sys.executable,str(POP/'scripts/hdfs.py'),'start'],180)
        result=subprocess.run(hdfs.command('dfs','-test','-e',args.hdfs_root),capture_output=True)
        if result.returncode!=1:raise RuntimeError('HDFS target exists or cannot be checked')
        logged('hdfs_mkdir.log',hdfs.command('dfs','-mkdir','-p',args.hdfs_root+'/curated'))
        logged('hdfs_stage_raw.log',hdfs.command('dfs','-put',str(bundle),args.hdfs_root+'/raw'))
        logged('hdfs_stage_cleaned.log',hdfs.command('dfs','-put',str(ROOT/'data/prepared'),args.hdfs_root+'/cleaned'))
        output=hdfs.URI+args.hdfs_root+'/curated/grid_year'
        logged('spark_hdfs.log',[sys.executable,str(ROOT/'src/spark_integrate.py'),
            '--input',hdfs.URI+args.hdfs_root+'/cleaned/tables','--output',output,
            '--report',str(ROOT/'reports/spark_hdfs_validation.json')],1800)
        args.local_output.parent.mkdir(parents=True,exist_ok=True)
        logged('hdfs_download.log',hdfs.command('dfs','-get',output,str(args.local_output)))
        logged('hdfs_health.txt',hdfs.command('fsck',args.hdfs_root,'-files','-blocks'))
        if 'HEALTHY' not in (ROOT/'reports/hdfs_health.txt').read_text():raise ValueError('HDFS health check failed')
        logged('hdfs_cluster.txt',hdfs.command('dfsadmin','-report'))
        logged('hdfs_files.txt',hdfs.command('dfs','-ls','-R',args.hdfs_root))
        (ROOT/'reports/hdfs_execution.json').write_text(json.dumps(dict(status='PASS',hdfs_root=args.hdfs_root,
             local_output=str(args.local_output),elapsed_seconds=round(time.monotonic()-started,2),
             source_archives=len(manifest),replication=1),indent=2)+'\n')
    finally:
        logged('hdfs_stop.log',[sys.executable,str(POP/'scripts/hdfs.py'),'stop'],60)
    print('Three-product HDFS execution passed; services stopped.',flush=True)


if __name__=='__main__':main()
