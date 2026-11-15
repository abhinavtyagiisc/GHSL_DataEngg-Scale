"""Assign native 100 m centres to a fixed, provenance-tracked district geography."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from pyproj import Transformer
import shapely
from shapely.geometry import shape
from shapely.ops import transform

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent


def mapping_table(table,district_ids,names):
    # Arrow projections retain source key-value metadata. Spark's embedded schema
    # would otherwise describe the old 21-column analytical table, not this mapping.
    return (table.select(['grid_id','cell_id']).replace_schema_metadata(None)
            .append_column('district_id',pa.array(district_ids))
            .append_column('district_name',pa.array(names)))


def assign_points(points,geometries,ids):
    """Boundary ties choose smallest stable ID; overlapping interiors are errors."""
    tree=shapely.STRtree(geometries)
    pairs=tree.query(points,predicate='covered_by')
    assignment=np.full(len(points),-1,dtype='int32')
    matches={}
    for point,polygon in pairs.T:
        matches.setdefault(int(point),[]).append(int(polygon))
    ties=0
    for point,polygons in matches.items():
        if len(polygons)>1:
            interiors=[i for i in polygons if points[point].within(geometries[i])]
            if len(interiors)>1:raise ValueError('District interiors overlap at an analytical cell centre')
            if interiors:polygons=interiors
            else:ties+=1
        assignment[point]=min(polygons,key=lambda i:ids[i])
    return assignment,ties


def build_mapping(input_path,boundary_path,provenance_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    provenance=json.loads(Path(provenance_path).read_text())
    content=Path(boundary_path).read_bytes()
    if hashlib.sha256(content).hexdigest()!=provenance['sha256']:raise ValueError('District checksum mismatch')
    data=json.loads(content)
    crs_name=data.get('crs',{}).get('properties',{}).get('name','urn:ogc:def:crs:OGC:1.3:CRS84')
    if crs_name not in ('urn:ogc:def:crs:OGC:1.3:CRS84','EPSG:4326','urn:ogc:def:crs:EPSG::4326'):
        raise ValueError('District GeoJSON must use longitude/latitude WGS84')
    grid=json.loads((PROJECT/'integration/config/grid_contract.json').read_text())
    project=Transformer.from_crs('EPSG:4326',grid['crs'],always_xy=True)
    geometries=[];metadata=[]
    for feature in data['features']:
        props=feature['properties'];g=shape(feature['geometry'])
        if not g.is_valid:raise ValueError(f'Invalid district source geometry: {props}')
        g=transform(project.transform,g.segmentize(0.01))
        if not g.is_valid:raise ValueError('District projection produced invalid geometry')
        district_id=props['shapeID']
        geometries.append(g);metadata.append(dict(district_id=district_id,district_name=props['shapeName'],
            district_area_km2=g.area/1e6,boundary_year=str(provenance['boundaryYearRepresented'])))
    ids=[m['district_id'] for m in metadata]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate district identifiers')
    dataset=ds.dataset(input_path,format='parquet',partitioning='hive')
    # A stable spatial footprint is checked across all epochs by the Spark analysis.
    table=dataset.to_table(filter=ds.field('year')==1975,columns=['grid_id','cell_id','source_row','source_col'])
    row=table['source_row'].to_numpy();col=table['source_col'].to_numpy()
    points=shapely.points(grid['origin_x']+(col+0.5)*100,grid['origin_y']-(row+0.5)*100)
    assignment,ties=assign_points(points,geometries,ids)
    district_ids=[ids[i] if i>=0 else 'UNASSIGNED' for i in assignment]
    names=[metadata[i]['district_name'] if i>=0 else 'Unassigned' for i in assignment]
    output.mkdir(parents=True)
    mapped=mapping_table(table,district_ids,names)
    pq.write_table(mapped,output/'cell_district.parquet',compression='snappy')
    pq.write_table(pa.Table.from_pylist(metadata),output/'district_metadata.parquet',compression='snappy')
    unique,counts=np.unique(assignment,return_counts=True)
    coverage=[]
    for index,count in zip(unique,counts):
        item=metadata[index].copy() if index>=0 else dict(district_id='UNASSIGNED',district_name='Unassigned',district_area_km2=None,boundary_year=str(provenance['boundaryYearRepresented']))
        item.update(fine_cells=int(count),sampled_area_km2=int(count)*0.01,scope='pilot intersection, not full district')
        coverage.append(item)
    report=dict(status='PASS',boundary=provenance,cell_rows=len(table),unassigned_cells=int((assignment<0).sum()),
                boundary_ties=ties,districts=coverage,
                policy='100 m centre covered by polygon; fixed district vintage for every epoch; edge ties by stable ID')
    (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (output/'_SUCCESS').write_text('PASS\n')
    print(json.dumps({k:report[k] for k in ('cell_rows','unassigned_cells','boundary_ties','districts')},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',default=str(PROJECT/'integration/data/curated/grid_year/analytical_100m'))
    p.add_argument('--boundary',default=str(ROOT/'data/boundaries/IND_ADM2.geojson'))
    p.add_argument('--provenance',default=str(ROOT/'data/boundaries/IND_ADM2.provenance.json'))
    p.add_argument('--output',default=str(ROOT/'data/district_mapping'))
    a=p.parse_args();build_mapping(a.input,a.boundary,a.provenance,a.output)
