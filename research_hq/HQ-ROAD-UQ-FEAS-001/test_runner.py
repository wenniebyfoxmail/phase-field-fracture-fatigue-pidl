import json, tempfile
from pathlib import Path
import numpy as np, torch
import runner

def test_parent_and_starts():
    assert runner.parent_id("20160316_142223_361_1281") == "20160316_142223"
    assert runner.parent_id("IMG_2941_1_969") == "IMG_2941"
    assert runner.starts(100,640,96)==[0]
    assert runner.starts(1000,640,96)==[0,360]

def test_model_loss_metric():
    m=runner.UNet().eval();x=torch.zeros(1,3,32,48)
    with torch.no_grad():y,z=m(x,True)
    assert y.shape==(1,1,32,48) and z.shape==(1,256)
    loss=runner.loss_fn(y,torch.zeros_like(y));assert torch.isfinite(loss)
    q=runner.metric(np.zeros((2,2),np.float32),np.zeros((2,2),bool));assert q['dice']==1 and q['pred_empty']

def test_risk_direction_and_protocol():
    rows=[{'id':'b','error':1.,'U_LC':.2},{'id':'a','error':0.,'U_LC':.1}]
    c=runner.risk(rows,'U_LC');assert [x['id'] for x in c]==['a','b'] and c[0]['risk']==0
    assert runner.PROTOCOL['road420_access']=='PROHIBITED_IN_D1'
    assert 'road420' not in runner.main.__code__.co_varnames

if __name__=='__main__':
    test_parent_and_starts();test_model_loss_metric();test_risk_direction_and_protocol();print('3/3 passed')
