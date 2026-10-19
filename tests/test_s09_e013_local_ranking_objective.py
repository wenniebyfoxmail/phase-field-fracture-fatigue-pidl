from collections import OrderedDict
from types import SimpleNamespace
import time
import numpy as np
import subprocess
import pytest
import torch
from s09_e013_local_ranking_objective import (
    ARM_GLOBAL, ARM_LOCAL, GROWTH_CYCLES, NEAR_STAGNANT_CYCLES,
    OBJECTIVE_ORDER, PAIR_ORDER, local_support_score,
    pair_schedule, ranking_loss, merge_ranking_gradients, classify_e013,
)
import s09_e013_producer as producer
from s09_e013_producer import (
    ArmRunResult, _classify_zero_step_records, _close_zero_step_audit,
    _execution_files_clean, _local_support_metrics, _reconstruct_saved_endpoint,
)
from s09_e011_ranking_objective import merge_ranking_gradients as merge_e011, ARM_RANK


def test_local_score_is_support_minus_background_positive_growth():
    pred=torch.tensor([.3,.1,.5,0.],dtype=torch.float64)
    pre=torch.tensor([.1,.2,.1,.0],dtype=torch.float64)
    target=torch.tensor([.2,.2,.2,.0],dtype=torch.float64)
    w=torch.tensor([1.,2.,3.,4.],dtype=torch.float64)
    score,record=local_support_score(pred,pre,target,w)
    assert score.item()==pytest.approx((.2+3*.4)/4 - 0.0)
    assert record['support_node_count']==2
    assert record['background_node_count']==2


def test_local_score_mask_comes_from_target_not_prediction():
    pred=torch.tensor([9.,8.,7.],dtype=torch.float64)
    pre=torch.zeros(3,dtype=torch.float64)
    target=torch.tensor([0.,1e-14,0.],dtype=torch.float64)
    w=torch.ones(3,dtype=torch.float64)
    score,record=local_support_score(pred,pre,target,w)
    assert record['support_node_count']==1
    assert score.item()==pytest.approx(8.-8.)


def test_local_score_rejects_negative_nodal_weight():
    with pytest.raises(ValueError, match="negative nodal weight"):
        local_support_score(
            torch.tensor([.2, .0]), torch.zeros(2), torch.tensor([.1, .0]),
            torch.tensor([1., -1.]),
        )


def test_schedule_and_ranking_descent_direction():
    assert len(PAIR_ORDER)==25 and len(pair_schedule())==500
    g=torch.tensor(1.,dtype=torch.float64,requires_grad=True)
    s=torch.tensor(2.,dtype=torch.float64,requires_grad=True)
    loss,_=ranking_loss(g,s)
    dg,ds=torch.autograd.grad(loss,(g,s))
    assert float((-dg)-(-ds))>0


def test_global_arm_replays_exact_e011_rank_merge():
    gradients=OrderedDict((name,torch.tensor([i+1.,-.3*(i+1),.2],dtype=torch.float64)) for i,name in enumerate(OBJECTIVE_ORDER))
    observed,_=merge_ranking_gradients(gradients,ARM_GLOBAL)
    expected,_=merge_e011(gradients,ARM_RANK)
    assert torch.equal(observed,expected)


def metric(wins,**overrides):
    out={'local_support_auc':{'wins':wins,'ties':0,'losses':25-wins,'value':wins/25},'G':1.,'F':1.,'L_P':1.,'L_judge':1.}
    out.update(overrides); return out


def test_classifier_keeps_graded_local_signal_and_protection():
    result=classify_e013(global_ranking=metric(17),local_ranking=metric(19),validity=True)
    assert result['status']=='LOCALISED_OBJECTIVE_SIGNAL'
    assert result['tier']=='ROBUST_LOCAL_OBJECTIVE_REPAIR'
    assert result['primary']['delta_pair_score']==4


def _audit_fixture(*, usable_count=8, correct_global_count=17):
    rows=[]
    expected_wrong={(g,s) for g in (58,60,69,70) for s in (3,4)}
    expected_correct=[pair for pair in PAIR_ORDER if pair not in expected_wrong]
    selected_correct=set(expected_correct[:correct_global_count])
    wrong_index=0
    for index,(growth,stagnant) in enumerate(PAIR_ORDER):
        wrong=(growth,stagnant) in expected_wrong
        local_change=1. if wrong and wrong_index < 2 else (-1. if wrong else 0.)
        rows.append({
            'growth_cycle':growth,'stagnant_cycle':stagnant,
            'initial_local_outcome':'LOSS' if wrong else 'WIN',
            'initial_global_outcome':'WIN' if (growth,stagnant) in selected_correct else 'LOSS',
            'initial_global_margin':1.,
            'local_contrast_gradient_usable':not wrong or wrong_index < usable_count,
            'arms':{
                ARM_GLOBAL:{'predicted_adamw_local_margin_change':0.,
                            'predicted_adamw_global_margin_change':0.},
                ARM_LOCAL:{'predicted_adamw_local_margin_change':local_change,
                           'predicted_adamw_global_margin_change':0.},
            },
        })
        if wrong: wrong_index+=1
    return rows


def test_zero_step_rejects_six_zero_local_gradients_even_when_two_help():
    result=_classify_zero_step_records(_audit_fixture(usable_count=2))
    assert result['usable_wrong_local_pair_count']==2
    assert result['predicted_adamw_increases_wrong_local_margin_count'][ARM_LOCAL]==2
    assert result['passed'] is False


def test_zero_step_rejects_global_protection_cohort_of_twelve():
    result=_classify_zero_step_records(
        _audit_fixture(usable_count=8,correct_global_count=12))
    assert result['usable_wrong_local_pair_count']==8
    assert result['correct_global_pair_count']==12
    assert result['passed'] is False


def test_zero_step_accepts_frozen_cohorts_with_directional_gain():
    assert _classify_zero_step_records(_audit_fixture())['passed'] is True


def test_audit_close_rejects_deadline_crossed_by_final_hash(monkeypatch):
    clock=[3599.]
    monkeypatch.setattr(producer.time,'time',lambda:clock[0])
    monkeypatch.setattr(producer,'parameter_state_sha256',lambda model:'same-model')
    def optimizer_hash(optimizer):
        clock[0]+=2.
        return 'same-optimizer'
    monkeypatch.setattr(producer,'_optimizer_state_sha256',optimizer_hash)
    with pytest.raises(TimeoutError,match='before_admission_publication'):
        _close_zero_step_audit(
            records=_audit_fixture(),runtime=SimpleNamespace(model=object()),
            optimizer=object(),before_hash='same-model',
            optimizer_hash='same-optimizer',deadline=3600.,
        )


def test_standalone_entry_drift_is_rejected(tmp_path):
    repo=tmp_path/'repo'
    entry=repo/'scripts/check_s09_e013_zero_step.py'
    entry.parent.mkdir(parents=True)
    entry.write_text('pass\n')
    def git(*args):
        return subprocess.run(
            ['git',*args],cwd=repo,check=True,capture_output=True,text=True,
        ).stdout.strip()
    git('init','-q'); git('add','.')
    git('-c','user.name=Review Fixture','-c','user.email=review@example.invalid',
        'commit','-qm','fixture')
    assert _execution_files_clean(repo)
    entry.write_text('pass\n# unreviewed entry change\n')
    assert not _execution_files_clean(repo)


def test_endpoint_local_metrics_distinguish_equal_amplitude_spatial_fields():
    cycles=np.asarray(GROWTH_CYCLES+NEAR_STAGNANT_CYCLES)
    amplitudes=np.asarray([2. if cycle in GROWTH_CYCLES else 1. for cycle in cycles])
    common={
        'cycles':cycles,'d_pre':np.zeros((len(cycles),2)),
        'target_peak':np.tile(np.asarray([1.,0.]),(len(cycles),1)),
        'nodal_weight':np.ones(2),
    }
    support={**common,'predicted_peak':np.stack([2*amplitudes,np.zeros_like(amplitudes)],axis=1)}
    background={**common,'predicted_peak':np.stack([np.zeros_like(amplitudes),2*amplitudes],axis=1)}
    support_global=np.mean(np.abs(support['predicted_peak']),axis=1)
    background_global=np.mean(np.abs(background['predicted_peak']),axis=1)
    assert np.array_equal(support_global,background_global)
    left=_local_support_metrics(support,deadline=time.time()+60,arm=ARM_GLOBAL)
    right=_local_support_metrics(background,deadline=time.time()+60,arm=ARM_LOCAL)
    assert left['auc']['wins']==25 and right['auc']['losses']==25


def test_endpoint_reconstruction_loads_checkpoint_before_collecting(monkeypatch,tmp_path):
    model=torch.nn.Linear(1,1,bias=False)
    with torch.no_grad(): model.weight.fill_(9.)
    arm_dir=tmp_path/ARM_LOCAL; arm_dir.mkdir()
    torch.save({'model':{'weight':torch.tensor([[1.]])},'optimizer':{},'update':500,
                'arm':ARM_LOCAL,'source_run':producer.RUN_ID},
               arm_dir/'checkpoint_update500.pt')
    runtime=SimpleNamespace(model=model)
    monkeypatch.setattr(producer,'_collect_fields',lambda runtime,**kwargs:{
        'observed_weight':runtime.model.weight.detach().clone().numpy()})
    result=ArmRunResult(ARM_LOCAL,arm_dir,{}, {})
    fields=_reconstruct_saved_endpoint(
        result=result,runtime=runtime,deadline=time.time()+60)
    assert fields['observed_weight'].item()==pytest.approx(1.)


def test_endpoint_local_metrics_checks_deadline_after_each_cycle(monkeypatch):
    fields={
        'cycles':np.asarray(GROWTH_CYCLES+NEAR_STAGNANT_CYCLES),
        'd_pre':np.zeros((10,2)),'target_peak':np.tile([1.,0.],(10,1)),
        'nodal_weight':np.ones(2),'predicted_peak':np.ones((10,2)),
    }
    times=iter([0.,2.])
    monkeypatch.setattr(producer.time,'time',lambda:next(times))
    with pytest.raises(TimeoutError,match='endpoint_local_metrics'):
        _local_support_metrics(fields,deadline=1.,arm=ARM_LOCAL)
