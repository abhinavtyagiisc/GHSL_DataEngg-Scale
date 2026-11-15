"""Scientific-correctness regression tests: counts, nulls, grid alignment, epochs."""
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
from affine import Affine
from rasterio.crs import CRS

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from prepare import validate_alignment
from spark_population import aggregate
from pyspark.sql import SparkSession

def raster(size, x=0, crs='ESRI:54009'):
    return SimpleNamespace(crs=CRS.from_string(crs),transform=Affine(size,0,x,0,-size,10000))

def test_exact_alignment():
    validate_alignment(raster(100),raster(1000))

def test_half_pixel_shift_rejected():
    with pytest.raises(ValueError,match='misaligned'):
        validate_alignment(raster(100,x=50),raster(1000))

def test_wrong_crs_rejected():
    with pytest.raises(ValueError,match='CRS'):
        validate_alignment(raster(100,crs='EPSG:4326'),raster(1000))

def test_wrong_resolution_rejected():
    with pytest.raises(ValueError,match='100 m'):
        validate_alignment(raster(90),raster(1000))

@pytest.fixture(scope='module')
def spark():
    session=(SparkSession.builder.master('local[2]').appName('population-regressions')
             .config('spark.ui.enabled','false').config('spark.sql.shuffle.partitions','2')
             .config('spark.driver.bindAddress','127.0.0.1').getOrCreate())
    session.sparkContext.setLogLevel('ERROR')
    yield session
    session.stop()

def test_conservative_aggregation_missing_zero_boundary_and_epochs(spark):
    rows=[(1975,1,1,2.5)]*100 + [(1980,1,1,3.0)]*100
    rows += [(1975,1,2,0.0)]*100  # A valid unpopulated cell.
    rows += [(1975,1,3,None)]*100 # Unknown population must stay null.
    rows += [(1975,1,4,4.0)]*99+[(1975,1,4,None)]
    rows += [(1975,1,5,2.0)]*25   # An AOI boundary: do not extrapolate.
    df=spark.createDataFrame(rows,'year int, grid_row int, grid_col int, population_100m double')
    result={(r.year,r.grid_col):r for r in aggregate(df).collect()}
    assert result[1975,1].population==250.0
    assert result[1980,1].population==300.0
    assert result[1975,2].population==0.0
    assert result[1975,2].valid_pixel_count==100
    assert result[1975,3].population is None
    assert result[1975,3].valid_pixel_count==0
    assert result[1975,3].expected_pixel_count==100
    assert result[1975,4].population==396.0
    assert result[1975,4].valid_pixel_count==99
    assert result[1975,5].population==50.0
    assert result[1975,5].expected_pixel_count==25
    assert sum(r.population or 0 for r in result.values())==sum(r[3] or 0 for r in rows)
