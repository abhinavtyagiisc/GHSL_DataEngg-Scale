# Weeks 6–8 analysis

Analysis is complete for **13 tiles across 156 tile-year combinations**.
R8_C27 is excluded; these results do not cover all of India. Historical analysis
uses 1975–2020; 2025/2030 projections are treated separately.

See the [final analysis report](data/final_results/REPORT.md) for results and
[regional validation and interpretation](../phase3/reports/regional_validation/REPORT.md)
for follow-up checks. Candidate events are exploratory and must not be interpreted
as unique or confirmed settlements.

For reproduction instructions and archive details, read the [reproduction guide](../REPRODUCTION.md).

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

## Pilot validation and sensitivity

The earlier Bengaluru pilot covered 1975–2020 and validated 4,343,630 fine cell-year
rows, 44,550 coarse cell-period rows and 349 district/year/class summary rows.
Its 225 overlapping candidate events comprised 155 boundary-censored, 33 no-candidate,
30 independent-growth, one absorption and six ambiguous-lineage events.
These are pilot intersections and candidate events, not city/district totals or
confirmed settlements. The schema regression suite passed ten tests in 15.86 seconds.

| Connectivity | Growth threshold | Growth events | Absorption events |
|---|---:|---:|---:|
| 8 | 10% | 30 | 1 |
| 4 | 10% | 40 | 22 |
| 8 | 25% | 16 | 1 |

The sensitivity results demonstrate dependence on connectivity and thresholds.
Final 13-tile results are separate from this pilot.

## Resume and reproduce the pilot

From the project root, with the existing `.venv` and completed weeks 1–5 input:

```sh
.venv/bin/python -m pytest analysis/tests -q
.venv/bin/python analysis/src/analyze_pilot_temporal.py --output analysis/data/pilot_results_new_run
.venv/bin/python analysis/scripts/build_pilot_handoff.py
```

Spark requires local socket access and a new temporal output directory. The optional
packager reads canonical `data/pilot_results`, exports summaries and writes a
checksummed `GHSL_Weeks6_8_Pilot_Handoff.zip`; it rejects an existing archive.
For a new experiment, update its input/output paths explicitly. Reproduction also
requires the weeks 1–5 integration dataset and `integration/src/spark_integrate.py`.
