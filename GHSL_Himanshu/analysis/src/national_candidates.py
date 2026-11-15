"""Array-based national component lineage, using global adjacency across tile seams."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from scipy import ndimage
from pyproj import Transformer
from temporal import periods

ROOT=Path(__file__).resolve().parents[1]


def label_state(state,mask,cfg):
    structure=ndimage.generate_binary_structure(2,1 if cfg['connectivity']==4 else 2)
    labels,n=ndimage.label(mask & np.isin(state['settlement_class'],cfg['urban_codes']),structure)
    counts=np.bincount(labels.ravel(),minlength=n+1)
    centre=np.bincount(labels.ravel(),weights=np.isin(state['settlement_class'],cfg['centre_codes']).ravel(),minlength=n+1)>0
    edge=mask & ((state['aoi_fraction']<1) | ~ndimage.binary_erosion(mask,structure=structure,border_value=0))
    censored=np.bincount(labels.ravel(),weights=edge.ravel(),minlength=n+1)>0
    return labels,counts,centre,censored


def array_events(before,after,mask,cfg,start,end,origin=(0,0)):
    l0,c0,centre0,edge0=label_state(before,mask,cfg)
    l1,c1,centre1,edge1=label_state(after,mask,cfg)
    overlap_mask=(l0>0)&(l1>0)
    encoded=l0[overlap_mask].astype('int64')*len(c1)+l1[overlap_mask]
    pairs,counts=np.unique(encoded,return_counts=True)
    base=pairs//len(c1);target=pairs%len(c1)
    splits=np.bincount(base,minlength=len(c0))
    merges=np.bincount(target,minlength=len(c1))
    # Highest overlap, then largest target index, matches deterministic tie policy.
    best={}
    for b,t,count in zip(base,target,counts):
        old=best.get(int(b))
        if old is None or (int(count),int(t))>(old[1],old[0]):best[int(b)]=(int(t),int(count))
    old_centres=mask & np.isin(before['settlement_class'],cfg['centre_codes'])
    connected=np.bincount(l1.ravel(),weights=old_centres.ravel(),minlength=len(c1))>0
    pop_delta=np.bincount(l0.ravel(),weights=(after['population']-before['population']).ravel(),minlength=len(c0))
    built_delta=np.bincount(l0.ravel(),weights=(after['built_surface_m2']-before['built_surface_m2']).ravel(),minlength=len(c0))
    flat=l0.ravel();positions=np.flatnonzero(flat)
    ids,first=np.unique(flat[positions],return_index=True)
    representatives={int(k):int(positions[i]) for k,i in zip(ids,first)}
    events=[]
    for b,(t,count) in sorted(best.items()):
        if centre0[b]:continue
        retained=count/c0[b];growth=(c1[t]-c0[b])/c0[b]
        censored=bool(edge0[b] or edge1[t]);split=splits[b]>1;merge=merges[t]>1
        connection=bool(connected[t] and centre1[t])
        status='no_candidate'
        if censored:status='boundary_censored'
        elif c0[b]<cfg['minimum_baseline_cells']:status='below_minimum_size'
        elif split or retained<cfg['minimum_retained_fraction']:status='ambiguous_lineage'
        elif connection:status='metropolitan_absorption_candidate'
        elif merge:status='ambiguous_lineage'
        elif growth>=cfg['minimum_growth_fraction'] and pop_delta[b]>0 and built_delta[b]>0:status='independent_growth_candidate'
        r,c=divmod(representatives[b],mask.shape[1]);r+=origin[0];c+=origin[1]
        events.append(dict(start_year=start,end_year=end,baseline_component=f'{r}_{c}',target_component_index=t,
            baseline_cells=int(c0[b]),target_cells=int(c1[t]),retained_fraction=float(retained),component_area_growth_fraction=float(growth),
            stable_footprint_population_delta=float(pop_delta[b]),stable_footprint_built_surface_delta_m2=float(built_delta[b]),
            boundary_censored=censored,split=bool(split),merge=bool(merge),connected_to_preexisting_centre=connection,status=status,
            representative_row=r,representative_col=c))
    return events


def run(source,out):
    source=Path(source);out=Path(out)
    if not (source/'_SUCCESS').exists():raise ValueError('National temporal analysis incomplete')
    if out.exists():raise FileExistsError(out)
    dataset=ds.dataset(source/'historical_common',format='parquet',partitioning='hive')
    cfg=json.loads((ROOT/'config/pilot.json').read_text())
    cfg['district_vintage_policy']='Fixed 2021 districts; national country-mask intersections'
    cfg['national_status']='Candidate screening on completed national common mask'
    first=dataset.to_table(filter=ds.field('year')==1975,columns=['parent_row','parent_col'])
    rr=first['parent_row'].to_numpy();cc=first['parent_col'].to_numpy()
    r0,c0=int(rr.min()),int(cc.min());h,w=int(rr.max()-r0+1),int(cc.max()-c0+1)
    mask=np.zeros((h,w),dtype=bool);mask[rr-r0,cc-c0]=True
    out.mkdir(parents=True)
    def state(year):
        columns=['parent_row','parent_col','settlement_class','population','built_surface_m2','aoi_fraction']
        table=dataset.to_table(filter=ds.field('year')==year,columns=columns)
        r=table['parent_row'].to_numpy()-r0;c=table['parent_col'].to_numpy()-c0
        if len(r)!=int(mask.sum()) or not mask[r,c].all():raise ValueError('Historical component masks differ')
        result={}
        for col in columns[2:]:
            a=np.zeros((h,w),dtype='int16' if col=='settlement_class' else 'float64')
            a[r,c]=table[col].to_numpy();result[col]=a
        return result
    cases=[(8,0.1),(4,0.1),(8,0.25)]
    sensitivity=[];primary=[]
    for connectivity,growth in cases:
        counts=Counter()
        for start,end in periods(cfg['historical_epochs']):
            before=state(start);after=state(end)
            events=array_events(before,after,mask,dict(cfg,connectivity=connectivity,minimum_growth_fraction=growth),start,end,(r0,c0))
            counts.update(e['status'] for e in events)
            if (connectivity,growth)==cases[0]:primary.extend(events)
            del before,after
            print(json.dumps(dict(connectivity=connectivity,growth=growth,start=start,end=end,events=len(events))),flush=True)
        sensitivity.append(dict(connectivity=connectivity,minimum_growth_fraction=growth,event_counts=dict(counts)))
    if not primary:raise ValueError('No national candidate events; investigate')
    pq.write_table(pa.Table.from_pylist(primary),out/'component_events.parquet')
    with (out/'component_events.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(primary[0]));writer.writeheader();writer.writerows(primary)
    grid=json.loads((ROOT.parent/'integration/config/grid_contract.json').read_text())
    to_lonlat=Transformer.from_crs(grid['crs'],'EPSG:4326',always_xy=True)
    selected=[r for r in primary if r['status'] in ('metropolitan_absorption_candidate','independent_growth_candidate')]
    features=[]
    for row in selected:
        x=grid['origin_x']+(row['representative_col']+0.5)*1000;y=grid['origin_y']-(row['representative_row']+0.5)*1000
        lon,lat=to_lonlat.transform(x,y)
        features.append(dict(type='Feature',geometry=dict(type='Point',coordinates=[lon,lat]),properties=dict(row,geometry_role='Representative baseline cell centre; not town centroid or footprint')))
    (out/'candidate_review.geojson').write_text(json.dumps(dict(type='FeatureCollection',features=features))+'\n')
    report=dict(status='PASS',scope='India common historical complete-case coarse mask; candidates not confirmed towns',events=len(primary),
                event_counts=dict(Counter(e['status'] for e in primary)),sensitivity=sensitivity,config=cfg,
                limitations=['Overlapping period events, not unique-town counts','Spatial adjacency is not economic integration',
                             'Country/missing-data-edge components censored','External administrative case validation not implied'])
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n');(out/'_SUCCESS').write_text('PASS\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--output',required=True)
    a=p.parse_args()
    project=Path(__file__).resolve().parents[2]
    if Path(a.output).resolve().is_relative_to(project):
        import sys
        sys.path.insert(0,str(project/'phase3/scripts'))
        from run_analysis_stage import run as publish_run
        publish_run('candidates',a.input,a.output)
    else:run(a.input,a.output)
