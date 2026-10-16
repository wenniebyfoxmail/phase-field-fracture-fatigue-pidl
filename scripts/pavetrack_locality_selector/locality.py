"""No-epsilon coordinate predicate and descriptive original-support retention."""
import math

def positive_intersection(row):
    old,new=row['original_box_xyxy'],row['box_xyxy']
    for box in [old,new]:
        if len(box)!=4 or not all(math.isfinite(v) for v in box) or box[0]>=box[2] or box[1]>=box[3]:raise ValueError('locality box')
    return min(old[2],new[2])>max(old[0],new[0]) and min(old[3],new[3])>max(old[1],new[1])

def retention_audit(data,cfg):
    candidates=data['candidates'];by={c['parent_id']:c for c in candidates}
    if len(by)!=len(candidates):raise ValueError('locality duplicate source')
    def pool(locations):
        base=[c for c in candidates if c['eligible'] and c['location'] in locations];kept=[c for c in base if c['positive_intersection']]
        return dict(base_eligible=len(base),retained=len(kept),removed=len(base)-len(kept))
    folds=[]
    for k,payload in enumerate(data['labels']):
        fit=[x for x in cfg['locations'] if x not in cfg['held_groups'][k]]
        if set(payload['locations'])!=set(fit):raise ValueError('locality FIT scope')
        rows=payload['rows']
        if len({r['parent_id'] for r in rows})!=len(rows):raise ValueError('locality duplicate label')
        for row in rows:
            candidate=by[row['parent_id']]
            if row['location'] not in fit or candidate['location']!=row['location'] or candidate['image_id']!=row['image_id'] or candidate['index']!=row['index'] or not candidate['eligible']:raise ValueError('locality label identity')
            if any(data['image_locations'].get(v[0]) not in fit for v in row['new_identities']+row['lost_identities']):raise ValueError('locality GT scope')
        positive=[r for r in rows if r['U']>0];kept=[r for r in positive if by[r['parent_id']]['positive_intersection']]
        before={tuple(v) for r in positive for v in r['new_identities']};after={tuple(v) for r in kept for v in r['new_identities']}
        folds.append(dict(fold=k,locations=fit,**pool(fit),positive_candidates_before=len(positive),positive_candidates_after=len(kept),positive_candidates_removed=len(positive)-len(kept),positive_GT_before=len(before),positive_GT_after=len(after),positive_GT_removed=len(before-after)))
    return dict(protocol=cfg['protocol'],scope='GT-free pool counts; own FIT8 original singleton support retention, not recomputed U or joint benefit',used_to_choose_main=False,new_policy_comparisons=0,new_U=0,all12_pool=pool(cfg['locations']),folds=folds)
