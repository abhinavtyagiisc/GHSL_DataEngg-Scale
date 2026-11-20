from pathlib import Path
import csv,json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
PROJECT=Path(__file__).resolve().parents[2];ROOT=PROJECT/'phase2'
sys.path.insert(0,str(PROJECT/'analysis/scripts'));from progress_log import update
rows=[]
for mode,w,p in json.loads((ROOT/'config/benchmark.json').read_text())['scenarios']:
    r=json.loads((ROOT/f'reports/benchmarks/{mode}_w{w}_p{p}/validation.json').read_text())
    rows.append(dict(scenario=f'{mode}, {w} workers, {p} partitions',median_seconds=r['median_seconds'],p95_seconds=r['p95_seconds'],rows_per_second=r['median_rows_per_second'],peak_rss_GB=r['peak_rss_bytes']/1e9,targets_pass=r['targets_pass']))
with (ROOT/'reports/benchmark_summary.csv').open('w') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
fig,ax=plt.subplots(figsize=(10,4.8));ax.barh([r['scenario'] for r in rows],[r['median_seconds'] for r in rows],color=['#718096','#276FBF','#228B75','#A269AE']);ax.invert_yaxis();ax.set_xlabel('Median end-to-end seconds (lower is faster)');ax.set_title('All-product integration: 434,363 cells, 2020');ax.grid(axis='x',alpha=.2);fig.tight_layout();fig.savefig(ROOT/'reports/benchmark_comparison.png',dpi=160);plt.close(fig)
h=json.loads((ROOT/'reports/hdfs_validation.json').read_text());v=json.loads((ROOT/'reports/reference_comparison.json').read_text())
text=f"""# Phase 2 completion report — weeks 4–5

India’s Urban Concentration and Emerging Growth Centres using GHSL  
7 November 2026

## Outcome

The reusable all-product Spark/Sedona pilot has executed successfully on HDFS across
all 12 epochs (1975–2030). Ten historical observations and two projection tests remain
separately labelled. Population, total built-up, non-residential built-up and
matching-year settlement class are available together for every valid native cell.

- {h['analytical_rows']:,} native 100 m records and {h['coarse_rows']:,} summed 1 km records.
- {h['rejected_rows']} rejected records; {h['incomplete_trajectories']} incomplete trajectories in this pilot.
- HDFS pipeline, including validation: {h['elapsed_seconds']} seconds (single observation).
- HDFS health passed, outputs retrieved locally, owned services stopped.
- Independent Arrow comparison passed for every native, coarse and SQL-summary column.
- Three actual Sedona regression tests passed in 35.25 seconds.

## Implementation and evaluation

Apache Sedona 1.9.1 assigns native centres to matching-year SMOD parent
polygons. The physical-plan guard requires a Sedona spatial operator; plans are
retained alongside execution evidence. Spark handles ingestion, validation, native
product joining, sums, SQL summaries and partitioned Parquet persistence.

Explicit quantitative metrics were declared before measurement: median and descriptive
P95 latency, native rows/s, peak sampled process-tree RSS, CPU, task time, GC,
shuffle/spill bytes, output size, worker scaling and partition sensitivity.
Every trial must pass persisted-result equivalence regardless of its speed.

## End-to-end results

One real epoch (2020), all products, 434,363 native cells. One warmup and three
measured repetitions per scenario. Timer includes fresh reads, joins, aggregation and
writes of native, coarse and class-summary outputs. Startup and post-write correctness
checks are excluded. No cached DataFrames or reused result query; OS cache uncontrolled.

| Scenario | Median s | P95 s | Cells/s | Peak RSS GB | Targets passed |
|---|---:|---:|---:|---:|---|
"""
for r in rows:text+=f"| {r['scenario']} | {r['median_seconds']:.3f} | {r['p95_seconds']:.3f} | {r['rows_per_second']:,.0f} | {r['peak_rss_GB']:.3f} | {r['targets_pass']} |\n"
text+=f"\nSedona one-to-two-worker time ratio: {rows[1]['median_seconds']/rows[2]['median_seconds']:.3f}×. "
text+=f"Sedona/key median time ratio at two workers and eight partitions: {rows[2]['median_seconds']/rows[0]['median_seconds']:.3f}×. "
text+=f"Using 32 instead of eight partitions changes Sedona median time by {(rows[3]['median_seconds']/rows[2]['median_seconds']-1)*100:+.1f}%. "
text+="These observations apply only to this workload and machine; extra partitions can add scheduling overhead.\n"
text+="""
Targets: median ≤120 s, median throughput ≥3,500 cells/s and sampled RSS ≤8 GB.
These are local engineering thresholds, not claims of production cluster capacity.
Three repetitions give only a descriptive P95, not a stable tail-latency estimate.
RSS can double-count shared pages and miss peaks shorter than 100 ms.

![End-to-end benchmark comparison](benchmark_comparison.png)

## Scientific correctness and scope

Native population counts and built-area values are retained. One-kilometre values
are sums; missing values remain null and valid zero is preserved. Settlement is an
inherited 1 km category, not an independently measured 100 m classification.
Partial pilot cells are flagged without extrapolation. Keys, epochs, masks, input
ranges, unique assignments and conservation are checked before completion. Projections
are excluded from historical conclusions. Independent aggregate comparisons permit
rtol 1e-10 / atol 1e-5; Spark reread comparisons are exact and null-safe.

This validates a reusable pilot/bounded-workload implementation. India-wide execution
and analytical conclusions are phase 3 and are not established by this report.
Official JRC archive acquisition substitutes for Earth Engine exports. All executions
use local Spark and a single-node HDFS; no multi-machine speedup is claimed.
The key-join baseline remains useful for aligned regular grids. Sedona adds spatial
semantics and independently checked geometry; it is not assumed to beat key arithmetic.

## Reproduction

Read ../README.md for commands, schemas, paths and limitations. Detailed evidence:
`hdfs_validation.json`, `hdfs_execution.json`, `reference_comparison.json`,
`tests_run1.txt`, `benchmarks/*/validation.json`, event logs, physical plans and CSV.
The phase-2 handoff includes code, reports and validated curated data; use it with the
phase-1 handoff for staged inputs and environment restoration. Raw national sources,
installed binaries and duplicate benchmark output datasets are excluded. Archive CRC
and per-file SHA256 are verified separately in HANDOFF_VALIDATION.json.

Sedona optimizer reference: https://sedona.apache.org/latest/api/sql/Optimizer/
"""
(ROOT/'reports/PHASE2_COMPLETION_REPORT.md').write_text(text)
update('Generate phase-2 completion report, metrics CSV and benchmark chart','PASS','Report generated from actual validation JSON; chart visual review and handoff verification follow.')
print(json.dumps(rows,indent=2))
