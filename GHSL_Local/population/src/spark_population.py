"""Spark DataFrame validation, conservative aggregation, SQL checks, and Parquet output."""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import time
import jdk4py
os.environ.setdefault('JAVA_HOME', str(jdk4py.JAVA_HOME))
os.environ.setdefault('SPARK_LOCAL_IP', '127.0.0.1')
os.environ.setdefault('PYSPARK_PYTHON', sys.executable)
from pyspark.sql import SparkSession, functions as F

ROOT=Path(__file__).resolve().parents[1]

def aggregate(df):
    return df.groupBy('year','grid_row','grid_col').agg(
        F.sum('population_100m').alias('population'),
        F.count('population_100m').cast('int').alias('valid_pixel_count'),
        F.count('*').cast('int').alias('expected_pixel_count'))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input', default=str(ROOT/'data/cleaned/population_100m'))
    parser.add_argument('--output', default=str(ROOT/'data/curated/population_1km'))
    parser.add_argument('--report', default='spark_validation.json')
    parser.add_argument('--master', default='local[2]')
    args=parser.parse_args()
    start=time.monotonic()
    grid=json.loads((ROOT/'config/grid_contract.json').read_text())
    cfg=json.loads((ROOT/'config/pilot.json').read_text())
    source={r['year']:r for r in json.loads((ROOT/'reports/raster_validation.json').read_text())}
    spark=(SparkSession.builder.master(args.master).appName('GHSL-Population-Weeks1-5')
           .config('spark.driver.memory','2g').config('spark.sql.shuffle.partitions','8')
           .config('spark.sql.adaptive.enabled','false')
           .config('spark.ui.enabled','false').config('spark.driver.bindAddress','127.0.0.1')
           .config('spark.sql.session.timeZone','UTC').getOrCreate())
    spark.sparkContext.setLogLevel('WARN')
    try:
        df=spark.read.parquet(args.input).cache()
        expected={'year':'int','source_row':'int','source_col':'int','grid_row':'int','grid_col':'int','population_100m':'double'}
        if dict(df.dtypes)!=expected:
            raise ValueError(f'Unexpected staging schema: {df.dtypes}')
        years=sorted(r.year for r in df.select('year').distinct().collect())
        if years!=cfg['epochs']:
            raise ValueError(f'Missing or unexpected epochs: {years}')
        if df.filter((F.col('population_100m')<0)|F.isnan('population_100m')|
                     (F.abs(F.col('population_100m'))==float('inf'))).limit(1).count():
            raise ValueError('Negative or nonfinite population')
        if df.groupBy('year','source_row','source_col').count().filter('count > 1').limit(1).count():
            raise ValueError('Duplicate source cells')
        if df.filter((F.col('grid_row') != F.floor(F.col('source_row')/10)) |
                     (F.col('grid_col') != F.floor(F.col('source_col')/10))).limit(1).count():
            raise ValueError('Invalid fine-to-coarse cell mapping')
        result=(aggregate(df)
                .withColumn('grid_id',F.lit(grid['grid_id']))
                .withColumn('cell_id',F.concat_ws('_', F.col('grid_row'),F.col('grid_col')))
                .withColumn('epoch_type',F.when(F.col('year')<=2020,'historical').otherwise('projection'))
                .withColumn('coverage_fraction',F.col('valid_pixel_count')/F.col('expected_pixel_count'))
                .withColumn('aoi_fraction',F.col('expected_pixel_count')/F.lit(100.0))
                .withColumn('is_complete',F.col('valid_pixel_count')==F.col('expected_pixel_count'))
                .withColumn('x_center',F.lit(grid['origin_x'])+(F.col('grid_col')+0.5)*1000)
                .withColumn('y_center',F.lit(grid['origin_y'])-(F.col('grid_row')+0.5)*1000)
                .withColumn('source_release',F.lit('R2023A'))
                .withColumn('source_version',F.lit('V1_0')).cache())
        if result.filter('expected_pixel_count > 100 OR expected_pixel_count < 1').limit(1).count():
            raise ValueError('Invalid 1 km coverage')
        result.createOrReplaceTempView('population_grid_year')
        summary=spark.sql('''SELECT year, epoch_type, count(*) AS cells,
            sum(population) AS total_population, sum(valid_pixel_count) AS valid_pixels,
            sum(expected_pixel_count) AS expected_pixels,
            sum(CASE WHEN NOT is_complete THEN 1 ELSE 0 END) AS incomplete_cells,
            sum(CASE WHEN aoi_fraction < 1 THEN 1 ELSE 0 END) AS boundary_cells
            FROM population_grid_year GROUP BY year, epoch_type ORDER BY year''').collect()
        reports=[]
        for row in summary:
            item=row.asDict()
            original=source[row.year]
            if not math.isclose(row.total_population, original['source_total'],rel_tol=1e-10,abs_tol=1e-5):
                raise ValueError(f'Population conservation failed: {item}')
            if row.valid_pixels!=original['valid_pixels'] or row.expected_pixels!=original['inside_pixels']:
                raise ValueError(f'Pixel count changed: {item}')
            item['source_total']=original['source_total']
            item['absolute_difference']=abs(row.total_population-original['source_total'])
            reports.append(item)
        if result.groupBy('cell_id').agg(F.countDistinct('year').alias('n')).filter(f'n != {len(years)}').count():
            raise ValueError('Cells missing epochs')
        # No overwrite: accidental replacement of an existing run is a failure.
        result.repartition('year').write.mode('errorifexists').partitionBy('epoch_type','year').parquet(args.output)
        reread=spark.read.parquet(args.output)
        if reread.count()!=sum(r['cells'] for r in reports):
            raise ValueError('Parquet round-trip row count mismatch')
        if reread.groupBy('grid_id','cell_id','year').count().filter('count != 1').limit(1).count():
            raise ValueError('Duplicate curated keys')
        # Verify every output value, including nulls, after storage round-trip.
        expected_rows=result.alias('e')
        actual_rows=reread.alias('a')
        key_match=(F.col('e.grid_id')==F.col('a.grid_id')) & (F.col('e.cell_id')==F.col('a.cell_id')) & (F.col('e.year')==F.col('a.year'))
        comparison=expected_rows.join(actual_rows,key_match,'full_outer')
        mismatch=F.lit(False)
        for column in result.columns:
            mismatch=mismatch | ~F.col('e.'+column).eqNullSafe(F.col('a.'+column))
        if comparison.filter(mismatch).limit(1).count():
            raise ValueError('Parquet round-trip content mismatch')
        report=dict(status='PASS', spark_version=spark.version, master=spark.sparkContext.master,
                    input=args.input, output=args.output, grid_id=grid['grid_id'],
                    input_rows=df.count(), output_rows=reread.count(), epochs=reports,
                    elapsed_seconds=round(time.monotonic()-start,2),
                    scope='Bengaluru pilot; population only; local Spark, not a multi-node performance test')
        (ROOT/'reports'/args.report).write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2),flush=True)
    finally:
        spark.stop()

if __name__=='__main__':
    main()
