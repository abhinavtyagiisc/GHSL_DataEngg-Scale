# Native 100 m extension: execution report

Date: 2026-11-06 (Asia/Kolkata).

**Completed:** a native 100 m Bengaluru handoff across all 12 population epochs,
2020 parent settlement inheritance, multi-tile processing and checkpointed recovery.
**Prepared, not executed:** India-wide processing across the retained boundary.

## Executed results

- Final run: `data/curated/bengaluru_100m_final/`.
- 5,212,356 native population cell-year records; 53,460 companion 1 km records.
- 434,363 fine cells and 4,455 coarse cells per epoch, including 268 partial coarse
  boundary cells. Years 1975–2020 historical; 2025/2030 projections.
- Native population remains unchanged; NoData stays null and zero stays zero.
- 434,363 fine cells in 2020 inherit their actual parent SMOD class. Other years
  have null settlement_class because only the available 2020 map was configured.
- Rasterio/Arrow extraction: 78.41 seconds. Exact every-column
  Parquet round-trip hashes, conservation, alignment and epoch footprint checks passed.
- Spark 3.5.6 (local[2]) validation: 33.95 seconds.
  Unique fine/coarse keys, complete epochs, correct parent IDs, count conservation,
  null semantics, area/validity coverage and settlement inheritance all passed.
- The new 1 km summaries match the previous verified pilot on every key and coverage
  field; population agreement uses absolute tolerance 1e-8 plus relative 1e-12.
- **14 regression tests passed.** Tests include a real Rasterio -> ZIP -> Parquet
  two-tile seam case; zero/null/boundary aggregation; category inheritance; rejection
  of wrong alignment/CRS/resolution/class; and interruption recovery, checksum
  tampering detection, skipping completed work and preserving partial files.
- Final output checksums and processor hash were independently rechecked.
- Third-party NumPy masked-array deprecation warnings occurred in tests; no failures.
  Spark required local socket permission outside the execution sandbox.

These timings are local measurements, not national or distributed performance claims.
The final run's successful extraction marker is `_SUCCESS`; its independent Spark
report is `spark_validation.json`. Earlier development run `bengaluru_100m_v2/`
remains preserved, but the final directory is the handoff target.

## National readiness and boundaries

- Configuration: `config/india.json`.
- Analysis mask: geoBoundaries gbOpen IND ADM0 (`IND-ADM0-67634026`, represented year
  2014). Exact source and checksum are retained. This is not an official Indian
  administrative boundary; final coverage must use the team's agreed mask.
- 14 intersecting tiles, approximately 328,368,413 fine cells per epoch,
  or 3,940,420,956 records across 12 epochs. These are area-based estimates.
- All 182 official JRC archive URLs returned HTTP 200 in read-only HEAD checks.
  Their advertised combined compressed size is 3,943,929,048 bytes.
- Country polygon holes and islands are preserved; boundary edges are densified
  before Mollweide projection; masking uses 100 m cell centres.
- Processing uses bounded windows aligned to 1 km, deterministic global indices,
  checked tile transforms, separate epoch partitions and no overlaps at tile seams.
- Explicit `--resume` checks code/configuration/boundary/input/output hashes before
  skipping completed tile-years. Interrupted output is preserved before recomputation.
  A POSIX lock prevents concurrent writers. Existing completed output is never overwritten.

The 182 national archives have **not** all been downloaded or processed. New results
have **not** been staged into HDFS. Built-up data and the full three-product integration
are still absent. Settlement epochs other than 2020 require their matching maps.

## Reproduce and hand off

Read `NATIVE_100M_HANDOFF.md` for schemas, commands and restart behavior.
`Population_100m_Handoff.zip` packages the new code, configurations, boundary,
source inventory, validation reports and completed native/coarse pilot Parquet.
It excludes raw raster archives and runtime environments. The older weeks 1–5
archive and execution report are preserved as historical deliverables.
