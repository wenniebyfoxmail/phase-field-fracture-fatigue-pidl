"""Experimental off-domain AT1 extension and actual-value RPROP safeguarding.

No change to production PFFModel. Valid nonnegative AT1 fields have identical
energy values and the original one-sided derivative at zero. This is not a
smooth Armijo method or proof of convergence.
"""
import copy
import torch

class PositiveAT1Extension:
    def __init__(self,base):
        if base.PFF_model!='AT1':raise ValueError('AT1 only')
        self.base=base
    def __getattr__(self,name):return getattr(self.base,name)
    def damageFun(self,alpha):
        # max(alpha,0), selecting the RIGHT subgradient1 at alpha==0.
        w=torch.where(alpha>=0,alpha,torch.zeros_like(alpha))
        return w,torch.where(alpha>=0,torch.ones_like(alpha),torch.zeros_like(alpha)),8./3.

def eliminate_fully_broken(d,lower):
    if bool(((lower<0)|(lower>1)).any()):raise ValueError('Illegal accepted lower bound')
    return torch.where(lower==1,torch.ones_like(d),d)

class SearchFailure(RuntimeError):pass

def safeguarded_rprop(params,optimizer,evaluate,old_merit,check_time,max_backtracks=20):
    """Accept only finite, positive-energy, NONINCREASING actual merit.

    evaluate is a no-history-mutating fixed-(mu,rho,h,A,f) scalar callback.
    RPROP generates one proposal using the current already-computed gradients.
    Halve the parameter displacement on rejection. No smooth directional-
    derivative claim at the extension/PHR kinks. Accepted shortened proposals
    retain RPROP prev/current sign and step count, and scale step_size by tau
    (clamped to the original1e-10 lower bound). Exhaustion or deadline failure
    restores BOTH parameters and the full prior optimizer state.

    On failure, exception.context retains last finite network, final rejected
    candidate, before/after optimizer state, evaluation count and reasons.
    Callers must serialize it before stopping, not launch another solve.
    """
    before=[p.detach().clone() for p in params]
    state_before=copy.deepcopy(optimizer.state_dict())
    optimizer.step()
    delta=[p.detach()-b for p,b in zip(params,before)]
    proposed_state=copy.deepcopy(optimizer.state_dict())
    reasons=[];failed=[p.detach().clone() for p in params];evaluations=0
    try:
        for k in range(max_backtracks+1):
            check_time();tau=2.**(-k)
            with torch.no_grad():
                for p,b,dx in zip(params,before,delta):p.copy_(b+tau*dx)
                failed=[p.detach().clone() for p in params]
                try:
                    value=float(evaluate());evaluations+=1
                    if not torch.isfinite(torch.tensor(value,dtype=torch.float64)):
                        reasons.append('nonfinite_merit');continue
                    if value>float(old_merit):reasons.append('merit_increase');continue
                except (FloatingPointError,ValueError) as exc:
                    evaluations+=1;reasons.append(repr(exc));continue
            if tau<1:
                with torch.no_grad():
                    for p in params:
                        if 'step_size' in optimizer.state[p]:
                            optimizer.state[p]['step_size'].mul_(tau).clamp_(min=1e-10,max=50)
            return dict(evaluations=evaluations,backtracks=k,tau=tau,merit=value,rejections=reasons)
        raise SearchFailure('nonincreasing actual-value backtracking exhausted')
    except Exception as exc:
        with torch.no_grad():
            for p,b in zip(params,before):p.copy_(b)
        optimizer.load_state_dict(state_before)
        exc.context=dict(last_finite_parameters=before,rejected_parameters=failed,
            optimizer_before=state_before,optimizer_proposal=proposed_state,
            evaluations=evaluations,rejection_reasons=reasons)
        raise
