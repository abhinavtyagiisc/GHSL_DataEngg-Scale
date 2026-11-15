"""Finish the real HDFS run, preserve prior output, collect evidence, stop services."""
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
PYTHON=sys.executable
HDFS=str(ROOT/'scripts/hdfs.py')

def run(arguments,log,timeout=180):
    with (ROOT/'reports'/log).open('w') as f:
        subprocess.run([PYTHON,*arguments],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)

def main():
    # Preserve the first output; it was written but its validation was interrupted
    # by a Spark executor heartbeat timeout. Never delete or overwrite it.
    run([HDFS,'dfs','-mv','/ghsl/population/curated/population_1km',
         '/ghsl/population/curated/population_1km_prior_'+str(time.time_ns())],'hdfs_preserve_attempt.log')
    run([str(ROOT/'src/spark_population.py'),
         '--input','hdfs://127.0.0.1:19000/ghsl/population/cleaned/population_100m',
         '--output','hdfs://127.0.0.1:19000/ghsl/population/curated/population_1km',
         '--report','spark_hdfs_validation.json'],'spark_hdfs_final.log',timeout=600)
    run([HDFS,'dfs','-get','/ghsl/population/curated/population_1km',
         str(ROOT/'data/curated/population_1km_from_hdfs')],'hdfs_download_output.log')
    run([HDFS,'fsck','/ghsl/population','-files','-blocks'],'hdfs_fsck.txt')
    run([HDFS,'dfsadmin','-report'],'hdfs_cluster_final.txt')
    run([HDFS,'dfs','-ls','-R','/ghsl/population'],'hdfs_files.txt')
    run([HDFS,'stop'],'hdfs_stop.log')
    print('HDFS execution and health checks passed; services stopped.',flush=True)

if __name__=='__main__':main()
