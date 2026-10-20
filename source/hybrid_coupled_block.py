"""Original active-set coupled Newton direction, one sparse general LU only.

No dense Schur, equation regularization, iterative refinement or solver fallback.
Working directions never commit history. Both original-scale block rows are
checked separately against their own RHS and the unchanged physical standards.
"""
import warnings
import hashlib
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import splu
from hybrid_reduced_tangent import coupled_blocks,natural_residual


def true_row_audit(A,B,C,D,du,di,rhs_u,rhs_d,settings,relative):
    ru=np.asarray(A@du+B@di-rhs_u);rd=np.asarray(C@du+D@di-rhs_d)
    u_rhs=float(np.linalg.norm(rhs_u));d_rhs=float(np.linalg.norm(rhs_d))
    u_l2=float(np.linalg.norm(ru));d_l2=float(np.linalg.norm(rd))
    u_inf=float(np.max(abs(ru),initial=0.));d_inf=float(np.max(abs(rd),initial=0.))
    def rounding_bound(X,Y,x,y,b):
        # Standard binary64 sparse dot/add absolute error envelope. No tunable
        # absolute floor: zero terms give zero allowance. Each row has its own
        # operations/magnitudes; the damage row never inherits mechanics scale.
        degree=np.diff(X.tocsr().indptr)+np.diff(Y.tocsr().indptr)+3
        eps=np.finfo(float).eps;gamma=degree*eps/(1-degree*eps)
        magnitude=np.asarray(abs(X)@abs(x)+abs(Y)@abs(y)+abs(b))
        return float(np.linalg.norm(gamma*magnitude))
    u_round=rounding_bound(A,B,du,di,rhs_u);d_round=rounding_bound(C,D,du,di,rhs_d)
    info=dict(mechanics_rhs_l2=u_rhs,damage_rhs_l2=d_rhs,
        mechanics_true_l2=u_l2,mechanics_true_inf=u_inf,
        damage_true_l2=d_l2,damage_true_inf=d_inf,
        mechanics_relative_target=relative*u_rhs,damage_relative_target=relative*d_rhs,
        mechanics_absolute_l2_target=settings.force_tolerance*settings.force_scale,
        damage_absolute_inf_target=settings.damage_tolerance*settings.damage_gradient_scale,
        damage_absolute_l2_target=settings.joint_residual_sum_tolerance,
        mechanics_relative_residual=None if u_rhs==0 else u_l2/u_rhs,
        damage_relative_residual=None if d_rhs==0 else d_l2/d_rhs,
        mechanics_roundoff_l2_bound=u_round,damage_roundoff_l2_bound=d_round,
        mechanics_effective_relative_target=max(relative*u_rhs,u_round),
        damage_effective_relative_target=max(relative*d_rhs,d_round),
        zero_rhs_rule='per-row binary64 sparse dot/add bound only; no arbitrary atol; original absolute targets also required')
    info['passed']=bool(np.isfinite([u_l2,d_l2,u_inf,d_inf,u_rhs,d_rhs]).all()
        and u_l2<=info['mechanics_effective_relative_target']
        and d_l2<=info['damage_effective_relative_target']
        and u_l2<=info['mechanics_absolute_l2_target']
        and d_inf<=info['damage_absolute_inf_target']
        and d_l2<=info['damage_absolute_l2_target'])
    return info,ru,rd


def solve_original_block(A,B,C,D,Ru,Rd,F,inactive,scale,settings,relative,call,remaining,emit,observer=None):
    """A is free mechanical tangent; B/C/D keep full damage support."""
    I=np.flatnonzero(inactive);delta=-np.asarray(F).copy();delta[I]=0.
    # Active natural-map rows are identity. They may move/release; not fixed d_n.
    rhs_u=-np.asarray(Ru)-np.asarray(B@delta)
    rhs_d=-np.asarray(Rd)[I]-np.asarray((D@delta)[I])
    BI=B[:,I].tocsc();CI=C[I].tocsc();DI=D[I][:,I].tocsc()
    remaining()
    K=call('block_sparse_assembly',lambda:sparse.bmat([[A,BI],[CI,DI]],format='csc'))
    K.sum_duplicates();K.eliminate_zeros();K.sort_indices()
    if not np.isfinite(K.data).all() or not np.isfinite(np.r_[rhs_u,rhs_d]).all():
        raise RuntimeError('nonfinite original coupled block')
    h=hashlib.sha256()
    for a in (K.indptr,K.indices,K.data):h.update(np.ascontiguousarray(a).tobytes())
    emit(dict(event='block_structure',dimension=K.shape[0],nnz=K.nnz,
        inactive_nodes=len(I),mechanical_free_dofs=A.shape[0],matrix_id=h.hexdigest(),
        rhs_mechanics_l2=float(np.linalg.norm(rhs_u)),rhs_damage_l2=float(np.linalg.norm(rhs_d)),
        solver='SuperLU COLAMD default threshold pivoting; one factor/solve; no fallback'))
    # Any actual warning here is a recorded scientific stop, not silently used.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        factor=call('block_sparse_factorization',lambda:splu(K,permc_spec='COLAMD'))
    if caught:
        emit(dict(event='block_numerical_warning',warnings=[str(w.message) for w in caught]))
        raise RuntimeError('coupled block factorization warning')
    remaining()
    piv=np.abs(factor.U.diagonal())
    if not np.isfinite(piv).all() or np.any(piv==0):raise RuntimeError('invalid coupled block LU pivot')
    rhs=np.r_[rhs_u,rhs_d]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always');solution=call('block_sparse_solve',lambda:factor.solve(rhs))
    if caught:
        emit(dict(event='block_numerical_warning',warnings=[str(w.message) for w in caught]))
        raise RuntimeError('coupled block solve warning')
    remaining();nu=A.shape[0]
    if not np.isfinite(solution).all():
        bad=dict(passed=False,reason='nonfinite coupled block solution',nonfinite_entries=int(np.sum(~np.isfinite(solution))))
        emit(dict(event='block_nonfinite_solution',**bad))
        if observer is not None:observer(bad,dict(raw_solution=solution,rhs_mechanics=rhs_u,rhs_damage_inactive=rhs_d))
        raise RuntimeError('nonfinite coupled block solution')
    du=solution[:nu];di=solution[nu:]
    info,ru,rd=true_row_audit(A,BI,CI,DI,du,di,rhs_u,rhs_d,settings,relative)
    info.update(inactive_nodes=len(I),mechanical_free_dofs=nu,block_dimension=K.shape[0],block_nnz=K.nnz,
        factor_L_nnz=factor.L.nnz,factor_U_nnz=factor.U.nnz,
        factor_pivot_ratio=float(np.min(piv)/np.max(piv)),matrix_id=h.hexdigest(),
        linear_factorizations=1,linear_solves=1,direction_type='original_coupled_active_set_block')
    delta[I]=di
    emit(dict(event='block_direction',**info))
    if observer is not None:
        observer(info,dict(delta_damage=delta,delta_u_free=du,mechanics_residual_before=np.asarray(Ru),
            damage_residual_before=np.asarray(Rd),natural_residual=F,inactive_mask=inactive,
            rhs_mechanics=rhs_u,rhs_damage_inactive=rhs_d,
            mechanics_true_linear_residual=ru,damage_true_linear_residual=rd))
    if not np.isfinite(solution).all() or not info['passed']:
        raise RuntimeError('coupled block linear solve failed original separate true-row targets')
    return delta,info


def block_direction(backend,old,point,dofs,settings,policy,call,remaining,emit):
    d,u,qp,q=point['d'],point['u'],point['qp'],point['q']
    gradient=np.asarray(qp.hessian@d+qp.linear)
    F,inactive=natural_residual(d,gradient,old.damage,settings.damage_gradient_scale)
    w=backend.mechanics_workspace
    matrix=call('block_current_mechanics_assembly',lambda:w.assemble(d,u))
    free=np.ones(len(u),bool);free[np.asarray(dofs,int)]=False;U=np.flatnonzero(free)
    A=matrix[U][:,U].tocsc();Ru=np.asarray(matrix@u)[U]
    B,C,D=call('coupled_residual_tangent',lambda:coupled_blocks(backend,old,u,d,qp,q))
    hook=getattr(backend,'block_direction_observer',None)
    def observer(info,vectors):
        if hook is not None:
            call('block_direction_evidence',lambda:hook(point,info,dict(vectors,free_dofs=U)))
    return solve_original_block(A,B[U].tocsc(),C[:,U].tocsc(),D,Ru,gradient,F,inactive,
        settings.damage_gradient_scale,settings,policy.block_relative_tolerance,
        call,remaining,emit,observer)
