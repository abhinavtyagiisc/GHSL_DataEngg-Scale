"""Inventory every national source and estimate disk needs from the measured pilot."""
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'integration/scripts'))
from download_sources import sources


def main():
    path=ROOT/'reports/national_source_plan.json'
    if path.exists():raise FileExistsError(path)
    prior=json.loads((PROJECT/'population/reports/india_source_plan.json').read_text())
    cfg=json.loads((PROJECT/'integration/config/pilot.json').read_text())
    records=[]
    for tile in prior['tiles']:
        for item in sources(dict(cfg,tile=tile)):
            item=dict(item,tile=tile,path=str(item['path'].relative_to(PROJECT)),cached=item['path'].exists())
            records.append(item)
    if len({r['url'] for r in records})!=len(records):raise ValueError('Duplicate planned sources')
    pilot=json.loads((PROJECT/'integration/reports/spark_hdfs_validation.json').read_text())
    curated=sum(p.stat().st_size for p in (PROJECT/'integration/data/curated/grid_year').rglob('*.parquet'))
    staging=sum(p.stat().st_size for p in (PROJECT/'integration/data/prepared/tables').rglob('*.parquet'))
    factor=prior['approximate_cell_year_rows']/pilot['analytical_rows']
    estimate_curated=round(curated*factor);estimate_staging=round(staging*factor)
    free=shutil.disk_usage(PROJECT).free
    result=dict(name='India three-product national execution preflight',status='PLANNED_NOT_EXECUTED',
        tiles=prior['tiles'],epochs=cfg['epochs'],historical_epochs=list(range(1975,2021,5)),projection_test_epochs=[2025,2030],
        boundary=prior['boundary'],sources=records,source_count=len(records),cached_sources=sum(r['cached'] for r in records),
        approximate_cell_year_rows=prior['approximate_cell_year_rows'],
        planning_estimates=dict(pilot_curated_parquet_bytes=curated,pilot_staging_parquet_bytes=staging,
            scale_factor=factor,national_curated_parquet_bytes=estimate_curated,national_staging_parquet_bytes=estimate_staging,
            duplicated_local_hdfs_payload_bytes=2*(estimate_curated+estimate_staging),free_local_bytes=free,
            excludes='Raw rasters, clipped rasters, Spark shuffle, temporary output and compression differences',
            caution='Linear pilot extrapolation, not a guaranteed national capacity estimate'),
        prerequisites=['Agree one country/district geometry and boundary vintage across products',
                       'Generalize three-product preparation to multi-tile windows, including cropped built-up extents',
                       'Checkpoint tile-year processing and reconcile cross-tile analytical/component keys',
                       'Use bounded staging and avoid retaining duplicate country-sized local/HDFS datasets',
                       'Revalidate national masks, seams, missing data and conservation before claiming national results'])
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('source_count','cached_sources','approximate_cell_year_rows','planning_estimates')},indent=2))


if __name__=='__main__':main()
