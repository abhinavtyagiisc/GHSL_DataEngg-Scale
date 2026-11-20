# Phase 1 — weeks 1–3, complete-project foundation

This phase covers every GHSL product needed by the proposal, owned by one person:
POP, BUILT-S total/NRES and SMOD. It adds the professor’s requirements: actual Apache
Sedona geospatial Spark operations and explicit quantitative performance benchmarks.
See [the reproduction guide](../REPRODUCTION.md) for the three phases. Do not advance to phases 2/3
merely to reproduce this phase. Existing earlier work remains preserved.

## Evidence and data

- `reports/PHASE1_COMPLETION_REPORT.md`: completion report, written only after checks pass.
- `reports/PHASE1_VALIDATION.json` and root `_SUCCESS`: final phase-1 evidence.
- `reports/input_audit_run2/`: all 48 archives, prepared rasters and real HDFS checks.
- `reports/sedona_local1_run3/`, `reports/sedona_local2_run1/`: accepted Sedona runs.
- `config/benchmark.json`: protocol and targets declared before measurements.
- `reports/BENCHMARK_RESULTS.csv`: measured results; raw repetitions are in run JSON.
- `runtime/jar_manifest.json`: pinned JVM sources and checksum verification.
- `requirements-lock.txt`: Python environment snapshot used for completed delivery.

All source archives remain under `../population/data/raw/`; prepared all-product pilot
rasters and independent tables are under `../integration/data/prepared/`. Data cover
ten historical observations (1975–2020) plus 2025/2030 test epochs. GeoBoundaries
provides fixed country/district reference geometries; it is not an official Indian
administrative boundary or a reconstruction of historical districts.

The actual existing HDFS root is `/ghsl/weeks1_5/bengaluru_run1`, containing raw, cleaned
and curated zones. Phase 1 rechecks this root rather than creating duplicate data.
The audit independently retrieves and hashes all raw and prepared/curated files,
checks HDFS health, and stops only the services it started.

## Reproduction in the retained project workspace

Use the project `.venv` with Spark 3.5.6, Java 17 and Apache Sedona 1.9.1. A new machine
can create an environment using the included requirements lock. The large raw archives
and HDFS runtime are not in the compact handoff ZIP; restore them using the original
source-acquisition and HDFS setup scripts before running the full HDFS audit.

```sh
uv pip sync --python .venv/bin/python phase1/requirements-lock.txt
.venv/bin/python phase1/scripts/bootstrap_sedona.py
.venv/bin/python -m pytest phase1/tests -q
.venv/bin/python phase1/scripts/audit_inputs.py --output phase1/reports/audit_new_run
.venv/bin/python phase1/src/sedona_benchmark.py --workers 1 --output phase1/reports/local1_new_run
.venv/bin/python phase1/src/sedona_benchmark.py --workers 2 --output phase1/reports/local2_new_run
```

Spark/HDFS require local sockets. Dependency bootstrap requires network access. Run
benchmarks sequentially after other project jobs stop. Scripts refuse existing output
directories; use fresh names and preserve failed evidence. The handoff builder reads
the documented accepted evidence paths, so review/update its paths before packaging
a new experiment. It refuses to overwrite an existing ZIP.

## Spatial validation and benchmark semantics

All 434,363 pilot 100 m centres undergo Sedona country coverage and 1 km parent-cell
containment checks. A Sedona indexed district spatial join is compared cell-for-cell
against the independent Shapely mapping. Physical plans and Spark event logs prove
that geospatial Spark work ran. Coordinate projection uses the established PyProj
contract before Sedona; no unsupported CRS-transform claim is made.

Benchmarks compare local[1] and local[2], using 10,000, 100,000 and 434,363 points,
one warmup and five measured repetitions. Inputs are cached; each repetition rebuilds
its query to avoid Spark reusing earlier shuffle computation. Job groups isolate task
metrics from input preparation, and at least 16 tasks must execute per timed query.
Startup/input preparation are excluded from warm query latency and separately recorded.
Metrics: median/P95 seconds, cells/second, sampled process-tree RSS/CPU, Spark task CPU
and runtime, GC, shuffle read/write and memory/disk spill. This is local parallelism,
not evidence of multi-machine cluster scaling. A ratio below 1 is reported honestly.

Predeclared full-pilot targets are median ≤120 s, throughput ≥3,500 cells/s and sampled
process-tree RSS ≤8 GB. These are engineering targets, not external standards; missing
them is reported rather than hidden. Zero source/mapping/key errors is a hard gate.

## Preserved attempts and limitations

`input_audit_run1` failed on relative-path reporting before HDFS started.
`sedona_local1_run1` passed spatial QA but its timings were invalidated because repeated
collects reused shuffle stages. `sedona_local1_run2` rebuilt queries but still assigned
next-input preparation metrics to the preceding job group. Neither timing attempt is
used in the final benchmark comparison. Their logs remain as diagnostic evidence.

Official JRC downloads substitute for the proposal’s Earth Engine exports. No Earth
Engine authentication/export execution is claimed. HDFS is single-node, replication one.
Later-phase integration and national analysis are not part of this revised completion.

Sources: JRC GHSL R2023A POP/BUILT-S V1_0 and SMOD V2_0; geoBoundaries gbOpen with
ODbL 1.0 attribution retained. Sedona setup: https://sedona.apache.org/1.9.1/setup/install-python/
