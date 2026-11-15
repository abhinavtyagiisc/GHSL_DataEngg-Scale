# Native 100 m population and India execution

Implemented 2026-11-06. The completed 100 m deliverable is the Bengaluru pilot;
India-wide processing is implemented and its inputs checked, but has not been run.
See `reports/NATIVE_100M_EXECUTION.md` for the measured results.

## What changed

`src/multitile_population.py` retains native 100 m population counts and assigns each
fine cell its exact parent 1 km cell. Where a matching-year GHS-SMOD map is configured,
the child inherits its parent's category. This repeats a classification; it does not
infer independently observed 100 m settlement classes. It never divides a population
total uniformly among children or interpolates categorical codes.

The same pass writes conservative 1 km population sums, with missing-data and area
coverage fields. This keeps both integration resolutions available. It uses the
existing official Mollweide origin, with distinct grid IDs for 100 m and 1 km.

The new extractor operates in bounded windows on multiple tiles using Rasterio and
Arrow. Independent Spark validation checks duplicates across windows/tiles, native
parent mapping, epoch isolation, counts and population conservation. This is local
extraction plus Spark validation, not distributed raster extraction. The original
weeks 1–5 scripts, data, notebook and HDFS results remain available.

## Completed output

`data/curated/bengaluru_100m_final/` contains:

- `population_100m/epoch_type=.../year=.../R8_C26.parquet`: 100 m handoff.
- `population_1km/epoch_type=.../year=.../R8_C26.parquet`: companion coarse summaries.
- `plan.json`: configuration, fine/parent grid IDs, spatial contract and processor hash.
- `download_manifest.json`: exact input URLs and SHA256 values.
- `progress.json`: completed tile-years and output checksums.
- `validation.json`: local extraction and exact Parquet round-trip checks.
- `spark_validation.json`: independently executed Spark checks.
- `_SUCCESS`: full extraction completed. Never treat a partial run as a finished dataset.

Both resolutions contain all 12 population epochs. The currently configured settlement
map is **2020 only**: all other years have null `settlement_class`. These nulls mean
classification was not supplied for those years, not that those places are rural or
uninhabited. To attach further settlement epochs, add the years to `settlement_epochs`
and execute into a new directory with `--download`. Each uses its own official map.
The three-product join still needs built-up inputs and compatible team grid/masks.

## 100 m schema and join rules

| Field | Meaning |
|---|---|
| `grid_id`, `cell_id`, `year` | Unique fine-grid/year key |
| `grid_row`, `grid_col` | Zero-based global 100 m indices |
| `parent_grid_id`, `parent_cell_id` | Exact parent 1 km grid and cell |
| `population` | Original 100 m count; decimal values retained; null is unknown |
| `settlement_class` | Matching-year parent 1 km code, or null |
| `epoch_type` | Historical through 2020; projection for 2025/2030 |

Year and epoch type are Hive directory partitions. Read the dataset directory using
Spark, or PyArrow with `partitioning='hive'`; individual files omit partition fields.
Parent row/column are integer division of fine indices by ten. The global origin is
(-18,041,000 m, 9,000,000 m), CRS ESRI:54009. Fine cell centre coordinates are:
`x = origin_x + (grid_col + 0.5)*100`, `y = origin_y - (grid_row + 0.5)*100`.

Use the fine key to join a genuinely aligned 100 m built-up dataset. To join a 1 km
settlement table, use `(parent_grid_id, parent_cell_id, year)` against its coarse key.
First reject duplicate keys, verify origins/transforms/releases/year coverage and
matching boundary masks, and check unmatched keys in both directions. Do not join
fine IDs directly to coarse IDs. Do not treat inherited class area as built-up area.

The companion coarse dataset has the original grid ID and includes
`valid_pixel_count`, `expected_pixel_count`, `coverage_fraction`, `aoi_fraction`,
`is_complete`, and `settlement_class`. A partial boundary cell retains only the
population of included 100 m centres; no extrapolation. Entirely missing population
stays null and valid zero stays zero.

## India boundary and acquisition plan

`config/india.json` uses the retained geoBoundaries gbOpen IND ADM0 GeoJSON and
provenance in `data/raw/boundaries/`. The source identifies boundary
`IND-ADM0-67634026`, represented year 2014, CC0, from geoBoundaries/Wikimedia.
It is a reproducible analysis mask, **not an official Indian administrative boundary**;
its coastline, islands and border detail determine included cells. For the team's
final presentation, use one agreed boundary for every product. Replacing the file
with a different agreed WGS84 polygon changes coverage; generate a new plan/run.

Source: https://www.geoboundaries.org/api/current/gbOpen/IND/ADM0/
The retained provenance records the pinned source URL and SHA256. Polygon holes and
multiple islands are preserved. Projected edges are densified before centre masking.

The current mask intersects 14 GHSL tiles, with approximately 328.37 million 100 m
cells per epoch and 3.94 billion cell-year records across all epochs. These are
area-based planning estimates, not executed national row counts.
`reports/india_source_plan.json` inventories 168 population and 14 settlement archives.
`reports/india_source_availability.json` records successful HEAD checks for all 182,
with total compressed size 3,943,929,048 bytes. HEAD availability is not downloaded
ZIP integrity validation; actual runs check ZIP CRCs and compute SHA256 values.

## Run commands (from GHSL project root)

Inspect a plan without fetching or processing data:

```sh
.venv/bin/python population/src/multitile_population.py --config population/config/india.json
```

Execute the national run into a new directory:

```sh
.venv/bin/python population/src/multitile_population.py \
  --config population/config/india.json \
  --output population/data/curated/india_100m_run1 \
  --download --block-pixels 500
```

This is a substantial local batch job, not a pilot-sized task. Plan for the complete
raw cache, billions of Parquet records, and additional Spark shuffle/scratch space.
Pilot compression and timing are not national benchmarks. Source archives are reused
only after validation. Window size must be a positive multiple of ten.

Resume that same incomplete run:

```sh
.venv/bin/python population/src/multitile_population.py \
  --config population/config/india.json \
  --output population/data/curated/india_100m_run1 \
  --download --block-pixels 500 --resume
```

Resume verifies configuration, boundary, processor, source and completed-output
hashes. Completed tile-years are skipped. Files from an interrupted, uncheckpointed
pair are preserved under `incomplete/` before that pair is recomputed. An exclusive
OS lock prevents concurrent writers to a run. This implementation uses POSIX locking
(macOS/Linux). A completed run cannot be resumed or overwritten. Code/config changes
require a new run directory. Processing reports measure the current attempt's time.

After extraction completes, independently validate with Spark:

```sh
.venv/bin/python population/src/validate_multitile_spark.py \
  --run population/data/curated/india_100m_run1
```

The default is `local[2]`; national validation entails large scans and shuffles.
The new run has not been copied into HDFS. Do not confuse the old HDFS pilot report
with validation of these new outputs.

To reproduce the Bengaluru run, substitute `config/pilot_100m.json` and a new output
directory. Optionally pass `--compare-legacy population/data/curated/population_1km`
to the Spark validator for this exact pilot only. Re-run the tests with:

```sh
.venv/bin/python -m pytest population/tests -q
```
