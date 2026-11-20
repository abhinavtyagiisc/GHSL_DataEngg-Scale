"""Verify the retrieved dataset, write completion evidence, and build the team package."""
import contextlib
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import zipfile

import numpy as np
import pyarrow.dataset as ds

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent


def verify_download(report):
    path=ROOT/'data/curated/grid_year'
    if not (path/'_INTEGRATION_SUCCESS').exists():raise ValueError('Final integration marker missing')
    dataset=ds.dataset(path/'analytical_100m',format='parquet',partitioning='hive')
    rows=[]
    for epoch in report['epochs']:
        year=epoch['year'];count=0;totals={name:0.0 for name in ('population','built_surface_m2','built_surface_nres_m2')}
        scanner=dataset.scanner(filter=ds.field('year')==year,columns=[*totals,'settlement_class','is_valid'])
        for batch in scanner.to_batches():
            count+=len(batch)
            for name in totals:
                column=batch.column(batch.schema.get_field_index(name))
                if column.null_count:raise ValueError('Null analytical value after HDFS retrieval')
                totals[name]+=float(np.asarray(column).sum(dtype='float64'))
            if batch.column(batch.schema.get_field_index('settlement_class')).null_count:raise ValueError('Missing settlement class')
            if not np.asarray(batch.column(batch.schema.get_field_index('is_valid'))).all():raise ValueError('Invalid analytical row')
        if count!=epoch['valid_rows']:raise ValueError('Downloaded row count changed')
        for name,total in totals.items():
            if not math.isclose(total,epoch[name],rel_tol=1e-10,abs_tol=1e-5):raise ValueError('Downloaded total changed')
        rows.append(dict(year=year,rows=count,**totals))
    if ds.dataset(path/'summary_1km',format='parquet',partitioning='hive').count_rows()!=report['coarse_rows']:
        raise ValueError('Downloaded coarse row count changed')
    hashes={str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob('*.parquet')}
    result=dict(status='PASS',epochs=rows,parquet_sha256=hashes)
    (ROOT/'reports/download_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    return rows


def notebook():
    cells=[]
    def md(text):cells.append(dict(cell_type='markdown',metadata={},source=text.splitlines(keepends=True)))
    def code(text):cells.append(dict(cell_type='code',metadata={},source=text.splitlines(keepends=True),execution_count=None,outputs=[]))
    md('''# GHSL weeks 1–5: completed three-product pilot

Population, built-up surface (total/NRES), and matching-year settlement classes.
The pipeline ran on local HDFS with Spark. These read-only notebook code cells were
executed by the package builder in Python; this is not a Colab or Jupyter-kernel run.
All ten historical epochs plus 2025/2030 projection tests are included.

The area is the Bengaluru test rectangle, not the municipal boundary. National
processing and settlement-change analysis belong to weeks 6–8.''')
    code('''from pathlib import Path
import json
here = Path.cwd().resolve()
ROOT = next(p / 'integration' for p in [here, *here.parents] if (p / 'integration/config/pilot.json').exists())
cfg = json.loads((ROOT / 'config/pilot.json').read_text())
print(cfg['name'], cfg['bbox_wgs84'], cfg['epochs'])''')
    md('## 1. Executed validation evidence')
    code('''report = json.loads((ROOT / 'reports/spark_hdfs_validation.json').read_text())
print(report['status'], report['spark_version'], report['master'])
print('Analytical rows:', report['analytical_rows'])
print('Coarse rows:', report['coarse_rows'])
print('Rejected rows:', report['rejected_rows'])
print('Incomplete trajectories:', report['incomplete_trajectories'])
print('Checks:', ', '.join(report['checks']))''')
    md('## 2. Read the partitioned three-product handoff')
    code('''import pyarrow.dataset as ds
path = ROOT / 'data/curated/grid_year'
assert (path / '_INTEGRATION_SUCCESS').exists()
dataset = ds.dataset(path / 'analytical_100m', format='parquet', partitioning='hive')
print(dataset.schema)
sample = dataset.scanner(filter=ds.field('year') == 2020,
    columns=['cell_id', 'parent_cell_id', 'year', 'population', 'built_surface_m2',
             'built_surface_nres_m2', 'settlement_class']).head(5)
for row in sample.to_pylist(): print(row)''')
    md('## 3. Saved Spark SQL summary for 2020')
    code('''summary = ds.dataset(path / 'sql_class_summary', format='parquet').to_table()
for row in summary.to_pylist():
    if row['year'] == 2020: print(row)''')
    md('''## 4. Reproduce a fresh Spark run

Run from the project root with the documented `.venv`. Never overwrite delivered data.

```sh
.venv/bin/python integration/src/spark_integrate.py \\
  --input integration/data/prepared/tables \\
  --output integration/data/curated/notebook_rerun_1 \\
  --report integration/reports/notebook_rerun_1.json
```

Prepared inputs and raw raster archives are retained in the development workspace.
They are excluded from the compact handoff ZIP; reproduce them with the download and
preparation scripts before rerunning from the ZIP. Read `integration/README.md` for
HDFS commands, source citations, NoData semantics and scope limitations.''')
    namespace={};counter=0
    for index,cell in enumerate(cells):
        cell['id']=f'ghsl-integration-{index:02d}'
        if cell['cell_type']=='code':
            counter+=1;stream=io.StringIO()
            with contextlib.redirect_stdout(stream):exec(compile(''.join(cell['source']),f'notebook-cell-{counter}','exec'),namespace)
            cell['execution_count']=counter
            cell['outputs']=[dict(output_type='stream',name='stdout',text=stream.getvalue().splitlines(keepends=True))]
    doc=dict(cells=cells,nbformat=4,nbformat_minor=5,
        metadata={'kernelspec':{'display_name':'Python 3 (GHSL)','language':'python','name':'python3'},
                  'language_info':{'name':'python','version':sys.version.split()[0]},
                  'execution_note':'Code cells executed by build_handoff.py with Python exec, not a Jupyter kernel'})
    folder=ROOT/'notebooks';folder.mkdir(exist_ok=True)
    (folder/'GHSL_Weeks_1_to_5_Complete.ipynb').write_text(json.dumps(doc,indent=2)+'\n')


def main():
    report=json.loads((ROOT/'reports/spark_hdfs_validation.json').read_text())
    hdfs=json.loads((ROOT/'reports/hdfs_execution.json').read_text())
    assert report['status']==hdfs['status']=='PASS'
    assert report['rejected_rows']==0 and report['incomplete_trajectories']==0
    assert '5 passed' in (ROOT/'reports/tests.txt').read_text()
    assert '2 passed' in (ROOT/'reports/raster_alignment_tests.txt').read_text()
    manifest=json.loads((ROOT/'reports/download_manifest_full.json').read_text())
    assert len(manifest)==48
    (ROOT/'reports/raster_validation.json').write_text((ROOT/'data/prepared/raster_validation.json').read_text())
    rows=verify_download(report)
    with (ROOT/'reports/epoch_summary.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    body=f'''# Weeks 1–5 completion report

Date: 2026-11-06 (Asia/Kolkata).

**Status: the three-product Bengaluru pilot milestones are complete, with the
explicit JRC-download substitution for the proposal's Earth Engine export step.**

## Proposal milestone checklist

| Requirement | Executed evidence |
|---|---|
| Weeks 1–3: acquire all three historical products for the pilot | 48 verified ZIPs: 12 POP, 12 SMOD, 12 total built-up, 12 NRES; includes ten historical and two test epochs |
| Validate CRS, resolution, grid alignment and values | `data/prepared/raster_validation.json`; exact shared crop, source-specific NoData, valid classes and area/count bounds |
| Establish raw/cleaned/curated HDFS zones | `/ghsl/weeks1_5/bengaluru_run1/`; staged actual archives, clipped GeoTIFFs and independent tables |
| Confirm 100 m ↔ 1 km integration | Native values retained, integer parent-grid mapping, matching-year settlement inheritance; companion coarse sums conserve values |
| Weeks 4–5: Spark ingestion and validation | Spark {report['spark_version']} reads all three independent tables from HDFS; schemas, epoch completeness, unique keys, value and coverage checks pass |
| Join all three products | {report['analytical_rows']:,} complete analytical 100 m cell-year rows; no missing required field |
| Aggregate and query | {report['coarse_rows']:,} 1 km summaries plus Spark SQL summaries by year and settlement category |
| Store partitioned Parquet | Historical/projection and year partitions in HDFS, retrieved local copy, complete every-column round-trip comparison |
| Reusable Spark pipeline | `src/spark_integrate.py` accepts local/HDFS inputs and new output/report paths |

## Measured execution

- Pilot: 77.3–77.9 E, 12.7–13.3 N; inside the retained India mask, not a municipal boundary.
- Products: POP V1_0, BUILT-S total/NRES V1_0 and SMOD V2_0, all R2023A.
- Source archive bytes: {sum(m['bytes'] for m in manifest):,}; ZIP CRCs and SHA256 recorded.
- 48 clipped GeoTIFFs and 36 independent staging Parquet files retained.
- 434,363 fine cells and 4,455 parent cells per epoch, across all 12 epochs.
- Complete analytical records: {report['analytical_rows']:,}; rejected records: {report['rejected_rows']}.
- Incomplete cell trajectories: {report['incomplete_trajectories']}.
- Spark execution/validation time: {report['elapsed_seconds']} seconds ({report['master']}).
- HDFS orchestration time, including staging/retrieval: {hdfs['elapsed_seconds']} seconds.
- **Seven new integration regressions passed** in two runs: five Spark/data tests,
  then two cropped-grid/misalignment tests. Existing population tests were not rerun
  because the population implementation was unchanged in this task.
- HDFS health: HEALTHY, one live DataNode, replication one. Services stopped afterward.
- Retrieved Parquet row counts, non-null fields, flags and per-epoch totals verified;
  local file SHA256 values recorded in `download_verification.json`.

Exact native raster origins were checked. The built-up tile has a cropped native
extent (9,000 columns), unlike the population tile (10,000); their actual pixel grids
align. This is handled by coordinate-based windows, not array-shape assumptions.

## Epoch summary for the pilot rectangle

| Year | Type | Population estimate | Built-up m² | Non-residential built-up m² | Complete fine rows |
|---|---|---:|---:|---:|---:|
'''
    for r in rows:
        body+=f"| {r['year']} | {'historical' if r['year']<=2020 else 'projection/test'} | {r['population']:,.3f} | {r['built_surface_m2']:,.0f} | {r['built_surface_nres_m2']:,.0f} | {r['rows']:,} |\n"
    body+='''
## Scientific scope and deviations

Native 100 m population and built-up values are retained. Settlement categories are
inherited from their matching-year 1 km parent, not independently estimated at 100 m.
NoData is never converted to zero; incomplete records are excluded and audited.
Valid category 10 (water) is retained and can be explicitly filtered for land analyses.
Boundary coarse cells contain only included fine-cell centres; totals are not rescaled.
The pilot rectangle's totals must not be presented as Bengaluru municipal totals.

Official JRC downloads replace GEE exports; no Earth Engine or Colab run is claimed.
Raster decoding is local, while validation/join/aggregation/storage use Spark with
real single-node HDFS. This is not a national or multi-machine scalability benchmark.
The read-only notebook cells were executed by the Python package builder, not by a
Jupyter kernel. It provides a reproducible walkthrough of actual saved outputs.

**Weeks 6–8 remain:** national execution, historical settlement transitions,
district-level summaries, metropolitan absorption and independent-growth analysis.
The existing national population-only plan does not yet constitute a nationwide
three-product run. No nationwide results are claimed.

## Deliverables

- `data/curated/grid_year/`: HDFS-retrieved analytical, coarse and SQL-summary Parquet.
- `reports/`: source, raster/Spark/HDFS, tests and retrieved-output evidence.
- `notebooks/GHSL_Weeks_1_to_5_Complete.ipynb`: executed read-only walkthrough.
- `GHSL_Weeks1_5_Complete_Handoff.zip` at the project root: code, source/configuration
  contracts, notebook, evidence and curated data. Raw/prepared data and runtimes are
  excluded from the compact archive but remain in the workspace and HDFS.

Source documentation and attribution are linked in `integration/README.md`.
'''
    (ROOT/'reports/COMPLETION_REPORT.md').write_text(body)
    notebook()
    destination=PROJECT/'GHSL_Weeks1_5_Complete_Handoff.zip'
    if destination.exists():raise FileExistsError(destination)
    include=[PROJECT/n for n in ('README.md','REPRODUCTION.md')]
    include.append(ROOT/'README.md')
    for folder in ('config','src','scripts','tests','notebooks'):
        include.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    include.extend(p for p in (ROOT/'reports').iterdir() if p.suffix in ('.md','.json','.csv','.txt'))
    include.extend(p for p in (ROOT/'data/curated/grid_year').rglob('*') if p.is_file() and not p.name.startswith('.'))
    for name in ('requirements.txt','requirements-lock.txt','src/prepare_population_rasters.py','src/multitile_population.py',
                 'src/spark_population.py','scripts/download_population_tiles.py','scripts/hdfs.py','scripts/bootstrap_hdfs.py',
                 'config/hdfs-pom.xml','data/raw/boundaries/geoBoundaries-IND-ADM0.geojson',
                 'data/raw/boundaries/geoBoundaries-IND-ADM0.provenance.json'):
        include.append(PROJECT/'population'/name)
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(include)):archive.write(path,str(path.relative_to(PROJECT)))
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip():raise ValueError('Package CRC failure')
    print(f'Completion report, notebook and {destination.name} verified ({destination.stat().st_size:,} bytes).')


if __name__=='__main__':main()
