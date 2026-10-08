import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from s09_operator import FractureOperator,decode,one_step_loss,rollout,IntegralBlock
from s09_data import build_graph,evaluate_damage,inventory,legal_origins,statistics

def tiny_graph():
    xy=np.array([[.25,.25],[.75,.25],[.25,.75],[.75,.75]])
    mesh={'centroids':xy,'areas':np.ones(4)/4,
          'connectivity':np.array([[0,1,4,3],[1,2,5,4],[3,4,7,6],[4,5,8,7]])}
    return {k:torch.from_numpy(v) for k,v in build_graph(mesh,.8,2).items()}

def test_zero_head_and_autonomous_feedback():
    g=tiny_graph();model=FractureOperator([0]*3,[1]*3,[.1]*3,width=8,rank=2)
    h=torch.ones(3,4,3)*.2;p=torch.tensor([0,.25,.5,.75,1.])
    out=rollout(model,h,g,p,3)
    assert torch.equal(out,h)
    with torch.no_grad():model.decoder[-1].bias.fill_(.1)
    out=rollout(model,h,g,p,3)
    assert torch.allclose(out[-1],h[-1]+.03)

def test_negative_raw_proposal_gets_corrective_gradient():
    g=tiny_graph();model=FractureOperator([0]*3,[1]*3,[.1]*3,width=8,rank=2)
    with torch.no_grad():model.decoder[-1].bias.fill_(-.5)
    h=torch.ones(3,4,3)*.2;target=h[-1]+.05
    loss,_=one_step_loss(model,h,target,g,torch.ones(5));loss.backward()
    assert torch.all(model.decoder[-1].bias.grad<0)

def test_bounds_and_no_rollback():
    current=torch.tensor([[.9,2.,.1],[.1,3.,1.]])
    out=decode(current,torch.tensor([[10.,-10.,-10.],[-10.,10.,3.]]),torch.ones(3))
    assert torch.all(out[:,:2]>=current[:,:2]) and out[:,0].max()<=1 and out[:,2].min()>=0

def test_integral_node_permutation_equivariance():
    g=tiny_graph();b=IntegralBlock(8,2);v=torch.randn(4,8);perm=torch.tensor([2,0,3,1]);inv=torch.argsort(perm)
    a=b(v,g['edges'],g['relative'],g['weight'])
    c=b(v[perm],inv[g['edges']],g['relative'],g['weight'])
    assert torch.allclose(a[perm],c,atol=1e-6)

def test_gate_rejects_tiny_growth_and_false_growth():
    current=np.zeros(4);ref=np.ones(4)*.1;area=np.ones(4)
    r=evaluate_damage([ref*.01],[ref],[current],area,1e-7,.1)
    assert r['verdict']=='fail'
    r=evaluate_damage([ref,np.ones(4)*.5],[ref,current],[current,current],area,1e-7,.1)
    assert r['verdict']=='fail'
    r=evaluate_damage([ref],[ref],[current],area,1e-7,.1)
    assert r['verdict']=='growth_only_pass'
    assert evaluate_damage([current],[current],[current],area,1e-7,.1)['verdict']=='not_evaluable'

def test_window_boundaries_and_no_fake_stagnation():
    assert legal_origins(6)==[2]
    raw=np.zeros((9,4,4),dtype=np.float32);raw[:,:,0]=np.arange(9)[:,None]*.01
    tr={'train':{'raw':raw},'dev':{'raw':raw}}
    inv=inventory(tr,np.ones(4),{'tau':1e-7,'train_ids':['train']})
    assert inv['p1_stagnant_available']==0
    assert all(t=='train' for t,o in inv['p1_windows'])
    assert all(2<=r['origin_index']<=5 for r in inv['windows'])

def test_statistics_ignore_development_and_f_channel():
    a=np.ones((6,128,4),dtype=np.float32)*.1;a[:,:,0]=np.arange(6)[:,None]*.01
    tr={'train':{'raw':a},'dev':{'raw':a.copy()}}
    first=statistics(tr,['train']);tr['dev']['raw']*=100
    tr['train']['raw'][:,:,2]=.99
    assert statistics(tr,['train'])==first
