"""Fresh-query, end-to-end all-product benchmark with validated persisted results."""
from pathlib import Path
import argparse,json,sys,time,platform,importlib.metadata
import numpy as np
PROJECT=Path(__file__).resolve().parents[2];ROOT=PROJECT/'phase2'
sys.path.insert(0,str(ROOT/'src'));from spark_sedona_integrate import session,join_products,key_join,decorate,aggregate_joined,F
sys.path.insert(0,str(PROJECT/'phase1/src'));from sedona_benchmark import ResourceSample,event_metrics
sys.path.insert(0,str(PROJECT/'analysis/scripts'));from progress_log import update
from compare_integration_outputs import compare

def run(mode,workers,partitions):
    cfg=json.loads((ROOT/'config/benchmark.json').read_text());grid=json.loads((PROJECT/'integration/config/grid_contract.json').read_text())
    name=f'{mode}_w{workers}_p{partitions}';out=ROOT/'reports/benchmarks'/name
    out.mkdir(parents=True,exist_ok=False)
    events=out/'events';start=time.perf_counter();spark=session(f'local[{workers}]',partitions,events)
    startup=time.perf_counter()-start;trials=[]
    env=dict(python=sys.version,platform=platform.platform(),spark=spark.version,sedona=importlib.metadata.version('apache-sedona'),master=spark.sparkContext.master,shuffle_partitions=partitions)
    try:
        for rep in range(cfg['warmups']+cfg['repetitions']):
            group=f'{name}_r{rep}';target=ROOT/'data/benchmarks'/group
            update('End-to-end benchmark '+group,'STARTED','Fresh read/join/aggregate/write; correctness comparison follows outside timer.')
            spark.sparkContext.setJobGroup(group,group)
            with ResourceSample() as resource:
                t=time.perf_counter()
                inputs=[spark.read.parquet(str(PROJECT/f'integration/data/prepared/tables/{kind}/{cfg["epoch"]}.parquet')) for kind in ['population','built_up','settlement']]
                joined=decorate(join_products(*inputs,grid) if mode=='sedona' else key_join(*inputs),grid)
                fine=joined.filter('is_valid');coarse=aggregate_joined(joined)
                summary=fine.groupBy('year','epoch_type','settlement_class').agg(F.count('*').alias('fine_cells'),*[F.sum(c).alias(c) for c in ['population','built_surface_m2','built_surface_nres_m2']])
                for label,frame in [('analytical_100m',fine),('summary_1km',coarse),('sql_class_summary',summary)]:
                    frame.write.mode('errorifexists').partitionBy('epoch_type','year').parquet(str(target/label))
                seconds=time.perf_counter()-t
            spark.sparkContext.setLocalProperty('spark.jobGroup.id',None);spark.sparkContext.setLocalProperty('spark.job.description',None)
            (out/f'plan_r{rep}.txt').write_text(joined._jdf.queryExecution().executedPlan().toString())
            validation=compare(target,PROJECT/'integration/data/curated/grid_year',cfg['epoch'])
            trial=dict(group=group,repetition=rep,warmup=rep<cfg['warmups'],wall_seconds=seconds,rows_per_second=cfg['rows']/seconds,process_tree_peak_rss_bytes=resource.peak,process_tree_cpu_seconds=resource.cpu_seconds,output_bytes=sum(p.stat().st_size for p in target.rglob('*.parquet')),validation=validation)
            trials.append(trial);(out/'trials.json').write_text(json.dumps(trials,indent=2))
            update('End-to-end benchmark '+group,'PASS',f'{seconds:.3f} seconds; all persisted columns match reference. See phase2/reports/benchmarks/'+name)
    finally:spark.stop()
    tasks=event_metrics(events)
    for trial in trials:
        trial['spark_task_metrics']=tasks[trial['group']]
        if not trial['spark_task_metrics']['tasks']:raise ValueError('No executed task metrics')
    measured=[t for t in trials if not t['warmup']];median=float(np.median([t['wall_seconds'] for t in measured]));peak=max(t['process_tree_peak_rss_bytes'] for t in measured)
    result=dict(status='PASS',mode=mode,environment=env,startup_seconds=startup,config=cfg,trials=trials,median_seconds=median,p95_seconds=float(np.percentile([t['wall_seconds'] for t in measured],95)),median_rows_per_second=cfg['rows']/median,peak_rss_bytes=peak,targets_pass=median<=cfg['targets']['median_seconds_max'] and cfg['rows']/median>=cfg['targets']['median_rows_per_second_min'] and peak<=cfg['targets']['peak_rss_bytes_max'])
    (out/'validation.json').write_text(json.dumps(result,indent=2));(out/'_SUCCESS').write_text('PASS\n')
    update('Complete benchmark '+name,'PASS',f'Median {median:.3f} s; target result {result["targets_pass"]}. Correctness passed for every trial.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['key','sedona'],required=True);p.add_argument('--workers',type=int,required=True);p.add_argument('--partitions',type=int,required=True);a=p.parse_args();run(a.mode,a.workers,a.partitions)
