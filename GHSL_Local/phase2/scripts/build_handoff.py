"""Require all phase-2 gates, package results and verify every archive entry."""
from pathlib import Path
import hashlib,json,zipfile
PROJECT=Path(__file__).resolve().parents[2];ROOT=PROJECT/'phase2'
import sys
sys.path.insert(0,str(PROJECT/'analysis/scripts'));from progress_log import update

def main():
    for name in ['hdfs_validation.json','hdfs_execution.json','reference_comparison.json']:
        if json.loads((ROOT/'reports'/name).read_text())['status']!='PASS':raise ValueError(name)
    cfg=json.loads((ROOT/'config/benchmark.json').read_text())
    for mode,w,p in cfg['scenarios']:
        folder=ROOT/f'reports/benchmarks/{mode}_w{w}_p{p}'
        result=json.loads((folder/'validation.json').read_text())
        if result['status']!='PASS' or not (folder/'_SUCCESS').exists():raise ValueError(str(folder))
    if '3 passed' not in (ROOT/'reports/tests_run1.txt').read_text():raise ValueError('Tests not passed')
    if not (ROOT/'data/grid_year/_INTEGRATION_SUCCESS').exists():raise ValueError('Integration marker missing')
    files=set()
    for relative in ['phase2','integration/src','population/src','analysis/src']:
        for p in (PROJECT/relative).rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts or '.pytest_cache' in p.parts:continue
            if relative=='phase2' and ('data/benchmarks' in str(p.relative_to(ROOT)) or p.name in ['MANIFEST.json','HANDOFF_VALIDATION.json'] or p==ROOT/'_SUCCESS'):continue
            files.add(p)
    for rel in ['SUBMISSION_README.md','phase1/README.md','phase1/config/benchmark.json','phase1/runtime/jar_manifest.json','phase1/requirements-lock.txt','phase1/src/sedona_benchmark.py','phase1/scripts/bootstrap_sedona.py','population/scripts/hdfs.py','analysis/scripts/progress_log.py','integration/config/grid_contract.json','integration/config/pilot.json']:
        files.add(PROJECT/rel)
    manifest=[]
    for p in sorted(files):
        with p.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
        manifest.append(dict(path=str(p.relative_to(PROJECT)),bytes=p.stat().st_size,sha256=sha))
    (ROOT/'reports/MANIFEST.json').write_text(json.dumps(manifest,indent=2))
    archive=PROJECT/'GHSL_Phase2_Weeks4_5_Handoff_v2.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for r in manifest:z.write(PROJECT/r['path'],r['path'])
        z.write(ROOT/'reports/MANIFEST.json','phase2/reports/MANIFEST.json')
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('CRC failed')
        for r in manifest:
            if hashlib.sha256(z.read(r['path'])).hexdigest()!=r['sha256']:raise ValueError('Archive hash mismatch')
    result=dict(status='PASS',archive=str(archive.relative_to(PROJECT)),files=len(manifest)+1,bytes=archive.stat().st_size,checks=['all phase-2 execution gates','ZIP CRC','every entry SHA256'])
    (ROOT/'reports/HANDOFF_VALIDATION.json').write_text(json.dumps(result,indent=2));(ROOT/'_SUCCESS').write_text('PASS\n')
    update('Build and verify phase-2 handoff archive','PASS',json.dumps(result));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
