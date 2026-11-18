"""Phase-1 benchmark event interpretation and all-product key contracts."""
import json
from pathlib import Path
import sys
import numpy as np
import pyarrow.parquet as pq
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sedona_benchmark import event_metrics
PROJECT=Path(__file__).resolve().parents[2]


def test_event_metrics_attribute_only_timed_jobs(tmp_path):
    events=[dict(Event='SparkListenerJobStart',Properties={'spark.jobGroup.id':'trial'},**{'Stage IDs':[7]}),
            {'Event':'SparkListenerTaskEnd','Stage ID':6,'Task Metrics':{'Executor Run Time':999}},
            {'Event':'SparkListenerTaskEnd','Stage ID':7,'Task Metrics':{'Executor Run Time':8,'Executor CPU Time':900,'JVM GC Time':2,'Memory Bytes Spilled':12,'Disk Bytes Spilled':3,'Shuffle Read Metrics':{'Remote Bytes Read':4,'Local Bytes Read':5},'Shuffle Write Metrics':{'Shuffle Bytes Written':6}}}]
    (tmp_path/'events').write_text('\n'.join(json.dumps(e) for e in events))
    m=event_metrics(tmp_path)['trial']
    assert dict(m)==dict(executor_run_ms=8,executor_cpu_ns=900,gc_ms=2,memory_spill_bytes=12,disk_spill_bytes=3,shuffle_read_bytes=9,shuffle_write_bytes=6,tasks=1)


def test_all_product_staging_keys_and_native_parent_contract():
    prep=PROJECT/'integration/data/prepared/tables'
    expected=None
    for year in range(1975,2031,5):
        pop=pq.read_table(prep/'population'/f'{year}.parquet')
        built=pq.read_table(prep/'built_up'/f'{year}.parquet')
        smod=pq.read_table(prep/'settlement'/f'{year}.parquet')
        for c in ('year','source_row','source_col'):assert pop[c].equals(built[c])
        row=pop['source_row'].to_numpy().astype('int64');col=pop['source_col'].to_numpy().astype('int64')
        fine=row*1000000+col
        assert len(np.unique(fine))==len(fine)
        if expected is None:expected=fine
        else:assert np.array_equal(expected,fine)
        parents=(row//10)*1000000+col//10
        actual=smod['parent_row'].to_numpy().astype('int64')*1000000+smod['parent_col'].to_numpy().astype('int64')
        assert len(actual)==len(np.unique(actual))
        assert np.array_equal(np.unique(parents),np.sort(actual))
        assert set(pop['year'].to_pylist())=={year} and set(smod['year'].to_pylist())=={year}


def test_benchmark_protocol_declares_repetitions_and_correctness_gates():
    cfg=json.loads((PROJECT/'phase1/config/benchmark.json').read_text())
    assert cfg['measured_repetitions']>=5 and cfg['warmup_repetitions']>=1
    assert cfg['worker_counts']==[1,2]
    assert cfg['correctness_gates']['spatial_assignment_mismatches']==0
    assert cfg['correctness_gates']['source_archive_coverage_fraction']==1.0
