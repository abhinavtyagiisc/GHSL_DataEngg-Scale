"""Verify a compact GHSL handoff without executing its pipeline."""
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
        required=['population/src/spark_population.py','population/src/multitile_population.py','integration/scripts/download_sources.py','integration/src/prepare_inputs.py','integration/src/spark_integrate.py','phase1/requirements-lock.txt','phase1/runtime/jar_manifest.json']
        if not set(required)<=set(manifest):raise ValueError('Required source/evidence missing')
        # Retain compatibility with source names in the original checksummed handoff.
        for alternatives in (
            {'population/src/prepare_population_rasters.py', 'population/src/prepare.py'},
            {'population/scripts/download_population_tiles.py', 'population/scripts/download.py'},
        ):
            if not alternatives & set(manifest):
                raise ValueError('Required source/evidence missing: ' + ', '.join(sorted(alternatives)))
        # Accept the guide name in existing checksummed archives as well as new handoffs.
        if not {'REPRODUCTION.md', 'SUBMISSION_README.md'} & set(manifest):
            raise ValueError('Reproduction guide missing')
        # Existing checksummed handoffs retain their original folder layout.
        def member(*alternatives):
            for name in alternatives:
                if name in manifest:
                    return name
            raise ValueError('Required source/evidence missing: ' + ', '.join(alternatives))

        report_path=member('analysis/data/final_results/REPORT.md',
                           'analysis/data/week8_handoff/REPORT.md')
        regional_path=member('phase3/reports/regional_validation/validation.json',
                             'phase3/reports/analytical_review/validation.json')
        report=z.read(report_path).decode()
        if 'R8_C27 excluded' not in report:raise ValueError('Missing coverage disclosure')
        if json.loads(z.read(regional_path))['status']!='PASS':raise ValueError('Analytical follow-up failed')
    return dict(status='PASS',archive=str(path),files=len(manifest),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),checks=['ZIP CRC','every entry SHA256','exact manifest membership','safe paths','Python syntax','required source/evidence','coverage disclosure','analytical follow-up PASS'])
if __name__=='__main__':print(json.dumps(verify(sys.argv[1]),indent=2))
