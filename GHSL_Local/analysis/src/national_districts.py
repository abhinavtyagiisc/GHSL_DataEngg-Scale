"""Bounded native-cell district attribution and Spark SQL national summaries.

Rasterized 100 m centre attribution, fixed 2021 geometry. Conflicting coverage is
reported as AMBIGUOUS rather than double counted; unmatched country cells remain
UNASSIGNED. Complete-case analytical rows only, with coverage reported separately.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from pyproj import Transformer
import rasterio
from rasterio.features import rasterize
from rasterio.enums import MergeAlg
from rasterio.transform import from_origin
import shapely
from shapely.geometry import shape,box
from shapely.ops import transform

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'integration/src'))
from spark_integrate import SparkSession,F,unique_keys,round_trip
sys.path.insert(0,str(PROJECT/'population/src'))
from multitile_population import digest,tile_bounds


def load_boundaries():
    path=ROOT/'data/boundaries/IND_ADM2.geojson'
    provenance=json.loads((ROOT/'data/boundaries/IND_ADM2.provenance.json').read_text())
    if digest(path)!=provenance['sha256']:raise ValueError('District source hash changed')
    project=Transformer.from_crs('EPSG:4326','ESRI:54009',always_xy=True)
    features=json.loads(path.read_text())['features']
    features.sort(key=lambda f:f['properties']['shapeID'])
    polygons=[];metadata=[dict(district_index=0,district_id='UNASSIGNED',district_name='Unassigned')]
    for i,f in enumerate(features,1):
        g=shape(f['geometry'])
        if not g.is_valid:raise ValueError('Invalid district geometry')
        g=transform(project.transform,g.segmentize(0.01))
        if not g.is_valid:raise ValueError('Invalid projected district geometry')
        polygons.append(g)
        metadata.append(dict(district_index=i,district_id=f['properties']['shapeID'],district_name=f['properties']['shapeName']))
    metadata.append(dict(district_index=65535,district_id='AMBIGUOUS',district_name='Overlapping district coverage'))
    return polygons,metadata,provenance


def district_grid(tile,grid,polygons):
    west,south,east,north=tile_bounds(tile,grid)
    extent=box(west,south,east,north)
    shapes=[(g.intersection(extent),i+1) for i,g in enumerate(polygons) if g.intersects(extent)]
    transform_=from_origin(west,north,100,100)
    if not shapes:return np.zeros((10000,10000),dtype='uint16')
    result=rasterize(shapes,out_shape=(10000,10000),transform=transform_,dtype='uint16',fill=0)
    counts=rasterize([(g,1) for g,i in shapes],out_shape=result.shape,transform=transform_,dtype='uint16',merge_alg=MergeAlg.add,fill=0)
    result[counts>1]=65535
    return result


def partial_summary(dataset,labels,tile,grid,year):
    tile_r,tile_c=(int(v[1:])-1 for v in tile.split('_'))
    totals={};input_count=0
    columns=['source_row','source_col','settlement_class','population','built_surface_m2','built_surface_nres_m2']
    for batch in dataset.scanner(columns=columns,batch_size=100000).to_batches():
        arrays={c:batch.column(c).to_numpy(zero_copy_only=False) for c in columns}
        rr=arrays['source_row']-tile_r*10000;cc=arrays['source_col']-tile_c*10000
        if np.any(rr<0)|np.any(rr>=10000)|np.any(cc<0)|np.any(cc>=10000):raise ValueError('Cell outside tile ownership')
        idx=labels[rr,cc].astype('int64')
        code=idx*100+arrays['settlement_class']
        unique,inverse=np.unique(code,return_inverse=True)
        counts=np.bincount(inverse)
        sums=[np.bincount(inverse,weights=arrays[c]) for c in columns[3:]]
        for k,cnt,*values in zip(unique,counts,*sums):
            key=(int(k//100),int(k%100))
            row=totals.setdefault(key,[0,0.,0.,0.]);row[0]+=int(cnt)
            for j,value in enumerate(values,1):row[j]+=float(value)
        input_count+=len(batch)
    rows=[dict(tile=tile,year=year,district_index=k[0],settlement_class=k[1],fine_cells=v[0],population=v[1],built_surface_m2=v[2],built_surface_nres_m2=v[3]) for k,v in totals.items()]
    if sum(r['fine_cells'] for r in rows)!=input_count:raise ValueError('District assignment lost cells')
    return rows


def run(source,out):
    source=Path(source);out=Path(out)
    identity=json.loads((source/'identity.json').read_text())
    if not (source/'_SUCCESS').exists():raise ValueError('National integration incomplete')
    if out.exists():raise FileExistsError(out)
    polygons,metadata,provenance=load_boundaries()
    out.mkdir(parents=True);(out/'partials').mkdir()
    pq.write_table(pa.Table.from_pylist(metadata),out/'district_metadata.parquet')
    expected=[]
    for tile in identity['tiles']:
        labels=district_grid(tile,identity['grid'],polygons)
        for year in identity['config']['epochs']:
            if year>2020:continue
            pair=source/'pairs'/f'{tile}_{year}'
            validation=json.loads((pair/'spark_validation.json').read_text())
            rows=partial_summary(ds.dataset(pair/'curated/analytical_100m',format='parquet',partitioning='hive'),labels,tile,identity['grid'],year)
            if sum(r['fine_cells'] for r in rows)!=validation['analytical_rows']:raise ValueError('District rows differ from integration')
            if 'sql_class_summary' in validation:
                for metric in ('population','built_surface_m2','built_surface_nres_m2'):
                    expected_total=sum(r[metric] or 0 for r in validation['sql_class_summary'])
                    actual_total=sum(r[metric] for r in rows)
                    if not math.isclose(expected_total,actual_total,rel_tol=1e-10,abs_tol=1e-5):
                        raise ValueError('District attribution failed value conservation: '+metric)
            pq.write_table(pa.Table.from_pylist(rows),out/'partials'/f'{tile}_{year}.parquet')
            expected.append(dict(tile=tile,year=year,analytical_rows=validation['analytical_rows'],rejected_rows=validation['rejected_rows']))
            print(json.dumps(expected[-1]),flush=True)
        del labels
    spark=(SparkSession.builder.master('local[2]').appName('GHSL-National-District-SQL').config('spark.ui.enabled','false').config('spark.driver.bindAddress','127.0.0.1').getOrCreate())
    spark.sparkContext.setLogLevel('WARN')
    try:
        partial=spark.read.parquet(str(out/'partials'))
        partial.createOrReplaceTempView('district_partials')
        result=spark.sql('''SELECT district_index,year,settlement_class,SUM(fine_cells) fine_cells,
            SUM(population) population,SUM(built_surface_m2) built_surface_m2,
            SUM(built_surface_nres_m2) built_surface_nres_m2 FROM district_partials
            GROUP BY district_index,year,settlement_class''')
        result=result.join(spark.read.parquet(str(out/'district_metadata.parquet')),'district_index')
        result=result.withColumn('boundary_year',F.lit('2021')).withColumn('scope',F.lit('district intersected with country mask; complete-case native cells'))
        result.write.partitionBy('year').parquet(str(out/'district_summary'))
        round_trip(result,spark.read.parquet(str(out/'district_summary')),['district_index','year','settlement_class'])
        coverage=[r.asDict() for r in result.groupBy('year','district_id').agg(F.sum('fine_cells').alias('fine_cells')).filter("district_id IN ('UNASSIGNED','AMBIGUOUS')").collect()]
        report=dict(status='PASS',boundary=provenance,district_features=len(polygons),coverage_exceptions=coverage,input_coverage=expected,
                    attribution='Rasterized 100 m centre, all_touched=False; overlapping polygon coverage AMBIGUOUS; unmatched UNASSIGNED',
                    caveat='Fixed 2021 districts and 2014 country mask can disagree; summaries use valid complete-case input only, not reconstructed historical districts')
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
        publish_run('districts',a.input,a.output)
    else:run(a.input,a.output)
