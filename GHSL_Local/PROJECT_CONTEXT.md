# GHSL project continuity notes

Last updated: 2026-11-18 (Asia/Kolkata).

## Approved filename cleanup applied — 19 November 2026

Applied all 18 reviewed renames in team checkout, using national_integration.py
(user correction) and build_benchmark_report.py (confirmed unchanged suggestion).
Mapping: analysis/reports/FILENAME_REVIEW.md. Updated active imports, controller
commands, documentation, packaging code and notebook references. Preserved historical
reports/data and prior README changes. Original workspace source files unchanged.
Validation: all Python files parse; notebook JSON valid; 63 tests collected across
six suites without import errors; five handoff tests passed in 24.21s. No stale
active old filename references; scoped git diff --check passed. Full computational
suite not executed. No data processing, commit or push.
Next: review local changes; commit/push only if requested.

## Final script name approved — 19 November 2026

User approved finalize_national_results.py. Applied in team checkout analysis/scripts;
controller and test import updated, plus FILENAME_REVIEW.md. Five existing handoff
tests passed in 25.18s; scoped git diff --check passed. No other script renames,
processing, commit or push. User requested all suggested renames; 18 candidates
are recorded in team analysis/reports/FILENAME_REVIEW.md for review.
Next: apply additional renames only when selected/authorized.

## Handoff script rename and filename review — 19 November 2026

In team checkout, renamed analysis/scripts/finish_week8.py to
analysis/scripts/build_national_handoff.py; updated controller path and test import.
Existing five handoff tests passed (40.49s); scoped git diff --check passed.
Saved 18 optional Python filename suggestions in analysis/reports/FILENAME_REVIEW.md.
Existing README edits preserved; no processing, commit or push. Original workspace
script unchanged. User subsequently requested a better name; recommended
finalize_national_results.py, pending selection (not applied).
Next: apply chosen replacement and update references if requested.

## Main README simplified — 18 November 2026

Simplified team checkout `GHSL_Local/README.md`: shorter introduction/navigation,
main results, directory table, corrected root notebook link, and concise reproduction
and limitations sections. All local links resolve and scoped whitespace check passed.
No code or analysis README changes, tests, commit or push. Changes reside in
`/private/tmp/ghsl-team-cleanup-20261118`; review and commit/push if requested.


## Folder rename and cleanup — 18 November 2026

User requested folder `GHSL_Local` (formerly `GHSL_Himanshu`) and exact commit
message `cleanup` for the team repository abhinavtyagiisc/GHSL_DataEngg-Scale.
Renamed the project directory and updated the README command location. Preserved
historical path references below as history. Included the prepared README,
submission-guide and editor-backup ignore changes. Existing root team files are
unchanged. No scientific reruns or artifact regeneration. Publication verification
is recorded in the original workspace continuity after push.


## Team destination correction staged, commit denied — 18 November 2026

User clarified intended target is abhinavtyagiisc/GHSL_DataEngg-Scale, not the
workspace origin used for the previous push. Cloned team repository into
`/private/tmp/ghsl-team-cleanup-20261118`; applied README/submission changes under
`GHSL_Himanshu/`. Adapted ignore change because /tmp/ already excluded there.
Exactly three files staged; diff whitespace check and four ignore examples passed.
Commit execution approval was rejected by user. No team commit or push occurred.
Previous push 704702e to himarora1/ghsl-india-urban-growth remains intact.
Next: await authorization to commit/push staged team changes; do not retry denial.


## Team repository check-in prepared — 15 November 2026

Base import: completed 10 November snapshot b386e26408adc41724592fca66780227ebb932ff.
User now requests inclusion of existing report and presentation: output/pdf/ and
output/docx/, plus their three analysis/scripts/build_* generators. No PPTX requested.
README links and submission notes updated. Original team notebook preserved unchanged.
Destination: https://github.com/abhinavtyagiisc/GHSL_DataEngg-Scale.
All imported project files are under GHSL_Himanshu/; existing repository root files
are preserved. Run reproduction commands from this subfolder. Check-in is staged locally; no commit, push or release publication performed in this step.
Original workspace data, archives and private repository remain unchanged.
Report author placeholders remain intentional; Word pagination has not been visually verified.
No pipeline reruns. Next: review staged diff and CHECKIN_MESSAGE.txt, then commit/push
when requested and repository write access is available. Prior notes below are historical.

## GitHub publication — 10 November 2026

User requested GitHub upload and selected private visibility. Repository: https://github.com/himarora1/ghsl-india-urban-growth
Default branch main; first commit c282a2e. Release: https://github.com/himarora1/ghsl-india-urban-growth/releases/tag/v1.0.0.
Code/config/tests/notebooks, compact final results, benchmark and validation evidence
are tracked. All three phase handoff archives are release assets. Over60GB raw/curated
and runtime data remain local; conversation archive/command log and credentials excluded.
README.md and GITHUB_DELIVERY.md explain scope/reproduction. GitHub CLI authenticated
as himarora1 via keyring, Git uses SSH. No credentials copied. Publication set scanned
for common credential patterns and oversized files; 69 Python files parsed. Keep
original local data directories; GitHub repository is not a full data backup.
Next: share private access only with intended reviewers; no new analysis is needed.

## Conversation archive — 10 November 2026

User requests explicit conversation archiving after each step. Saved user-visible
messages from this exact local thread to analysis/reports/CONVERSATION_ARCHIVE.md;
source registry CONVERSATION_ARCHIVE_SOURCES.json. No hidden reasoning, system or
developer instructions, tool payloads or attachment contents exported. Source logs
may omit older messages; archive header states limits. Helper:
analysis/scripts/archive_conversation.py; --watch polls every10s with singleton lock.
progress_log.update now refreshes archive after each logged command. AGENTS.md tells
future sessions to refresh after decisions/steps and before final replies. Read current
PROJECT_CONTEXT.md first, archive as historical reference. Filter/partial-record and
idempotent refresh checks passed. Project analytical outputs and final ZIP unchanged.

## Final follow-up complete — 10 November 2026

Reviewed original proposal and added regional analytical validation/interpretation:
26,870 cell-period class/delta/growth comparisons and all108,804 candidate status-rule
checks passed, no mismatches. Evidence phase3/reports/analytical_review/. This does not
establish external ground truth. Added REQUIREMENTS_REVIEW.md and SUBMISSION_README.md;
explicitly disclose original unattended-run objective required engineering recovery.
Preferred v2 archive includes all phase source/config/test dependencies and environment
pins, plus final analytical evidence. Standard-library verify_submission_archive.py
checks CRC, everySHA, membership, safe paths, source syntax and required modules.
Final v2 archive verified: 192 files, 11,861,055 bytes; all eight archive checks PASS. Receipt: phase3/reports/FINAL_ARCHIVE_V2_VALIDATION.json. Original artifacts preserved. No remaining required tasks for approved scope.

## PROJECT COMPLETE — accepted coverage, 10 November 2026

All three phases complete within the explicitly approved reduced footprint: 13 tiles,
156 verified tile-years, 624 source archives. R8_C27 excluded all 12 epochs; original
national_run1 and failures preserved. accepted_coverage_run1 is a symlink view and
requires original pair data to remain in place. Do not restart downloads/controllers.
All six stages PASS; controller session 48684 exited 0. Temporal common mask:
3,280,884 coarse cells, ten periods; 13,743 additional cells excluded for completeness.
District counts/values conserved; 108,804 overlapping candidate events (not unique towns).
Regional raw checks: 750 coarse cell-years, zero numeric differences, exact class agreement;
Mumbai window coverage adjustment documented. Figure visually reviewed and PASS.
Acceptance: phase3/reports/FINAL_ACCEPTANCE.json. Report:
analysis/data/week8_handoff/REPORT.md. Preferred delivery:
GHSL_Weeks1_8_Accepted_Coverage_Final_v2.zip (reviewed archive); original automated
GHSL_Weeks1_8_National_Handoff.zip retained. Detailed archive verification receipt:
phase3/reports/FINAL_ARCHIVE_V2_VALIDATION.json. Large data remain local, not in compact ZIP.
Tests this completion: 7 accepted-scope/publication/handoff regressions passed25.82s;
additional coverage-disclosure packaging test passed27.09s. Prior phases unchanged.
Next: submit/review the final report and archive. No processing remains for accepted scope.
Any restoration of excluded geography or external candidate ground-truth validation is
new scope; do not silently broaden or claim those are complete.

## Analysis milestone and regional window correction — 10 November 2026

Temporal, district and candidate stages passed and were published. Regional check initially failed because original Mumbai window contains no cells in the retained country mask (point 3.61 km outside). Original config and failure logs preserved. Repositioned only Mumbai centre by nearest full 5x5 historical-common-coverage rule (30-cell search, deterministic ties), shift 8.06 km; no comparison outcomes used. Delhi/Bengaluru unchanged, all tolerances unchanged. Evidence phase3/reports/case_study_coverage_revision.json. Controller resumed in session 48684; skips passed stages and reruns regional check before handoff.

## Accepted reduced coverage — 10 November 2026

User explicitly authorizes ignoring unresolved datasets and completing project on verified inputs. Scope is 13 tiles × 12 epochs = 156 pairs; R8_C27 excluded all years. Original national_run1 remains preserved/incomplete. New accept_verified_scope.py rehashes all completed outputs/raw sources and constructs accepted_coverage_run1 using pair symlinks plus explicit coverage/original identity evidence. Controller now gates this audit before temporal, district, candidate, regional evaluation and handoff. Coverage warnings propagate to each published stage and final report. Do not redownload excluded inputs or claim full India coverage. Seven accepted-scope/publication/handoff tests passed in 25.82s. Controller launched in managed session 60548, PID 99989, initially accepted_scope hash audit. All 156 checkpoint hashes passed fresh audit; accepted_coverage_run1/_SUCCESS exists for accepted scope only. Temporal analysis running, controller session 60548. Coverage-disclosure packaging regression additionally passed in 27.09s. Temporal stage passed: 3,280,884 common complete coarse cells, 13,743 excluded from common mask, ten periods. Published analysis/data/national_temporal; district processing running. Remaining district/candidate/regional/handoff validation pending.

## Deferred pass finished — 10 November 2026, 01:38 IST

Current check: controller FAILED and lock free. 156/168 jobs verified complete; all other tiles succeeded. All 12 R8_C27 epochs freshly downloaded and retried, each UNRESOLVED with the same no-valid-analytical-cells error. See integration/data/national_run1/deferred.json and deferred_validation.json. No national success marker or downstream completion claimed. Do not restart unchanged or repeat downloads; next inspect the mask/source coverage discrepancy and implement explicit, tested no-coverage accounting if justified, preserving all completed checkpoints.

## Deferred retry authorized — 10 November 2026

User requests postponing R8_C27 and any identical empty-analytical-cell failures, completing other pairs, then reacquiring deferred sources and retrying. Implemented --defer-empty in national.py and enabled in week8 controller. deferred.json persists states DEFERRED/RESOLVED/UNRESOLVED. Fresh source copies go under population/data/raw/*/deferred_retries/; originals and failed attempts retained. Only exact no-valid-analytical-cells ValueError is deferred; other errors still stop. Any unresolved pair prevents national _SUCCESS and downstream stages. Seven national regressions passed in 2.72s. Prior code/identity and migration receipt in phase3/reports/*deferred_retry*. Resume verifies all 120 saved checkpoints before new processing. Restart launched in managed session 32999; controller PID 97462. Next: check active controller, remaining pass, fresh-source retry outcomes; never label skipped jobs complete.

## Verification stopped — diagnosed 10 November 2026

Stopped 9 November at 22:56 IST after 120/168 verified pairs. Controller FAILED, ownership lock free. R8_C27/1975 preparation contains 1,502 country-mask cells, all NoData in POP, BUILT_S and NRES (zero valid pixels). spark_integrate.py rejects an epoch with no valid analytical cells. This is a missing-coverage edge case, not a GPT-token stop; raw archives validated. About 83.6 GB free at diagnosis. Completed checkpoints preserved. No restart or validation bypass performed. Next: independently verify raw coverage and implement/test explicit all-NoData tile-year handling through integration and downstream acceptance before controlled fingerprint migration and resume. Failure log: analysis/reports/week8_integration_1794203755895955000.log. Previous ETA no longer applies while stopped.

## ETA update — 9 November 2026, 09:26 IST

Live controller RUNNING, 90/168 complete, R7_C26/2005 active. About 61% of native-cell workload done. Recent wall-clock throughput across 6/12/24 jobs implies 14–14.4 hours remaining; planning range 14–18 hours for integration/verification only. Downstream analyses/evaluation/handoff remain additional and unmeasured at national scale. Evidence: phase3/reports/ETA_ESTIMATE_20261109.json and eta_observations_20261109.json. Existing process unchanged; do not duplicate.

## Unattended continuation requested — 8 November 2026

User requests that the existing verification continue without further progress checks or messages; report updates may be deferred. Confirmed controller RUNNING with ownership lock held, 26/168 checkpoints complete and R6_C25/1985 active. Existing controller proceeds automatically through remaining stages and retries qualifying transport failures up to five times. Preserve validation failure stops and existing checkpoints; do not duplicate or restart a live writer. Execution is a managed process, not guaranteed to survive computer sleep/shutdown or environment termination.

## ETA requested — 8 November 2026, 09:18 IST

User requested an ETA during active completion work. At measurement, 17/168 jobs
were verified; remaining native workload estimated at 3.727 billion cell-years using
country-mask intersection area per tile. Aggregate observed Spark throughput was
36,713 cells/s, implying 28.2 remaining integration hours before other work.
Planning estimate: 36–60 more uninterrupted hours, roughly evenings 9–10 November IST.
This is not a deadline/confidence interval: only two tile sizes observed; larger tiles,
downloads/preparation, analysis and review add uncertainty. Multi-hour wall-clock gaps
exceed recorded Spark durations; pauses can substantially extend calendar completion.
Evidence and calculation: phase3/reports/ETA_ESTIMATE.json, eta_observations.json and
eta_wall_clock_observations.json. ETA also added to main progress report. Continue the
existing controller and refine the estimate after materially different tile sizes run.

## First complete national tile — 8 November 2026

R5_C25 completed all 12 epochs (1975–2030), with 194,412,528
validated native cell-years and 1,953,156 coarse cell-years.
Saved per-pair reports and success markers reviewed; no processing rerun.
See phase3/reports/first_complete_tile.json. Projection years remain separate tests.
The controller has moved to R5_C26; 13/168 jobs were verified at this check.
Existing controller session 35965 and progress watcher 20588 continue; no duplicate
writer launched. Check actual checkpoint/status files for current counts.

## Active monitoring — 8 November 2026

Confirmed existing controller and integration locks held; did not launch duplicate work.
Added phase3/scripts/watch_progress.py (managed session 20588): read-only reporter
refreshes an active-job description and per-tile completed-year table in the main report
every 30 seconds under the existing report lock. This displays preparation/integration/
publication progress while retaining verified checkpoints as the sole completion source.
Actual report rendering checked. Computation remains in controller session 35965.
Monitor current status/checkpoint rather than relying on historical counts below.

## Resume on 8 November 2026 — national batch restarted

Four national pairs completed (R5_C25, 1975/1980/1985/1990). Prior batch stopped on
JRC DNS resolution failure while acquiring 1995 POP, not on output corruption.
Both ownership locks were free. JRC 1995 archive HEAD retried outside sandbox:
HTTP 200, Content-Length 16,285,780. No completed work rerun.

Added orchestration-only transport retries: at most five, 15–60 second backoff;
only failed integration requests ConnectionError/timeout/chunked-transfer errors.
Data correctness, 404 and certificate failures do not retry. Unit test passed in
0.03 s (phase3/reports/network_retry_tests_20261108.txt). Core fingerprinted national
implementation unchanged. Final handoff snapshot regression from prior turn verified:
four tests passed in 29.96 s (final_handoff_snapshot_tests.txt).

Controller restarted in managed execution session 35965. Read phase3/reports/STATUS.json
and analysis/reports/WEEK8_RUN_STATUS.json for current PIDs and logs. Next pair is
R5_C25/1995; verify actual checkpoints. Do not launch a duplicate writer. Pipeline
continues through national analysis, regional raw-raster evaluation and handoff;
actual national outputs and final visual review are still required for completion.

## Phase 2 complete; phase 3 authorized (2026-11-07)

User requested completion of the remaining project, in phase order. Phase 2 COMPLETE:
three actual Sedona regressions passed (35.25 s); 12-epoch HDFS integration passed
(171.61 s), 5,212,356 fine / 53,460 coarse records, zero rejected/incomplete trajectories.
HDFS healthy, retrieved outputs, services stopped. Independent all-column comparison
passed on fine/coarse/95 SQL rows with zero observed numerical differences.
All 16 benchmark trials passed persisted comparisons. Medians: key local2/8 4.1788 s;
Sedona local1/8 7.8757 s; local2/8 7.4264 s; local2/32 8.9902 s. All performance
targets passed. Chart visually reviewed. See phase2/reports/PHASE2_COMPLETION_REPORT.md.
GHSL_Phase2_Weeks4_5_Handoff_v2.zip: 132 files, 49,381,180 bytes, CRC/SHA256 verified;
phase2/_SUCCESS and reports/HANDOFF_VALIDATION.json PASS. Preserve completed outputs.

Phase 3 controller: phase3/scripts/complete_project.py gates one-job recovery, then
national integration/temporal/district/candidate/handoff stages. Initial capped-file
recovery FAILED: one zero-byte Parquet chunk caused exactly 250,000 missing rows.
Original cause remains unconfirmed. Both original and capped-file attempts preserved.

Implemented national.py revision: Spark writes/validates in a system temporary
folder, verifies every Parquet footer, copies with per-file SHA256 checks, atomically
publishes the directory and rechecks hashes. Failed scratch folders are retained;
only successfully published scratch is removed. Six preparation/resume/publication
tests passed in 2.34 s (phase3/reports/publication_tests.txt). Explicit identity migration
verified the one completed pair's 34 files and all source hashes, preserved old code
and identity, and changed only national.py's implementation fingerprint. Evidence:
phase3/reports/identity_migration.json and national_before_atomic_publication.py.

REVISED RECOVERY PASSED (R5_C25/1980): 16,201,044 fine / 162,763 coarse,
zero rejected, 348.26 Spark seconds, 156 files verified and published. Recovery.json
PASS. Full national completion controller automatically launched; check
phase3/reports/STATUS.json and analysis/reports/WEEK8_RUN_STATUS.json for active
PIDs/stage/log. Do not start another writer. Last verified count 2/168; full processing
will take many hours. No repeated resume needed while controller remains alive.

New remaining gates: three predeclared case-study windows (Delhi/Mumbai/Bengaluru),
all ten historical epochs, independent raw-raster sums and classes vs saved results.
Implemented phase3/scripts/evaluate_regions.py and config/case_studies.json. This is
numerical processing accuracy, not external candidate ground-truth precision/recall.
complete_week8.py includes the evaluation before final handoff; final packager requires
its PASS marker when completed revised phase 2 is present and includes its evidence.
Five regional-reference/handoff fixture tests passed in 30.33 s.

Downstream temporal/district/candidate CLI calls now use phase3/scripts/run_analysis_stage.py:
validate in system temporary storage, check footers, SHA256-copy verification and
atomic publication, 20 GB reserve, preserve failures. Direct CLI dispatch protects
already-running controllers with earlier command lists. Three regional/publication tests
passed in 1.23 s. Actual candidate pipeline publication smoke test on saved real pilot
passed: 225 events, every event/sensitivity count and CSV/Parquet/GeoJSON byte matched
preserved validated results. See phase3/reports/candidates_publication_comparison.json.

Final national packager includes completed Sedona/benchmark evidence, publication
provenance, regional evaluation and observed per-pair throughput with timing caveats.
Next: monitor existing national batch, handle any failures without overwriting evidence,
then verify all analysis/evaluation/handoff gates and visually review final figures.
Full project remains incomplete until actual national results and final review pass.
Continue updating main progress report and command log after every execution.

## Revised phase 1 completed (2026-11-07)

Completed the solo-owned all-product weeks 1–3 scope including real Apache Sedona and
quantitative benchmarks. Read `phase1/reports/PHASE1_COMPLETION_REPORT.md` and
`phase1/README.md`. `phase1/_SUCCESS` and PHASE1_VALIDATION.json are PASS.

Verified all 48 cached source archives (SHA256/CRC), 48 clipped rasters and actual
HDFS zones: retrieved raw/cleaned/curated, compared all source hashes and 132 prepared/
curated files, health passed, services stopped. No HDFS PID files remain.
Three contract tests passed. Independent Arrow aggregation matched every coarse cell
for population/total-built/NRES and matching-year class/counts over all 12 epochs;
maximum observed numeric differences were zero.

Apache Sedona 1.9.1 + Spark 3.5.6/Scala 2.12/Java 17: country coverage, parent geometry,
indexed district spatial join and persisted mapping validated on 434,363 pilot cells.
Exact independent-reference agreement, no missing/duplicate/mismatched assignments.
Final accepted benchmarks: `phase1/reports/sedona_local1_run3/` and
`phase1/reports/sedona_local2_run1/`; three sizes, one warmup and five measured
repetitions each; every trial executed 17 tasks. Full-pilot medians 2.8583 s/1.5141 s
(one/two workers), ratio 1.8878; all declared latency/throughput/memory targets passed.
RSS, CPU, task runtime, GC, shuffle/spill and raw repetitions retained in reports.
Chart reviewed visually. Benchmark first two single-worker attempts are explicitly
invalidated for caching/task-group measurement issues; preserve them, do not cite them.

Handoff `GHSL_Phase1_Weeks1_3_Handoff.zip`: 226 files, 49,867,294 bytes,
CRC/SHA256 verified; contains all 48 clipped rasters and 36 staging Parquets plus code,
reports and provenance. Full raw source ZIPs, HDFS runtime and JVM/Python binaries are
excluded; manifests/reproduction instructions included. No later phase started.

Next only when user requests phase 2: use PROJECT_PLAN.md and validated phase-1 data
to implement/revalidate the reusable all-product Spark/Sedona integration and broader
end-to-end benchmarks. Phase 3 national failure remains historical/preserved and must
be diagnosed before resuming national execution. Official JRC acquisition instead of
GEE exports and single-machine execution remain explicit documented deviations.
Continue updating both progress report and command log after every command.

## Revised user scope — phase 1 first (2026-11-07)

User now owns the entire project alone and requests three sequential deliverables:
weeks 1–3, weeks 4–5, weeks 6–8. First complete revised weeks 1–3 for ALL GHSL
products, including professor feedback: real Apache Sedona integration and explicit
quantitative performance benchmarks. Do not resume phase 3/national processing now.

Earlier national controller is FAILED and both locks are free. R5_C25/1980 failed
on a zero-length Parquet output; preserve its files/logs. R5_C25/1975 remains complete.
New workspace: `phase1/`, with README and AGENTS. Main submission progress report
was rewritten to reflect revised phases. `progress_log.py` now uses phase-1 scope.
Next: pin compatible Sedona/Python/JAR dependencies, execute spatial QA and repeated
benchmarks, audit all 48 cached source archives/prepared inputs and actual HDFS zones,
then deliver a verified phase-1 report/handoff. Earlier context below is historical.

## Final-handoff validation while national processing runs (2026-11-07)

National controller remains active; inspect WEEK8_RUN_STATUS.json and checkpoint for
latest counts. Added `analysis/tests/test_week8_handoff.py`; 3 tests passed in 42.82 s.
Tests use synthetic fixtures under `analysis/data/packaging_test_fixture/`, not national
results. They exercise ZIP/checksum creation and rejection of changed source files or
district totals. Final auditor now also rejects missing epochs, duplicate/empty tile
inventories and conflicting source hashes. Integration code/checkpoint identity unchanged.
Saved log: `analysis/reports/tests_week8_handoff.txt`. These tests do not establish
actual national completion. Continue the active run; do not launch another processor.

## National continuation launched (2026-11-07)

Renewed permission received. District end-to-end pilot validation PASS: independent
comparison matched all 349 original district/year/class rows and totals, no coverage
exceptions. Evidence: `analysis/reports/national_districts_validation_comparison.json`.

A detached shell launch did not create a status file; no success was claimed.
Started `analysis/scripts/complete_week8.py` in managed execution session 13820 instead.
`analysis/reports/WEEK8_RUN_STATUS.json` now records RUNNING, controller/child PIDs,
stage, command and detailed log. Inspect that file and runtime before any restart.
Do not start a second writer. National integration resumes its completed checkpoint;
controller advances through temporal, district, candidate and final handoff stages
only after previous stages succeed; records FAILED and stops on errors.

`analysis/scripts/progress_log.py` updates COMMAND_LOG.md and PROGRESS_REPORT.md at
command start/end and refreshes the progress report every 30 seconds during long
jobs. National count comes from the actual checkpoint. Full week 8 is not complete.
A managed process is not guaranteed to survive session/environment shutdown.

## Live reporting and renewed permission (2026-11-07)

User approved both previously denied execution actions. District fixture validation
was launched; check `analysis/reports/national_districts_validation.log` and its
success marker before claiming completion. After EVERY command, update both
`analysis/reports/PROGRESS_REPORT.md` (plain-language latest status) and
`analysis/reports/COMMAND_LOG.md` (detailed command history). Root AGENTS.md updated.
National checkpoint remains 1/168 as last checked.

## Submission-ready report (2026-11-07)

At the user's request, created `analysis/reports/PROGRESS_REPORT.md`: a plain-language
report with milestone status, verified results, limitations, remaining work and an
evidence index. Updated the technical `analysis/reports/PROGRESS.md` to point to it.
Figures checked against saved JSON validation/checkpoint records and test logs; no
processing/tests rerun for this writing task. National completion remains 1/168 jobs;
previously denied execution actions still require renewed permission.

## Latest status and command logging (2026-11-07)

User requires progress logging after every command. Read and maintain
`analysis/reports/COMMAND_LOG.md`; root AGENTS.md now records this instruction.

First national pair R5_C25/1975 completed with PASS; checkpoint contains 1/168 pairs.
Spark duration 443.75 s. Exact row/disk statistics are in the command log and
`integration/data/national_run1/pairs/R5_C25_1975/spark_validation.json`.
The first-pair process exited. Two further execution requests were denied by the
user's permission prompt: district fixture validation and national continuation.
They DID NOT RUN. No national or analysis jobs currently remain active.

National temporal fixture validation passed (4,455 common complete coarse cells,
10 periods, zero excluded). Array candidate results matched every original pilot
primary/sensitivity count. Nine new unit regressions passed. National district
end-to-end validation is still pending permission; its implementation is not verified
complete. Added `analysis/scripts/complete_week8.py` controller and `finish_week8.py`
final auditor/packager; syntax checked but NOT launched or end-to-end verified.
Do not use the controller to bypass the denied district/continuation actions.

Next: obtain renewed permission for national continuation and district validation,
run/verify those, then launch the sequential remaining analysis/handoff workflow.
Full week 8 is not complete; national completion must never be inferred from the
successful first pair or the pilot fixture. Earlier RUNNING notes below are historical.

## Active full weeks 1–8 completion (2026-11-07)

User explicitly requested completing everything remaining through week 8. Original
proposal re-read: weeks 6–8 require India-wide transitions, district summaries,
absorption/independent-growth candidates, and national pipeline execution.

Actual national first pair is RUNNING via `integration/src/national.py` with
`--config integration/config/india.json --output integration/data/national_run1
--download --max-pairs 1`. Log `integration/reports/national_first_pair.log`.
Four R5_C25/1975 source archives downloaded and CRC/SHA checked; Spark integration
is in progress, not yet claimed successful. Do not start another writer to this run.
After it finishes, inspect checkpoint and resource use, then resume remaining pairs.

Added national analysis modules under `analysis/src/`: `national_temporal.py`
(common complete historical coarse mask + Spark transitions), `national_districts.py`
(native centre district attribution with explicit unmatched/overlap labels + Spark
SQL summaries), and `national_candidates.py` (array-based cross-tile components).
Nine new regressions passed in 20.76 s; national temporal end-to-end pilot fixture
validation currently running (`analysis/reports/national_temporal_validation.log`).
No national analytical conclusions or week 8 completion claimed yet.

Installed pypdf 7.0.0 to read proposal, SciPy 1.18.1 for component labelling and
Matplotlib 3.11.2 for final figures. Existing original outputs are preserved.

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

## Latest resume: historical pilot validated (2026-11-06)

Resumed at user request. The schema fix now passes all 10 analysis regression tests
(15.86 seconds, socket-enabled run); the sandbox-only attempt failed on Spark local
socket permissions and is retained. Full temporal Spark analysis PASS in 72.69 seconds:
4,343,630 fine historical rows, 44,550 coarse historical rows, 44,550 transitions,
and 349 district/year/class summary rows. Outputs: `analysis/data/pilot_results/`.
Independently checked `_SUCCESS`, historical-only periods and district scope/vintage.
See `analysis/reports/PROGRESS.md` for logs and `analysis/reports/PILOT_REPORT.md`.

Added a no-overwrite handoff builder and CSV summary exports. Delivered
`GHSL_Weeks6_8_Pilot_Handoff.zip`: 190 files, 4,238,206 bytes; archive CRC and
every manifested file SHA256 passed. All three CSV row counts match source Parquet.
Packaging initially encountered Decimal sorting serialization; fixed using string
serialization for sorting and preserved the attempt directory/log. Final evidence:
`analysis/reports/handoff_build_final.log`. National execution has
not started. Next: bounded multi-tile three-product execution/checkpointing and seam,
cropped-extent and mask validation. Weeks 6–8 remain incomplete. Preserve all pilot
outputs; do not repeat completed processing. Older pending-test statements below
are historical and superseded by this update.

## Current resume point: weeks 6–8 checkpoint, saved at user request

The user authorized starting weeks 6–8 and then explicitly asked to save current
progress for later resumption. Development stopped at this checkpoint on 2026-11-06.
**Read `analysis/reports/PROGRESS.md` next** for full state and exact resume commands.
Weeks 6–8 are in progress, not complete; weeks 1–5 remain complete and unchanged.

Completed this session: a provenance-tracked 2021 geoBoundaries district snapshot;
434,363 pilot cell assignments across six district intersections (zero missing or
tied assignments); candidate-screening code and 225 period/component events with
boundary/lineage flags and sensitivity checks; and a 672-archive national three-product
inventory. All 672 URLs passed HEAD checks (6,220,776,281 advertised compressed bytes).
No national raster processing or bulk national download was started.

The historical Spark analysis is implemented in `analysis/src/temporal.py` but its
first run failed on an ambiguous settlement_class column. Diagnosed stale embedded
Spark schema metadata carried through Arrow projection into the district mapping.
Fixed `analysis/src/districts.py` with `replace_schema_metadata(None)` and regenerated
`analysis/data/district_mapping/` successfully. Preserved the old mapping in
`analysis/data/district_mapping_metadata_attempt/`. Added a Spark regression for the
metadata bug. **The updated test and full temporal run are still pending.** Prior
tests passed 10/10 before this latest fix; do not claim those results verify the fix.

Next actions: run the updated `analysis/tests`, then rerun `analysis/src/temporal.py`
using fresh log filenames as specified in PROGRESS.md. There is no pilot_results
directory yet. Finish validation and pilot reporting before generalizing national
three-product execution. Candidate counts are exploratory overlapping period events,
not confirmed or unique-town counts; district figures are pilot intersections only.

Resource warning based on measured planning: duplicate national staging+curated data
in local storage and HDFS would use roughly 122.93 GB before raw files/shuffle, against
about 143.38 GB free at planning time. National execution needs bounded staging and
checkpointing. No HDFS PID files or active analysis jobs remain at the checkpoint.

## Completed milestone: weeks 1–5 three-product pilot

On 2026-11-06 the user explicitly requested completion of the first five weeks.
Read the original proposal PDF: weeks 1–3 require all three pilot products and HDFS;
weeks 4–5 require a reusable Spark three-product join, not just population.
Completed that work under `integration/`, retaining all prior population artifacts.

- `integration/config/pilot.json`: same Bengaluru rectangle and all 12 epochs.
- Acquired 48 official source archives (12 POP, 12 SMOD, 12 BUILT-S total and
  12 BUILT-S NRES), 636,093,006 bytes, with ZIP CRC/SHA256 provenance. Shared cache
  under `population/data/raw/`; the new source manifest is
  `integration/reports/download_manifest_full.json`.
- Prepared 48 clipped GeoTIFFs and 36 independent staging Parquet files under
  `integration/data/prepared/`. All product/epoch masks and native grid alignment
  verified, and the pilot is inside the retained India boundary.
- Important source detail: built-up R8_C26 has 9,000 columns and x-origin 7,059,000,
  whereas POP/SMOD span the full tile from 6,959,000. Grids align, but source extents
  differ. `integration/src/prepare_inputs.py` uses coordinate windows, not equal
  source array dimensions. It has an independent grid contract under integration/config.
- `integration/src/spark_integrate.py`: reusable Spark validation, bidirectional
  coverage checks, native fine join, matching-year class inheritance, conservative
  coarse aggregation, Spark SQL class summaries and every-column Parquet round trips.
- **Actual HDFS/Spark run PASS:** 5,212,356 complete 100 m records, 53,460 coarse
  records, zero rejected cells and zero incomplete trajectories. Every epoch now has
  real settlement, population, total built-up and NRES values. Earlier notes about
  missing built-up/non-2020 settlement apply only to the older population outputs.
- Seven new integration regressions passed (five Spark/value tests plus two
  cropped-grid/misalignment tests), with saved logs. Prior population tests were
  not rerun because their implementation was unchanged in this task.
- HDFS root `/ghsl/weeks1_5/bengaluru_run1/` contains actual raw/cleaned/curated zones.
  Spark 3.5.6 local[2] execution and validation took 134.46 seconds. HDFS health
  passed (one DataNode, replication one); services stopped after completion.
- Downloaded final dataset: `integration/data/curated/grid_year/`, containing
  `analytical_100m/`, `summary_1km/`, `sql_class_summary/` and `_INTEGRATION_SUCCESS`.
- Entry points: `integration/README.md`, `integration/reports/COMPLETION_REPORT.md`.
  Final builder verified retrieval and produced the executed read-only notebook and
  root archive `GHSL_Weeks1_5_Complete_Handoff.zip` (48,693,372 bytes, 82 files).
  Package CRC, required files, Python source compilation and all four notebook-cell
  outputs passed the final audit. Cached acquisition also reran successfully against
  all 48 saved hashes. No HDFS PID files remain. Notebook cells are executed
  by the Python builder, explicitly not a Jupyter/Colab kernel run.
- The only acquisition-method deviation remains official JRC download instead of
  GEE export. No Earth Engine authentication/export execution is claimed. Raster
  extraction is local; Spark joins/aggregation/storage run against real local HDFS.

Next work is weeks 6–8: temporal settlement transitions, district attribution,
metropolitan absorption/independent growth, and a nationwide **three-product** run.
The existing India-ready processor currently covers population plus configured
settlement maps; it is not a completed nationwide three-product integration.
Do not rerun completed pilot jobs or overwrite outputs just to restore context.
The user's current scope is first-five-week completion, not national execution.

## Previous resume point: population extension (historical)

The user authorized further implementation after sharing the team replies. Implemented
native 100 m integration output alongside 1 km rollups, multi-tile India processing,
and resumable tile-year execution. Both resolutions remain available, so the team's
resolution choice does not discard native population or the earlier coarse results.

- New implementation: `population/src/multitile_population.py`.
- Independent Spark checks: `population/src/validate_multitile_spark.py`.
- Configurations: `population/config/pilot_100m.json` and `population/config/india.json`.
- Final executed handoff: `population/data/curated/bengaluru_100m_final/`, with
  `population_100m/` and `population_1km/`, plan, input/output hashes, progress,
  validation reports and `_SUCCESS`.
- Executed all 12 population epochs: 5,212,356 native rows and 53,460 coarse rows.
  Exact Parquet round-trip checks passed; Spark confirmed uniqueness, mapping,
  conservation, settlement inheritance and agreement with the old 1 km output.
- 14 regression tests passed, including a real synthetic two-tile raster/ZIP/Parquet
  seam test and interruption recovery with tampered-output rejection. Evidence:
  `population/reports/tests_100m_final.txt`. Final source/output hashes also checked.
- Matching-year settlement inheritance is implemented. Only **2020** is currently
  configured and populated; other epochs have null settlement_class. Do not imply
  that all historical settlement maps have been processed. Native counts are never
  divided uniformly, and inherited classifications are not new 100 m observations.
- India mask downloaded with provenance: `population/data/raw/boundaries/`,
  geoBoundaries gbOpen IND ADM0, boundary ID IND-ADM0-67634026, represented year 2014.
  This is a reproducible analysis boundary, not an official Indian administrative
  boundary. The team should use one agreed mask for final cross-product results.
- National plan: 14 tiles, approximately 328,368,413 fine cells per epoch and
  3,940,420,956 cell-year records. All 182 official archive URLs passed HTTP HEAD
  checks; advertised total compressed size 3,943,929,048 bytes. Sources are listed
  in `population/reports/india_source_plan.json`; HEAD evidence is in
  `population/reports/india_source_availability.json`.
- **India-wide data processing has not run.** The new pipeline performs local
  windowed raster extraction/Arrow writing and separate Spark validation. It is
  not distributed raster processing, and the new outputs have not been put in HDFS.
- Documentation: `population/NATIVE_100M_HANDOFF.md` and
  `population/reports/NATIVE_100M_EXECUTION.md`.
- New shareable archive: `population/Population_100m_Handoff.zip`, built by
  `population/scripts/build_native_handoff.py`. Original pilot data and archive
  remain intact; `bengaluru_100m_v2/` is a preserved earlier development run.

Next actual work is national execution with `config/india.json` into a new run
directory using `--download`, followed by Spark validation, and eventual built-up
integration. Follow the documented commands and the user's scope. For an interrupted
new run, `--resume` verifies code/configuration/boundary/input/output hashes, skips
completed tile-years and preserves uncheckpointed partial files before recomputing.
Completed runs cannot be overwritten/resumed; changed processing code requires a new
run. OS locking requires macOS/Linux. No current pipeline process needs resumption.

Do not rerun old `build_handoff.py` merely to package the extension: it regenerates
the historical report/notebook. Use the new packaging script for native outputs.

## Purpose and provenance

The user requested persistent context so future assistant sessions can resume this
project. This file reconstructs earlier development from the saved documentation
and artifacts inspected on 2026-11-06; the earlier development chat was not available.
No pipeline or tests were rerun during that inspection. Neither the GHSL root nor
`population/` was a Git repository when checked.

## Project and completed scope

Team Vector's GHSL project; proposal: `Team_Vector_GHSL_Project_Proposal.pdf`.
The implemented contribution is the population member's weeks 1–5 work, under
`population/`. The saved execution report dated 2026-10-31 records a successful
population-only Bengaluru pilot. India-wide execution belongs to later milestones.

- Product: official JRC GHS-POP R2023A V1_0, native 100 m population counts.
- Twelve five-year epochs, 1975–2030: historical 1975–2020; projections 2025/2030.
- Pilot rectangle: 77.3–77.9 degrees east, 12.7–13.3 degrees north. This is not an
  administrative Bengaluru boundary; pilot totals are not city population totals.
- Acquisition used official JRC downloads instead of the proposal's Earth Engine
  exports. No Colab or Earth Engine login was required.
- Pipeline: source ZIPs and SMOD grid reference -> validated and masked 100 m
  GeoTIFFs -> cell Parquet -> Spark validation and 1 km sums -> partitioned Parquet.
- Raster decoding/staging uses local Rasterio. Spark runs local[2] with genuine
  single-node HDFS (replication one); this is not a multi-machine benchmark.

## Where to find the implementation

- `population/README.md`: reproduction commands, setup, scope, limitations.
- `population/reports/EXECUTION_REPORT.md`: results and execution caveats.
- `population/TEAM_HANDOFF.md`: schema, spatial join contract, integration example.
- `population/config/pilot.json`: area, tile, and epoch configuration.
- `population/config/grid_contract.json`: exact shared grid definition and WKT.
- `population/scripts/download.py`: acquisition and provenance.
- `population/src/prepare.py`: raster preparation and staging.
- `population/src/spark_population.py`: validation, aggregation, persistence.
- `population/scripts/bootstrap_hdfs.py`, `population/scripts/hdfs.py`: local HDFS.
- `population/scripts/finish_execution.py`, `population/scripts/build_handoff.py`:
  execution completion and handoff packaging; inspect before invoking.
- `population/tests/test_population.py`: regression tests.
- `population/notebooks/Population_Weeks_1_to_5.ipynb`: walkthrough and rerun commands;
  underlying scripts ran, but the notebook is not claimed as an executed Colab run.

## Saved validation evidence (not freshly rerun)

The 2026-10-31 execution report records:

- 13 source ZIPs (12 population and one reference); CRC and SHA256 provenance.
- 434,363 in-pilot 100 m cells per epoch, with no in-pilot NoData.
- 5,212,356 input cell-year records -> 4,455 coarse cells per epoch -> 53,460 rows.
- 268 partial-area boundary cells per epoch, explicitly flagged.
- Maximum population conservation difference: about 3.73e-09 persons.
- Five regression tests passed: alignment, half-pixel shift rejection, CRS mismatch,
  incorrect resolution, and aggregation semantics.
- Input/schema/epoch/key/value/coverage/conservation/trajectory checks and complete
  Parquet round-trip comparison passed; local and HDFS outputs agreed.
- Local Spark: 41.47 seconds; HDFS Spark: 30.57 seconds. Single-run local timings only.
- HDFS health check passed. Services were stopped after validation; current process
  state must be checked if needed, rather than assumed from the old report.

Evidence is in `population/reports/`, including `download_manifest.json`,
`raster_validation.json`, `spark_validation.json`, `spark_hdfs_validation.json`,
`tests.txt`, `hdfs_fsck.txt`, and execution logs.

Earlier HDFS attempts stalled during Spark multiset round-trip comparison; one lost
its executor heartbeat. Their outputs were preserved as `population_1km_initial_attempt`
and `population_1km_prior_*` in HDFS. The final implementation uses a full outer join
with null-safe comparison of every column after checking unique keys, with adaptive
execution disabled. Do not mistake interrupted-attempt logs for the final run.

## Deliverables and environment

- Main handoff dataset: `population/data/curated/population_1km/` (a partitioned
  Parquet directory; preserve all partitions).
- Independently retrieved HDFS output: `population/data/curated/population_1km_from_hdfs/`.
- Shareable archive: `population/Population_Weeks1_5_Handoff.zip`; includes source,
  config, notebook, evidence, and curated Parquet, excluding large raw/staging/runtime files.
- Raw data, cleaned rasters, and staging Parquet remain under `population/data/`.
- HDFS zones: `/ghsl/population/{raw,cleaned,curated}`; runtime/metadata/blocks persist
  under `population/runtime/`. Do not delete or reformat them.
- Existing `.venv/`: documented Python 3.12, Spark 3.5.6, Java 17 via jdk4py.
  Dependency pins: `population/requirements-lock.txt`.
- HDFS endpoint: `hdfs://127.0.0.1:19000`; listeners use loopback.
- Existing output is deliberately not overwritten. Reruns need distinct output
  directories and report names; read README before running pipeline commands.

Useful commands from the project root, when required for an actual task:

```sh
.venv/bin/python -m pytest population/tests -q
.venv/bin/python population/scripts/hdfs.py start
.venv/bin/python population/scripts/hdfs.py dfsadmin -report
.venv/bin/python population/scripts/hdfs.py stop
```

## Scientific and integration constraints

- CRS: ESRI:54009 (World Mollweide), 1,000 m north-up grid.
- Global upper-left origin: x=-18,041,000 m, y=9,000,000 m.
- Grid ID: `ghsl_r2023a_54009_1000_e87889c9acde`.
- Reference: GHS-SMOD R2023A V2_0, 2020, tile R8_C26, used for geometry only.
- Join key: `(grid_id, cell_id, year)`; `cell_id = grid_row + '_' + grid_col`,
  using zero-based global indices. Consult the exact grid contract before joining.
- Population is a count: SUM, not average; retain decimal estimates.
- NoData becomes null; zero remains valid. Missing coarse cells stay null; partially
  missing cells retain known subtotals and `is_complete=false`.
- `coverage_fraction` measures missing-data completeness; `aoi_fraction` measures
  the fraction of the coarse cell within the pilot. Do not extrapolate boundary sums.
- Preserve `epoch_type=historical|projection/year=YYYY` partitions.
- Matching nominal resolution alone does not establish compatible grids. Team joins
  require matching origin, CRS, resolution, years, masks, and unique keys, plus
  checks for coverage mismatch in both directions.

## Remaining work and resume point

The population weeks 1–5 pilot is documented as complete. Full three-product
integration has NOT run: settlement and built-up outputs were not supplied.
The join in TEAM_HANDOFF.md is only an example. No mock teammate data was substituted.

Next integration work, once requested and inputs are available:

1. Confirm the team's shared pilot, release, grid contract, and masking convention.
2. Inspect real settlement and built-up datasets and validate keys/coverage.
3. Perform and validate the three-product join.

Later milestones include a validated India boundary, multi-tile processing with seam
checks and shared masks, district attribution/summaries, and settlement-growth analysis.
Do not start these merely because this continuity file lists them; follow the user's
next task.

## Team replies shared on 2026-11-06

The user relayed these teammate answers to the earlier coordination questions:

- Final output must cover all India. Bengaluru-first then India, or India directly,
  are both acceptable. The teammate found Bengaluru too small for their chain.
- They identified `JRC/GHSL/P2023A/GHS_POP`, covering 1975–2030, as the population
  dataset. Its official Earth Engine catalog cites GHS-POP R2023A and specifies
  native 100 m population counts, consistent with our population release choice.
  Release/version and epoch range are separate concepts.
- They said "Split the 1km * 1km into 100*100m". This suggests a possible 100 m
  integration grid but does not unambiguously establish the final join resolution.
  Existing implementation aggregates population to 1 km. Before changing it,
  clarify whether the team wants a 100 m join with inherited parent settlement
  classes or the existing 1 km join with summed population.
- Subdividing a settlement cell repeats its parent category into 100 child cells;
  it does not create independently measured 100 m settlement classifications.
  Native 100 m population should be retained if joining at 100 m, not obtained
  by equally dividing a coarse population total.
- No settlement file, exact transform, or confirmed teammate grid was provided
  with these replies. Our downloaded SMOD reference remains available to share.

Catalog checked on 2026-11-06:
https://developers.google.com/earth-engine/datasets/catalog/JRC_GHSL_P2023A_GHS_POP
This update records coordination context only; no pipeline code or data was changed
and no tests were rerun.

## Maintaining these notes

On 2026-11-06, the user requested this continuity workflow for all future projects
and VS Code work. Installed the standing instructions in `/Users/rio/.codex/AGENTS.md`
with approval and verified the installed content. Future Codex sessions using that
configuration should read/create project context and update it at milestones and
before finishing substantive work. Other machines/profiles need the same setup.

After substantive work, record the date, changes, exact validation performed,
remaining blockers, and next actionable step. Keep saved historical evidence distinct
from new checks. Never store credentials or secrets here.

## Automated week-8 completion 2026-11-10T02:16:10.242681+05:30

All national stages including regional evaluation finished with PASS markers. See
`analysis/reports/WEEK8_RUN_STATUS.json` and `analysis/data/week8_handoff/REPORT.md`.
Compact archive: `GHSL_Weeks1_8_National_Handoff.zip`.
Human visual review of generated figures remains separate from automated validation.
