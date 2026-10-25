"""Fixed D21 wiring benchmark: artificial receipts only, no Mac training."""
import copy
import json
from pathlib import Path

import pytest

import hybrid_d21_pipeline as d21
from hybrid_inputs import sha256
from hybrid_producer_common import write_json
from run_hybrid_producer import validate_card, require_enabled_execution, initial_totals

ROOT = Path(__file__).resolve().parents[1]


def card():
    return json.loads((ROOT/d21.TASK/'execution_card.json').read_text())


def test_exact_d21_labels_fit_frozen_test_and_budget():
    c=card();validate_card(c);require_enabled_execution(c,ROOT)
    assert [p['role'] for p in c['phases'] if p['id'] in ('train_A','train_B','validation')] == ['labels']*3
    t=initial_totals(c,100000.,ROOT)
    assert t['wall_seconds'] >= 23338.64800595003 and t['historical_cpu_seconds'] is None
    assert t['gpu_seconds']==0 and t['start_monotonic']==100000.-c['prior_charged_host_seconds']


@pytest.mark.parametrize('mutate',[
    lambda c:c['solver'].update(wall_seconds=600),
    lambda c:c['solver'].update(force_tolerance=1e-6),
    lambda c:c['coupling'].update(subproblem_action_limit=101),
    lambda c:c['phases'][1].update(role='reference'),
    lambda c:c['phases'].reverse(),
    lambda c:c['training'].update(fits=2),
    lambda c:c['budget'].update(gpu_hours=13),
])
def test_scientific_drift_is_rejected(mutate):
    c=card();mutate(c)
    with pytest.raises(ValueError):validate_card(c)


def test_fit_reservation_cannot_be_repeated_after_unknown_outcome(tmp_path):
    d21.admit_phase(dict(id='training'),tmp_path,tmp_path)
    with pytest.raises(FileExistsError):d21.admit_phase(dict(id='training'),tmp_path,tmp_path)


def frozen(tmp_path, n=1800):
    phase=tmp_path/'training';phase.mkdir()
    (phase/'best.pt').write_bytes(b'artificial-checkpoint-never-trained')
    write_json(phase/'qualified_labels.json',dict(qualified_transitions=n))
    write_json(phase/'training_record.json',dict(test_opened=False,train_transitions=1200,validation_transitions=600))
    write_json(phase/'receipt.json',dict(completed=True,checkpoint_sha256=sha256(phase/'best.pt'),
        model_manifest=dict(training_receipt_sha256=sha256(phase/'training_record.json'))))


def test_test_phases_only_after_complete_qualification_and_freeze(tmp_path):
    with pytest.raises(FileNotFoundError):d21.admit_phase(dict(id='test_reference'),tmp_path,tmp_path)
    frozen(tmp_path,1799)
    with pytest.raises(RuntimeError,match='1800'):d21.admit_phase(dict(id='test_reference'),tmp_path,tmp_path)
    write_json(tmp_path/'training/qualified_labels.json',dict(qualified_transitions=1800))
    for name in ('test_reference','test_classical','test_hybrid'):
        d21.admit_phase(dict(id=name),tmp_path,tmp_path)
    (tmp_path/'training/best.pt').write_bytes(b'changed-after-freeze')
    with pytest.raises(RuntimeError):d21.admit_phase(dict(id='test_hybrid'),tmp_path,tmp_path)


def test_mechanical_admission_retry_is_finite_and_technical_failure_is_not_retried(tmp_path,monkeypatch):
    c=card();calls=[];waits=[]
    monkeypatch.setattr(d21,'sleep',waits.append)
    def busy():
        calls.append(1)
        if len(calls)<3:raise RuntimeError('selected GPU is occupied')
        return 'free'
    assert d21.admission_retry(busy,c,tmp_path,dict(start_monotonic=d21.perf_counter()))=='free'
    assert len(calls)==3 and waits==[30,30]
    def technical():raise RuntimeError('GPU index/UUID changed')
    with pytest.raises(RuntimeError,match='UUID'):d21.admission_retry(technical,c,tmp_path,dict(start_monotonic=d21.perf_counter()))
    assert waits==[30,30]


def test_benchmark_is_honest_and_exactly_bound(tmp_path):
    p=tmp_path/'card.json';write_json(p,card())
    receipt=dict(verdict='FIXED_BENCHMARK_PASS',artifact_id='abc',card_sha256=sha256(p),independent_review_performed=False)
    d21.require_benchmark(card(),dict(artifact_id='abc'),receipt,p)
    receipt['verdict']='REVIEW_PASS'
    with pytest.raises(RuntimeError):d21.require_benchmark(card(),dict(artifact_id='abc'),receipt,p)


def test_boundary_repair_changes_only_declared_coupling_strategy():
    c=card();c['boundary_repair']='projected_path_v1'
    c['coupling']['box_subproblem_solver']='active_face_projected_cg'
    validate_card(c)
    c['solver']['force_tolerance']=1e-6
    with pytest.raises(ValueError):validate_card(c)


def test_boundary_benchmark_must_bind_actual_saved_model_improvement(tmp_path):
    c=card();c['boundary_repair']='projected_path_v1'
    p=tmp_path/'card.json';write_json(p,c)
    report=dict(passed=True,artifact_id='abc',new_FEM_states=0,training_updates=0,
                projected=dict(pred_lower=2.),original=dict(pred_upper=1.))
    bp=tmp_path/'boundary_benchmark.json';write_json(bp,report)
    receipt=dict(verdict='FIXED_BENCHMARK_PASS',artifact_id='abc',card_sha256=sha256(p),
                 independent_review_performed=False,saved_model_benchmark_sha256=sha256(bp))
    d21.require_benchmark(c,dict(artifact_id='abc'),receipt,p)
    report['projected']['pred_lower']=.5;write_json(bp,report)
    receipt['saved_model_benchmark_sha256']=sha256(bp)
    with pytest.raises(RuntimeError,match='did not pass'):d21.require_benchmark(c,dict(artifact_id='abc'),receipt,p)
