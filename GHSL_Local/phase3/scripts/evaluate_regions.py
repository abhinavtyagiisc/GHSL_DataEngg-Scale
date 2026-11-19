"""Independent raw-raster accuracy checks for predeclared national study windows."""
import argparse,csv,hashlib,json,math,sys
from contextlib import ExitStack
from pathlib import Path
import numpy as np
import pyarrow.dataset as ds
import rasterio
from rasterio.windows import from_bounds,Window
from pyproj import Transformer
PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'population/src'));from prepare_population_rasters import zipped_raster
sys.path.insert(0,str(PROJECT/'analysis/scripts'));from progress_log import update
METRICS={'population':'POP','built_surface_m2':'BUILT_S','built_surface_nres_m2':'BUILT_S_NRES'}

def raw_cell(dataset,grid,row,col,resolution):
    x=grid['origin_x']+col*1000;y=grid['origin_y']-row*1000
    window=from_bounds(x,y-1000,x+1000,y,dataset.transform)
    parts=[window.col_off,window.row_off,window.width,window.height]
    if not np.allclose(parts,np.round(parts),rtol=0,atol=1e-6):raise ValueError('Raw study window is misaligned')
    data=dataset.read(1,window=Window(*[round(v) for v in parts]),boundless=True,masked=True)
    expected=(1000//resolution)**2
    if data.size!=expected or data.count()!=expected:raise ValueError('Complete output cell has missing raw values')
    return np.asarray(data,dtype='float64')

def check_cell(saved,datasets,grid,config):
    row,col=saved['parent_row'],saved['parent_col'];result={}
    for metric,product in METRICS.items():
        expected=float(raw_cell(datasets[product],grid,row,col,100).sum());actual=saved[metric]
        if actual is None or not math.isclose(actual,expected,rel_tol=config['relative_tolerance'],abs_tol=config['absolute_tolerance']):raise ValueError(f'Raw/persisted {metric} mismatch at {row},{col}')
        result[metric+'_absolute_difference']=abs(actual-expected)
    code=int(raw_cell(datasets['SMOD'],grid,row,col,1000)[0,0])
    if saved['settlement_class']!=code:raise ValueError('Raw/persisted settlement class mismatch')
    result['settlement_class']=code
    return result

def run(source,out):
    source=Path(source);out=Path(out)
    if not (source/'_SUCCESS').exists():raise ValueError('National integration incomplete')
    if out.exists():raise FileExistsError(out)
    cfg=json.loads((PROJECT/'phase3/config/case_studies.json').read_text());identity=json.loads((source/'identity.json').read_text());grid=identity['grid']
    transform=Transformer.from_crs('EPSG:4326',grid['crs'],always_xy=True)
    comparisons=[];summaries=[]
    for region in cfg['regions']:
        x,y=transform.transform(region['lon'],region['lat']);row=math.floor((grid['origin_y']-y)/1000);col=math.floor((x-grid['origin_x'])/1000)
        radius=cfg['radius_coarse_cells'];tiles={f'R{r//1000+1}_C{c//1000+1}' for r in range(row-radius,row+radius+1) for c in range(col-radius,col+radius+1)}
        for year in cfg['epochs']:
            accepted=[]
            for tile in sorted(tiles):
                pair=source/'pairs'/f'{tile}_{year}'
                manifest=json.loads((pair/'sources.json').read_text())
                paths={r['product']:PROJECT/'population'/r['path'] for r in manifest}
                for record in manifest:
                    with paths[record['product']].open('rb') as f:
                        if hashlib.file_digest(f,'sha256').hexdigest()!=record['sha256']:raise ValueError('Source changed during regional evaluation')
                query=(ds.field('parent_row')>=row-radius)&(ds.field('parent_row')<=row+radius)&(ds.field('parent_col')>=col-radius)&(ds.field('parent_col')<=col+radius)&(ds.field('expected_pixel_count')==100)&(ds.field('is_complete')==True)
                saved=ds.dataset(pair/'curated/summary_1km',format='parquet',partitioning='hive').to_table(filter=query).to_pylist()
                with ExitStack() as stack:
                    datasets={p:stack.enter_context(rasterio.open(zipped_raster(path))) for p,path in paths.items()}
                    for cell in saved:
                        result=check_cell(cell,datasets,grid,cfg)
                        accepted.append(dict(region=region['name'],year=year,parent_row=cell['parent_row'],parent_col=cell['parent_col'],**result))
            if len(accepted)<cfg['minimum_complete_cells_per_region_epoch']:raise ValueError('Insufficient complete case-study cells')
            comparisons.extend(accepted);summaries.append(dict(region=region['name'],year=year,cells=len(accepted),class_agreement_fraction=1.0,**{metric+'_max_absolute_difference':max(r[metric+'_absolute_difference'] for r in accepted) for metric in METRICS}))
            update('Independent raw-raster case study '+region['name']+'/'+str(year),'PASS',f'{len(accepted)} complete coarse cells checked for all three numerical products and matching-year class.')
    out.mkdir(parents=True)
    for name,rows in [('cell_comparisons.csv',comparisons),('region_summary.csv',summaries)]:
        with (out/name).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    report=dict(status='PASS',config=cfg,regions=len(cfg['regions']),region_epochs=len(summaries),coarse_cell_years=len(comparisons),native_cell_years=len(comparisons)*100,classification_agreement_fraction=1.0,maximum_absolute_differences={m:max(r[m+'_absolute_difference'] for r in comparisons) for m in METRICS},interpretation=cfg['interpretation'])
    (out/'validation.json').write_text(json.dumps(report,indent=2));(out/'_SUCCESS').write_text('PASS\n')
    update('Complete independent regional raw-raster evaluation','PASS',f'{len(comparisons)} coarse cell-years checked. This is processing accuracy, not external candidate ground truth.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--integration',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.integration,a.output)
