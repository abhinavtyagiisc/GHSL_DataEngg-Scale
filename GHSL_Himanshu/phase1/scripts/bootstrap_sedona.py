"""Download pinned Sedona JVM dependencies into project-local storage."""
from pathlib import Path
import hashlib
import json
import sys
import requests
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'analysis/scripts'))
from progress_log import update


def main():
    target=ROOT/'runtime/jars';target.mkdir(parents=True,exist_ok=True)
    specs=[('org/apache/sedona','sedona-spark-shaded-3.5_2.12','1.9.1'),
           ('org/datasyslab','geotools-wrapper','1.9.1-33.5')]
    records=[]
    try:
        for group,artifact,version in specs:
            name=f'{artifact}-{version}.jar'
            url=f'https://repo.maven.apache.org/maven2/{group}/{artifact}/{version}/{name}'
            path=target/name
            for algorithm in ('sha512','sha256','sha1'):
                checksum=requests.get(url+'.'+algorithm,timeout=60)
                if checksum.status_code==404:continue
                checksum.raise_for_status();expected=checksum.text.strip().split()[0];break
            else:raise ValueError('No published dependency checksum available')
            if not path.exists():
                response=requests.get(url,timeout=(30,180),stream=True);response.raise_for_status()
                temp=path.with_suffix('.jar.part')
                with temp.open('wb') as f:
                    for chunk in response.iter_content(1024*1024):f.write(chunk)
                if hashlib.new(algorithm,temp.read_bytes()).hexdigest()!=expected:raise ValueError('Remote checksum mismatch')
                temp.replace(path)
            if hashlib.new(algorithm,path.read_bytes()).hexdigest()!=expected:raise ValueError('Cached JAR checksum mismatch')
            records.append(dict(artifact=artifact,version=version,url=url,path=str(path.relative_to(PROJECT)),bytes=path.stat().st_size,
                                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),remote_checksum_algorithm=algorithm,remote_checksum=expected))
            update('Download/verify '+name,'PASS','Pinned Maven Central dependency verified against its published checksum; local SHA256 also recorded; cached locally under phase1/runtime/jars.')
        (ROOT/'runtime/jar_manifest.json').write_text(json.dumps(records,indent=2)+'\n')
        print(json.dumps(records,indent=2))
    except Exception as exc:
        update('Bootstrap pinned Sedona JVM dependencies','FAILED',str(exc));raise


if __name__=='__main__':main()
