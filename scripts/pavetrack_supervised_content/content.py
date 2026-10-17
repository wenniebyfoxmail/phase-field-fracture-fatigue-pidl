"""Fixed sketch8; own-FIT Q/N labels select two bounded content directions."""
import copy, importlib.util
from pathlib import Path
import numpy as np

def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

prior=load('e020_private_content_scope',Path(__file__).resolve().parent.parent/'pavetrack_content_probe/content.py')
math=load('e020_private_direction_math',Path(__file__).resolve().parent/'learning.py')

def sketch(cfg):
    if cfg['content']['dimensions']!=576 or cfg['content']['sketch_dimensions']!=8 or cfg['content']['rank']!=2:
        raise ValueError('fixed sketch dimensions')
    result=np.zeros((576,8),dtype=np.float64)
    for j in range(576):result[j,j%8]=(-1.)**((j//8).bit_count())/np.sqrt(72.)
    return result

def rows(X,indices,cfg,guard):
    ids=prior.metadata(indices,['scope']*len(indices),[str(i) for i in indices],X.shape,cfg)
    S=sketch(cfg);out=[]
    for start,x in prior.batches(X,ids,cfg,guard):
        values=np.einsum('ij,jk->ik',x,S,optimize=False)
        if not np.isfinite(values).all():raise ValueError('nonfinite sketch')
        out.extend(values.tolist())
    return np.asarray(out,dtype=np.float64)

def standardize(raw,statistics):
    mean=np.asarray(statistics['mean'],dtype=np.float64);scale=np.asarray(statistics['scale'],dtype=np.float64)
    if statistics['verified'] is not True or mean.shape!=(8,) or scale.shape!=(8,) or not np.isfinite(mean).all() or not np.isfinite(scale).all() or (scale<=0).any():
        raise ValueError('invalid sketch statistics')
    z=(raw-mean)/scale
    if not np.isfinite(z).all():raise ValueError('nonfinite standardized sketch')
    return z

def fit(X,indices,locations,images,labels,cfg,guard,statistics=None):
    prior.metadata(indices,locations,images,X.shape,cfg)
    if not len(labels)==len(indices) or any((r['index'],r['location'],r['image_id'])!=(i,l,im) for r,i,l,im in zip(labels,indices,locations,images,strict=True)):
        raise ValueError('direction label row identity')
    raw=rows(X,indices,cfg,guard)
    if statistics is None:
        guard.take('content_statistics_fits');guard.take('content_statistics_rows',len(indices))
        w=prior.weights(locations,images);mean=np.sum(w[:,None]*raw,axis=0);variance=np.sum(w[:,None]*(raw-mean)**2,axis=0)
        statistics=dict(verified=True,mean=mean.tolist(),scale=np.maximum(np.sqrt(variance),cfg['content']['standard_deviation_floor']).tolist(),fit_indices=list(indices),locations=sorted(set(locations),key=int),fit_rows=len(indices),GT_free_fit=True)
    z=standardize(raw,statistics);targets=math.target_columns(labels);directions={}
    # Count the shared input rows once, not once per Q/N target.
    guard.take('content_direction_training_rows',len(indices))
    for target in ['Q','N']:
        y=targets[target];w=math.weights([int(v>=.5) for v in y],locations,images)
        guard.take('content_direction_fits');guard.take('linear_solves')
        model=math.ridge(z,y,w,cfg['content']['direction_ridge'],cfg['fit']['numerical_tolerance'])
        beta=np.asarray(model['coefficients'][1:],dtype=np.float64);norm=float(np.linalg.norm(beta))
        if not np.isfinite(norm):raise ValueError('nonfinite direction norm')
        directions[target]=dict(**model,norm=norm,active=norm>cfg['content']['direction_norm_floor'],target=target)
    return dict(verified=True,rank=2,input_dimensions=576,sketch_dimensions=8,sketch=sketch(cfg).tolist(),statistics=copy.deepcopy(statistics),directions=directions,supervised_coefficient_count=18,fit_indices=list(indices),fit_locations=sorted(set(locations),key=int),fit_rows=len(indices),target_informed=True,GT_free_prediction=True)

def project(model,X,indices,cfg,guard):
    if model['verified'] is not True or model['rank']!=2 or model['input_dimensions']!=576 or model['sketch_dimensions']!=8 or not np.array_equal(model['sketch'],sketch(cfg)):
        raise ValueError('unverified content model')
    z=standardize(rows(X,indices,cfg,guard),model['statistics']);out=[]
    guard.take('content_transform_calls');guard.take('content_projection_rows',len(indices))
    for target in ['Q','N']:
        direction=model['directions'][target];b=np.asarray(direction['coefficients'],dtype=np.float64)
        if direction['verified'] is not True or b.shape!=(9,) or not np.isfinite(b).all():raise ValueError('invalid supervised direction')
        norm=float(np.linalg.norm(b[1:]));active=norm>cfg['content']['direction_norm_floor']
        if not np.isfinite(norm) or norm!=direction['norm'] or active!=direction['active']:raise ValueError('invalid direction norm')
        out.append(np.tanh(np.einsum('ij,j->i',z,b[1:],optimize=False)/max(norm,cfg['content']['direction_norm_floor'])) if active else np.zeros(len(z)))
    values=np.column_stack(out)
    if not np.isfinite(values).all():raise ValueError('nonfinite content projection')
    return values.tolist()
