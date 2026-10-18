"""Small span/AD/control fixtures, not a physical run or full-network training."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest
import torch

PATH=Path(__file__).resolve().parents[1]/'tools/s04_e011_analysis/run_pidl_hidden_newton.py'
SPEC=importlib.util.spec_from_file_location('hidden_newton_toy',PATH);m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)


def test_reconditioning_keeps_all_original_raw_directions_and_current_head():
    rng=np.random.default_rng(7);features=rng.normal(size=(23,4));q,_=np.linalg.qr(rng.normal(size=(5,3)))
    old=q/np.array([.2,.7,1.5]);span,err=m.fixed_raw_span(old)
    assert err<1e-14
    mass=np.linspace(.3,1.7,23);bubble=np.linspace(.1,.4,23)
    transform,phi,info=m.whiten_fixed_span(features,mass,bubble,span)
    assert info['retained_rank']==3 and not info['further_rank_truncation'] and info['ridge']==0
    np.testing.assert_allclose((np.eye(5)-span@span.T)@transform,0,atol=1e-13)
    np.testing.assert_allclose(phi.T@(mass[:,None]*phi),np.eye(3),atol=1e-13)
    design=.11999988*bubble[:,None]*np.column_stack((features,np.ones(23)))
    head=rng.normal(size=(2,5));z=rng.normal(size=(2,3))
    np.testing.assert_allclose(design@(head+(transform@z.T).T).T,design@head.T+phi@z.T,atol=1e-13)


def test_rank_loss_raises_instead_of_silently_dropping_columns():
    span=np.eye(3)
    with pytest.raises(m.RankLoss,match='1/3'):
        m.whiten_fixed_span(np.zeros((7,2)),np.ones(7),np.ones(7),span)


class TinyNet(torch.nn.Module):
    def __init__(self):
        super().__init__();self.input_layer=torch.nn.Linear(1,1,dtype=torch.float64)
        self.output_layer=torch.nn.Linear(1,3,dtype=torch.float64)


def test_hidden_trial_interrupt_restores_completed_step_and_frozen_head(tmp_path,monkeypatch):
    net=TinyNet()
    with torch.no_grad():net.input_layer.weight.zero_()
    original=m.snapshot(net)
    class ScriptedLBFGS:
        calls=0
        def __init__(self,params,**kw):self.params=list(params)
        def zero_grad(self,set_to_none=True):
            for p in self.params:p.grad=None
        def step(self,closure):
            self.calls+=1;loss=closure()
            with torch.no_grad():self.params[0].add_(.5 if self.calls==1 else 17.)
            if self.calls>1:closure();closure() # Third trial is blocked by global reserve.
            return loss
    monkeypatch.setattr(torch.optim,'LBFGS',ScriptedLBFGS)
    budget=m.JournalBudget(tmp_path);budget.cap=5
    result=m.hidden_microblock(net,lambda:(net.input_layer.weight[0,0]-1)**2,budget,1.,1.,1,max_calls=10)
    assert result['stop']=='evaluation_budget' and len(result['accepted'])==1
    assert float(net.input_layer.weight)==.5
    for name,value in net.state_dict().items():
        if name.startswith('output_layer.'):assert torch.equal(value,original[name])
    assert len(budget.trace)==4 and result['evaluations']==4


def test_numerically_increasing_completed_hidden_step_is_hard_failure(tmp_path,monkeypatch):
    net=TinyNet()
    with torch.no_grad():net.input_layer.weight.zero_()
    class BadLBFGS:
        def __init__(self,params,**kw):self.params=list(params)
        def zero_grad(self,set_to_none=True):pass
        def step(self,closure):
            result=closure()
            with torch.no_grad():self.params[0].fill_(7.)
            return result
    monkeypatch.setattr(torch.optim,'LBFGS',BadLBFGS)
    result=m.hidden_microblock(net,lambda:(net.input_layer.weight[0,0]-1)**2,m.JournalBudget(tmp_path),1.,1.,1)
    assert result['hard_failure'] and result['stop']=='completed_hidden_step_energy_increase'
    assert float(net.input_layer.weight)==0 and not result['accepted']


def test_raw_parameter_and_nodal_gradients_share_one_unscaled_graph(tmp_path):
    torch.manual_seed(9);net=TinyNet();x=torch.tensor([[-.3],[.2],[.7]],dtype=torch.float64)
    class Field:
        def __init__(self):self.net=net
        def fieldCalculation(self,coords):
            z=self.net.output_layer(torch.tanh(self.net.input_layer(coords)))
            return z[:,0],z[:,1],torch.sigmoid(z[:,2])
    class Problem:
        def __init__(self):
            self.x=x;self.df=torch.zeros(3,dtype=torch.float64);self.uf=torch.ones(3,dtype=torch.float64)
            self.vf=self.uf*.4;self.mass=self.uf;self.fu=torch.arange(6);self.w=torch.ones((3,1),dtype=torch.float64);self.uv_denom=torch.tensor(1.,dtype=torch.float64)
        def parts(self,u,v,d):return ((u*u+2*v*v).sum(),torch.tensor(0.),torch.tensor(0.))
        def grad(self,z):return z[:,None,None]
    field=Field();problem=Problem();phi=torch.tensor([[1.,.2],[.3,.4],[.5,-.1]],dtype=torch.float64)
    span=np.eye(2);budget=m.JournalBudget(tmp_path)
    u,v,_=field.fieldCalculation(x);raw=(u*u+2*v*v).sum()
    hidden=torch.autograd.grad(raw,tuple(p for _,p in m.hidden_named(net)))
    expected_hidden=float(torch.linalg.vector_norm(torch.cat([g.reshape(-1) for g in hidden])))
    row,fields,g=m.raw_network_readout(field,problem,span,budget,'toy',dict(phi=phi))
    assert row['E_el']==pytest.approx(float(raw.detach()))
    assert row['hidden_gradient_l2']==pytest.approx(expected_hidden)
    expected=torch.cat((phi.T@(2*torch.as_tensor(fields['u'])),phi.T@(4*torch.as_tensor(fields['v']))))
    np.testing.assert_allclose(g,expected.numpy(),atol=1e-14)
    assert len(budget.trace)==1 and row['objective']=='raw_Eel'
