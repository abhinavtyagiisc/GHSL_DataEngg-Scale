"""Read-only independent temporal/rule review using saved accepted-coverage outputs."""
import csv,json,math
from collections import Counter
from pathlib import Path
import pyarrow.dataset as ds
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'phase3/reports/regional_validation'
def run():
    OUT.mkdir(exist_ok=False)
    cfg=json.loads((ROOT/'phase3/config/case_studies.json').read_text())
    grid=json.loads((ROOT/'integration/config/grid_contract.json').read_text())
    project=Transformer.from_crs('EPSG:4326',grid['crs'],always_xy=True)
    data=ds.dataset(ROOT/'analysis/data/temporal_analysis/historical_common',format='parquet',partitioning='hive')
    events=ds.dataset(ROOT/'analysis/data/settlement_candidates/component_events.parquet',format='parquet').to_table().to_pylist()
    policy=json.loads((ROOT/'analysis/config/pilot.json').read_text())
    for e in events:
        if e['boundary_censored']:expected='boundary_censored'
        elif e['baseline_cells']<policy['minimum_baseline_cells']:expected='below_minimum_size'
        elif e['split'] or e['retained_fraction']<policy['minimum_retained_fraction']:expected='ambiguous_lineage'
        elif e['connected_to_preexisting_centre']:expected='metropolitan_absorption_candidate'
        elif e['merge']:expected='ambiguous_lineage'
        elif e['component_area_growth_fraction']>=0.1 and e['stable_footprint_population_delta']>0 and e['stable_footprint_built_surface_delta_m2']>0:expected='independent_growth_candidate'
        else:expected='no_candidate'
        assert expected==e['status'],e
    states={};summaries=[];regional_events=[];examples=[]
    for reg in cfg['regions']:
        x,y=project.transform(reg['lon'],reg['lat']);r=math.floor((grid['origin_y']-y)/1000);c=math.floor((x-grid['origin_x'])/1000)
        # Fixed 31 x 31 km square, including surrounding settlements; common mask only.
        q=(ds.field('parent_row')>=r-15)&(ds.field('parent_row')<=r+15)&(ds.field('parent_col')>=c-15)&(ds.field('parent_col')<=c+15)
        rows=data.to_table(filter=q).to_pylist();state={(v['parent_cell_id'],v['year']):v for v in rows};keys={v['parent_cell_id'] for v in rows}
        assert len(state)==len(keys)*10
        states[reg['name']]=(state,keys)
        before=[state[k,1975] for k in keys];after=[state[k,2020] for k in keys]
        pop0=sum(v['population'] for v in before);pop1=sum(v['population'] for v in after);built0=sum(v['built_surface_m2'] for v in before);built1=sum(v['built_surface_m2'] for v in after)
        ru=sum(state[k,1975]['settlement_class'] in [11,12,13] and state[k,2020]['settlement_class'] in [21,22,23,30] for k in keys)
        summaries.append(dict(region=reg['name'],common_cells=len(keys),rural_to_urban_cells_1975_2020=ru,population_1975=pop0,population_2020=pop1,population_growth_percent=100*(pop1/pop0-1),built_m2_1975=built0,built_m2_2020=built1,built_growth_percent=100*(built1/built0-1)))
        local=[e for e in events if abs(e['representative_row']-r)<=15 and abs(e['representative_col']-c)<=15]
        for status,count in sorted(Counter(e['status'] for e in local).items()):regional_events.append(dict(region=reg['name'],status=status,events=count))
        for status in ['metropolitan_absorption_candidate','independent_growth_candidate']:
            selected=sorted([e for e in local if e['status']==status],key=lambda e:(e['start_year'],e['end_year'],e['baseline_component']))[:3]
            examples.extend(dict(region=reg['name'],**e) for e in selected)
    checked=0
    allkeys=set().union(*(keys for state,keys in states.values()))
    for period in sorted((ROOT/'analysis/data/temporal_analysis/periods').iterdir()):
        start,end=map(int,period.name.split('_'))
        records=ds.dataset(period/'cell_transitions',format='parquet').to_table(filter=ds.field('parent_cell_id').isin(list(allkeys))).to_pylist();saved={v['parent_cell_id']:v for v in records}
        assert len(saved)==len(allkeys)
        for state,keys in states.values():
            for k in keys:
                a,b=state[k,start],state[k,end];v=saved[k];ca,cb=a['settlement_class'],b['settlement_class']
                expected=('rural_to_urban' if ca in [11,12,13] and cb in [21,22,23,30] else 'urban_to_rural' if ca in [21,22,23,30] and cb in [11,12,13] else 'water_involved' if 10 in [ca,cb] else 'unchanged_class' if ca==cb else 'other_class_change')
                assert v['transition_type']==expected
                for metric in ['population','built_surface_m2','built_surface_nres_m2']:
                    delta=b[metric]-a[metric];assert math.isclose(v[metric+'_delta'],delta,rel_tol=1e-10,abs_tol=1e-5)
                    actual=v[metric+'_growth_fraction'];expected_growth=delta/a[metric] if a[metric]>0 else None
                    assert actual is None if expected_growth is None else math.isclose(actual,expected_growth,rel_tol=1e-10,abs_tol=1e-10)
                checked+=1
    for name,rows in [('regional_growth.csv',summaries),('regional_event_counts.csv',regional_events),('candidate_examples.csv',examples)]:
        if rows:
            with (OUT/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    report=dict(status='PASS',regional_cell_periods_checked=checked,candidate_status_rules_checked=len(events),regions=summaries,scope='31x31 km study squares on historical common mask; events selected by representative cell, not full component containment',limitations='Temporal arithmetic and candidate-rule consistency against saved data; not external settlement ground truth or independent topology validation. Raw agreement is assessed separately in the 750-cell-year study.')
    (OUT/'validation.json').write_text(json.dumps(report,indent=2))
    lines=['# Regional analytical validation and interpretation','',report['scope'],'',f"Independently checked {checked:,} regional cell-period transitions and all {len(events):,} candidate status decisions against their stored evidence. No mismatches.",'','| Study region | Common cells | Rural-to-urban cells, 1975–2020 | Population growth | Built-surface growth |','|---|---:|---:|---:|---:|']
    for v in summaries:lines.append(f"| {v['region']} | {v['common_cells']:,} | {v['rural_to_urban_cells_1975_2020']:,} | {v['population_growth_percent']:.1f}% | {v['built_growth_percent']:.1f}% |")
    lines+=['','These percentages compare each measure with its own 1975 baseline. A larger built-surface percentage indicates faster proportional horizontal expansion, not a causal explanation or a measure of building height. Study squares are not administrative city boundaries.','',report['limitations'],'','Candidate examples and counts cover overlapping periods and representative-cell locations; they are not distinct or confirmed settlements. Mumbai uses the documented coverage-adjusted centre. R8_C27 remains excluded.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n');print(json.dumps(report))
if __name__=='__main__':run()
