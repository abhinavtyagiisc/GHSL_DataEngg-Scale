"""Publish a separately audited view of explicitly accepted geographic coverage."""
import fcntl,hashlib,json,os,sys
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'analysis/scripts'))
from progress_log import update

def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def inventory(identity,progress,excluded):
    tiles=[t for t in identity['tiles'] if t not in excluded]
    expected={(t,y) for t in tiles for y in identity['config']['epochs']}
    actual=[(r['tile'],r['year']) for r in progress]
    if not tiles or set(actual)!=expected or len(actual)!=len(expected):
        raise ValueError('Accepted scope lacks exact verified pair inventory')
    return tiles

def main():
    source=PROJECT/'integration/data/national_run1';out=PROJECT/'integration/data/accepted_coverage_run1'
    if (out/'_SUCCESS').exists():return
    with (source/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        original=json.loads((source/'identity.json').read_text());progress=json.loads((source/'progress.json').read_text())
        tiles=inventory(original,progress,['R8_C27'])
        deferred=json.loads((source/'deferred.json').read_text())
        if {(d['tile'],d['year']) for d in deferred if d['status']=='UNRESOLVED' and d.get('refreshed_sources')}!={('R8_C27',y) for y in original['config']['epochs']}:
            raise ValueError('Exclusion evidence differs from approved scope')
        checked=set()
        for i,r in enumerate(progress,1):
            pair=source/'pairs'/f"{r['tile']}_{r['year']}"
            if not (pair/'curated/_INTEGRATION_SUCCESS').exists():raise ValueError('Pair lacks success')
            if json.loads((pair/'spark_validation.json').read_text())['status']!='PASS':raise ValueError('Pair failed')
            for rel,sha in r['files'].items():
                if digest(source/rel)!=sha:raise ValueError('Completed output changed: '+rel)
            for rel,sha in r['inputs'].items():
                if (rel,sha) not in checked:
                    if digest(PROJECT/rel)!=sha:raise ValueError('Source changed: '+rel)
                    checked.add((rel,sha))
            if i%12==0:update('Audit accepted coverage','RUNNING',f'{i}/{len(progress)} saved checkpoints rechecked; no data recomputed.')
        if out.exists():raise FileExistsError(out)
        out.mkdir();(out/'pairs').mkdir()
        for r in progress:
            name=f"{r['tile']}_{r['year']}";(out/'pairs'/name).symlink_to(os.path.relpath(source/'pairs'/name,out/'pairs'),target_is_directory=True)
        coverage=dict(authorization_date='2026-11-10',policy='User-approved completion using verified coverage; excluded area is missing, never zero or extrapolated',original_planned_pairs=len(original['tiles'])*len(original['config']['epochs']),accepted_pairs=len(progress),excluded_tiles=['R8_C27'],excluded_pairs=deferred,source_run=str(source),warning='R8_C27 excluded in all 12 epochs. Results describe the verified study footprint, not complete India coverage.')
        identity=dict(original);identity['tiles']=tiles;identity['coverage']=coverage
        for name,value in [('identity',identity),('progress',progress),('coverage',coverage),('original_identity',original),('validation',dict(status='PASS',scope='user-approved verified coverage excluding R8_C27',tile_years=len(progress),all_checkpoint_hashes='PASS',coverage=coverage))]:
            (out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
        (out/'_SUCCESS').write_text('PASS for accepted coverage only\n')
        update('Accept verified coverage','PASS',f'{len(progress)} pairs rehashed; R8_C27 explicitly excluded. Original national run unchanged.')
if __name__=='__main__':main()
