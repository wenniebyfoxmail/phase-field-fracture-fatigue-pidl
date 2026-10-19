"""Synthetic arrays/fake frozen engine only; no real forward or neural training."""
import copy
import importlib.util
import json
from pathlib import Path
import time
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('e027_test',ROOT/'scripts/pavetrack_spatial_source/run.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r);p=r.probe
CFG=json.loads((ROOT/'docs/research/S01/S01-E027/run_config.json').read_text())


def fixture():
    y=np.zeros((12,320,480),np.uint8)
    for j in range(12):y[j,8+j*20:12+j*20,30:350]=1
    regions=np.zeros((16,32,32),np.uint8);regions[:,8:16,8:16]=1
    rgb=np.repeat(y[:,None],3,axis=1)*np.uint8(255)
    target=np.repeat(np.repeat(regions,4,1),4,2)[:,None].repeat(3,1)*np.uint8(255)
    return dict(cfd=rgb,pavetrack=target),dict(cfd=y,pavetrack=regions)


def test_official_bgr_native_preprocessing_no_normalisation_or_resize():
    x=np.zeros((3,32,64),np.uint8);x[0]=255;x[1]=128
    a=p.preprocess(x);assert a.shape==x.shape and a.dtype==np.float32 and a.flags.c_contiguous
    assert np.all(a[0]==0) and np.all(a[2]==1) and np.allclose(a[1],128/255)
    for bad in [x.astype(np.float32),x[:,:,:63],x.transpose(1,2,0)]:
        with pytest.raises(ValueError):p.preprocess(bad)


@pytest.mark.parametrize('good,count,passed',[(12,12,True),(7,7,True),(6,6,False),(0,0,False)])
def test_minimal_majority_primary_and_no_empty_background_rescue(good,count,passed):
    _,refs=fixture();maps=refs['cfd'].astype(np.float32);maps[good:]=0
    result=p.evaluate(maps,refs['cfd'],np.zeros((16,128,128),np.float32),refs['pavetrack'])
    assert result['cfd']['passed_images']==count and result['cfd']['primary_pass']==passed
    assert result['OOF'] is result['net_GT'] is result['retention'] is None and result['pavetrack']['qualification'] is None
    assert all('FP' not in row and 'Dice' not in row and 'outside_envelope_predictions' in row and 'envelope_Dice' in row for row in result['pavetrack']['rows'])


def test_leave_one_out_reference_excludes_self_and_mismatch_is_fixed_next():
    _,refs=fixture();maps=refs['cfd'].astype(np.float32);result=p.evaluate(maps,refs['cfd'],np.zeros((16,128,128),np.float32),refs['pavetrack'])
    total=refs['cfd'].sum(0,dtype=np.float64)
    for j,row in enumerate(result['cfd']['rows']):
        expected=p.component((total-refs['cfd'][j])/11,refs['cfd'][j]);assert row['baselines']['leave_one_out_position']==expected
        assert row['baselines']['fixed_identity_mismatch']==p.component(maps[(j+1)%12],refs['cfd'][j])


def test_same_mean_position_cannot_pass_and_brier_is_secondary():
    _,refs=fixture();constant=np.full((12,320,480),.01,np.float32)
    result=p.evaluate(constant,refs['cfd'],np.zeros((16,128,128),np.float32),refs['pavetrack']);assert not result['cfd']['primary_pass']
    # Fixed threshold remains.5 even when correctly placed soft values are.49.
    result=p.evaluate(refs['cfd'].astype(np.float32)*.49,refs['cfd'],np.zeros((16,128,128),np.float32),refs['pavetrack']);assert not result['cfd']['primary_pass']


class Fake:
    def __init__(self,changed=False):self.calls=0;self.changed=changed
    def predict(self,rgb):
        self.calls+=1;value=rgb[0].astype(np.float32)/255
        if self.changed and self.calls>28:value=np.clip(value+.01,0,1)
        return value
    def verify_unchanged(self):return 'synthetic-only-no-neural-model'


def test_reference_barrier_reverse_order_and56calls(tmp_path):
    rgb,refs=fixture();engine=Fake();g=r.prior.Guard(CFG,tmp_path,memory=lambda:100,start=time.monotonic())
    def labels():
        assert engine.calls==56 and (tmp_path/'prediction_freeze.json').exists();return refs
    result=r.execute(rgb,tmp_path,CFG,g,engine,labels);assert result['cfd']['primary_pass']
    freeze=json.loads((tmp_path/'prediction_freeze.json').read_text());calls=freeze['calls']
    assert [(x['source'],x['index']) for x in calls[:28]]==list(reversed([(x['source'],x['index']) for x in calls[28:]]))
    assert g.counts==dict(models=0,updates=0,training_rows=0,prediction_rows=56)
    repeat=json.loads((tmp_path/'repeatability.json').read_text());assert max(repeat['maximum_absolute_difference'].values())==0


def test_repeat_failure_stops_before_labels_or_primary(tmp_path):
    rgb,refs=fixture();engine=Fake(changed=True);g=r.prior.Guard(CFG,tmp_path,memory=lambda:100,start=time.monotonic());seen=[]
    with pytest.raises(ValueError,match='reproducibility'):r.execute(rgb,tmp_path,CFG,g,engine,lambda:seen.append(1))
    assert not seen and not (tmp_path/'result.json').exists()


def test_invalid_reference_range_shape_and_producer_denial():
    _,refs=fixture();bad=refs['cfd'].copy();bad[0,0,0]=2
    with pytest.raises(ValueError):p.evaluate(bad.astype(np.float32)/2,bad,np.zeros((16,128,128),np.float32),refs['pavetrack'])
    with pytest.raises(ValueError):p.repeat_difference(np.zeros((2,),np.float32),np.zeros((3,),np.float32))
    with pytest.raises(PermissionError):r.prior.runtime.production_environment(CFG)
    r.validate_config(CFG);badcfg=copy.deepcopy(CFG);badcfg['primary']['minimum_images']=6
    with pytest.raises(ValueError):r.validate_config(badcfg)


def test_forward_and_zero_fit_caps(tmp_path):
    g=r.prior.Guard(CFG,tmp_path,memory=lambda:100,start=time.monotonic())
    for name,n in [('models',1),('updates',1),('training_rows',1),('prediction_rows',57)]:
        with pytest.raises(RuntimeError):g.take(name,n)
