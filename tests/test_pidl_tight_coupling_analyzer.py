"""Synthetic metadata/array-parser tests; no model forward or mechanics solve."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/s04_e011_analysis'))
from analyze_pidl_tight_coupling_hidden_newton import (classify_checkpoint,select_last_closed,
    validate_budget,basis_folder,decision,GTOL)


def row(kind,pair,completed=False,retained=False,g=8e-11):
    return dict(checkpoint_kind=kind,pair=pair,pair_completed=completed,retained_closed_endpoint=retained,
                conditioned_head_gradient_inf=g)


def test_hidden_in_completed_pair_is_still_only_candidate():
    r=row('hidden_candidate',1,True,False);r['completed_pair_head_checkpoint']='head_1'
    assert classify_checkpoint('hidden_1',r)=='hidden_candidate_in_closed_pair'
    r['retained_closed_endpoint']=True
    with pytest.raises(ValueError,match='never'):classify_checkpoint('hidden_1',r)


def test_unclosed_head_cannot_claim_closed_endpoint():
    r=row('closed_head',1,True,True,g=GTOL*2)
    with pytest.raises(ValueError,match='CLOSED'):classify_checkpoint('head_1',r)
    assert classify_checkpoint('head_1',row('head_candidate',1))=='head_candidate_unaccepted'


def test_last_closed_ignores_later_unaccepted_candidates():
    entries=[('initial','initial_closed'),('hidden_1','hidden_candidate_in_closed_pair'),('head_1','closed_head'),
             ('hidden_2','hidden_candidate'),('head_2','head_candidate_unaccepted')]
    assert select_last_closed(entries,'head_1')=='head_1'
    with pytest.raises(ValueError,match='LAST'):select_last_closed(entries,'head_2')


def test_dynamic_basis_parser_accepts_eighth_not_ninth_pair(tmp_path):
    assert basis_folder(tmp_path,'/remote/bases/hidden_8')==tmp_path/'bases/hidden_8'
    with pytest.raises(ValueError):basis_folder(tmp_path,'/remote/bases/hidden_9')


def test_new_allocation_does_not_deduct_historical35():
    value=dict(prior_evaluations=0,new_probe_production_cap=365,total_prior_plus_new_cap=365,
        new_probe_production_deadline_seconds=600,cap=325,deadline_seconds=540,evaluations=10,
        prior_elapsed_seconds=None,cumulative_elapsed_seconds_claim=False)
    validate_budget(value,'production')
    value['prior_evaluations']=35
    with pytest.raises(ValueError,match='prior_evaluations'):validate_budget(value,'production')


def state(closure_miss):
    base=.005267089573071509
    info=dict(closed_pairs=1,all_nonzero_hidden_steps_closed=not closure_miss,
        head_closure_failure_encountered=closure_miss,operational_coupling_closure=not closure_miss,
        coupling_endpoint_eligible=True,previous_same_start_terminal_E_el=base,directional_margin=1e-10,
        actual_network=dict(conditioned_head_gradient_inf=8e-11))
    return dict(endpoint=dict(worker=info,terminal_readout_verified=True,final_head_closed=True),
        probe_stability=dict(status='verified_three_same_actual_Phi'),
        metrics=dict(preceding_baseline=dict(E_el=base),common_initial=dict(E_el=.0052684),new_last_closed=dict(E_el=base-1e-7)),
        producer_stages=[dict(nonzero_completed_hidden_step=True,pair_completed=True)]+([dict(nonzero_completed_hidden_step=True,pair_completed=False)] if closure_miss else []),
        stage_records=[dict(classification='initial_closed'),dict(classification='closed_head')],
        hidden_change=dict(actual_hidden_changed=True,verified_from_digest_and_delta=True))


def test_energy_gain_does_not_rescue_later_closure_failure():
    result=decision(state(True))
    assert result['efficacy']=='inconclusive' and result['primary_met'] is False
    assert result['preceding_energy_minus_new']>1e-10
    assert result['endpoint_eligible'] is True


def test_closed_route_with_registered_gain_supports_only_bounded_policy():
    result=decision(state(False))
    assert result['primary_met'] is True and result['efficacy']=='supports_bounded_directional_gain'


def test_failed_probe_blocks_efficacy_promotion():
    value=state(False);value['probe_stability']['status']='unadmitted_or_partial_probe'
    assert decision(value)['efficacy']=='inconclusive'
