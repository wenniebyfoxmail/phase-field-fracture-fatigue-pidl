"""Fixed GT-free geometry ordering and read-only saved-policy membership."""
import math

def geometry_change(row,core):
    for box in [row['original_box_xyxy'],row['box_xyxy']]:
        if len(box)!=4 or not all(math.isfinite(v) for v in box) or box[0]>=box[2] or box[1]>=box[3]:raise ValueError('geometry box')
    value=1-core.e8.box_iou(row['original_box_xyxy'],row['box_xyxy'])
    if not 0<=value<=1:raise ValueError('geometry change range')
    return value

def select(candidates,threshold,locations,cfg,core):
    if threshold not in cfg['feature']['thresholds']:raise ValueError('unfrozen threshold')
    if threshold=='abstain':return []
    rows=[c for c in candidates if c['location'] in locations and c['eligible'] and c['x']>=threshold]
    for c in rows:
        if c['geometry_change']!=geometry_change(c['row'],core):raise ValueError('geometry representation mismatch')
    rows.sort(key=lambda c:(-c['geometry_change'],-c['row']['score'],c['image_id'],tuple(c['row']['box_xyxy']),c['parent_id']))
    seen={};counts={};accepted=[]
    for c in rows:
        im=c['image_id'];group=core.group_of(c['location'],cfg);prior=seen.get(im,[])
        if any(core.e8.box_iou(c['row']['box_xyxy'],r['box_xyxy'])>cfg['policy']['correction_duplicate_iou'] for r in prior):continue
        if len(prior)>=cfg['policy']['max_per_image'] or counts.get(group,0)>=cfg['policy']['max_per_source_group']:continue
        accepted.append(c['row']);seen.setdefault(im,[]).append(c['row']);counts[group]=counts.get(group,0)+1
    return sorted(accepted,key=lambda r:r['parent_id'])

def capacity_audit(data,models,cfg):
    """Join already saved FIT policy keys/own labels; never evaluate a policy."""
    folds=[]
    for k,(payload,model) in enumerate(zip(data['labels'],models,strict=True)):
        fit=[x for x in cfg['locations'] if x not in cfg['held_groups'][k]]
        if set(payload['locations'])!=set(fit) or set(model['locations'])!=set(fit):raise ValueError('capacity FIT scope')
        rows=payload['rows'];by={r['parent_id']:r for r in rows}
        if len(by)!=len(rows) or any(r['location'] not in fit for r in rows):raise ValueError('capacity candidate scope')
        for r in rows:
            if any(data['image_locations'].get(v[0]) not in fit for v in r['new_identities']+r['lost_identities']):raise ValueError('capacity GT scope')
        available={tuple(v) for r in rows if r['U']>0 for v in r['new_identities']};policies=[]
        if [p['threshold'] for p in model['policies']]!=cfg['feature']['thresholds']:raise ValueError('capacity policy inventory')
        for p in model['policies']:
            keys=p['source_keys']
            if len(keys)!=len(set(keys)) or any(key not in by for key in keys):raise ValueError('capacity selected identity')
            positive=[by[key] for key in keys if by[key]['U']>0];GT={tuple(v) for r in positive for v in r['new_identities']}
            policies.append(dict(threshold=p['threshold'],appended=len(keys),selected_positive_candidates=len(positive),selected_positive_GT=len(GT),selected_positive_GT_ids=[list(v) for v in sorted(GT)],joint_new_GT=p['comparison']['new_GT'],joint_net_GT=p['comparison']['net_GT']))
        chosen=next(p for p in policies if p['threshold']==model['threshold'])
        folds.append(dict(fold=k,locations=fit,available_positive_GT=len(available),policies=policies,chosen_policy=chosen,max_policy_positive_GT=max(p['selected_positive_GT'] for p in policies)))
    return dict(protocol=cfg['protocol'],scope='own main FIT8 saved singleton support; membership is not joint detection gain',used_to_choose_main=False,new_policy_comparisons=0,new_U=0,folds=folds)
