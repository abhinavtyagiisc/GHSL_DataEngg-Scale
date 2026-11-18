"""Verify a compact GHSL submission without executing its pipeline."""
import ast,hashlib,json,sys,zipfile
from pathlib import Path,PurePosixPath

def verify(path):
    path=Path(path)
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):raise ValueError('Duplicate ZIP entries')
        if z.testzip() is not None:raise ValueError('ZIP CRC failed')
        manifest=json.loads(z.read('SHA256.json'))
        if set(names)!=set(manifest)|{'SHA256.json'}:raise ValueError('Manifest membership differs')
        for name,sha in manifest.items():
            if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts:raise ValueError('Unsafe archive path')
            data=z.read(name)
            if hashlib.sha256(data).hexdigest()!=sha:raise ValueError('SHA256 mismatch: '+name)
            if name.endswith('.py'):ast.parse(data,filename=name)
        required=['population/src/prepare.py','population/src/spark_population.py','population/src/multitile_population.py','population/scripts/download.py','integration/scripts/download_sources.py','integration/src/prepare_inputs.py','integration/src/spark_integrate.py','phase1/requirements-lock.txt','phase1/runtime/jar_manifest.json','phase3/reports/analytical_review/validation.json','phase3/reports/REQUIREMENTS_REVIEW.md','SUBMISSION_README.md']
        if not set(required)<=set(manifest):raise ValueError('Required source/evidence missing')
        report=z.read('analysis/data/week8_handoff/REPORT.md').decode()
        if 'R8_C27 excluded' not in report:raise ValueError('Missing coverage disclosure')
        if json.loads(z.read('phase3/reports/analytical_review/validation.json'))['status']!='PASS':raise ValueError('Analytical follow-up failed')
    return dict(status='PASS',archive=str(path),files=len(manifest),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),checks=['ZIP CRC','every entry SHA256','exact manifest membership','safe paths','Python syntax','required source/evidence','coverage disclosure','analytical follow-up PASS'])
if __name__=='__main__':print(json.dumps(verify(sys.argv[1]),indent=2))
