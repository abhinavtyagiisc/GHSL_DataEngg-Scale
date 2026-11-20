# GHSL population processing

Downloads, validates and aggregates GHS-POP R2023A V1_0 population counts.
The population-only Bengaluru pilot covers ten historical epochs (1975–2020)
and two projection tests (2025/2030). Source and validation evidence is retained in
`reports/`; population totals are in `reports/epoch_summary.csv`.
Later three-product and 13-tile results are documented in [integration](../integration/README.md)
and the [final analysis report](../analysis/data/final_results/REPORT.md).

Rasterio/Arrow extracts aligned native cells; Spark validates keys, values,
coverage and conservative 1 km sums. The pilot also ran on single-node HDFS.
Inputs come from official JRC archives, replacing the proposed Earth Engine exports.

## Pilot validation summary

The population-only pilot has 434,363 native cells per epoch, 5,212,356 native
cell-year records and 53,460 companion 1 km records. It includes 268 partial coarse
boundary cells per epoch. Local/HDFS coarse validation is recorded in
`reports/spark_validation.json` and `reports/spark_hdfs_validation.json`;
`reports/epoch_summary.csv` retains the population totals.

The native extension recorded 78.41 seconds for Rasterio/Arrow extraction and
33.95 seconds for Spark local[2] validation. Fourteen regression tests passed
(`reports/tests_100m_final.txt`). These are single-machine pilot observations.
The retained full run's `validation.json` and `spark_validation.json` contain its
independent extraction, conservation and persisted-content checks.

## Datasets and join contract

- Original coarse output: `data/curated/population_1km/`.
- Native pilot: `data/curated/bengaluru_100m_final/`, containing `population_100m/`
  and companion `population_1km/` directories.
- Both use Hive partitions `epoch_type=historical|projection/year=YYYY`.
  Read the dataset directory; individual files omit partition fields.
- CRS: ESRI:54009, World Mollweide. Global origin: x=-18,041,000 m, y=9,000,000 m.
- Coarse resolution: 1,000 m; grid ID `ghsl_r2023a_54009_1000_e87889c9acde`.
  Exact transforms and identifiers are in `config/grid_contract.json` and each run's `plan.json`.
- Pilot: 77.3–77.9°E, 12.7–13.3°N, a study rectangle rather than a city boundary.

| Fields | Meaning |
|---|---|
| `grid_id`, `cell_id`, `year` | Unique key at the dataset's resolution |
| `grid_row`, `grid_col` | Zero-based global grid indices |
| `parent_grid_id`, `parent_cell_id` | Native dataset's exact 1 km parent key |
| `population` | Decimal population count; native value at 100 m, summed value at 1 km |
| `settlement_class` | Matching-year parent category when supplied |
| `valid_pixel_count`, `expected_pixel_count` | Valid and in-mask native cells contributing to coarse summaries |
| `coverage_fraction`, `aoi_fraction`, `is_complete` | Missing-data completeness, area fraction and completeness flag |
| `x_center`, `y_center` | Coarse cell centre in Mollweide metres |
| `source_release`, `source_version` | Source identifiers |

Cell IDs combine row and column as `row_col`. Native parent indices are integer
division by ten. Fine centres are `x=origin_x+(grid_col+0.5)*100` and
`y=origin_y-(grid_row+0.5)*100`. Fine and coarse grid IDs are different.
Join aligned 100 m products by the fine key; join 1 km categories through
`(parent_grid_id, parent_cell_id, year)`. Verify transforms, releases, years,
masks, unique keys and unmatched keys in both directions before joining.

The native population-only pilot supplies settlement classes for 2020 only;
other epochs have null classes. Inherited 1 km categories are repeated labels,
not independently measured 100 m classifications. Population is never uniformly
divided among children. NoData (-200 in source population rasters) becomes null;
valid zero remains zero. Coarse sums retain known subtotals without extrapolation.
For full coarse cells, filter `aoi_fraction = 1 AND is_complete`.

## Reproduce from the GHSL project root

Python 3.12 was used. Java 17 is bundled within the virtual environment by jdk4py;
the scripts set JAVA_HOME without changing system configuration.

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r population/requirements-lock.txt
.venv/bin/python population/scripts/download_population_tiles.py
.venv/bin/python population/src/prepare_population_rasters.py
.venv/bin/python population/src/spark_population.py
.venv/bin/python -m pytest population/tests -q
```

The Spark output defaults to `population/data/curated/population_1km`. Existing output
is intentionally not overwritten. On reruns, supply a new `--output` directory and a
new `--report` filename, e.g. `--output population/data/curated/rerun_1 --report rerun_1.json`.
Downloads are reused only after ZIP validation; the manifest records local SHA256 values.

For actual HDFS execution:

```bash
.venv/bin/python population/scripts/bootstrap_hdfs.py
.venv/bin/python population/scripts/hdfs.py start
# Stage once into an empty /ghsl/population tree:
.venv/bin/python population/scripts/hdfs.py stage
.venv/bin/python population/src/spark_population.py \
  --input hdfs://127.0.0.1:19000/ghsl/population/cleaned/population_100m \
  --output hdfs://127.0.0.1:19000/ghsl/population/curated/population_1km \
  --report spark_hdfs_validation.json
.venv/bin/python population/scripts/hdfs.py dfsadmin -report
.venv/bin/python population/scripts/hdfs.py stop
```

HDFS metadata and blocks persist under `population/runtime`. `start` formats only
when no NameNode VERSION file exists. Listeners use loopback and replication is one.
Use the CLI health reports; stop services after validation.


## Native and multi-tile processing

Inspect the multi-tile plan without processing:

```sh
.venv/bin/python population/src/multitile_population.py --config population/config/india.json
```

To reproduce the native pilot, use a new output directory:

```sh
.venv/bin/python population/src/multitile_population.py \
  --config population/config/pilot_100m.json \
  --output population/data/curated/pilot_100m_new --download --block-pixels 500
.venv/bin/python population/src/validate_multitile_spark.py \
  --run population/data/curated/pilot_100m_new
```

For a new population-only national run, substitute `population/config/india.json`
and a new output path. National planning estimates and boundary provenance are in
`reports/india_source_plan.json` and `reports/india_source_availability.json`; they are
separate from the later completed three-product analysis. Window size must be a
positive multiple of ten. National processing requires substantial storage and scans.

`--resume` continues an incomplete run only after checking configuration, boundary,
processor, source and output hashes. An exclusive lock prevents concurrent writers.
Uncheckpointed outputs are preserved under `incomplete/`; completed runs reject
resume/overwrite. `_SUCCESS`, `validation.json` and `spark_validation.json` record
extraction and independent Spark validation. Optional `--compare-legacy` is for the
matching pilot coarse dataset only. Settlement maps for additional years require
matching `settlement_epochs` configuration and a new output directory.

## Sources and acknowledgement

- Schiavina, M.; Freire, S.; Carioli, A.; MacManus, K. (2023), **GHS-POP R2023A**,
  European Commission, Joint Research Centre. DOI: https://doi.org/10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE
- Official product documentation: https://human-settlement.emergency.copernicus.eu/ghs_pop2023.php
- Official downloads: https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/
- Earth Engine product description: https://developers.google.com/earth-engine/datasets/catalog/JRC_GHSL_P2023A_GHS_POP
- Reference geometry, GHS-SMOD R2023A V2_0: https://human-settlement.emergency.copernicus.eu/ghs_smod2023.php
- Hadoop single-node operation: https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-common/SingleCluster.html

GHSL data are European Commission/JRC open data; acknowledge the source on reuse.
Population values are modelled residential estimates; 2025/2030 are projections, not
observed census counts. The pilot totals must not be described as Bengaluru city totals.
