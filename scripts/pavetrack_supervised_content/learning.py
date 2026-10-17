"""Eleven supervised coefficients on four scalar plus two bounded content columns."""
import importlib.util
from pathlib import Path
import numpy as np
s=importlib.util.spec_from_file_location('e020_private_role_math',Path(__file__).resolve().parent.parent/'pavetrack_role_probe/learning.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
weights=old.weights;target_columns=old.target_columns;select=old.select
COLUMNS={'Q':[0,1,4,5],'N':[2,4,5],'A':[3]}


def ridge(x,y,w,penalty,tolerance):
    """Same weighted ridge equations; explicit contractions avoid BLAS status artefacts."""
    x=np.asarray(x,dtype=np.float64);y=np.asarray(y,dtype=np.float64);w=np.asarray(w,dtype=np.float64)
    if x.ndim!=2 or not len(x) or y.shape!=(len(x),) or w.shape!=(len(x),) or not all(np.isfinite(v).all() for v in [x,y,w]) or (w<=0).any() or not np.isclose(w.sum(),1,atol=1e-12,rtol=0):raise ValueError('ridge values')
    z=np.column_stack([np.ones(len(x)),x]);reg=np.diag([0.]+[penalty]*x.shape[1])
    normal=np.einsum('ni,n,nj->ij',z,w,z,optimize=False)+reg;rhs=np.einsum('ni,n,n->i',z,w,y,optimize=False)
    b=np.linalg.solve(normal,rhs);res=float(np.max(np.abs(np.einsum('ij,j->i',normal,b,optimize=False)-rhs)))
    errors=np.einsum('ij,j->i',z,b,optimize=False)-y
    loss=float(np.sum(w*errors**2)+penalty*np.sum(b[1:]**2));constant=float(np.sum(w*(y-np.sum(w*y))**2))
    if not np.isfinite(b).all() or not np.isfinite([res,loss,constant]).all() or res>tolerance or loss>constant+tolerance:raise ValueError('fit numerical admissibility')
    return dict(coefficients=b.tolist(),normal_residual_inf=res,objective=loss,constant_baseline_objective=constant,rows=len(x),verified=True)


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
    return dict(heads=heads,coefficient_count=sum(len(h['coefficients']) for h in heads.values()),ridge=cfg['fit']['ridge'],GT_free_prediction=True,not_probability=True,coefficient_count_excludes_supervised_directions=True)


def predict(model,values,guard):
    x=matrix(values);guard.take('prediction_rows',len(x));parts=[]
    for name,cols in COLUMNS.items():
        h=model['heads'][name]
        if h['verified'] is not True or h['columns']!=cols:raise ValueError('unverified head')
        b=np.asarray(h['coefficients'],dtype=np.float64)
        if b.shape!=(len(cols)+1,) or not np.isfinite(b).all():raise ValueError('head coefficients')
        parts.append(np.clip(b[0]+np.einsum('ij,j->i',x[:,cols],b[1:],optimize=False),0,1))
    out=np.column_stack(parts)
    if not np.isfinite(out).all():raise ValueError('nonfinite prediction')
    return [dict(roles=r.tolist(),rank_score=float(np.prod(r))) for r in out]
