"""Actual Sedona regressions: year selection, zero/null and coverage defects."""
import json
from pathlib import Path
import sys
import pytest
PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'phase2/src'))
from integrate import session, join_products, key_join, validate_inputs, decorate, aggregate_joined, round_trip

@pytest.fixture(scope='module')
def spark():
    s=session();yield s;s.stop()

@pytest.fixture
def inputs(spark):
    pop=spark.createDataFrame([(2000,9,9,0.),(2000,10,10,None),(2005,9,9,7.),(2005,10,10,8.)], 'year int,source_row int,source_col int,population double')
    built=spark.createDataFrame([(y,r,c,5.,1.) for y,r,c in [(2000,9,9),(2000,10,10),(2005,9,9),(2005,10,10)]], 'year int,source_row int,source_col int,built_surface_m2 double,built_surface_nres_m2 double')
    smod=spark.createDataFrame([(2000,0,0,11),(2000,1,1,21),(2005,0,0,30),(2005,1,1,23)], 'year int,parent_row int,parent_col int,settlement_class int')
    return pop,built,smod

def test_spatial_matches_key_and_missing_policy(spark,inputs):
    grid=json.loads((PROJECT/'integration/config/grid_contract.json').read_text())
    validate_inputs(*inputs,[2000,2005])
    actual=decorate(join_products(*inputs,grid),grid)
    expected=decorate(key_join(*inputs),grid)
    round_trip(expected,actual,['year','source_row','source_col'])
    rows={(r.year,r.source_row):r for r in actual.collect()}
    assert rows[2000,9].population==0 and rows[2000,9].is_valid
    assert rows[2005,9].settlement_class==30
    assert rows[2000,10].population is None and not rows[2000,10].is_valid
    coarse=aggregate_joined(actual).filter('year=2000 AND parent_row=1').first()
    assert not coarse.is_complete and coarse.population is None and coarse.built_surface_m2==5
    assert coarse.aoi_fraction==0.01

def test_duplicate_rejected(inputs):
    p,b,s=inputs
    with pytest.raises(ValueError,match='duplicate key'):validate_inputs(p.union(p),b,s,[2000,2005])

def test_missing_parent_rejected(inputs):
    p,b,s=inputs
    with pytest.raises(ValueError,match='unmatched'):validate_inputs(p,b,s.filter('NOT (year=2005 AND parent_row=1)'),[2000,2005])
