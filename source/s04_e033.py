"""E033 full original-head diagnostic and at most one verified-axis correction.

Reuses E024/E031 convex-hull certificate and one-axis enrichment, extending
metric count to eleven; E032 joint proxy extended to eight coordinates.
No input/model IO or optimization on import.
"""
from itertools import combinations
import numpy as np
from scipy.linalg import lstsq
from scipy.optimize import minimize
import torch
import s04_e027 as old
import s04_e031 as base
import s04_e032 as previous
from s04_e031 import fields,head_state
PROTOCOL='S04-E033/v1-full-head-eleven-guards-one-axis-20261019'
METRICS=base.METRICS+('u_global','u_Z','v_global','v_Z')
UV_TERMS=('UV_global','UV_Z','u_global','u_Z','v_global','v_Z')
RADIUS_FRACTION=.02
MAX_CANDIDATES=9
MAX_PROXY_ITERATIONS=100

def metric_values(problem,q,reference,force_norm,create_graph):
    result=base.metric_values(problem,q,reference,force_norm,create_graph)
    delta=q[:,:2]-problem.ref[:,:2]
    for channel,index in [('u',0),('v',1)]:
        for region,mask in [('global',torch.ones_like(problem.zone)),('Z',problem.zone)]:
            w=problem.mass[mask]
            value=(w*delta[mask,index].square()).sum()/w.sum()/old.US**2
            old.finite(value,channel+'_'+region)
            result[channel+'_'+region]=value
    return {name:result[name] for name in METRICS}

def admit_candidate(values,baseline,relative_delta):
    if set(values)!=set(METRICS) or set(baseline)!=set(METRICS):raise ValueError('eleven-metric schema')
    numbers=[*values.values(),*baseline.values(),relative_delta]
    if not np.isfinite(numbers).all() or min(numbers)<0:raise ValueError('finite nonnegative admission required')
    failures=[name for name in METRICS if values[name]>baseline[name]]
    if relative_delta>RADIUS_FRACTION*(1+1e-12):failures.append('head radius')
    return not failures,failures

def common_descent(gradients,guard=lambda:None):
    """Exact small active-set hull from E024/E031, max rows7->11."""
    a,norms=base.unit_rows(gradients)
    if not 1<=len(a)<=11:raise ValueError('one to eleven gradients required')
    zero=np.flatnonzero(norms==0)
    if len(zero):
        q=np.zeros(a.shape[1]);weights=np.zeros(len(a));weights[zero[0]]=1.
        return q.copy(),q,dict(unit_gradient_margin=0.,resolved_strict=False,reason='finite zero metric gradient',
            zero_gradient_indices=zero.tolist(),weights=weights.tolist(),active=[int(zero[0])],
            normal_norms=norms.tolist(),simplex_sum=1.,min_weight=float(weights.min()),
            certificate_min_gap=0.,largest_unit_slope=0.)
    candidates=[]
    for count in range(1,len(a)+1):
        for active in combinations(range(len(a)),count):
            guard();sub=a[list(active)]
            if count==1:weights=np.ones(1)
            else:
                beta=lstsq((sub[1:]-sub[0]).T,-sub[0],cond=1e-12,lapack_driver='gelsd')[0]
                weights=np.r_[1-beta.sum(),beta]
            if weights.min()< -1e-10:continue
            q=np.einsum('i,ij->j',weights,sub);q2=float(np.einsum('i,i->',q,q))
            gaps=np.einsum('ij,j->i',a,q)-q2
            if gaps.min()< -1e-10 or np.max(abs(gaps[list(active)]))>1e-10:continue
            full=np.zeros(len(a));full[list(active)]=weights;candidates.append((q2,q,full,active,gaps))
    if not candidates:raise ValueError('convex hull numerical certificate unresolved')
    q2,q,weights,active,gaps=min(candidates,key=lambda row:row[0]);margin=float(np.sqrt(q2))
    proposed=-q/margin if margin>1e-8 else np.zeros_like(q)
    resolved=bool(margin>1e-8 and np.einsum('ij,j->i',a,proposed).max()<=-.5*margin)
    direction=proposed if resolved else np.zeros_like(q)
    return direction,q,dict(unit_gradient_margin=margin,resolved_strict=resolved,weights=weights.tolist(),
        active=list(active),normal_norms=norms.tolist(),simplex_sum=float(weights.sum()),
        min_weight=float(weights.min()),certificate_min_gap=float(gaps.min()),
        largest_unit_slope=float(np.einsum('ij,j->i',a,direction).max()))

def enrich_one_axis(old_basis,direction):
    """E024 enrich_basis generalized from two old axes to frozen seven."""
    old_basis=np.asarray(old_basis);direction=np.asarray(direction)
    if old_basis.shape!=(7,2,401) or direction.shape!=(2,401):raise ValueError('exact frozen7/original802 schema')
    if not np.isfinite(old_basis).all() or not np.isfinite(direction).all():raise ValueError('finite enrichment required')
    flat=old_basis.reshape(7,-1);v=direction.ravel()
    if not np.allclose(np.einsum('ij,kj->ik',flat,flat),np.eye(7),rtol=0,atol=1e-12):raise ValueError('old plane orthonormality')
    if abs(np.linalg.norm(v)-1)>1e-12:raise ValueError('unit verified full-head direction required')
    projection=np.einsum('ij,j->i',flat,v);orth=v-np.einsum('i,ij->j',projection,flat);norm=float(np.linalg.norm(orth))
    info=dict(orthogonal_remainder_norm=norm,old_projection_norm=float(np.linalg.norm(projection)),eligible=norm>1e-8)
    if norm<=1e-8:
        info['reason']='verified direction already represented; no forced extra axis'
        return None,None,info
    basis=np.concatenate((old_basis,(orth/norm).reshape(1,2,401)),axis=0);coordinates=np.r_[projection,norm]
    realized=np.einsum('i,ijk->jk',coordinates,basis)
    gram=np.einsum('ijk,ljk->il',basis,basis);gap=float(abs(realized-direction).max())
    if gap>1e-12 or not np.allclose(gram,np.eye(8),rtol=0,atol=1e-12):raise ValueError('one-axis identity unresolved')
    info.update(reconstruction_max_abs=gap,old_axes_bitwise_equal=bool(np.array_equal(basis[:7],old_basis)))
    return basis,coordinates,info

def component_quadratics(error,velocities,weights):
    terms=previous.uv_quadratics(error,velocities,weights)
    for channel,index in [('u',0),('v',1)]:
        e=np.zeros_like(error);e[:,index]=error[:,index]
        v=np.zeros_like(velocities);v[:,:,index]=velocities[:,:,index]
        component=previous.uv_quadratics(e,v,weights)
        for region in ['global','Z']:terms[channel+'_'+region]=component['UV_'+region]
    return terms

def curvature_seed(terms,direction):
    values={}
    for name in UV_TERMS:
        b=float(np.einsum('i,i->',terms[name]['b'],direction))
        aa=float(np.einsum('i,ij,j->',direction,terms[name]['q'],direction))
        if not np.isfinite([b,aa]).all() or b>=0 or aa<=0:raise ValueError('component curvature has no strict descent')
        crossing=-2*b/aa
        values[name]=dict(linear_half=b,quadratic=aa,positive_zero_crossing=crossing)
    fraction=min(1.,.5*min(row['positive_zero_crossing'] for row in values.values()))
    if not np.isfinite(fraction) or fraction<=0:raise ValueError('component seed unresolved')
    return fraction,values

def joint_coefficients(gradients,baseline,terms,seed,margin,guard=lambda:None):
    """One <=8D selection: six exact displacement guards, eleven tangent cones."""
    gradients=np.asarray(gradients);seed=np.asarray(seed);a,norms=base.unit_rows(gradients);k=gradients.shape[1]
    if not 1<=k<=8 or gradients.shape!=(11,k) or seed.shape!=(k,) or set(terms)!=set(UV_TERMS):raise ValueError('augmented proxy schema')
    if np.any(norms==0) or not 1e-8<margin<=1:raise ValueError('strict reconstructed direction certificate required')
    scales=np.array([baseline[n] for n in METRICS])
    if not np.isfinite(scales).all() or np.any(scales<=0):raise ValueError('positive metric scales required')
    raw=gradients[2]/scales[2];kappa=.5*margin
    uv=lambda z,n:previous.quadratic_value(z,terms[n])
    uvgrad=lambda z,n:2*terms[n]['b']+2*np.einsum('ij,j->i',terms[n]['q'],z)
    norm=lambda z:float(np.linalg.norm(z))
    cone=lambda z:-np.einsum('ij,j->i',a,z)-kappa*norm(z)
    conejac=lambda z:-a-kappa*(z/norm(z) if norm(z)>0 else np.zeros(k))[None,:]
    constraints=[dict(type='ineq',fun=lambda x:1-float(np.einsum('i,i',x[:k],x[:k])),jac=lambda x:np.r_[-2*x[:k],0.])]
    for name in UV_TERMS:
        constraints.append(dict(type='ineq',fun=lambda x,n=name:1-uv(x[:k],n),jac=lambda x,n=name:np.r_[-uvgrad(x[:k],n),0.]))
    constraints.extend([
        dict(type='ineq',fun=lambda x:x[-1]-uv(x[:k],'UV_global'),jac=lambda x:np.r_[-uvgrad(x[:k],'UV_global'),1.]),
        dict(type='ineq',fun=lambda x:x[-1]-1-float(np.einsum('i,i',raw,x[:k])),jac=lambda x:np.r_[-raw,1.]),
        dict(type='ineq',fun=lambda x:cone(x[:k]),jac=lambda x:np.column_stack((conejac(x[:k]),np.zeros(11))))])
    seed_t=max(uv(seed,'UV_global'),1+float(np.einsum('i,i',raw,seed)));x0=np.r_[seed,seed_t]
    minimum=lambda x:min(float(np.min(c['fun'](x))) for c in constraints)
    if minimum(x0)< -1e-10:raise ValueError('six-component curvature seed infeasible')
    iterations=[]
    def callback(x):
        guard()
        if not np.isfinite(x).all():raise ValueError('nonfinite proxy iterate')
        iterations.append(dict(index=len(iterations)+1,z=x[:k].tolist(),epigraph=float(x[-1]),minimum_constraint=minimum(x)))
    result=minimize(lambda x:float(x[-1]),x0,jac=lambda x:np.r_[np.zeros(k),1.],method='SLSQP',constraints=constraints,
                    callback=callback,options=dict(maxiter=100,ftol=1e-12))
    z=result.x[:k]
    info=dict(success=bool(result.success),message=str(result.message),iterations=int(result.nit),epigraph=float(result.x[-1]),
        seed_epigraph=float(seed_t),minimum_constraint=minimum(result.x),tangent_cone_margin=kappa,plane_norm=norm(z),
        coefficient_iterations=iterations,predicted_displacement_ratios={name:uv(z,name) for name in UV_TERMS},
        predicted_raw_global=1+float(np.einsum('i,i',raw,z)))
    if not np.isfinite(result.x).all() or not result.success or info['minimum_constraint']< -1e-10:
        raise ValueError('joint proxy numerical certificate unresolved: '+str(info))
    return z,info
