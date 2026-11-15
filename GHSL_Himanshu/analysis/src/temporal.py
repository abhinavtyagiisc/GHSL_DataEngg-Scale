"""Spark historical transitions, concentration, and fixed-vintage district summaries."""
import argparse
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'integration/src'))
from spark_integrate import SparkSession,F,unique_keys,reject,round_trip
from pyspark import StorageLevel
from pyspark.sql import Window


def periods(epochs):
    if not epochs or epochs!=sorted(set(epochs)) or any(y>2020 for y in epochs):
        raise ValueError('Historical epochs must be unique, increasing and <=2020')
    pairs=list(zip(epochs,epochs[1:]))
    if len(epochs)>2:pairs.append((epochs[0],epochs[-1]))
    return pairs


def transitions(coarse,start,end):
    keys=['parent_grid_id','parent_cell_id']
    cols=['settlement_class','population','built_surface_m2','built_surface_nres_m2','aoi_fraction']
    left=coarse.filter(F.col('year')==start).select(*keys,*[F.col(c).alias(c+'_from') for c in cols])
    right=coarse.filter(F.col('year')==end).select(*keys,*[F.col(c).alias(c+'_to') for c in cols])
    result=left.join(right,keys,'inner').withColumn('start_year',F.lit(start)).withColumn('end_year',F.lit(end))
    for col in ('population','built_surface_m2','built_surface_nres_m2'):
        result=result.withColumn(col+'_delta',F.col(col+'_to')-F.col(col+'_from'))
        result=result.withColumn(col+'_growth_fraction',F.when(F.col(col+'_from')>0,F.col(col+'_delta')/F.col(col+'_from')))
    rural=[11,12,13];urban=[21,22,23,30]
    return result.withColumn('transition_type',
        F.when(F.col('settlement_class_from').isin(rural)&F.col('settlement_class_to').isin(urban),'rural_to_urban')
         .when(F.col('settlement_class_from').isin(urban)&F.col('settlement_class_to').isin(rural),'urban_to_rural')
         .when((F.col('settlement_class_from')==10)|(F.col('settlement_class_to')==10),'water_involved')
         .when(F.col('settlement_class_from')==F.col('settlement_class_to'),'unchanged_class').otherwise('other_class_change'))


def run(input_root,mapping_root,output):
    output=Path(output);mapping_root=Path(mapping_root)
    if output.exists():raise FileExistsError(output)
    if not (Path(input_root)/'_INTEGRATION_SUCCESS').exists():raise ValueError('Integration incomplete')
    if not (mapping_root/'_SUCCESS').exists():raise ValueError('District mapping incomplete')
    cfg=json.loads((ROOT/'config/pilot.json').read_text());epochs=cfg['historical_epochs']
    district_report=json.loads((mapping_root/'validation.json').read_text())
    start_time=time.monotonic()
    spark=(SparkSession.builder.master('local[2]').appName('GHSL-Weeks6-8-Historical')
        .config('spark.driver.memory','2g').config('spark.sql.shuffle.partitions','12')
        .config('spark.sql.adaptive.enabled','false').config('spark.ui.enabled','false')
        .config('spark.driver.bindAddress','127.0.0.1').getOrCreate())
    spark.sparkContext.setLogLevel('WARN')
    try:
        fine=spark.read.parquet(str(Path(input_root)/'analytical_100m')).filter(F.col('year').isin(epochs)).persist(StorageLevel.DISK_ONLY)
        coarse=spark.read.parquet(str(Path(input_root)/'summary_1km')).filter(F.col('year').isin(epochs)).persist(StorageLevel.DISK_ONLY)
        unique_keys(fine,['grid_id','cell_id','year'],'Historical fine cells')
        reject(fine.groupBy('grid_id','cell_id').agg(F.countDistinct('year').alias('n')).filter(F.col('n')!=len(epochs)), 'Historical fine trajectory incomplete')
        unique_keys(coarse,['parent_grid_id','parent_cell_id','year'],'Historical coarse cells')
        reject(coarse.filter(~F.col('is_complete')),'Incomplete source cells need a common-valid-mask policy before temporal analysis')
        reject(coarse.groupBy('parent_grid_id','parent_cell_id').agg(F.countDistinct('year').alias('n')).filter(F.col('n')!=len(epochs)), 'Historical coarse trajectory incomplete')
        reject(coarse.groupBy('parent_grid_id','parent_cell_id').agg(F.countDistinct('expected_pixel_count').alias('n')).filter('n != 1'),'Temporal area masks differ')
        if sorted(r.year for r in coarse.select('year').distinct().collect())!=epochs:raise ValueError('Historical epoch missing')
        mapping=spark.read.parquet(str(mapping_root/'cell_district.parquet'))
        unique_keys(mapping,['grid_id','cell_id'],'District mapping')
        reject(fine.select('grid_id','cell_id').distinct().join(mapping,['grid_id','cell_id'],'left_anti'),'Unmapped fine key')
        district=fine.join(mapping,['grid_id','cell_id'],'inner').persist(StorageLevel.DISK_ONLY)
        district.createOrReplaceTempView('district_cells')
        district_summary=spark.sql('''SELECT district_id, district_name, year, settlement_class,
            count(*) AS fine_cells, count(*)*0.01 AS sampled_area_km2,
            sum(population) AS population, sum(built_surface_m2) AS built_surface_m2,
            sum(built_surface_nres_m2) AS built_surface_nres_m2
            FROM district_cells GROUP BY district_id, district_name, year, settlement_class''')
        totals=fine.groupBy('year').agg(F.count('*').alias('fine_rows'),F.sum('population').alias('population'),F.sum('built_surface_m2').alias('built_surface_m2'))
        district_totals=district_summary.groupBy('year').agg(F.sum('fine_cells').alias('fine_rows'),F.sum('population').alias('population'),F.sum('built_surface_m2').alias('built_surface_m2'))
        expected={r.year:r.asDict() for r in totals.collect()}
        for r in district_totals.collect():
            if r.fine_rows!=expected[r.year]['fine_rows']:raise ValueError('District join duplicated/dropped cells')
            for c in ('population','built_surface_m2'):
                if not math.isclose(r[c],expected[r.year][c],rel_tol=1e-10,abs_tol=1e-5):raise ValueError('District conservation failed')
        frames=[transitions(coarse,a,b) for a,b in periods(epochs)]
        all_transitions=frames[0]
        for frame in frames[1:]:all_transitions=all_transitions.unionByName(frame)
        all_transitions=all_transitions.persist(StorageLevel.DISK_ONLY)
        counts={r.year:r['count'] for r in coarse.groupBy('year').count().collect()}
        for row in all_transitions.groupBy('start_year','end_year').count().collect():
            if row['count']!=counts[row.start_year] or counts[row.start_year]!=counts[row.end_year]:raise ValueError('Transition join lost cells')
        all_transitions.createOrReplaceTempView('historical_transitions')
        matrix=spark.sql('''SELECT start_year,end_year,settlement_class_from,settlement_class_to,transition_type,
            count(*) AS coarse_cells,sum(aoi_fraction_from) AS sampled_area_km2,
            sum(population_from) AS population_from,sum(population_to) AS population_to,
            sum(built_surface_m2_from) AS built_surface_m2_from,sum(built_surface_m2_to) AS built_surface_m2_to
            FROM historical_transitions GROUP BY start_year,end_year,settlement_class_from,settlement_class_to,transition_type''')
        matrix=matrix.withColumn('row_share',F.col('coarse_cells')/F.sum('coarse_cells').over(Window.partitionBy('start_year','end_year','settlement_class_from')))
        coarse.createOrReplaceTempView('historical_coarse')
        concentration=spark.sql('''SELECT year,settlement_class,count(*) AS coarse_cells,
            sum(aoi_fraction) AS sampled_area_km2,sum(population) AS population,
            sum(built_surface_m2) AS built_surface_m2 FROM historical_coarse GROUP BY year,settlement_class''')
        concentration=(concentration.withColumn('population_share',F.col('population')/F.sum('population').over(Window.partitionBy('year')))
                       .withColumn('built_surface_share',F.col('built_surface_m2')/F.sum('built_surface_m2').over(Window.partitionBy('year'))))
        output.mkdir(parents=True)
        district_summary=district_summary.withColumn('boundary_year',F.lit(str(district_report['boundary']['boundaryYearRepresented']))).withColumn('scope',F.lit('pilot district intersection'))
        district_summary.write.mode('errorifexists').partitionBy('year').parquet(str(output/'district_summary'))
        all_transitions.write.mode('errorifexists').partitionBy('start_year','end_year').parquet(str(output/'cell_transitions'))
        matrix.write.mode('errorifexists').parquet(str(output/'transition_matrix'))
        concentration.write.mode('errorifexists').parquet(str(output/'concentration'))
        round_trip(all_transitions,spark.read.parquet(str(output/'cell_transitions')),['parent_grid_id','parent_cell_id','start_year','end_year'])
        round_trip(district_summary,spark.read.parquet(str(output/'district_summary')),['district_id','year','settlement_class'])
        result=dict(status='PASS',historical_epochs=epochs,periods=periods(epochs),projection_epochs_excluded=[2025,2030],
            fine_historical_rows=fine.count(),coarse_historical_rows=coarse.count(),transition_rows=all_transitions.count(),
            district_summary_rows=district_summary.count(),unassigned_district_cells=district_report['unassigned_cells'],
            source_totals=expected,transition_matrix=[r.asDict() for r in matrix.collect()],
            concentration=[r.asDict() for r in concentration.collect()],
            elapsed_seconds=round(time.monotonic()-start_time,2),scope='Bengaluru pilot; fixed-vintage district intersections only')
        (output/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
        (output/'_SUCCESS').write_text('PASS\n')
        print(json.dumps({k:result[k] for k in ('status','fine_historical_rows','transition_rows','district_summary_rows','elapsed_seconds')},indent=2))
    finally:spark.stop()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',default=str(PROJECT/'integration/data/curated/grid_year'))
    p.add_argument('--mapping',default=str(ROOT/'data/district_mapping'))
    p.add_argument('--output',default=str(ROOT/'data/pilot_results'))
    a=p.parse_args();run(a.input,a.mapping,a.output)
