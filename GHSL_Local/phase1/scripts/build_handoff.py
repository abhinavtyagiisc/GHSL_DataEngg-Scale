"""Build a phase-1-only handoff after source, HDFS and Sedona evidence passes."""
from pathlib import Path
import csv
import hashlib
import importlib.metadata
import json
import platform
import re
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'analysis/scripts'));from progress_log import update


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    archive=PROJECT/'GHSL_Phase1_Weeks1_3_Handoff.zip'
    if archive.exists():raise FileExistsError(archive)
    audit_path=ROOT/'reports/input_audit_run2'
    benchmark_paths=[ROOT/'reports/sedona_local1_run3',ROOT/'reports/sedona_local2_run1']
    for path in [audit_path]+benchmark_paths:
        if not (path/'_SUCCESS').exists():raise ValueError('Missing completed phase-1 evidence: '+str(path))
    audit=json.loads((audit_path/'validation.json').read_text())
    benchmarks=[json.loads((p/'validation.json').read_text()) for p in benchmark_paths]
    if any(r['status']!='PASS' for r in [audit]+benchmarks):raise ValueError('Failed validation')
    tests=(ROOT/'reports/tests_contract_after_pandas.txt').read_text()
    if not re.search(r'\b3 passed\b',tests):raise ValueError('Phase-1 contract tests not verified')
    aggregation=json.loads((ROOT/'reports/aggregation_validation.json').read_text())
    if aggregation['status']!='PASS' or len(aggregation['epochs'])!=12:raise ValueError('Independent aggregation validation incomplete')
    cfg=json.loads((ROOT/'config/benchmark.json').read_text())
    summaries=[]
    for b in benchmarks:
        if b['spatial_qa']['cells']!=434363 or b['spatial_qa']['assignment_mismatches']!=0:raise ValueError('Spatial validation failed')
        for r in b['summaries']:
            if r['repetitions']!=cfg['measured_repetitions']:raise ValueError('Wrong benchmark repetition count')
            summaries.append(dict(master=b['environment']['master'],**r))
    comparisons=[]
    for rows in cfg['input_sizes']:
        one=next(r for r in summaries if r['rows']==rows and r['master']=='local[1]')
        two=next(r for r in summaries if r['rows']==rows and r['master']=='local[2]')
        comparisons.append(dict(rows=rows,single_to_dual_worker_time_ratio=one['median_seconds']/two['median_seconds']))
    target=cfg['engineering_targets'];outcomes=[]
    for r in summaries:
        if r['rows']==434363:
            outcomes.append(dict(master=r['master'],median_latency_target_pass=r['median_seconds']<=target['full_pilot_join_median_seconds_max'],
                                 throughput_target_pass=r['median_rows_per_second']>=target['full_pilot_join_min_rows_per_second'],
                                 sampled_memory_target_pass=r['peak_rss_bytes']<=target['full_pilot_process_tree_peak_rss_bytes_max']))
    with (ROOT/'reports/BENCHMARK_RESULTS.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    sizes=cfg['input_sizes'];x=np.arange(len(sizes));width=.35
    for j,master in enumerate(('local[1]','local[2]')):
        data=[next(r for r in summaries if r['rows']==size and r['master']==master) for size in sizes]
        positions=x+(j-.5)*width
        axes[0].bar(positions,[r['median_seconds'] for r in data],width,label=master,
                    yerr=np.array([[0]*len(data),[max(0,r['p95_seconds']-r['median_seconds']) for r in data]]),capsize=3)
        axes[1].bar(positions,[r['median_rows_per_second']/1000 for r in data],width,label=master)
    for ax in axes:
        ax.set_xticks(x,[f'{size:,}' for size in sizes]);ax.set_xlabel('Input cells');ax.legend();ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    axes[0].set(title='Spatial join latency',ylabel='Median seconds (upper bars: P95)')
    axes[1].set(title='Spatial join throughput',ylabel='Thousand cells / second')
    fig.suptitle('Apache Sedona: cached inputs, fresh query per repetition',fontsize=11)
    fig.savefig(ROOT/'reports/BENCHMARK_RESULTS.png',dpi=180);plt.close(fig)
    env=benchmarks[0]['environment']
    lines=['# Phase 1 Completion Report — Weeks 1–3','',
           '**Project:** India’s Urban Concentration and Emerging Growth Centres using GHSL  ',
           '**Date:** 7 November 2026  ',
           '**Status:** Completed pilot validation and benchmarks.','',
           '## 1. Scope','',
           'A validated foundation for all three GHSL products: population, built-up surface (total and non-residential), and settlement classification. The work covers the Bengaluru pilot across all ten historical observations from 1975 to 2020, plus 2025/2030 test observations. Existing source data were re-audited and reused. Apache Sedona now performs actual geospatial Spark operations, and quantitative benchmark definitions and measurements are supplied.','',
           '## 2. Validation results','',
           '| Requirement | Verified result |','| --- | --- |',
           '| All-product coverage | 48 source archives: four raster components × 12 observations; 100% expected coverage |',
           '| Source integrity | All cached archive SHA256 and ZIP CRC checks passed |',
           '| Grid and value checks | All 48 clipped rasters checked for CRS, resolution, NoData, masks, valid categories and totals |',
           '| Native/parent relationship | All product keys and parent domains agree; independently recomputed population, total built-up and NRES sums match every 1 km output cell over all 12 observations |',
           f"| Actual HDFS verification | Raw, cleaned and curated zones retrieved; 48 source archive hashes and {audit['hdfs_compared_prepared_curated_files']} prepared/curated files matched |",
           '| Apache Sedona | Spatial country coverage, district assignment and fine-cell-to-parent containment executed in Spark |',
           '| Independent spatial validation | Every one of 434,363 pilot cells matched the separate Shapely district reference; zero missing/duplicate or mismatched assignments |',
           '| Tests | Three phase-1 contract/metric tests passed; actual Sedona jobs independently passed on both worker settings |',
           '| Performance evaluation | Three input sizes, one warmup and five measured repetitions per size, for local[1] and local[2] |','',
           'These spatial checks validate the pilot workload. The study area is a rectangle around Bengaluru, not a city administrative boundary.','',
           '## 3. Geospatial processing with Apache Sedona','',
           f"Apache Sedona {env['sedona']} runs with Spark {env['spark']}, Scala {env['scala']} and Java {env['java']}. The pinned JVM artifacts and their published-checksum/local-SHA256 evidence are in `runtime/jar_manifest.json`.",'',
           'Spatial SQL uses ST_Covers for point-in-polygon matching, ST_Point for native cell centres, ST_PolygonFromEnvelope for 1 km parents, and ST_Area for parent-area validation. Saved physical query plans must contain a Sedona spatial join operator. The output mapping is persisted and checked after reading it back. This is functional integration rather than installation alone.','',
           'Boundary geometries are projected with the established PyProj grid contract before Sedona processing. No new accuracy is implied by inheriting a 1 km settlement class at 100 m.','',
           '## 4. Quantitative performance evaluation','',
           'Protocol: benchmark.json was saved before measurements. Each workload uses cached inputs but recomputes and materializes the spatial join result. JVM startup and input/validation preparation are recorded separately. All runs use eight Spark partitions; only local worker count changes. Input sizes use deterministic spatially ordered subsets, not random samples. Results are workload-specific and are not extrapolated to India. No minimum speedup is assumed.','',
           '| Workers | Input cells | Median seconds | P95 seconds | Median cells/second | Peak sampled process-tree RSS (GB) |',
           '| --- | ---: | ---: | ---: | ---: | ---: |']
    for r in summaries:lines.append(f"| {r['master']} | {r['rows']:,} | {r['median_seconds']:.3f} | {r['p95_seconds']:.3f} | {r['median_rows_per_second']:,.0f} | {r['peak_rss_bytes']/1e9:.3f} |")
    lines+=['','![Measured Sedona spatial join performance](BENCHMARK_RESULTS.png)','','Single-worker median time divided by two-worker median time (a ratio below 1 indicates slower two-worker execution):','']
    for r in comparisons:lines.append(f"- {r['rows']:,} cells: {r['single_to_dual_worker_time_ratio']:.3f}×.")
    lines+=['','Per-repetition JSON also records sampled CPU time, Spark task runtime/CPU time, JVM garbage collection, memory/disk spill and shuffle read/write bytes. Peak RSS is sampled every 100 ms and sums Python/JVM descendants; shared pages can be counted more than once. Five repetitions provide a small-sample P95 estimate, not a formal confidence interval.','',
            f"Machine: {env['platform']}; {env['physical_cpus']} physical / {env['logical_cpus']} logical CPUs; {env['ram_bytes']/1e9:.1f} GB RAM. These are single-machine results, not multi-machine distributed scaling evidence.",'',
            'Predeclared engineering targets for the full pilot join: median ≤120 s, throughput ≥3,500 cells/s, sampled process-tree RSS ≤8 GB. These are local engineering targets, not external standards. Correctness is a hard gate; performance target outcomes are reported below without changing the thresholds after measurement.','']
    for r in outcomes:lines.append(f"- {r['master']}: latency {'PASS' if r['median_latency_target_pass'] else 'NOT MET'}; throughput {'PASS' if r['throughput_target_pass'] else 'NOT MET'}; sampled memory {'PASS' if r['sampled_memory_target_pass'] else 'NOT MET'}.")
    lines+=['','## 5. Storage verification measurements','',
            '| HDFS zone retrieved | Bytes | Wall seconds | MB/second |','| --- | ---: | ---: | ---: |']
    for r in audit['hdfs_transfer']:lines.append(f"| {r['zone']} | {r['bytes']:,} | {r['wall_seconds']:.2f} | {r['decimal_MB_per_second']:.2f} |")
    lines+=['','These are single local-HDFS retrieval observations including command startup; they are not repeated cold-cache storage benchmarks. HDFS health passed with replication one. The audit stopped its own services and removed only its newly created verification copies; original data remain intact.','',
            '## 6. Scope and limitations','',
            'Official JRC native downloads substitute for the proposal’s Earth Engine exports. The source releases, grids and provenance are explicit; no Earth Engine authentication or export execution is claimed. This report therefore documents an acquisition-method deviation rather than presenting literal compliance with that step.','',
            'The fixed country boundary represents 2014 and the district boundary represents 2021. District polygons support spatial validation here, not reconstruction of historical administrative boundaries.','',
            '## 7. Reproduction and evidence','',
            'See README.md for commands and REPRODUCTION.md for the three-phase overview. Key evidence: reports/input_audit_run2/validation.json; reports/sedona_local1_run3/validation.json; reports/sedona_local2_run1/validation.json; saved physical plans and Spark event logs; reports/tests_contract_after_pandas.txt; config/benchmark.json.','',
            'The phase-1 ZIP includes clipped all-product pilot rasters/tables, source provenance, Sedona mapping outputs, code, configuration and reports. Large original source ZIPs, HDFS runtime, the Python environment and JVM binaries remain outside the package; dependency and source manifests identify them.','',
            'Sources: European Commission Joint Research Centre GHSL R2023A (POP/BUILT-S V1_0, SMOD V2_0); geoBoundaries gbOpen, district sources Pathways Data Pvt. Ltd. and lgdirectory.gov.in, ODbL 1.0. Preserve attribution when sharing derived data.','',
            'Apache Sedona setup: https://sedona.apache.org/1.9.1/setup/install-python/  ',
            'Spatial join documentation: https://sedona.apache.org/latest/api/sql/Optimizer/','']
    (ROOT/'reports/PHASE1_COMPLETION_REPORT.md').write_text('\n'.join(lines))
    result=dict(status='PASS',phase='weeks1_3',all_three_products=True,source_archives=48,sedona_spatial_cells=434363,benchmarks=summaries,parallelism_ratios=comparisons,engineering_target_outcomes=outcomes,tests='3 contract tests plus real Sedona QA for both worker settings',later_phases='Deferred under revised user scope')
    (ROOT/'reports/PHASE1_VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
    pins=sorted(f'{d.metadata["Name"]}=={d.version}' for d in importlib.metadata.distributions() if d.metadata.get('Name'))
    (ROOT/'requirements-lock.txt').write_text('\n'.join(pins)+'\n')
    files=[]
    for folder in [ROOT/'src',ROOT/'scripts',ROOT/'config',ROOT/'tests',ROOT/'reports',PROJECT/'integration/data/prepared',PROJECT/'population/src',PROJECT/'population/scripts',PROJECT/'integration/src',PROJECT/'integration/scripts',PROJECT/'analysis/src',PROJECT/'population/config']:
        files.extend(p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.startswith('.') and p.suffix not in ('.pyc',))
    files.extend([ROOT/'README.md',ROOT/'requirements-lock.txt',ROOT/'runtime/jar_manifest.json',PROJECT/'REPRODUCTION.md',PROJECT/'integration/reports/download_manifest_full.json',PROJECT/'integration/config/pilot.json',PROJECT/'integration/config/grid_contract.json',PROJECT/'analysis/data/boundaries/IND_ADM2.provenance.json',PROJECT/'analysis/data/boundaries/IND_ADM2.geojson',PROJECT/'analysis/data/district_mapping/cell_district.parquet',PROJECT/'analysis/data/district_mapping/validation.json',PROJECT/'population/data/raw/boundaries/geoBoundaries-IND-ADM0.geojson',PROJECT/'population/data/raw/boundaries/geoBoundaries-IND-ADM0.provenance.json'])
    missing=[str(p) for p in files if not p.exists()]
    if missing:raise FileNotFoundError('Missing handoff file: '+str(missing))
    files=sorted(set(files))
    manifest={str(p.relative_to(PROJECT)):sha(p) for p in files}
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(PROJECT))
        z.writestr('SHA256.json',json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise ValueError('Archive CRC failed')
        for path,digest in manifest.items():
            if hashlib.sha256(z.read(path)).hexdigest()!=digest:raise ValueError('Archive SHA256 failed')
    (ROOT/'_SUCCESS').write_text('PASS\n')
    update('Build and verify phase-1 handoff','PASS',f'All phase-1 correctness gates passed. ZIP contains {len(files)} files ({archive.stat().st_size:,} bytes), CRC/SHA256 verified. See `phase1/reports/PHASE1_COMPLETION_REPORT.md`. No phase 2/3 execution started.')
    print(json.dumps(result,indent=2));print(archive)


if __name__=='__main__':
    try:main()
    except Exception as exc:update('Build phase-1 handoff','FAILED',str(exc));raise
