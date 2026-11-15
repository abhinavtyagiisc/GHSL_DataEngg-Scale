"""Check remote archive availability without downloading raster contents."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import requests


def probe(item):
    try:
        response = requests.head(item['url'],allow_redirects=True,timeout=(20,60))
        return dict(url=item['url'],status=response.status_code,
                    content_length=int(response.headers['Content-Length']) if response.headers.get('Content-Length') else None)
    except requests.RequestException as exc:
        return dict(url=item['url'],status=None,error=str(exc))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    if args.report.exists():
        raise FileExistsError(args.report)
    plan=json.loads(args.plan.read_text())
    with ThreadPoolExecutor(max_workers=4) as pool:
        records=list(pool.map(probe,plan['sources']))
    result=dict(checked_at=datetime.now(timezone.utc).isoformat(),sources=records,
                available=sum(r['status']==200 for r in records),requested=len(records),
                known_download_bytes=sum(r.get('content_length') or 0 for r in records if r['status']==200),
                sizes_known=sum(r.get('content_length') is not None for r in records if r['status']==200))
    args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='sources'},indent=2))
    if result['available']!=result['requested']:
        raise SystemExit(1)
