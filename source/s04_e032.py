"""E032: frozen saved-gradient plane, exact UV quadratics and joint coefficients.

Reuses E031 physical metric/head definitions and E024 small-coefficient SLSQP
pattern. No model/data IO or optimization on import.
"""
import numpy as np
from scipy.optimize import minimize
import s04_e031 as previous
from s04_e031 import fields, head_state, metric_values, admit_candidate, common_descent, uv_safe_fraction
PROTOCOL='S04-E032/v1-fixed-damage-joint-head-plane-20261018'
METRICS=previous.METRICS
RADIUS_FRACTION=.02
MAX_CANDIDATES=9
MAX_PROXY_ITERATIONS=100

def frozen_basis(saved_gradients):
    a,_=previous.unit_rows(saved_gradients)
    if a.shape!=(7,802):raise ValueError('exact saved E031 seven-by-802 matrix required')
    _,singular,vh=np.linalg.svd(a,full_matrices=False)
    rank=int(np.count_nonzero(singular>1e-10*singular[0]))
    if rank<1:raise ValueError('saved gradient span unresolved')
    basis=vh[:rank]
    gram=np.einsum('ij,kj->ik',basis,basis)
    if not np.allclose(gram,np.eye(rank),atol=1e-12,rtol=1e-12):raise ValueError('plane orthonormality')
    return basis,dict(dimension=rank,singular_values=singular.tolist(),relative_rank_cutoff=1e-10)

def uv_quadratics(error,velocities,weights):
    error,velocities=np.asarray(error),np.asarray(velocities)
    if error.ndim!=2 or error.shape[1]!=2 or velocities.ndim!=3 or velocities.shape[1:]!=error.shape:raise ValueError('UV plane schema')
    if not np.isfinite(error).all() or not np.isfinite(velocities).all():raise ValueError('finite UV plane required')
    result={}
    for name,w in weights.items():
        w=np.asarray(w)
        if w.shape!=(len(error),) or not np.isfinite(w).all() or np.any(w<0) or w.sum()<=0:raise ValueError('UV weights')
        c=float(np.einsum('n,na,na->',w,error,error))
        if c<=0:raise ValueError('positive own UV error required')
        b=np.einsum('n,na,kna->k',w,error,velocities)/c
        q=np.einsum('n,kna,lna->kl',w,velocities,velocities)/c
        if not np.isfinite(b).all() or not np.isfinite(q).all():raise ValueError('UV quadratic overflow')
        result[name]=dict(b=b,q=q,constant=c)
    if set(result)!={'UV_global','UV_Z'}:raise ValueError('both UV regions required')
    return result

def quadratic_value(z,term):
    return float(1+2*np.einsum('i,i',term['b'],z)+np.einsum('i,ij,j',z,term['q'],z))

def joint_coefficients(gradients,baseline,terms,seed,margin,guard=lambda:None):
    """One <=7D convex proxy, epigraph balances actual UV quadratic/raw tangent.

    Seven strict tangent cones protect descent direction, not finite physics.
    Actual seven metrics and endpoint primary remain authoritative.
    """
    gradients=np.asarray(gradients);seed=np.asarray(seed)
    a,norms=previous.unit_rows(gradients);k=gradients.shape[1]
    if not 1<=k<=7 or gradients.shape!=(7,k) or seed.shape!=(k,):raise ValueError('joint proxy schema')
    if np.any(norms==0) or not 1e-8<margin<=1:raise ValueError('strict plane certificate required')
    scales=np.array([baseline[n] for n in METRICS])
    if not np.isfinite(scales).all() or np.any(scales<=0):raise ValueError('positive metric scales required')
    raw=gradients[2]/scales[2];kappa=.5*margin
    uv=lambda z,n:quadratic_value(z,terms[n])
    uvgrad=lambda z,n:2*terms[n]['b']+2*np.einsum('ij,j->i',terms[n]['q'],z)
    norm=lambda z:float(np.linalg.norm(z))
    cone=lambda z:-np.einsum('ij,j->i',a,z)-kappa*norm(z)
    conejac=lambda z:-a-kappa*(z/norm(z) if norm(z)>0 else np.zeros(k))[None,:]
    constraints=[
        dict(type='ineq',fun=lambda x:1-float(np.einsum('i,i',x[:k],x[:k])),jac=lambda x:np.r_[-2*x[:k],0.]),
        dict(type='ineq',fun=lambda x:1-uv(x[:k],'UV_global'),jac=lambda x:np.r_[-uvgrad(x[:k],'UV_global'),0.]),
        dict(type='ineq',fun=lambda x:1-uv(x[:k],'UV_Z'),jac=lambda x:np.r_[-uvgrad(x[:k],'UV_Z'),0.]),
        dict(type='ineq',fun=lambda x:x[-1]-uv(x[:k],'UV_global'),jac=lambda x:np.r_[-uvgrad(x[:k],'UV_global'),1.]),
        dict(type='ineq',fun=lambda x:x[-1]-1-float(np.einsum('i,i',raw,x[:k])),jac=lambda x:np.r_[-raw,1.]),
        dict(type='ineq',fun=lambda x:cone(x[:k]),jac=lambda x:np.column_stack((conejac(x[:k]),np.zeros(7))))]
    seed_t=max(uv(seed,'UV_global'),1+float(np.einsum('i,i',raw,seed)))
    x0=np.r_[seed,seed_t]
    minimum=lambda x:min(float(np.min(c['fun'](x))) for c in constraints)
    if minimum(x0)<-1e-10:raise ValueError('prospective curvature seed infeasible')
    iterations=[]
    def callback(x):
        guard()
        if not np.isfinite(x).all():raise ValueError('nonfinite proxy iterate')
        iterations.append(dict(index=len(iterations)+1,z=x[:k].tolist(),epigraph=float(x[-1]),minimum_constraint=minimum(x)))
    result=minimize(lambda x:float(x[-1]),x0,jac=lambda x:np.r_[np.zeros(k),1.],
                    method='SLSQP',constraints=constraints,callback=callback,
                    options=dict(maxiter=MAX_PROXY_ITERATIONS,ftol=1e-12))
    z=result.x[:k]
    info=dict(success=bool(result.success),message=str(result.message),iterations=int(result.nit),
              epigraph=float(result.x[-1]),seed_epigraph=float(seed_t),minimum_constraint=minimum(result.x),
              tangent_cone_margin=kappa,plane_norm=norm(z),coefficient_iterations=iterations,
              predicted_UV_global=uv(z,'UV_global'),predicted_UV_Z=uv(z,'UV_Z'),
              predicted_raw_global=1+float(np.einsum('i,i',raw,z)))
    if not np.isfinite(result.x).all():raise ValueError('nonfinite joint proxy result')
    if not result.success or info['minimum_constraint']< -1e-10:raise ValueError('joint proxy numerical certificate unresolved: '+str(info))
    return z,info
