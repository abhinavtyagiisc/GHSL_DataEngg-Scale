# GHSL reproduction guide

**Analysis completed for 13 tiles across 156 tile-year combinations, excluding tile R8_C27.**

Start with `analysis/data/final_results/REPORT.md` for results, validation and
scope limitations.
The additional regional interpretation is in `phase3/reports/regional_validation/REPORT.md`.

## Analysis archive

`GHSL_Analysis_Results.zip` includes the reviewed results, regional
follow-up, source/config/test modules for all phases, environment pins, provenance,
and benchmark evidence.
Large raster archives, native/temporal Parquet data, JVM binaries, JARs and HDFS blocks
are deliberately excluded. This compact archive is a report/source handoff, not a
self-contained copy of the multi-gigabyte execution environment.

## Verify without rerunning computation

From the project root:

```sh
.venv/bin/python phase3/scripts/verify_handoff_archive.py GHSL_Analysis_Results.zip
```

The verifier uses only the Python standard library and can also be run with Python 3
on another computer. It checks ZIP CRC, manifest membership, every entry SHA256,
required source modules, Python syntax and coverage disclosure.

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
   intentionally prevent overwriting completed results. The adapter excludes tile R8_C27 and
   requires a checkpoint containing all 156 verified tile-year jobs.
5. Given copied full outputs, `phase3/scripts/final_analytical_review.py` reproduces the
   additional arithmetic/rule checks; it refuses to overwrite its existing report folder.

## Interpretation

Historical comparisons use 1975–2020 and a constant complete-data footprint. Projection
2025/2030 outputs are test epochs. District geometries are fixed 2021 boundaries.
NoData is never converted to zero. Candidate events overlap across periods, and
representative points are neither settlement boundaries nor confirmed town locations.
The regional Mumbai window moved by a documented coverage-only rule. Do not interpret
study-window summaries as administrative city totals or full-India population estimates.
