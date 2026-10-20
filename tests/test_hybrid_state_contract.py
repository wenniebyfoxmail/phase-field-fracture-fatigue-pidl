"""Artificial failure injection; no project arrays, producer, or optimizer."""
from copy import deepcopy
from dataclasses import replace
import json

import numpy as np
import pytest

from hybrid_incremental import solve_step
from hybrid_state_contract import (CONTRACT_ID, FEATURE_TIMING, bind_proposal, step_context,
    verify_comparable, verify_expected, verify_transition, FIELD_CONTRACT)
from hybrid_transaction import StateStore
from audit_hybrid_labels import qualify_transition
from test_hybrid_incremental import AlgebraicBackend, state, settings
from test_hybrid_producer import card


def context_inputs(phase='test_reference'):
    c=card();s=next(x for x in c['phases'] if x['id']==phase)
    from dataclasses import asdict
    c['state0_id']=state().fingerprint();c['solver']=asdict(settings())
    return c,s,np.array([0]),np.array([0.])


def bound(phase='test_reference'):
    c,s,dofs,bc=context_inputs(phase);old=state()
    p=solve_step(AlgebraicBackend(),old,dofs,bc,next_load_id='next',settings=settings())
    return old,bind_proposal(p,step_context(c,s,p.state,1,dofs,bc)),step_context(c,s,old,0,dofs,bc)


def test_atomic_evidence_roundtrip_preserves_numeric_fingerprint(tmp_path):
    old,p,initial=bound();store=StateStore(tmp_path/'state.npz')
    store.initialize(old,context=initial);a,am=store.load()
    expected=p.state.fingerprint();store.commit(p);b,bm=store.load()
    assert b.fingerprint()==expected
    verify_transition(a,am,b,bm)
    with np.load(store.path,allow_pickle=False) as z:
        assert np.array_equal(z['evidence_f_solve_gp'],p.field_evidence['f_solve_gp'])
        assert np.array_equal(z['evidence_psi_raw_commit_gp'],p.field_evidence['psi_raw_commit_gp'])
    assert not p.field_evidence['f_solve_gp'].flags.writeable


@pytest.mark.parametrize('defect',['dropped_contract','wrong_parent','wrong_trajectory','changed_schedule'])
def test_commit_rejects_transition_mix_without_replacement(tmp_path,defect):
    old,p,initial=bound();store=StateStore(tmp_path/'state.npz');store.initialize(old,context=initial)
    before=store.path.read_bytes()
    if defect=='dropped_contract':p=replace(p,accepted_contract=None)
    else:
        contract=deepcopy(p.accepted_contract)
        if defect=='wrong_parent':contract['parent_id']='wrong'
        elif defect=='wrong_trajectory':contract['context']['trajectory_id']='other'
        else:contract['context']['physical']['schedule_id']='other'
        p=replace(p,accepted_contract=contract)
    with pytest.raises(RuntimeError):store.commit(p)
    assert store.path.read_bytes()==before


def test_legacy_readable_but_cannot_supply_new_labels(tmp_path):
    old,p,initial=bound();store=StateStore(tmp_path/'legacy.npz');store.initialize(old)
    a,am=store.load();assert a.fingerprint()==old.fingerprint()
    with pytest.raises(RuntimeError,match='legacy'):store.commit(p)
    row=dict(domain='nodal-K-v1',load_index_in=0,load_index_out=1)
    result=qualify_transition(row,physics_id='physics',mesh_id='mesh',settings_id='settings')
    assert 'state_contract_id' in result['missing_or_mismatched']
    assert 'feature_timing' in result['missing_or_mismatched']


def test_corrupted_saved_field_evidence_is_rejected(tmp_path):
    old,p,initial=bound();store=StateStore(tmp_path/'state.npz')
    store.initialize(old,context=initial);store.commit(p)
    with np.load(store.path,allow_pickle=False) as z:payload={k:z[k].copy() for k in z.files}
    payload['evidence_psi_raw_commit_gp'][0,0]+=1
    np.savez(store.path,**payload)
    with pytest.raises(RuntimeError,match='digest'):store.load()


def test_f_solve_not_reconstructed_from_committed_factor():
    old,p,_=bound()
    # A synthetic accepted residual within the original 1e-8 bound. Distinct
    # f_solve must survive binding; no claim about a real fatigue trajectory.
    e={k:v.copy() for k,v in p.field_evidence.items()};e['f_solve_gp']-=5e-9
    p=replace(p,field_evidence=e,certificate=dict(p.certificate,fatigue_residual=float(np.max(abs(e['f_solve_gp']-p.state.fatigue)))))
    q=bind_proposal(p,p.accepted_contract['context'])
    assert not np.array_equal(q.field_evidence['f_solve_gp'],q.state.fatigue)
    bad=replace(p,certificate=dict(p.certificate,fatigue_residual=0.))
    with pytest.raises(RuntimeError,match='residual'):bind_proposal(bad,p.accepted_contract['context'])


@pytest.mark.parametrize('key,value',[('cycle',2),('substep',2),('prescribed_load',.123),('branch','unloaded')])
def test_scoring_refuses_same_step_different_physical_state(key,value):
    a,p,_=bound();_,q,_=bound('test_hybrid')
    # Test comparison validation independently of the storage check.
    am=dict(state_contract=p.accepted_contract,certificate=dict(p.certificate,mechanics={'reaction_dofs':[0]}))
    bm=dict(state_contract=deepcopy(q.accepted_contract),certificate=dict(q.certificate,mechanics={'reaction_dofs':[0]}))
    verify_comparable(p.state,am,q.state,bm)
    bm['state_contract']['context']['physical'][key]=value
    with pytest.raises(RuntimeError,match='different physical'):verify_comparable(p.state,am,q.state,bm)


def test_expected_context_and_reaction_order_are_enforced():
    _,p,_=bound();_,q,_=bound('test_hybrid')
    am=dict(state_contract=p.accepted_contract,certificate={'mechanics':{'reaction_dofs':[0,1]}})
    bm=dict(state_contract=q.accepted_contract,certificate={'mechanics':{'reaction_dofs':[1,0]}})
    with pytest.raises(RuntimeError,match='reaction'):verify_comparable(p.state,am,q.state,bm)
    c,s,dofs,bc=context_inputs();wrong=step_context(c,s,p.state,2,dofs,bc)
    with pytest.raises(RuntimeError,match='physical'):verify_expected(p.state,am,wrong)


def test_card_cannot_silently_use_old_timing_and_features():
    from run_hybrid_producer import validate_card
    c=card();validate_card(c);del c['state_contract_id']
    with pytest.raises(ValueError,match='field timing'):validate_card(c)
    assert FIELD_CONTRACT['fields']['NN_output'][1].endswith('never accepted damage or teacher')
    assert FEATURE_TIMING.startswith('old_accepted') and len(CONTRACT_ID)==64


@pytest.mark.parametrize('key',['initial_state_id','inputs_sha256','settings_id','coupling_policy_id'])
def test_comparison_cannot_mix_initial_history_or_solver_policy(key):
    _,p,_=bound();_,q,_=bound('test_hybrid')
    am=dict(state_contract=p.accepted_contract,certificate={'mechanics':{'reaction_dofs':[0]}})
    bm=dict(state_contract=deepcopy(q.accepted_contract),certificate={'mechanics':{'reaction_dofs':[0]}})
    bm['state_contract']['context']['physical'][key]='different'
    with pytest.raises(RuntimeError,match='different physical'):verify_comparable(p.state,am,q.state,bm)


def test_matching_but_wrong_reaction_support_is_not_enough():
    _,p,_=bound();am=dict(state_contract=p.accepted_contract,certificate={'mechanics':{'reaction_dofs':[1]}})
    c,s,dofs,bc=context_inputs()
    with pytest.raises(RuntimeError,match='prescribed boundary'):
        verify_expected(p.state,am,step_context(c,s,p.state,1,dofs,bc))


@pytest.mark.parametrize('launcher_name',['launch_hybrid_detached','launch_hybrid_budgeted'])
@pytest.mark.parametrize('enabled',[False,True])
def test_disabled_or_unreconciled_card_never_reserves_or_spawns(tmp_path,monkeypatch,launcher_name,enabled):
    import importlib
    import sys
    launcher=importlib.import_module(launcher_name)
    c=card();c.update(execution_enabled=enabled,run_root=str(tmp_path),archive_root=str(tmp_path/'archive'))
    path=tmp_path/'card.json';path.write_text(json.dumps(c))
    monkeypatch.setattr(launcher.platform,'system',lambda:'Linux')
    monkeypatch.setattr(launcher.subprocess,'Popen',lambda *a,**k:pytest.fail('must not spawn'))
    monkeypatch.setattr(sys,'argv',['launch','--card',str(path),'--package',str(tmp_path/'absent'),
                                  '--review',str(tmp_path/'absent'),'--inputs',str(tmp_path)])
    with pytest.raises(RuntimeError,match='preparation|reconciled'):launcher.main()
    assert not (tmp_path/'launch_reservation.json').exists()


@pytest.mark.parametrize('defect',['none','x_future_damage','d_old','d_target','u_pred','psi_pred'])
def test_training_feature_timing_and_target_arrays_are_checked(defect):
    import hashlib
    from hybrid_incremental import NativeQ4Backend
    from hybrid_network import features_for, FEATURES
    from hybrid_producer_worker import verify_label_feature_arrays
    from test_hybrid_incremental import one_element
    backend=NativeQ4Backend(one_element(),np.zeros(4,bool))
    old=replace(state(),mesh_id=backend.mesh_id,physics_id=backend.physics_id)
    new=replace(old,damage=np.full(4,.4))
    dofs=np.array([0]);values=np.array([0.]);up=np.zeros(8);pp=np.zeros((1,4))
    z=dict(x=features_for(backend,old,up,pp,dofs,values).astype(np.float32),
           d_old=old.damage.astype(np.float32),d_target=new.damage.astype(np.float32),u_pred=up,psi_pred=pp)
    sha=hashlib.sha256(up.tobytes()+pp.tobytes()).hexdigest()
    if defect=='x_future_damage':z['x'][:,FEATURES.index('d_old')]=.4
    elif defect!='none':z[defect].flat[0]+=.1
    if defect=='none':verify_label_feature_arrays(backend,old,new,z,dofs,values,sha)
    else:
        with pytest.raises(RuntimeError,match='timing'):verify_label_feature_arrays(backend,old,new,z,dofs,values,sha)


@pytest.mark.parametrize('defect',['none','bad_sha','unknown_run','insufficient_steps','fit_consumed','unbound_cost','reused_run'])
def test_future_execution_requires_real_hashed_settled_cost_receipt(tmp_path,defect):
    from run_hybrid_producer import require_enabled_execution
    from hybrid_inputs import sha256
    c=card();c['execution_enabled']=True;c['run_id']='artificial_fresh'
    used='pf_hybrid_complete_20261020_r2'
    receipt=dict(schema='hybrid-budget-reconciliation-v1',complete=True,active_or_unknown_runs=[],
                 settled_runs=[used],remaining_numerical_steps=3600,remaining_training_fits=1)
    if defect=='unknown_run':receipt['active_or_unknown_runs']=[used]
    elif defect=='insufficient_steps':receipt['remaining_numerical_steps']=3599
    elif defect=='fit_consumed':receipt['remaining_training_fits']=0
    elif defect=='reused_run':c['run_id']=used
    p=tmp_path/'reconciled.json';p.write_text(json.dumps(receipt));h=sha256(p)
    c['budget_reconciliation']=dict(complete=True,receipt='reconciled.json',receipt_sha256=h,active_or_unknown_runs=[])
    c['prior_costs']=[dict(source='reconciled.json',sha256=h,lineage=[used],cost_only_not_admission=True)]
    if defect=='bad_sha':c['budget_reconciliation']['receipt_sha256']='wrong'
    elif defect=='unbound_cost':c['prior_costs']=[]
    if defect=='none':require_enabled_execution(c,tmp_path)
    else:
        with pytest.raises(RuntimeError):require_enabled_execution(c,tmp_path)
