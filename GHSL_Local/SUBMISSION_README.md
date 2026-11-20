# GHSL project: final submission guide

**Complete for approved coverage: 13 tiles, 156 tile-years. R8_C27 excluded.**

Start with `analysis/data/week8_handoff/REPORT.md`. Use
`phase3/reports/REQUIREMENTS_REVIEW.md` to trace proposal requirements and deviations.
The additional regional interpretation is in `phase3/reports/analytical_review/REPORT.md`.

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
.venv/bin/python phase3/scripts/verify_submission_archive.py GHSL_Weeks1_8_Accepted_Coverage_Final_v2.zip
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

## Submission contents

Use the reviewed archive above for source, results and validation evidence. Include
only the final report and presentation requested by the course alongside it; retain
older drafts and duplicate exports locally. Check author placeholders in final
exports before submitting.

Do not add the local `.venv/`, `tmp/`, Python caches, editor backups or debug logs to
the submission. Retain dependency pins, source manifests, benchmark records and
validation reports needed to interpret and reproduce the results. Keep project
continuity and administration records in the working project. Follow course
requirements for AI-use disclosure and individual contribution statements.

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

## Report and presentation notes

The supplied PDF report has seven A4 pages, 10-point text and 2.5 cm margins; saved
format evidence is in `output/pdf/REPORT_FORMAT_VALIDATION.json`. Himanshu Arora is
listed; three other author fields remain placeholders and must be completed before
submission. Individual contribution forms and required disclosures remain separate.
The presentation PDF has 16 pages of copy-ready content; it is not an editable
PowerPoint deck. The Word report is editable; rendered Word pagination remains
unverified. Preserve the approved-coverage and methodological limitations in all exports.

Rebuild the report with `python analysis/scripts/build_final_report.py` using
reportlab 5.1.0; the original PDF inspection used PyMuPDF 1.26.6. Rebuilding an export
does not rerun scientific processing or update existing checksummed ZIP archives.
