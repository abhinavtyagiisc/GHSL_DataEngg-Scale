# GHSL India urban concentration and growth

A solo-delivered data engineering project integrating GHSL population, built-up surface
(total and non-residential), and settlement classes across historical epochs.

**Completed for the approved study footprint: 13 tiles × 12 epochs = 156 verified jobs.**
R8_C27 is excluded in all years after fresh-source retries returned no valid analytical
cells within the selected country-mask intersection. Results are not complete India coverage.

Phase handoff release assets are prepared locally; publication is pending. · [Team repository](https://github.com/abhinavtyagiisc/GHSL_DataEngg-Scale)

## Start here

- [Course report (PDF)](output/pdf/GHSL_Final_Project_Report.pdf) · [Editable Word report](output/docx/GHSL_Final_Project_Report.docx)
- [Presentation content (PDF)](output/pdf/GHSL_Presentation_Slide_Content.pdf) · [Structured slide content](output/pdf/GHSL_Presentation_Slide_Content.json)
- [Document submission notes](output/pdf/SUBMISSION_NOTES.md)

- [Final completion report](analysis/data/week8_handoff/REPORT.md)
- [Proposal requirements and evidence](phase3/reports/REQUIREMENTS_REVIEW.md)
- [Regional analytical review](phase3/reports/analytical_review/REPORT.md)
- [Submission and reproduction guide](SUBMISSION_README.md)
- [GitHub contents and data policy](GITHUB_DELIVERY.md)
- [Current project context](PROJECT_CONTEXT.md)

## Delivered results

- 624 validated source archives; native 100 m values retained with matching-year 1 km settlement classes.
- Ten historical epochs, 1975–2020; 2025 and 2030 retained as separate projection tests.
- Temporal analysis on 3,280,884 common complete coarse cells; ten transition periods.
- District summaries with count/value conservation and explicit unmatched/overlap categories.
- 108,804 overlapping candidate events with sensitivity checks; not confirmed or unique towns.
- Raw-raster regional checks over 750 coarse cell-years: zero observed numerical differences and exact class agreement.
- Additional 26,870 regional cell-period checks and 108,804 candidate-rule checks passed.

![Population and built-surface concentration](analysis/data/week8_handoff/national_concentration.png)

## Engineering phases

| Phase | Work | Evidence |
|---|---|---|
| Weeks 1–3 | All-product pilot ingestion, HDFS zones, Sedona spatial QA and baseline benchmarks | [Phase 1 report](phase1/reports/PHASE1_COMPLETION_REPORT.md) |
| Weeks 4–5 | Reusable Spark/Sedona integration and repeated end-to-end benchmarks | [Phase 2 report](phase2/reports/PHASE2_COMPLETION_REPORT.md) |
| Weeks 6–8 | Accepted-scope integration, temporal/district/candidate analysis and regional validation | [Final acceptance](phase3/reports/FINAL_ACCEPTANCE.json) |

The pipeline uses Apache Sedona 1.9.1 and Spark 3.5.6. Pilot HDFS and Sedona
benchmarks ran on a single machine; national processing uses local Spark and Parquet.
Official JRC acquisition substitutes for proposed Earth Engine exports. The Mumbai
regional check uses a disclosed coverage-adjusted window. The phase reports document
execution failures and scope changes. These benchmarks do not establish multi-machine scaling.

## Code and environment

Run project commands from `GHSL_Local/` after cloning the team repository.

`population/` contains the initial ingestion and shared raster utilities; `integration/`
contains the reusable join and bounded tile-year runner; `analysis/` contains temporal,
district and candidate analysis; `phase1/`, `phase2/`, `phase3/` contain phase-specific
execution, tests, benchmarks and acceptance evidence.

Use the pinned [phase 1 requirements](phase1/requirements-lock.txt) and phase READMEs.
A fresh clone contains code and compact results, not the original data workspace.
Do not run completion controllers against an empty clone: they expect documented raw
sources, boundary snapshots and completed checkpoints. Follow the reproduction guide
in a separate workspace; guards prevent overwriting saved outputs.

## Data and attribution

Sources: European Commission Joint Research Centre GHSL R2023A, POP/BUILT-S V1_0,
SMOD V2_0; geoBoundaries gbOpen country/district geometries. Preserve the attribution
and derived-data licensing information in the final report. No new code license is
asserted by this upload; obtain the owner's permission before redistribution.

## Existing team notebook

`DE_S_Project_Aug2026.ipynb` is preserved from this repository before the completed
GHSL project import. Imported implementation and evidence come from the 10 November
2026 snapshot, supplemented by the course report, editable Word report, presentation
content and their build scripts prepared on 15 November 2026.
