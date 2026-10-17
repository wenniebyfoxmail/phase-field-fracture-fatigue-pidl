"""Eleven supervised coefficients on four scalar plus two bounded content columns."""
import importlib.util
from pathlib import Path
import numpy as np
s=importlib.util.spec_from_file_location('e019_private_role_math',Path(__file__).resolve().parent.parent/'pavetrack_role_probe/learning.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
weights=old.weights;ridge=old.ridge;target_columns=old.target_columns;select=old.select
COLUMNS={'Q':[0,1,4,5],'N':[2,4,5],'A':[3]}


def matrix(values):
    x=np.asarray(values,dtype=np.float64)
    if x.ndim!=2 or x.shape[1]!=6 or not np.isfinite(x).all() or (x[:,:4]<0).any() or (x[:,:4]>1).any() or (x[:,4:]< -1).any() or (x[:,4:]>1).any():raise ValueError('GT-free six-column matrix')
    return x


def fit(values,rows,cfg,guard):
    x=matrix(values)
    if len(x)!=len(rows) or not rows:raise ValueError('training alignment')
    ys=target_columns(rows);heads={};guard.take('model_sets')
    for name,cols in COLUMNS.items():
        y=ys[name];strata=[int(v>=.5) for v in y];w=weights(strata,[r['location'] for r in rows],[r['image_id'] for r in rows]);guard.take('model_fits');guard.take('linear_solves')
        heads[name]=dict(columns=cols,**ridge(x[:,cols],y,w,cfg['fit']['ridge'],cfg['fit']['numerical_tolerance']),strata=[dict(value=s,rows=sum(v==s for v in strata),images=len({r['image_id'] for r,v in zip(rows,strata) if v==s}),locations=sorted({r['location'] for r,v in zip(rows,strata) if v==s},key=int),distinct_reference_GT=len({tuple(r['corrected_reference']) for r,v in zip(rows,strata) if v==s and r['corrected_reference'] is not None}),weight_mass=float(sum(w[i] for i,v in enumerate(strata) if v==s))) for s in sorted(set(strata))])
    return dict(heads=heads,coefficient_count=sum(len(h['coefficients']) for h in heads.values()),ridge=cfg['fit']['ridge'],GT_free_prediction=True,not_probability=True,coefficient_count_excludes_unsupervised_PCA=True)


def predict(model,values,guard):
    x=matrix(values);guard.take('prediction_rows',len(x));parts=[]
    for name,cols in COLUMNS.items():
        h=model['heads'][name]
        if h['verified'] is not True or h['columns']!=cols:raise ValueError('unverified head')
        b=np.asarray(h['coefficients'],dtype=np.float64)
        if b.shape!=(len(cols)+1,) or not np.isfinite(b).all():raise ValueError('head coefficients')
        parts.append(np.clip(b[0]+x[:,cols]@b[1:],0,1))
    out=np.column_stack(parts)
    if not np.isfinite(out).all():raise ValueError('nonfinite prediction')
    return [dict(roles=r.tolist(),rank_score=float(np.prod(r))) for r in out]
