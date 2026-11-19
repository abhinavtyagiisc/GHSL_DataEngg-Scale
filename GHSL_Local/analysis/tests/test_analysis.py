from pathlib import Path
import sys
import json
import pytest
import shapely
from shapely.geometry import box
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from settlement_components import components,candidate_events
from assign_pilot_districts import assign_points
from analyze_pilot_temporal import periods,transitions,SparkSession

CFG=json.loads((Path(__file__).resolve().parents[1]/'config/pilot.json').read_text())


def world():
    return {(r,c):dict(settlement_class=11,population=10.0,built_surface_m2=5.0,aoi_fraction=1.0) for r in range(12) for c in range(12)}


def urban(cells,positions,code=22):
    for p in positions:cells[p]['settlement_class']=code


def test_diagonal_connectivity_is_explicit():
    cells=world();urban(cells,[(3,3),(4,4)])
    assert len(components(cells,CFG['urban_codes'],[30],4)[1])==2
    assert len(components(cells,CFG['urban_codes'],[30],8)[1])==1


def test_absorption_requires_connection_to_preexisting_centre():
    before=world();urban(before,[(3,2),(3,3)]);urban(before,[(3,8),(3,9)],30)
    after={k:v.copy() for k,v in before.items()};urban(after,[(3,c) for c in range(4,8)],21)
    events=candidate_events(before,after,CFG,1975,1980)
    assert len(events)==1 and events[0]['status']=='metropolitan_absorption_candidate'
    assert events[0]['connected_to_preexisting_centre']


def test_independent_growth_requires_stable_footprint_support():
    before=world();urban(before,[(3,2),(3,3)])
    after={k:v.copy() for k,v in before.items()};urban(after,[(4,2)])
    for k in [(3,2),(3,3)]:after[k].update(population=12.0,built_surface_m2=6.0)
    e=candidate_events(before,after,CFG,1975,1980)[0]
    assert e['status']=='independent_growth_candidate'
    assert e['stable_footprint_population_delta']==4.0
    after[3,2]['population']=8.0
    assert candidate_events(before,after,CFG,1975,1980)[0]['status']=='no_candidate'


def test_edge_components_are_censored():
    before=world();urban(before,[(0,2),(0,3)])
    after={k:v.copy() for k,v in before.items()};urban(after,[(1,2)])
    assert candidate_events(before,after,CFG,1975,1980)[0]['status']=='boundary_censored'


def test_split_lineage_is_ambiguous():
    before=world();urban(before,[(3,2),(3,3),(3,4)])
    after={k:v.copy() for k,v in before.items()};after[3,3]['settlement_class']=11
    assert candidate_events(before,after,CFG,1975,1980)[0]['status']=='ambiguous_lineage'


def test_different_observation_footprints_rejected():
    before=world();after=world();del after[0,0]
    with pytest.raises(ValueError,match='footprints'):
        candidate_events(before,after,CFG,1975,1980)


def test_district_boundary_ties_and_unassigned():
    polygons=[box(0,0,1,1),box(1,0,2,1)]
    points=shapely.points([0.5,1.0,3.0],[0.5,0.5,0.5])
    assignment,ties=assign_points(points,polygons,['B','A'])
    assert assignment.tolist()==[0,1,-1] and ties==1


def test_overlapping_district_interiors_rejected():
    with pytest.raises(ValueError,match='overlap'):
        assign_points(shapely.points([1.0],[1.0]),[box(0,0,2,2),box(0.5,0.5,3,3)],['A','B'])


def test_historical_periods_exclude_projections():
    assert periods([1975,1980,1985])==[(1975,1980),(1980,1985),(1975,1985)]
    with pytest.raises(ValueError,match='Historical'):periods([2020,2025])


def test_transition_zero_baselines_are_not_infinite(tmp_path):
    spark=(SparkSession.builder.master('local[2]').appName('temporal-regression')
           .config('spark.ui.enabled','false').config('spark.sql.shuffle.partitions','2')
           .config('spark.driver.bindAddress','127.0.0.1').getOrCreate())
    spark.sparkContext.setLogLevel('ERROR')
    try:
        df=spark.createDataFrame([(1975,'g','1_1',11,0.0,0.0,0.0,0.5),(1980,'g','1_1',23,10.0,100.0,2.0,0.5)],
            'year int,parent_grid_id string,parent_cell_id string,settlement_class int,population double,built_surface_m2 double,built_surface_nres_m2 double,aoi_fraction double')
        row=transitions(df,1975,1980).first()
        assert row.transition_type=='rural_to_urban' and row.population_delta==10.0
        assert row.population_growth_fraction is None and row.built_surface_m2_growth_fraction is None
        # Regression: projected Arrow data must not carry a stale embedded Spark schema.
        import pyarrow as pa
        import pyarrow.parquet as pq
        from assign_pilot_districts import mapping_table
        source=pa.table({'grid_id':['g'],'cell_id':['1_1'],'unused':[1]}).replace_schema_metadata(
            {b'org.apache.spark.sql.parquet.row.metadata':df.schema.json().encode()})
        path=tmp_path/'mapping.parquet'
        pq.write_table(mapping_table(source,['D1'],['District']),path)
        restored=spark.read.parquet(str(path))
        assert set(restored.columns)=={'grid_id','cell_id','district_id','district_name'}
        assert restored.first().district_id=='D1'
    finally:spark.stop()
