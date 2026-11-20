"""Read the current completion state for the interactive monitor; never launch work."""
from pathlib import Path
import json,fcntl,re,sys
PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'analysis/scripts'));from progress_log import update

def snapshot():
    root=PROJECT/'integration/data/national_run1'
    records=json.loads((root/'progress.json').read_text())
    status=json.loads((PROJECT/'phase3/reports/STATUS.json').read_text())
    stage=json.loads((PROJECT/'analysis/reports/WEEK8_RUN_STATUS.json').read_text())
    held=False
    with (PROJECT/'phase3/reports/controller.lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN)
        except BlockingIOError:held=True
    done={f"{r['tile']}_{r['year']}" for r in records}
    pending=[p for p in (root/'pairs').iterdir() if p.is_dir() and p.name not in done]
    active=max(pending,key=lambda p:p.stat().st_mtime).name if pending else None
    log=Path(stage['log'])
    with log.open('rb') as f:
        f.seek(max(0,log.stat().st_size-16000));tail=f.read().decode(errors='replace')
    boundary=tail.rfind('{"completed":')
    if boundary>=0:tail=tail[tail.find('\n',boundary)+1:]
    stages=re.findall(r'\[Stage (\d+):',tail)
    return dict(status=status['status'],stage=stage.get('stage'),completed=len(records),planned=168,active=active,spark_stage=int(stages[-1]) if stages else None,controller_lock_held=held,log=str(log),handoff_ready=(PROJECT/'analysis/data/final_results/_SUCCESS').exists())

if __name__=='__main__':
    value=snapshot()
    update('Monitor national completion workflow',value['status'],f"{value['completed']}/168 verified; active job {value['active']}; workflow stage {value['stage']}. Spark stage identifier: {value['spark_stage']} (not a completion percentage).")
    print(json.dumps(value))
