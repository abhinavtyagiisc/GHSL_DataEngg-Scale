"""Run final single/dual-worker measurements sequentially, with durable progress."""
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'analysis/scripts'));from progress_log import update

for workers,name in [(1,'sedona_local1_run3'),(2,'sedona_local2_run1')]:
    output=ROOT/'reports'/name;log=ROOT/'reports'/(name+'.log')
    if output.exists() or log.exists():raise FileExistsError(output)
    command=[sys.executable,str(ROOT/'src/sedona_benchmark.py'),'--workers',str(workers),'--output',str(output)]
    update(' '.join(command),'STARTED','Final accepted benchmark instrumentation: fresh query per repetition, isolated task groups, no concurrent project workload.')
    with log.open('x') as f:result=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,cwd=PROJECT)
    update(' '.join(command),'PASS' if result.returncode==0 else 'FAILED',f'Detailed output: `{log.relative_to(PROJECT)}`.')
    if result.returncode:raise SystemExit(result.returncode)
print('Both final Sedona benchmark runs passed.')
