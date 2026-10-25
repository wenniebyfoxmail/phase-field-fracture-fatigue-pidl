"""Bounded active-face CG refinement of an already certified Cauchy LS point.

Uses A=diag(w) J diag(1/D) actions, never forms A.T A. Actual represented
states are re-certified/evaluated; only disjointly proven model improvements
replace best. This is a finite inexact subproblem enhancement, not a root or
subproblem-optimality certificate, and not a reproduction of PETSc GPCG.
CG gradient/Jv guards use computed vectors; only original evaluate() intervals
certify model improvement, not these search-direction dot products.
"""
import hashlib
import numpy as np
from hybrid_box_residual_subproblem import (normal,divide,multiply,dot_bound,
                                            exact_difference)
from hybrid_representable_box import state_intervals

# Each iteration reserves JT1, J1, candidate J/absJ at most4, four new
# vector scans/dots plus one possible descent restart; optional comparison retains four actions.
ITERATION_ACTION_UPPER=11
OPTIONAL_ACTION_RESERVE=4


def face_mask(x,gradient,il,iu):
    """Only outward KKT-bound components are fixed; inward gradients release."""
    return ~((il==iu)|((x<=il)&(gradient>=0))|((x>=iu)&(gradient<=0)))


def boundary_step(x,v,D,il,iu):
    """First bound intersection along scaled v, before representable recheck."""
    positive=v>0;negative=v<0;moving=positive|negative
    if not np.any(moving):return None
    target=np.where(positive,iu,il)
    h,t=exact_difference(target[moving],x[moving])
    distance=multiply(D[moving],h,'Krylov bound high')+multiply(D[moving],t,'Krylov bound tail')
    normal(distance,'Krylov bound distance')
    ratio=divide(distance,v[moving],'Krylov boundary intersection')
    if np.any(ratio<0):raise RuntimeError('negative feasible Krylov boundary distance')
    return float(ratio.min())


def refine_box_krylov(model,base,free,lower,radius,best,feasible,stage,max_steps=8,*,projected_path=False):
    if type(max_steps)is not int or not 1<=max_steps<=8:raise ValueError('unbounded Krylov refinement')
    b=model.budget;nu=len(free);x0=np.r_[base['u'][free],base['d']]
    if b.used+1+OPTIONAL_ACTION_RESERVE>b.limit:
        stage('Krylov_end',_best_point=best,iterations_completed=0,stop_reason='initial_action_reserve',
            last_projected_gradient_inf=None,subproblem_optimality_certified=False)
        best.update(krylov_status='initial_action_reserve',krylov_iterations=0,subproblem_optimality_certified=False)
        return best
    b.action('norm_scans')
    il,iu,_,_=state_intervals(x0,model.D,radius,
        np.r_[np.full(nu,-np.inf),lower],np.r_[np.full(nu,np.inf),np.ones(len(lower))])
    previous_mask=None;previous_g2=None;previous_v=None;full_step=False
    completed=0;reason='iteration_limit';last_pg=None;retry_alpha=None
    for index in range(1,max_steps+1):
        # A normal finite budget exit returns the certified best; no attempted
        # operator/evaluation may partly exceed the action/update envelope.
        if b.used+ITERATION_ACTION_UPPER+OPTIONAL_ACTION_RESERVE>b.limit:
            reason='action_reserve';break
        if b.updates>=b.update_limit-2:
            reason='update_reserve';break
        b.update();b.action('norm_scans',4)
        stage('Krylov_gradient_start',_best_point=best,iteration=index)
        gradient=model.gradient(best['residual'])
        x=np.r_[best['u'][free],best['d']];mask=face_mask(x,gradient,il,iu)
        pg=np.where(mask,gradient,0.);g2,eg2=dot_bound(pg,pg);last_pg=float(np.max(abs(pg),initial=0.))
        if g2==0:
            reason='represented_projected_gradient_zero_not_physical_root';break
        if g2-eg2<=0:
            reason='projected_gradient_norm_not_certified';break
        restart=not(full_step and previous_mask is not None and np.array_equal(mask,previous_mask))
        if restart:v=-pg
        else:
            beta=float(divide(g2,previous_g2,'Krylov recurrence ratio'))
            v=-pg+multiply(beta,previous_v,'Krylov recurrence');v[~mask]=0.
        # A conjugate direction may point outside the current tangent cone.
        # Restart with the projected steepest descent direction rather than
        # clipping its components and pretending conjugacy was preserved.
        outward=((x<=il)&(v<0))|((x>=iu)&(v>0))
        if np.any(outward):v=-pg;restart=True
        gd,egd=dot_bound(gradient,v)
        if gd+egd>=0:
            b.action('norm_scans')
            v=-pg;restart=True;gd,egd=dot_bound(gradient,v)
        if gd+egd>=0:
            reason='computed_descent_dot_unresolved';break
        Av=model.scaled_action(v);curvature,ecurvature=dot_bound(Av,Av)
        if curvature-ecurvature<=0:
            reason='computed_curvature_unresolved';break
        alpha_cg=float(divide(-gd,curvature,'Krylov quadratic step'))
        alpha_bound=boundary_step(x,v,model.D,il,iu)
        if alpha_bound is None or alpha_bound<=0:
            reason='no_positive_represented_boundary_step';break
        # First-intersection truncation can make an entire direction vanish
        # when one component is only a few representable steps from a bound.
        # On the projected path, cross those breakpoints by projecting the
        # actual state; the original model interval remains the sole authority
        # to keep a candidate. Restart CG after any projection/truncation.
        alpha=(alpha_cg if projected_path else min(alpha_cg,alpha_bound))
        if projected_path and retry_alpha is not None:alpha=min(alpha,retry_alpha)
        if not np.isfinite(alpha)or alpha<=0:raise RuntimeError('invalid Krylov step length')
        y=best['y']+multiply(alpha,v,'Krylov feasible line step');normal(y,'Krylov proposed coordinate')
        candidate=feasible('Krylov',y,_best_point=best)
        stage('Krylov_before_model',candidate,_best_point=best,iteration=index,alpha=alpha,
            alpha_cg=alpha_cg,alpha_bound=alpha_bound,restart=restart,
            projected_path=projected_path,backtracking=retry_alpha is not None,
            free_components=int(mask.sum()),free_mask_id=hashlib.sha256(mask.tobytes()).hexdigest(),
            projected_gradient_inf=last_pg)
        candidate.update(model.evaluate(candidate['p'],candidate['p_tail']))
        improved=candidate['pred_lower']>=best['pred_upper']
        if improved:
            best=candidate;best['selection']='active_face_Krylov_improvement'
        completed+=1
        stage('Krylov_complete',candidate,_best_point=best,iteration=index,retained_as_best=improved,
            boundary_truncated=alpha_bound<=alpha_cg,projected_gradient_inf=last_pg,
            projected_path=projected_path)
        if not improved:
            if not projected_path:
                reason='model_improvement_not_certified';break
            # A projected quadratic line need not decrease at the unprojected
            # line minimizer. Retry a smaller *projected gradient* step from
            # the unchanged certified best; each attempt uses one of the same
            # eight iterations and the same shared action/update budget.
            retry_alpha=alpha*.5
            full_step=False
            reason='projected_model_improvement_not_certified'
            continue
        retry_alpha=None;reason='iteration_limit'
        previous_mask=mask.copy();previous_g2=g2;previous_v=v.copy()
        full_step=alpha_cg<alpha_bound
    stage('Krylov_end',_best_point=best,iterations_completed=completed,stop_reason=reason,
        last_projected_gradient_inf=last_pg,subproblem_optimality_certified=False)
    best['krylov_status']=reason;best['krylov_iterations']=completed
    best['subproblem_optimality_certified']=False
    return best
