"""Independently confirm all-product 100 m to 1 km aggregation for every epoch."""
from pathlib import Path
import sys
import json
import numpy as np
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'analysis/scripts'));from progress_log import update


def main():
    output=ROOT/'reports/aggregation_validation.json'
    if output.exists():raise FileExistsError(output)
    prep=PROJECT/'integration/data/prepared/tables'
    coarse=ds.dataset(PROJECT/'integration/data/curated/grid_year/summary_1km',format='parquet',partitioning='hive')
    results=[]
    metrics=['population','built_surface_m2','built_surface_nres_m2']
    keys=['parent_row','parent_col']
    for year in range(1975,2031,5):
        pop=pq.read_table(prep/'population'/f'{year}.parquet');built=pq.read_table(prep/'built_up'/f'{year}.parquet')
        for c in ('source_row','source_col','year'):
            if not pop[c].equals(built[c]):raise ValueError('Fine product keys differ')
        table=pa.table(dict(parent_row=pop['source_row'].to_numpy()//10,parent_col=pop['source_col'].to_numpy()//10,
                           population=pop['population'],built_surface_m2=built['built_surface_m2'],built_surface_nres_m2=built['built_surface_nres_m2'],pixels=np.ones(len(pop),dtype='int64')))
        grouped=table.group_by(keys).aggregate([(c,'sum') for c in metrics+['pixels']]).sort_by([(k,'ascending') for k in keys])
        actual=coarse.to_table(filter=ds.field('year')==year).sort_by([(k,'ascending') for k in keys])
        settlement=pq.read_table(prep/'settlement'/f'{year}.parquet').sort_by([(k,'ascending') for k in keys])
        if len(actual)!=len(grouped) or len(settlement)!=len(grouped):raise ValueError('Coarse footprint mismatch')
        for key in keys:
            if not np.array_equal(grouped[key].to_numpy(),actual[key].to_numpy()) or not np.array_equal(grouped[key].to_numpy(),settlement[key].to_numpy()):raise ValueError('Parent keys differ')
        if not np.array_equal(grouped['pixels_sum'].to_numpy(),actual['expected_pixel_count'].to_numpy()):raise ValueError('Parent pixel count mismatch')
        if not np.array_equal(settlement['settlement_class'].to_numpy(),actual['settlement_class'].to_numpy()):raise ValueError('Matching-year settlement mismatch')
        errors={}
        for col in metrics:
            expected=grouped[col+'_sum'].to_numpy();observed=actual[col].to_numpy()
            if not np.allclose(expected,observed,rtol=1e-10,atol=1e-5,equal_nan=True):raise ValueError('Conservative aggregation mismatch: '+col)
            errors[col]=float(np.nanmax(np.abs(expected-observed)))
        results.append(dict(year=year,fine_rows=len(pop),coarse_rows=len(grouped),maximum_absolute_errors=errors))
    report=dict(status='PASS',method='Independent Arrow aggregation from separate prepared products, compared at every parent cell to saved Spark/HDFS output',relative_tolerance=1e-10,absolute_tolerance=1e-5,epochs=results)
    output.write_text(json.dumps(report,indent=2)+'\n')
    update('Independent all-product 100 m to 1 km aggregation validation','PASS','Every parent cell across all 12 epochs matched for population, total built-up, NRES, child count and matching-year settlement class. Evidence: `phase1/reports/aggregation_validation.json`.')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    try:main()
    except Exception as exc:update('Independent all-product aggregation validation','FAILED',str(exc));raise
