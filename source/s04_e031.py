"""E031 fixed physical damage, frozen backbone, original UV output coordinates.

Geometry helpers reused from E024 D009/D010; common-gradient count extended5->7.
No model/data IO or optimizer on import.
"""
from itertools import combinations
import numpy as np
from scipy.linalg import lstsq
import torch
import s04_e027 as old
PROTOCOL='S04-E031/v1-fixed-damage-UV-head-common-step-20261018'
METRICS=('UV_global','UV_Z','raw_global','raw_Z','active_global','active_Z','force_squared')
RADIUS_FRACTION=.02
MAX_CANDIDATES=9


def head_state(model):
    return torch.cat((model.output_layer.weight[:2],model.output_layer.bias[:2,None]),1).detach().clone()


def fields(theta,features,problem,damage):
    if theta.shape!=(2,features.shape[1]+1):raise ValueError('original UV W+b coordinates required')
    raw=features@theta[:,:-1].T+theta[:,-1]
    y=problem.xy[:,1];bubble=(y+.5)*(.5-y)
    return torch.stack((old.US*bubble*raw[:,0],old.US*(bubble*raw[:,1]+y+.5),damage),1)


def metric_values(problem,q,reference,force_norm,create_graph):
    parts=problem.parts(*q.unbind(1));delta=q[:,:2]-problem.ref[:,:2];metrics={}
    for name,mask in [('global',torch.ones_like(problem.zone)),('Z',problem.zone)]:
        w=problem.mass[mask];metrics['UV_'+name]=(w*delta[mask].square().sum(1)).sum()/w.sum()/old.US**2
    for name,mask in [('global',torch.ones_like(problem.gp_zone)),('Z',problem.gp_zone)]:
        w=problem.w[mask]
        for k,index in [('raw',3),('active',4)]:
            denom=(w*reference[index][mask].square()).sum()
            if denom<=1e-24*w.sum():raise ValueError('reference scale unavailable')
            metrics[k+'_'+name]=(w*(parts[index][mask]-reference[index][mask]).square()).sum()/denom
    force=problem.force(q,create_graph=create_graph)[problem.free]
    metrics['force_squared']=force.square().sum()/force_norm**2
    for name,v in metrics.items():
        old.finite(v,name)
        if v<0:raise ValueError('negative metric')
    return {name:metrics[name] for name in METRICS}


def admit_candidate(values,baseline,relative_delta):
    if set(values)!=set(METRICS) or set(baseline)!=set(METRICS):raise ValueError('metric schema')
    if not np.isfinite([*values.values(),*baseline.values(),relative_delta]).all():raise ValueError('nonfinite candidate')
    failures=[name for name in METRICS if values[name]>baseline[name]]
    if relative_delta>RADIUS_FRACTION*(1+1e-12):failures.append('head radius')
    return not failures,failures


def unit_rows(a):
    a = np.asarray(a, dtype=np.float64)
    if a.ndim != 2 or not np.isfinite(a).all():
        raise ValueError('finite row matrix required')
    norms = np.linalg.norm(a, axis=1)
    return np.divide(a, norms[:, None], out=np.zeros_like(a), where=norms[:, None] > 0), norms


def common_descent(gradients):
    """Min-norm convex hull of <=7 unit gradients; nonzero q gives common descent."""
    a, norms = unit_rows(gradients)
    if not 1 <= len(a) <= 7 or np.any(norms == 0):
        raise ValueError('common descent requires 1..7 nonzero gradients')
    candidates = []
    for count in range(1, len(a) + 1):
        for active in combinations(range(len(a)), count):
            sub = a[list(active)]
            if count == 1:
                weights = np.ones(1)
            else:
                beta = lstsq((sub[1:] - sub[0]).T, -sub[0], cond=1e-12, lapack_driver='gelsd')[0]
                weights = np.r_[1 - beta.sum(), beta]
            if weights.min() < -1e-10:
                continue
            q = np.einsum('i,ij->j', weights, sub)
            q2 = float(np.dot(q, q))
            gaps = a @ q - q2
            if gaps.min() < -1e-10 or np.max(abs(gaps[list(active)])) > 1e-10:
                continue
            full = np.zeros(len(a)); full[list(active)] = weights
            candidates.append((q2, q, full, active, gaps))
    if not candidates:
        raise ValueError('convex hull certificate not resolved')
    q2, q, weights, active, gaps = min(candidates, key=lambda r: r[0])
    margin = float(np.sqrt(q2))
    proposed = -q / margin if margin > 1e-8 else np.zeros_like(q)
    # A tiny q amplifies hull certificate roundoff: verify every actual slope.
    resolved = bool(margin > 1e-8 and np.max(a @ proposed) <= -.5 * margin)
    direction = proposed if resolved else np.zeros_like(q)
    return direction, q, dict(unit_gradient_margin=margin, resolved_strict=resolved,
                             weights=weights.tolist(), active=list(active), normal_norms=norms.tolist(),
                             simplex_sum=float(weights.sum()), min_weight=float(weights.min()),
                             certificate_min_gap=float(gaps.min()),
                             largest_unit_slope=float(np.max(a @ direction)))


def uv_safe_fraction(error, velocity, weights):
    """Half the smallest positive UV zero crossing; velocity is one full R step."""
    error,velocity=np.asarray(error),np.asarray(velocity)
    if error.ndim!=2 or error.shape!=velocity.shape or error.shape[1]!=2:
        raise ValueError('UV quadratic schema')
    if not np.isfinite(error).all() or not np.isfinite(velocity).all():raise ValueError('nonfinite UV quadratic')
    terms={}
    for name,weight in weights.items():
        weight=np.asarray(weight)
        if weight.shape!=(len(error),) or not np.isfinite(weight).all() or np.any(weight<0) or weight.sum()<=0:
            raise ValueError('UV quadratic weights')
        c=float(np.sum(weight[:,None]*error**2))
        b=float(np.sum(weight[:,None]*error*velocity))
        aa=float(np.sum(weight[:,None]*velocity**2))
        if not np.isfinite([c,b,aa]).all() or c<=0 or aa<=0 or b>=0:
            raise ValueError('no resolved descending UV quadratic')
        crossing=-2*b/aa
        if not np.isfinite(crossing) or crossing<=0:raise ValueError('UV crossing unresolved')
        terms[name]=dict(constant=c,linear_half=b,quadratic=aa,positive_zero_crossing=crossing)
    if not terms:raise ValueError('UV regions missing')
    fraction=min(1.,.5*min(t['positive_zero_crossing'] for t in terms.values()))
    if fraction<=0 or not np.isfinite(fraction):raise ValueError('UV safe fraction unresolved')
    return fraction,terms
