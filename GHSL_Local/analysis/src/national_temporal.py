"""National coarse historical analysis on one common complete observation mask."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'integration/src'))
from spark_integrate import SparkSession,F,unique_keys,round_trip,reject
from temporal import transitions,periods
from pyspark import StorageLevel
from pyspark.sql import Window


def stage_coarse(source,out):
    identity=json.loads((source/'identity.json').read_text())
    for tile in identity['tiles']:
        for year in identity['config']['epochs']:
            if year>2020:continue
            pair=source/'pairs'/f'{tile}_{year}'
            if not (pair/'curated/_INTEGRATION_SUCCESS').exists():raise ValueError('Missing completed pair')
            target=out/f'year={year}';target.mkdir(parents=True,exist_ok=True)
            for i,path in enumerate(sorted((pair/'curated/summary_1km').rglob('*.parquet'))):
                os.link(path,target/f'{tile}_{i}.parquet')
    return identity


def run(source,out):
    source=Path(source);out=Path(out)
    if not (source/'_SUCCESS').exists():raise ValueError('National integration incomplete')
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    identity=stage_coarse(source,out/'source_coarse')
    epochs=[y for y in identity['config']['epochs'] if y<=2020]
    if epochs!=list(range(1975,2021,5)):raise ValueError('Ten historical epochs required')
    spark=(SparkSession.builder.master('local[2]').appName('GHSL-National-Temporal')
           .config('spark.driver.memory','3g').config('spark.sql.shuffle.partitions','32')
           .config('spark.sql.adaptive.enabled','false').config('spark.ui.enabled','false')
           .config('spark.driver.bindAddress','127.0.0.1').getOrCreate())
    spark.sparkContext.setLogLevel('WARN')
    keys=['parent_grid_id','parent_cell_id']
    metrics=['population','built_surface_m2','built_surface_nres_m2']
    try:
        coarse=spark.read.parquet(str(out/'source_coarse')).persist(StorageLevel.DISK_ONLY)
        unique_keys(coarse,keys+['year'],'National coarse keys including seams')
        trajectory=coarse.groupBy(*keys).agg(F.countDistinct('year').alias('epochs'),
            F.min(F.col('is_complete').cast('int')).alias('complete'),
            F.countDistinct('expected_pixel_count').alias('masks'))
        reject(trajectory.filter((F.col('epochs')!=10)|(F.col('masks')!=1)),'National footprint/epoch mismatch')
        mask=trajectory.filter('complete = 1').select(*keys)
        valid=coarse.join(mask,keys,'inner').persist(StorageLevel.DISK_ONLY)
        coverage=[r.asDict() for r in coarse.groupBy('year').agg(F.count('*').alias('source_cells'),
                  F.sum(F.col('is_complete').cast('long')).alias('complete_cells'),F.sum('expected_pixel_count').alias('source_fine_cells')).collect()]
        common_cells=mask.count()
        if not common_cells:raise ValueError('No common complete historical cells')
        valid.write.partitionBy('year').parquet(str(out/'historical_common'))
        # Shared class summaries are SQL over the stable complete-case footprint.
        valid.createOrReplaceTempView('historical_cells')
        concentration=spark.sql('''SELECT year,settlement_class,COUNT(*) coarse_cells,
            SUM(aoi_fraction) sampled_area_km2,SUM(population) population,
            SUM(built_surface_m2) built_surface_m2,SUM(built_surface_nres_m2) built_surface_nres_m2
            FROM historical_cells GROUP BY year,settlement_class''')
        concentration=concentration.withColumn('population_share',F.col('population')/F.sum('population').over(Window.partitionBy('year')))
        concentration=concentration.withColumn('built_surface_share',F.col('built_surface_m2')/F.sum('built_surface_m2').over(Window.partitionBy('year')))
        concentration.write.parquet(str(out/'concentration'))
        counts=[]
        for start,end in periods(epochs):
            frame=transitions(valid,start,end).persist(StorageLevel.DISK_ONLY)
            if frame.count()!=common_cells:raise ValueError('Transition join lost cells')
            frame.createOrReplaceTempView('period_cells')
            matrix=spark.sql('''SELECT start_year,end_year,settlement_class_from,settlement_class_to,transition_type,
                COUNT(*) coarse_cells,SUM(aoi_fraction_from) sampled_area_km2,
                SUM(population_from) population_from,SUM(population_to) population_to,
                SUM(built_surface_m2_from) built_surface_m2_from,SUM(built_surface_m2_to) built_surface_m2_to
                FROM period_cells GROUP BY start_year,end_year,settlement_class_from,settlement_class_to,transition_type''')
            matrix=matrix.withColumn('row_share',F.col('coarse_cells')/F.sum('coarse_cells').over(Window.partitionBy('start_year','end_year','settlement_class_from')))
            period=out/'periods'/f'{start}_{end}'
            frame.write.parquet(str(period/'cell_transitions'));matrix.write.parquet(str(period/'transition_matrix'))
            round_trip(frame,spark.read.parquet(str(period/'cell_transitions')),keys+['start_year','end_year'])
            counts.append(dict(start_year=start,end_year=end,rows=common_cells));frame.unpersist()
            print(json.dumps(counts[-1]),flush=True)
        report=dict(status='PASS',historical_epochs=epochs,projection_epochs_excluded=[2025,2030],common_complete_cells=common_cells,
                    source_coverage=coverage,periods=counts,policy='One common coarse mask complete in all historical epochs; partial country-edge cells retained without extrapolation',
                    excluded_cells=trajectory.count()-common_cells,concentration=[r.asDict() for r in concentration.collect()])
        (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n');(out/'_SUCCESS').write_text('PASS\n')
    finally:spark.stop()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--output',required=True)
    a=p.parse_args()
    project=Path(__file__).resolve().parents[2]
    if Path(a.output).resolve().is_relative_to(project):
        import sys
        sys.path.insert(0,str(project/'phase3/scripts'))
        from run_analysis_stage import run as publish_run
        publish_run('temporal',a.input,a.output)
    else:run(a.input,a.output)
