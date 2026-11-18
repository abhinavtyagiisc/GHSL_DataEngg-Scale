# Population dataset handoff

For the new native **100 m** dataset and inherited settlement categories, read
[NATIVE_100M_HANDOFF.md](NATIVE_100M_HANDOFF.md). The contract below describes the
original **1 km** population deliverable. Fine and coarse grid IDs are different;
use the new dataset's parent IDs when joining it to 1 km data.

Use `data/curated/population_1km/` as the population team's deliverable.
It is a Parquet dataset directory, not a single file. Keep all partition directories.

## Shared join contract

- Product: GHS-POP R2023A, V1_0; years 1975–2030 every five years.
- CRS: **ESRI:54009**, World Mollweide; metres. Do not silently substitute EPSG:4326.
- Grid resolution: 1,000 m; north-up.
- Global upper-left origin: **x = -18,041,000 m, y = 9,000,000 m**.
- Grid ID: `ghsl_r2023a_54009_1000_e87889c9acde`.
- Reference: official GHS-SMOD R2023A V2_0, 2020, tile R8_C26.
- Full reference transform and WKT: `config/grid_contract.json`.
- Pilot: 77.3–77.9°E, 12.7–13.3°N. A test rectangle around Bengaluru, **not Bengaluru's administrative boundary**.
- Primary key: **(grid_id, cell_id, year)**. `cell_id = grid_row + '_' + grid_col`.
- Zero-based global indices: `grid_col = floor((x - origin_x)/1000)` and `grid_row = floor((origin_y - y)/1000)` for cell-centre coordinates.
- Source 100 m cells are assigned by integer row/column division by ten after alignment verification.

The settlement and built-up teams should use this same origin, CRS, resolution and
masking convention, or supply their shared reference before merging. Matching only
"1 km" or only the geographic bounding box is insufficient.

## Columns

| Column | Meaning |
|---|---|
| grid_id, cell_id, year | Unique join key |
| grid_row, grid_col | Global zero-based 1 km indices |
| population | Sum of known population counts inside the pilot; double; may be null |
| valid_pixel_count | Number of non-NoData 100 m cells contributing |
| expected_pixel_count | Number of 100 m cell centres inside the pilot (1–100) |
| coverage_fraction | valid / expected; missing-data completeness |
| aoi_fraction | expected / 100; fraction of the 1 km cell included by the pilot mask |
| is_complete | All expected in-pilot population cells are valid |
| x_center, y_center | 1 km centre in Mollweide metres |
| epoch_type | historical (1975–2020) or projection (2025, 2030) |
| source_release, source_version | R2023A, V1_0 |

Population is a count, **not density**. Preserve decimal estimates. Zero is valid;
NoData (-200 in source TIFFs) becomes null, never zero. An entirely missing coarse
cell remains null. A partially missing coarse cell contains the known subtotal and
has `is_complete=false`; do not interpret it as a full count or extrapolate it.

Boundary cells contain only population within the pilot rectangle. For comparisons
requiring full 1 km cells, filter `aoi_fraction = 1 AND is_complete`. Do not join a
partial-area population subtotal to a full-area built-up sum and assume equal coverage.

## Join example (run after teammates deliver real datasets)

```python
pop = spark.read.parquet('population/data/curated/population_1km')
smod = spark.read.parquet('path/to/teammate/settlement_parquet')
built = spark.read.parquet('path/to/teammate/built_up_parquet')
keys = ['grid_id', 'cell_id', 'year']
# First reject duplicate keys in all three datasets; verify matching grid contracts,
# years, and masks. Check both left-anti join directions to detect coverage mismatch.
combined = pop.join(smod, keys, 'inner').join(built, keys, 'inner')
```

This join is a handoff example, not an executed integration result. The other two
datasets have not been supplied. The reference settlement TIFF was used only to
establish geometry; no settlement analysis was performed.

## Questions to send the team

“Are we all testing the same area? Are we using GHSL R2023A? Can the settlement
teammate share the 1 km GeoTIFF, so we can confirm our cell boundaries match?”
