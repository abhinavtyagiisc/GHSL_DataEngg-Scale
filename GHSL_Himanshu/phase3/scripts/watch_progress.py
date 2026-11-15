"""Show active national work without altering processing or completion checkpoints."""
from datetime import datetime
from zoneinfo import ZoneInfo
import fcntl,json,re,time
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[2];REPORTS=PROJECT/'analysis/reports'
import sys
sys.path.insert(0,str(REPORTS.parent/'scripts'));from progress_log import update

def snapshot():
    root=PROJECT/'integration/data/national_run1'
    records=json.loads((root/'progress.json').read_text())
    identity=json.loads((root/'identity.json').read_text())
    status=json.loads((PROJECT/'phase3/reports/STATUS.json').read_text())
    done={(r['tile'],r['year']) for r in records};names={f'{t}_{y}' for t,y in done}
    pending=[p for p in (root/'pairs').iterdir() if p.is_dir() and p.name not in names]
    current='Waiting for next validated stage.'
    if status['status']=='RUNNING' and pending:
        pair=max(pending,key=lambda p:p.stat().st_mtime)
        step='acquiring and checking source archives'
        if (pair/'sources.json').exists():step='preparing aligned native grids'
        if (pair/'prepared/_SUCCESS').exists():step='Spark integration, validation and output publication'
        if (pair/'curated/_INTEGRATION_SUCCESS').exists():step='checking published files before recording the checkpoint'
        current=f'{pair.name}: {step}.'
        stats=pair/'prepared/raster_validation.json'
        if stats.exists():current+=f" Input: {json.loads(stats.read_text())['epochs'][0]['fine_rows']:,} native cells."
    elif status['status']!='RUNNING':current=f"Controller state: {status['status']}. Inspect its recorded status before restarting."
    elif (root/'_SUCCESS').exists():
        stage=json.loads((REPORTS/'WEEK8_RUN_STATUS.json').read_text()).get('stage','analysis')
        current=f'National integration complete; current stage: {stage}.'
    stamp=datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()
    lines=['### Active execution detail','',f'Updated: {stamp}', '',current,'',
           'A tile-year counts as completed only after validation and verified publication.','',
           '| Tile | Verified years | Completed / planned |','|---|---|---|']
    for tile in identity['tiles']:
        years=[y for y in identity['config']['epochs'] if (tile,y) in done]
        lines.append(f"| {tile} | {', '.join(map(str,years)) or 'Pending'} | {len(years)} / {len(identity['config']['epochs'])} |")
    return '\n'.join(lines)+'\n\n',status

def refresh():
    section,status=snapshot()
    with (REPORTS/'progress_report.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        p=REPORTS/'PROGRESS_REPORT.md';text=p.read_text()
        if '### 1. Overall status' not in text:return False
        if '### Active execution detail' in text:
            text=re.sub(r'### Active execution detail\n.*?(?=### |\Z)',lambda m:section,text,flags=re.S)
        else:text=text.replace('### Existing work that can be reused',section+'### Existing work that can be reused',1)
        tmp=p.with_suffix('.md.tmp');tmp.write_text(text);tmp.replace(p)
    return status['status'] in ('RUNNING','WAITING_NETWORK_RETRY')

if __name__=='__main__':
    with (PROJECT/'phase3/reports/progress_watcher.lock').open('a') as ownership:
        fcntl.flock(ownership,fcntl.LOCK_EX|fcntl.LOCK_NB)
        update('Start active-job progress display','STARTED','Reports active tile/year, processing step and per-tile completion every 30 seconds. It does not launch or change computation.')
        while refresh():time.sleep(30)
        update('Active-job progress display','STOPPED','Controller stopped or final automated report replaced interim progress. Inspect execution status for the outcome.')
