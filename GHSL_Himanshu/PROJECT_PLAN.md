# Revised project plan — single-owner delivery

Updated 7 November 2026 following professor feedback. One owner implements the entire
proposal across POP, BUILT-S total/NRES and SMOD. All phases share the same spatial
contract and provenance. Sedona is used for spatial SQL, not merely installed.

## Phase 1 — weeks 1–3 (complete)

Acquire/validate all pilot products over 1975–2020, retaining 2025/2030 tests; verify
raw/cleaned/curated HDFS zones and native grids; execute Sedona spatial QA against an
independent reference; define and measure baseline quantitative performance. Deliver
reproducible environment pins, benchmark protocol/results and phase-1 handoff.

## Phase 2 — weeks 4–5 (complete)

Build/revalidate the reusable all-product Spark/Sedona integration workflow, preserve
native and aggregate outputs, enforce matching-year categories and missing-data policy.
Benchmark end-to-end ingestion/join/write throughput, shuffle/spill, resource use,
partition sensitivity and result equivalence. Incorporate lessons from phase 1.

## Phase 3 — weeks 6–8 (complete for accepted coverage)

Completed 13-tile execution with checkpointing and storage safeguards, transitions,
concentration, validated district attribution/SQL summaries and candidate lineage.
Sedona spatial execution and comparative benchmarks are delivered in phases 1–2;
national district attribution retains the independently validated raster-centre method. Evaluate accuracy using
case-study regions and sensitivity checks; report national throughput/resource metrics.
Deliver analytical outputs, final evaluation and reproducible handoff. Preserve and
diagnose the earlier failed national Parquet-write attempt before scaling.

## Rules shared across phases

- Data completeness and correctness are hard gates; speed does not override them.
- Quantitative performance definitions and workloads are declared before measurement.
- No phase is called complete from implementation alone; execution evidence is required.
- Each phase has a separate report and handoff. Existing artifacts remain preserved.
- Official JRC acquisition substitutes for Earth Engine exports and is explicitly
  documented; no authenticated Earth Engine execution is claimed.
- No claim of multi-machine distributed performance from Spark local execution.
- Update analysis/reports/PROGRESS_REPORT.md and COMMAND_LOG.md after each command.

## Final acceptance — 10 November 2026

All three phases complete for user-approved coverage: 156 verified tile-years, with R8_C27 excluded in all 12 epochs after unsuccessful fresh-source retries. Historical/district/candidate/regional analyses and final audits passed. Final report: analysis/data/week8_handoff/REPORT.md. Do not represent this as complete India coverage.
