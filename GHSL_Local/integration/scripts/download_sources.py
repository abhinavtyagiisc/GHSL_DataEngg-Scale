"""Acquire official native pilot archives, preserving the existing population cache."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
POP=ROOT.parent/'population'
sys.path.insert(0,str(POP/'scripts'))
from download_population_tiles import download, BASE


def sources(cfg):
    for year in cfg['epochs']:
        for product,resolution,version,version_dir,folder in [
            ('POP',100,'V1_0','V1-0','downloads'),
            ('SMOD',1000,'V2_0','V2-0','reference'),
            ('BUILT_S',100,'V1_0','V1-0','built_up'),
            ('BUILT_S_NRES',100,'V1_0','V1-0','built_up')]:
            stem=f'GHS_{product}_E{year}_GLOBE_R2023A_54009_{resolution}'
            name=f'{stem}_{version}_{cfg["tile"]}.zip'
            family = 'BUILT_S' if product.startswith('BUILT_S') else product
            yield dict(product=product,year=year,url=f'{BASE}/GHS_{family}_GLOBE_R2023A/{stem}/{version_dir}/tiles/{name}',
                       path=POP/'data/raw'/folder/name)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=ROOT/'reports/download_manifest_full.json')
    args=parser.parse_args()
    cfg=json.loads((ROOT/'config/pilot.json').read_text())
    items=list(sources(cfg))
    previous = {(r['product'],r['year']):r for r in json.loads(args.manifest.read_text())} if args.manifest.exists() else {}
    if previous and set(previous)!={(r['product'],r['year']) for r in items}:
        raise ValueError('Saved manifest does not match the requested source inventory')
    def acquire(item):
        return dict(product=item['product'],year=item['year'],**download((item['url'],item['path'])))
    with ThreadPoolExecutor(max_workers=3) as pool:
        records=list(pool.map(acquire,items))
    for record in records:
        old=previous.get((record['product'],record['year']))
        if old and any(old[k]!=record[k] for k in ('url','path','sha256','bytes')):
            raise ValueError('Source differs from the saved manifest; preserve it and investigate')
    if not previous:
        args.manifest.write_text(json.dumps(records,indent=2)+'\n')
    print(f'{len(records)} validated source archives; {sum(r["bytes"] for r in records):,} bytes')


if __name__=='__main__':main()
