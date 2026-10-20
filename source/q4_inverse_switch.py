"""Right-direction VI solver on supplied Q4 states; no primal FEM driver.

History variables are eliminated by the exact directional history map. A
sparse interval enclosure covers EVERY constitutive selection, not only the
Newton branch. A positive strong-monotonicity bound proves at most one VI
solution in exact arithmetic; a converged independently audited solution then
supplies existence. Bounds use padded float64, not interval proof software.
"""
from dataclasses import dataclass
import hashlib
import json
from time import monotonic

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import splu

from damage_conditioned_equilibrium import plane_strain_tensors
from hybrid_history import frozen_array
from q4_inverse_derivatives import Variation, _array, _indices
from q4_inverse_sparse import (SparseLimits, SparsePreparationFailure, _check_time,
    _comparison_inverse_inf, _norm_upper, _gamma, _up)
from q4_inverse_trajectory import DirectionalTransitionProblem, freeze_variation


@dataclass(frozen=True)
class SwitchLimits:
    sparse: SparseLimits
    max_iterations: int
    max_backtracks: int
    armijo: float = 1.e-4

    def __post_init__(self):
        if not isinstance(self.sparse, SparseLimits):
            raise ValueError('explicit sparse resource limits required')
        if any(type(v) is not int or v <= 0 for v in (self.max_iterations, self.max_backtracks)):
            raise ValueError('positive iteration and line-search budgets required')
        if not np.isfinite(self.armijo) or not 0 < self.armijo < .5:
            raise ValueError('invalid Armijo coefficient')


def _fingerprint(p):
    h = hashlib.sha256()
    h.update(p.r.old.fingerprint().encode())
    h.update(json.dumps(vars(p.r.material), sort_keys=True).encode())
    h.update(json.dumps(vars(p.margins), sort_keys=True).encode())
    for a in (p.u, p.d, p.bc, p.free_u, p.fixed, p.interior,
              p.weak_lower, p.weak_upper, p.strong_lower, p.strong_upper,
              p.r.kin.points, p.r.kin.cells):
        h.update(np.ascontiguousarray(a).tobytes())
    h.update(np.asarray([p.force_scale,p.damage_scale,p.history_scale]).tobytes())
    return h.hexdigest()


def _assemble(p, nodes, limits, started, *, variation=None, old=None, parameters=None):
    """Selected analytic Jacobian OR all-selection entrywise interval hull.

    Assemble local 12x12 blocks; no global basis probing or dense native matrix.
    Products of history/fatigue selections are enclosed in [0,1]. Correlations
    are deliberately over-enclosed, making the uniqueness test sufficient only.
    """
    r,m=p.r,p.r.material; size=len(p.free_u)+len(nodes)
    if size > limits.max_unknowns or r.e > limits.max_elements:
        raise SparsePreparationFailure('switch_assembly','declared dimension budget exceeded')
    reduced=np.full(3*r.n,-1,dtype=int)
    reduced[p.free_u]=np.arange(len(p.free_u))
    reduced[2*r.n+nodes]=len(p.free_u)+np.arange(len(nodes))
    point=r.evaluate(p.u,p.d)
    C,vol,dev,bulk,shear=plane_strain_tensors(m.youngs_modulus,m.poisson_ratio)
    lower=sparse.csr_matrix((size,size)); upper=lower.copy()
    selected=variation is not None
    out=None if not selected else r.directional(p.u,p.d,variation.displacement,variation.damage,
                           old_variation=old,parameters=parameters,strict=False,margins=p.margins)
    for start in range(0,r.e,limits.chunk_elements):
        _check_time(started,limits,'switch_assembly')
        stop=min(start+limits.chunk_elements,r.e); B=r.B[start:stop]
        eps=np.einsum('egai,ei->ega',B,p.u[r.dofs[start:stop]])
        deps=None if not selected else np.einsum('egai,ei->ega',B,variation.displacement[r.dofs[start:stop]])
        local_d=p.d[r.cells[start:stop]]
        grad_d=np.einsum('egai,ei->ega',r.grad[start:stop],local_d)
        lo=np.zeros((stop-start,12,12)); hi=lo.copy()
        for gp in range(4):
            N=r.shape[gp]; b=B[:,gp]; tr=eps[:,gp,0]+eps[:,gp,1]
            trace_switch=abs(tr)<=p.margins.strain
            # The nominal directional map is continuous only at an exact
            # constitutive kink. Do not certify a snapped nearby nonzero base.
            gap=point.driver[start:stop,gp]-r.old.driver[start:stop,gp]
            fg=point.accumulated[start:stop,gp]-m.alpha_t
            if np.any(trace_switch & (tr!=0)) or np.any((abs(gap)<=p.margins.energy)&(gap!=0)) or np.any((abs(fg)<=p.margins.energy)&(fg!=0)):
                raise SparsePreparationFailure('switch_domain','nonzero nominal kink requires tighter state/branch evidence')
            dg=local_d@N; g=(1-dg)**2; psi=point.raw[start:stop,gp]
            f=point.fatigue[start:stop,gp]; A=point.accumulated[start:stop,gp]
            sp=np.einsum('eab,eb->ea',np.where((tr>0)[:,None,None],C,2*shear*dev),eps[:,gp])
            v=np.einsum('eai,ea->ei',b,sp)
            grad=r.grad[start:stop,gp]
            fracture=N[None,:]/m.length_scale+2*m.length_scale*np.einsum('eai,ea->ei',grad,grad_d[:,gp])
            if selected:
                cp_sign=np.where(trace_switch,deps[:,gp,0]+deps[:,gp,1]>=0,tr>0)
                hsel=np.where(abs(gap)<=p.margins.energy,out.driver[start:stop,gp]-old.driver[start:stop,gp]>=0,gap>0)
                dT=parameters[2]
                decay=f*m.power*(dT/m.alpha_t-(out.accumulated[start:stop,gp]+dT)/(A+m.alpha_t))
                fsel=np.where(abs(fg)<=p.margins.energy,decay<0,fg>0)
                choices=[(cp_sign,hsel*fsel)]
            else:
                cp_low=(tr>0)&~trace_switch; cp_high=(tr>0)|trace_switch
                product_low=(gap>p.margins.energy)&(fg>p.margins.energy)
                product_high=(gap>=-p.margins.energy)&(fg>=-p.margins.energy)
                choices=[(cp,h) for cp in (cp_low,cp_high) for h in (product_low,product_high)]
            candidates=[]
            for cp_sign,hsel in choices:
                cp=np.where(cp_sign[:,None,None],C,2*shear*dev)
                cm=np.where(cp_sign[:,None,None],0.,bulk*vol)
                fA=-m.power*f/(A+m.alpha_t)*hsel
                dfdu=(fA*g)[:,None]*v
                dfdd=(fA*(-2*(1-dg)*psi))[:,None]*N
                block=np.zeros((stop-start,12,12))
                block[:,:8,:8]=np.einsum('eai,eab,ebj->eij',b,g[:,None,None]*cp+cm,b)
                block[:,:8,8:]=(-2*(1-dg))[:,None,None]*v[:,:,None]*N[None,None,:]
                block[:,8:,:8]=2*(dg-1)[:,None,None]*N[None,:,None]*v[:,None,:]+m.gc/(8/3)*fracture[:,:,None]*dfdu[:,None,:]
                block[:,8:,8:]=2*psi[:,None,None]*N[None,:,None]*N[None,None,:]
                block[:,8:,8:]+=(2*m.gc*m.length_scale*f/(8/3))[:,None,None]*np.einsum('eai,eaj->eij',grad,grad)
                block[:,8:,8:]+=m.gc/(8/3)*fracture[:,:,None]*dfdd[:,None,:]
                candidates.append(block*r.weights[start:stop,gp,None,None])
            lo+=np.minimum.reduce(candidates); hi+=np.maximum.reduce(candidates)
        indices=reduced[np.c_[r.dofs[start:stop],2*r.n+r.cells[start:stop]]]
        row=np.repeat(indices,12,axis=1).ravel(); col=np.tile(indices,(1,12)).ravel()
        keep=(row>=0)&(col>=0)
        pieces=[]
        for local in (lo,hi):
            if not np.isfinite(local).all():
                raise SparsePreparationFailure('switch_assembly','nonfinite local Jacobian')
            piece=sparse.coo_matrix((local.ravel()[keep],(row[keep],col[keep])),shape=(size,size)).tocsr()
            pieces.append(piece)
        lower=lower+pieces[0]; upper=upper+pieces[1]
        if max(lower.nnz,upper.nnz)>limits.max_matrix_nnz:
            raise SparsePreparationFailure('switch_assembly','matrix nnz budget exceeded')
    return lower.tocsc(),upper.tocsc()


def _monotonicity_bounds(lower,upper,weights):
    """Weighted Gershgorin bound for EVERY symmetric generalized derivative."""
    n=lower.shape[0]
    if not n:
        return 1.,0.
    # Outward numerical padding, including accumulated element sum error.
    magnitude=abs(lower).maximum(abs(upper))
    pad=magnitude*(128*np.finfo(float).eps*(n+1))
    lower=lower-pad; upper=upper+pad
    slo=(lower+lower.T)*.5; shi=(upper+upper.T)*.5
    off=abs(slo).maximum(abs(shi)).tocsr(); off.setdiag(0); off.eliminate_zeros()
    radius=np.asarray(off@weights).ravel()/weights
    mu=float(np.min(slo.diagonal()-radius))
    norm1=float(np.max(np.asarray(magnitude.sum(axis=0)).ravel(),initial=0))
    normi=float(np.max(np.asarray(magnitude.sum(axis=1)).ravel(),initial=0))
    lipschitz=float(np.sqrt(norm1*normi)*(1+128*np.finfo(float).eps*(n+1)))
    return float(np.nextafter(mu,-np.inf)),float(np.nextafter(lipschitz,np.inf))


def _ldlt_monotonicity_bounds(lower,upper,limits,started):
    """Sparse positive-pivot LDL^T plus interval-radius perturbation bound.

    Unlike testing a selected Newton branch, this lower bound covers all
    generalized derivatives in the assembled hull. No eigenvalue estimation
    or dense inverse is trusted as a lower bound. Native use needs a watchdog.
    """
    n=lower.shape[0]
    if not n:
        return 1.,0.,dict(uniqueness_factorizations=0)
    magnitude=abs(lower).maximum(abs(upper))
    padding=magnitude*(128*np.finfo(float).eps*(n+1))
    lower=lower-padding; upper=upper+padding
    center=((lower+upper+lower.T+upper.T)*.25).tocsc()
    radius=((upper-lower+upper.T-lower.T)*.25).tocsc()
    radius_norm=_norm_upper(radius,1)
    lipschitz=_up(np.sqrt(_up(_norm_upper(magnitude,0)*_norm_upper(magnitude,1))))
    _check_time(started,limits,'switch_uniqueness_factor')
    try:
        lu=splu(center,permc_spec='MMD_AT_PLUS_A',diag_pivot_thresh=0.,
                options={'SymmetricMode':True,'Equil':False})
    except (RuntimeError,ValueError) as exc:
        raise SparsePreparationFailure('switch_uniqueness','symmetric midpoint factorization inconclusive') from exc
    _check_time(started,limits,'switch_uniqueness_factor')
    if lu.L.nnz+lu.U.nnz>limits.max_factor_nnz:
        raise SparsePreparationFailure('switch_uniqueness_factor','factor fill budget exceeded')
    diagonal=lu.U.diagonal()
    if not np.array_equal(lu.perm_r,lu.perm_c) or np.any(diagonal<=0):
        raise SparsePreparationFailure('switch_uniqueness','symmetric positive-pivot evidence unavailable')
    # B=L D L^T is SPD by construction. Verify its closeness to the midpoint;
    # do not assume SuperLU is a Cholesky routine or that U equals D L^T.
    L=lu.L.tocsc(); LD=L@sparse.diags(diagonal)
    counts=np.diff(L.tocsc().indptr)
    work=sum(int(x)*int(x) for x in counts)
    if work>limits.max_product_work:
        raise SparsePreparationFailure('switch_uniqueness_product','LDLT product work budget exceeded')
    permuted=center[np.argsort(lu.perm_r)][:,np.argsort(lu.perm_c)]
    difference=permuted-LD@L.T
    error=_up(_norm_upper(difference,1)+_gamma(n+3)*(
        _norm_upper(LD,1)*_norm_upper(L.T,1)+_norm_upper(center,1)))
    li=_comparison_inverse_inf(L,True,started,limits)
    l1=_comparison_inverse_inf(L.T,False,started,limits)
    base=np.nextafter(float(np.min(diagonal))/_up(li*l1),0.)
    mu=np.nextafter(base-error-radius_norm,-np.inf)
    _check_time(started,limits,'switch_uniqueness_bound')
    return float(mu),lipschitz,dict(uniqueness_factorizations=1,
        midpoint_min_eigenvalue_lower=float(base-error),interval_radius_norm_upper=radius_norm,
        ldlt_residual_norm_upper=error,uniqueness_factor_nnz=lu.L.nnz+lu.U.nnz,
        uniqueness_product_work=work)


@dataclass(frozen=True)
class DirectionalSolution:
    variation: Variation
    fields: object
    record: dict


class DirectionalSolver:
    """Budgeted sparse semismooth Newton with a global sufficient VI test.

    Positive row/column scales define the equivalent scaled product-cone VI.
    If the all-selection strong-monotonicity bound is inconclusive, STOP before
    Newton. It is not evidence of nonuniqueness. No smoothing or branch-only
    uniqueness inference is used. Semismooth Newton may fail within its finite
    budget despite a unique solution; failure never commits a history tangent.
    """
    def __init__(self,problem,*,row_scale,column_scale,uniqueness_weights,limits,
                 minimum_monotonicity,minimum_reciprocal_bound,
                 uniqueness_method="sparse_ldlt_interval"):
        if not isinstance(problem,DirectionalTransitionProblem) or not isinstance(limits,SwitchLimits):
            raise TypeError('explicit directional problem and resource limits required')
        self.problem,self.limits=problem,limits
        self.nodes=_indices(np.flatnonzero(problem.interior|problem.weak_lower|problem.weak_upper),problem.r.n,"directional damage DOFs")
        self.size=len(problem.free_u)+len(self.nodes)
        self.rows=frozen_array(_array(row_scale,(self.size,),'row scales'))
        self.cols=frozen_array(_array(column_scale,(self.size,),'column scales'))
        self.weights=frozen_array(_array(uniqueness_weights,(self.size,),'uniqueness weights'))
        if any(np.any(x<=0) for x in (self.rows,self.cols,self.weights)):
            raise ValueError('positive fixed scaling and comparison weights required')
        thresholds=[minimum_monotonicity,minimum_reciprocal_bound]
        if not np.isfinite(thresholds).all() or min(thresholds)<=0 or minimum_reciprocal_bound>1:
            raise ValueError('positive prospective uniqueness thresholds required')
        if uniqueness_method not in ("sparse_ldlt_interval","weighted_gershgorin"):
            raise ValueError("unknown uniqueness bound method")
        self.uniqueness_method=uniqueness_method
        self.thresholds=tuple(thresholds)
        self.identity=_fingerprint(problem)
        self.binding_id=self._binding()

    def _binding(self):
        h=hashlib.sha256(self.identity.encode())
        for a in (self.nodes,self.rows,self.cols,self.weights):
            h.update(np.ascontiguousarray(a).tobytes())
        h.update(json.dumps(dict(thresholds=self.thresholds,method=self.uniqueness_method,
            limits=dict(sparse=vars(self.limits.sparse),max_iterations=self.limits.max_iterations,
                        max_backtracks=self.limits.max_backtracks,armijo=self.limits.armijo)),sort_keys=True).encode())
        return h.hexdigest()

    def _assert_identity(self):
        if _fingerprint(self.problem)!=self.identity or self._binding()!=self.binding_id:
            raise ValueError('directional problem or solver configuration changed after binding')

    def _variation(self,x,old,bc,parameters):
        p=self.problem; z=p.r.zero_variation(); nu=len(p.free_u)
        z.displacement[p.bc]=bc; z.displacement[p.free_u]=x[:nu]*self.cols[:nu]
        z.damage[p.strong_lower]=old.damage[p.strong_lower]
        z.damage[self.nodes]=x[nu:]*self.cols[nu:]
        out=p.r.directional(p.u,p.d,z.displacement,z.damage,old_variation=old,
                            parameters=parameters,strict=False,margins=p.margins)
        return Variation(z.displacement,z.damage,out.accumulated,out.driver),out

    def _natural(self,x,old,bc,parameters,jacobian,started):
        p=self.problem; nu=len(p.free_u)
        v,out=self._variation(x,old,bc,parameters)
        g=np.r_[out.force[p.free_u],out.damage_residual[self.nodes]]/self.rows
        value=g.copy(); take=np.zeros(self.size,dtype=bool)
        wl=p.weak_lower[self.nodes]; wu=p.weak_upper[self.nodes]
        lower=(v.damage[self.nodes]-old.damage[self.nodes])/self.cols[nu:]
        upper=v.damage[self.nodes]/self.cols[nu:]
        take[nu:]=(wl&(lower<=g[nu:]))|(wu&(upper>=g[nu:]))
        value[nu:]=np.where(wl,np.minimum(lower,g[nu:]),np.where(wu,np.maximum(upper,g[nu:]),g[nu:]))
        matrix=None
        if jacobian:
            matrix=_assemble(p,self.nodes,self.limits.sparse,started,variation=v,old=old,parameters=parameters)[0]
            matrix=(sparse.diags(1/self.rows)@matrix@sparse.diags(self.cols)).tolil()
            for i in np.flatnonzero(take):
                matrix.rows[i]=[i]; matrix.data[i]=[1.]
            matrix=matrix.tocsc()
        return value,matrix,v,out

    def solve(self,old_variation,*,parameters,boundary_variation=None,
              residual_tolerance,solution_tolerance):
        self._assert_identity(); started=monotonic(); p=self.problem
        tol=[residual_tolerance,solution_tolerance]
        if not np.isfinite(tol).all() or min(tol)<=0:
            raise ValueError('positive directional residual and solution-error tolerances required')
        old=freeze_variation(old_variation,p.r.n,p.r.e)
        parameters=tuple(_array(parameters,(3,),'material direction'))
        bc=np.zeros(len(p.bc)) if boundary_variation is None else _array(boundary_variation,(len(p.bc),),'boundary direction').copy()
        if np.any(old.damage[p.fixed]!=0):
            raise ValueError('fixed crack initial tangent must remain zero')
        lo,hi=_assemble(p,self.nodes,self.limits.sparse,started)
        lo=sparse.diags(1/self.rows)@lo@sparse.diags(self.cols)
        hi=sparse.diags(1/self.rows)@hi@sparse.diags(self.cols)
        if self.uniqueness_method=="sparse_ldlt_interval":
            mu,L,unique_stats=_ldlt_monotonicity_bounds(lo,hi,self.limits.sparse,started)
        else:
            mu,L=_monotonicity_bounds(lo,hi,self.weights)
            unique_stats=dict(uniqueness_factorizations=0)
        if not np.isfinite([mu,L]).all() or mu<self.thresholds[0] or (self.size and (L<=0 or mu/L<self.thresholds[1])):
            raise SparsePreparationFailure('switch_uniqueness','all-selection strong-monotonicity bound inconclusive',{'mu_lower':mu,'lipschitz_upper':L})
        x=np.zeros(self.size); nu=len(p.free_u)
        x[nu:]=np.where(p.weak_lower[self.nodes],old.damage[self.nodes]/self.cols[nu:],0.)
        factors=0; backs=0
        for iteration in range(self.limits.max_iterations+1):
            _check_time(started,self.limits.sparse,'switch_iteration')
            value,_,v,out=self._natural(x,old,bc,parameters,False,started)
            norm=float(np.max(abs(value),initial=0))
            error_bound=float((1+(L+1)/mu)*np.linalg.norm(value))
            if norm<=residual_tolerance and error_bound<=solution_tolerance:
                check,_=p.check(v,old,parameters=parameters,boundary_variation=bc,tolerance=residual_tolerance)
                if not check.satisfies_directional_equations:
                    raise SparsePreparationFailure('switch_audit','independent full directional equations failed')
                self._assert_identity()
                return DirectionalSolution(freeze_variation(v,p.r.n,p.r.e),out,dict(
                    problem_id=self.identity,solver_binding_id=self.binding_id,method='sparse_semismooth_newton_product_cone_VI',
                    derivative_unique=True,uniqueness_method='all_selection_strong_monotonicity_'+self.uniqueness_method,
                    uniqueness_statistics=unique_stats,
                    mu_lower=mu,lipschitz_upper=L,natural_residual_inf=norm,
                    scaled_solution_error_upper=error_bound,full_equation_inf=check.equation_inf,
                    residual_tolerance=residual_tolerance,solution_tolerance=solution_tolerance,
                    parameters=parameters,iterations=iteration,factorizations=factors,backtracks=backs,
                    elapsed_seconds=monotonic()-started,unknowns=self.size,
                    arithmetic='padded float64 numerical evidence; not interval proof',
                    native_execution_verified=False,primal_steps=0))
            if iteration==self.limits.max_iterations:
                break
            value,J,_,_=self._natural(x,old,bc,parameters,True,started)
            if J.nnz>self.limits.sparse.max_matrix_nnz:
                raise SparsePreparationFailure('switch_newton','matrix nnz budget exceeded')
            try:
                factor=splu(J); factors+=1
            except (ValueError,RuntimeError) as exc:
                raise SparsePreparationFailure('switch_newton','selected linearization factorization failed') from exc
            _check_time(started,self.limits.sparse,'switch_factorization')
            if factor.L.nnz+factor.U.nnz>self.limits.sparse.max_factor_nnz:
                raise SparsePreparationFailure('switch_factorization','factor fill budget exceeded')
            dx=factor.solve(-value)
            if not np.isfinite(dx).all() or np.max(abs(J@dx+value),initial=0)>residual_tolerance*max(1.,norm):
                raise SparsePreparationFailure('switch_newton','Newton linear residual failed')
            merit=float(value@value); accepted=False
            for back in range(self.limits.max_backtracks):
                _check_time(started,self.limits.sparse,'switch_line_search')
                alpha=2.**(-back)
                trial=self._natural(x+alpha*dx,old,bc,parameters,False,started)[0]
                if trial@trial <= (1-self.limits.armijo*alpha)*merit:
                    x=x+alpha*dx; backs+=back; accepted=True; break
            if not accepted:
                raise SparsePreparationFailure('switch_line_search','no sufficient decrease within budget')
        raise SparsePreparationFailure('switch_iteration','iteration budget exhausted')
