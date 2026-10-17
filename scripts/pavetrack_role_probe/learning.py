"""Seven-coefficient role probe; prediction accepts only numeric GT-free columns."""
import collections,math
import numpy as np

COLUMNS={'Q':[0,1],'N':[2],'A':[3]}

def weights(strata,locations,images):
    if not strata or not len(strata)==len(locations)==len(images):raise ValueError('training rows')
    counts=collections.Counter(zip(strata,locations,images));sites=collections.defaultdict(set);ims=collections.defaultdict(set)
    for s,l,i in zip(strata,locations,images):sites[s].add(l);ims[s,l].add(i)
    w=np.array([1/(len(sites)*len(sites[s])*len(ims[s,l])*counts[s,l,i]) for s,l,i in zip(strata,locations,images)],dtype=np.float64)
    if not np.isclose(w.sum(),1,rtol=0,atol=1e-12):raise ValueError('weight mass')
    return w


def target_columns(rows):
    return dict(Q=[r['corrected_max_IoU'] for r in rows],N=[int(r['valid_localisation'] and r['novel_reference']) for r in rows],A=[int(r['cached_singleton']['admitted'] and r['cached_singleton']['lost']==0 and r['cached_singleton']['FP']==0) for r in rows])


def matrix(values):
    x=np.asarray(values,dtype=np.float64)
    if x.ndim!=2 or x.shape[1]!=4 or not np.isfinite(x).all() or (x<0).any() or (x>1).any():raise ValueError('GT-free four-column matrix')
    return x


def ridge(x,y,w,penalty,tolerance):
    x=np.asarray(x,dtype=np.float64);y=np.asarray(y,dtype=np.float64);w=np.asarray(w,dtype=np.float64)
    if x.ndim!=2 or not len(x):raise ValueError('ridge shape')
    if y.shape!=(len(x),) or w.shape!=(len(x),) or not np.isfinite(x).all() or not np.isfinite(y).all() or not np.isfinite(w).all() or (w<=0).any() or not np.isclose(w.sum(),1,atol=1e-12,rtol=0):raise ValueError('ridge values')
    z=np.column_stack([np.ones(len(x)),x]);reg=np.diag([0.]+[penalty]*x.shape[1]);normal=z.T@(w[:,None]*z)+reg;rhs=z.T@(w*y)
    b=np.linalg.solve(normal,rhs);res=float(np.max(np.abs(normal@b-rhs)));loss=float(np.dot(w,(z@b-y)**2)+b@reg@b);constant=float(np.dot(w,(y-np.dot(w,y))**2))
    if not np.isfinite(b).all() or not all(math.isfinite(v) for v in [res,loss,constant]) or res>tolerance or loss>constant+tolerance:raise ValueError('fit numerical admissibility')
    return dict(coefficients=b.tolist(),normal_residual_inf=res,objective=loss,constant_baseline_objective=constant,rows=len(x),verified=True)


def fit(values,rows,cfg,guard):
    x=matrix(values)
    if len(x)!=len(rows) or not rows:raise ValueError('training alignment')
    ys=target_columns(rows);heads={};guard.take('model_sets')
    for name,cols in COLUMNS.items():
        y=ys[name];strata=[int(v>=.5) for v in y];w=weights(strata,[r['location'] for r in rows],[r['image_id'] for r in rows]);guard.take('model_fits');guard.take('linear_solves')
        heads[name]=dict(columns=cols,**ridge(x[:,cols],y,w,cfg['fit']['ridge'],cfg['fit']['numerical_tolerance']),strata=[dict(value=s,rows=sum(v==s for v in strata),images=len({r['image_id'] for r,v in zip(rows,strata) if v==s}),locations=sorted({r['location'] for r,v in zip(rows,strata) if v==s},key=int),distinct_reference_GT=len({tuple(r['corrected_reference']) for r,v in zip(rows,strata) if v==s and r['corrected_reference'] is not None}),weight_mass=float(sum(w[i] for i,v in enumerate(strata) if v==s))) for s in sorted(set(strata))])
    return dict(heads=heads,coefficient_count=sum(len(h['coefficients']) for h in heads.values()),ridge=cfg['fit']['ridge'],GT_free_prediction=True,not_probability=True)


def predict(model,values,guard):
    x=matrix(values);guard.take('prediction_rows',len(x));parts=[]
    for name,cols in COLUMNS.items():
        h=model['heads'][name]
        if not h['verified'] or h['columns']!=cols:raise ValueError('unverified head')
        b=np.asarray(h['coefficients'],dtype=np.float64)
        if b.shape!=(len(cols)+1,) or not np.isfinite(b).all():raise ValueError('head coefficients')
        parts.append(np.clip(b[0]+x[:,cols]@b[1:],0,1))
    out=np.column_stack(parts)
    if not np.isfinite(out).all():raise ValueError('nonfinite prediction')
    return [dict(roles=r.tolist(),rank_score=float(np.prod(r))) for r in out]


def select(candidates,scores,threshold,locations,cfg,core,locality):
    if isinstance(threshold,bool) or threshold not in cfg['feature']['thresholds']:raise ValueError('unfrozen gate')
    if threshold=='abstain':return [],[]
    expected={v['parent_id'] for v in candidates if v['eligible'] and v['location'] in locations}
    if set(scores)!=expected:raise ValueError('score scope')
    rows=[]
    for c in candidates:
        if c['parent_id'] not in expected:continue
        score=scores[c['parent_id']]['rank_score']
        if not math.isfinite(score) or not 0<=score<=1:raise ValueError('role rank range')
        if c['positive_intersection']!=locality.positive_intersection(c['row']):raise ValueError('locality representation')
        if c['positive_intersection'] and c['x']>=0 and score>threshold:rows.append(c)
    rows.sort(key=lambda c:(-scores[c['parent_id']]['rank_score'],-c['row']['score'],c['image_id'],tuple(c['row']['box_xyxy']),c['parent_id']))
    seen={};counts={};accepted=[];trace=[]
    for c in rows:
        im=c['image_id'];g=core.group_of(c['location'],cfg);prior=seen.get(im,[]);reason='accepted'
        if any(core.e8.box_iou(c['row']['box_xyxy'],r['box_xyxy'])>cfg['policy']['correction_duplicate_iou'] for r in prior):reason='correction_duplicate'
        elif len(prior)>=cfg['policy']['max_per_image']:reason='image_cap'
        elif counts.get(g,0)>=cfg['policy']['max_per_source_group']:reason='group_cap'
        if reason=='accepted':accepted.append(c['row']);seen.setdefault(im,[]).append(c['row']);counts[g]=counts.get(g,0)+1
        trace.append(dict(parent_id=c['parent_id'],group=g,rank_score=scores[c['parent_id']]['rank_score'],reason=reason))
    return sorted(accepted,key=lambda r:r['parent_id']),trace
