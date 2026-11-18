# Bounded national three-product runner

`src/national.py` prepares independent population, built-up and settlement tables
in aligned windows, then runs the existing Spark validator/join on one tile-year.
It retains curated output, source hashes and validation metadata, commits a checkpoint,
and removes only that completed pair's generated staging tables. Raw archives remain
in the shared cache. No duplicate national HDFS copy is created by this runner.

The supplied `config/india.json` uses the retained geoBoundaries ADM0 snapshot and
all twelve epochs. Historical conclusions must exclude the 2025/2030 projections.
The boundary is a reproducible study mask, not an official Indian administrative map.

## Execution

From the project root, with the existing environment:

```sh
.venv/bin/python integration/src/national.py \
  --config integration/config/india.json \
  --output integration/data/national_run1 --download --max-pairs 1
```

This processes one tile-year as a resource checkpoint. Resume in bounded batches:

```sh
.venv/bin/python integration/src/national.py \
  --config integration/config/india.json \
  --output integration/data/national_run1 --download --resume --max-pairs 1
```

Omit `--max-pairs` only when ready for the entire remaining workload. `--download`
is needed only for missing sources. Source ZIP CRC and SHA256 are recorded. Existing
sources are reused. `--block-pixels` defaults to 1000 (one million fine pixels per
raster window); use multiples of ten. Spark requires local socket access.

The 20 GB free-space reserve is a pre-pair guard, not a guarantee against exhaustion
within a pair. Failed attempts are preserved in `incomplete/` and count against free
space. Review actual first-pair disk/time measurements before scaling up. Spark runs
local[2] and performs disk-backed processing over the whole tile-year staging table;
this is not distributed raster processing or a multi-machine benchmark.

## Resume and integrity

An OS lock prevents concurrent writers to one run. Resume checks configuration,
country-mask hash, grid, processing-source hashes, source archive hashes and every
checkpointed output hash. Completed runs refuse resume. Changed code/configuration
requires a new output directory. Completed pairs are skipped, and an uncheckpointed
pair is preserved before recomputation. A checkpoint is committed before staging
cleanup; resume can finish cleanup if interrupted between those steps.

Only the top-level `_SUCCESS` plus `validation.json` indicates every planned pair
completed. Per-pair `_INTEGRATION_SUCCESS` does not establish national completion.
Dataset paths are under `pairs/<tile>_<year>/curated/`; read matching child dataset
paths together, rather than treating the whole run as one Parquet dataset.

## Spatial and missing-data policy

The nominal tile ownership and 1 km-aligned windows keep both fine and parent keys
disjoint across tile seams. All products use the same 100 m centre mask. POP must
provide the nominal tile grid. Built-up and settlement may have cropped extents;
reads outside those extents become null, never inferred zero. Alignment, rotation,
CRS, explicit NoData and value ranges are checked. NRES cannot exceed total built-up.
Matching-year settlement categories are inherited from native 1 km parents.

Spark reports rejected fine cells and writes them separately. Coarse summaries keep
known per-variable subtotals and completeness counts. Thus coarse totals can include
values from cells absent from the complete-case fine analytical table. Historical
analysis needs an explicit common-valid mask when completeness varies; do not feed
incomplete national trajectories into the pilot temporal analysis blindly.

National district attribution, cross-year common-valid-mask validation and national
component/temporal analysis remain separate work. No full national result is claimed
merely because this runner exists or a validation subset succeeds.

## Executed validation, 2026-11-07

The cached pilot validation subset (2015/2020) passed real Spark execution and
checkpoint resume in `data/bounded_validation_run1`. Every column agrees with the
completed pilot for 868,726 fine rows and 8,910 coarse rows total, using float
tolerance rtol=1e-10 and atol=1e-5. See `reports/bounded_validation_comparison.json`.
Both pairs' staging tables were removed, and completed output hashes were verified.
The integration suite passed 10 tests; the subsequently expanded national-specific
suite passed four tests, including preservation/recovery of an interrupted pair.
These are validation-subset results, not national processing results.
