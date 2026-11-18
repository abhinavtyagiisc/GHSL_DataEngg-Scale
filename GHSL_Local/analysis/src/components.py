"""Exploratory settlement lineage using deterministic raster-connected components."""
from collections import deque


def offsets(connectivity):
    if connectivity not in (4,8):raise ValueError('Connectivity must be 4 or 8')
    return [(r,c) for r in (-1,0,1) for c in (-1,0,1) if (r or c) and (connectivity==8 or abs(r)+abs(c)==1)]


def components(cells,urban_codes,centre_codes,connectivity=8):
    """cells maps (global row,col) to valid coarse observations; absent neighbours censor edges."""
    neighbours=offsets(connectivity)
    available={key for key,value in cells.items() if value['settlement_class'] in urban_codes}
    labels={};groups={}
    for seed in sorted(available):
        if seed not in available:continue
        identifier=f'{seed[0]}_{seed[1]}'
        queue=deque([seed]);available.remove(seed);members=set()
        while queue:
            cell=queue.popleft();members.add(cell);labels[cell]=identifier
            for dr,dc in neighbours:
                adjacent=(cell[0]+dr,cell[1]+dc)
                if adjacent in available:available.remove(adjacent);queue.append(adjacent)
        censored=any(cells[k].get('aoi_fraction',1)<1 or
                     any((k[0]+dr,k[1]+dc) not in cells for dr,dc in neighbours) for k in members)
        groups[identifier]=dict(cells=members,boundary_censored=censored,
            has_centre=any(cells[k]['settlement_class'] in centre_codes for k in members),
            population=sum(cells[k]['population'] for k in members),
            built_surface_m2=sum(cells[k]['built_surface_m2'] for k in members))
    return labels,groups


def candidate_events(before,after,cfg,start,end):
    if set(before)!=set(after):raise ValueError('Candidate analysis requires identical complete coarse footprints')
    labels0,groups0=components(before,cfg['urban_codes'],cfg['centre_codes'],cfg['connectivity'])
    labels1,groups1=components(after,cfg['urban_codes'],cfg['centre_codes'],cfg['connectivity'])
    old_centres={cell for cell,v in before.items() if v['settlement_class'] in cfg['centre_codes']}
    reverse={}
    for cell,label0 in labels0.items():
        if cell in labels1:reverse.setdefault(labels1[cell],set()).add(label0)
    events=[]
    for label,group in groups0.items():
        if group['has_centre']:continue
        members=group['cells'];overlap={}
        for cell in members:
            if cell in labels1:overlap[labels1[cell]]=overlap.get(labels1[cell],0)+1
        if not overlap:continue
        target=max(overlap,key=lambda k:(overlap[k],k));future=groups1[target]
        retained=overlap[target]/len(members)
        centre_connected=bool(future['cells'] & old_centres) and future['has_centre']
        split=len(overlap)>1;merge=len(reverse.get(target,set()))>1
        censored=group['boundary_censored'] or future['boundary_censored']
        growth=(len(future['cells'])-len(members))/len(members)
        stable_population_delta=sum(after[k]['population']-before[k]['population'] for k in members)
        stable_built_delta=sum(after[k]['built_surface_m2']-before[k]['built_surface_m2'] for k in members)
        status='no_candidate'
        if censored:status='boundary_censored'
        elif len(members)<cfg['minimum_baseline_cells']:status='below_minimum_size'
        elif split or retained<cfg['minimum_retained_fraction']:status='ambiguous_lineage'
        elif centre_connected:status='metropolitan_absorption_candidate'
        elif merge:status='ambiguous_lineage'
        elif growth>=cfg['minimum_growth_fraction'] and stable_population_delta>0 and stable_built_delta>0:
            status='independent_growth_candidate'
        events.append(dict(start_year=start,end_year=end,baseline_component=label,target_component=target,
            baseline_cells=len(members),target_cells=len(future['cells']),retained_fraction=retained,
            component_area_growth_fraction=growth,stable_footprint_population_delta=stable_population_delta,
            stable_footprint_built_surface_delta_m2=stable_built_delta,boundary_censored=censored,
            split=split,merge=merge,connected_to_preexisting_centre=centre_connected,status=status))
    return events
