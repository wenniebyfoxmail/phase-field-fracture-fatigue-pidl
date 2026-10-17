"""Finite capacity ordering optimized by actual joint utility, not U regression."""
import collections,math


def representation(candidate,core):
    x=candidate['x'];row=candidate['row']
    if not math.isfinite(x):raise ValueError('ranking nonfinite gain')
    h=core.e8.box_iou(row['original_box_xyxy'],row['box_xyxy']);g=math.tanh(x/2)
    if not math.isfinite(h) or not 0<=h<=1:raise ValueError('ranking overlap')
    return g,h


def select(candidates,mixture,locations,cfg,core,locality):
    if type(mixture) not in (float,int,str) or mixture not in cfg['ranking']['mixtures']:raise ValueError('unfrozen mixture')
    if len({x['parent_id'] for x in candidates})!=len(candidates):raise ValueError('ranking duplicate identity')
    trace=dict(mixture=mixture,ordered_source_keys=[],accepted_source_keys=[],groups={})
    if mixture=='abstain':return [],trace
    considered=[];groups=collections.defaultdict(collections.Counter)
    for row in candidates:
        if row['location'] not in locations or not row['eligible']:continue
        marker=row['positive_intersection']
        if type(marker) is not bool or marker!=locality.positive_intersection(row['row']):raise ValueError('ranking locality representation')
        g,h=representation(row,core)
        if row['bounded_gain']!=g or row['original_corrected_IoU']!=h:raise ValueError('ranking representation mismatch')
        group=core.group_of(row['location'],cfg)
        if not marker:groups[group]['rejected_locality']+=1;continue
        if row['x']<0:groups[group]['rejected_negative_gain']+=1;continue
        q=(1-mixture)*g+mixture*h
        considered.append((q,row))
    considered.sort(key=lambda pair:(-pair[0],-pair[1]['row']['score'],pair[1]['image_id'],tuple(pair[1]['row']['box_xyxy']),pair[1]['parent_id']))
    seen={};counts={};accepted=[]
    for q,item in considered:
        row=item['row'];im=item['image_id'];group=core.group_of(item['location'],cfg);prior=seen.get(im,[])
        trace['ordered_source_keys'].append(item['parent_id']);groups[group]['considered']+=1
        if any(core.e8.box_iou(row['box_xyxy'],r['box_xyxy'])>cfg['policy']['correction_duplicate_iou'] for r in prior):groups[group]['rejected_duplicate']+=1;continue
        if len(prior)>=cfg['policy']['max_per_image']:groups[group]['rejected_image_cap']+=1;continue
        if counts.get(group,0)>=cfg['policy']['max_per_source_group']:groups[group]['rejected_group_cap']+=1;continue
        accepted.append(row);seen.setdefault(im,[]).append(row);counts[group]=counts.get(group,0)+1;groups[group]['accepted']+=1;trace['accepted_source_keys'].append(item['parent_id'])
    trace['groups']={str(k):dict(v) for k,v in sorted(groups.items())}
    return sorted(accepted,key=lambda row:row['parent_id']),trace


def choose(table):
    active=[p for p in table if p['mixture']!='abstain' and p['comparison']['retention']==1 and p['comparison']['net_GT']>=1 and p['comparison']['macro_delta'] is not None and p['comparison']['macro_delta']>0]
    if not active:return 'abstain'
    return max(active,key=lambda p:(p['comparison']['net_GT'],-p['comparison']['added_FP'],-p['comparison']['appended'],-p['mixture']))['mixture']


def calibrate(data,cfg,guard,core,locality,metric=None):
    core.require_producer(cfg);guard.take('ranking_fits');guard.take('fit_baseline_metrics');ref=core.baseline(data);table=[];metric=core.compare if metric is None else metric
    for mixture in cfg['ranking']['mixtures']:
        guard.take('calibration_policy_comparisons');added,trace=select(data['candidates'],mixture,data['locations'],cfg,core,locality)
        score=metric(data,added,ref);guard.check();table.append(dict(mixture=mixture,source_keys=[r['parent_id'] for r in added],ranking_trace=trace,comparison=score))
    mixture=choose(table)
    return dict(mixture=mixture,locations=data['locations'],baseline=ref[0],training_original_digest=core.digest(data['originals']),policies=table,abstained=mixture=='abstain',selection_reason='no protected FIT joint gain' if mixture=='abstain' else 'FIT joint netGT, correction FP, exposure, then smallest alpha',per_candidate_U_regression=False)


def audits(data,models,cfg,core,locality):
    retained=locality.retention_audit(data,cfg);by={r['parent_id']:r for r in data['candidates']};folds=[]
    for k,(payload,model) in enumerate(zip(data['labels'],models,strict=True)):
        fit=[x for x in cfg['locations'] if x not in cfg['held_groups'][k]]
        if set(payload['locations'])!=set(fit) or set(model['locations'])!=set(fit):raise ValueError('capacity FIT scope')
        labels={r['parent_id']:r for r in payload['rows']}
        if len(labels)!=len(payload['rows']):raise ValueError('capacity duplicate label')
        positive=[r for r in labels.values() if r['U']>0];available={tuple(v) for r in positive for v in r['new_identities']}
        admitted=[r for r in positive if by[r['parent_id']]['positive_intersection'] and by[r['parent_id']]['x']>=0]
        info=dict(fixed_admission_positive_candidates=len(admitted),fixed_admission_positive_GT=len({tuple(v) for r in admitted for v in r['new_identities']}));retained['folds'][k].update(info)
        policies=[]
        if [p['mixture'] for p in model['policies']]!=cfg['ranking']['mixtures']:raise ValueError('capacity policy inventory')
        for p in model['policies']:
            keys=p['source_keys']
            if len(keys)!=len(set(keys)) or any(key not in labels for key in keys):raise ValueError('capacity selected identity')
            selected=[labels[key] for key in keys if labels[key]['U']>0];GT={tuple(v) for r in selected for v in r['new_identities']}
            policies.append(dict(mixture=p['mixture'],appended=len(keys),selected_positive_candidates=len(selected),selected_positive_GT=len(GT),selected_positive_GT_ids=[list(v) for v in sorted(GT)],joint_new_GT=p['comparison']['new_GT'],joint_net_GT=p['comparison']['net_GT']))
        chosen=next(p for p in policies if p['mixture']==model['mixture'])
        folds.append(dict(fold=k,locations=fit,available_positive_GT=len(available),**info,policies=policies,chosen_policy=chosen,max_policy_positive_GT=max(p['selected_positive_GT'] for p in policies)))
    return retained,dict(protocol=cfg['protocol'],scope='own main FIT8 singleton support membership, not joint detection benefit',used_to_choose_main=False,new_policy_comparisons=0,new_U=0,folds=folds)
