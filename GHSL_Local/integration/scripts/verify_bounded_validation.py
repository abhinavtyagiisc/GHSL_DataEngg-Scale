"""Compare the new bounded-runner validation subset with the completed pilot."""
import json
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.compute as pc

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'data/bounded_validation_run1'


def main():
    if not (RUN/'_SUCCESS').exists():raise ValueError('Bounded validation run incomplete')
    results=[]
    for year in (2015,2020):
        for name,keys in [('analytical_100m',['grid_id','cell_id','year']),
                          ('summary_1km',['parent_grid_id','parent_cell_id','year'])]:
            old=ds.dataset(ROOT/'data/curated/grid_year'/name,format='parquet',partitioning='hive').to_table(filter=ds.field('year')==year)
            new=ds.dataset(RUN/'pairs'/f'R8_C26_{year}'/'curated'/name,format='parquet',partitioning='hive').to_table()
            assert set(old.column_names)==set(new.column_names)
            old=old.sort_by([(k,'ascending') for k in keys])
            new=new.sort_by([(k,'ascending') for k in keys])
            assert len(old)==len(new)
            for col in old.column_names:
                a=old[col].combine_chunks();b=new[col].combine_chunks()
                assert a.is_valid().equals(b.is_valid()),col
                if pa.types.is_floating(a.type):
                    assert np.allclose(a.to_numpy(),b.to_numpy(),rtol=1e-10,atol=1e-5,equal_nan=True),col
                else:
                    assert a.cast(b.type).equals(b),col
            results.append(dict(year=year,dataset=name,rows=len(new),columns=len(new.column_names),comparison='PASS'))
    progress=json.loads((RUN/'progress.json').read_text())
    assert len(progress)==2
    for r in progress:
        assert not (RUN/'pairs'/f"{r['tile']}_{r['year']}"/'prepared/tables').exists()
    report=dict(status='PASS',comparisons=results,staging_removed=True,
                floating_tolerance=dict(relative=1e-10,absolute=1e-5),
                scope='Cached pilot validation of bounded national runner; not national execution')
    path=ROOT/'reports/bounded_validation_comparison.json'
    with path.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
