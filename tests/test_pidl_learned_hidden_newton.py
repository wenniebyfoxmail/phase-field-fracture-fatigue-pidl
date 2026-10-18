"""New adapter/algebra/phase caps only; no real network inference or training."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest
import torch

PATH=Path(__file__).resolve().parents[1]/'tools/s04_e011_analysis/run_pidl_learned_hidden_newton.py'
SPEC=importlib.util.spec_from_file_location('learned_hidden_toy',PATH);m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)


def test_probe_production_caps_share_total_and_reserve_terminal(tmp_path):
    p=tmp_path/'probe';p.mkdir();q=tmp_path/'production';q.mkdir()
    a=m.phase_budget(p,'probe');b=m.phase_budget(q,'production')
    assert a.cap==40 and b.cap==360 and a.cap+b.cap==400
    assert a.seconds==60 and b.seconds==540 and a.seconds+b.seconds==600
    for _ in range(39):a.begin('ordinary')
    with pytest.raises(m.BudgetStop,match='evaluation_budget'):a.begin('over_probe_cap')
    a.begin('terminal',final=True);assert len(a.trace)==40


def test_source_field_identity_checked_without_model_or_objective(tmp_path):
    fields=dict(u=np.array([.1,.2]),v=np.array([.3,.4]),d=np.array([0.,1.]))
    path=tmp_path/'source.npz';np.savez_compressed(path,**fields)
    assert max(m.verify_source_fields(fields,path).values())==0
    bad={**fields,'u':fields['u']+1e-8}
    with pytest.raises(AssertionError,match='source-field mismatch'):m.verify_source_fields(bad,path)


def test_local_hidden_budget_allows_head_but_global_budget_stops_new_work(tmp_path):
    assert not m.global_microblock_stop('hidden_block_budget')
    assert not m.global_microblock_stop('hidden_exact_parameter_stagnation')
    for stop in ['evaluation_budget','wall_deadline','dense_assembly_budget','tangent_product_budget']:
        assert m.global_microblock_stop(stop)
    folder=tmp_path/'phase';folder.mkdir();budget=m.phase_budget(folder,'probe')
    work=m.PhaseWork(budget);work.check()
    budget.trace=[{}]*39
    with pytest.raises(m.BudgetStop,match='evaluation_budget'):work.check()
    # The terminal readout alone may consume the explicit reserved call.
    budget.begin('terminal',final=True);assert len(budget.trace)==40


def test_dynamic_full_design_preserves_discarded_current_head_coefficients():
    x=np.linspace(-1,1,19);features=np.column_stack((x,2*x,x*x))
    transform,phi,info=m.conditioned_basis(features,np.ones(len(x)),np.ones(len(x)),.12)
    assert info['original_columns']==4 and info['retained_rank']==3
    head=np.array([[1.,7.,.2,.4],[-.2,5.,.3,.2]])
    z=np.array([[.2,.3,.1],[-.1,.2,.4]])
    updated=head+(transform@z.T).T
    null=np.array([-2.,1.,0.,0.]);np.testing.assert_allclose(updated@null,head@null,atol=1e-13)
    design=.12*np.column_stack((features,np.ones(len(x))))
    np.testing.assert_allclose(design@updated.T,design@head.T+phi@z.T,atol=1e-13)


def test_restore_verified_restores_hidden_and_head_exactly():
    class Field:
        def __init__(self):self.net=torch.nn.Sequential(torch.nn.Linear(1,2,dtype=torch.float64),torch.nn.Linear(2,2,dtype=torch.float64))
    f=Field();before=m.snapshot(f.net);space=object()
    with torch.no_grad():
        for p in f.net.parameters():p.add_(3.)
    assert m.restore_verified(f,dict(state=before,space=space)) is space
    assert all(torch.equal(value,before[name]) for name,value in f.net.state_dict().items())


def test_actual_uv_realization_guard_is_identity_not_fem_performance():
    linear=(torch.tensor([.2,.4],dtype=torch.float64),torch.tensor([.1,.3],dtype=torch.float64))
    fields=dict(u=np.array([.2,.4]),v=np.array([.1,.3]))
    assert m.linear_realization_error(fields,linear)==0
    fields['u'][0]+=2e-10
    assert m.linear_realization_error(fields,linear)>m.UV_REALIZATION_TOLERANCE
    fields['u'][0]=.2+3e-13
    assert m.linear_realization_error(fields,linear)<m.UV_REALIZATION_TOLERANCE


def test_contract_rejects_unbudgeted_phase_and_no_gain_selection():
    c=dict(protocol=m.PROTOCOL,states=[{}],total_cap=400,total_deadline_seconds=600,max_hidden_blocks=2,
           hidden_block_cap=40,dense_assemblies_max=50,tangent_products_max=1000,cap=40,deadline_seconds=60)
    m.validate_contract(c,'probe')
    with pytest.raises(AssertionError):m.validate_contract(c,'production')
    assert m.actual_nonincrease(.01,.009)
    assert not m.actual_nonincrease(.01,.010001)
