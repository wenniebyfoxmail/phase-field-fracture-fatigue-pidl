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
