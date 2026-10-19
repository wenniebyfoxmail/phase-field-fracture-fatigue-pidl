from collections import OrderedDict
import pytest
import torch
from s09_e013_local_ranking_objective import (
    ARM_GLOBAL, ARM_LOCAL, OBJECTIVE_ORDER, PAIR_ORDER, local_support_score,
    pair_schedule, ranking_loss, merge_ranking_gradients, classify_e013,
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
