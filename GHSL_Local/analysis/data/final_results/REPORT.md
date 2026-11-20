# GHSL analysis report — 13-tile study area

R8_C27 excluded in all 12 epochs. Results describe the verified study footprint, not complete India coverage.

## Study coverage and exclusions

The analysis uses verified data from 13 tiles. Excluded areas remain missing and are neither treated as zero nor estimated by extrapolation.

Processed and verified 156 of the 168 originally planned tile-year jobs. Tile R8_C27 was excluded across all 12 epochs because repeated downloads still yielded no valid analytical cells within the study mask.


## Executed scope

13 tiles; 156 tile-year jobs; 624 source archives. All 12 nominal epochs processed. Historical conclusions use 1975–2020 only; 2025/2030 remain projection tests.

Historical comparisons retain 3,280,884 coarse cells complete in every historical epoch; 13,743 cells excluded from this common mask.

## Results and interpretation

See the included CSV tables and concentration figure. Epoch totals use complete-case native cells per epoch; temporal results use a fixed common complete coarse footprint. Those totals therefore have different denominators. District summaries retain UNASSIGNED and AMBIGUOUS coverage explicitly and conserve the complete-case national totals.

Candidate screening produced 108,804 overlapping period/component events. These are morphological screening results, not confirmed metropolitan absorption or unique-town counts.

- no_candidate: 59,143
- independent_growth_candidate: 23,317
- ambiguous_lineage: 9,317
- boundary_censored: 8,336
- metropolitan_absorption_candidate: 5,085
- below_minimum_size: 3,606

Sensitivity results and representative-cell GeoJSON are included. Review shortlisted cases against independent administrative/local evidence before treating them as confirmed settlements.

## Engineering and validation

Windowed local raster extraction and native 100 m retention; Spark local[2] validation, joins and aggregation per tile-year. Spark SQL computes transitions and district summaries. Per-pair source and curated hashes, schemas, keys, coverage, conservation and Parquet round trips were verified; this final audit rechecked every checkpoint hash and national district count/value conservation.

Official JRC downloads replace the proposed Earth Engine exports. The completed pilot used real single-node HDFS; national runs retain local partitioned Parquet to avoid duplicate national storage. This is not a multi-machine benchmark or national HDFS-storage claim.

Country mask: geoBoundaries IND ADM0 represented year 2014. District mask: geoBoundaries IND ADM2 represented year 2021, 735 actual features. These are reproducible study geometries, not official Indian administrative boundaries or reconstructed historical districts.

Sources: European Commission Joint Research Centre GHSL R2023A POP/BUILT-S V1_0 and SMOD V2_0. geoBoundaries gbOpen, Pathways Data Pvt. Ltd., lgdirectory.gov.in; ODbL 1.0: https://opendatacommons.org/licenses/odbl/1-0/. Preserve source attribution and derived-database license obligations when sharing.

## Output locations

Paths below are relative to the project root. Compact tables and the chart are in
`analysis/data/final_results/`; large Parquet partitions require the external data workspace.

| Output | Path |
|---|---|
| Native integration | `integration/data/accepted_coverage_run1/` |
| Common footprint and transitions | `analysis/data/temporal_analysis/` |
| District summaries | `analysis/data/district_summaries/` |
| Settlement candidates | `analysis/data/settlement_candidates/` |
| Raw-data regional checks | `analysis/data/regional_case_studies/` |

## Independent regional data checks

Direct raw-raster comparisons covered 750 complete coarse cell-years across three urban study windows and ten historical epochs. The Mumbai window was relocated by a documented coverage-only rule after the original window fell outside the retained country mask; Delhi and Bengaluru retain their original centres. Population and both built-area sums plus matching-year settlement classes agreed within the declared tolerances. See `analysis/data/regional_case_studies/region_summary.csv` and `validation.json`. This is numerical processing accuracy on the documented sample, not precision/recall against independently labelled settlement-growth events.

## Observed national pipeline performance

156 recorded tile-year pipeline timings total 117,739.66 seconds; summed analytical rows divided by these timings gives 33,361 rows/s. Each is one observation, including Spark startup/validation/write, excluding preceding source acquisition and raster preparation. This is not total project wall time or a repeated national scaling experiment. Per-pair values are in national_pipeline_performance.csv.

## Geospatial engine and quantitative evaluation

The revised weeks 1–5 foundation additionally executed Apache Sedona 1.9.1 spatial joins and independently validated all-product pilot outputs. The phase-2 completion report and raw benchmark evidence are included. Its repeated end-to-end metrics describe local pilot execution; they must not be interpreted as national or multi-machine timings. National district attribution uses the separately validated raster-centre method described in its own validation report.

## Main findings on the common observed footprint

Between 1975 and 2020, population share in urban centres rose from 29.4% to 38.7%, and in urban clusters from 35.5% to 44.3%; rural-class share fell from 35.1% to 16.9%. Urban-cluster built-surface share rose from 26.9% to 47.2%. These are descriptive shares on the fixed complete-case footprint, not full-India totals or causal estimates. Settlement categories can change between epochs.

## Final validation

Analysis of 13 tiles across 156 tile-year combinations was completed on 10 November 2026. All six automated stages passed, including saved-file hashes, district conservation, regional raw-data comparisons and archive integrity. The concentration figure was visually reviewed for legibility, labels, legends and historical-year coverage. R8_C27 remains excluded and is not labelled verified. The Mumbai study-window adjustment and all failed attempts remain documented.

Results and supporting evidence are packaged in `GHSL_Analysis_Results.zip`.

## Regional consistency checks

The final follow-up independently checked 26,870 regional cell-period transitions,
including settlement-class rules, all three numerical deltas and growth fractions,
and checked all 108,804 candidate status decisions against their stored evidence.
No mismatches were found. Three 31x31 km study squares compare population and built
surface growth and include Bengaluru candidate examples. See
`phase3/reports/regional_validation/REPORT.md`, regional CSVs and validation.json.
These are consistency checks, not external detection ground truth.

The original objective of completing the run without manual engineering intervention
was not achieved. Engineering recovery and an explicit coverage revision were required.
`REPRODUCTION.md` explains inspection, source dependencies and reproduction.
