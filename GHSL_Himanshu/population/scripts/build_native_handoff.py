"""Package the verified native pilot, code and India plan without raw tile archives."""
import argparse
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'Population_100m_Handoff.zip')
    args=parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    run=ROOT/'data/curated/bengaluru_100m_final'
    assert (run/'_SUCCESS').exists()
    for name in ('validation.json','spark_validation.json'):
        assert json.loads((run/name).read_text())['status']=='PASS'
    include=[ROOT/name for name in ('README.md','NATIVE_100M_HANDOFF.md','TEAM_HANDOFF.md','requirements.txt','requirements-lock.txt')]
    for folder in ('config','src','scripts','tests','data/raw/boundaries'):
        include.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    include.extend(ROOT/'reports'/name for name in ('NATIVE_100M_EXECUTION.md','tests_100m_final.txt','india_source_plan.json','india_source_availability.json'))
    include.extend(p for p in run.rglob('*') if p.is_file() and not p.name.startswith('.'))
    with zipfile.ZipFile(args.output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(include)):
            archive.write(path,'population/'+str(path.relative_to(ROOT)))
    with zipfile.ZipFile(args.output) as archive:
        if archive.testzip():
            raise ValueError('Handoff archive integrity failure')
    print(f'{args.output}: {args.output.stat().st_size:,} bytes; ZIP integrity PASS')


if __name__=='__main__':
    main()
