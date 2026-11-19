# GHSL population: weeks 1–5

**2026-11-06 extension:** Native 100 m handoff, inherited 2020 settlement classes,
multi-tile India processing, and resumable tile-year checkpoints are now implemented.
Read [NATIVE_100M_HANDOFF.md](NATIVE_100M_HANDOFF.md) and
[the new execution report](reports/NATIVE_100M_EXECUTION.md). The new Bengaluru
output has been executed; the national archive inventory has been checked, but
India-wide processing has not run. The original weeks 1–5 results below remain intact.

This directory implements the population member's contribution to Team Vector's
proposal. The executed scope is a Bengaluru pilot for all 12 GHS-POP R2023A epochs.
The proposal schedules India-wide execution for weeks 6–8, so it is not claimed here.

Start with `reports/EXECUTION_REPORT.md` for results and `TEAM_HANDOFF.md` for joining
the population data to teammates' work. `notebooks/Population_Weeks_1_to_5.ipynb`
provides a walkthrough and rerun commands. No Colab or Earth Engine login is required.

`Population_Weeks1_5_Handoff.zip` is the compact shareable package: source code,
configuration, notebook, validation evidence and curated Parquet. It excludes the
large raw downloads, clipped/staging data, Java/Python environment and HDFS runtime;
those remain in this workspace and can be reproduced using the supplied scripts.

## Week mapping

| Proposal milestone | Population implementation |
|---|---|
| Weeks 1–3: obtain historical data for pilot | Official JRC 100 m population tiles downloaded for 1975–2020; 2025/2030 retained separately as projections |
| Validate rasters | ZIP integrity/SHA256 manifest; CRS, resolution, affine alignment, data types, NoData, nonnegative finite counts, epoch completeness |
| Establish raw and curated HDFS zones | Isolated local NameNode/DataNode; raw, cleaned, curated directories |
| Confirm 100 m to 1 km aggregation | Native 100 m grid aligned to official SMOD V2_0 reference; Spark sums counts and checks conservation |
| Weeks 4–5: ingest, validate, aggregate | Spark DataFrames read cell Parquet, reject duplicate/malformed records and aggregate by grid cell/year |
| Join and persist | Population joins to geometry through deterministic reference-grid indices; join-ready population output. Full three-product join requires teammate data |
| Store partitioned Parquet | Partitions `epoch_type=historical|projection/year=YYYY`, verified by complete round-trip comparison |

**Acquisition deviation:** the proposal describes Google Earth Engine export. This
execution uses the official JRC download service instead, obtaining the native
population tiles without authentication or resampling. Both the source GeoTIFF ZIPs
and clipped pilot GeoTIFFs are retained. This is not an Earth Engine export run.

## Pipeline

```text
Official JRC ZIP tiles + SMOD grid reference
  → validated source files + provenance manifest
  → aligned, masked 100 m GeoTIFFs + 100 m cell Parquet
  → HDFS raw/cleaned zones
  → Spark validation + SUM by 1 km cell/year + SQL checks
  → partitioned 1 km Parquet in HDFS and local handoff copy
```

Raster decoding and staging run locally with Rasterio; the DataFrame validation and
aggregation run in Spark. This is a genuine single-node HDFS + local[2] Spark pilot,
not a distributed raster decoder, YARN job, multi-machine cluster, or national benchmark.

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

All HDFS metadata and blocks persist under `population/runtime`. `start` formats only
when no NameNode VERSION file exists. RPC and HTTP listeners use loopback. The minimal
Maven-based runtime supplies small web contexts instead of the full Hadoop web UI;
use the CLI reports. macOS uses Hadoop's Java fallback rather than native Linux libraries.
HDFS replication is one, suitable for this local pilot only. The services are stopped
after validation to avoid leaving background processes running.

## Configuration and limits

`config/pilot.json` controls the pilot bounding box, tile and years. This version is
deliberately locked to R2023A POP V1_0 and SMOD V2_0; changing release labels alone
does not change the source products. The preparer refuses pilots outside the configured
reference tile. It uses a densified geographic rectangle, then a 100 m centre-in-polygon
mask. The current rectangle is inland around Bengaluru; it is not a district boundary.

For India-wide expansion, add a validated India boundary and multi-tile manifest,
process tiles/windows in parallel, enforce no overlaps at tile seams, and apply one
shared boundary mask. Keep the same global grid indices. District attribution and
cross-product integration belong to the subsequent/team integration work.

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
