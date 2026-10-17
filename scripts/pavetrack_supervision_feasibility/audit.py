"""FIT-scoped decomposition and two fixed training oracles; never a predictor."""
import bisect,collections,copy,math

FEATURE_NAMES=['original_higher_score_rows_per_image','original_equal_score_rows_per_image','higher_or_equal_score_nonparent_overlap_count']


def context_features(originals,candidates,image_locations,core,guard=None):
    """No GT, cutoffs, H0, singleton roles or annotation arguments."""
    if not image_locations or any(r['image_id'] not in image_locations for r in originals+candidates):raise ValueError('feature scope')
    images=collections.defaultdict(list)
    for r in originals:images[r['image_id']].append(r)
    scores=sorted(r['score'] for r in originals)
    if not all(math.isfinite(x) for x in scores):raise ValueError('feature scores')
    n=len(image_locations);out=[]
    for i,c in enumerate(candidates):
        if not c['eligible']:continue
        row=c['row'];score=row['score']
        if not math.isfinite(score):raise ValueError('feature candidate score')
        values=[(len(scores)-bisect.bisect_right(scores,score))/n,(bisect.bisect_right(scores,score)-bisect.bisect_left(scores,score))/n,sum(r['parent_id']!=c['parent_id'] and r['score']>=score and core.e8.box_iou(r['box_xyxy'],row['box_xyxy'])>=.5 for r in images[c['image_id']])]
        out.append(dict(index=c['index'],parent_id=c['parent_id'],image_id=c['image_id'],location=c['location'],values=values))
        if guard is not None and i%256==0:guard.check()
    return dict(names=FEATURE_NAMES,GT_free=True,fit_scaler=False,scope_images=n,rows=out)


def best_reference(box,GT,core):
    vals=[core.e8.box_iou(box,b) for b in GT]
    if not vals or max(vals)==0:return 0.,None
    value=max(vals);return value,vals.index(value)


def validate_cached(payload,own,reference,core):
    support=core.support_labels(payload,own['candidates'],own['locations'],own['image_locations'])
    if payload['baseline']!=reference[0]:raise ValueError('cached FIT baseline mismatch')
    by={c['parent_id']:c for c in own['candidates']};H0=reference[1]
    for label in payload['rows']:
        c=by[label['parent_id']]
        if label['score']!=c['row']['score']:raise ValueError('cached score mismatch')
        for name in ['new','lost','FP','U']:
            if type(label[name]) is not int:raise ValueError('cached integer role')
        if min(label['new'],label['lost'])<0 or label['FP'] not in (0,1):raise ValueError('cached role range')
        new={tuple(x) for x in label['new_identities']};lost={tuple(x) for x in label['lost_identities']}
        if len(new)!=len(label['new_identities']) or len(lost)!=len(label['lost_identities']) or label['new']!=len(new) or label['lost']!=len(lost):raise ValueError('cached role identity counts')
        for im,j in new|lost:
            if im not in own['targets'] or type(j) is not int or not 0<=j<len(own['targets'][im]):raise ValueError('cached GT identity')
        if new&H0 or not lost<=H0:raise ValueError('cached baseline role membership')
        cutoff=label['cutoff']
        if cutoff is not None and not math.isfinite(cutoff):raise ValueError('cached cutoff')
        if type(label['admitted']) is not bool or label['admitted']!=(cutoff is not None and label['score']>=cutoff) or (label['FP'] and not label['admitted']):raise ValueError('cached admission role')
    return support


def supervision(own,payload,reference,core,locality,guard=None):
    support=validate_cached(payload,own,reference,core);by={r['parent_id']:r for r in payload['rows']};out=[];H0=reference[1]
    for i,c in enumerate(own['candidates']):
        if not c['eligible']:continue
        im=c['image_id'];GT=own['targets'][im];row=c['row'];q,j=best_reference(row['box_xyxy'],GT,core);old_q,old_j=best_reference(row['original_box_xyxy'],GT,core)
        same=None if j is None else core.e8.box_iou(row['original_box_xyxy'],GT[j]);gain=None if same is None else q-same;ref=None if j is None else [im,j]
        marker=locality.positive_intersection(row)
        if type(c['positive_intersection']) is not bool or c['positive_intersection']!=marker or not math.isfinite(c['x']):raise ValueError('supervision candidate representation')
        out.append(dict(index=c['index'],parent_id=c['parent_id'],image_id=im,location=c['location'],corrected_max_IoU=q,parent_max_IoU=old_q,corrected_reference=ref,parent_reference=None if old_j is None else [im,old_j],parent_IoU_on_corrected_reference=same,gain_same_reference=gain,reference_state='no_corrected_reference' if j is None else ('no_parent_reference' if old_j is None else ('same' if j==old_j else 'switched')),valid_localisation=q>=.5,novel_reference=j is not None and (im,j) not in H0,positive_intersection=marker,fixed_admission=marker and c['x']>=0,cached_singleton=copy.deepcopy(by[c['parent_id']])))
        if guard is not None and i%256==0:guard.check()
    return out,support


def support_summary(rows):
    filters={
        'valid_localisation':lambda r:r['valid_localisation'],
        'positive_same_reference_gain':lambda r:r['gain_same_reference'] is not None and r['gain_same_reference']>0,
        'novel_valid_reference':lambda r:r['valid_localisation'] and r['novel_reference'],
        'cached_positive_utility':lambda r:r['cached_singleton']['U']>0,
        'fixed_admitted_positive_utility':lambda r:r['fixed_admission'] and r['cached_singleton']['U']>0,
        'valid_but_cached_FP':lambda r:r['valid_localisation'] and r['cached_singleton']['FP']>0,
        'valid_but_not_budget_admitted':lambda r:r['valid_localisation'] and not r['cached_singleton']['admitted'],
        'valid_reference_already_detected':lambda r:r['valid_localisation'] and not r['novel_reference'],
        'positive_gain_nonpositive_utility':lambda r:r['gain_same_reference'] is not None and r['gain_same_reference']>0 and r['cached_singleton']['U']<=0}
    table={}
    for name,predicate in filters.items():
        selected=[r for r in rows if predicate(r)];refs={tuple(r['corrected_reference']) for r in selected if r['corrected_reference'] is not None};new={tuple(x) for r in selected for x in r['cached_singleton']['new_identities']}
        table[name]=dict(candidates=len(selected),distinct_reference_GT=len(refs),distinct_cached_new_GT=len(new),images=len({r['image_id'] for r in selected}),locations=sorted({r['location'] for r in selected},key=int),by_location=dict(sorted(collections.Counter(r['location'] for r in selected).items(),key=lambda pair:int(pair[0]))))
    return dict(records=len(rows),components=table,reference_states=dict(collections.Counter(r['reference_state'] for r in rows)),counts_not_independent_across_FIT=True)


def oracle_select(candidates,labels,name,cfg,core):
    if name not in cfg['oracles']['names']:raise ValueError('unfrozen oracle')
    by={r['parent_id']:r for r in labels}
    if len(by)!=len(labels):raise ValueError('duplicate supervision identity')
    selected=[]
    for c in candidates:
        if not c['eligible']:continue
        y=by[c['parent_id']]
        if not y['fixed_admission'] or not y['valid_localisation']:continue
        b=y['cached_singleton']
        if name=='decomposed_novel_budget' and not (y['novel_reference'] and b['admitted'] and b['lost']==0 and b['FP']==0):continue
        selected.append(c)
    def key(c):
        stable=(-c['row']['score'],c['image_id'],tuple(c['row']['box_xyxy']),c['parent_id'])
        return (-by[c['parent_id']]['gain_same_reference'],)+stable if name=='decomposed_novel_budget' else stable
    selected.sort(key=key);seen={};counts={};accepted=[];trace=[]
    for c in selected:
        im=c['image_id'];g=core.group_of(c['location'],cfg);prior=seen.get(im,[]);reason='accepted'
        if any(core.e8.box_iou(c['row']['box_xyxy'],r['box_xyxy'])>cfg['policy']['correction_duplicate_iou'] for r in prior):reason='correction_duplicate'
        elif len(prior)>=cfg['policy']['max_per_image']:reason='image_cap'
        elif counts.get(g,0)>=cfg['policy']['max_per_source_group']:reason='group_cap'
        if reason=='accepted':accepted.append(c['row']);seen.setdefault(im,[]).append(c['row']);counts[g]=counts.get(g,0)+1
        trace.append(dict(parent_id=c['parent_id'],reason=reason,group=g))
    return sorted(accepted,key=lambda r:r['parent_id']),trace


def feature_summary(features):
    return {name:dict(minimum=min((r['values'][j] for r in features['rows']),default=None),maximum=max((r['values'][j] for r in features['rows']),default=None),unique_values=len({r['values'][j] for r in features['rows']})) for j,name in enumerate(features['names'])}


def process_scope(data,targets,payload,fold,cfg,guard,core,locality):
    locations=[x for x in cfg['locations'] if x not in cfg['held_groups'][fold]]
    own=core.scoped(data['originals'],data['candidates'],targets,data['image_locations'],locations)
    guard.take('fit_baseline_metrics');reference=core.baseline(own);guard.take('context_feature_builds')
    features=context_features(own['originals'],own['candidates'],own['image_locations'],core,guard)
    guard.take('supervision_rows',len(payload['rows']));labels,support=supervision(own,payload,reference,core,locality,guard)
    if support['positive_GT_count']!=cfg['fit']['expected_positive_GT'][fold] or len(support['positive_sites'])!=cfg['fit']['expected_positive_sites'][fold]:raise ValueError('support lineage')
    original_digest=core.digest(own['originals']);oracles=[];cases=[];by={c['parent_id']:c for c in own['candidates']}
    for name in cfg['oracles']['names']:
        added,trace=oracle_select(own['candidates'],labels,name,cfg,core);guard.take('oracle_comparisons');comparison=core.compare(own,added,reference)
        prefix=[dict(parent_id=r['parent_id'],GT_identity=None if hit is None else list(hit)) for r,hit in core.assignment.classified(own['originals']+added,own['targets'],comparison['candidate']) if r['kind']=='correction']
        chosen={r['parent_id'] for r in added};positive=[y for y in labels if y['parent_id'] in chosen and y['cached_singleton']['U']>0];new={tuple(v) for y in positive for v in y['cached_singleton']['new_identities']}
        rule=cfg['criterion'];passed=comparison['retention'] is not None and comparison['retention']>=rule['old_E003_retention_minimum'] and comparison['net_GT']>=rule['net_new_GT_minimum'] and comparison['macro_delta'] is not None and comparison['macro_delta']>0
        oracles.append(dict(name=name,GT_informed=True,learned_result=False,mathematical_upper_bound=False,source_keys=sorted(chosen),trace=trace,comparison=comparison,correction_prefix_roles=prefix,selected_positive_candidates=len(positive),selected_positive_GT=len(new),protected_increment=passed))
        if name=='decomposed_novel_budget':
            for row in added:cases.append(dict(fold=fold,parent_id=row['parent_id'],location=row['reid'],image_id=row['image_id'],original_box=by[row['parent_id']]['row']['original_box_xyxy'],corrected_box=row['box_xyxy'],original_score=next(r['score'] for r in own['originals'] if r['parent_id']==row['parent_id']),targets=own['targets'][row['image_id']]))
        guard.check()
    if core.digest(own['originals'])!=original_digest:raise ValueError('original mutation')
    report=dict(fold=fold,locations=locations,baseline=reference[0],original_rows_digest=original_digest,support=support,supervision=support_summary(labels),context=feature_summary(features),oracles=oracles,models_fitted=0,scope='own FIT only; GT-informed feasibility, not learned or held results')
    return report,dict(fold=fold,locations=locations,GT_informed=True,new_singleton_U=0,rows=labels),dict(fold=fold,locations=locations,**features),cases
