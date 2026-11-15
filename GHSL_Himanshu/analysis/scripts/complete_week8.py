"""Sequential, durable week-8 completion controller. Never labels running work complete."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from progress_log import update

PROJECT=Path(__file__).resolve().parents[2]
REPORTS=PROJECT/'analysis/reports'
STATUS=REPORTS/'WEEK8_RUN_STATUS.json'
PYTHON=PROJECT/'.venv/bin/python'
INTEGRATION=PROJECT/'integration/data/accepted_coverage_run1'
TEMPORAL=PROJECT/'analysis/data/national_temporal'
DISTRICTS=PROJECT/'analysis/data/national_districts'
CANDIDATES=PROJECT/'analysis/data/national_candidates'
HANDOFF=PROJECT/'analysis/data/week8_handoff'
EVALUATION=PROJECT/'analysis/data/national_case_studies'


def now():return datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()


def save(value):
    value.update(updated=now(),controller_pid=os.getpid())
    tmp=STATUS.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(STATUS)


def main():
    with (REPORTS/'week8_controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        status=dict(status='RUNNING',started=now(),completed_stages=[])
        stages=[
          ('integration',INTEGRATION,[str(PYTHON),'integration/src/national.py','--config','integration/config/india.json','--output',str(INTEGRATION),'--download','--resume','--defer-empty']),
          ('temporal',TEMPORAL,[str(PYTHON),'phase3/scripts/run_analysis_stage.py','--stage','temporal','--input',str(INTEGRATION),'--output',str(TEMPORAL)]),
          ('districts',DISTRICTS,[str(PYTHON),'phase3/scripts/run_analysis_stage.py','--stage','districts','--input',str(INTEGRATION),'--output',str(DISTRICTS)]),
          ('candidates',CANDIDATES,[str(PYTHON),'phase3/scripts/run_analysis_stage.py','--stage','candidates','--input',str(TEMPORAL),'--output',str(CANDIDATES)]),
          ('case_studies',EVALUATION,[str(PYTHON),'phase3/scripts/run_analysis_stage.py','--stage','case_studies','--input',str(INTEGRATION),'--output',str(EVALUATION)]),
          ('handoff',HANDOFF,[str(PYTHON),'analysis/scripts/finish_week8.py','--integration',str(INTEGRATION),'--temporal',str(TEMPORAL),'--districts',str(DISTRICTS),'--candidates',str(CANDIDATES),'--output',str(HANDOFF)])]
        try:
            for name,output,command in stages:
                status.update(stage=name,output=str(output));save(status)
                if name=='integration':
                    # Wait for any first-pair/manual owner, then inspect its saved result.
                    with (INTEGRATION/'run.lock').open('a') as run_lock:
                        fcntl.flock(run_lock,fcntl.LOCK_EX)
                        fcntl.flock(run_lock,fcntl.LOCK_UN)
                if (output/'_SUCCESS').exists():
                    report=json.loads((output/'validation.json').read_text())
                    if report['status']!='PASS':raise ValueError(f'Invalid success marker: {name}')
                else:
                    if name!='integration' and output.exists():
                        raise FileExistsError(f'Preserve and inspect unfinished {name} output before restarting: {output}')
                    log=REPORTS/f'week8_{name}_{time.time_ns()}.log'
                    status.update(log=str(log),command=command);save(status)
                    update(' '.join(command),'STARTED',f'Detailed output: `{log.relative_to(PROJECT)}`. Completion is not yet verified.')
                    with log.open('x') as stream:
                        child=subprocess.Popen(command,cwd=PROJECT,stdout=stream,stderr=subprocess.STDOUT)
                        status['child_pid']=child.pid;save(status)
                        while child.poll() is None:
                            time.sleep(30)
                            update(' '.join(command),'RUNNING',f'Detailed output: `{log.relative_to(PROJECT)}`. Checkpoint count is refreshed automatically.',history=False)
                        rc=child.returncode
                    update(' '.join(command),'PASS' if rc==0 else f'FAILED (exit {rc})',f'Detailed output: `{log.relative_to(PROJECT)}`.')
                    if rc!=0:raise RuntimeError(f'{name} exited {rc}; see {log}')
                    if not (output/'_SUCCESS').exists():raise ValueError(f'{name} lacks final success marker')
                status['completed_stages'].append(name);save(status)
            status.update(status='PASS',stage='complete',finished=now());save(status)
            context=PROJECT/'PROJECT_CONTEXT.md'
            with context.open('a') as f:
                f.write('\n## Automated week-8 completion '+now()+'\n\nAll national stages including regional evaluation finished with PASS markers. See\n`analysis/reports/WEEK8_RUN_STATUS.json` and `analysis/data/week8_handoff/REPORT.md`.\nCompact archive: `GHSL_Weeks1_8_National_Handoff.zip`.\nHuman visual review of generated figures remains separate from automated validation.\n')
        except Exception as exc:
            status.update(status='FAILED',error=str(exc),finished=now());save(status)
            update('Week 8 sequential controller','FAILED',str(exc))
            raise


if __name__=='__main__':main()
