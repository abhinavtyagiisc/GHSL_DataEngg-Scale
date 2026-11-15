"""Isolated single-node HDFS. All state lives in population/runtime; loopback only."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import jdk4py

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'runtime'
CONF=RUNTIME/'hdfs-conf'
URI='hdfs://127.0.0.1:19000'
CLASSES={'namenode':'org.apache.hadoop.hdfs.server.namenode.NameNode',
         'datanode':'org.apache.hadoop.hdfs.server.datanode.DataNode',
         'dfs':'org.apache.hadoop.fs.FsShell',
         'fsck':'org.apache.hadoop.hdfs.tools.DFSck',
         'dfsadmin':'org.apache.hadoop.hdfs.tools.DFSAdmin'}

def setup():
    CONF.mkdir(parents=True,exist_ok=True)
    # Maven server jars exclude the distribution's web UI. Supply minimal web
    # contexts; HDFS RPC, block storage, health reporting and WebHDFS are real.
    for name in ('hdfs','datanode','static'):
        web=CONF/'webapps'/name
        web.mkdir(parents=True,exist_ok=True)
        (web/'index.html').write_text('<!doctype html><title>GHSL local HDFS</title><p>Local HDFS pilot. Use scripts/hdfs.py dfsadmin -report for cluster status. The Apache distribution web UI is not installed.</p>')
    configs={
        'core-site.xml':{'fs.defaultFS':URI,'hadoop.tmp.dir':str(RUNTIME/'hdfs-tmp'),
                         'hadoop.security.authentication':'simple'},
        'hdfs-site.xml':{'dfs.replication':'1','dfs.namenode.name.dir':(RUNTIME/'namenode').as_uri(),
                         'dfs.datanode.data.dir':(RUNTIME/'datanode').as_uri(),
                         'dfs.namenode.rpc-address':'127.0.0.1:19000',
                         'dfs.namenode.http-address':'127.0.0.1:19870',
                         'dfs.datanode.address':'127.0.0.1:19866',
                         'dfs.datanode.ipc.address':'127.0.0.1:19867',
                         'dfs.datanode.http.address':'127.0.0.1:19864',
                         'dfs.datanode.hostname':'127.0.0.1',
                         'dfs.client.use.datanode.hostname':'true',
                         'dfs.namenode.datanode.registration.ip-hostname-check':'false',
                         'dfs.permissions.enabled':'true','dfs.namenode.safemode.min.datanodes':'1'}}
    for name,properties in configs.items():
        (CONF/name).write_text('<configuration>'+''.join(
            f'<property><name>{k}</name><value>{v}</value></property>' for k,v in properties.items())+'</configuration>')
    (CONF/'log4j.properties').write_text('log4j.rootLogger=INFO,console\nlog4j.appender.console=org.apache.log4j.ConsoleAppender\nlog4j.appender.console.layout=org.apache.log4j.PatternLayout\nlog4j.appender.console.layout.ConversionPattern=%d %p %c: %m%n\n')

def command(kind,*args):
    jars=[str(p) for p in sorted((RUNTIME/'hdfs-libs').glob('*.jar'))
          if not p.name.startswith(('slf4j-log4j12-','log4j-1.2.'))]
    return [str(jdk4py.JAVA_HOME/'bin/java'),'-Xmx512m',
            '--add-opens=java.base/java.lang=ALL-UNNAMED',
            '-cp',os.pathsep.join([str(CONF),*jars]),CLASSES[kind],*args]

def run(kind,*args,**kwargs):
    return subprocess.run(command(kind,*args),check=True,**kwargs)

def start():
    setup()
    if not (RUNTIME/'namenode/current/VERSION').exists():
        run('namenode','-format','-nonInteractive','ghsl-population-pilot')
    for kind in ('namenode','datanode'):
        pidfile=RUNTIME/f'{kind}.pid'
        if pidfile.exists():
            try:
                os.kill(int(pidfile.read_text()),0)
                continue
            except ProcessLookupError:
                pass
        with (ROOT/f'reports/hdfs_{kind}.log').open('a') as log:
            proc=subprocess.Popen(command(kind),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        pidfile.write_text(str(proc.pid))
    for _ in range(30):
        try:
            report=run('dfsadmin','-report',capture_output=True,text=True).stdout
            if 'Live datanodes (1)' in report:
                run('dfsadmin','-safemode','wait',timeout=60)
                (ROOT/'reports/hdfs_cluster.txt').write_text(report)
                print('Single-node HDFS ready at '+URI)
                return
        except subprocess.CalledProcessError:
            pass
        time.sleep(1)
    raise RuntimeError('HDFS failed to start; inspect reports/hdfs_*.log')

def stage():
    for target in ('raw/downloads','raw/reference','cleaned/population_100m'):
        exists=subprocess.run(command('dfs','-test','-e','/ghsl/population/'+target),
                              capture_output=True).returncode
        if exists==0:
            raise RuntimeError('HDFS data already staged; use existing data instead of nesting another copy')
        if exists!=1:
            raise RuntimeError('Cannot check HDFS destination; verify the cluster is running')
    for zone in ('raw','cleaned','curated'):
        run('dfs','-mkdir','-p',f'/ghsl/population/{zone}')
    for local,remote in [('data/raw/downloads','raw/downloads'),('data/raw/reference','raw/reference'),
                         ('data/cleaned/population_100m','cleaned/population_100m')]:
        run('dfs','-put',str(ROOT/local),'/ghsl/population/'+remote)
    for tif in sorted((ROOT/'data/cleaned').glob('*.tif')):
        run('dfs','-put',str(tif),'/ghsl/population/cleaned/')
    listing=run('dfs','-ls','-R','/ghsl/population',capture_output=True,text=True).stdout
    (ROOT/'reports/hdfs_files.txt').write_text(listing)

def stop():
    for kind in ('datanode','namenode'):
        pidfile=RUNTIME/f'{kind}.pid'
        if pidfile.exists():
            pid=int(pidfile.read_text())
            # Check identity before signalling a PID that may have been reused.
            process=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout
            if CLASSES[kind] in process and str(CONF) in process:
                os.kill(pid,signal.SIGTERM)
            pidfile.unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['start','stop','stage','dfs','dfsadmin','fsck'])
    args,rest=p.parse_known_args()
    if args.action in ('dfs','dfsadmin','fsck'):
        run(args.action,*rest)
    else:
        globals()[args.action]()
