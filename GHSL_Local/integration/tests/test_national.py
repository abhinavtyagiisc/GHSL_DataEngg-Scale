"""Real raster windows across a tile seam, cropped coverage, and checkpoint safety."""
import json
from pathlib import Path
import sys
import zipfile
import numpy as np
import pyarrow.parquet as pq
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.windows import Window
from shapely.geometry import box
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import national as n

GRID=json.loads((n.ROOT/'config/grid_contract.json').read_text())


def archive(tmp,tile,product,cropped=False,shift=0):
    west,south,east,north=n.tile_bounds(tile,GRID)
    res=1000 if product=='SMOD' else 100
    width=1000000//res
    left=west+(100 if cropped else 0)+shift
    tif=tmp/f'{tile}_{product}.tif'
    with rasterio.open(tif,'w',driver='GTiff',width=width-int(cropped),height=width,count=1,
                       dtype='int16',crs=GRID['crs'],transform=from_origin(left,north,res,res),
                       nodata=-9999,compress='deflate',tiled=True,SPARSE_OK=True) as dst:
        # Small strip adjacent to the seam at north edge.
        col=width-10 if tile=='R8_C25' else 0
        w=Window(col,0,min(10,dst.width-col),10)
        value={'POP':2,'BUILT_S':4,'BUILT_S_NRES':1,'SMOD':22}[product]
        dst.write(np.full((10,int(w.width)),value,dtype='int16'),1,window=w)
    z=tmp/f'{tile}_{product}.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as f:f.write(tif,tif.name)
    return z


def test_seam_cropped_extent_and_nodata(tmp_path):
    west,south,east,north=n.tile_bounds('R8_C25',GRID)
    area=box(east-1000,north-1000,east+1000,north)
    keys=[];parents=[]
    for tile in ('R8_C25','R8_C26'):
        paths={p:archive(tmp_path,tile,p,cropped=(tile=='R8_C26' and p.startswith('BUILT'))) for p in n.PRODUCTS}
        out=tmp_path/tile
        report=n.prepare_pair(paths,tile,2020,area,GRID,out,10)
        pop=pq.read_table(out/'tables/population/part.parquet').to_pylist()
        smod=pq.read_table(out/'tables/settlement/part.parquet').to_pylist()
        assert report['fine_rows']==100 and report['coarse_rows']==1
        assert report['products']['POP']['total']==200
        assert report['products']['BUILT_S']['nodata_pixels']==(10 if tile=='R8_C26' else 0)
        keys.extend((r['source_row'],r['source_col']) for r in pop)
        parents.extend((r['parent_row'],r['parent_col']) for r in smod)
    assert len(set(keys))==200 and len(set(parents))==2


def test_shift_rejected(tmp_path):
    path=archive(tmp_path,'R8_C26','BUILT_S',shift=50)
    with rasterio.open(n.zipped_raster(path)) as src:
        with pytest.raises(ValueError,match='aligned'):n.validate_source(src,'R8_C26',GRID,100)


def test_resume_identity_and_tampering(tmp_path,monkeypatch):
    # Isolate checkpoint protocol without invoking Spark or network.
    monkeypatch.setattr(n,'load_area',lambda cfg:(box(1,1,2,2),{}))
    monkeypatch.setattr(n,'tiles_for_area',lambda *args:['R8_C26'])
    cfg=dict(name='test',epochs=[2020],release='R2023A',population_version='V1_0',built_version='V1_0',settlement_version='V2_0')
    out=tmp_path/'run'
    n.execute(cfg,out,max_pairs=0)
    with pytest.raises(ValueError,match='identity'):n.execute(dict(cfg,name='changed'),out,resume=True,max_pairs=0)
    artifact=out/'artifact';artifact.write_text('original')
    n.save(out/'progress.json',[dict(tile='R8_C26',year=2020,files={'artifact':n.digest(artifact)},inputs={})])
    artifact.write_text('tampered')
    with pytest.raises(ValueError,match='output changed'):n.execute(cfg,out,resume=True,max_pairs=0)


def test_interrupted_pair_is_preserved_and_checkpoint_skipped(tmp_path,monkeypatch):
    monkeypatch.setattr(n,'PROJECT',tmp_path)
    monkeypatch.setattr(n,'fingerprints',lambda:{})
    monkeypatch.setattr(n,'load_area',lambda cfg:(box(1,1,2,2),{}))
    monkeypatch.setattr(n,'tiles_for_area',lambda *args:['R8_C26'])
    source=tmp_path/'source.zip';source.write_bytes(b'test source')
    monkeypatch.setattr(n,'sources',lambda cfg:[dict(product=p,path=source,url='test') for p in n.PRODUCTS])
    monkeypatch.setattr(n,'download',lambda item:dict(path='source.zip',sha256=n.digest(source)))
    calls=[]
    def prepare(paths,tile,year,area,grid,out,block_pixels):
        calls.append(year)
        out.mkdir();(out/'tables').mkdir();(out/'tables/payload').write_text('temporary')
        return dict(fine_rows=1,coarse_rows=1)
    monkeypatch.setattr(n,'prepare_pair',prepare)
    def pipeline(prep,input_prefix,output,report,master):
        Path(output).mkdir();(Path(output)/'_INTEGRATION_SUCCESS').write_text('PASS')
        n.save(report,dict(status='PASS'))
    monkeypatch.setattr(n,'pipeline',pipeline)
    cfg=dict(name='test',epochs=[2015,2020],release='R2023A',population_version='V1_0',built_version='V1_0',settlement_version='V2_0')
    out=tmp_path/'run'
    n.execute(cfg,out,max_pairs=1)
    assert calls==[2015] and not (out/'_SUCCESS').exists()
    # Simulate a partial second pair left by a crash.
    partial=out/'pairs/R8_C26_2020';partial.mkdir();(partial/'partial.txt').write_text('evidence')
    n.execute(cfg,out,resume=True)
    assert calls==[2015,2020]
    assert (out/'_SUCCESS').exists()
    assert len(list((out/'incomplete').glob('*/partial.txt')))==1
    assert not list((out/'pairs').glob('*/prepared/tables'))


def test_publication_rejects_zero_byte_parquet(tmp_path):
    source=tmp_path/'source';source.mkdir();(source/'_INTEGRATION_SUCCESS').write_text('PASS')
    (source/'part.parquet').write_bytes(b'')
    with pytest.raises(ValueError,match='Zero-byte'):n.publish_curated(source,tmp_path/'dest')
    assert not (tmp_path/'dest').exists()


def test_publication_rejects_copy_corruption(tmp_path,monkeypatch):
    source=tmp_path/'source';source.mkdir();(source/'_INTEGRATION_SUCCESS').write_text('PASS')
    (source/'payload').write_bytes(b'correct')
    original=n.shutil.copytree
    def corrupt(src,dst):
        original(src,dst);(Path(dst)/'payload').write_bytes(b'changed')
    monkeypatch.setattr(n.shutil,'copytree',corrupt)
    with pytest.raises(ValueError,match='checksum'):n.publish_curated(source,tmp_path/'dest')
    assert not (tmp_path/'dest').exists()
    assert (tmp_path/'dest.publishing/payload').exists()


def test_deferred_pass_refreshes_and_never_marks_unresolved_complete(tmp_path,monkeypatch):
    monkeypatch.setattr(n,'PROJECT',tmp_path)
    monkeypatch.setattr(n,'fingerprints',lambda:{})
    monkeypatch.setattr(n,'load_area',lambda cfg:(box(1,1,2,2),{}))
    monkeypatch.setattr(n,'tiles_for_area',lambda *args:['R8_C27','R9_C26','R9_C28'])
    source=tmp_path/'source.zip';source.write_bytes(b'original')
    monkeypatch.setattr(n,'sources',lambda cfg:[dict(product=p,path=source,url='test') for p in n.PRODUCTS])
    downloaded=[]
    def download(item):
        path=item[1];path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():path.write_bytes(b'fresh')
        downloaded.append(path)
        return dict(path=str(path.relative_to(tmp_path)),sha256=n.digest(path))
    monkeypatch.setattr(n,'download',download)
    calls=[]
    def prepare(paths,tile,year,area,grid,out,block_pixels):
        out.mkdir();(out/'tables').mkdir()
        return dict(fine_rows=1,coarse_rows=1)
    monkeypatch.setattr(n,'prepare_pair',prepare)
    def pipeline(prep,input_prefix,output,report,master):
        tile=prep.parent.name.rsplit('_',1)[0];calls.append(tile)
        if tile=='R8_C27' or (tile=='R9_C26' and calls.count(tile)==1):
            raise ValueError('An epoch has no valid analytical cells')
        Path(output).mkdir();(Path(output)/'_INTEGRATION_SUCCESS').write_text('PASS')
        n.save(report,dict(status='PASS'))
    monkeypatch.setattr(n,'pipeline',pipeline)
    cfg=dict(name='test',epochs=[2020],release='R2023A',population_version='V1_0',built_version='V1_0',settlement_version='V2_0')
    out=tmp_path/'run'
    with pytest.raises(ValueError,match='remain unresolved'):
        n.execute(cfg,out,allow_download=True,defer_empty=True)
    assert calls==['R9_C26','R9_C28','R8_C27','R9_C26']
    assert not (out/'_SUCCESS').exists()
    assert len(json.loads((out/'progress.json').read_text()))==2
    assert [d['status'] for d in json.loads((out/'deferred.json').read_text())]==['UNRESOLVED','RESOLVED']
    assert len([p for p in downloaded if 'deferred_retries' in p.parts])==8
    assert source.read_bytes()==b'original'
    assert len(list((out/'incomplete').iterdir()))==1
