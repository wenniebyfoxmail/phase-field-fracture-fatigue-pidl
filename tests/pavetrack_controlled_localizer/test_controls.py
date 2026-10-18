import copy,importlib.util,json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
a=module('e025_test',ROOT/'scripts/pavetrack_controlled_localizer/run.py');c=a.c;sp=a.spatial;net=a.model
old=module('e025_fixtures',ROOT/'tests/pavetrack_qualified_localizer/test_localizer.py')
CFG=json.loads((ROOT/'docs/research/S01/S01-E025/run_config.json').read_text())

def fixture(tmp):
    d,t,prior=old.fixture(tmp);cfg=copy.deepcopy(CFG)
    for key in ['input_counts','budget_definitions']:cfg[key]=prior[key]
    cfg['localizer'].update(steps_per_fold=2,batch_size=2,train_rows=prior['localizer']['train_rows'],qual_rows=prior['localizer']['qual_rows'])
    cfg['localizer']['control'].update(contexts=2,steps=2,prediction_rows=12)
    b=cfg['budget'];b.update(prior['budget']);b.update(localizer_models=9,localizer_steps=18,gradient_steps=18,parameter_gradient_steps=18,localizer_training_rows=36,localizer_backward_rows=36,control_prediction_rows=12,control_models=6,control_steps=12,control_training_rows=24)
    return d,t,cfg

def guard(cfg):return a.Guard(cfg,memory=lambda:100)
def extracted(tmp):
    d,t,cfg=fixture(tmp/'images');run=tmp/'run';run.mkdir();emit,expected=old.emit_for(run);g=guard(cfg);d['rgb'],d['contexts']=sp.extract(d,run,cfg,g,c,emit);return d,t,cfg,run,emit,expected,g

class ToyBackend:
    def __init__(self,cfg,g,fail=(),control_fail=()):self.cfg=cfg;self.g=g;self.fail=fail;self.control_fail=control_fail
    def fit(self,rgb,bank,rows,k,control=None):
        by,p,support=net.training_scope(rows,bank,self.cfg,k);steps=self.cfg['localizer']['steps_per_fold'] if control is None else self.cfg['localizer']['control']['steps'];batch=self.cfg['localizer']['batch_size']
        for _ in range(steps):
            for key,n in [('localizer_steps',1),('gradient_steps',1),('parameter_gradient_steps',1),('localizer_training_rows',batch),('localizer_backward_rows',batch)]:self.g.take(key,n)
            if control is not None:self.g.take('control_steps');self.g.take('control_training_rows',batch)
        state={'synthetic_color_oracle':[k,control]}
        return dict(fold=k,control=control,control_indices=[] if control is None else net.control_indices(rows,bank,self.cfg,k),seed=25000+k if control is None else self.cfg['localizer']['control']['seeds'][control]+k,parameters=29761,verified=True,state=state,state_digest=net.digest(state),train_prevalence=p,train_support=support,synthetic=True,not_real_localisation=True)
    def predict(self,m,rgb):
        if (m['control'] is None and m['fold'] in self.fail) or (m['control'] is not None and (m['fold'],m['control']) in self.control_fail):return np.zeros((len(rgb),32,32),dtype=np.float32)
        return np.clip((rgb[:,0,2::4,2::4].astype(np.float32)-20)/180,0,1)

def pipeline(tmp,monkeypatch,fail=(),control_fail=(),real_hook=False):
    d,t,cfg=fixture(tmp/'images');run=tmp/'S01-E025-synthetic';run.mkdir();snap=run/'input_snapshot';snap.mkdir();c.write(snap/'train_polygons.json',{'rows':[r for vals in d['annotations'].values() for r in vals]});lock=dict(source_files={},source_zip_sha256='synthetic',annotation_snapshot_sha256=c.sha(snap/'train_polygons.json'),original_rows_digest=c.digest(d['originals']),source_B12_hits=len(c.baseline(c.scoped(d['originals'],d['candidates'],t,d['image_locations'],cfg['locations']))[1]))
    monkeypatch.setattr(a.inputs,'load',lambda *args:d);monkeypatch.setattr(a.legacy,'metadata',lambda *args:d['records']);monkeypatch.setattr(c,'require_producer',lambda cfg:None)
    if not real_hook:monkeypatch.setattr(a.sys,'addaudithook',lambda hook:None)
    monkeypatch.setattr(a,'backend',lambda cfg,g:ToyBackend(cfg,g,fail,control_fail));g=guard(cfg);launch={'synthetic':True};c.write(run/'launch.json',launch);args=SimpleNamespace(run=run,source=tmp/'source',metadata=tmp/'metadata');result=a.execute(args,cfg,lock,g,launch);return run,result,g,lock,cfg

def test_structure_parameters_shape_and_native_synthetic_gradient():
    import torch
    torch.set_num_threads(1);torch.manual_seed(7);m=net.network(CFG);x=torch.rand(2,3,128,128);y=torch.zeros(2,1,32,32);y[:,:,7:22,7:22]=1
    assert sum(v.numel() for v in m.parameters())==29761
    assert len([v for v in m.modules() if isinstance(v,torch.nn.Conv2d)])==11
    before=[v.detach().clone() for v in m.parameters()];loss=net.probability_loss(m(x),y);assert m(x).shape==(2,1,32,32);loss.backward();assert all(v.grad is not None and torch.isfinite(v.grad).all() for v in m.parameters());opt=torch.optim.AdamW(m.parameters(),lr=.001);opt.step();assert any(not torch.equal(v,b) for v,b in zip(m.parameters(),before))

def test_train_only_native_fit_control_and_deploy_ignore_qual_outer(tmp_path):
    d,t,cfg,run,emit,expected,g=extracted(tmp_path);bank=sp.references(d,0,run,cfg,g,c,emit);train=set(cfg['localizer']['train_locations'][0]);rgb=np.array(d['rgb']);labels=np.array(bank['values'])
    for row in d['candidates']:
        if row['location'] not in train:
            rgb[row['index']]=255
            if row['index'] in bank['lookup']:labels[bank['lookup'][row['index']]]=1-labels[bank['lookup'][row['index']]]
    for control in [None,0,1]:
        one=net.Backend(cfg,guard(cfg),production=False).fit(d['rgb'],bank,d['candidates'],0,control=control)
        engine=net.Backend(cfg,guard(cfg),production=False);two=engine.fit(rgb,dict(bank,values=labels),d['candidates'],0,control=control)
        assert one['state']==two['state'] and one['control_indices']==two['control_indices'] and one['train_prevalence']==two['train_prevalence']
        assert engine.predict(one,np.array(d['rgb'][:2])).shape==(2,32,32)
        with pytest.raises(TypeError):engine.predict(one,np.array(d['rgb'][:1]),GT=[])
        bad=copy.deepcopy(one);bad['state']['out.bias'][0]+=.01
        with pytest.raises(ValueError):engine.predict(bad,np.array(d['rgb'][:1]))


def test_control_selection_distinct_images_train_only_and_missing_support(tmp_path):
    d,t,cfg,run,emit,expected,g=extracted(tmp_path);bank=sp.references(d,0,run,cfg,g,c,emit);ids=net.control_indices(d['candidates'],bank,cfg,0);rows={v['index']:v for v in d['candidates']}
    assert len(ids)==len({rows[i]['image_id'] for i in ids})==2
    assert all(rows[i]['location'] in cfg['localizer']['train_locations'][0] for i in ids)
    cfg['localizer']['control']['contexts']=999
    with pytest.raises(net.ReferenceUnavailable):net.control_indices(d['candidates'],bank,cfg,0)


def test_bucket_alternation_and_fallback():
    buckets={'24':{'one':([10],[20])}}
    assert net.sample_batch(buckets,np.random.default_rng(1),4,0)==[10,20,10,20]
    assert net.sample_batch({'24':{'one':([],[20])}},np.random.default_rng(1),4,0)==[20]*4
    with pytest.raises(net.ReferenceUnavailable):net.sample_batch({'24':{'one':([],[])}},np.random.default_rng(1),1,0)

@pytest.mark.parametrize('fail,control_fail,admitted',[([],[],[0,1,2]),([0],[],[1,2]),([] ,[(0,1)],[1,2]),([0,1,2],[],[]),([],[(0,0),(1,0),(2,0)],[])])
def test_all_partial_none_and_either_control_veto(tmp_path,monkeypatch,fail,control_fail,admitted):
    run,result,g,lock,cfg=pipeline(tmp_path,monkeypatch,fail,control_fail);assert c.read(run/'qualification_freeze.json')['admitted_folds']==admitted
    assert g.counts['localizer_models']==9 and g.counts['gradient_steps']==18 and g.counts['control_prediction_rows']==12
    assert g.counts['model_fits']==3*len(admitted)
    if not admitted:
        assert result['primary_pass'] is None and all(v is None for v in result['comparison'].values());assert not (run/'OOF_predictions.json').exists()
    else:
        assert result['comparison']['retention']==1 and result['comparison']['net_GT']>=1
        oof=c.read(run/'OOF_predictions.json')
        assert all(oof['folds'][k]['rows']==[] and oof['folds'][k]['threshold']=='abstain' for k in range(3) if k not in admitted)
    assert result['originals_unchanged']


def test_all_nine_frozen_before_control_and_qualification_and_controls_never_deploy(tmp_path,monkeypatch):
    original=sp.infer
    def checked(engine,m,cache,ids,path,counter,cfg,g):
        assert len(list(path.parent.glob('localizer_model_fold_*.json')))==3
        assert len(list(path.parent.glob('localizer_control_fold_*.json')))==6
        assert len(c.read(path.parent/'localizer_training_freeze.json')['files'])==9
        if counter!='control_prediction_rows':assert (path.parent/'control_freeze.json').exists() and m['control'] is None
        if counter=='localizer_prediction_rows':assert (path.parent/'qualification_freeze.json').exists()
        return original(engine,m,cache,ids,path,counter,cfg,g)
    monkeypatch.setattr(sp,'infer',checked);pipeline(tmp_path,monkeypatch)


def test_control_arrays_bound_to_trusted_freeze(tmp_path,monkeypatch):
    run,result,g,lock,cfg=pipeline(tmp_path,monkeypatch);receipt=c.read(run/'output_receipt.json');expected={n:c.read(run/n) for n in receipt['files'] if n.endswith('.json') and not n.startswith('input_snapshot/')};path=run/'control_maps_fold_0_seed_0.npy';maps=np.load(path,mmap_mode='r+');maps[0,0,0]=.321;maps.flush();del maps;receipt['files'][path.name]=c.sha(path)
    with pytest.raises(ValueError):a.verify(run,expected,receipt,lock)

@pytest.mark.parametrize('field',['localizer_models','localizer_steps','control_models','control_steps','control_training_rows','control_prediction_rows'])
def test_control_and_model_caps_fail_closed(field):
    g=guard(CFG)
    with pytest.raises(RuntimeError):g.take(field,CFG['budget'][field]+1)


def test_production_denied_on_Mac_before_training():
    with pytest.raises(PermissionError):c.require_producer(CFG)
