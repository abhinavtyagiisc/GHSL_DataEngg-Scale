"""Run pilot connectivity/overlap candidate screening and sensitivity checks."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from settlement_components import candidate_events

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent


def pairs(epochs):return list(zip(epochs,epochs[1:]))+[(epochs[0],epochs[-1])]


def run(source,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    cfg=json.loads((ROOT/'config/pilot.json').read_text())
    dataset=ds.dataset(source,format='parquet',partitioning='hive')
    observations={}
    for year in cfg['historical_epochs']:
        rows=dataset.to_table(filter=ds.field('year')==year).to_pylist()
        if any(not r['is_complete'] for r in rows):raise ValueError('Incomplete source observations')
        by_cell={(r['parent_row'],r['parent_col']):r for r in rows}
        if len(by_cell)!=len(rows):raise ValueError('Duplicate coarse source cells')
        observations[year]=by_cell
    if len({frozenset(v) for v in observations.values()})!=1:raise ValueError('Historical footprints differ')
    output.mkdir(parents=True)
    sensitivity=[];primary=[]
    for connectivity,growth in [(8,0.1),(4,0.1),(8,0.25)]:
        settings=dict(cfg,connectivity=connectivity,minimum_growth_fraction=growth)
        events=[]
        for start,end in pairs(cfg['historical_epochs']):
            events.extend(candidate_events(observations[start],observations[end],settings,start,end))
        counts=dict(Counter(e['status'] for e in events))
        sensitivity.append(dict(connectivity=connectivity,minimum_growth_fraction=growth,event_counts=counts))
        if connectivity==cfg['connectivity'] and growth==cfg['minimum_growth_fraction']:primary=events
    if not primary:raise ValueError('No baseline non-centre components found; inspect the study extent')
    pq.write_table(pa.Table.from_pylist(primary),output/'component_events.parquet',compression='snappy')
    with (output/'component_events.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(primary[0]));writer.writeheader();writer.writerows(primary)
    result=dict(status='PASS',config=cfg,screened_events=len(primary),event_counts=dict(Counter(e['status'] for e in primary)),
        sensitivity=sensitivity,scope='Bengaluru pilot; exploratory morphological candidates, not confirmed administrative settlements',
        method='Same-year urban components, persistent-overlap lineage, pre-existing class-30 centre connectivity; positive stable-footprint population and built-up deltas for independent growth',
        limitations=['Pilot-edge components are censored','Splits and non-centre mergers are ambiguous',
                     'Connectivity is spatial adjacency, not evidence of economic integration',
                     'Absorption candidates require external case-study validation'])
    (output/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    (output/'_SUCCESS').write_text('PASS\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',default=str(PROJECT/'integration/data/curated/grid_year/summary_1km'))
    p.add_argument('--output',default=str(ROOT/'data/pilot_candidates'))
    a=p.parse_args();run(a.input,a.output)
