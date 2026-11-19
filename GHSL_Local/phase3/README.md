# Completed — accepted coverage

See `reports/FINAL_ACCEPTANCE.json` and `../analysis/data/week8_handoff/REPORT.md`. All stages passed for 156 accepted tile-years; R8_C27 is excluded. The approved scope and regional sample adjustment are explicit in the report. Do not restart the preserved national run.

# Weeks 6–8 recovery and national execution

Authorized after phase 2 by the user on 7 November 2026. The preserved national
run completed one of 168 tile-years and failed on a zero-byte fine Parquet in
R5_C25/1980. The original cause is not established. The file remains zero bytes;
coarse and class outputs have readable footers. Do not delete the failed attempt.

The initial recovery attempt used the unchanged integration implementation and verified
sources, with an explicit Spark output-file cap of 250,000 records per Parquet file.
This bounds file size and avoids a single huge year file; it is a mitigation to test,
not a claim that the root cause has been proved. Original source/code fingerprints
remain enforced. The runner automatically moves unfinished pairs to `incomplete/`
and skips only verified completed checkpoints. A successful recovery still requires
full schema/key/coverage/conservation and exact persisted reread checks.

`run_recovery.py` runs one pending tile-year first, records the execution environment,
refreshes progress every 30 seconds, and rejects zero-length or unreadable checkpointed
Parquet files. Do not run concurrently with benchmarks or another national writer.
A later full run must inherit the same recorded Spark configuration. National analysis
and final handoff must wait for all 168 integrated pairs; pilot evidence is insufficient.

## Recovery revision after first retry

The capped-file retry also produced one zero-byte chunk (250,000 missing rows),
and the exact reread comparison stopped execution. Original root cause is still
unconfirmed. The revised runner writes Spark output in a system temporary directory,
requires full validation there, then checks every file SHA256 before and after atomic
directory publication into the project. Failed scratch data is retained; successfully
published scratch data is removed. Six national tests passed, including zero-byte
and copy-corruption rejection. The explicit identity migration verified every saved
completed output/source, preserved the previous code and identity, and changed only
national_integration.py's recorded implementation fingerprint. See reports/identity_migration.json.
Recovery attempts now have separate timestamped logs; reports/recovery_current.json
points to the active attempt. The original failed logs remain available.

## Current execution and completion gates

Revised R5_C25/1980 recovery PASSED: 16,201,044 native records, 162,763 coarse
records, zero rejected, 348.26 seconds for Spark startup/validation/write; 156 files
passed verified publication. The full national controller then resumed automatically.
Jobs vary in size; the remaining batch is expected to take many hours. Timing excludes
source acquisition and preparation and is not an end-to-end national ETA.

The remaining sequence is integration, temporal analysis, district summaries,
candidate/sensitivity analysis, independent regional evaluation and final handoff.
The regional configuration was declared before measurement in config/case_studies.json:
three approximate urban study windows and ten historical epochs; independent original
raster sums/classes must match saved national values. This tests numerical processing
accuracy, not precision/recall of candidates against external labels.

National analysis CLI calls now validate in system temporary storage, check Parquet
footers, verify every file hash before/after atomic publication, and preserve failed
scratch directories. A 20 GB free-space reserve is required before publication.
See scripts/run_analysis_stage.py. Direct stage invocations receive the same protection.
Current execution remains visible in reports/STATUS.json and
../analysis/reports/WEEK8_RUN_STATUS.json. Do not start a second writer.
