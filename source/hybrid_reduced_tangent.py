"""Piecewise derivative of the ORIGINAL coupled Amor/Carrara residual.

No differentiation of an energy with substituted fatigue, and no history
updates.  The Schur inverse action uses one fixed CURRENT mechanical LU.
"""
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import LinearOperator, gmres, splu
from damage_conditioned_equilibrium import plane_strain_tensors


def _scatter(local, rows, cols, shape):
    return sparse.coo_matrix((local.ravel(),
        (np.repeat(rows, cols.shape[1], axis=1).ravel(),
         np.tile(cols, (1, rows.shape[1])).ravel())), shape=shape).tocsc()


def coupled_blocks(backend, old, u, d, qp, trial):
    """Return B=Ru,d, C=Rd,u, D=Rd,d including trial-fatigue chain.

    Loading/fatigue-threshold equality chooses the inactive one-sided branch.
    Trace equality follows the original >=0 tensile branch. These are stated
    generalized derivatives; original residuals are always re-evaluated.
    """
    k=backend.kin; n=len(d); cells=k.cells; ed=k.element_dofs
    ue=np.asarray(u)[ed]; de=np.asarray(d)[cells]
    _,vol,dev,bulk,shear=plane_strain_tensors(
        backend.material['youngs_modulus'],backend.material['poisson_ratio'])
    b_local=np.zeros((len(cells),8,4)); c_extra=np.zeros((len(cells),4,8))
    d_extra=np.zeros((len(cells),4,4))
    coeff=(backend.gc/backend.length_scale)/(8./3.)
    for j in range(4):
        N=k.shape_values[j]; B=k.b_matrices[:,j]
        strain=np.einsum('eij,ej->ei',B,ue)
        pos=(strain[:,0]+strain[:,1])>=0.
        constitutive=2*shear*dev[None,:,:]+pos[:,None,None]*bulk*vol[None,:,:]
        stress=np.einsum('eij,ej->ei',constitutive,strain)
        psi=.5*np.einsum('ei,ei->e',strain,stress)
        psi_u=np.einsum('eai,ea->ei',B,stress)
        dg=de@N; w=backend.material['thickness']*k.det_jacobians[:,j]
        b_local+=(-2*w*(1-dg))[:,None,None]*psi_u[:,:,None]*N[None,None,:]
        loading=(trial.driver[:,j]>old.driver[:,j])
        df_dA=np.where(trial.accumulated[:,j]>backend.alpha_t,
            -backend.power*trial.fatigue[:,j]/(trial.accumulated[:,j]+backend.alpha_t),0.)
        df_dr=df_dA*loading
        df_du=(df_dr*(1-dg)**2)[:,None]*psi_u
        df_dd=(-2*df_dr*(1-dg)*psi)[:,None]*N
        gx=B[:,0,0::2]; gy=B[:,1,1::2]
        gradx=np.einsum('ei,ei->e',gx,de); grady=np.einsum('ei,ei->e',gy,de)
        fracture=(w*coeff)[:,None]*(N[None,:]+2*backend.length_scale**2*(
            gx*gradx[:,None]+gy*grady[:,None]))
        c_extra+=fracture[:,:,None]*df_du[:,None,:]
        d_extra+=fracture[:,:,None]*df_dd[:,None,:]
    B=_scatter(b_local,ed,cells,(2*n,n))
    C=(B.T+_scatter(c_extra,cells,ed,(n,2*n))).tocsc()
    D=(qp.hessian+_scatter(d_extra,cells,cells,(n,n))).tocsc()
    if any(not np.isfinite(x.data).all() for x in (B,C,D)):
        raise RuntimeError('nonfinite original-residual tangent')
    return B,C,D


def natural_residual(d, gradient, lower, scale):
    z=np.asarray(d)-np.asarray(gradient)/scale
    F=np.asarray(d)-np.clip(z,lower,1.)
    inactive=(z>lower)&(z<1.)&(lower<1.)
    return F,inactive


def reduced_direction(backend,old,point,dofs,settings,policy,call,remaining,emit):
    d,u,qp,q=point['d'],point['u'],point['qp'],point['q']
    gradient=np.asarray(qp.hessian@d+qp.linear)
    F,inactive=natural_residual(d,gradient,old.damage,settings.damage_gradient_scale)
    I=np.flatnonzero(inactive)
    # Active rows of the natural-map derivative are identity, not permanently
    # fixed nodes.  A bound node with the wrong gradient sign is inactive.
    delta=-F.copy();delta[inactive]=0.;delta[old.damage==1.]=0.
    if not len(I):return delta,dict(inactive_nodes=0,matvecs=0,reason='projected_active_rows')
    w=backend.mechanics_workspace
    cert=call('schur_current_mechanics_factor',lambda:w.certify_factor(d,u,dofs,observe=backend.mechanics_observer))
    remaining()
    # Keep a local fixed reference: candidate mechanics may later replace cache.
    factor=w.factor
    free=np.ones(len(u),bool);free[np.asarray(dofs,int)]=False
    U=np.flatnonzero(free)
    B,C,D=call('coupled_residual_tangent',lambda:coupled_blocks(backend,old,u,d,qp,q))
    Bu=B[U].tocsc();Cu=C[:,U].tocsc();counts={'matvecs':0,'inverse_actions':0}
    def S(v):
        remaining();counts['matvecs']+=1
        if counts['matvecs']>policy.schur_action_limit:
            raise RuntimeError('Schur action budget exhausted')
        value=D@v
        if len(U):
            counts['inverse_actions']+=1
            value=value-Cu@factor.solve(np.asarray(Bu@v))
        if not np.isfinite(value).all():raise RuntimeError('nonfinite Schur action')
        return np.asarray(value)
    rhs=-settings.damage_gradient_scale*F[I]
    if np.any(delta):rhs-=S(delta)[I]
    H=qp.hessian[I][:,I].tocsc()
    pre=call('schur_damage_preconditioner',lambda:splu(H))
    def action(v):
        full=np.zeros(len(d));full[I]=v
        return S(full)[I]
    op=LinearOperator((len(I),len(I)),matvec=action,dtype=float)
    M=LinearOperator(op.shape,matvec=pre.solve,dtype=float)
    residuals=[]
    def callback(r):
        remaining();residuals.append(float(r))
        if not np.isfinite(r):raise RuntimeError('nonfinite Schur Krylov residual')
    target=policy.schur_relative_tolerance*float(np.linalg.norm(rhs))
    if not np.any(rhs):solution=np.zeros(len(I));code=0
    else:
        solution,code=call('schur_krylov',lambda:gmres(op,rhs,M=M,rtol=policy.schur_relative_tolerance,
            atol=0.,restart=policy.schur_restart,maxiter=policy.schur_cycles,
            callback=callback,callback_type='pr_norm'))
    true=float(np.linalg.norm(action(solution)-rhs))
    info=dict(inactive_nodes=len(I),linear_iterations=len(residuals),code=int(code),
        true_residual=true,target=target,mechanics_matrix_key=cert.get('matrix_key'),
        preconditioner='frozen-QP inactive Hessian',fixed_current_A_inverse=True,**counts)
    emit(dict(event='schur_direction',**info))
    if code!=0 or not np.isfinite(solution).all() or true>target*(1+1e-10):
        raise RuntimeError('Schur linear solve failed original true-residual target')
    delta[I]=solution
    return delta,info
