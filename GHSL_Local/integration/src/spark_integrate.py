"""Validate, join and aggregate the three GHSL products with Spark DataFrames."""
import argparse
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'population/src'))
from spark_population import SparkSession, F
from pyspark import StorageLevel

FINE_KEYS=['year','source_row','source_col']
PARENT_KEYS=['year','parent_row','parent_col']
FIELDS=['population','built_surface_m2','built_surface_nres_m2','settlement_class']
CODES=[10,11,12,13,21,22,23,30]


def reject(df,message):
    if df.limit(1).count():raise ValueError(message)


def unique_keys(df,keys,label):
    missing=F.lit(False)
    for key in keys:missing=missing | F.col(key).isNull()
    reject(df.filter(missing),f'{label}: null key')
    reject(df.groupBy(*keys).count().filter('count != 1'),f'{label}: duplicate key')


def match_keys(left,right,keys,label):
    reject(left.select(*keys).join(right.select(*keys),keys,'left_anti'),f'{label}: unmatched left keys')
    reject(right.select(*keys).join(left.select(*keys),keys,'left_anti'),f'{label}: unmatched right keys')


def validate_inputs(pop,built,smod,epochs):
    schemas=[(pop,{'year':'int','source_row':'int','source_col':'int','population':'double'},FINE_KEYS,'population'),
             (built,{'year':'int','source_row':'int','source_col':'int','built_surface_m2':'double','built_surface_nres_m2':'double'},FINE_KEYS,'built-up'),
             (smod,{'year':'int','parent_row':'int','parent_col':'int','settlement_class':'int'},PARENT_KEYS,'settlement')]
    for frame,schema,keys,label in schemas:
        if dict(frame.dtypes)!=schema:raise ValueError(f'{label}: unexpected schema {frame.dtypes}')
        unique_keys(frame,keys,label)
        reject(frame.filter((F.col(keys[1])<0)|(F.col(keys[2])<0)),f'{label}: negative index')
        if sorted(r.year for r in frame.select('year').distinct().collect())!=epochs:
            raise ValueError(f'{label}: missing/unexpected epochs')
    for frame,column in [(pop,'population'),(built,'built_surface_m2'),(built,'built_surface_nres_m2')]:
        reject(frame.filter((F.col(column)<0)|F.isnan(column)|(F.abs(column)==float('inf'))),f'{column}: negative/nonfinite')
    reject(built.filter((F.col('built_surface_m2')>10000)|(F.col('built_surface_nres_m2')>10000)|
                       (F.col('built_surface_nres_m2')>F.col('built_surface_m2'))), 'Impossible built-up area')
    reject(smod.filter(~F.col('settlement_class').isin(CODES)),'Invalid settlement code')
    match_keys(pop,built,FINE_KEYS,'Population/built-up coverage')
    parents=pop.select('year',F.floor(F.col('source_row')/10).cast('int').alias('parent_row'),
                      F.floor(F.col('source_col')/10).cast('int').alias('parent_col')).distinct()
    match_keys(parents,smod,PARENT_KEYS,'Fine/settlement coverage')


def join_products(pop,built,smod):
    fine=(pop.join(built,FINE_KEYS,'inner')
          .withColumn('parent_row',F.floor(F.col('source_row')/10).cast('int'))
          .withColumn('parent_col',F.floor(F.col('source_col')/10).cast('int')))
    return fine.join(F.broadcast(smod),PARENT_KEYS,'inner')


def decorate(joined,grid):
    complete=F.lit(True)
    for name in FIELDS:complete=complete & F.col(name).isNotNull()
    return (joined.withColumn('grid_id',F.lit(grid['fine_grid_id']))
            .withColumn('cell_id',F.concat_ws('_','source_row','source_col'))
            .withColumn('parent_grid_id',F.lit(grid['grid_id']))
            .withColumn('parent_cell_id',F.concat_ws('_','parent_row','parent_col'))
            .withColumn('epoch_type',F.when(F.col('year')<=2020,'historical').otherwise('projection'))
            .withColumn('is_valid',complete)
            .withColumn('settlement_resolution_m',F.lit(1000))
            .withColumn('settlement_inherited',F.lit(True))
            .withColumn('source_release',F.lit('R2023A'))
            .withColumn('population_version',F.lit('V1_0'))
            .withColumn('built_version',F.lit('V1_0'))
            .withColumn('settlement_version',F.lit('V2_0')))


def aggregate_joined(joined):
    sums=[F.sum(c).alias(c) for c in FIELDS[:3]]
    return (joined.groupBy('year','parent_grid_id','parent_cell_id','parent_row','parent_col','epoch_type','settlement_class')
            .agg(*sums,F.count('*').cast('int').alias('expected_pixel_count'),
                 F.sum(F.col('is_valid').cast('int')).cast('int').alias('analytical_pixel_count'),
                 *[F.count(c).cast('int').alias(c+'_valid_count') for c in FIELDS[:3]])
            .withColumn('aoi_fraction',F.col('expected_pixel_count')/100.0)
            .withColumn('is_complete',F.col('expected_pixel_count')==F.col('analytical_pixel_count')))


def round_trip(expected,actual,keys):
    unique_keys(actual,keys,'Curated output')
    if set(expected.columns)!=set(actual.columns):raise ValueError('Round-trip columns changed')
    left,right=expected.alias('e'),actual.alias('a')
    condition=F.lit(True)
    for key in keys:condition=condition & (F.col('e.'+key)==F.col('a.'+key))
    compare=left.join(right,condition,'full_outer')
    bad=F.lit(False)
    for col in expected.columns:bad=bad | ~F.col('e.'+col).eqNullSafe(F.col('a.'+col))
    reject(compare.filter(bad),'Parquet round-trip value/key mismatch')


def pipeline(prepared,input_prefix,output,report,master):
    prepared=Path(prepared);report=Path(report)
    if report.exists():raise FileExistsError(report)
    if not (prepared/'_SUCCESS').exists():raise ValueError('Preparation incomplete')
    cfg=json.loads((prepared/'config.json').read_text())
    grid=json.loads((prepared/'grid_contract.json').read_text())
    source={r['year']:r for r in json.loads((prepared/'raster_validation.json').read_text())['epochs']}
    start=time.monotonic()
    spark=(SparkSession.builder.master(master).appName('GHSL-Three-Products-Weeks1-5')
           .config('spark.driver.memory','2g').config('spark.sql.shuffle.partitions','16')
           .config('spark.sql.adaptive.enabled','false').config('spark.ui.enabled','false')
           .config('spark.driver.bindAddress','127.0.0.1').getOrCreate())
    spark.sparkContext.setLogLevel('WARN')
    try:
        # Fail before writing any child dataset if the output root already exists.
        jpath=spark._jvm.org.apache.hadoop.fs.Path(output)
        fs=jpath.getFileSystem(spark._jsc.hadoopConfiguration())
        if fs.exists(jpath):raise FileExistsError(output)
        pop=spark.read.parquet(input_prefix+'/population').persist(StorageLevel.DISK_ONLY)
        built=spark.read.parquet(input_prefix+'/built_up').persist(StorageLevel.DISK_ONLY)
        smod=spark.read.parquet(input_prefix+'/settlement').persist(StorageLevel.DISK_ONLY)
        validate_inputs(pop,built,smod,cfg['epochs'])
        joined=decorate(join_products(pop,built,smod),grid).persist(StorageLevel.DISK_ONLY)
        summary=joined.groupBy('year').agg(F.count('*').alias('rows'),
            F.sum(F.col('is_valid').cast('long')).alias('valid_rows'),
            *[F.sum(c).alias(c) for c in FIELDS[:3]],
            *[F.count(c).alias(c+'_valid_count') for c in FIELDS[:3]]).orderBy('year').collect()
        reports=[]
        for row in summary:
            r=row.asDict();original=source[row.year]
            if r['rows']!=original['fine_rows']:raise ValueError('Join changed row count')
            for column,product in [('population','POP'),('built_surface_m2','BUILT_S'),('built_surface_nres_m2','BUILT_S_NRES')]:
                expected=original['products'][product]
                if r[column+'_valid_count']!=expected['valid_pixels'] or not math.isclose(r[column] or 0,expected['total'],rel_tol=1e-10,abs_tol=1e-5):
                    raise ValueError(f'{column}: join conservation failed')
            reports.append(r)
        analytical=joined.filter('is_valid').persist(StorageLevel.DISK_ONLY)
        invalid=joined.filter('NOT is_valid')
        rejected=sum(r['rows']-r['valid_rows'] for r in reports)
        if sorted(r.year for r in analytical.select('year').distinct().collect())!=cfg['epochs']:
            raise ValueError('An epoch has no valid analytical cells')
        coarse=aggregate_joined(joined).persist(StorageLevel.DISK_ONLY)
        reject(coarse.filter('expected_pixel_count < 1 OR expected_pixel_count > 100'),'Invalid coarse coverage')
        coarse_summary=coarse.groupBy('year').agg(F.count('*').alias('cells'),
            F.sum('expected_pixel_count').alias('fine_rows'),*[F.sum(c).alias(c) for c in FIELDS[:3]]).collect()
        for row in coarse_summary:
            expected=next(r for r in reports if r['year']==row.year)
            if row.cells!=source[row.year]['coarse_rows'] or row.fine_rows!=expected['rows']:raise ValueError('Coarse footprint changed')
            for c in FIELDS[:3]:
                if not math.isclose(row[c] or 0,expected[c] or 0,rel_tol=1e-10,abs_tol=1e-5):raise ValueError('Coarse totals changed')
        analytical.createOrReplaceTempView('ghsl_analytical')
        sql_summary=spark.sql('''SELECT year, epoch_type, settlement_class, count(*) AS fine_cells,
          sum(population) AS population, sum(built_surface_m2) AS built_surface_m2,
          sum(built_surface_nres_m2) AS built_surface_nres_m2 FROM ghsl_analytical
          GROUP BY year, epoch_type, settlement_class ORDER BY year, settlement_class''')
        analytical.repartition('year').write.mode('errorifexists').partitionBy('epoch_type','year').parquet(output+'/analytical_100m')
        coarse.repartition('year').write.mode('errorifexists').partitionBy('epoch_type','year').parquet(output+'/summary_1km')
        sql_summary.write.mode('errorifexists').parquet(output+'/sql_class_summary')
        if rejected:
            invalid.repartition('year').write.mode('errorifexists').partitionBy('epoch_type','year').parquet(output+'/rejected_cells')
        reread=spark.read.parquet(output+'/analytical_100m')
        round_trip(analytical,reread,['grid_id','cell_id','year'])
        round_trip(coarse,spark.read.parquet(output+'/summary_1km'),['parent_grid_id','parent_cell_id','year'])
        # Ensure every full-coverage trajectory is retained; report holes if missing inputs occur.
        incomplete_trajectories=(reread.groupBy('cell_id').agg(F.countDistinct('year').alias('epochs'))
                                 .filter(F.col('epochs')!=len(cfg['epochs'])).count())
        result=dict(status='PASS',scope=cfg.get('scope','Three-product Bengaluru pilot, all ten historical epochs plus two projection tests'),
                    input=input_prefix,output=output,spark_version=spark.version,master=spark.sparkContext.master,
                    epochs=reports,analytical_rows=sum(r['valid_rows'] for r in reports),rejected_rows=rejected,
                    coarse_rows=sum(r.cells for r in coarse_summary),incomplete_trajectories=incomplete_trajectories,
                    sql_class_summary=[r.asDict() for r in sql_summary.collect()],
                    checks=['source schemas/values/epochs','unique keys','bidirectional coverage joins',
                            'native counts and inherited matching-year classes','three-product conservation',
                            'coarse coverage/conservation','full-content Parquet round trips'],
                    elapsed_seconds=round(time.monotonic()-start,2))
        report.write_text(json.dumps(result,indent=2)+'\n')
        marker=spark._jvm.org.apache.hadoop.fs.Path(output+'/_INTEGRATION_SUCCESS')
        stream=fs.create(marker,False);stream.close()
        print(json.dumps(result,indent=2),flush=True)
    finally:spark.stop()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared',default=str(ROOT/'data/prepared'))
    parser.add_argument('--input',default=str(ROOT/'data/prepared/tables'))
    parser.add_argument('--output',required=True)
    parser.add_argument('--report',required=True)
    parser.add_argument('--master',default='local[2]')
    args=parser.parse_args()
    pipeline(args.prepared,args.input,args.output,args.report,args.master)
