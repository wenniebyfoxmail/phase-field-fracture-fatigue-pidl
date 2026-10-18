"""Algebra and persistence fixtures only: no real network inference/training."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest
import torch

PATH=Path(__file__).resolve().parents[1]/'tools/s04_e011_analysis/run_pidl_head_readout_audit.py'
SPEC=importlib.util.spec_from_file_location('head_audit_toy',PATH);m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)


def test_stationarity_above_threshold_is_label_not_stop():
    row=m.projected_label(np.array([2e-10,-3e-12]))
    assert row['gradient_inf']==2e-10 and not row['below_or_equal_threshold']
    assert row['threshold_is_readout_label_only']
    assert m.projected_label(np.array([m.GTOL,0.]))['below_or_equal_threshold']


def test_cpu_add_at_mass_with_shared_nodes_is_reproducible():
    c=np.array([[0,1,2,3],[1,4,5,2]]);contrib=np.arange(8,dtype=float).reshape(2,4)/7
    expected=np.zeros(6)
    for row,vals in zip(c,contrib):
        for node,value in zip(row,vals):expected[node]+=value
    np.testing.assert_array_equal(m.cpu_mass(c,contrib,6),expected)
    np.testing.assert_array_equal(m.cpu_mass(c,contrib,6),m.cpu_mass(c,contrib,6))


def test_saved_attempt_survives_nonfinite_stop(tmp_path):
    f=dict(u=np.array([0.,1.]),v=np.zeros(2),d=np.ones(2))
    with pytest.raises(AssertionError,match='attempt arrays were preserved'):
        m.save_force(tmp_path,'attempt',f,np.array([np.nan,0.]),np.zeros(2),dict(E_el=1.))
    assert (tmp_path/'attempt.npz').exists() and (tmp_path/'attempt.json').exists()
    assert m.observation_json(dict(gradient_inf=float('nan'),finite=False))==dict(gradient_inf=None,finite=False)


def test_raw_head_gradient_saved_without_new_gradient_computation(tmp_path):
    f=dict(u=np.zeros(2),v=np.zeros(2),d=np.ones(2));head=np.arange(8,dtype=float).reshape(2,4)
    m.save_force(tmp_path,'raw',f,np.ones(2),np.zeros(2),dict(E_el=1.),extra={'raw_head_gradient':head})
    with np.load(tmp_path/'raw.npz') as z:np.testing.assert_array_equal(z['raw_head_gradient'],head)


def test_state_identity_and_basis_projection_are_separate(tmp_path):
    state={'weight':torch.tensor([[1.,2.]],dtype=torch.float64)};clone={k:v.clone() for k,v in state.items()}
    assert m.state_digest(state)==m.state_digest(clone)
    clone['weight'][0,0]+=1;assert m.state_digest(state)!=m.state_digest(clone)
    phi=np.array([[1.,2.],[2.,-1.],[0.,1.]]);force=np.array([1.,0.,-2.])
    g=phi.T@force
    np.testing.assert_array_equal(np.stack([phi.T@force for _ in range(5)]),np.tile(g,(5,1)))
