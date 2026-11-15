from pathlib import Path
import json,subprocess,sys
PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'analysis/scripts'));from progress_log import update
cfg=json.loads((PROJECT/'phase2/config/benchmark.json').read_text())
for mode,workers,partitions in cfg['scenarios']:
    name=f'{mode}_w{workers}_p{partitions}'
    if (PROJECT/f'phase2/reports/benchmarks/{name}/_SUCCESS').exists():continue
    cmd=[sys.executable,str(PROJECT/'phase2/scripts/benchmark.py'),'--mode',mode,'--workers',str(workers),'--partitions',str(partitions)]
    with (PROJECT/f'phase2/reports/benchmark_{name}.log').open('x') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    update('Run benchmark scenario '+name,'PASS' if r.returncode==0 else 'FAIL','See phase2/reports/benchmark_'+name+'.log');r.check_returncode()
