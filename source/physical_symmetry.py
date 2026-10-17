"""Opt-in SENT physical-field parity terms, independent of training/history.

Points are fixed seed probes. The helper constructs their exact reflected
partners and assigns each pair equal weight. It neither changes the fields nor
projects damage/history. Weights/scales must be declared by the caller.
"""
import torch


def physical_symmetry_terms(field_comp, points, pair_weights, displacement_scale):
    """Return dimensionless alpha/u/v squared residuals of complete fields.

    Valid for a y-centred rectangular SENT toy with vertical prescribed U.
    Residuals: d-dR, (u-uR)/Uref, (v+vR-U)/Uref. Uref is fixed and positive,
    including at U=0. No training, gradient adaptation or history update occurs.
    Seed locations and pair weights are fixed data, not learned quantities.
    """
    if not torch.is_tensor(points) or points.ndim != 2 or points.shape[1] != 2 or len(points)==0:
        raise ValueError('physical symmetry requires nonempty [N,2] fixed probe points')
    if not points.is_floating_point() or points.requires_grad or not bool(torch.isfinite(points).all()):
        raise ValueError('probe points must be finite fixed floating-point data')
    weights=torch.as_tensor(pair_weights,device=points.device,dtype=points.dtype)
    scale=torch.as_tensor(displacement_scale,device=points.device,dtype=points.dtype)
    if weights.requires_grad or weights.shape != (len(points),) or not bool(torch.isfinite(weights).all()):
        raise ValueError('one finite fixed pair weight is required per seed probe')
    if bool((weights<0).any()) or not bool(weights.sum()>0) or not bool(torch.isfinite(weights.sum())):
        raise ValueError('pair weights must be nonnegative with finite positive sum')
    if scale.requires_grad or scale.numel()!=1 or not bool(torch.isfinite(scale).all()) or not bool(scale>0):
        raise ValueError('displacement_scale must be finite, fixed and strictly positive')
    domain=torch.as_tensor(field_comp.domain_extrema,device=points.device,dtype=points.dtype)
    if domain.shape!=(2,2) or not bool(torch.isfinite(domain).all()) or bool((domain[:,1]<=domain[:,0]).any()):
        raise ValueError('expected finite rectangular domain_extrema')
    tol=10*torch.finfo(points.dtype).eps
    if not bool(torch.abs(domain[1].sum())<=tol):
        raise ValueError('physical symmetry currently requires domain centred at y=0')
    angle=torch.as_tensor(field_comp.theta,device=points.device,dtype=points.dtype)
    if angle.numel()!=1 or not bool(torch.isfinite(angle).all()) or not bool(torch.abs(torch.cos(angle))<=1e-6) or not bool(torch.abs(torch.sin(angle)-1)<=1e-6):
        raise ValueError('physical symmetry currently supports vertical tensile loading only')
    load=torch.as_tensor(field_comp.lmbda,device=points.device,dtype=points.dtype)
    if load.numel()!=1 or not bool(torch.isfinite(load).all()) or load.requires_grad:
        raise ValueError('prescribed displacement must be one finite fixed scalar')
    if bool((points<domain[:,0]-tol).any()) or bool((points>domain[:,1]+tol).any()):
        raise ValueError('probe support leaves the declared rectangle')
    reflected=points*points.new_tensor([1.,-1.])
    u,v,d=field_comp.fieldCalculation(torch.cat((points,reflected),0))
    n=len(points)
    if any(q.shape!=(2*n,) or not bool(torch.isfinite(q).all()) for q in (u,v,d)):
        raise ValueError('complete physical fields must be finite flat vectors')
    w=weights/weights.sum()
    return {'alpha':torch.sum(w*(d[:n]-d[n:]).square()),
            'u':torch.sum(w*((u[:n]-u[n:])/scale).square()),
            'v':torch.sum(w*((v[:n]+v[n:]-load)/scale).square())}
