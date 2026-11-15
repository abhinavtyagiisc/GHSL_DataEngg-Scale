"""Independent Arrow comparison of every persisted column; numerical sum tolerance."""
from pathlib import Path
import json,sys
import numpy as np
import pyarrow.dataset as ds
import pyarrow.compute as pc
PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'analysis/scripts'));from progress_log import update

def compare(actual,reference,epoch=None):
    result={}
    for name,keys in [('analytical_100m',['year','source_row','source_col']),('summary_1km',['year','parent_row','parent_col']),('sql_class_summary',['year','settlement_class'])]:
        a=ds.dataset(str(Path(actual)/name),format='parquet',partitioning='hive').to_table(filter=ds.field("year")==epoch if epoch is not None else None).sort_by([(k,'ascending') for k in keys])
        b=ds.dataset(str(Path(reference)/name),format='parquet',partitioning='hive').to_table(filter=ds.field("year")==epoch if epoch is not None else None).sort_by([(k,'ascending') for k in keys])
        if set(a.column_names)!=set(b.column_names) or a.num_rows!=b.num_rows:raise ValueError(name+' shape mismatch')
        diffs={}
        for c in b.column_names:
            av,bv=a[c].combine_chunks(),b[c].combine_chunks()
            if av.null_count!=bv.null_count or not av.is_null().equals(bv.is_null()):raise ValueError(c+' null mismatch')
            if c in ['population','built_surface_m2','built_surface_nres_m2','aoi_fraction']:
                x,y=av.to_numpy(zero_copy_only=False),bv.to_numpy(zero_copy_only=False)
                if not np.allclose(x,y,rtol=1e-10,atol=1e-5,equal_nan=True):raise ValueError(c+' value mismatch')
                diffs[c]=float(np.nanmax(np.abs(x-y))) if len(x) else 0
            elif not pc.all(pc.fill_null(pc.equal(av,bv),True)).as_py():raise ValueError(c+' mismatch')
        result[name]=dict(rows=a.num_rows,columns=len(a.column_names),maximum_absolute_differences=diffs)
    return result
if __name__=='__main__':
    result=compare(PROJECT/'phase2/data/grid_year',PROJECT/'integration/data/curated/grid_year')
    (PROJECT/'phase2/reports/reference_comparison.json').write_text(json.dumps(dict(status='PASS',datasets=result),indent=2))
    update('Independent all-column comparison of HDFS Sedona outputs','PASS','Every native/coarse/SQL output agrees with preserved key-join reference; see phase2/reports/reference_comparison.json')
    print(json.dumps(result,indent=2))
