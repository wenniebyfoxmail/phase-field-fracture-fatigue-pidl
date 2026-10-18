"""Pure-array and fake-engine contracts. Never enters a neural training loop."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import time
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('test_e026_run',ROOT/'scripts/pavetrack_translation_control/run.py')
run=importlib.util.module_from_spec(spec);spec.loader.exec_module(run);p=run.probe
CFG=json.loads((ROOT/'docs/research/S01/S01-E026/run_config.json').read_text())


def synthetic():
    masks=np.zeros((16,32,32),np.uint8)
    for j in range(16):masks[j,(j*2)%24:((j*2)%24)+4,3+j%8:7+j%8]=1
    rgb=np.repeat(np.repeat(masks,4,1),4,2)[:,None].repeat(3,1)*np.uint8(255)
    folds=np.array([list(range(8)),list(range(8,16)),list(range(8))],np.int64)
    src=np.arange(16,dtype=np.int64)
    packet=dict(rgb=rgb,masks=masks,fold_indices=folds,source_indices=src)
    meta=dict(fold_source_indices=[src[v].tolist() for v in folds],rows=[dict(source_index=j,image_id=f'synthetic{j}',location=str(j),rgb_sha256=hashlib.sha256(rgb[j].tobytes()).hexdigest(),mask_sha256=hashlib.sha256(masks[j].tobytes()).hexdigest()) for j in range(16)])
    return packet,meta,dict(fold_source_indices=meta['fold_source_indices'])


def test_actual_flow_is_fixed_independent_and_excludes_all_test_phases():
    a=p.flow(25100);assert a.shape==(128,8,2) and np.array_equal(a,p.flow(25100))
    assert not np.array_equal(a,p.flow(25200)) and not np.array_equal(a[:,0],a[:,1])
    held={tuple(s) for s in p.TEST_SHIFTS}
    assert all(tuple(s) not in held for s in a.reshape(-1,2))
    assert all(len({tuple(s) for s in a[:,j]})==128 for j in range(8))


def test_pool_alignment_mass_and_actual_position_prior():
    packet,_,_=synthetic();y=packet['masks'][:8];rgb=packet['rgb'][0];ss=p.flow(25100)
    for shift in [[0,0],[8,8],[31,17]]:
        pooled=p.shift_rgb(rgb,shift)[0].reshape(32,4,32,4).mean((1,3))/255
        assert np.array_equal(pooled,p.shift_mask(y[0],shift))
        assert p.shift_mask(y[0],shift).sum()==y[0].sum()
    expected=np.stack([p.shift_mask(target,s) for step in ss for target,s in zip(y,step)]).mean(0)
    assert np.array_equal(p.position_prior(y,ss),expected.astype(np.float32))


def test_shared_exclusion_includes_both_input_seams():
    for shift in p.TEST_SHIFTS:
        keep=p.shared_seam_mask(shift)
        assert keep.shape==(32,32) and keep.dtype==bool and keep.any()
        assert not keep[:4].any() and not keep[:,:4].any() and not keep[-4:].any() and not keep[:,-4:].any()
        for s in [shift,(shift+16)%32]:
            assert not keep[s[0],:].any() and not keep[:,s[1]].any()


def test_private_packet_exact_scope_and_hashes():
    a,meta,lock=synthetic();p.validate_packet(a,meta,lock)
    bad=copy.deepcopy(a);bad['rgb'][0,0,0,0]^=np.uint8(1)
    with pytest.raises(ValueError,match='array identity'):p.validate_packet(bad,meta,lock)
    bad=copy.deepcopy(a);bad['masks'][0]=0
    with pytest.raises(ValueError,match='support'):p.validate_packet(bad,meta,lock)
    bad=copy.deepcopy(a);bad['fold_indices'][0,0]=8
    with pytest.raises(ValueError,match='original control'):p.validate_packet(bad,meta,lock)


def maps_for(ys,good=True):
    maps=np.empty((3,4,8,32,32),np.float32)
    for phase,s in enumerate(p.TEST_SHIFTS):
        for j,y in enumerate(ys):
            maps[0,phase,j]=p.shift_mask(y,s) if good else 0
            maps[1,phase,j]=p.shift_mask(y,(s+16)%32) if good else 0
            maps[2,phase,j]=p.shift_mask(ys[(j+1)%8],s) if good else 0
    return maps


def test_regional_pass_and_probability_only_miss_do_not_change_threshold():
    packet,_,_=synthetic();y=packet['masks'][:8];prior=p.position_prior(y,p.flow(25100));maps=maps_for(y)
    result=p.evaluate(maps,y,prior);assert result['passed'] and result['level']=='L2'
    assert result['averages']['correct']['Brier']==0 and result['averages']['correct']['Dice']==1
    # Low but correctly placed probability may improve Brier/phase pairing; Dice still0.
    maps*=.49;result=p.evaluate(maps,y,prior)
    assert not result['passed'] and not result['components_pass']['Dice_gain']
    for phase in range(4):
        rows=[r for r in result['records'] if r['phase']==phase and r['context']==0]
        pixels={None if r['shared_seam_excluded'] is None else r['shared_seam_excluded']['pixels'] for r in rows}
        assert len(pixels)==1


class FakeEngine:
    def __init__(self,out,g,zero=False):self.out=out;self.g=g;self.zero=zero;self.predicted=False
    def fit(self,rgb,y,ss,seed):
        assert not self.predicted and len(list(self.out.glob('plan_*.npz')))==6
        assert (self.out/'plans_freeze.json').exists() and not (self.out/'models_freeze.json').exists()
        self.g.take('updates',128);self.g.take('training_rows',1024);self.g.take('models')
        return dict(verified=True,state={'fake_synthetic_only':seed},state_digest=p.digest({'fake_synthetic_only':seed}),seed=seed)
    def predict(self,model,x):
        self.predicted=True
        assert len(list(self.out.glob('model_*.json')))==6 and (self.out/'models_freeze.json').exists()
        assert self.g.counts['updates']==768
        self.g.take('prediction_rows',len(x))
        return np.zeros((len(x),32,32),np.float32) if self.zero else (x[:,0].reshape(8,32,4,32,4).mean((2,4))/255).astype(np.float32)


@pytest.mark.parametrize('zero,stable',[(False,[0,1,2]),(True,[])])
def test_all_states_frozen_before_prediction_and_scientific_levels(tmp_path,zero,stable):
    packet,meta,_=synthetic();g=run.Guard(CFG,tmp_path,memory=lambda:100,start=time.monotonic())
    result=run.execute(packet,meta,CFG,tmp_path,g,FakeEngine(tmp_path,g,zero))
    assert result['stable_folds']==stable and result['OOF'] is None and result['retention'] is None and result['net_GT'] is None
    assert g.counts==dict(models=6,updates=768,training_rows=6144,prediction_rows=576)
    assert len(list(tmp_path.glob('maps_*.npy')))==6


@pytest.mark.parametrize('counter',['models','updates','training_rows','prediction_rows'])
def test_counter_cap_fails_closed(tmp_path,counter):
    g=run.Guard(CFG,tmp_path,memory=lambda:100,start=time.monotonic())
    with pytest.raises(RuntimeError):g.take(counter,CFG['budget'][counter]+1)


def test_resource_time_output_and_producer_caps(tmp_path):
    g=run.Guard(CFG,tmp_path,memory=lambda:4*1024**3+1,start=time.monotonic())
    with pytest.raises(MemoryError):g.check()
    g=run.Guard(CFG,tmp_path,memory=lambda:1,start=time.monotonic()-601)
    with pytest.raises(TimeoutError):g.check()
    g=run.Guard(CFG,tmp_path,memory=lambda:1,start=time.monotonic());g.gpu=lambda:(1,4*1024**3+1)
    with pytest.raises(MemoryError):g.check()
    with (tmp_path/'sparse').open('wb') as f:f.truncate(100*1024**2+1)
    g=run.Guard(CFG,tmp_path,memory=lambda:1,start=time.monotonic())
    with pytest.raises(RuntimeError,match='output'):g.check()
    with pytest.raises(PermissionError):run.runtime.production_environment(CFG)


def test_config_and_range_tampering_rejected():
    run.validate_config(CFG);bad=copy.deepcopy(CFG);bad['test_shifts'][0]=[1,1]
    with pytest.raises(ValueError):run.validate_config(bad)
    with pytest.raises(ValueError):p.component(np.ones((32,32))*1.01,np.ones((32,32)))
