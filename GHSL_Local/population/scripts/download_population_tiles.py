"""Download the official JRC pilot tiles, with resumable per-file reuse and checksums."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import time
import zipfile
import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL'

def download(item):
    url, path = item
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        for attempt in range(4):
            try:
                with requests.get(url, stream=True, timeout=(30, 180)) as r:
                    r.raise_for_status()
                    with path.with_suffix('.part').open('wb') as f:
                        for chunk in r.iter_content(1024 * 1024):
                            f.write(chunk)
                with zipfile.ZipFile(path.with_suffix('.part')) as z:
                    bad = z.testzip()
                    if bad:
                        raise ValueError(f'Corrupt ZIP member: {bad}')
                path.with_suffix('.part').replace(path)
                break
            except (requests.RequestException, zipfile.BadZipFile, ValueError):
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
    with zipfile.ZipFile(path) as z:
        if z.testzip():
            raise ValueError(f'Corrupt archive: {path}')
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    print(f'Validated {path.name} ({path.stat().st_size:,} bytes)', flush=True)
    return dict(url=url, path=str(path.relative_to(ROOT)), bytes=path.stat().st_size, sha256=digest)

def main():
    cfg = json.loads((ROOT / 'config/pilot.json').read_text())
    if (cfg['release'],cfg['population_version'],cfg['reference_version'])!=('R2023A','V1_0','V2_0'):
        raise ValueError('This pipeline supports R2023A POP V1_0 / SMOD V2_0 only')
    items = []
    for year in cfg['epochs']:
        stem = f'GHS_POP_E{year}_GLOBE_R2023A_54009_100'
        filename = f'{stem}_V1_0_{cfg["tile"]}.zip'
        items.append((f'{BASE}/GHS_POP_GLOBE_R2023A/{stem}/V1-0/tiles/{filename}', ROOT/'data/raw/downloads'/filename))
    stem = f'GHS_SMOD_E{cfg["reference_epoch"]}_GLOBE_R2023A_54009_1000'
    filename = f'{stem}_V2_0_{cfg["tile"]}.zip'
    items.append((f'{BASE}/GHS_SMOD_GLOBE_R2023A/{stem}/V2-0/tiles/{filename}', ROOT/'data/raw/reference'/filename))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(download, items))
    (ROOT/'reports/download_manifest.json').write_text(json.dumps(results, indent=2)+'\n')

if __name__ == '__main__':
    main()
