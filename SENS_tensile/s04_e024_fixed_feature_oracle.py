"""Read-only weighted truncated-SVD projection; no network or optimizer update."""
import numpy as np
from scipy.linalg import svd

MULTIPLIERS = (0.1, 1.0, 10.0)

def project_head(phi, target, mass):
    phi, target, mass = [np.asarray(x, dtype=np.float64) for x in (phi, target, mass)]
    if phi.ndim != 2 or target.shape != (len(phi), 2) or mass.shape != (len(phi),):
        raise ValueError('design/target/mass shape')
    if not all(np.isfinite(x).all() for x in (phi,target,mass)) or not (mass>0).all():
        raise ValueError('nonfinite or nonpositive inputs')
    weights=mass/mass.sum(); sw=np.sqrt(weights)
    x=np.asfortranarray(sw[:,None]*phi); y=sw[:,None]*target
    u,s,vt=svd(x,full_matrices=False,check_finite=True,lapack_driver='gesdd')
    if not len(s) or s[0]<=0:raise ValueError('zero design')
    base=np.finfo(np.float64).eps*max(x.shape)
    allcross=u.T@y
    orth=float(np.linalg.norm(u.T@u-np.eye(len(s)),ord=np.inf))
    if orth>1e-10:raise ValueError('SVD orthogonality')
    out=[]
    for mult in MULTIPLIERS:
        cutoff=mult*base*s[0];rank=int(np.count_nonzero(s>cutoff))
        cross=allcross[:rank];coef=vt[:rank].T@(cross/s[:rank,None])
        projected=u[:,:rank]@cross;direct=x@coef
        residual=y-projected
        orth_res=float(np.linalg.norm(u[:,:rank].T@residual)/max(np.linalg.norm(y),np.finfo(float).tiny))
        if orth_res>1e-10:raise ValueError('retained projection orthogonality')
        if not np.isfinite(coef).all():raise ValueError('nonfinite coefficients')
        out.append(dict(multiplier=mult,primary=mult==1.,rcond=mult*base,cutoff=float(cutoff),rank=rank,
            retained_condition=float(s[0]/s[rank-1]) if rank else None,
            coefficient_norm=float(np.linalg.norm(coef)),projection_rms=float(np.linalg.norm(residual)),
            direct_rms=float(np.linalg.norm(direct-y)),projection_realization_weighted_gap=float(np.linalg.norm(direct-projected)),
            retained_residual_orthogonality=orth_res,coefficient_backward_residual=float(np.linalg.norm(direct-projected)/max(np.linalg.norm(x)*np.linalg.norm(coef),np.finfo(float).tiny)),
            projected_discarded_target_energy=float(np.sum(allcross[rank:]**2)),
            coef=coef,prediction=phi@coef,projection_prediction=projected/sw[:,None]))
    return out,dict(rows=len(phi),columns=phi.shape[1],base_rcond=base,svd_orthogonality_inf=orth,singular_values=s)
