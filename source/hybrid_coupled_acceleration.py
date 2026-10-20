"""Projected Anderson guesses for the unchanged full-space coupled map.

No accelerated vector is an accepted state. A full original u/QP/u/fresh audit
must evaluate it. Active nodes retain the latest plain-map output; inactive
nodes may be extrapolated and then projected onto the ORIGINAL accepted lower.
"""
from dataclasses import dataclass,asdict
import numpy as np


@dataclass(frozen=True)
class CouplingSettings:
    mode: str = 'none'
    depth: int = 3
    max_proposals: int = 3
    max_rejections: int = 1
    merit_factor: float = .5
    coefficient_l1_cap: float = 5.
    trust_factor: float = 2.
    ridge_relative: float = 1.e-10
    condition_cap: float = 1.e6
    mechanics_solver: str = 'direct'

    def __post_init__(self):
        if self.mode not in ('none','projected_anderson','projected_anderson_monotone'):raise ValueError('unknown coupling policy')
        if self.mechanics_solver not in ('direct','recycled_gmres'):raise ValueError('unknown mechanics solver')
        for k in ('depth','max_proposals','max_rejections'):
            if type(getattr(self,k)) is not int or not 1<=getattr(self,k)<=5:raise ValueError('unbounded coupling policy')
        vals=[self.merit_factor,self.coefficient_l1_cap,self.trust_factor,self.ridge_relative,self.condition_cap]
        if (not np.isfinite(vals).all() or not 0<self.merit_factor<1 or self.coefficient_l1_cap<1
                or not 0<self.trust_factor<=5 or not 0<self.ridge_relative<=1.e-4 or self.condition_cap<1):raise ValueError('invalid coupling safeguard')


    def trial_improves(self, trial_merit, baseline_merit):
        if not np.isfinite([trial_merit, baseline_merit]).all():
            raise RuntimeError('nonfinite trial merit')
        if self.mode == 'projected_anderson_monotone':
            return trial_merit < baseline_merit
        return trial_merit <= self.merit_factor * baseline_merit


def active_codes(d,lower,tol):
    fixed=lower==1.;lo=(d<=lower+tol)&~fixed;hi=(d>=1.-tol)&~lo&~fixed
    code=np.zeros(len(d),np.int8);code[lo]=1;code[hi]=2;code[fixed]=3
    return code


def joint_merit(damage,force,fatigue,settings):
    """<=1 iff ALL original physical scalar predicates hold; no new scale."""
    raw=[damage[k] for k in ('primal_inf','kkt_scaled_inf','projected_inf','kkt_l2')]
    raw += [force[k] for k in ('force_inf','force_l2','force_scaled','boundary_inf')]+[fatigue]
    if not np.isfinite(raw).all():raise RuntimeError('nonfinite fresh joint audit')
    v=[damage['primal_inf']/settings.bound_tolerance,
       damage['kkt_scaled_inf']/settings.damage_tolerance,damage['projected_inf']/settings.damage_tolerance,
       force['force_scaled']/settings.force_tolerance,
       force['force_l2']/(settings.force_tolerance*settings.force_scale),
       (force['force_l2']+damage['kkt_l2'])/settings.joint_residual_sum_tolerance,
       force['boundary_inf']/settings.bound_tolerance,fatigue/settings.fatigue_tolerance]
    if not np.isfinite(v).all():raise RuntimeError('nonfinite fresh joint audit')
    return float(max(v))


class ProjectedAnderson:
    def __init__(self,lower,crack,weights,tol,policy):
        self.lower=np.asarray(lower,float).copy();self.crack=np.asarray(crack,bool).copy()
        self.weights=np.asarray(weights,float).copy();self.tol=tol;self.policy=policy
        if (self.lower.ndim!=1 or self.crack.shape!=self.lower.shape or self.weights.shape!=self.lower.shape
                or not np.isfinite(self.lower).all() or not np.isfinite([tol]).all() or tol<=0
                or not np.isfinite(self.weights).all() or np.any(self.weights<=0)
                or np.any(self.lower<0) or np.any(self.lower>1) or np.any(self.lower[self.crack]!=1)):
            raise ValueError('invalid acceleration domain/weights')
        self.weights/=np.max(self.weights)
        if np.any(self.weights<=0):raise ValueError('unrepresentable acceleration weight range')
        self.history=[];self.proposals=0;self.rejections=0;self.kept_trials=0

    def norm(self,x):return float(np.sqrt(np.sum(self.weights*np.asarray(x)**2)/np.sum(self.weights)))

    def add(self,x,g):
        for a in (np.asarray(x),np.asarray(g)):
            if a.shape!=self.lower.shape or not np.isfinite(a).all() or np.any(a<self.lower) or np.any(a>1):
                raise ValueError('infeasible fixed-point history')
        self.history.append((np.asarray(x,float).copy(),np.asarray(g,float).copy(),active_codes(g,self.lower,self.tol)))
        self.history=self.history[-(self.policy.depth+1):]

    def reject(self):
        self.rejections+=1;self.history=[]

    def propose(self):
        p=self.policy
        if p.mode=='none':return None,dict(reason='disabled')
        if self.proposals>=p.max_proposals or self.rejections>=p.max_rejections:return None,dict(reason='step_budget_exhausted')
        if len(self.history)<2:return None,dict(reason='insufficient_history')
        # Do not extrapolate physical bound-active or active-changing nodes.
        free=np.logical_and.reduce([h[2]==0 for h in self.history])
        if not free.any():return None,dict(reason='no_stable_free_nodes')
        gs=[h[1] for h in self.history];fs=[h[1]-h[0] for h in self.history]
        df=np.column_stack([b-a for a,b in zip(fs[:-1],fs[1:])]);dg=np.column_stack([b-a for a,b in zip(gs[:-1],gs[1:])])
        w=np.sqrt(self.weights[free]/np.mean(self.weights[free]));a=df[free]*w[:,None];b=fs[-1][free]*w
        energy=float(np.sum(a*a))
        if not np.isfinite(energy) or energy<=np.finfo(float).tiny:return None,dict(reason='zero_secant_information')
        ridge=p.ridge_relative*energy/len(gs[:-1])
        gamma,_,rank,singular=np.linalg.lstsq(np.vstack((a,np.sqrt(ridge)*np.eye(a.shape[1]))),np.r_[b,np.zeros(a.shape[1])],rcond=None)
        condition=float(singular[0]/singular[-1]) if singular[-1]>0 else float('inf')
        if rank<a.shape[1] or not np.isfinite(condition) or condition>p.condition_cap:
            return None,dict(reason='regularized_condition_guard',rank=int(rank),condition=condition if np.isfinite(condition) else None)
        alpha=np.r_[gamma[0],np.diff(gamma),1-gamma[-1]]
        l1=float(np.sum(abs(alpha)))
        if not np.isfinite(gamma).all() or not np.isfinite(l1) or l1>p.coefficient_l1_cap:
            return None,dict(reason='coefficient_guard',coefficient_l1=l1 if np.isfinite(l1) else None)
        candidate=gs[-1].copy();candidate[free]-=(dg@gamma)[free]
        candidate=np.clip(candidate,self.lower,1.);candidate[self.crack]=1.
        correction=self.norm(candidate-gs[-1]);fp=self.norm(fs[-1])
        if not np.isfinite(candidate).all() or correction>p.trust_factor*fp:return None,dict(reason='trust_guard',correction_rms=correction,fixed_point_rms=fp)
        if np.array_equal(candidate,gs[-1]):return None,dict(reason='unchanged_projection')
        self.proposals+=1
        return candidate,dict(reason='proposed',depth=len(gs)-1,stable_free_nodes=int(free.sum()),
                              coefficient_l1=l1,correction_rms=correction,fixed_point_rms=fp,
                              regularization=ridge,regularized_rank=int(rank),regularized_condition=condition)
