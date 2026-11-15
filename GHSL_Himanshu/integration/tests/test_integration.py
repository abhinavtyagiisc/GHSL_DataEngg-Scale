"""Scientific and join-contract regressions for three-product integration."""
from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from spark_integrate import (SparkSession,join_products,decorate,aggregate_joined,
                             validate_inputs,unique_keys,match_keys)
from prepare_inputs import validate_values


@pytest.fixture(scope='module')
def spark():
    s=(SparkSession.builder.master('local[2]').appName('three-product-tests')
       .config('spark.ui.enabled','false').config('spark.sql.shuffle.partitions','2')
       .config('spark.driver.bindAddress','127.0.0.1').getOrCreate())
    s.sparkContext.setLogLevel('ERROR')
    yield s
    s.stop()


def inputs(spark):
    pop=spark.createDataFrame([(1975,0,0,2.5),(1975,0,1,0.0),(1975,0,10,4.0),(1980,0,0,9.0)],
        'year int, source_row int, source_col int, population double')
    built=spark.createDataFrame([(1975,0,0,25.0,5.0),(1975,0,1,0.0,0.0),(1975,0,10,None,None),(1980,0,0,30.0,10.0)],
        'year int, source_row int, source_col int, built_surface_m2 double, built_surface_nres_m2 double')
    smod=spark.createDataFrame([(1975,0,0,11),(1975,0,1,21),(1980,0,0,30)],
        'year int, parent_row int, parent_col int, settlement_class int')
    return pop,built,smod


def test_join_preserves_native_values_and_matching_year_categories(spark):
    pop,built,smod=inputs(spark)
    validate_inputs(pop,built,smod,[1975,1980])
    joined=decorate(join_products(pop,built,smod),{'fine_grid_id':'fine','grid_id':'coarse'})
    rows={(r.year,r.source_col):r for r in joined.collect()}
    assert rows[1975,0].population==2.5 and rows[1975,0].settlement_class==11
    assert rows[1980,0].population==9 and rows[1980,0].settlement_class==30
    assert rows[1975,1].population==0 and rows[1975,1].is_valid
    assert not rows[1975,10].is_valid and rows[1975,10].built_surface_m2 is None
    coarse={(r.year,r.parent_col):r for r in aggregate_joined(joined).collect()}
    assert coarse[1975,0].population==2.5
    assert coarse[1975,0].built_surface_m2==25
    assert coarse[1975,0].built_surface_nres_m2==5
    assert coarse[1975,0].aoi_fraction==0.02
    assert coarse[1975,1].built_surface_m2 is None
    assert coarse[1975,1].analytical_pixel_count==0


def test_duplicate_join_keys_rejected(spark):
    pop,_,_=inputs(spark)
    with pytest.raises(ValueError,match='duplicate'):
        unique_keys(pop.unionByName(pop),['year','source_row','source_col'],'population')


def test_coverage_mismatch_rejected(spark):
    pop,built,_=inputs(spark)
    with pytest.raises(ValueError,match='unmatched'):
        match_keys(pop,built.filter('year=1975'),['year','source_row','source_col'],'coverage')


def test_missing_epoch_rejected(spark):
    pop,built,smod=inputs(spark)
    with pytest.raises(ValueError,match='epochs'):
        validate_inputs(pop,built,smod,[1975,1980,1985])


def test_invalid_continuous_and_category_values():
    valid=np.array([True])
    for value in (-1,float('nan'),float('inf')):
        with pytest.raises(ValueError,match='nonfinite'):
            validate_values(np.array([value]),valid,'POP')
    with pytest.raises(ValueError,match='cell area'):
        validate_values(np.array([10001]),valid,'BUILT_S')
    with pytest.raises(ValueError,match='class'):
        validate_values(np.array([99]),valid,'SMOD')


def test_cropped_native_tile_aligns_without_resampling():
    import rasterio
    from rasterio.io import MemoryFile
    from affine import Affine
    from types import SimpleNamespace
    from prepare_inputs import read_aligned
    ref=SimpleNamespace(crs=rasterio.crs.CRS.from_string('ESRI:54009'),transform=Affine(1000,0,0,0,-1000,2000),width=3,height=2)
    values=np.arange(400,dtype='uint16').reshape(20,20)
    with MemoryFile() as memory:
        with memory.open(driver='GTiff',width=20,height=20,count=1,dtype='uint16',nodata=65535,
                         crs=ref.crs,transform=Affine(100,0,1000,0,-100,2000)) as src:
            src.write(values,1)
            arr,affine=read_aligned(src,ref,(1000,0,3000,2000),100)
            np.testing.assert_array_equal(arr.data,values)
            assert affine==src.transform
            with pytest.raises(ValueError,match='cover'):
                read_aligned(src,ref,(0,0,3000,2000),100)


def test_half_pixel_shift_rejected_before_join():
    import rasterio
    from rasterio.io import MemoryFile
    from affine import Affine
    from types import SimpleNamespace
    from prepare_inputs import read_aligned
    ref=SimpleNamespace(crs=rasterio.crs.CRS.from_string('ESRI:54009'),transform=Affine(1000,0,0,0,-1000,2000))
    with MemoryFile() as memory:
        with memory.open(driver='GTiff',width=20,height=20,count=1,dtype='uint16',nodata=65535,
                         crs=ref.crs,transform=Affine(100,0,1050,0,-100,2000)) as src:
            with pytest.raises(ValueError,match='misaligned'):
                read_aligned(src,ref,(1000,0,3000,2000),100)
