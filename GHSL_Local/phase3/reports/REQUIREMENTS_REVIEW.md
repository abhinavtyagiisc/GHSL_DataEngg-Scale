# Final requirement-to-evidence review

Reviewed 10 November 2026 against the original two-page proposal, professor feedback,
and the user-approved 156-job coverage decision. One person owns the complete delivery.

| Requirement | Executed evidence | Outcome / qualification |
|---|---|---|
| Three GHSL products, native alignment and 100 m/1 km aggregation | phase1/reports/PHASE1_COMPLETION_REPORT.md; integration/data/accepted_coverage_run1/validation.json | Passed; total and non-residential built surface retained alongside POP and SMOD |
| Pilot HDFS raw/cleaned/curated zones | phase1 and phase2 completion reports | Actual single-node HDFS executed and checked; national output is local Parquet |
| Reusable Spark integration and SQL | phase2/reports/PHASE2_COMPLETION_REPORT.md; integration/src/spark_integrate.py | Passed for all accepted epochs and tiles |
| Geospatial Spark engine | phase1/src and phase2/src; phase2 completion report | Apache Sedona 1.9.1 actually executed on pilot workloads |
| Explicit quantitative performance metrics | phase1/reports; phase2/reports; analysis/data/week8_handoff/national_pipeline_performance.csv | Repeated pilot latency/throughput/resource/partition comparisons; national timings are single observations, not cluster scaling |
| Ten historical epochs plus two projection tests | accepted_coverage_run1 identity/progress/validation | 156 accepted pairs across 13 tiles; projections excluded from historical conclusions |
| Rural-to-urban transition matrices | analysis/data/national_temporal/validation.json and periods | Ten periods passed on 3,280,884 common complete coarse cells |
| District summaries | analysis/data/national_districts/validation.json | Fixed 2021 districts; counts and values conserved; unmatched/overlap labels retained |
| Absorption and independent-growth candidates | analysis/data/national_candidates/validation.json | 108,804 overlapping events plus sensitivity analysis and review GeoJSON; not confirmed or unique towns |
| Case-study raw accuracy | analysis/data/national_case_studies/validation.json | 750 coarse cell-years: zero numerical differences and exact class agreement; Mumbai centre adjustment disclosed |
| Regional trajectories and population/built growth | phase3/reports/analytical_review/REPORT.md | Additional 26,870 cell-period arithmetic/class comparisons and 108,804 candidate-rule checks passed; regional examples supplied |
| Final report and review | analysis/data/week8_handoff/REPORT.md; phase3/reports/FINAL_ACCEPTANCE.json | Final figure inspected and all accepted-scope stages passed |
| Complete original national scope | accepted_coverage_run1/coverage.json | Approved deviation: R8_C27 excluded in all 12 epochs after fresh-source retries remained empty |
| Earth Engine export method | phase1/README.md; final report | Documented substitution: official JRC downloads; no Earth Engine execution claimed |
| Unattended run without correction | preserved failure logs and migration records | Original ideal was not achieved: engineering recovery and explicit scope revision were required; no clean uninterrupted first-run claim |

No required computation remains within the approved scope. External confirmation of
candidate settlements, restoring excluded coverage, Earth Engine execution and
multi-machine benchmarking are not claimed as delivered. The saved regional checks
establish processing and rule consistency, not external detection precision/recall.
