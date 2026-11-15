# GitHub delivery

Repository: [https://github.com/abhinavtyagiisc/GHSL_DataEngg-Scale](https://github.com/abhinavtyagiisc/GHSL_DataEngg-Scale).

Release: [v1.0.0](https://github.com/abhinavtyagiisc/GHSL_DataEngg-Scale/releases/tag/v1.0.0), with the weeks 1–3, weeks 4–5 and final weeks 1–8 handoff archives.

## Included

All phase source, configuration, tests, notebooks, environment pins, benchmark records,
validation summaries, final report/CSV/figure, regional checks, candidate Parquet and
review GeoJSON, original proposal and durable project notes.

The reviewed submission ZIP is provided as a release asset rather than storing
multiple generated archives in Git history. Earlier local archives are preserved.

## Kept locally

Over 60 GB of source/curated datasets and runtime files, the Python virtual environment,
HDFS blocks, JVM/JAR binaries, Spark event logs, temporary files, private conversation
archives and command history. No local credentials are required or included.

This is the full code/report deliverable, not a byte-for-byte backup of the workspace.
Raw-source URLs, hashes and reproduction notes are retained in the reports and release
archive metadata. For a full backup, copy the original data workspace separately.
`accepted_coverage_run1` depends on its symlink targets in `national_run1`; keep both.

## Review without processing data

Read README.md, the final report and REQUIREMENTS_REVIEW.md. Download the release ZIP
and run the standard-library verifier:

```sh
python3 phase3/scripts/verify_submission_archive.py GHSL_Weeks1_8_Accepted_Coverage_Final_v2.zip
```

Saved PASS records describe original executions; a clone does not imply new runs occurred.
PROJECT_CONTEXT.md is current continuity guidance. Historical reports remain for audit.
The local conversation archive is intentionally not published; AGENTS.md archiving
instructions apply when its registered local transcript is available.
