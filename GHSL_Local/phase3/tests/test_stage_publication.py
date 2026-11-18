import json,sys
from pathlib import Path
import pytest
import pyarrow as pa
import pyarrow.parquet as pq
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_analysis_stage as stage

def source(tmp):
    p=tmp/'source';p.mkdir();(p/'_SUCCESS').write_text('PASS');(p/'validation.json').write_text(json.dumps({'status':'PASS'}))
    pq.write_table(pa.table({'value':[1,2,3]}),p/'part.parquet');return p

def test_valid_stage_publication_and_existing_output_rejected(tmp_path):
    p=source(tmp_path);dest=tmp_path/'out'
    assert stage.publish(p,dest)==3
    assert pq.read_table(dest/'part.parquet')['value'].to_pylist()==[1,2,3]
    with pytest.raises(FileExistsError):stage.publish(p,dest)

def test_corrupt_copy_never_published(tmp_path,monkeypatch):
    p=source(tmp_path);original=stage.shutil.copytree
    def corrupt(src,dst):
        original(src,dst);(Path(dst)/'part.parquet').write_bytes(b'')
    monkeypatch.setattr(stage.shutil,'copytree',corrupt)
    with pytest.raises(ValueError,match='checksum'):stage.publish(p,tmp_path/'out')
    assert not (tmp_path/'out').exists()
