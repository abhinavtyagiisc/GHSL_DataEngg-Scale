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
from sedona.spark import SedonaContext
PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/"integration/src"))
from spark_integrate import (reject, unique_keys, match_keys, validate_inputs, decorate, aggregate_joined, round_trip, join_products as key_join)
from pyspark import StorageLevel

FINE_KEYS=['year','source_row','source_col']
PARENT_KEYS=['year','parent_row','parent_col']
FIELDS=['population','built_surface_m2','built_surface_nres_m2','settlement_class']
CODES=[10,11,12,13,21,22,23,30]


def join_products(pop,built,smod,grid):
    """Indexed spatial inheritance with explicit matching epoch; preserve nulls."""
    if grid['crs'] != 'ESRI:54009':raise ValueError('Expected World Mollweide grid')
    x,y=grid['origin_x'],grid['origin_y']
    fine=pop.join(built,FINE_KEYS,'inner').withColumn('point',F.expr(
        f'ST_Point({x}+(source_col+0.5)*100.0,{y}-(source_row+0.5)*100.0)')).alias('f')
    parents=smod.withColumn('parent_geom',F.expr(
        f'ST_PolygonFromEnvelope({x}+parent_col*1000.0,{y}-(parent_row+1)*1000.0,{x}+(parent_col+1)*1000.0,{y}-parent_row*1000.0)')).alias('s')
    joined=fine.join(F.broadcast(parents),F.expr('ST_Covers(s.parent_geom,f.point) AND f.year=s.year'))
    plan=joined._jdf.queryExecution().executedPlan().toString()
    if 'BroadcastIndexJoin' not in plan and 'RangeJoin' not in plan:
        raise ValueError('Sedona spatial join was not selected: '+plan)
    return joined.select('f.*','s.parent_row','s.parent_col','s.settlement_class').drop('point')


def session(master='local[2]',partitions=16,events=None):
    jars=json.loads((PROJECT/'phase1/runtime/jar_manifest.json').read_text())
    import hashlib
    for jar in jars:
        with (PROJECT/jar['path']).open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=jar['sha256']:raise ValueError('JAR changed')
    builder=(SedonaContext.builder().master(master).appName('GHSL-Phase2-All-Products')
        .config('spark.jars',','.join(str(PROJECT/j['path']) for j in jars))
        .config('spark.driver.memory','2g').config('spark.sql.shuffle.partitions',str(partitions))
        .config('spark.sql.adaptive.enabled','false').config('spark.ui.enabled','false')
        .config('sedona.join.optimizationmode','all')
        .config('spark.driver.bindAddress','127.0.0.1'))
    if events:
        Path(events).mkdir(parents=True,exist_ok=False)
        builder=builder.config('spark.eventLog.enabled','true').config('spark.eventLog.compress','false').config('spark.eventLog.dir',Path(events).resolve().as_uri())
    spark=SedonaContext.create(builder.getOrCreate());spark.sparkContext.setLogLevel('WARN')
    return spark


def pipeline(prepared,input_prefix,output,report,master):
    prepared=Path(prepared);report=Path(report)
    if report.exists():raise FileExistsError(report)
    if not (prepared/'_SUCCESS').exists():raise ValueError('Preparation incomplete')
    cfg=json.loads((prepared/'config.json').read_text())
    grid=json.loads((prepared/'grid_contract.json').read_text())
    source={r['year']:r for r in json.loads((prepared/'raster_validation.json').read_text())['epochs']}
    start=time.monotonic()
    spark=session(master)
    try:
        # Fail before writing any child dataset if the output root already exists.
        jpath=spark._jvm.org.apache.hadoop.fs.Path(output)
        fs=jpath.getFileSystem(spark._jsc.hadoopConfiguration())
        if fs.exists(jpath):raise FileExistsError(output)
        pop=spark.read.parquet(input_prefix+'/population').persist(StorageLevel.DISK_ONLY)
        built=spark.read.parquet(input_prefix+'/built_up').persist(StorageLevel.DISK_ONLY)
        smod=spark.read.parquet(input_prefix+'/settlement').persist(StorageLevel.DISK_ONLY)
        validate_inputs(pop,built,smod,cfg['epochs'])
        joined=decorate(join_products(pop,built,smod,grid),grid).persist(StorageLevel.DISK_ONLY)
        (report.parent/(report.stem+'_plan.txt')).write_text(joined._jdf.queryExecution().executedPlan().toString())
        unique_keys(joined,FINE_KEYS,'Spatial assignment')
        match_keys(pop,joined,FINE_KEYS,'Spatial assignment coverage')
        reject(joined.filter('parent_row != floor(source_row/10) OR parent_col != floor(source_col/10)'), 'Spatial parent mismatch')
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
    parser.add_argument('--prepared',default=str(PROJECT/'integration/data/prepared'))
    parser.add_argument('--input',default=str(PROJECT/'integration/data/prepared/tables'))
    parser.add_argument('--output',required=True)
    parser.add_argument('--report',required=True)
    parser.add_argument('--master',default='local[2]')
    args=parser.parse_args()
    pipeline(args.prepared,args.input,args.output,args.report,args.master)
