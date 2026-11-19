from pathlib import Path
import sys
import numpy as np
import pyarrow as pa
import pyarrow.dataset as ds
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from screen_national_candidates import array_events
from summarize_national_districts import partial_summary
from settlement_components import candidate_events
from test_analysis import CFG,world,urban


def arrays(cells):
    result={c:np.zeros((12,12)) for c in ('settlement_class','population','built_surface_m2','aoi_fraction')}
    for key,row in cells.items():
        for c in result:result[c][key]=row[c]
    return result


@pytest.mark.parametrize('connectivity',[4,8])
@pytest.mark.parametrize('mode',['growth','absorption','split','edge'])
def test_array_lineage_matches_reference(connectivity,mode):
    before=world();urban(before,[(3,2),(3,3)]);urban(before,[(3,8),(3,9)],30)
    if mode=='edge':urban(before,[(0,2),(0,3)])
    after={k:v.copy() for k,v in before.items()}
    if mode=='absorption':urban(after,[(3,c) for c in range(4,8)],21)
    if mode=='growth':
        urban(after,[(4,2)])
        for k in [(3,2),(3,3)]:after[k].update(population=12.,built_surface_m2=6.)
    if mode=='split':
        urban(before,[(3,4)]);urban(after,[(3,4)]);after[3,3]['settlement_class']=11
    cfg=dict(CFG,connectivity=connectivity)
    expected=candidate_events(before,after,cfg,1975,1980)
    actual=array_events(arrays(before),arrays(after),np.ones((12,12),bool),cfg,1975,1980)
    compare=['start_year','end_year','baseline_component','baseline_cells','target_cells','retained_fraction',
             'component_area_growth_fraction','stable_footprint_population_delta','stable_footprint_built_surface_delta_m2',
             'boundary_censored','split','merge','connected_to_preexisting_centre','status']
    assert [{k:r[k] for k in compare} for r in actual]==[{k:r[k] for k in compare} for r in expected]


def test_district_partials_conserve_unassigned_and_ambiguous():
    labels=np.array([[1,0],[65535,1]],dtype='uint16')
    table=pa.table(dict(source_row=[70000,70000,70001,70001],source_col=[250000,250001,250000,250001],
        settlement_class=[11,11,30,30],population=[2.,3.,4.,5.],built_surface_m2=[1.,2.,3.,4.],built_surface_nres_m2=[0.,1.,1.,2.]))
    rows=partial_summary(ds.dataset(table),labels,'R8_C26',{},2020)
    assert sum(r['fine_cells'] for r in rows)==4
    assert sum(r['population'] for r in rows)==14.
    assert {r['district_index'] for r in rows}=={0,1,65535}
