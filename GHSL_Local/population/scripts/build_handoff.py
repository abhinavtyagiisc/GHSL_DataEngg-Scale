"""Generate human-readable evidence, notebook walkthrough and a compact team ZIP."""
import csv
from datetime import datetime
import json
from pathlib import Path
import zipfile
from zoneinfo import ZoneInfo
import numpy as np
import pyarrow.dataset as ds

ROOT=Path(__file__).resolve().parents[1]

def main():
    local=json.loads((ROOT/'reports/spark_validation.json').read_text())
    hdfs=json.loads((ROOT/'reports/spark_hdfs_validation.json').read_text())
    rasters=json.loads((ROOT/'reports/raster_validation.json').read_text())
    manifest=json.loads((ROOT/'reports/download_manifest.json').read_text())
    assert local['status']==hdfs['status']=='PASS'
    assert local['input_rows']==hdfs['input_rows'] and local['output_rows']==hdfs['output_rows']
    assert all(r['nodata_pixels']==0 for r in rasters)
    assert '5 passed' in (ROOT/'reports/tests.txt').read_text()
    assert 'HEALTHY' in (ROOT/'reports/hdfs_fsck.txt').read_text()
    years=hdfs['epochs']
    with (ROOT/'reports/epoch_summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(years[0]))
        w.writeheader();w.writerows(years)
    data=ds.dataset(ROOT/'data/curated/population_1km',format='parquet',partitioning='hive')
    table=data.to_table().sort_by([('year','ascending'),('grid_row','ascending'),('grid_col','ascending')])
    downloaded=ds.dataset(ROOT/'data/curated/population_1km_from_hdfs',format='parquet',partitioning='hive')
    other=downloaded.to_table().select(table.column_names).sort_by([('year','ascending'),('grid_row','ascending'),('grid_col','ascending')])
    if not table.drop(['population']).equals(other.drop(['population'])):
        raise ValueError('Local and HDFS metadata or coverage differ')
    np.testing.assert_allclose(table['population'].to_numpy(),other['population'].to_numpy(),rtol=1e-12,atol=1e-8,equal_nan=True)
    with (ROOT/'reports/population_sample.csv').open('w',newline='') as f:
        rows=table.slice(0,20).to_pylist()
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    maximum=max(r['absolute_difference'] for r in years)
    body=f'''# Population weeks 1–5: execution report

Generated {datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(timespec='seconds')}.

**Status: population-only Bengaluru pilot executed successfully. No Colab required.**

## Scope and milestone evidence

- Official GHS-POP R2023A V1_0, 100 m, ESRI:54009.
- 10 historical epochs (1975–2020) and 2 projection test epochs (2025, 2030).
- Bengaluru test rectangle: 77.3–77.9°E, 12.7–13.3°N; not an administrative city boundary.
- 13 official source ZIPs (12 population + one SMOD grid reference), {sum(r['bytes'] for r in manifest):,} bytes. ZIP CRCs checked; SHA256 provenance in `download_manifest.json`.
- {rasters[0]['inside_pixels']:,} in-pilot 100 m cells per epoch; no NoData cells inside this pilot.
- {hdfs['input_rows']:,} input cell-year records processed using Spark {hdfs['spark_version']}.
- {years[0]['cells']:,} 1 km cells per epoch; {hdfs['output_rows']:,} output grid-year records.
- {years[0]['boundary_cells']} partial-AOI boundary cells per epoch, explicitly flagged by `aoi_fraction`.
- Maximum absolute source-to-output population difference: {maximum:.12g} persons (floating-point summation only).
- Local Spark run: {local['elapsed_seconds']} seconds. HDFS Spark run: {hdfs['elapsed_seconds']} seconds. These are single-run local measurements, not scalability benchmarks.
- Five regression tests passed: exact alignment, half-pixel shift rejection, CRS mismatch rejection, wrong-resolution rejection, and aggregation semantics (sum/null/zero/boundary/epoch isolation).
- Genuine local HDFS NameNode/DataNode, replication 1; raw/cleaned/curated zones populated; filesystem health check passed.
- Both Spark runs checked input schema, complete epochs, duplicate fine-cell keys, finite nonnegative values, fine/coarse mapping, population conservation, coverage counts, complete cell trajectories, unique curated keys and exact Parquet round-trip contents.
- Local output and downloaded HDFS output agree on every key/metadata/coverage value and all population values (relative tolerance 1e-12, absolute 1e-8 persons).

## Population totals for the pilot rectangle

| Year | Type | Population estimate | 1 km records |
|---|---|---:|---:|
'''
    body+=''.join(f"| {r['year']} | {r['epoch_type']} | {r['total_population']:,.3f} | {r['cells']:,} |\n" for r in years)
    body+='''
These totals describe the chosen rectangle and must not be presented as Bengaluru
municipal population. Projections are not historical observations. No substantive
urban-growth conclusions or nationwide findings are claimed at this stage.

## Deliverables

- `data/raw/downloads/`: original official population ZIPs.
- `data/raw/reference/`: official settlement-grid ZIP and reference GeoTIFF.
- `data/cleaned/GHS_POP_*_bengaluru_100m.tif`: 12 aligned clipped rasters.
- `data/cleaned/population_100m/`: Spark staging Parquet.
- `data/curated/population_1km/`: local verified handoff Parquet.
- `data/curated/population_1km_from_hdfs/`: downloaded HDFS output, independently verified during HDFS execution.
- HDFS tree: `/ghsl/population/{raw,cleaned,curated}`; curated output at `/ghsl/population/curated/population_1km`.
- `config/grid_contract.json` and `TEAM_HANDOFF.md`: shared spatial/key contract.
- `notebooks/Population_Weeks_1_to_5.ipynb`: executable walkthrough of saved results and optional rerun commands. The underlying scripts were executed; the notebook is supplied as a walkthrough, not claimed as an executed Colab session.
- `reports/`: source manifest, validation JSON, SQL epoch summary, samples, test evidence, HDFS status/health and execution logs.

## Explicit boundaries

The population member's weeks 1–5 pilot work is implemented and executed. Native JRC
downloads substitute for the proposal's Earth Engine export step. Raster extraction
is local; DataFrame processing is Spark local[2] backed by real single-node HDFS.
The full three-product join awaits the team's settlement and built-up outputs and
agreement on the shared pilot. No mock versions of those datasets were substituted.
India-wide multi-tile processing, India/district boundaries, district summaries,
and settlement-growth analysis are outside this pilot and remain later milestones.

The HDFS services are stopped after validation; data persist on disk and can be
reopened with `scripts/hdfs.py start`. See README for reproducible commands.

Earlier HDFS attempts wrote output but stalled in Spark's multiset round-trip
comparison; one also lost its executor heartbeat. Their outputs are preserved in
HDFS under `population_1km_initial_attempt` / `population_1km_prior_*`. The final
pipeline uses a full outer join with null-safe comparison of every column after
checking unique keys, with adaptive execution disabled. Reported timings and PASS
status refer to the successful run, not the interrupted attempts.

## Scientific interpretation

Counts are summed, not averaged. Source NoData is null and zeros remain valid.
At the pilot boundary, totals cover only in-pilot 100 m cell centres. Do not rescale
boundary subtotals to full-cell counts. `coverage_fraction` concerns missing data;
`aoi_fraction` concerns area coverage. Read the team handoff before cross-product joins.

Source: European Commission Joint Research Centre, GHS-POP R2023A,
https://doi.org/10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE.
'''
    (ROOT/'reports/EXECUTION_REPORT.md').write_text(body)
    def md(s):return dict(cell_type='markdown',metadata={},source=s.splitlines(keepends=True))
    def code(s):return dict(cell_type='code',metadata={},source=s.splitlines(keepends=True),execution_count=None,outputs=[])
    cells=[md('''# GHSL population — weeks 1–5

Population-only Bengaluru pilot. The Python scripts have been executed locally,
including real HDFS storage. This notebook is a walkthrough of the resulting files
and provides optional rerun commands; it is not an executed Colab session.

Open from the GHSL project with its `.venv` kernel. No Earth Engine authentication is
needed. Keep 2025/2030 projections separate from historical data. See README and
TEAM_HANDOFF for scope, sources and grid details.'''),
    code('''from pathlib import Path
import json, sys, subprocess
here = Path.cwd().resolve()
ROOT = next(p / 'population' for p in [here, *here.parents] if (p / 'population/config/pilot.json').exists())
print('Population project:', ROOT)
print(json.dumps(json.loads((ROOT / 'config/pilot.json').read_text()), indent=2))'''),
    md('## 1. Source provenance and grid alignment\nRead the download manifest and the exact shared 1 km grid.'),
    code('''manifest = json.loads((ROOT / 'reports/download_manifest.json').read_text())
print(len(manifest), 'validated source archives')
print(json.dumps(json.loads((ROOT / 'config/grid_contract.json').read_text()), indent=2))'''),
    md('## 2. Executed validation results\nThe reports below come from the actual local and HDFS Spark runs.'),
    code('''for name in ['spark_validation.json', 'spark_hdfs_validation.json']:
    report = json.loads((ROOT / 'reports' / name).read_text())
    print(name, report['status'], report['input_rows'], 'input rows →', report['output_rows'], 'output rows')
print((ROOT / 'reports/tests.txt').read_text())'''),
    md('## 3. Query the delivered Parquet\nPopulation is the sum of residents inside the pilot mask. Boundary cells may cover less than 1 km².'),
    code('''import pyarrow.dataset as ds
dataset = ds.dataset(ROOT / 'data/curated/population_1km', format='parquet', partitioning='hive')
print(dataset.schema)
sample = dataset.to_table(filter=ds.field('year') == 2020).slice(0, 5)
sample.to_pylist()'''),
    code('''summary = json.loads((ROOT / 'reports/spark_hdfs_validation.json').read_text())['epochs']
for row in summary:
    print(row['year'], row['epoch_type'], f"{row['total_population']:,.3f}", 'estimated residents in pilot rectangle')'''),
    md('## 4. Optional pipeline rerun\nSet RUN_PIPELINE to True only when you want to process the source files again. This uses a fresh output directory; existing outputs are not overwritten.'),
    code('''RUN_PIPELINE = False
if RUN_PIPELINE:
    import uuid
    run_id = uuid.uuid4().hex[:8]
    for script in ['scripts/download_population_tiles.py', 'src/prepare_population_rasters.py']:
        subprocess.run([sys.executable, str(ROOT / script)], check=True)
    subprocess.run([sys.executable, str(ROOT / 'src/spark_population.py'),
                    '--output', str(ROOT / 'data/curated' / ('rerun_' + run_id)),
                    '--report', 'rerun_' + run_id + '.json'], check=True)
else:
    print('Using completed execution results; no recomputation requested.')'''),
    md('## 5. HDFS and team handoff\nSee README for HDFS start/stage/run/stop commands. The real HDFS execution is documented in reports/hdfs_fsck.txt and reports/spark_hdfs_validation.json. Join to teammates on (grid_id, cell_id, year) only after confirming grid and mask compatibility. The full three-product join has not been run because those inputs were not supplied.')]
    notebook=dict(cells=cells,metadata={'kernelspec':{'display_name':'Python 3 (GHSL .venv)','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12'}},nbformat=4,nbformat_minor=5)
    for i,cell in enumerate(cells):cell['id']=f'population-{i:02d}'
    for cell in cells:
        if cell['cell_type']=='code':compile(''.join(cell['source']),'<notebook-cell>','exec')
    (ROOT/'notebooks/Population_Weeks_1_to_5.ipynb').write_text(json.dumps(notebook,indent=2)+'\n')
    # Compact handoff excludes raw tile archives, environment, runtime and noisy logs.
    include=[ROOT/'README.md',ROOT/'TEAM_HANDOFF.md',ROOT/'requirements.txt',ROOT/'requirements-lock.txt']
    for folder in ['config','src','scripts','tests','notebooks']:
        include.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    include.extend(p for p in (ROOT/'reports').iterdir() if p.suffix in ('.md','.json','.csv','.txt') and p.name!='hdfs_files.txt')
    include.extend(p for p in (ROOT/'data/curated/population_1km').rglob('*') if p.is_file() and not p.name.startswith('.'))
    destination=ROOT/'Population_Weeks1_5_Handoff.zip'
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for path in include:z.write(path,'population/'+str(path.relative_to(ROOT)))
    with zipfile.ZipFile(destination) as z:
        if z.testzip():raise ValueError('Handoff ZIP failed integrity check')
    print(f'Built {destination.name}: {destination.stat().st_size:,} bytes')

if __name__=='__main__':main()
