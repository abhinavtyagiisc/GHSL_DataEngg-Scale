from pathlib import Path
import sys
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from contextlib import ExitStack
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from evaluate_regions import check_cell

def test_independent_raw_sum_and_reject_changed_saved_value(tmp_path):
    grid={'origin_x':0,'origin_y':1000};cfg={'relative_tolerance':1e-10,'absolute_tolerance':1e-5}
    with ExitStack() as stack:
        datasets={}
        for name,value in [('POP',2),('BUILT_S',4),('BUILT_S_NRES',0),('SMOD',23)]:
            n=1 if name=='SMOD' else 10;path=tmp_path/f'{name}.tif'
            with rasterio.open(path,'w',driver='GTiff',width=n,height=n,count=1,dtype='int16',nodata=-9999,transform=from_origin(0,1000,1000/n,1000/n)) as dst:dst.write(np.full((n,n),value,dtype='int16'),1)
            datasets[name]=stack.enter_context(rasterio.open(path))
        saved=dict(parent_row=0,parent_col=0,population=200.,built_surface_m2=400.,built_surface_nres_m2=0.,settlement_class=23)
        assert check_cell(saved,datasets,grid,cfg)['population_absolute_difference']==0
        with pytest.raises(ValueError,match='population mismatch'):check_cell(dict(saved,population=199.),datasets,grid,cfg)
        with pytest.raises(ValueError,match='class mismatch'):check_cell(dict(saved,settlement_class=30),datasets,grid,cfg)
