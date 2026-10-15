import copy
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('e009_test_runner',ROOT/'scripts/pavetrack_localization_cv/run.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
CFG=r.read(ROOT/r.CONTRACT/'run_config.json')


def fixture():
    originals=[];pairs=[];records=[];targets={};locations={}
    for loc in CFG['locations']:
        for j in range(2):
            im=loc+'-'+str(j);pid=len(originals)
            box=[0,0,4,10] if j==0 else [0,0,10,10]
            old=dict(image_id=im,reid=loc,parent_id=pid,candidate_id='o:'+str(pid),kind='original',box_xyxy=box,score=.2 if j==0 else .8,E003_score=.2 if j==0 else .8,probability=.05 if j==0 else .8,proposer_confidence=.81)
            new=dict(old,candidate_id='c:'+str(pid),kind='correction',box_xyxy=[0,0,10,10] if j==0 else [20,0,30,10],original_box_xyxy=box)
            originals.append(old);pairs.extend([old,new]);records.append(dict(image_id=im,reid=loc,width=40,height=20,crack_boxes_xyxy=[[0,0,10,10]]));targets[im]=[[0,0,10,10]];locations[im]=loc
    return dict(originals=originals,pairs=pairs,records=records,targets=targets,locations=locations,probabilities=np.full(8,.81),pooled=np.zeros((8,576),dtype=np.float32))


def stationary(X,y,train,held,cfg,guard):
    # Fixed known stationary point on synthetic all-zero features; no optimizer or fit.
    mean,std=r.scale_train(X[train]);theta=np.zeros(X.shape[1]+1)
    value,grad=r.objective_gradient(theta,(X[train]-mean)/std,y[train],cfg['l2'])
    return dict(mean=mean.tolist(),std=std.tolist(),theta=theta.tolist(),train_indices=train.tolist(),held_indices=held.tolist(),positive=int(y[train].sum()),negative=int(len(train)-y[train].sum()),initial_objective=math.log(2.),final_objective=value,gradient_inf=float(abs(grad).max()),closure_objectives=[value],iterations=1,func_evals=1)


def test_feature_order_gt_independence_and_overlap_features():
    d=fixture();X=r.features(d);assert X.shape==(8,588)
    assert np.all(X[:,:576]==0)
    assert X[0,576]==pytest.approx(math.log(.81/.19))
    assert X[0,585]==pytest.approx(.4)  # parent/correction overlap
    assert X[0,586]==0 and X[0,587]==0
    d['targets']={im:None for im in d['targets']}
    for rec in d['records']:rec['crack_boxes_xyxy']=None
    assert np.array_equal(X,r.features(d))
    other=dict(d['originals'][0],parent_id=8,candidate_id='o:8',box_xyxy=[0,0,10,10],score=.7)
    d['originals'].append(other);X=r.features(d)
    assert X[0,586]==1. and X[0,587]==.7


def test_labels_are_localisation_not_duplicate_novelty():
    d=fixture();assert r.labels(d).tolist()==[1.,0.]*4
    d['pairs'][3]['box_xyxy']=[0,0,10,10]
    assert r.labels(d)[1]==1.  # Valid duplicate is deliberately positive.
    d['targets']['353-0']=[];assert r.labels(d)[0]==0


def test_fold_scaling_excludes_held_values_and_labels():
    d=fixture();folds=r.partitions(d,CFG);X=np.arange(8*2).reshape(8,2).astype(float)
    for train,held in folds:
        assert not set(train)&set(held)
        m,s=r.scale_train(X[train]);altered=X.copy();altered[held]=1e12
        assert np.array_equal(m,r.scale_train(altered[train])[0])
        assert np.array_equal(s,r.scale_train(altered[train])[1])
    assert sorted(np.concatenate([h for _,h in folds]).tolist())==list(range(8))
    cfg=copy.deepcopy(CFG);cfg['folds'][0]['fit'].append('353')
    with pytest.raises(ValueError):r.partitions(d,cfg)


def test_analytic_objective_gradient_finite_difference_and_unpenalised_bias():
    Z=np.array([[1.,2.],[-1.,1.],[2.,-1.],[-2.,-1.]])
    y=np.array([1.,0.,1.,0.]);theta=np.array([.1,-.2,.3]);eps=1e-6
    loss,g=r.objective_gradient(theta,Z,y,.001)
    for j in range(3):
        step=np.eye(3)[j]*eps
        finite=(r.objective_gradient(theta+step,Z,y,.001)[0]-r.objective_gradient(theta-step,Z,y,.001)[0])/(2*eps)
        assert g[j]==pytest.approx(finite,abs=1e-8)
    assert g[-1]==pytest.approx(r.objective_gradient(theta,Z,y,0)[1][-1])
    assert math.isfinite(loss)


def test_protected_net_gain_and_immutable_prefix():
    d=fixture();saved=copy.deepcopy(d['originals']);e=r.evaluate(d,r.labels(d),CFG)
    assert e['rows'][:8]==saved and d['originals']==saved
    assert e['retention']==1 and e['net_targets']==4 and e['protected_primary_pass'] is True
    row=e['rows'][8];assert row['score']==pytest.approx(math.sqrt(.81*.81)) and row['probability']==.81 and row['localization_quality']==1.
    assert r.criterion(0,1.,4,CFG) is False
    assert r.criterion(.1,.94,4,CFG) is False
    assert r.criterion(.1,1.,0,CFG) is False
    assert r.criterion(None,1.,4,CFG) is None


def test_admission_strict_ties_attenuation_and_duplicate_guards():
    d=fixture();q=np.zeros(8);q[0]=d['originals'][0]['score']/math.sqrt(.81*.81)
    assert r.added_bank(d,q,CFG)[1]['accepted_corrections']==0
    q[0]=1.;d['pairs'][1]['box_xyxy']=d['originals'][0]['box_xyxy']
    assert r.added_bank(d,q,CFG)[1]['original_duplicate_rejected']==1
    for bad in [np.nan,np.inf,-.01,1.01]:
        q[0]=bad
        with pytest.raises(ValueError):r.added_bank(d,q,CFG)
    d=fixture();d['pairs'][0]=dict(d['pairs'][0],score=.3)
    with pytest.raises(ValueError):r.added_bank(d,np.ones(8),CFG)


def test_correction_nms_cannot_delete_an_original():
    d=fixture();old=dict(d['originals'][0],parent_id=8,candidate_id='o:8',box_xyxy=[20,0,24,10]);d['originals'].append(old)
    new=dict(old,kind='correction',candidate_id='c:8',box_xyxy=[0,0,10,10],original_box_xyxy=old['box_xyxy'])
    d['pairs'].extend([old,new]);d['probabilities']=np.r_[d['probabilities'],.9]
    rows,c=r.added_bank(d,np.ones(9),CFG)
    assert rows[:9]==d['originals'];assert c['correction_duplicate_rejected']==1
    assert any(z['parent_id']==8 and z['kind']=='correction' for z in rows[9:])


def test_head_replay_rejects_scaler_indices_convergence_and_counters():
    d=fixture();X=np.zeros((8,588));y=r.labels(d);train,held=r.partitions(d,CFG)[0]
    model=stationary(X,y,train,held,CFG,None);r.verify_head(model,X,y,train,held,CFG)
    for key,value in [('held_indices',train.tolist()),('positive',999),('iterations',201),('func_evals',2),('initial_objective',10.),('gradient_inf',.1)]:
        bad=dict(model,**{key:value})
        with pytest.raises(ValueError):r.verify_head(bad,X,y,train,held,CFG)
    bad=copy.deepcopy(model);bad['std'][0]=1.
    with pytest.raises(ValueError):r.verify_head(bad,X,y,train,held,CFG)
    bad=copy.deepcopy(model);bad['theta'][-1]=1.
    with pytest.raises(ValueError):r.verify_head(bad,X,y,train,held,CFG)


def test_budget_total_fold_and_rss_caps():
    now=[0.];rss=[0];b=r.Budget(Path('/unused'),CFG['budget'],clock=lambda:now[0],memory=lambda:rss[0])
    b.check();now[0]=3601
    with pytest.raises(RuntimeError,match='TOTAL'):b.check()
    now[0]=901;b.fold_start=0
    with pytest.raises(RuntimeError,match='FIT'):b.check()
    now[0]=0;b.fold_start=None;rss[0]=4*1024**3+1
    with pytest.raises(RuntimeError,match='RSS'):b.check()


def test_pixels_forbidden_but_output_figures_can_be_written():
    with pytest.raises(PermissionError):r.pixel_guard('open',('/tmp/secret.jpg','rb',0))
    with pytest.raises(PermissionError):r.pixel_guard('open',('/cache/images/no-extension','rb',0))
    r.pixel_guard('open',('/run/analysis/F00_decision.png','wb',0))
    r.pixel_guard('open',('/cache/features.npz','rb',0))


def test_supplied_contract_copy_tampering_rejected(tmp_path):
    config=tmp_path/'config.json';lock=tmp_path/'lock.json'
    config.write_bytes((ROOT/r.CONTRACT/'run_config.json').read_bytes());lock.write_bytes((ROOT/r.CONTRACT/'data_lock.json').read_bytes())
    r.verify_source(config,lock)
    changed=r.read(config);changed['minimum_retention']=0;config.write_text(json.dumps(changed))
    with pytest.raises(ValueError):r.verify_source(config,lock)


def setup_pipeline(tmp_path,monkeypatch):
    d=fixture();a=SimpleNamespace(run=tmp_path/'synthetic-run',cache=tmp_path/'cache',metadata=tmp_path/'metadata.json',config=ROOT/r.CONTRACT/'run_config.json',lock=ROOT/r.CONTRACT/'data_lock.json')
    monkeypatch.setattr(r,'load_cached',lambda *args:d)
    monkeypatch.setattr(r,'features',lambda data:np.zeros((8,588)))
    def fake_fit_all(run,X,y,folds,cfg,guard,lineage):
        return original(run,X,y,folds,cfg,guard,lineage,fitter=stationary)
    original=r.fit_all;monkeypatch.setattr(r,'fit_all',fake_fit_all)
    return a,CFG,r.read(a.lock),d


def test_full_synthetic_pipeline_no_optimizer_and_exact_tamper_replay(tmp_path,monkeypatch):
    a,cfg,lock,d=setup_pipeline(tmp_path,monkeypatch);r.execute(a,cfg,lock)
    e,_=r.verify(a,cfg,lock);assert e['protected_primary_pass'] is True
    assert len(list(a.run.glob('fold_*_started.json')))==4
    with pytest.raises(FileExistsError):r.execute(a,cfg,lock)
    score=r.read(a.run/'oof_scores.json');score['quality_probabilities'][0]=.9;r.write(a.run/'oof_scores.json',score)
    with pytest.raises(ValueError,match='OOF'):r.verify(a,cfg,lock)


def test_fit_failure_stops_before_any_held_predictions(tmp_path,monkeypatch):
    a,cfg,lock,d=setup_pipeline(tmp_path,monkeypatch)
    calls=[]
    def failing(run,X,y,folds,cfg,guard,lineage):
        def fitter(*args):
            calls.append(1)
            if len(calls)==2:raise ValueError('synthetic fit failure')
            return stationary(*args)
        # Recover real orchestration without changing production code.
        spec=importlib.util.spec_from_file_location('orchestration_failure',ROOT/'scripts/pavetrack_localization_cv/run.py')
        other=importlib.util.module_from_spec(spec);spec.loader.exec_module(other)
        return other.fit_all(run,X,y,folds,cfg,guard,lineage,fitter=fitter)
    monkeypatch.setattr(r,'fit_all',failing)
    with pytest.raises(ValueError,match='synthetic fit'):r.execute(a,cfg,lock)
    assert len(calls)==2 and r.read(a.run/'status.json')['fits_consumed']==2
    assert not (a.run/'prediction_started.json').exists() and not (a.run/'oof_scores.json').exists()


def test_feasibility_stops_without_head_and_detects_extra_prediction(tmp_path,monkeypatch):
    a,cfg,lock,d=setup_pipeline(tmp_path,monkeypatch)
    original=r.audit
    def impossible(*args):
        out=original(*args);out['oracle_policy']['protected_primary_pass']=False;return out
    monkeypatch.setattr(r,'audit',impossible);r.execute(a,cfg,lock);assert r.verify(a,cfg,lock)[0] is None
    assert not list(a.run.glob('fold_*'))
    r.write(a.run/'oof_scores.json',{})
    with pytest.raises(ValueError,match='boundary'):r.verify(a,cfg,lock)


def test_full_decision_fresh_resource_or_original_tamper_rejected(tmp_path,monkeypatch):
    a,cfg,lock,d=setup_pipeline(tmp_path,monkeypatch);r.execute(a,cfg,lock)
    original=r.read(a.run/'decision.json');r.write(a.run/'decision.json',dict(original,fresh_access=True))
    with pytest.raises(ValueError,match='outcome'):r.verify(a,cfg,lock)
    r.write(a.run/'decision.json',original)
    status=r.read(a.run/'status.json');status['resource']['peak_rss_bytes']=5*1024**3;r.write(a.run/'status.json',status)
    with pytest.raises(ValueError,match='resource'):r.verify(a,cfg,lock)


def test_actual_fitting_host_and_environment_boundary(monkeypatch):
    with pytest.raises(PermissionError,match='producer'):r.require_producer('Mac')
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES','0')
    with pytest.raises(PermissionError,match='CPU-only'):r.require_producer('D-26-09')
    for name,value in [('CUDA_VISIBLE_DEVICES','-1'),('OMP_NUM_THREADS','1'),('MKL_NUM_THREADS','1')]:monkeypatch.setenv(name,value)
    r.require_producer('D-26-09')
