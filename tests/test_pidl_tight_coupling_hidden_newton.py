"""Deterministic toy state transitions only; never real-network optimization."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest
import torch

PATH=Path(__file__).resolve().parents[1]/'tools/s04_e011_analysis/run_pidl_tight_coupling_hidden_newton.py'
SPEC=importlib.util.spec_from_file_location('tight_coupling_toy',PATH);m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)


class ToyNet(torch.nn.Module):
    def __init__(self):
        super().__init__();self.hidden=torch.nn.Parameter(torch.tensor([1.],dtype=torch.float64))
        self.output_layer=torch.nn.Linear(1,3,dtype=torch.float64)


def test_only_first_completed_step_and_counted_actual_post_energy(tmp_path,monkeypatch):
    calls=[]
    class Optimizer:
        def __init__(self,params,**kw):
            self.params=list(params);assert kw['max_iter']==1 and kw['history_size']==5 and kw['line_search_fn']=='strong_wolfe'
        def zero_grad(self,**kw):
            for p in self.params:p.grad=None
        def step(self,closure):
            calls.append('step');closure()
            with torch.no_grad():self.params[0].fill_(.5)
            return torch.tensor(999.)  # Torch's returned original loss is not the new energy.
    monkeypatch.setattr(m.torch.optim,'LBFGS',Optimizer)
    net=ToyNet();head=net.output_layer.weight.detach().clone();budget=m.base.phase_budget(tmp_path,'production')
    result=m.hidden_first_step(net,lambda:net.hidden.square().sum(),budget,1.,1.,1,40)
    assert calls==['step'] and result['completed_steps']==1 and result['evaluations']==2
    assert result['E_el']==.25 and result['stop']=='first_completed_hidden_step'
    assert budget.trace[-1]['role']=='hidden_completed_step_readout'
    assert torch.equal(head,net.output_layer.weight) and result['accepted'][0]['retained_closed_endpoint'] is False


@pytest.mark.parametrize('global_limit',[False,True])
def test_interrupted_wolfe_trial_restores_whole_initial_step(tmp_path,monkeypatch,global_limit):
    class Optimizer:
        def __init__(self,params,**kw):self.params=list(params)
        def zero_grad(self,**kw):
            for p in self.params:p.grad=None
        def step(self,closure):
            closure()
            with torch.no_grad():self.params[0].fill_(2.)
            closure()
    monkeypatch.setattr(m.torch.optim,'LBFGS',Optimizer)
    net=ToyNet();before=m.base.snapshot(net);budget=m.base.phase_budget(tmp_path,'production')
    if global_limit:budget.cap=2
    result=m.hidden_first_step(net,lambda:net.hidden.square().sum(),budget,1.,1.,1,40 if global_limit else 2)
    assert result['completed_steps']==0 and result['evaluations']==1
    assert result['stop']==('evaluation_budget' if global_limit else 'hidden_step_budget')
    assert all(torch.equal(p,before[n]) for n,p in net.state_dict().items())


def test_zero_parameter_change_stops_without_another_step(tmp_path,monkeypatch):
    class Optimizer:
        def __init__(self,params,**kw):self.params=list(params)
        def zero_grad(self,**kw):
            for p in self.params:p.grad=None
        def step(self,closure):closure()
    monkeypatch.setattr(m.torch.optim,'LBFGS',Optimizer)
    net=ToyNet();budget=m.base.phase_budget(tmp_path,'production')
    result=m.hidden_first_step(net,lambda:net.hidden.square().sum(),budget,1.,1.,1,40)
    assert result['stop']=='hidden_exact_parameter_stagnation' and result['accepted'][0]['hidden_parameter_delta_inf']==0


def test_original_actual_head_and_realization_thresholds_remain_conjunctive():
    assert m.head_contract_passed(dict(E_el=.9,reduced_gradient_inf=1e-10),1e-10,1.)
    assert not m.head_contract_passed(dict(E_el=.9,reduced_gradient_inf=1.01e-10),0.,1.)
    assert not m.head_contract_passed(dict(E_el=.9,reduced_gradient_inf=0.),1.01e-10,1.)
    assert not m.head_contract_passed(dict(E_el=1.01,reduced_gradient_inf=0.),0.,1.)


def test_candidate_checkpoint_persists_without_becoming_closed_endpoint(tmp_path):
    class Field:net=ToyNet()
    fields=dict(u=np.zeros(2),v=np.ones(2),d=np.zeros(2));path=tmp_path/'candidate'
    row=m.record_checkpoint(path,Field(),dict(E_el=1.,reduced_gradient_inf=2e-10),fields,1,'head_candidate',False)
    assert not row['pair_completed'] and not row['retained_closed_endpoint']
    assert (path/'accepted_network.pt').exists() and (path/'fields.npz').exists()


def test_new_allocation_does_not_charge_or_replenish_old_attempt():
    result=m.allocation(dict(prior_evaluations=35,total_prior_plus_new_cap=400))
    assert result['prior_evaluations']==0 and result['total_prior_plus_new_cap']==365
    c=dict(protocol=m.PROTOCOL,states=[{}],prior_evaluations=0,new_total_cap=365,total_cap=365,new_deadline_seconds=600,
        max_hidden_pairs=8,hidden_total_cap=80,hidden_step_cap=40,newton_steps_max=10,dense_assemblies_max=50,tangent_products_max=1000,
        cap=325,deadline_seconds=540)
    m.validate_contract(c,'production')
    with pytest.raises(AssertionError):m.validate_contract(c,'probe')
