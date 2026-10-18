"""Tiny algebra/one-backward fixtures; no model training or producer call."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest
import torch


PATH = Path(__file__).resolve().parents[1]/'tools/s04_e011_analysis/run_pidl_energy_head.py'
SPEC = importlib.util.spec_from_file_location('energy_head_fixture',PATH)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def test_conditioned_physical_basis_has_no_ridge_and_retains_theta0():
    x = np.linspace(-.5,.5,31)
    features = np.column_stack((x,x*x))
    mass = np.linspace(.3,1.7,len(x));bubble=(x+.5)*(.5-x)
    transform,phi,info=m.conditioned_basis(features,mass,bubble,.12)
    assert info['retained_rank']==3 and info['ridge']==0
    np.testing.assert_allclose(phi.T@(mass[:,None]*phi),np.eye(3),atol=3e-14)
    head=np.array([[.2,.3,.4],[-.3,.5,.1]])
    delta=np.array([[.1,-.2,.3],[.4,.1,-.2]])
    design=.12*bubble[:,None]*np.column_stack((features,np.ones(len(x))))
    np.testing.assert_allclose(design@(head+(transform@delta.T).T).T,
                               design@head.T+phi@delta.T,atol=1e-14)


def test_rank_deficiency_is_explicit_not_silent_regularization():
    x=np.linspace(-1,1,17)
    t,p,info=m.conditioned_basis(np.column_stack((x,2*x)),np.ones(len(x)),np.ones(len(x)),.12)
    assert info['original_columns']==3 and info['retained_rank']==2
    assert info['sensitivity_solves']==0 and t.shape==(3,2)


def test_evaluation_budget_reserves_final_and_counts_deadline():
    now=[0.]
    b=m.EvaluationBudget(cap=3,seconds=2,clock=lambda:now[0])
    b.begin('first');b.begin('trial')
    with pytest.raises(m.BudgetStop,match='evaluation_budget'):b.begin('extra_trial')
    b.begin('actual_readout',final=True)
    assert len(b.trace)==3
    d=m.EvaluationBudget(cap=3,seconds=2,clock=lambda:now[0]);now[0]=2.
    with pytest.raises(m.BudgetStop,match='wall_deadline'):d.begin('terminal',final=True)
    assert len(d.trace)==0


def test_one_backward_reduced_quadratic_gradient_is_exact():
    class Problem:
        df=torch.zeros(3,dtype=torch.float64)
        def parts(self,u,v,d):
            return ((u.square()+2*v.square()).sum(),torch.tensor(0.),torch.tensor(0.))
    phi=torch.tensor([[1.,0.],[0.,1.],[.5,-.3]],dtype=torch.float64)
    u0=torch.tensor([.1,.2,-.1],dtype=torch.float64);v0=-u0
    problem=Problem();r=m.ReducedElastic(problem,phi,u0,v0);z=np.array([.3,-.2,.1,.4])
    value,g=r.value_gradient(z)
    uv=np.column_stack((u0.numpy(),v0.numpy()))+phi.numpy()@z.reshape(2,2).T
    exact=np.r_[2*phi.numpy().T@uv[:,0],4*phi.numpy().T@uv[:,1]]
    np.testing.assert_allclose(g,exact,atol=1e-14)
    assert value==pytest.approx(float(np.sum(uv[:,0]**2+2*uv[:,1]**2)))
