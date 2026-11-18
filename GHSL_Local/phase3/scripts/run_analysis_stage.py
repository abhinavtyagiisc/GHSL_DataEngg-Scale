"""Keep national analysis Spark writes off the project path until fully validated."""
import argparse,hashlib,json,shutil,subprocess,sys,tempfile,time
from pathlib import Path
import pyarrow.parquet as pq
PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'analysis/scripts'));from progress_log import update
STAGES={'temporal':('analysis/src/national_temporal.py','--input'),'districts':('analysis/src/national_districts.py','--input'),'candidates':('analysis/src/national_candidates.py','--input'),'case_studies':('phase3/scripts/evaluate_regions.py','--integration')}

def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def publish(source,out):
    source,out=Path(source),Path(out);pending=out.with_name(out.name+'.publishing')
    if out.exists() or pending.exists():raise FileExistsError(out)
    if not (source/'_SUCCESS').exists() or json.loads((source/'validation.json').read_text())['status']!='PASS':raise ValueError('Stage is not validated')
    files=[p for p in source.rglob('*') if p.is_file()]
    if shutil.disk_usage(out.parent).free < sum(p.stat().st_size for p in files)+20e9:raise ValueError('Insufficient space for verified stage publication')
    for p in source.rglob('*.parquet'):
        if not p.stat().st_size:raise ValueError('Zero-byte stage Parquet')
        pq.ParquetFile(p).metadata
    expected={str(p.relative_to(source)):digest(p) for p in files}
    shutil.copytree(source,pending)
    for rel,sha in expected.items():
        if digest(pending/rel)!=sha:raise ValueError('Stage publication checksum mismatch')
    pending.rename(out)
    for rel,sha in expected.items():
        if digest(out/rel)!=sha:raise ValueError('Published stage changed')
    return len(files)

def run(stage,source,out):
    out=Path(out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists() or out.with_name(out.name+'.publishing').exists():raise FileExistsError(out)
    scratch=Path(tempfile.mkdtemp(prefix='ghsl-'+stage+'-'));record=PROJECT/'phase3/reports'/f'{stage}_publication_{time.time_ns()}.json'
    info=dict(status='RUNNING',stage=stage,scratch=str(scratch),output=str(out));record.write_text(json.dumps(info,indent=2))
    script,flag=STAGES[stage];cmd=[sys.executable,str(PROJECT/script),flag,str(Path(source).resolve()),'--output',str(scratch/'result')]
    update('Execute national '+stage+' in temporary storage','STARTED',f'Publication record: {record.relative_to(PROJECT)}')
    try:
        subprocess.run(cmd,check=True)
        coverage=Path(source)/'coverage.json'
        if coverage.exists():
            scope=json.loads(coverage.read_text());(scratch/'result/coverage.json').write_text(json.dumps(scope,indent=2))
            report_path=scratch/'result/validation.json';report=json.loads(report_path.read_text());report['coverage']=scope;report_path.write_text(json.dumps(report,indent=2))
        count=publish(scratch/'result',out)
        info.update(status='PASS',files_verified=count);record.write_text(json.dumps(info,indent=2));shutil.rmtree(scratch)
        update('Publish national '+stage,'PASS',f'{count} files verified before and after atomic publication.')
    except Exception as exc:
        info.update(status='FAILED',error=str(exc));record.write_text(json.dumps(info,indent=2))
        update('Execute/publish national '+stage,'FAIL',f'{exc}; scratch preserved at {scratch}');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=list(STAGES),required=True);p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.stage,a.input,a.output)
