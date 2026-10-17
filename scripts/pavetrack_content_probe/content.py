"""FIT-only GT-free weighted PCA2; no targets, GT identities or held argument."""
import collections,hashlib
import numpy as np


def metadata(indices,locations,images,shape,cfg):
    if cfg['content']['rank']!=2 or len(shape)!=2 or shape[1]<2 or shape[1]!=cfg['content']['dimensions'] or not len(indices)==len(locations)==len(images) or not indices:raise ValueError('content scope/shape')
    if len(set(indices))!=len(indices) or any(type(i) is not int or not 0<=i<shape[0] for i in indices):raise ValueError('content row identity')
    if any(not isinstance(s,str) or not s for s in locations+images):raise ValueError('content grouping')
    mapping={}
    for im,loc in zip(images,locations):
        if mapping.setdefault(im,loc)!=loc:raise ValueError('content image/location')
    return np.asarray(indices,dtype=np.int64)


def weights(locations,images):
    counts=collections.Counter(zip(locations,images));ims=collections.defaultdict(set)
    for loc,im in zip(locations,images):ims[loc].add(im)
    w=np.array([1/(len(ims)*len(ims[loc])*counts[loc,im]) for loc,im in zip(locations,images)],dtype=np.float64)
    if not np.isfinite(w).all() or not np.isclose(w.sum(),1,atol=1e-12,rtol=0):raise ValueError('content weight mass')
    return w


def batches(X,ids,cfg,guard):
    batch=cfg['content']['covariance_batch']
    for start in range(0,len(ids),batch):
        guard.check();v=np.asarray(X[ids[start:start+batch]],dtype=np.float64)
        if not np.isfinite(v).all():raise ValueError('nonfinite content')
        yield start,v


def fit(X,indices,locations,images,cfg,guard):
    ids=metadata(indices,locations,images,X.shape,cfg);w=weights(locations,images);guard.take('PCA_fits');p=X.shape[1];mean=np.zeros(p,dtype=np.float64)
    for start,x in batches(X,ids,cfg,guard):mean+=np.sum(w[start:start+len(x),None]*x,axis=0)
    variance=np.zeros(p,dtype=np.float64)
    for start,x in batches(X,ids,cfg,guard):variance+=np.sum(w[start:start+len(x),None]*(x-mean)**2,axis=0)
    scale=np.maximum(np.sqrt(variance),cfg['content']['standard_deviation_floor']);cov=np.zeros((p,p),dtype=np.float64)
    for start,x in batches(X,ids,cfg,guard):
        z=(x-mean)/scale;cov+=np.einsum('ni,nj->ij',z,w[start:start+len(x),None]*z,optimize=False);guard.take('covariance_rows',len(x))
    # Explicit contractions avoid BLAS floating-status artefacts on rank-deficient synthetic banks.
    cov=(cov+cov.T)/2
    if not np.isfinite(mean).all() or not np.isfinite(scale).all() or not np.isfinite(cov).all():raise ValueError('PCA finite statistics')
    guard.take('eigendecompositions');eigenvalues,vectors=np.linalg.eigh(cov);order=np.argsort(-eigenvalues,kind='stable');values=eigenvalues[order];basis=vectors[:,order[:2]].copy();lam=values[:2].copy()
    if not np.isfinite(values).all() or not np.isfinite(basis).all():raise ValueError('PCA nonfinite decomposition')
    for j in range(2):
        pivot=int(np.argmax(np.abs(basis[:,j])))
        if basis[pivot,j]<0:basis[:,j]*=-1
    limit=max(1.,float(values[0]));residual=float(np.max(np.abs(np.einsum('ij,jk->ik',cov,basis,optimize=False)-basis*lam)));ortho=float(np.max(np.abs(np.einsum('pi,pj->ij',basis,basis,optimize=False)-np.eye(2))))
    if values[-1]<-cfg['content']['negative_eigenvalue_relative_tolerance']*limit or residual>cfg['content']['eigen_residual_relative_max']*limit or ortho>cfg['content']['orthogonality_max']:raise ValueError('PCA numerical admissibility')
    floor=cfg['content']['eigenvalue_floor'];trace=float(np.trace(cov));active=[bool(v>floor) for v in lam]
    return dict(verified=True,rank=2,input_dimensions=p,mean=mean.tolist(),scale=scale.tolist(),basis=basis.tolist(),eigenvalues=values.tolist(),projection_eigenvalues=lam.tolist(),projection_scales=np.sqrt(np.maximum(lam,floor)).tolist(),active_components=active,eigen_residual_inf=residual,orthogonality_inf=ortho,covariance_trace=trace,top2_variance_fraction=0. if trace<=0 else float(np.maximum(lam,0).sum()/trace),boundary_gap=float(values[1]-values[2]) if p>2 else None,scale_floor_columns=int(np.sum(np.sqrt(variance)<cfg['content']['standard_deviation_floor'])),effective_components=sum(active),fit_rows=len(ids),locations=sorted(set(locations),key=int),images=len(set(images)),fit_indices=list(indices),covariance_sha256=hashlib.sha256(np.ascontiguousarray(cov).tobytes()).hexdigest(),GT_free_fit=True,fit_scopes_do_not_include_held=True)


def project(model,X,indices,cfg,guard):
    ids=metadata(indices,['scope']*len(indices),[str(i) for i in indices],X.shape,cfg)
    if model['verified'] is not True or model['rank']!=2 or model['input_dimensions']!=X.shape[1]:raise ValueError('unverified PCA')
    mean=np.asarray(model['mean'],dtype=np.float64);scale=np.asarray(model['scale'],dtype=np.float64);basis=np.asarray(model['basis'],dtype=np.float64);denom=np.asarray(model['projection_scales'],dtype=np.float64);active=np.asarray(model['active_components'],dtype=bool)
    if mean.shape!=(X.shape[1],) or scale.shape!=mean.shape or basis.shape!=(X.shape[1],2) or denom.shape!=(2,) or active.shape!=(2,) or not all(np.isfinite(x).all() for x in [mean,scale,basis,denom]) or (scale<=0).any() or (denom<=0).any():raise ValueError('PCA model representation')
    guard.take('content_transform_calls');out=[]
    for start,x in batches(X,ids,cfg,guard):
        z=np.tanh(np.einsum('ij,jk->ik',(x-mean)/scale,basis,optimize=False)/denom);z[:,~active]=0.
        if not np.isfinite(z).all():raise ValueError('nonfinite content projection')
        guard.take('content_projection_rows',len(x));out.extend(z.tolist())
    return out
