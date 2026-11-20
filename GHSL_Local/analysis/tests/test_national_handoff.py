"""Exercise final package auditing on small synthetic data, never national results."""
import json
from pathlib import Path
import sys
import zipfile
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import finalize_national_results as f


def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value))


def fixture(tmp,monkeypatch):
    monkeypatch.setattr(f,'PROJECT',tmp);monkeypatch.setattr(f,'ROOT',tmp/'analysis')
    monkeypatch.setenv('MPLCONFIGDIR',str(tmp/'matplotlib_cache'))
    integration=tmp/'integration/run';temporal=tmp/'analysis/temporal';districts=tmp/'analysis/districts';candidates=tmp/'analysis/candidates'
    for folder in (integration,temporal,districts,candidates):
        put(folder/'validation.json',dict(status='PASS'));(folder/'_SUCCESS').write_text('PASS')
    epochs=list(range(1975,2031,5))
    put(integration/'identity.json',dict(tiles=['R8_C26'],config=dict(epochs=epochs)))
    progress=[]
    for year in epochs:
        path=integration/'pairs'/f'R8_C26_{year}'/'spark_validation.json'
        put(path,dict(status='PASS',elapsed_seconds=1.0,analytical_rows=2,rejected_rows=0,sql_class_summary=[dict(population=3.,built_surface_m2=4.,built_surface_nres_m2=1.)]))
        raw=tmp/'raw'/f'{year}.zip';raw.parent.mkdir(exist_ok=True);raw.write_text('synthetic checksum fixture')
        progress.append(dict(tile='R8_C26',year=year,files={str(path.relative_to(integration)):f.digest(path)},inputs={str(raw.relative_to(tmp)):f.digest(raw)}))
    put(integration/'progress.json',progress)
    (districts/'district_summary').mkdir()
    pq.write_table(pa.Table.from_pylist([dict(year=y,district_id='D1',settlement_class=11,fine_cells=2,population=3.,built_surface_m2=4.,built_surface_nres_m2=1.) for y in epochs if y<=2020]),districts/'district_summary/part.parquet')
    put(temporal/'validation.json',dict(status='PASS',common_complete_cells=1,excluded_cells=0))
    (temporal/'concentration').mkdir()
    pq.write_table(pa.Table.from_pylist([dict(year=y,settlement_class=11,population_share=1.,built_surface_share=1.) for y in epochs if y<=2020]),temporal/'concentration/part.parquet')
    matrix=temporal/'periods/1975_2020/transition_matrix';matrix.mkdir(parents=True)
    pq.write_table(pa.table(dict(start_year=[1975],end_year=[2020],coarse_cells=[1])),matrix/'part.parquet')
    put(candidates/'validation.json',dict(status='PASS',events=1,event_counts=dict(no_candidate=1)))
    (candidates/'component_events.csv').write_text('status\nno_candidate\n')
    pq.write_table(pa.table(dict(status=['no_candidate'])),candidates/'component_events.parquet')
    put(candidates/'candidate_review.geojson',dict(type='FeatureCollection',features=[]))
    put(tmp/'analysis/data/boundaries/IND_ADM2.provenance.json',dict(test_fixture=True))
    (tmp/'integration/README.md').write_text('Synthetic test fixture')
    return integration,temporal,districts,candidates,tmp/'analysis/handoff'


def test_package_hashes_and_csv_output(tmp_path,monkeypatch):
    paths=fixture(tmp_path,monkeypatch)
    f.run(*paths)
    assert (paths[-1]/'_SUCCESS').exists()
    with zipfile.ZipFile(tmp_path/'GHSL_Weeks1_8_National_Handoff.zip') as z:
        assert z.testzip() is None
        manifest=json.loads(z.read('SHA256.json'))
        assert any(p.endswith('national_concentration.png') for p in manifest)
        assert any(p.endswith('district_summary.csv') for p in manifest)
        assert any(p.endswith('national_pipeline_performance.csv') for p in manifest)
    assert json.loads((paths[-1]/'validation.json').read_text())['district_conservation']=='PASS'


def test_package_rejects_changed_source_before_writing(tmp_path,monkeypatch):
    paths=fixture(tmp_path,monkeypatch)
    (tmp_path/'raw/1975.zip').write_text('tampered')
    with pytest.raises(ValueError,match='Raw archive hash mismatch'):f.run(*paths)
    assert not paths[-1].exists()


def test_package_rejects_district_value_loss(tmp_path,monkeypatch):
    paths=fixture(tmp_path,monkeypatch)
    path=paths[2]/'district_summary/part.parquet';table=pq.read_table(path)
    table=table.set_column(table.column_names.index('population'),'population',pa.array([2.]*len(table)))
    pq.write_table(table,path)
    with pytest.raises(ValueError,match='district value conservation'):f.run(*paths)
    assert not paths[-1].exists()


def test_package_includes_revised_phase2_evidence(tmp_path,monkeypatch):
    paths=fixture(tmp_path,monkeypatch)
    put(tmp_path/'phase2/reports/HANDOFF_VALIDATION.json',dict(status='PASS'))
    (tmp_path/'phase2/_SUCCESS').write_text('PASS')
    (tmp_path/'phase2/README.md').write_text('Reproduction guide')
    (tmp_path/'phase3').mkdir()
    (tmp_path/'phase3/README.md').write_text('Recovery guide')
    put(tmp_path/'phase3/reports/STATUS.json',dict(status='RUNNING',stage='handoff'))
    put(tmp_path/'analysis/data/regional_case_studies/validation.json',dict(status='PASS',coarse_cell_years=750))
    (tmp_path/'analysis/data/regional_case_studies/_SUCCESS').write_text('PASS')
    f.run(*paths)
    assert 'Apache Sedona' in (paths[-1]/'REPORT.md').read_text()
    with zipfile.ZipFile(tmp_path/'GHSL_Weeks1_8_National_Handoff.zip') as z:
        assert 'phase2/reports/HANDOFF_VALIDATION.json' in z.namelist()
        assert 'analysis/handoff/execution_status_snapshot.json' in z.namelist()
        assert 'phase3/reports/STATUS.json' not in z.namelist()


def test_package_discloses_accepted_coverage(tmp_path,monkeypatch):
    paths=fixture(tmp_path,monkeypatch)
    p=paths[0]/'identity.json';identity=json.loads(p.read_text())
    identity['coverage']=dict(warning='R8_C27 excluded; not complete India coverage.',policy='Missing coverage is not zero.',original_planned_pairs=24,excluded_tiles=['R8_C27'])
    put(p,identity)
    f.run(*paths)
    report=(paths[-1]/'REPORT.md').read_text()
    assert 'not complete India coverage' in report and 'Accepted: 12 of 24' in report
    assert json.loads((paths[-1]/'validation.json').read_text())['coverage']['excluded_tiles']==['R8_C27']
    with zipfile.ZipFile(tmp_path/'GHSL_Weeks1_8_National_Handoff.zip') as z:
        assert 'analysis/handoff/coverage.json' in z.namelist()
