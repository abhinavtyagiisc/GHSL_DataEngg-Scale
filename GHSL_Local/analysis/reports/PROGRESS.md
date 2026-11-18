# Weeks 6–8 checkpoint

## Current execution — 7 November 2026

Phases 1–2 are complete. Phase 3 recovery is running under the already authorized
completion controller; no renewed user permission is pending. Read
`PROGRESS_REPORT.md`, `../../phase3/reports/STATUS.json` and root PROJECT_CONTEXT.md.
Earlier permission denials and implementation status below are historical.

## Historical submission checkpoint — 7 November 2026

Read [PROGRESS_REPORT.md](PROGRESS_REPORT.md) for the plain-language, submission-ready
status report. Weeks 1–5 and historical pilot analysis are complete. National
processing has completed 1/168 jobs (R5_C25/1975: 16,201,044 fine records, zero rejected).
Continuation and district-validation permission requests were denied; both remain
pending renewed permission. Older entries below are historical. The report separates
implemented code, pilot-tested methods and completed national results.


## Bounded runner validation completed (2026-11-07)

Implemented `integration/src/national.py` with aligned windowed three-product
preparation, cropped-extent null handling, per-tile-year Spark integration, atomic
checkpoints, locking, code/config/boundary/source/output hash verification, preservation
of partial attempts, and cleanup of generated staging only after validated checkpoints.
`integration/config/india.json` covers all 12 epochs; `integration/NATIONAL_RUNNER.md`
records commands, missing-data semantics, resource constraints and limitations.
The Spark report now accepts an explicit scope from prepared configuration.

Actual validation:
- Full integration suite: 10 passed in 26.37 s (`tests_bounded_20261107.txt`).
- Added interruption-recovery test afterward; national-specific suite: 4 passed in
  1.79 s (`tests_national_resume_final.txt`). Tests cover real synthetic tile seams,
  cropped extents, misalignment, checkpoint tampering and preservation of partial runs.
- Cached 2015 then resumed 2020 run completed at
  `integration/data/bounded_validation_run1/`; no new downloads. Spark times 49.01 s
  and 41.92 s. Completed 2015 was skipped on resume; staging tables were removed.
- `integration/scripts/verify_bounded_validation.py` compared every column to the
  original pilot: 434,363 fine rows (21 columns) and 4,455 coarse rows (17 columns)
  per year, all PASS; float tolerance rtol 1e-10/atol 1e-5. Result:
  `integration/reports/bounded_validation_comparison.json`.
- After resume, every checkpointed output SHA256 was rechecked successfully.

National preflight only: 14 tiles, 168 tile-year jobs, 146,475,442,176 free bytes
at measurement; first pair R5_C25/1975 has about 16.2 million cells (area estimate).
See `integration/reports/national_bounded_preflight.json`. No national processing
or new downloads started. No validation jobs remain active. Old pilot data and ZIPs
are unchanged. Weeks 6–8 remain incomplete.

Next concrete step is the first bounded national pair, then inspect actual disk/time,
coverage and rejected-cell counts before scaling:

```sh
.venv/bin/python integration/src/national.py --config integration/config/india.json --output integration/data/national_run1 --download --max-pairs 1
```

Use the normal approval mechanism for network/Spark socket access if required.
Resume that run with the same arguments plus `--resume`; do not rerun the completed
validation subset. Per-pair free-space reserve is a guard, not a capacity guarantee.
National district attribution, cross-year common-valid masks and temporal/component
analysis are still pending. The runner uses local staging and Spark local[2], not HDFS.


## Resumed 2026-11-06: historical pilot validated

The checkpoint below is historical; its pending regression and temporal run are now
complete. All 10 tests passed in 15.86 seconds with Spark socket access (see
`tests_after_metadata_fix_socket_enabled.txt`). The initial sandbox attempt had nine
passes and one socket-permission failure, preserved separately.

`data/pilot_results/validation.json` reports PASS: 4,343,630 fine historical rows,
44,550 coarse historical rows, 44,550 cell-period transitions, and 349 district
summary rows. Spark finished in 72.69 seconds. Success marker, historical-only
periods, and all district scope/2021-vintage labels were independently inspected.
The successful log is `temporal_after_metadata_fix.log`. Existing outputs were preserved.

Added `scripts/build_pilot_handoff.py` for CSV summaries, a pilot report, and a
CRC/SHA256-verified root ZIP. It consumes saved results and refuses overwrites.
See `PILOT_REPORT.md` for findings and attribution. No spatial-review GeoJSON yet.

Next implementation milestone: bounded national three-product tile-year staging
and checkpointing, with seam/cropped-extent/missing-mask validation, followed by
resource review before execution. National processing has not started; weeks 6–8
remain incomplete. Current disk check showed about 135 GiB available.

## Previous saved checkpoint

Saved 2026-11-06 (Asia/Kolkata), at the user's explicit request to save progress and
resume later. Development stopped at this checkpoint. Weeks 6–8 are NOT complete.
The completed weeks 1–5 data and handoff remain unchanged.

## Completed in this session

- Added `analysis/config/pilot.json` with ten historical epochs (1975–2020), explicit
  rural/urban/centre classes, connectivity, lineage and growth thresholds. Projection
  epochs 2025/2030 are excluded from historical analysis.
- Downloaded the fixed geoBoundaries IND ADM2 district snapshot and provenance into
  `analysis/data/boundaries/`: ID `IND-ADM2-76128533`, represented year 2021, ODbL 1.0.
  The API advertises 736 units but the actual GeoJSON has **735 features**. Preserve
  that discrepancy in documentation; do not claim 736 processed districts.
- Implemented `analysis/src/districts.py`: 100 m centre-to-polygon assignment, stable
  IDs, deterministic shared-edge ties, rejection of overlapping district interiors,
  source hash/CRS validation and fixed boundary vintage across all years.
- Mapped **434,363 pilot cells**, with **zero unassigned cells and zero edge ties**.
  Six district intersections: Chikkaballapura (4,333), Kolar (13,432), Bangalore Rural
  (144,636), Bangalore (201,473), Ramanagara (48,791), Krishnagiri (21,698).
  These represent only district portions inside the pilot, NOT full district totals.
- Implemented `analysis/src/components.py` and `candidates.py`: deterministic 4/8-way
  urban components; overlap-based lineage; connection to pre-existing class-30 centres;
  positive growth on the stable baseline footprint; edge censoring and ambiguity flags.
- Ran the candidate screening into `analysis/data/pilot_candidates/`: **225 component
  events** across nine adjacent intervals plus 1975–2020. Counts: 155 boundary-censored,
  33 no-candidate, 30 independent-growth candidates, 1 absorption candidate and 6
  ambiguous lineages. These are overlapping period events, not counts of distinct towns.
- Ran sensitivity cases: 4-neighbour connectivity gives 40 growth and 22 absorption
  events; raising the 8-neighbour growth threshold from 10% to 25% gives 16 growth and
  1 absorption events. Results are method-sensitive and remain exploratory candidates.
- Added `analysis/src/temporal.py`: Spark historical transitions, growth deltas with
  safe zero baselines, concentration measures and district summaries, with footprint,
  uniqueness, conservation and Parquet round-trip checks. This script has NOT yet
  completed successfully; see the precise failure/fix below.
- Ten regression tests passed before the latest metadata fix. Saved result:
  `analysis/reports/tests.txt` (10 passed in 17.20 seconds).
- Added `analysis/scripts/plan_national.py` and generated a complete **672-source**
  India inventory (14 tiles × 12 epochs × four raster components: POP, SMOD,
  total built-up, NRES). All 672 URLs returned HTTP 200 in HEAD checks; advertised
  compressed size **6,220,776,281 bytes**. Only 48 are cached locally. This was an
  availability check, NOT a national raster download or processing run.

## Latest failure, diagnosis and applied fix

The first historical Spark run failed before writing its final output directory:
`AMBIGUOUS_REFERENCE: settlement_class` in the district SQL aggregation.

Root cause was **stale embedded Spark schema metadata in the Arrow district mapping**.
Arrow's `table.select()` kept `org.apache.spark.sql.parquet.row.metadata` from the
21-column analytical source. The physical Parquet had four mapping columns, but
Spark read it as the original analytical schema, causing duplicate/incorrect columns.

Applied fix:

- Added `mapping_table()` in `analysis/src/districts.py` to clear source schema
  metadata with `replace_schema_metadata(None)` before writing the mapping.
- Preserved the original attempt as `analysis/data/district_mapping_metadata_attempt/`.
- Regenerated `analysis/data/district_mapping/` successfully; its validation is PASS
  with the same 434,363 assignments and zero missing/tied cells.
- Extended the existing Spark regression in `analysis/tests/test_analysis.py` to
  write Arrow data with a deliberately stale Spark schema and confirm that Spark
  reads the corrected mapping's four columns and district value.

**The extended regression and full temporal pipeline have NOT been rerun after this
fix.** Do not describe the district SQL summaries or transition matrices as completed.
The failure log remains `analysis/reports/temporal.log`. There is currently no
`analysis/data/pilot_results/` directory.

## Exact next steps

Run from the GHSL project root. Use existing inputs; no need to redownload or rerun
weeks 1–5, district acquisition, corrected mapping, candidate screening or HEAD probes.

1. Run the updated regression suite, preserving the earlier log:

```sh
.venv/bin/python -m pytest analysis/tests -q > analysis/reports/tests_after_metadata_fix.txt 2>&1
```

2. Rerun historical Spark analysis against the corrected mapping, preserving the
   first failure log:

```sh
.venv/bin/python analysis/src/temporal.py > analysis/reports/temporal_after_metadata_fix.log 2>&1
```

Spark needs local sockets. The sandbox previously required escalation; approval
prefixes were requested for pytest and this temporal script. Use the normal tool
permission mechanism if required, not a silent workaround.

3. If another error occurs, inspect and fix it; preserve partial output. Existing
   output directories are intentionally refused, so use `--output` with a fresh run
   name after any failure that wrote files. When successful, verify `validation.json`
   and `_SUCCESS`, conservation, historical-only periods and district scope labels.
4. Prepare a documented pilot analysis report, source/ODbL attribution, candidate
   review files (a GeoJSON spatial-review export was considered but NOT implemented),
   and a reproducible handoff. Do not present morphological candidates as confirmed
   metropolitan absorption or causal findings.
5. Then generalize the three-product preparer to bounded multi-tile execution and
   checkpointing before attempting the national run. Reconcile tile seams, cropped
   built-up extents, country/district masks and missing-data policies.

## National resource planning

`analysis/reports/national_source_plan.json` estimates about **3.94 billion cell-year
records** at 100 m for all 12 epochs. Linear extrapolation from the measured pilot:

- Curated Parquet: about 48.78 GB.
- Staging Parquet: about 12.69 GB.
- Keeping both entire datasets in local storage AND HDFS: about 122.93 GB,
  excluding raw/clipped rasters, shuffle, temporary output and compression differences.
- Free disk at planning time: about 143.38 GB (decimal bytes).

These are planning estimates, not executed national results. A naive duplication of
all national intermediates risks exhausting this machine's disk. Implement bounded
staging/checkpointed tile-year processing and recheck free space before execution.
The current national population-only processor is NOT a national three-product runner.

## State when stopping

- No active national download or processing run was started.
- The failed Spark analysis and all acquisition/mapping/candidate/probe commands have
  finished. No HDFS PID files are present.
- Existing weeks 1–5 outputs and ZIP are unchanged.
- The new analysis code/data remain in the workspace; no weeks 6–8 handoff ZIP has
  been built and no completion claim is made.
