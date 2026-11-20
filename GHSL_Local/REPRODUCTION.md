# GHSL reproduction guide

**Complete for approved coverage: 13 tiles, 156 tile-years. R8_C27 excluded.**

Start with `analysis/data/final_results/REPORT.md`. Use
`phase3/reports/REQUIREMENTS_REVIEW.md` to trace proposal requirements and deviations.
The additional regional interpretation is in `phase3/reports/regional_validation/REPORT.md`.

## Preferred archive

`GHSL_Weeks1_8_Accepted_Coverage_Final_v2.zip` includes the reviewed results, regional
follow-up, source/config/test modules for all phases, environment pins, provenance,
and benchmark evidence. Earlier archives are preserved historical deliveries.
Large raster archives, native/temporal Parquet data, JVM binaries, JARs and HDFS blocks
are deliberately excluded. This compact archive is a report/source handoff, not a
self-contained copy of the multi-gigabyte execution environment.

## Verify without rerunning computation

From the project root:

```sh
.venv/bin/python phase3/scripts/verify_handoff_archive.py GHSL_Weeks1_8_Accepted_Coverage_Final_v2.zip
```

The verifier uses only the Python standard library and can also be run with Python 3
on another computer. It checks ZIP CRC, manifest membership, every entry SHA256,
required source modules, Python syntax, and the approved coverage disclosure.

## Reproduce or inspect results

1. Read each phase README and pinned requirements before installing anything.
   `phase1/requirements-lock.txt` records Sedona/Spark/Java-related Python versions;
   `phase1/runtime/jar_manifest.json` records external JAR provenance.
2. Saved final stage outputs in this workspace have PASS markers. Inspect them directly;
   do not restart controllers merely to review the project.
3. `integration/data/accepted_coverage_run1/pairs` uses relative symlinks to the preserved
   `integration/data/national_run1/pairs`. Keep both directories together when copying
   large data. The compact ZIP contains metadata, not these target datasets.
4. For a full computational reproduction, use a separate workspace, acquire official
   sources from the recorded manifests and follow phase READMEs. Existing-output guards
   intentionally prevent overwriting completed results. The accepted-scope adapter is
   specific to the approved R8_C27 exclusion and expects the verified 156-job checkpoint.
5. Given copied full outputs, `phase3/scripts/final_analytical_review.py` reproduces the
   additional arithmetic/rule checks; it refuses to overwrite its existing report folder.

## Interpretation

Historical comparisons use 1975–2020 and a constant complete-data footprint. Projection
2025/2030 outputs are test epochs. District geometries are fixed 2021 boundaries.
NoData is never converted to zero. Candidate events overlap across periods, and
representative points are neither settlement boundaries nor confirmed town locations.
The regional Mumbai window moved by a documented coverage-only rule. Do not interpret
study-window summaries as administrative city totals or full-India population estimates.

The analysis is complete within the approved 13-tile scope.

## Phase overview

Phase 1 (weeks 1–3) validates the pilot inputs, HDFS zones and Sedona spatial
operations, with declared benchmark methods. Phase 2 (weeks 4–5) validates reusable
integration and repeated end-to-end benchmarks. Phase 3 (weeks 6–8) delivers
accepted-coverage execution, temporal/district/candidate results and regional checks.
Each phase README provides commands; the requirements review maps results to the
proposal. Saved PASS records describe original executions, not new runs in a clone.

## Delivery and local files

Team repository: https://github.com/abhinavtyagiisc/GHSL_DataEngg-Scale.
No releases were listed in this team repository on 20 November 2026. The preferred
archive named above is a separate handoff; obtain it from the project owner if it
is not supplied alongside the repository. Do not assume a team v1.0.0 release exists.

The clone contains source, configuration, tests, dependency pins, notebooks, compact
results and validation/benchmark evidence. Large raw and curated datasets, HDFS
blocks, JVM/JAR binaries and the virtual environment remain external. Recorded source
URLs, hashes and environment manifests support reproduction. Preserve both
`accepted_coverage_run1` and its `national_run1` symlink targets when backing up full data.
Local continuity, assistant instructions, conversation archives and progress logs are
not part of the published deliverable. Packaging must not require these local files.

## Folder names and saved provenance

Current results use `analysis/data/final_results`, `settlement_candidates`,
`temporal_analysis`, `district_summaries`, `regional_case_studies`, and
`phase3/reports/regional_validation`. Older checksummed archives retain the names
`week8_handoff`, `national_candidates`, `national_temporal`, `national_districts`,
`national_case_studies`, and `analytical_review`, respectively. The archive verifier
accepts either layout. Saved execution logs/manifests and absolute paths describe
the original run workspace; they have not been rewritten as evidence of a new run.
When restoring large external outputs into a new clone, use the current folder names.
