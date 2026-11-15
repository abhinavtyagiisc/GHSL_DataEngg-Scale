"""Run gated recovery, then the existing sequential national completion workflow."""
from pathlib import Path
import fcntl,json,os,re,subprocess,sys,time
from datetime import datetime,timezone
PROJECT=Path(__file__).resolve().parents[2];ROOT=PROJECT/'phase3'
sys.path.insert(0,str(PROJECT/'analysis/scripts'));from progress_log import update

def save(status):
    status['updated_utc']=datetime.now(timezone.utc).isoformat();status['controller_pid']=os.getpid()
    p=ROOT/'reports/STATUS.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(status,indent=2));tmp.replace(p)

def retryable_network_failure(report,tail):
    """Retry transport errors only; never retry a data correctness failure."""
    if report.get('status')!='FAILED' or report.get('stage')!='integration':return False
    if 'ValueError:' in tail or 'AssertionError:' in tail:return False
    return bool(re.search(r'requests\.exceptions\.(?:ConnectionError|Timeout|ReadTimeout|ConnectTimeout|ChunkedEncodingError):',tail))


def main():
    if not (PROJECT/'phase2/_SUCCESS').exists():raise ValueError('Phase 2 is not complete')
    with (ROOT/'reports/controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        status=dict(status='RUNNING',stage='recovery');save(status)
        env=os.environ.copy();env['PYSPARK_SUBMIT_ARGS']='--conf spark.sql.files.maxRecordsPerFile=250000 pyspark-shell'
        try:
            recovery=ROOT/'reports/recovery.json'
            stages=[]
            if not recovery.exists():stages.append(('recovery',[sys.executable,'phase3/scripts/run_recovery.py']))
            elif json.loads(recovery.read_text())['status']!='PASS':raise ValueError('Recovery did not pass')
            stages.append(('accepted_scope',[sys.executable,'phase3/scripts/accept_verified_scope.py']))
            stages.append(('national_completion',[sys.executable,'analysis/scripts/complete_week8.py']))
            for stage,cmd in stages:
                status['stage']=stage;save(status)
                for attempt in range(6):
                    status.update(status='RUNNING',retry_count=attempt);save(status)
                    log=ROOT/'reports'/f'{stage}_{time.time_ns()}.log'
                    update('Phase 3 '+stage,'STARTED','Detailed output: '+str(log.relative_to(PROJECT)))
                    with log.open('x') as f:
                        child=subprocess.Popen(cmd,cwd=PROJECT,env=env,stdout=f,stderr=subprocess.STDOUT)
                        status.update(child_pid=child.pid,log=str(log.relative_to(PROJECT)));save(status)
                        while child.poll() is None:
                            time.sleep(30);save(status)
                            update('Phase 3 '+stage,'RUNNING','See phase3/reports/STATUS.json and stage log. Completion remains unverified.',history=False)
                    if not child.returncode:break
                    report_path=PROJECT/'analysis/reports/WEEK8_RUN_STATUS.json'
                    report=json.loads(report_path.read_text()) if report_path.exists() else {}
                    failure_log=Path(report.get('log',str(log)))
                    with failure_log.open('rb') as stream:
                        stream.seek(max(0,failure_log.stat().st_size-20000));tail=stream.read().decode(errors='replace')
                    if stage!='national_completion' or attempt==5 or not retryable_network_failure(report,tail):
                        raise RuntimeError(f'{stage} exited {child.returncode}; see {log}')
                    delay=min(15*2**attempt,60)
                    status.update(status='WAITING_NETWORK_RETRY',last_failure_log=str(failure_log),retry_delay_seconds=delay);save(status)
                    update('Retry transient national download failure','WAITING',f'Retry {attempt+1}/5 in {delay} seconds. Completed checkpoints preserved; validation failures are never automatically retried.')
                    time.sleep(delay)
                update('Phase 3 '+stage,'PASS','Stage completed; next stage proceeds only after its own acceptance checks.')
            status.update(status='PASS',stage='automated_workflow_complete_visual_review_pending');save(status)
        except Exception as exc:
            status.update(status='FAILED',error=str(exc));save(status);update('Phase 3 controller','FAILED',str(exc));raise
if __name__=='__main__':main()
