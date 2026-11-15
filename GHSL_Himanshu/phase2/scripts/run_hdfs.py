"""Reuse verified HDFS inputs, write a new Sedona run, retrieve and health-check."""
from pathlib import Path
import sys,subprocess,json,time
PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'population/scripts'));import hdfs
sys.path.insert(0,str(PROJECT/'analysis/scripts'));from progress_log import update
ROOT=PROJECT/'phase2'
def run(label,cmd,timeout=1800):
    update(label,'STARTED','Phase-2 HDFS execution; see phase2/reports/'+label+'.log')
    with (ROOT/'reports'/f'{label}.log').open('x') as f:
        r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
    update(label,'PASS' if r.returncode==0 else 'FAIL','See phase2/reports/'+label+'.log')
    r.check_returncode()
def main():
    output='/ghsl/phase2/sedona_run1/grid_year'
    local=ROOT/'data/grid_year'
    if local.exists() or (ROOT/'reports/hdfs_validation.json').exists():raise FileExistsError('Preserve previous run')
    if any((hdfs.RUNTIME/f'{k}.pid').exists() for k in ('namenode','datanode')):raise RuntimeError('Existing HDFS ownership; inspect first')
    if not (hdfs.RUNTIME/'namenode/current/VERSION').exists():raise RuntimeError('Existing HDFS metadata missing; never format here')
    try:
        run('hdfs_start',[sys.executable,str(PROJECT/'population/scripts/hdfs.py'),'start'],180)
        run('hdfs_mkdir',hdfs.command('dfs','-mkdir','-p','/ghsl/phase2/sedona_run1'))
        run('hdfs_integrate',[sys.executable,str(ROOT/'src/integrate.py'),'--input',hdfs.URI+'/ghsl/weeks1_5/bengaluru_run1/cleaned/tables','--output',hdfs.URI+output,'--report',str(ROOT/'reports/hdfs_validation.json')])
        run('hdfs_retrieve',hdfs.command('dfs','-get',output,str(local)))
        run('hdfs_health',hdfs.command('fsck','/ghsl/phase2/sedona_run1','-files','-blocks'))
        if 'HEALTHY' not in (ROOT/'reports/hdfs_health.log').read_text():raise ValueError('HDFS unhealthy')
    finally:run('hdfs_stop',[sys.executable,str(PROJECT/'population/scripts/hdfs.py'),'stop'],60)
    (ROOT/'reports/hdfs_execution.json').write_text(json.dumps(dict(status='PASS',output=output,local_output=str(local),replication=1),indent=2))
if __name__=='__main__':main()
