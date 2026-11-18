# Weeks 6–8 historical pilot results

Generated from validated saved outputs on 2026-11-06. National execution and weeks 6–8 remain incomplete.

## Scope and validation

Bengaluru rectangular pilot only; 1975–2020 historical epochs. Projections 2025/2030 are excluded. All district figures are intersections with the pilot, not full district totals. The same 2021 district snapshot is used across historical years.

Spark validated 4,343,630 fine cell-year rows and 44,550 coarse cell-period rows; 349 district/year/class summary rows. Checks include unique keys, complete trajectories, temporal footprint consistency, district population/total-built conservation, and every-column Parquet round trips for cell transitions and district summaries.

The corrected schema regression suite passed 10 tests in 15.86 seconds. The first sandboxed test attempt failed because local Spark sockets were unavailable; the socket-enabled rerun passed.

## Pilot totals

| Year | Population estimate | Total built surface (km²) |
| --- | ---: | ---: |
| 1975 | 3,392,379.96 | 68.831 |
| 1980 | 4,268,016.75 | 76.784 |
| 1985 | 5,006,835.66 | 87.641 |
| 1990 | 5,798,559.49 | 100.433 |
| 1995 | 6,748,239.97 | 133.790 |
| 2000 | 7,797,628.78 | 177.599 |
| 2005 | 9,247,386.56 | 217.228 |
| 2010 | 10,986,968.60 | 270.875 |
| 2015 | 12,993,645.23 | 328.486 |
| 2020 | 15,257,398.19 | 370.987 |

Population values are estimated counts; built surface is area, not floor space. Transition matrix row_share uses coarse-cell counts, including partial pilot-edge cells; sampled_area_km2 separately accounts for the pilot footprint.

## Candidate screening

There are 225 overlapping period/component events, not distinct-town counts.

- boundary_censored: 155
- no_candidate: 33
- independent_growth_candidate: 30
- metropolitan_absorption_candidate: 1
- ambiguous_lineage: 6

Sensitivity results:

| Connectivity | Growth threshold | Growth events | Absorption events |
| --- | ---: | ---: | ---: |
| 8 | 10% | 30 | 1 |
| 4 | 10% | 40 | 22 |
| 8 | 25% | 16 | 1 |

These are exploratory morphological candidates. Adjacency does not establish economic integration or administrative absorption. Pilot-edge censoring and lineage ambiguity limit interpretation. External case-study review is pending; no spatial review GeoJSON is included.

## Sources and reproduction

GHSL: European Commission Joint Research Centre, GHS-POP/GHS-BUILT-S R2023A and GHS-SMOD R2023A V2_0. Source manifests and grid contracts are included.

District source: geoBoundaries gbOpen IND ADM2, boundary ID IND-ADM2-76128533, represented year 2021; Pathways Data Pvt. Ltd., lgdirectory.gov.in. Licensed under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). The source has 735 actual features despite API metadata advertising 736. Derived district mapping and summaries retain this attribution; preserve it when sharing.

See analysis/README.md for commands. This handoff includes analysis outputs, mapping, scripts, configuration and evidence; source rasters and the large weeks 1–5 analytical input are excluded. Reproduction requires the existing weeks 1–5 integration dataset and the project Python environment.
