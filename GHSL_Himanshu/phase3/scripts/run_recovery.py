"""Validate one preserved national resume with bounded Parquet file sizes."""
from pathlib import Path
import os,sys,subprocess,time,json
import pyarrow.parquet as pq
PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'analysis/scripts'));from progress_log import update
ROOT=PROJECT/'phase3';DATA=PROJECT/'integration/data/national_run1'
def main():
    if not (PROJECT/'phase2/_SUCCESS').exists():raise ValueError('Phase 2 must pass first')
    before=json.loads((DATA/'progress.json').read_text())
    report=ROOT/'reports/recovery.json'
    if report.exists():raise FileExistsError(report)
    attempt=ROOT/'reports'/f'recovery_attempt_{time.time_ns()}';attempt.mkdir()
    (ROOT/'reports/recovery_current.json').write_text(json.dumps(dict(attempt=str(attempt.relative_to(PROJECT)),log=str((attempt/'recovery.log').relative_to(PROJECT))),indent=2))
    env=os.environ.copy();env['PYSPARK_SUBMIT_ARGS']='--conf spark.sql.files.maxRecordsPerFile=250000 pyspark-shell'
    config=dict(max_records_per_file=250000,prior_completed=len(before),reason='Repeated zero-byte output: temporary-directory validation and checksum-verified publication plus file cap; original cause unconfirmed',code='Explicit migrated national identity; original code and all failed attempts preserved')
    (attempt/'recovery_environment.json').write_text(json.dumps(config,indent=2))
    cmd=[sys.executable,'integration/src/national.py','--config','integration/config/india.json','--output',str(DATA),'--resume','--download','--max-pairs','1']
    label='National recovery: one pending tile-year with bounded output files'
    update(label,'STARTED','See '+str((attempt/'recovery.log').relative_to(PROJECT))+'; completed pair and failed attempts preserved.')
    with (attempt/'recovery.log').open('x') as f:
        child=subprocess.Popen(cmd,cwd=PROJECT,env=env,stdout=f,stderr=subprocess.STDOUT)
        while child.poll() is None:
            time.sleep(30);update(label,'RUNNING','See '+str((attempt/'recovery.log').relative_to(PROJECT))+'; full national completion not established.',history=False)
    if child.returncode:
        update(label,'FAIL',f'Exit {child.returncode}; inspect {attempt}/recovery.log');raise RuntimeError('Recovery failed')
    after=json.loads((DATA/'progress.json').read_text())
    if len(after)!=len(before)+1:raise ValueError('Recovery did not add exactly one verified pair')
    record=after[-1];files=[]
    for rel in record['files']:
        if rel.endswith('.parquet'):
            p=DATA/rel;meta=pq.ParquetFile(p).metadata
            if p.stat().st_size==0 or meta.num_rows>250000:raise ValueError('Output cap/footer validation failed')
            files.append(dict(path=rel,bytes=p.stat().st_size,rows=meta.num_rows))
    report.write_text(json.dumps(dict(status='PASS',tile=record['tile'],year=record['year'],completed=len(after),files=files,environment=config),indent=2))
    update(label,'PASS',f'{record["tile"]}/{record["year"]} passed full integration; every output footer readable and record cap respected. National count {len(after)}/168.')
if __name__=='__main__':main()
