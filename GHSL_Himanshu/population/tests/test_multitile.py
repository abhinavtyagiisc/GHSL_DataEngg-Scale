"""Regression tests for 100 m inheritance, area masks, and tile seams."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from affine import Affine
from rasterio.crs import CRS
from shapely.geometry import box, Polygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from multitile_population import (build_tables, table_digest, tiles_for_area, tile_bounds,
                                 validate_tile, aligned_windows, load_area, make_plan)

GRID = dict(origin_x=-18041000.0, origin_y=9000000.0, crs='ESRI:54009',
            grid_id='parent', fine_grid_id='fine')


def test_native_values_parent_classes_nulls_and_partial_cells(tmp_path):
    values = np.arange(200, dtype='float64').reshape(10,20)
    inside = np.ones((10,20), dtype=bool)
    inside[5:,10:] = False
    valid = np.ones_like(inside)
    valid[0,1] = False
    smod = np.array([[11,30]], dtype='int16')
    fine, coarse = build_tables(values, valid, inside, 100, 200, GRID, smod, np.ones((1,2),dtype=bool))
    rows = {r['cell_id']:r for r in fine.to_pylist()}
    assert len(rows) == 150
    assert rows['100_200']['population'] == 0.0
    assert rows['100_201']['population'] is None
    assert rows['100_209']['parent_cell_id'] == '10_20'
    assert rows['100_210']['parent_cell_id'] == '10_21'
    assert rows['100_209']['settlement_class'] == 11
    assert rows['100_210']['settlement_class'] == 30
    c = coarse.to_pylist()
    assert c[0]['valid_pixel_count'] == 99 and not c[0]['is_complete']
    assert c[1]['aoi_fraction'] == 0.5
    assert sum(r['population'] or 0 for r in c) == values[inside & valid].sum()
    path = tmp_path/'test.parquet'
    pq.write_table(fine,path)
    assert table_digest(fine) == table_digest(pq.ParquetFile(path).read())


def test_missing_population_and_missing_settlement_are_null():
    values = np.zeros((10,10))
    fine, coarse = build_tables(values, np.zeros((10,10),dtype=bool), np.ones((10,10),dtype=bool), 0,0,GRID)
    assert fine['population'].null_count == 100
    assert fine['settlement_class'].null_count == 100
    assert coarse['population'].to_pylist() == [None]
    assert coarse['coverage_fraction'].to_pylist() == [0.0]


def test_bad_class_negative_and_block_alignment_rejected():
    values = np.ones((10,10))
    valid = np.ones((10,10),dtype=bool)
    with pytest.raises(ValueError,match='classification'):
        build_tables(values,valid,valid,0,0,GRID,np.array([[99]]),np.array([[True]]))
    with pytest.raises(ValueError,match='nonfinite'):
        build_tables(-values,valid,valid,0,0,GRID)
    with pytest.raises(ValueError,match='align'):
        build_tables(values,valid,valid,1,0,GRID)


def test_tile_seam_includes_both_tiles_without_duplicate_ids():
    west,south,east,north = tile_bounds('R8_C26',GRID)
    area = box(east-500, north-2000, east+500, north-1000)
    assert tiles_for_area(area,GRID) == ['R8_C26','R8_C27']
    assert tiles_for_area(box(west,south,east,north),GRID) == ['R8_C26']
    values = np.ones((10,10)); valid = np.ones_like(values,dtype=bool)
    left,_ = build_tables(values,valid,valid,70000,259990,GRID)
    right,_ = build_tables(values,valid,valid,70000,260000,GRID)
    assert set(left['cell_id'].to_pylist()).isdisjoint(right['cell_id'].to_pylist())


def test_windows_align_and_cover_once():
    west,south,east,north = tile_bounds('R8_C26',GRID)
    src = SimpleNamespace(bounds=(west,south,east,north), transform=Affine(100,0,west,0,-100,north),width=10000,height=10000)
    area = box(west+123,north-4567,west+2345,north-234)
    windows = list(aligned_windows(area,src,20))
    cells = set()
    for w in windows:
        assert all(v%10==0 for v in (w.row_off,w.col_off,w.height,w.width))
        for row in range(int(w.row_off),int(w.row_off+w.height)):
            for col in range(int(w.col_off),int(w.col_off+w.width)):
                assert (row,col) not in cells
                cells.add((row,col))
    assert len(cells)==30*50
    with pytest.raises(ValueError,match='multiple'):
        list(aligned_windows(area,src,11))


def test_wrong_tile_origin_rejected():
    west,south,east,north = tile_bounds('R8_C26',GRID)
    src = SimpleNamespace(crs=CRS.from_string('ESRI:54009'),transform=Affine(100,0,west+100,0,-100,north),width=10000,height=10000,count=1)
    with pytest.raises(ValueError,match='origin'):
        validate_tile(src,'R8_C26',GRID,100)


def test_boundary_holes_and_provenance(tmp_path):
    geom = Polygon([(77,12),(78,12),(78,13),(77,13)], holes=[[(77.2,12.2),(77.2,12.4),(77.4,12.4),(77.4,12.2)]])
    from shapely.geometry import mapping
    p=tmp_path/'area.geojson'
    p.write_text(json.dumps(mapping(geom)))
    area, provenance = load_area({'boundary':str(p)})
    assert len(area.interiors)==1
    assert len(provenance['sha256'])==64
    with pytest.raises(ValueError,match='exactly one'):
        load_area({'boundary':str(p),'bbox_wgs84':[77,12,78,13]})


def test_two_tile_raster_execution_preserves_seam_and_classes(tmp_path):
    """Real Rasterio/ZIP/Parquet path across adjacent native GHSL-shaped tiles."""
    import rasterio
    from rasterio.windows import Window
    import zipfile
    from multitile_population import process_pair
    west,south,east,north = tile_bounds('R8_C26',GRID)
    area = box(east-1000,north-1000,east+1000,north)
    output = tmp_path/'run'
    ids = []
    for tile, col, coarse_col, value, category in [('R8_C26',9990,999,2.0,11),('R8_C27',0,0,3.0,30)]:
        x,_,_,y = tile_bounds(tile,GRID)
        paths = []
        for kind, size, dim, dtype, nodata, column, content in [
            ('pop',100,10000,'float32',-200,col,np.full((10,10),value,dtype='float32')),
            ('smod',1000,1000,'int16',0,coarse_col,np.array([[category]],dtype='int16'))]:
            tif=tmp_path/f'{tile}_{kind}.tif'
            with rasterio.open(tif,'w',driver='GTiff',width=dim,height=dim,count=1,dtype=dtype,
                               crs='ESRI:54009',transform=Affine(size,0,x,0,-size,y),nodata=nodata,
                               tiled=True,compress='deflate',SPARSE_OK='TRUE') as dst:
                dst.write(content,1,window=Window(column,0,content.shape[1],content.shape[0]))
            archive=tif.with_suffix('.zip')
            with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
                z.write(tif,tif.name)
            paths.append(archive)
        stats=process_pair(paths[0],paths[1],paths[1],tile,2020,area,GRID,output,10)
        assert stats['fine_rows']==100 and stats['coarse_rows']==1
        assert stats['population']==100*value
        table=pq.ParquetFile(output/'population_100m/epoch_type=historical/year=2020'/f'{tile}.parquet').read()
        assert set(table['settlement_class'].to_pylist())=={category}
        ids.extend(table['cell_id'].to_pylist())
    assert len(set(ids))==200


def test_resume_checks_hashes_skips_completed_and_preserves_partial(tmp_path, monkeypatch):
    import multitile_population as module
    cfg = json.loads((module.ROOT/'config/pilot_100m.json').read_text())
    cfg['epochs'] = [1975,1980]
    cfg['settlement_epochs'] = []
    plan, area = make_plan(cfg)
    monkeypatch.setattr(module,'download',lambda item: {'path':str(item[1].relative_to(module.ROOT)), 'sha256':'stable'})
    calls=[]
    def fake_process(pop, ref, smod, tile, year, area, grid, out, block_pixels):
        calls.append(year)
        p=out/'population_100m/epoch_type=historical'/f'year={year}'/f'{tile}.parquet'
        p.parent.mkdir(parents=True,exist_ok=True)
        if year==1980 and calls.count(1980)==1:
            p.with_suffix('.part').write_text('interrupted data')
            raise RuntimeError('test interruption')
        p.write_text(str(year))
        return dict(tile=tile,year=year,fine_rows=1,coarse_rows=1,files={str(p.relative_to(out)):module.digest(p)})
    monkeypatch.setattr(module,'process_pair',fake_process)
    out=tmp_path/'run'
    with pytest.raises(RuntimeError,match='interruption'):
        module.execute(plan,area,out,False,100)
    completed=out/'population_100m/epoch_type=historical/year=1975/R8_C26.parquet'
    completed.write_text('tampered')
    with pytest.raises(ValueError,match='output changed'):
        module.execute(plan,area,out,False,100,resume=True)
    completed.write_text('1975')
    report=module.execute(plan,area,out,False,100,resume=True)
    assert calls==[1975,1980,1980]
    assert report['status']=='PASS'
    assert (out/'_SUCCESS').exists() and not (out/'RUNNING').exists()
    assert list((out/'incomplete').rglob('*.part'))
    with pytest.raises(ValueError,match='already complete'):
        module.execute(plan,area,out,False,100,resume=True)
