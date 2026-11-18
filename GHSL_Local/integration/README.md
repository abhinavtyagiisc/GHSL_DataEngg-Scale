# GHSL weeks 1–5: three-product pilot

This component completes the proposal's pilot ingestion and integration workflow for
population, built-up surface (including its non-residential component), and settlement
classification. Use `reports/COMPLETION_REPORT.md` for executed results and the exact
milestone checklist. The earlier population-only work remains under `../population/`.

## Scope and method

- Bengaluru pilot rectangle: 77.3–77.9 E, 12.7–13.3 N, checked to lie inside the
  retained India boundary. This is not a city/district administrative boundary.
- Ten historical epochs, 1975–2020 in five-year intervals, plus 2025/2030 test epochs.
- GHS-POP R2023A V1_0; GHS-BUILT-S R2023A V1_0 (total and NRES); GHS-SMOD R2023A V2_0.
- Native population and built-up values remain at 100 m. Each cell inherits its
  matching-year parent 1 km settlement category. No interpolation or uniform division.
- A companion 1 km summary sums the fine population and built-up areas.
- Raster extraction is local Rasterio; Spark DataFrames perform validation, joins,
  aggregation and persistence. Spark SQL produces summaries by year and class.
- Execution uses real single-node HDFS and Spark local[2]. It is not a multi-machine
  benchmark. Raw archives, clipped GeoTIFFs and independent staging tables are retained.

**Acquisition deviation from the proposal:** official JRC native GeoTIFF downloads
replace Google Earth Engine exports. No Earth Engine/Colab execution is claimed.
The datasets and native alignment are validated directly. Nationwide execution,
settlement transitions and district summaries remain weeks 6–8 work.

## Data and evidence

The final local copy retrieved from HDFS is `data/curated/grid_year/`:

- `analytical_100m/`: partitioned by `epoch_type` and `year`, with all three products.
- `summary_1km/`: population and built-up sums with area/completeness counts.
- `sql_class_summary/`: Spark SQL counts and totals by epoch and settlement category.
- `_INTEGRATION_SUCCESS`: written only after all checks and full-content Parquet
  round-trip comparisons pass. Spark's child `_SUCCESS` files alone are insufficient.

`data/prepared/` contains 48 clipped GeoTIFFs, three independent Parquet staging
tables, raster validation, configuration and the spatial contract. `reports/` contains
source SHA256/CRC evidence, tests, Spark validation, HDFS health and execution logs.
The source archive cache is shared with `../population/data/raw/`; the HDFS staging
bundle uses hard links to avoid duplicating those local raw bytes.

HDFS run root: `/ghsl/weeks1_5/bengaluru_run1`. Its zones are:

```text
raw/{POP,BUILT_S,BUILT_S_NRES,SMOD}/
cleaned/rasters/{POP,BUILT_S,BUILT_S_NRES,SMOD}/
cleaned/tables/{population,built_up,settlement}/
curated/grid_year/{analytical_100m,summary_1km,sql_class_summary}/
```

## Join contract

CRS ESRI:54009, World Mollweide. Global origin is x=-18,041,000 m and y=9,000,000 m.
The exact fine/parent grid IDs are in `data/prepared/grid_contract.json`.

| Fields | Meaning |
|---|---|
| `grid_id`, `cell_id`, `year` | Unique 100 m analytical key |
| `source_row`, `source_col` | Zero-based global 100 m indices |
| `parent_row`, `parent_col`, `parent_grid_id`, `parent_cell_id` | Exact 1 km parent; indices use integer division by ten |
| `population` | Native population count; decimals retained |
| `built_surface_m2` | Total built-up surface in square metres per 100 m cell |
| `built_surface_nres_m2` | Built-up surface allocated to predominant non-residential use |
| `settlement_class` | Code from the same year's parent settlement cell |
| `settlement_resolution_m`, `settlement_inherited` | 1000 and true: classification has not gained finer scientific resolution |
| `is_valid` | All required values exist; true for every analytical output row |
| `epoch_type` | Historical through 2020; projection/test for 2025 and 2030 |
| `source_release`, product version columns | Reproducible source identifiers |

Built-up units are area, not percent or building count. Zero is valid. NoData stays
null during ingestion; incomplete joined cells are excluded from the analytical
output and counted/reported, with `rejected_cells/` written if any exist. Category 10
is water, a valid GHSL code retained in the complete dataset; filter it explicitly
for land-only analyses. Do not silently reclassify water or NoData as rural.

The 1 km summary keeps known subtotals and per-variable valid counts. It uses
`expected_pixel_count`, `analytical_pixel_count`, `aoi_fraction` and `is_complete`.
At the pilot edge, the totals cover only included fine-cell centres, not a full
square kilometre. The coarse unique key is `(parent_grid_id, parent_cell_id, year)`.

Built-up tiles can have cropped native extents (the pilot tile is 9,000 rather than
10,000 columns). Preparation validates actual CRS, transforms and window coverage;
it does not rely on tile names or array shapes to infer alignment.

## Reproduction

Use the existing project `.venv` and `population/requirements-lock.txt`. Commands
below run from the GHSL project root. Source downloads are reusable after validation:

```sh
.venv/bin/python integration/scripts/download_sources.py
.venv/bin/python integration/src/prepare_inputs.py
.venv/bin/python -m pytest integration/tests -q
.venv/bin/python integration/scripts/run_hdfs.py
```

The downloader checks existing manifest hashes and reuses validated archives; it can
restore missing archives from the packaged manifest. Preparation and the evidence
orchestrator intentionally refuse to overwrite existing outputs. Do not rerun
the commands just to read results. `run_hdfs.py` performs the one-time evidence run,
stages all three products, runs Spark against HDFS, retrieves the verified result,
checks filesystem health and stops its local services in a `finally` block.

The **Spark pipeline itself is reusable** with fresh output/report paths:

```sh
.venv/bin/python integration/src/spark_integrate.py \
  --input integration/data/prepared/tables \
  --output integration/data/curated/recheck_run1 \
  --report integration/reports/recheck_run1.json
```

It also accepts HDFS input/output URIs, as used in the recorded execution. The
`--prepared` option selects the validated source metadata. Existing output roots
are rejected before any child dataset is written. Failed runs remain preserved;
choose new output/report paths after resolving an error. Do not describe an
unfinished directory as a complete run.

To access the persisted HDFS data later:

```sh
.venv/bin/python population/scripts/hdfs.py start
.venv/bin/python population/scripts/hdfs.py dfs -ls /ghsl/weeks1_5/bengaluru_run1
.venv/bin/python population/scripts/hdfs.py stop
```

## Sources and acknowledgement

European Commission / Joint Research Centre GHSL open data; acknowledge the source.

- Population: https://developers.google.com/earth-engine/datasets/catalog/JRC_GHSL_P2023A_GHS_POP
- Built-up surface: https://developers.google.com/earth-engine/datasets/catalog/JRC_GHSL_P2023A_GHS_BUILT_S
- Settlement V2_0: https://developers.google.com/earth-engine/datasets/catalog/JRC_GHSL_P2023A_GHS_SMOD_V2-0
- Native archives: https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/

The original Earth Engine SMOD collection is deprecated in favour of V2_0; this
implementation uses V2_0 consistently. Source URLs and checksums for every epoch
and product are retained in `reports/download_manifest_full.json`.

## National runner development

See [the bounded runner guide](NATIONAL_RUNNER.md) for the new windowed, checkpointed
three-product workflow. It runs Spark one tile-year at a time and discards generated
staging tables only after validated output is checkpointed. This avoids retaining
national staging plus duplicate HDFS output. It does not change the completed pilot.
