"""Audit successful national stages and build the final compact week-8 handoff."""
import argparse
import csv
import fcntl
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import math
from pathlib import Path
import zipfile
import pyarrow.dataset as ds

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def run(integration,temporal,districts,candidates,out):
    integration,temporal,districts,candidates,out=map(Path,(integration,temporal,districts,candidates,out))
    if out.exists():raise FileExistsError(out)
    for p in (integration,temporal,districts,candidates):
        if not (p/'_SUCCESS').exists() or json.loads((p/'validation.json').read_text())['status']!='PASS':raise ValueError(f'Unfinished stage: {p}')
    evaluation=PROJECT/'analysis/data/regional_case_studies'
    regional=None
    if (PROJECT/'phase2/_SUCCESS').exists():
        if not (evaluation/'_SUCCESS').exists():raise ValueError('Independent regional evaluation incomplete')
        regional=json.loads((evaluation/'validation.json').read_text())
        if regional['status']!='PASS':raise ValueError('Independent regional evaluation failed')
    identity=json.loads((integration/'identity.json').read_text())
    if identity['config']['epochs']!=list(range(1975,2031,5)):
        raise ValueError('Final handoff requires all twelve epochs')
    if not identity['tiles'] or len(set(identity['tiles']))!=len(identity['tiles']):
        raise ValueError('Invalid tile inventory')
    progress=json.loads((integration/'progress.json').read_text())
    expected={(t,y) for t in identity['tiles'] for y in identity['config']['epochs']}
    if {(r['tile'],r['year']) for r in progress}!=expected or len(progress)!=len(expected):raise ValueError('Pair inventory mismatch')
    coverage=identity.get('coverage')
    totals={};raw={};performance=[]
    for record in progress:
        for path,sha in record['files'].items():
            if digest(integration/path)!=sha:raise ValueError('Curated checkpoint hash mismatch')
        for path,sha in record['inputs'].items():
            if path in raw and raw[path]!=sha:raise ValueError('Conflicting source hashes')
            raw[path]=sha
        report=json.loads((integration/'pairs'/f"{record['tile']}_{record['year']}"/'spark_validation.json').read_text())
        if report['status']!='PASS':raise ValueError('Failed pair')
        if report.get('elapsed_seconds',0)>0:
            performance.append(dict(tile=record['tile'],year=record['year'],analytical_rows=report['analytical_rows'],pipeline_seconds=report['elapsed_seconds'],analytical_rows_per_second=report['analytical_rows']/report['elapsed_seconds']))
        year=record['year'];row=totals.setdefault(year,dict(year=year,analytical_rows=0,rejected_rows=0,population=0.,built_surface_m2=0.,built_surface_nres_m2=0.))
        row['analytical_rows']+=report['analytical_rows'];row['rejected_rows']+=report['rejected_rows']
        for summary in report['sql_class_summary']:
            for col in ('population','built_surface_m2','built_surface_nres_m2'):row[col]+=summary[col] or 0
    for path,sha in raw.items():
        if digest(PROJECT/path)!=sha:raise ValueError('Raw archive hash mismatch')
    district_rows=ds.dataset(districts/'district_summary',format='parquet',partitioning='hive').to_table().to_pylist()
    for year in range(1975,2021,5):
        rows=[r for r in district_rows if r['year']==year]
        if sum(r['fine_cells'] for r in rows)!=totals[year]['analytical_rows']:raise ValueError('National district count conservation failed')
        for col in ('population','built_surface_m2','built_surface_nres_m2'):
            if not math.isclose(sum(r[col] for r in rows),totals[year][col],rel_tol=1e-10,abs_tol=1e-4):raise ValueError('National district value conservation failed')
    temporal_report=json.loads((temporal/'validation.json').read_text())
    candidate_report=json.loads((candidates/'validation.json').read_text())
    out.mkdir(parents=True)
    live_status=PROJECT/'phase3/reports/STATUS.json'
    if live_status.exists():
        (out/'execution_status_snapshot.json').write_text(json.dumps(dict(note='Controller status snapshot collected during packaging, before final completion',status=json.loads(live_status.read_text())),indent=2))
    def csv_file(name,rows):
        with (out/name).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    csv_file('national_epoch_totals.csv',list(totals.values()))
    if performance:csv_file('national_pipeline_performance.csv',performance)
    csv_file('district_summary.csv',district_rows)
    concentration=ds.dataset(temporal/'concentration',format='parquet').to_table().to_pylist()
    csv_file('concentration.csv',concentration)
    matrices=[]
    for p in sorted((temporal/'periods').glob('*/transition_matrix')):matrices.extend(ds.dataset(p,format='parquet').to_table().to_pylist())
    csv_file('transition_matrices.csv',matrices)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    years=list(range(1975,2021,5))
    fig,ax=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for codes,label in [([30],'Urban centres'),([21,22,23],'Urban clusters'),([11,12,13],'Rural classes')]:
        for j,col in enumerate(('population_share','built_surface_share')):
            values=[sum(r[col] for r in concentration if r['year']==year and r['settlement_class'] in codes) for year in years]
            ax[j].plot(years,values,marker='o',label=label)
    for a,title in zip(ax,('Population concentration','Built-surface concentration')):
        a.set(title=title,xlabel='Year',ylabel='Share on common valid footprint');a.grid(alpha=.2);a.legend(fontsize=8)
    fig.savefig(out/'national_concentration.png',dpi=180);plt.close(fig)
    lines=['# GHSL weeks 1–8 national handoff','',
           'National integration and historical analysis completed with validated saved outputs.','',
           '## Executed scope','',
           f"{len(identity['tiles'])} tiles; {len(progress)} tile-year jobs; {len(raw)} source archives. All 12 nominal epochs processed. Historical conclusions use 1975–2020 only; 2025/2030 remain projection tests.",'',
           f"Historical comparisons retain {temporal_report['common_complete_cells']:,} coarse cells complete in every historical epoch; {temporal_report['excluded_cells']:,} cells excluded from this common mask.",'',
           '## Results and interpretation','',
           'See the included CSV tables and concentration figure. Epoch totals use complete-case native cells per epoch; temporal results use a fixed common complete coarse footprint. Those totals therefore have different denominators. District summaries retain UNASSIGNED and AMBIGUOUS coverage explicitly and conserve the complete-case national totals.','',
           f"Candidate screening produced {candidate_report['events']:,} overlapping period/component events. These are morphological screening results, not confirmed metropolitan absorption or unique-town counts.",'']
    for status,count in candidate_report['event_counts'].items():lines.append(f'- {status}: {count:,}')
    lines+=['','Sensitivity results and representative-cell GeoJSON are included. Review shortlisted cases against independent administrative/local evidence before treating them as confirmed settlements.','',
            '## Engineering and validation','',
            'Windowed local raster extraction and native 100 m retention; Spark local[2] validation, joins and aggregation per tile-year. Spark SQL computes transitions and district summaries. Per-pair source and curated hashes, schemas, keys, coverage, conservation and Parquet round trips were verified; this final audit rechecked every checkpoint hash and national district count/value conservation.','',
            'Official JRC downloads replace the proposed Earth Engine exports. The completed pilot used real single-node HDFS; national runs retain local partitioned Parquet to avoid duplicate national storage. This is not a multi-machine benchmark or national HDFS-storage claim.','',
            'Country mask: geoBoundaries IND ADM0 represented year 2014. District mask: geoBoundaries IND ADM2 represented year 2021, 735 actual features. These are reproducible study geometries, not official Indian administrative boundaries or reconstructed historical districts.','',
            'Sources: European Commission Joint Research Centre GHSL R2023A POP/BUILT-S V1_0 and SMOD V2_0. geoBoundaries gbOpen, Pathways Data Pvt. Ltd., lgdirectory.gov.in; ODbL 1.0: https://opendatacommons.org/licenses/odbl/1-0/. Preserve source attribution and derived-database license obligations when sharing.','',
            '## Data locations','',f'- National native/summary partitions: `{integration}`',f'- Historical common-mask and cell transitions: `{temporal}`',f'- District summaries: `{districts}`',f'- Candidate events and review GeoJSON: `{candidates}`','',
            'The compact ZIP contains summaries, methods, provenance and execution evidence. Multi-gigabyte native cell datasets remain at the listed workspace paths; it is not a self-contained copy of all national data.','']
    if regional:
        lines+=['## Independent regional data checks','',
                f"Direct raw-raster comparisons covered {regional['coarse_cell_years']:,} complete coarse cell-years across three urban study windows and ten historical epochs. The Mumbai window was relocated by a documented coverage-only rule after the original window fell outside the retained country mask; Delhi and Bengaluru retain their original centres. Population and both built-area sums plus matching-year settlement classes agreed within the declared tolerances. See regional_case_studies/region_summary.csv and validation.json. This is numerical processing accuracy on a predefined sample, not precision/recall against independently labelled settlement-growth events.",'']
    if performance:
        seconds=sum(r['pipeline_seconds'] for r in performance)
        lines+=['## Observed national pipeline performance','',
                f"{len(performance)} recorded tile-year pipeline timings total {seconds:,.2f} seconds; summed analytical rows divided by these timings gives {sum(r['analytical_rows'] for r in performance)/seconds:,.0f} rows/s. Each is one observation, including Spark startup/validation/write, excluding preceding source acquisition and raster preparation. This is not total project wall time or a repeated national scaling experiment. Per-pair values are in national_pipeline_performance.csv.",'']
    if (PROJECT/'phase2/_SUCCESS').exists():
        phase2=json.loads((PROJECT/'phase2/reports/HANDOFF_VALIDATION.json').read_text())
        if phase2['status']!='PASS':raise ValueError('Phase-2 acceptance invalid')
        lines+=['## Geospatial engine and quantitative evaluation','',
                'The revised weeks 1–5 foundation additionally executed Apache Sedona 1.9.1 spatial joins and independently validated all-product pilot outputs. The phase-2 completion report and raw benchmark evidence are included. Its repeated end-to-end metrics describe local pilot execution; they must not be interpreted as national or multi-machine timings. National district attribution uses the separately validated raster-centre method described in its own validation report.','']
    if coverage:
        lines[2]=coverage['warning']
        lines[3:3]=['', '## Study coverage and exclusions', '', coverage['policy'], '', f"Accepted: {len(progress)} of {coverage['original_planned_pairs']} originally planned jobs. Excluded: R8_C27, all 12 epochs, after fresh-source retries still had no valid analytical cells.", '']
        (out/'coverage.json').write_text(json.dumps(coverage,indent=2))
    (out/'REPORT.md').write_text('\n'.join(lines))
    audit=dict(status='PASS',pairs=len(progress),raw_archives=len(raw),epoch_totals=list(totals.values()),
               common_complete_cells=temporal_report['common_complete_cells'],district_conservation='PASS',all_checkpoint_hashes='PASS')
    if coverage:audit['coverage']=coverage
    (out/'validation.json').write_text(json.dumps(audit,indent=2)+'\n')
    files=list(out.glob('*'))
    if regional:files.extend(p for p in evaluation.iterdir() if p.is_file())
    for folder in (ROOT/'src',ROOT/'tests',ROOT/'scripts',PROJECT/'integration/src',PROJECT/'integration/config'):
        files.extend(p for p in folder.glob('*') if p.is_file() and p.suffix in ('.py','.json'))
    files.extend([p/'validation.json' for p in (integration,temporal,districts,candidates)])
    files.extend(candidates/name for name in ('component_events.csv','component_events.parquet','candidate_review.geojson'))
    files.extend(ROOT/'data/boundaries'/name for name in ('IND_ADM2.provenance.json',))
    files.extend([PROJECT/'integration/README.md',integration/'identity.json',integration/'progress.json'])
    if (PROJECT/'phase2/_SUCCESS').exists():
        for relative in ['phase2/src','phase2/scripts','phase2/config','phase2/reports','phase3/scripts','phase3/reports','phase3/config','phase3/tests']:
            folder=PROJECT/relative
            files.extend(p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts
                         and p.suffix in ('.py','.json','.md','.csv','.png') and 'events' not in p.parts
                         and p != PROJECT/'phase3/reports/STATUS.json')
        files.extend([PROJECT/'phase2/README.md',PROJECT/'phase3/README.md'])
    files=list(dict.fromkeys(files))
    archive=PROJECT/'GHSL_Weeks1_8_National_Handoff.zip'
    manifest={str(p.relative_to(PROJECT)):digest(p) for p in files}
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(PROJECT))
        z.writestr('SHA256.json',json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('ZIP CRC failed')
        for path,sha in manifest.items():
            if hashlib.sha256(z.read(path)).hexdigest()!=sha:raise ValueError('ZIP SHA256 failed')
    (out/'_SUCCESS').write_text('PASS\n')
    # Replace the interim completion report only after every final audit passes.
    # A distinct heading prevents the live heartbeat from restoring an in-progress notice.
    progress_report=ROOT/'reports/PROGRESS_REPORT.md'
    if progress_report.exists():
        with (ROOT/'reports/progress_report.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            final_text=('### Final automated validation status\n\nUpdated: '+datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()+'\n\n'
                        'All processing and analytical stages for the declared accepted coverage passed automated validation. '
                        'Final visual review of national figures remains to be recorded separately.\n\n'+(out/'REPORT.md').read_text())
            tmp=progress_report.with_suffix('.md.tmp');tmp.write_text(final_text);tmp.replace(progress_report)
    print(json.dumps(dict(status='PASS',archive=str(archive),bytes=archive.stat().st_size)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--integration',required=True);p.add_argument('--temporal',required=True)
    p.add_argument('--districts',required=True);p.add_argument('--candidates',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();run(a.integration,a.temporal,a.districts,a.candidates,a.output)
