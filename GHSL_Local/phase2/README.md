# Weeks 4–5: reusable all-product integration

Current work: validated Spark/Sedona integration, native 100 m and summed 1 km Parquet, SQL summaries, actual HDFS execution, end-to-end performance comparisons. Inputs reuse the verified phase-1 products and pinned environment. Existing outputs are preserved.

Sedona spatial SQL assigns each native cell centre to its matching-year settlement polygon in ESRI:54009. Population and both built-area measurements remain native; settlement categories are inherited, not newly measured at 100 m. Missing values remain null, zero remains valid, and partial AOI totals are not extrapolated.

Optimizer reference: https://sedona.apache.org/latest/api/sql/Optimizer/

## Reproduce from the project root

Use the existing `.venv` and pinned `phase1/requirements-lock.txt`. Restore the JARs
with `phase1/scripts/bootstrap_sedona.py` only if missing; the integration verifies
both JAR SHA256 values before starting Spark. Read the phase-1 guide for input restore.

```sh
.venv/bin/python -m pytest phase2/tests -q
.venv/bin/python phase2/scripts/run_hdfs.py
.venv/bin/python phase2/scripts/compare_integration_outputs.py
.venv/bin/python phase2/scripts/run_benchmarks.py
```

HDFS and Spark need loopback socket permission. The HDFS runner refuses existing
local outputs, owns only services it starts and stops them in `finally`. Existing
HDFS metadata must be present; it never intentionally initializes a replacement.
It reads `/ghsl/weeks1_5/bengaluru_run1/cleaned/tables` and writes the new path
`/ghsl/phase2/sedona_run1/grid_year`. Completed benchmark scenarios are skipped;
partial attempts must be inspected and preserved under a different name before retry.

For another prepared area/epoch set conforming to the shared grid contract:

```sh
.venv/bin/python phase2/src/spark_sedona_integrate.py --prepared /path/to/prepared --input /path/to/prepared/tables --output /new/output --report /new/report.json --master 'local[2]'
```

The prepared directory must have `_SUCCESS`, config, grid contract and raster source
validation metadata. Inputs are population, built_up (total and non-residential) and
settlement tables; all epochs and coverage must agree. Unsupported CRS is rejected.
This reuses the existing all-product input validator and aggregation functions rather
than maintaining conflicting copies. Grid IDs and release/version metadata are retained.
The indexed settlement side is suitable for bounded tile-year/pilot workloads;
India is processed in bounded jobs, not a single nationwide broadcast.

## Output and validation contract

- `analytical_100m`: 21 columns, only jointly valid records, historical/projection and year partitions.
- `summary_1km`: known native sums, valid counts, partial-footprint fraction and completeness flag (17 columns).
- `sql_class_summary`: population and built-area totals and fine-cell counts by year/class.
- `rejected_cells`: written when any input measurement/category is missing.
- `_INTEGRATION_SUCCESS`: only after schema/key/coverage/conservation and full-content reread checks pass.

A matching-year category is selected by actual `ST_Covers` against parent polygons.
The executed physical plan must contain a Sedona spatial join operator. Independent
integer-parent output comparison checks every persisted column. Float aggregate
comparisons allow rtol 1e-10 / atol 1e-5; round-trip checks within Spark are exact.

## Performance protocol

See `config/benchmark.json`, declared before measurement. A timed trial starts before
reading all three product tables and ends after writing all three analytical outputs.
No DataFrame is cached; each repetition constructs a fresh query and output path.
This measures repeated work for separately written outputs as implemented, including
Parquet compression. Post-write comparison is outside the timer. Trial task metrics
exclude validation by clearing Spark job-group properties immediately after timing.
One warmup and three measured repetitions per scenario; median, descriptive P95,
rows/s, sampled process-tree RSS/CPU, Spark task time/GC/shuffle/spill and output bytes.
RSS sums process values and can double-count shared pages; 100 ms sampling can miss
brief peaks. CPU may miss short-lived descendants. OS cache is not flushed; no claim
of cold disk or multi-machine scaling. Performance targets were defined before measurement and used to evaluate the runs. Correctness is mandatory even if
a performance target is missed.
