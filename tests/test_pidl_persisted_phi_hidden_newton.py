"""Saved floating-point basis identity and accounting; no real-network run."""
import importlib.util
from pathlib import Path
import time
import numpy as np
import pytest
import torch

PATH=Path(__file__).resolve().parents[1]/'tools/s04_e011_analysis/run_pidl_persisted_phi_hidden_newton.py'
SPEC=importlib.util.spec_from_file_location('persisted_phi_toy',PATH);m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)


def test_initial_actual_phi_loaded_exactly_without_reconstruction_or_svd(tmp_path,monkeypatch):
    # Intentionally unrelated T/Phi catches an accidental features@T rebuild.
    phi=np.arange(3*386,dtype=np.float64).reshape(3,386)*1e-14
    transform=np.zeros((401,386),dtype=np.float64)
    p=tmp_path/'phi.npy';t=tmp_path/'transform.npy';np.save(p,phi);np.save(t,transform)
    monkeypatch.setattr(m,'conditioned_basis',lambda *a:pytest.fail('initial SVD forbidden'))
    space=m.load_actual_space(p,t,np.zeros((2,401)),'cpu',3)
    np.testing.assert_array_equal(space['phi'].numpy(),phi)
    assert space['report']['actual_saved_Phi_reused'] and space['report']['initial_SVD_calls']==0


def test_source_basis_persistence_is_byte_identical_and_shared(tmp_path):
    class Net(torch.nn.Module):
        def __init__(self):
            super().__init__();self.input_layer=torch.nn.Linear(1,2,dtype=torch.float64);self.output_layer=torch.nn.Linear(2,3,dtype=torch.float64)
    class Field:net=Net()
    phi=np.ones((2,386),dtype=np.float64);transform=np.zeros((401,386),dtype=np.float64)
    p=tmp_path/'sourcephi.npy';t=tmp_path/'sourcet.npy';np.save(p,phi);np.save(t,transform)
    space=m.load_actual_space(p,t,np.zeros((2,401)),'cpu',2)
    dest=tmp_path/'bases'/'initial';m.persist_space(space,dest,Field(),p,t)
    assert m.sha(p)==m.sha(dest/'phi.npy') and m.sha(t)==m.sha(dest/'transform.npy')
    assert space['basis_ref']==str(dest) and space['report']['phi_sha256']==m.sha(p)


def test_budget_deducts_prior_work_and_counts_preparation_time(tmp_path):
    for phase,cap,seconds in [('probe',40,60),('production',325,540)]:
        d=tmp_path/phase;d.mkdir();start=time.monotonic()-3
        b=m.phase_budget(d,phase,start)
        assert b.cap==cap and b.seconds==seconds and b.start==start
    assert 35+m.PHASE_LIMITS['probe'][0]+m.PHASE_LIMITS['production'][0]==400
    assert sum(x[1] for x in m.PHASE_LIMITS.values())==600


def test_actual_readout_vectors_persist_before_stationarity_decision(tmp_path,monkeypatch):
    (tmp_path/'readouts').mkdir()
    budget=m.phase_budget(tmp_path,'production')
    class Net(torch.nn.Module):
        def __init__(self):super().__init__();self.input_layer=torch.nn.Linear(1,1,dtype=torch.float64)
    class Field:net=Net()
    class Problem:
        device='cpu';mass=torch.ones(2,dtype=torch.float64);uf=torch.ones(2,dtype=torch.float64);vf=torch.ones(2,dtype=torch.float64)
        w=torch.ones((1,2),dtype=torch.float64);uv_denom=torch.tensor(1.,dtype=torch.float64);fu=torch.arange(4)
        def grad(self,a):return a.reshape(1,2,1).repeat(1,1,2)
    def fake_raw(field,problem,budget,label,folder):
        budget.begin(label)
        fields=dict(u=np.ones(2),v=np.ones(2),d=np.zeros(2));gu=np.array([2e-10,0.]);gv=np.zeros(2)
        np.savez(folder/(label+'.npz'),**fields,gu=gu,gv=gv,raw_head_gradient=np.zeros((2,401)))
        return fields,gu,gv,dict(label=label,E_el=.1,objective='raw_Eel')
    monkeypatch.setattr(m,'raw_network_force',fake_raw)
    field=Field()
    space=dict(phi=torch.eye(2,dtype=torch.float64),basis_ref='same-basis',
               report=dict(phi_sha256='exact',bound_hidden_sha256=m.hidden_digest(field.net.state_dict())))
    obs,fields,g=m.persisted_readout(field,Problem(),None,budget,'attempt',space)
    assert obs['reduced_gradient_inf']>m.GTOL and not obs['head_stationarity_closed']
    assert (tmp_path/'readouts'/'attempt.npz').exists()
    np.testing.assert_array_equal(np.load(tmp_path/'readouts'/'attempt_actual_projected_gradient.npy'),g)
    space['report']['bound_hidden_sha256']='different-hidden-state'
    with pytest.raises(AssertionError,match='Phi/hidden-state identity mismatch'):
        m.persisted_readout(field,Problem(),None,budget,'mismatch',space)
    assert (tmp_path/'readouts'/'mismatch.npz').exists()
    assert (tmp_path/'readouts'/'mismatch_actual_projected_gradient.npy').exists()


def test_global_budget_stops_new_basis_work_and_restores_whole_verified_state(tmp_path):
    folder=tmp_path/'phase';folder.mkdir();budget=m.phase_budget(folder,'probe');budget.trace=[{}]*39
    with pytest.raises(m.BudgetStop,match='evaluation_budget'):m.PhaseWork(budget).check()
    assert m.global_microblock_stop('evaluation_budget') and not m.global_microblock_stop('hidden_block_budget')
    class Field:
        net=torch.nn.Linear(1,2,dtype=torch.float64)
    f=Field();state=m.snapshot(f.net);basis=object()
    with torch.no_grad():f.net.weight.add_(2.)
    assert m.restore_verified(f,dict(state=state,space=basis)) is basis
    assert all(torch.equal(v,state[k]) for k,v in f.net.state_dict().items())
