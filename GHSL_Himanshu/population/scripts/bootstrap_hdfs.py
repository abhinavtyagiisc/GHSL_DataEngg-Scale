"""Install Maven + HDFS runtime locally without changing system Java or Hadoop."""
import hashlib
import os
from pathlib import Path
import subprocess
import tarfile
import jdk4py
import requests

ROOT=Path(__file__).resolve().parents[1]
runtime=ROOT/'runtime'
runtime.mkdir(parents=True,exist_ok=True)
name='apache-maven-3.9.9-bin.tar.gz'
url='https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.9.9/'+name
archive=runtime/name
if not archive.exists():
    response=requests.get(url,timeout=120)
    response.raise_for_status()
    archive.write_bytes(response.content)
checksum=requests.get(url+'.sha512',timeout=30)
checksum.raise_for_status()
with archive.open('rb') as stream:
    actual=hashlib.file_digest(stream,'sha512').hexdigest()
if actual!=checksum.text.strip().split()[0]:
    raise ValueError('Maven archive SHA512 verification failed')
if not (runtime/'apache-maven-3.9.9').exists():
    with tarfile.open(archive) as tar:
        tar.extractall(runtime,filter='data')
subprocess.run([str(runtime/'apache-maven-3.9.9/bin/mvn'),'-B',
                '-f',str(ROOT/'config/hdfs-pom.xml'),
                '-Dmaven.repo.local='+str(runtime/'maven-repository'),
                'dependency:copy-dependencies','-DincludeScope=runtime',
                '-DoutputDirectory='+str(runtime/'hdfs-libs')],
               env=dict(os.environ,JAVA_HOME=str(jdk4py.JAVA_HOME)),check=True)
print('HDFS dependencies ready; Maven archive SHA512 verified.')
