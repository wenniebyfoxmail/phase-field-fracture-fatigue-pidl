"""Tiny tangent algebra, one-sided branch and budget fixtures; no real training."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest
import torch

PATH=Path(__file__).resolve().parents[1]/'tools/s04_e011_analysis/run_pidl_head_newton.py'
SPEC=importlib.util.spec_from_file_location('tiny_head_newton',PATH);m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)


def energy(z,x,y,w,g,base):
    r=x.shape[1];a=base[:,0]+x@z[:r];b=base[:,1]+y@z[r:];shear=base[:,2]+y@z[:r]+x@z[r:];tr=a+b
    raw=(a*a+b*b+.5*shear*shear-tr*tr/3)/2.6+.5/1.2*torch.relu(tr).square()
    return (w*(g*raw+.5/1.2*torch.relu(-tr).square())).sum()


def test_mixed_sign_analytic_H_matches_AD_and_FD():
    x=torch.tensor([[1.,.2],[.4,-.5],[.2,.6]],dtype=torch.float64)
    y=torch.tensor([[.2,-.3],[.7,.4],[-.2,.8]],dtype=torch.float64)
    w=torch.tensor([.7,.5,1.3],dtype=torch.float64);g=torch.tensor([.4,.8,.2],dtype=torch.float64)
    base=torch.tensor([[.3,.1,.2],[-.8,-.2,.3],[.4,.2,-.1]],dtype=torch.float64);z=torch.zeros(4,dtype=torch.float64)
    h,_=m.assemble_blocks(x,y,w,g,base[:,:2].sum(1),chunk=2)
    exact=torch.autograd.functional.hessian(lambda zz:energy(zz,x,y,w,g,base),z)
    torch.testing.assert_close(h,exact,rtol=1e-13,atol=1e-14)
    vec=torch.tensor([.2,-.3,.5,.1],dtype=torch.float64)
    def grad(q):
        q=q.clone().requires_grad_(True);return torch.autograd.grad(energy(q,x,y,w,g,base),q)[0]
    torch.testing.assert_close((grad(z+1e-6*vec)-grad(z-1e-6*vec))/(2e-6),h@vec,rtol=1e-9,atol=1e-10)


def test_zero_trace_selected_generalized_branch_is_not_both_sides():
    x=torch.tensor([[1.]],dtype=torch.float64);y=torch.tensor([[0.]],dtype=torch.float64)
    w=torch.ones(1,dtype=torch.float64);g=torch.tensor([.25],dtype=torch.float64);base=torch.zeros((1,3),dtype=torch.float64)
    h,_=m.assemble_blocks(x,y,w,g,torch.zeros(1,dtype=torch.float64))
    hp,_=m.assemble_blocks(x,y,w,g,torch.ones(1,dtype=torch.float64));hn,_=m.assemble_blocks(x,y,w,g,-torch.ones(1,dtype=torch.float64))
    torch.testing.assert_close(h,hp);assert hn[0,0]>hp[0,0]
    # One-sided second quotient, compression usesq1 and tension usesqg.
    e0=energy(torch.zeros(2,dtype=torch.float64),x,y,w,g,base)
    for sign,target in [(1,hp),(-1,hn)]:
        q=torch.tensor([sign*1e-5,0.],dtype=torch.float64)
        assert float(2*(energy(q,x,y,w,g,base)-e0)/1e-10)==pytest.approx(float(target[0,0]),rel=1e-12)


def test_dense_solve_no_ridge_and_singular_stops():
    budget=m.EvaluationBudget();work=m.Work(budget);h=torch.tensor([[2.,.1],[.1,3.]],dtype=torch.float64)
    p,r=m.linear_solve(h,np.array([.3,-.2]),work);np.testing.assert_allclose(h.numpy()@p,[-.3,.2],atol=1e-15)
    assert r['ridge']==0 and work.products==1 and work.solves==1
    with pytest.raises(m.TangentFailure,match='singular_tangent'):
        m.linear_solve(torch.zeros((2,2),dtype=torch.float64),np.ones(2),work)


def test_budget_reserves_terminal_and_deadline_not_bypassed():
    now=[0.];b=m.EvaluationBudget(cap=3,seconds=2.,clock=lambda:now[0])
    b.begin('contract');b.begin('line_trial')
    with pytest.raises(m.BudgetStop):b.begin('more_trial')
    now[0]=2.
    with pytest.raises(m.BudgetStop,match='wall_deadline'):b.begin('terminal',final=True)
    assert len(b.trace)==2


def test_Newton_budget_interrupt_keeps_completed_accepted_point():
    # Deliberately scripted scalar oracle: test control/rollback, not training.
    budget=m.EvaluationBudget();work=m.Work(budget);identity=torch.eye(2,dtype=torch.float64)
    class Tangent:
        def __init__(self):self.work=work
        def matrix(self,z):return identity,None
    class Scripted:
        calls=0
        def value_gradient(self,z):
            self.calls+=1
            if self.calls==2:raise m.BudgetStop('scripted_trial_interruption')
            return .5,np.array([.5,.5])
    initial=dict(z=np.zeros(2),value=1.,gradient=np.ones(2))
    last,accepted,report=m.newton_solve(Scripted(),Tangent(),budget,initial,identity)
    assert report['stop']=='scripted_trial_interruption' and len(accepted)==1
    np.testing.assert_array_equal(last['z'],[-1.,-1.])
    assert last['value']==.5 and budget.trace[0]['completed'] and not budget.trace[1]['completed']
