# Final execution and regional validation

All six stages passed for 13 tiles and 156 tile-year jobs. R8_C27 is excluded
across all 12 epochs. Historical comparisons use 1975–2020; 2025/2030 are projection tests.

## Results and evidence

- [Final analysis report](../analysis/data/final_results/REPORT.md): findings, scope and limitations.
- [Regional validation](reports/regional_validation/REPORT.md): 26,870 cell-period checks
  and 108,804 candidate-rule checks.
- `reports/FINAL_ACCEPTANCE.json`: final validation summary.
- `config/case_studies.json`: regional sampling configuration.
- `../analysis/data/regional_case_studies/`: 750 raw-raster/cell-year comparisons.

District boundaries are fixed to 2021. Regional windows are study areas rather than
administrative city limits; Mumbai uses a documented coverage-adjusted centre.
Numerical and rule checks establish processing consistency, not externally labelled
settlement-detection accuracy.

## Execution and recovery

The sequence is integration, temporal analysis, district summaries, candidate and
sensitivity screening, regional raw-data evaluation, then final reporting.
`scripts/complete_project.py` and `../analysis/scripts/run_national_workflow.py`
coordinate these stages; they require external data and checkpoints.
See [reproduction instructions](../REPRODUCTION.md) before running them.

Early Spark writes produced zero-byte Parquet files; the root cause was not proved.
The recovery implementation validates output in temporary storage, checks Parquet
footers and file hashes, then verifies atomic publication. Interrupted data and logs
remain preserved. A 20 GB reserve is checked before publication; concurrent writers
are prevented by locks. See `scripts/run_analysis_stage.py`,
`reports/identity_migration.json` and timestamped publication records.
The original goal of an uninterrupted unattended run was not achieved.
