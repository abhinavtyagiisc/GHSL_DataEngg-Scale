"""Independent Spark validation of a completed windowed population run."""
import argparse
import json
from pathlib import Path
import time

# Reuse the existing Java/Python environment setup.
from spark_population import SparkSession, F
from pyspark import StorageLevel


def validate(run, master='local[2]', legacy=None):
    run = Path(run)
    if not (run/'_SUCCESS').exists():
        raise ValueError('Windowed run is incomplete')
    plan = json.loads((run/'plan.json').read_text())
    report_path = run/'spark_validation.json'
    if report_path.exists():
        raise FileExistsError(report_path)
    started = time.monotonic()
    spark = (SparkSession.builder.master(master).appName('GHSL-native-100m-validation')
             .config('spark.driver.memory','2g').config('spark.sql.shuffle.partitions','16')
             .config('spark.sql.adaptive.enabled','false').config('spark.ui.enabled','false')
             .config('spark.driver.bindAddress','127.0.0.1').getOrCreate())
    spark.sparkContext.setLogLevel('WARN')
    def reject(df, message):
        if df.limit(1).count():
            raise ValueError(message)
    try:
        fine = spark.read.parquet(str(run/'population_100m')).persist(StorageLevel.DISK_ONLY)
        coarse = spark.read.parquet(str(run/'population_1km')).persist(StorageLevel.DISK_ONLY)
        for frame, grid_id in [(fine,plan['grid']['fine_grid_id']), (coarse,plan['grid']['grid_id'])]:
            reject(frame.filter(F.col('grid_id').isNull() | (F.col('grid_id') != grid_id) |
                                F.col('cell_id').isNull() | F.col('year').isNull() |
                                F.col('grid_row').isNull() | F.col('grid_col').isNull()), 'Missing/incorrect keys')
            reject(frame.groupBy('grid_id','cell_id','year').count().filter('count > 1'), 'Duplicate keys across tiles/windows')
            reject(frame.filter((F.col('population')<0) | F.isnan('population') | (F.abs('population')==float('inf'))), 'Invalid population')
            reject(frame.filter(F.col('cell_id') != F.concat_ws('_','grid_row','grid_col')), 'Incorrect cell ID')
            if sorted(r.year for r in frame.select('year').distinct().collect()) != plan['config']['epochs']:
                raise ValueError('Incomplete epochs')
        expected_parent = F.concat_ws('_', F.floor(F.col('grid_row')/10).cast('int'), F.floor(F.col('grid_col')/10).cast('int'))
        reject(fine.filter((F.col('parent_grid_id') != plan['grid']['grid_id']) |
                           F.col('parent_grid_id').isNull() | F.col('parent_cell_id').isNull() |
                           (F.col('parent_cell_id') != expected_parent)), 'Invalid parent mapping')
        smod_years = plan['config'].get('settlement_epochs', [])
        reject(fine.filter(~F.col('year').isin(smod_years) & F.col('settlement_class').isNotNull()), 'Settlement leaked across epochs')
        summary = (fine.groupBy('parent_grid_id','parent_cell_id','year')
                   .agg(F.sum('population').alias('fine_total'), F.count('*').alias('fine_count'),
                        F.count('population').alias('known'), F.count('settlement_class').alias('class_known'),
                        F.min('settlement_class').alias('min_class'), F.max('settlement_class').alias('max_class')))
        comparison = summary.alias('f').join(coarse.alias('c'),
            (F.col('f.parent_grid_id')==F.col('c.grid_id')) &
            (F.col('f.parent_cell_id')==F.col('c.cell_id')) & (F.col('f.year')==F.col('c.year')), 'full_outer')
        mismatch = (F.col('f.parent_cell_id').isNull() | F.col('c.cell_id').isNull() |
                    (F.col('fine_count') != F.col('expected_pixel_count')) |
                    (F.col('known') != F.col('valid_pixel_count')) |
                    (F.col('fine_total').isNull() != F.col('population').isNull()) |
                    (F.abs(F.col('fine_total')-F.col('population')) > F.lit(1e-8)+F.abs(F.col('population'))*1e-12) |
                    ~F.col('min_class').eqNullSafe(F.col('settlement_class')) |
                    ~F.col('max_class').eqNullSafe(F.col('settlement_class')) |
                    (F.col('class_known') != F.when(F.col('settlement_class').isNull(),0).otherwise(F.col('fine_count'))) |
                    (F.col('expected_pixel_count') < 1) | (F.col('expected_pixel_count') > 100) |
                    (F.col('aoi_fraction') != F.col('expected_pixel_count')/100.0) |
                    (F.col('coverage_fraction') != F.col('valid_pixel_count')/F.col('expected_pixel_count')) |
                    (F.col('is_complete') != (F.col('valid_pixel_count')==F.col('expected_pixel_count'))))
        reject(comparison.filter(mismatch), '100 m to 1 km conservation/coverage/class comparison failed')
        legacy_checked = False
        if legacy:
            old = spark.read.parquet(str(legacy))
            reject(old.groupBy('grid_id','cell_id','year').count().filter('count > 1'), 'Duplicate legacy keys')
            joined = coarse.alias('n').join(old.alias('o'), ['grid_id','cell_id','year'], 'full_outer')
            bad = F.col('n.grid_row').isNull() | F.col('o.grid_row').isNull()
            for name in ('grid_row','grid_col','valid_pixel_count','expected_pixel_count','coverage_fraction','aoi_fraction','is_complete'):
                bad = bad | ~F.col('n.'+name).eqNullSafe(F.col('o.'+name))
            bad = bad | (F.col('n.population').isNull()!=F.col('o.population').isNull()) | (F.abs(F.col('n.population')-F.col('o.population')) > 1e-8+F.abs(F.col('o.population'))*1e-12)
            reject(joined.filter(bad),'New coarse output differs from legacy population pilot')
            legacy_checked = True
        report = dict(status='PASS', spark_version=spark.version, master=spark.sparkContext.master,
                      fine_rows=fine.count(), coarse_rows=coarse.count(), legacy_compared=legacy_checked,
                      elapsed_seconds=round(time.monotonic()-started,2),
                      checks=['unique keys across tiles/windows','epoch coverage','native-parent mapping',
                              'population conservation','null and zero semantics','coverage counts',
                              'settlement inheritance and epoch isolation'])
        report_path.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:
        spark.stop()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True)
    parser.add_argument('--master',default='local[2]')
    parser.add_argument('--compare-legacy')
    args=parser.parse_args()
    validate(args.run,args.master,args.compare_legacy)
