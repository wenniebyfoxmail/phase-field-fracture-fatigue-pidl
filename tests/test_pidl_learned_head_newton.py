"""Tiny current-basis/frozen-state/endpoint fixtures; no actual PIDL optimization."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest
import torch

PATH=Path(__file__).resolve().parents[1]/'tools/s04_e011_analysis/run_pidl_learned_head_newton.py'
SPEC=importlib.util.spec_from_file_location('learned_head_toy',PATH);m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)


def test_current_full_design_can_retain_more_than_old_restricted_span():
    x=np.linspace(-1,1,23);features=np.column_stack((x,x*x,x*x*x))
    transform,phi,info=m.conditioned_basis(features,np.ones(len(x)),np.ones(len(x)),.12)
    assert info['original_columns']==4 and info['retained_rank']==4
    # No old restricted-span mask is supplied; every resolvable current column survives.
    np.testing.assert_allclose(phi.T@phi,np.eye(4),atol=1e-13)
    assert transform.shape==(4,4) and info['ridge']==0


class Tiny(torch.nn.Module):
    def __init__(self):
        super().__init__();self.hidden=torch.nn.Linear(2,2,dtype=torch.float64);self.output_layer=torch.nn.Linear(2,3,dtype=torch.float64)


def test_head_install_only_changes_UV_rows_and_hidden_tamper_is_detected():
    net=Tiny();before=m.snapshot(net);head=np.array([[.2,.4,.3],[-.1,.8,.7]])
    m.install_uv_head(net,head);m.assert_frozen(net,before)
    np.testing.assert_array_equal(net.output_layer.weight[:2].detach().numpy(),head[:,:-1])
    assert torch.equal(net.output_layer.weight[2],before['output_layer.weight'][2])
    with torch.no_grad():net.hidden.bias[0].add_(.1)
    with pytest.raises(AssertionError,match='hidden parameter changed'):m.assert_frozen(net,before)


def test_increasing_actual_endpoint_restores_before_without_extra_eval():
    net=Tiny();before=m.snapshot(net);m.install_uv_head(net,np.ones((2,3)))
    row=dict(E_el=1.);fields=dict(u=np.zeros(2));bad=dict(E_el=1.01)
    actual,retained,rollback,reason=m.finish_endpoint(net,before,bad,dict(u=np.ones(2)),row,fields)
    assert rollback and reason=='actual_energy_increase_rollback' and actual is row and retained is fields
    assert all(torch.equal(value,before[name]) for name,value in net.state_dict().items())


def test_hard_failure_is_distinct_from_finite_budget_candidate():
    assert m.hard_head_failure('nonpositive_or_numerically_singular_tangent_cholesky_info_2')
    assert m.hard_head_failure('Newton_direction_not_descent')
    assert not m.hard_head_failure('newton_step_budget')
    assert not m.hard_head_failure('evaluation_budget')
