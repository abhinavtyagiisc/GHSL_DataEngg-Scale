"""Fetch and preserve a fixed geoBoundaries district snapshot and its provenance."""
import hashlib
import json
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
API='https://www.geoboundaries.org/api/current/gbOpen/IND/ADM2/'

def main():
    out=ROOT/'data/boundaries'
    path=out/'IND_ADM2.geojson';meta_path=out/'IND_ADM2.provenance.json'
    if path.exists() and meta_path.exists():
        meta=json.loads(meta_path.read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest()!=meta['sha256']:raise ValueError('District file changed')
        print('Reused validated district snapshot');return
    if path.exists() or meta_path.exists():raise FileExistsError('Incomplete boundary acquisition; inspect before retry')
    r=requests.get(API,timeout=60);r.raise_for_status();meta=r.json()
    if meta['boundaryISO']!='IND' or meta['boundaryType']!='ADM2':raise ValueError('Wrong boundary dataset')
    r=requests.get(meta['gjDownloadURL'],timeout=180);r.raise_for_status()
    data=r.json()
    if data['type']!='FeatureCollection':raise ValueError('Expected GeoJSON feature collection')
    meta.update(metadata_url=API,sha256=hashlib.sha256(r.content).hexdigest(),feature_count=len(data['features']))
    path.write_bytes(r.content);meta_path.write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps({k:meta[k] for k in ('boundaryID','boundaryYearRepresented','boundaryLicense','feature_count')},indent=2))

if __name__=='__main__':main()
