"""Offline centered Frobenius-norm trust region; shared multiplier for both UV heads."""
import numpy as np
from scipy.linalg import svd
from scipy.linalg.blas import dgemm
from scipy.optimize import brentq


def product(a, b, trans_a=False):
    return dgemm(1., np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64), trans_a=trans_a)


def centered_head(phi, target, mass, theta0, radius_fraction=.1):
    phi, target, mass, theta0 = [np.asarray(x, dtype=np.float64) for x in (phi,target,mass,theta0)]
    if phi.ndim!=2 or target.shape!=(len(phi),2) or mass.shape!=(len(phi),) or theta0.shape!=(phi.shape[1],2):
        raise ValueError('design/target/mass/center shape')
    if not all(np.isfinite(x).all() for x in (phi,target,mass,theta0)) or not (mass>0).all() or not np.isfinite(radius_fraction) or radius_fraction<=0:
        raise ValueError('nonfinite input or invalid mass/radius')
    radius=float(radius_fraction*np.linalg.norm(theta0))
    if radius<=0:raise ValueError('zero center norm: relative radius undefined')
    sw=np.sqrt(mass/mass.sum());x=np.asfortranarray(sw[:,None]*phi)
    residual_target=sw[:,None]*(target-product(phi,theta0))
    u,s,vt=svd(x,full_matrices=False,check_finite=True,lapack_driver='gesdd')
    ortho=float(np.linalg.norm(product(u,u,True)-np.eye(len(s)),ord=np.inf))
    if ortho>1e-10:raise ValueError('SVD orthogonality')
    cross=product(u,residual_target,True)
    scale=float(s[0]) if len(s) and s[0]>0 else 1.
    q=s/scale;cc=cross/scale
    def spectral_step(mu):
        factors=np.divide(q,q*q+mu,out=np.zeros_like(q),where=(q*q+mu)>0)
        return factors[:,None]*cc
    # Infinite/huge unregularized norm only signals active constraint; no truncation.
    with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
        free=spectral_step(0.);free_norm=float(np.linalg.norm(free))
    active=not np.isfinite(free_norm) or free_norm>radius
    if active:
        upper=max(1.,float(np.linalg.norm(q[:,None]*cc))/radius)
        def secular(mu):return float(np.linalg.norm(spectral_step(mu)))-radius
        if secular(upper)>0:raise ValueError('secular bracket failure')
        mu=brentq(secular,0.,upper,xtol=1e-30,rtol=8*np.finfo(float).eps,maxiter=250)
        z=spectral_step(mu)
    else:mu=0.;z=free
    delta=product(vt.T,z);coef=theta0+delta;lam=float(mu*scale*scale)
    realized_delta=coef-theta0
    if not all(np.isfinite(v).all() for v in (delta,coef,z)):raise ValueError('nonfinite solution')
    norm=float(np.linalg.norm(realized_delta));relative_feasibility=max(0.,norm/radius-1.)
    if relative_feasibility>1e-10:raise ValueError('trust-region infeasible')
    if active and abs(norm/radius-1.)>1e-10:raise ValueError('active boundary mismatch')
    residual=product(x,realized_delta)-residual_target
    gradient=product(x,residual,True);stationarity=gradient+lam*realized_delta
    kkt_scale=float(np.linalg.norm(x)*np.linalg.norm(residual)+lam*norm)
    kkt=float(np.linalg.norm(stationarity)/max(kkt_scale,np.finfo(float).tiny))
    comp=abs(lam*(norm*norm-radius*radius))/max(lam*radius*radius,np.finfo(float).tiny)
    if kkt>1e-10 or comp>1e-9:raise ValueError('KKT residual')
    before=float(np.linalg.norm(residual_target));after=float(np.linalg.norm(residual))
    if after>before+1e-13:raise ValueError('objective increased')
    projected=product(u,s[:,None]*z)
    projection_gap=float(np.linalg.norm(product(x,realized_delta)-projected))
    rank=int(np.count_nonzero(s>np.finfo(float).eps*max(x.shape)*s[0])) if len(s) else 0
    return dict(coef=coef,delta=realized_delta,prediction=product(phi,coef),singular_values=s,
        radius=radius,radius_fraction=radius_fraction,original_norm=float(np.linalg.norm(theta0)),
        delta_norm=norm,delta_relative=norm/np.linalg.norm(theta0),active=bool(active),lambda_value=lam,
        dimensionless_multiplier=float(mu),numerical_rank=rank,columns=phi.shape[1],rows=len(phi),
        rank_rule='eps64*max(N,p)*smax; descriptive only, no SVD truncation in solve',
        free_delta_norm=free_norm if np.isfinite(free_norm) else None,
        regularized_condition=float((s[0]**2+lam)/(s[-1]**2+lam)) if len(s) and (s[-1]**2+lam)>0 else None,
        svd_orthogonality_inf=ortho,kkt_stationarity_relative=kkt,complementarity_relative=comp,
        feasibility_relative=relative_feasibility,boundary_relative_gap=abs(norm/radius-1.),
        centered_before_rms=before,centered_after_rms=after,projection_realization_gap=projection_gap)
