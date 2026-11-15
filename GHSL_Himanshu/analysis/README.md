# Weeks 6–8 analysis — work in progress

Read [the saved checkpoint](reports/PROGRESS.md) before resuming.

Implemented and run: fixed-vintage district mapping, exploratory connected-component
candidate screening and sensitivity checks, and a national three-product source
inventory. Historical Spark transitions/district summaries now pass validation after the
Arrow-to-Spark schema-metadata fix. See [pilot results](reports/PILOT_REPORT.md).

Weeks 6–8 and national processing are **not complete**. All analysis results currently
refer to the Bengaluru pilot. District summaries must be labelled as pilot district
intersections; candidate events must not be described as confirmed settlements.

Source attribution:

- GHSL, European Commission Joint Research Centre:
  https://developers.google.com/earth-engine/datasets/catalog/JRC_GHSL_P2023A_GHS_SMOD_V2-0
- geoBoundaries IND ADM2, represented year 2021, sourced from Pathways Data Pvt. Ltd.
  and lgdirectory.gov.in; Open Data Commons Open Database License 1.0:
  https://www.geoboundaries.org/api/current/gbOpen/IND/ADM2/
  https://opendatacommons.org/licenses/odbl/1-0/

Exact boundary source URLs, license metadata and SHA256 are retained with the data.
The same district snapshot is used for all historical epochs, not reconstructed
historical administrative boundaries.

## Resume and reproduce the pilot

From the project root, with the existing `.venv` and completed weeks 1–5 input:

```sh
.venv/bin/python -m pytest analysis/tests -q
.venv/bin/python analysis/src/temporal.py --output analysis/data/pilot_results_new_run
.venv/bin/python analysis/scripts/build_pilot_handoff.py
```

Spark requires local socket access. The temporal script refuses existing output
folders. The handoff builder reads the validated canonical `data/pilot_results`,
exports CSV summaries, writes `reports/PILOT_REPORT.md`, and creates the root
`GHSL_Weeks6_8_Pilot_Handoff.zip` with a SHA256 manifest. It refuses to replace an
existing handoff. It does not rerun processing or download inputs. For a new run,
explicitly review and change its source/destination paths before packaging.

The ZIP contains historical pilot results, candidate event CSV/Parquet, district
mapping, source provenance, configuration, code and validation evidence. Reproduction
also requires `integration/src/spark_integrate.py` and the weeks 1–5 analytical
input, retained in the original workspace/handoff.
