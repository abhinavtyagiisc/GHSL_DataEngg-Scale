# Population weeks 1–5: execution report

Generated 2026-10-31T18:36:37+05:30.

**Status: population-only Bengaluru pilot executed successfully. No Colab required.**

## Scope and milestone evidence

- Official GHS-POP R2023A V1_0, 100 m, ESRI:54009.
- 10 historical epochs (1975–2020) and 2 projection test epochs (2025, 2030).
- Bengaluru test rectangle: 77.3–77.9°E, 12.7–13.3°N; not an administrative city boundary.
- 13 official source ZIPs (12 population + one SMOD grid reference), 414,710,332 bytes. ZIP CRCs checked; SHA256 provenance in `download_manifest.json`.
- 434,363 in-pilot 100 m cells per epoch; no NoData cells inside this pilot.
- 5,212,356 input cell-year records processed using Spark 3.5.6.
- 4,455 1 km cells per epoch; 53,460 output grid-year records.
- 268 partial-AOI boundary cells per epoch, explicitly flagged by `aoi_fraction`.
- Maximum absolute source-to-output population difference: 3.72529029846e-09 persons (floating-point summation only).
- Local Spark run: 41.47 seconds. HDFS Spark run: 30.57 seconds. These are single-run local measurements, not scalability benchmarks.
- Five regression tests passed: exact alignment, half-pixel shift rejection, CRS mismatch rejection, wrong-resolution rejection, and aggregation semantics (sum/null/zero/boundary/epoch isolation).
- Genuine local HDFS NameNode/DataNode, replication 1; raw/cleaned/curated zones populated; filesystem health check passed.
- Both Spark runs checked input schema, complete epochs, duplicate fine-cell keys, finite nonnegative values, fine/coarse mapping, population conservation, coverage counts, complete cell trajectories, unique curated keys and exact Parquet round-trip contents.
- Local output and downloaded HDFS output agree on every key/metadata/coverage value and all population values (relative tolerance 1e-12, absolute 1e-8 persons).

## Population totals for the pilot rectangle

| Year | Type | Population estimate | 1 km records |
|---|---|---:|---:|
| 1975 | historical | 3,392,379.957 | 4,455 |
| 1980 | historical | 4,268,016.749 | 4,455 |
| 1985 | historical | 5,006,835.657 | 4,455 |
| 1990 | historical | 5,798,559.490 | 4,455 |
| 1995 | historical | 6,748,239.972 | 4,455 |
| 2000 | historical | 7,797,628.776 | 4,455 |
| 2005 | historical | 9,247,386.565 | 4,455 |
| 2010 | historical | 10,986,968.603 | 4,455 |
| 2015 | historical | 12,993,645.233 | 4,455 |
| 2020 | historical | 15,257,398.187 | 4,455 |
| 2025 | projection | 17,104,825.156 | 4,455 |
| 2030 | projection | 18,741,841.272 | 4,455 |

These totals describe the chosen rectangle and must not be presented as Bengaluru
municipal population. Projections are not historical observations. No substantive
urban-growth conclusions or nationwide findings are claimed at this stage.

## Deliverables

- `data/raw/downloads/`: original official population ZIPs.
- `data/raw/reference/`: official settlement-grid ZIP and reference GeoTIFF.
- `data/cleaned/GHS_POP_*_bengaluru_100m.tif`: 12 aligned clipped rasters.
- `data/cleaned/population_100m/`: Spark staging Parquet.
- `data/curated/population_1km/`: local verified handoff Parquet.
- `data/curated/population_1km_from_hdfs/`: downloaded HDFS output, independently verified during HDFS execution.
- HDFS tree: `/ghsl/population/{raw,cleaned,curated}`; curated output at `/ghsl/population/curated/population_1km`.
- `config/grid_contract.json` and `TEAM_HANDOFF.md`: shared spatial/key contract.
- `notebooks/Population_Weeks_1_to_5.ipynb`: executable walkthrough of saved results and optional rerun commands. The underlying scripts were executed; the notebook is supplied as a walkthrough, not claimed as an executed Colab session.
- `reports/`: source manifest, validation JSON, SQL epoch summary, samples, test evidence, HDFS status/health and execution logs.

## Explicit boundaries

The population member's weeks 1–5 pilot work is implemented and executed. Native JRC
downloads substitute for the proposal's Earth Engine export step. Raster extraction
is local; DataFrame processing is Spark local[2] backed by real single-node HDFS.
The full three-product join awaits the team's settlement and built-up outputs and
agreement on the shared pilot. No mock versions of those datasets were substituted.
India-wide multi-tile processing, India/district boundaries, district summaries,
and settlement-growth analysis are outside this pilot and remain later milestones.

The HDFS services are stopped after validation; data persist on disk and can be
reopened with `scripts/hdfs.py start`. See README for reproducible commands.

Earlier HDFS attempts wrote output but stalled in Spark's multiset round-trip
comparison; one also lost its executor heartbeat. Their outputs are preserved in
HDFS under `population_1km_initial_attempt` / `population_1km_prior_*`. The final
pipeline uses a full outer join with null-safe comparison of every column after
checking unique keys, with adaptive execution disabled. Reported timings and PASS
status refer to the successful run, not the interrupted attempts.

## Scientific interpretation

Counts are summed, not averaged. Source NoData is null and zeros remain valid.
At the pilot boundary, totals cover only in-pilot 100 m cell centres. Do not rescale
boundary subtotals to full-cell counts. `coverage_fraction` concerns missing data;
`aoi_fraction` concerns area coverage. Read the team handoff before cross-product joins.

Source: European Commission Joint Research Centre, GHS-POP R2023A,
https://doi.org/10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE.
