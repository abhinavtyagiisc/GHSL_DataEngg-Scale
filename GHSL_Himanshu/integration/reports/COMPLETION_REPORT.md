# Weeks 1–5 completion report

Date: 2026-11-06 (Asia/Kolkata).

**Status: the three-product Bengaluru pilot milestones are complete, with the
explicit JRC-download substitution for the proposal's Earth Engine export step.**

## Proposal milestone checklist

| Requirement | Executed evidence |
|---|---|
| Weeks 1–3: acquire all three historical products for the pilot | 48 verified ZIPs: 12 POP, 12 SMOD, 12 total built-up, 12 NRES; includes ten historical and two test epochs |
| Validate CRS, resolution, grid alignment and values | `data/prepared/raster_validation.json`; exact shared crop, source-specific NoData, valid classes and area/count bounds |
| Establish raw/cleaned/curated HDFS zones | `/ghsl/weeks1_5/bengaluru_run1/`; staged actual archives, clipped GeoTIFFs and independent tables |
| Confirm 100 m ↔ 1 km integration | Native values retained, integer parent-grid mapping, matching-year settlement inheritance; companion coarse sums conserve values |
| Weeks 4–5: Spark ingestion and validation | Spark 3.5.6 reads all three independent tables from HDFS; schemas, epoch completeness, unique keys, value and coverage checks pass |
| Join all three products | 5,212,356 complete analytical 100 m cell-year rows; no missing required field |
| Aggregate and query | 53,460 1 km summaries plus Spark SQL summaries by year and settlement category |
| Store partitioned Parquet | Historical/projection and year partitions in HDFS, retrieved local copy, complete every-column round-trip comparison |
| Reusable Spark pipeline | `src/spark_integrate.py` accepts local/HDFS inputs and new output/report paths |

## Measured execution

- Pilot: 77.3–77.9 E, 12.7–13.3 N; inside the retained India mask, not a municipal boundary.
- Products: POP V1_0, BUILT-S total/NRES V1_0 and SMOD V2_0, all R2023A.
- Source archive bytes: 636,093,006; ZIP CRCs and SHA256 recorded.
- 48 clipped GeoTIFFs and 36 independent staging Parquet files retained.
- 434,363 fine cells and 4,455 parent cells per epoch, across all 12 epochs.
- Complete analytical records: 5,212,356; rejected records: 0.
- Incomplete cell trajectories: 0.
- Spark execution/validation time: 134.46 seconds (local[2]).
- HDFS orchestration time, including staging/retrieval: 228.39 seconds.
- **Seven new integration regressions passed** in two runs: five Spark/data tests,
  then two cropped-grid/misalignment tests. Existing population tests were not rerun
  because the population implementation was unchanged in this task.
- HDFS health: HEALTHY, one live DataNode, replication one. Services stopped afterward.
- Retrieved Parquet row counts, non-null fields, flags and per-epoch totals verified;
  local file SHA256 values recorded in `download_verification.json`.

Exact native raster origins were checked. The built-up tile has a cropped native
extent (9,000 columns), unlike the population tile (10,000); their actual pixel grids
align. This is handled by coordinate-based windows, not array-shape assumptions.

## Epoch summary for the pilot rectangle

| Year | Type | Population estimate | Built-up m² | Non-residential built-up m² | Complete fine rows |
|---|---|---:|---:|---:|---:|
| 1975 | historical | 3,392,379.957 | 68,830,808 | 6,603,518 | 434,363 |
| 1980 | historical | 4,268,016.749 | 76,784,196 | 7,328,707 | 434,363 |
| 1985 | historical | 5,006,835.657 | 87,640,586 | 8,281,001 | 434,363 |
| 1990 | historical | 5,798,559.490 | 100,433,084 | 9,417,400 | 434,363 |
| 1995 | historical | 6,748,239.972 | 133,789,501 | 12,094,672 | 434,363 |
| 2000 | historical | 7,797,628.776 | 177,598,655 | 15,887,656 | 434,363 |
| 2005 | historical | 9,247,386.565 | 217,227,793 | 18,690,922 | 434,363 |
| 2010 | historical | 10,986,968.603 | 270,874,840 | 22,568,179 | 434,363 |
| 2015 | historical | 12,993,645.233 | 328,486,240 | 27,209,111 | 434,363 |
| 2020 | historical | 15,257,398.187 | 370,987,479 | 30,368,562 | 434,363 |
| 2025 | projection/test | 17,104,825.156 | 392,703,480 | 33,319,032 | 434,363 |
| 2030 | projection/test | 18,741,841.272 | 402,422,306 | 35,411,747 | 434,363 |

## Scientific scope and deviations

Native 100 m population and built-up values are retained. Settlement categories are
inherited from their matching-year 1 km parent, not independently estimated at 100 m.
NoData is never converted to zero; incomplete records are excluded and audited.
Valid category 10 (water) is retained and can be explicitly filtered for land analyses.
Boundary coarse cells contain only included fine-cell centres; totals are not rescaled.
The pilot rectangle's totals must not be presented as Bengaluru municipal totals.

Official JRC downloads replace GEE exports; no Earth Engine or Colab run is claimed.
Raster decoding is local, while validation/join/aggregation/storage use Spark with
real single-node HDFS. This is not a national or multi-machine scalability benchmark.
The read-only notebook cells were executed by the Python package builder, not by a
Jupyter kernel. It provides a reproducible walkthrough of actual saved outputs.

**Weeks 6–8 remain:** national execution, historical settlement transitions,
district-level summaries, metropolitan absorption and independent-growth analysis.
The existing national population-only plan does not yet constitute a nationwide
three-product run. No nationwide results are claimed.

## Deliverables

- `data/curated/grid_year/`: HDFS-retrieved analytical, coarse and SQL-summary Parquet.
- `reports/`: source, raster/Spark/HDFS, tests and retrieved-output evidence.
- `notebooks/GHSL_Weeks_1_to_5_Complete.ipynb`: executed read-only walkthrough.
- `GHSL_Weeks1_5_Complete_Handoff.zip` at the project root: code, source/configuration
  contracts, notebook, evidence and curated data. Raw/prepared data and runtimes are
  excluded from the compact archive but remain in the workspace and HDFS.

Source documentation and attribution are linked in `integration/README.md`.

## Later extension: bounded runner (2026-11-07)

Weeks 1–5 results above are unchanged. The bounded national runner is implemented
and validated against the cached 2015/2020 pilot, including actual Spark execution
and checkpoint resume. All-column comparisons passed for 868,726 fine and 8,910
coarse rows total. Full integration suite passed 10 tests; an additional recovery
regression brought the national-specific suite to four passing tests. See
`../NATIONAL_RUNNER.md`, `bounded_validation_comparison.json`, and the root
`PROJECT_CONTEXT.md`. No national execution is claimed.
