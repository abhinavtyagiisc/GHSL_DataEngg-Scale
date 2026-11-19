"""Real Sedona spatial QA and reproducible phase-1 microbenchmarks."""
import argparse
from collections import defaultdict
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import threading
import time

import numpy as np
import psutil
import jdk4py
os.environ.setdefault('JAVA_HOME',str(jdk4py.JAVA_HOME))
os.environ.setdefault('SPARK_LOCAL_IP','127.0.0.1')
os.environ.setdefault('PYSPARK_PYTHON',sys.executable)
from sedona.spark import SedonaContext
from pyspark.sql import functions as F
from pyspark import StorageLevel
from shapely.geometry import box

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'analysis/src'));from summarize_national_districts import load_boundaries
sys.path.insert(0,str(PROJECT/'population/src'));from multitile_population import load_area,digest
sys.path.insert(0,str(PROJECT/'analysis/scripts'));from progress_log import update


class ResourceSample:
    """Sample aggregate process-tree RSS; shared pages may be counted more than once."""
    def __init__(self):self.stop=threading.Event();self.peak=0;self.cpu={};self.initial={}
    def sample(self):
        try:processes=[psutil.Process()]+psutil.Process().children(recursive=True)
        except psutil.Error:processes=[]
        rss=0
        for p in processes:
            try:
                rss+=p.memory_info().rss;t=p.cpu_times();value=t.user+t.system
                self.initial.setdefault(p.pid,value);self.cpu[p.pid]=value
            except psutil.Error:pass
        self.peak=max(self.peak,rss)
    def __enter__(self):
        self.sample()
        def loop():
            while not self.stop.wait(.1):self.sample()
        self.thread=threading.Thread(target=loop,daemon=True);self.thread.start();return self
    def __exit__(self,*args):self.stop.set();self.thread.join();self.sample()
    @property
    def cpu_seconds(self):return sum(v-self.initial[k] for k,v in self.cpu.items())


def event_metrics(directory):
    stage_groups={};metrics=defaultdict(lambda:defaultdict(int))
    for path in directory.rglob('*'):
        if not path.is_file() or path.name.startswith('.'):continue
        with path.open() as f:
            for line in f:
                try:event=json.loads(line)
                except json.JSONDecodeError:continue
                if event['Event']=='SparkListenerJobStart':
                    group=(event.get('Properties') or {}).get('spark.jobGroup.id')
                    if group:
                        for sid in event['Stage IDs']:stage_groups[sid]=group
                if event['Event']=='SparkListenerTaskEnd' and event['Stage ID'] in stage_groups:
                    group=stage_groups[event['Stage ID']];m=event.get('Task Metrics',{})
                    for original,name in [('Executor Run Time','executor_run_ms'),('Executor CPU Time','executor_cpu_ns'),('JVM GC Time','gc_ms'),('Memory Bytes Spilled','memory_spill_bytes'),('Disk Bytes Spilled','disk_spill_bytes')]:metrics[group][name]+=m.get(original,0)
                    read=m.get('Shuffle Read Metrics',{})
                    metrics[group]['shuffle_read_bytes']+=read.get('Remote Bytes Read',0)+read.get('Local Bytes Read',0)
                    metrics[group]['shuffle_write_bytes']+=m.get('Shuffle Write Metrics',{}).get('Shuffle Bytes Written',0)
                    metrics[group]['tasks']+=1
    return dict(metrics)


def run(workers,out):
    out=Path(out).resolve()
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True);events=out/'spark_events';events.mkdir()
    cfg=json.loads((ROOT/'config/benchmark.json').read_text())
    jars=json.loads((ROOT/'runtime/jar_manifest.json').read_text())
    for r in jars:
        if digest(PROJECT/r['path'])!=r['sha256']:raise ValueError('JAR checksum changed')
    start=time.monotonic()
    spark=(SedonaContext.builder().master(f'local[{workers}]').appName('GHSL-Phase1-Sedona')
        .config('spark.jars',','.join(str(PROJECT/r['path']) for r in jars))
        .config('spark.driver.memory','2g').config('spark.sql.shuffle.partitions','8')
        .config('spark.sql.adaptive.enabled','false').config('spark.ui.enabled','false')
        .config('spark.driver.bindAddress','127.0.0.1').config('spark.eventLog.enabled','true')
        .config('spark.eventLog.compress','false').config('spark.eventLog.dir',events.resolve().as_uri())
        .getOrCreate())
    spark=SedonaContext.create(spark);spark.sparkContext.setLogLevel('WARN')
    startup=time.monotonic()-start
    trials=[]
    try:
        grid=json.loads((PROJECT/'integration/config/grid_contract.json').read_text())
        pilot=json.loads((PROJECT/'integration/config/pilot.json').read_text())
        area,_=load_area(dict(bbox_wgs84=pilot['bbox_wgs84']))
        polygons,metadata,provenance=load_boundaries()
        records=[(metadata[i+1]['district_id'],g.wkt) for i,g in enumerate(polygons) if g.intersects(area.envelope)]
        districts=(spark.createDataFrame(records,'district_id string,wkt string')
                   .select('district_id',F.expr('ST_GeomFromWKT(wkt)').alias('district_geom')).cache())
        if districts.filter('NOT ST_IsValid(district_geom)').count():raise ValueError('Sedona invalid district geometry')
        districts.count()
        x,y=grid['origin_x'],grid['origin_y']
        points=(spark.read.parquet(str(PROJECT/'integration/data/prepared/tables/population/1975.parquet'))
                .select('source_row','source_col').withColumn('cell_id',F.concat_ws('_','source_row','source_col'))
                .withColumn('point',F.expr(f'ST_Point({x}+(source_col+0.5)*100.0,{y}-(source_row+0.5)*100.0)'))
                .repartition(8).cache())
        total=points.count()
        if total!=434363:raise ValueError('Unexpected pilot footprint')
        country,_=load_area(dict(boundary='data/raw/boundaries/geoBoundaries-IND-ADM0.geojson'))
        country=country.intersection(area.envelope.buffer(1000))
        countrydf=spark.createDataFrame([(country.wkt,)],'wkt string').select(F.expr('ST_GeomFromWKT(wkt)').alias('country_geom'))
        if points.join(F.broadcast(countrydf),F.expr('ST_Covers(country_geom,point)')).count()!=total:raise ValueError('Pilot centres outside country mask')
        parents=points.withColumn('parent_geom',F.expr(f'ST_PolygonFromEnvelope({x}+floor(source_col/10)*1000.0,{y}-(floor(source_row/10)+1)*1000.0,{x}+(floor(source_col/10)+1)*1000.0,{y}-floor(source_row/10)*1000.0)'))
        if parents.filter('NOT ST_Covers(parent_geom,point) OR abs(ST_Area(parent_geom)-1000000.0)>0.001').count():raise ValueError('Fine-to-parent spatial mapping failed')
        def joined(frame):return frame.join(F.broadcast(districts),F.expr('ST_Covers(district_geom,point)')).select('cell_id','district_id')
        full=joined(points).persist(StorageLevel.DISK_ONLY)
        if full.count()!=total or full.select('cell_id').distinct().count()!=total:raise ValueError('Missing/duplicate Sedona assignments')
        reference=spark.read.parquet(str(PROJECT/'analysis/data/district_mapping/cell_district.parquet')).select('cell_id',F.col('district_id').alias('expected_id'))
        if full.join(reference,'cell_id','full').filter('district_id IS NULL OR expected_id IS NULL OR district_id != expected_id').count():raise ValueError('Sedona assignment differs from independent reference')
        full.write.parquet(str(out/'sedona_cell_district'))
        if spark.read.parquet(str(out/'sedona_cell_district')).exceptAll(full).count() or full.exceptAll(spark.read.parquet(str(out/'sedona_cell_district'))).count():raise ValueError('Spatial mapping round trip failed')
        full.unpersist()
        qa_seconds=time.monotonic()-start-startup
        for size in cfg['input_sizes']:
            sample=points.orderBy('source_row','source_col').limit(size).repartition(8).cache()
            if sample.count()!=size:raise ValueError('Incorrect benchmark sample size')
            expected={r.expected_id:r['count'] for r in sample.select('cell_id').join(reference,'cell_id').groupBy('expected_id').count().collect()}
            query=joined(sample).groupBy('district_id').count()
            plan=query._jdf.queryExecution().executedPlan().toString()
            (out/f'plan_{size}.txt').write_text(plan)
            if 'BroadcastIndexJoin' not in plan and 'RangeJoin' not in plan:raise ValueError('Sedona spatial join operator not found')
            for repetition in range(cfg['warmup_repetitions']+cfg['measured_repetitions']):
                group=f'w{workers}_n{size}_r{repetition}';spark.sparkContext.setJobGroup(group,group)
                # New QueryExecution/RDD DAG for every action: repeated collect on
                # one DataFrame can reuse shuffle results even without cache().
                query=joined(sample).groupBy('district_id').count()
                with ResourceSample() as resources:
                    t=time.perf_counter();actual={r.district_id:r['count'] for r in query.collect()};seconds=time.perf_counter()-t
                spark.sparkContext.setLocalProperty('spark.jobGroup.id',None)
                spark.sparkContext.setLocalProperty('spark.job.description',None)
                if actual!=expected:raise ValueError('Benchmark result differs from reference')
                trial=dict(group=group,workers=workers,rows=size,repetition=repetition,warmup=repetition<cfg['warmup_repetitions'],wall_seconds=seconds,rows_per_second=size/seconds,process_tree_peak_rss_bytes=resources.peak,process_tree_cpu_seconds=resources.cpu_seconds)
                trials.append(trial);print(json.dumps(trial),flush=True)
            sample.unpersist()
        environment=dict(python=sys.version,spark=spark.version,sedona=importlib.metadata.version('apache-sedona'),java=spark._jvm.java.lang.System.getProperty('java.version'),scala=spark._jvm.scala.util.Properties.versionNumberString(),platform=platform.platform(),logical_cpus=psutil.cpu_count(),physical_cpus=psutil.cpu_count(logical=False),ram_bytes=psutil.virtual_memory().total,master=spark.sparkContext.master,shuffle_partitions=8)
    finally:spark.stop()
    tasks=event_metrics(events)
    for trial in trials:
        if trial['group'] not in tasks:raise ValueError('Missing Spark task metrics for timed trial')
        trial['spark_task_metrics']=tasks[trial['group']]
        if trial['spark_task_metrics']['tasks']<16:
            raise ValueError('Timed trial did not execute both 8-partition spatial-map and aggregate stages')
    summaries=[]
    for size in cfg['input_sizes']:
        selected=[r for r in trials if r['rows']==size and not r['warmup']]
        seconds=[r['wall_seconds'] for r in selected]
        summaries.append(dict(rows=size,repetitions=len(seconds),median_seconds=float(np.median(seconds)),p95_seconds=float(np.percentile(seconds,95)),median_rows_per_second=size/float(np.median(seconds)),peak_rss_bytes=max(r['process_tree_peak_rss_bytes'] for r in selected)))
    result=dict(status='PASS',environment=environment,config=cfg,spatial_qa=dict(cells=total,district_polygons=len(records),assignment_mismatches=0,parent_mapping_errors=0,country_mask_errors=0,independent_reference='Shapely centre-to-polygon assignments; exact cell-level equality',boundary=provenance),startup_seconds=startup,spatial_qa_and_preparation_seconds=qa_seconds,trials=trials,summaries=summaries,elapsed_seconds=time.monotonic()-start,
        measurement_notes='Cached inputs; uncached spatial join result. RSS sampled at 100 ms over Python/JVM descendants; shared pages may be counted multiple times. CPU excludes work between samples for short-lived processes. Percentile estimates use five measured repetitions.')
    (out/'validation.json').write_text(json.dumps(result,indent=2)+'\n');(out/'_SUCCESS').write_text('PASS\n')
    update(f'Sedona spatial validation and local[{workers}] benchmark','PASS',f'Exact assignment agreement on {total:,} cells; three input sizes with five measured repetitions. Evidence: `{out.relative_to(PROJECT)}/validation.json`.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,choices=[1,2],required=True);p.add_argument('--output',required=True);a=p.parse_args()
    try:run(a.workers,a.output)
    except Exception as exc:update('Sedona spatial validation/benchmark','FAILED',str(exc));raise
