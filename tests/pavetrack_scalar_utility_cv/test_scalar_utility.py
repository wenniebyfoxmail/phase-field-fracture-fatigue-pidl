import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('e011_test',ROOT/'scripts/pavetrack_scalar_utility_cv/run.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
spec=importlib.util.spec_from_file_location('e009_fixture',ROOT/'tests/pavetrack_localization_cv/test_localization.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
CFG=r.read(ROOT/r.CONTRACT/'run_config.json')

spec=importlib.util.spec_from_file_location('e010_reference_fixture',ROOT/'scripts/pavetrack_utility_cv/run.py')
r10=importlib.util.module_from_spec(spec);spec.loader.exec_module(r10)


def fixture():
    data=f.fixture()
    reference,evaluation=r10.preparation(data,CFG)
    data['e010_reference']=reference
    data['e010_evaluation']=evaluation
    return data


def test_fit_only_labels_and_gt_free_eligibility_and_features():
    d=fixture();eligible,scores=r.eligibility(d)
    assert eligible.all()
    report=r.label_partition(d,CFG['folds'][0]['fit'],eligible,scores)
    assert report['signs']==dict(positive=3,negative=3)
    changed=copy.deepcopy(d)
    for im in changed['targets']:
        if changed['locations'][im]=='353':changed['targets'][im]=None
    assert r.label_partition(changed,CFG['folds'][0]['fit'],eligible,scores)==report
    assert np.array_equal(r.features(d),r.features(changed))
    assert np.array_equal(eligible,r.eligibility(changed)[0])
    X=r.features(d); train=np.asarray([v['index'] for v in report['rows']]);altered=X.copy();altered[:2]=1e10
    assert np.array_equal(r.scale_train(X[train])[0],r.scale_train(altered[train])[0])


def test_synthetic_oracle_support_and_frozen_score_not_utility_multiplier():
    d=fixture();report,e=r.preparation(d,CFG)
    assert report['ready_for_code_review'] and e['net_targets']==4 and e['retention']==1
    u=[2. if i%2==0 else -3. for i in range(8)]
    actual=r.evaluate(d,u,CFG)
    assert actual['rows'][:8]==d['originals']
    assert all(v['score']==pytest.approx(.81) for v in actual['rows'][8:])
    assert r.evaluate(d,[1e-9 if i%2==0 else 0. for i in range(8)],CFG)['rows'][8:][0]['score']==pytest.approx(.81)
    assert r.evaluate(d,[0.]*8,CFG)['net_targets']==0
    with pytest.raises(ValueError):r.evaluate(d,[None]*8,CFG)
    with pytest.raises(ValueError):r.evaluate(d,[float('inf')]*8,CFG)


def test_valid_duplicate_is_actual_FP_not_iou_label():
    d=fixture();context=r.counterfactual_context(d,CFG['locations'])
    row=r.correction(d,1,.7);row['box_xyxy']=[0,0,10,10]
    label=r.single_label(context,row)
    assert max(r.e8.box_iou(row['box_xyxy'],t) for t in d['targets'][row['image_id']])==1
    assert label['admitted'] and label['FP']==1 and label['U']<=0


def test_shortcuts_exact_and_strict_tie_cross_image_displacement():
    d=fixture()
    # Synthetic original bank exhausted at a tied FP group; below that group is safe.
    for i,row in enumerate(d['originals']):
        if i%2==0:row['score']=.3
    d['pairs'][::2]=d['originals']
    for j in range(5):
        row=d['originals'][0]
        extra=dict(row,parent_id=len(d['originals']),candidate_id='extra:'+str(j),score=.3)
        d['originals'].append(extra)
    eligible,scores=r.eligibility(d)
    report=r.label_partition(d,CFG['locations'],eligible,scores)
    context=r.counterfactual_context(d,CFG['locations'])
    for item in report['rows']:
        exact=r.single_label(context,r.correction(d,item['index'],scores[item['index']]))
        assert {k:item[k] for k in exact}==exact
    assert context['first_excluded']==.3
    for score in [.29,.3,.31]:
        exact=r.single_label(context,r.correction(d,0,score))
        if score<.3:assert exact['U']==0 and not exact['admitted']
    # Cross-image displacement: expend a new FP before the budget cutoff.
    row=r.correction(d,1,.95)
    value=r.single_label(context,row)
    assert value['FP']==1


def test_objective_gradient_and_sign_mass_no_solve():
    y=np.array([2.,1.,0.,0.,-1.]);w=r.sign_weights(y)
    for sign in [-1,0,1]:assert w[np.sign(y)==sign].sum()==pytest.approx(1/3)
    with pytest.raises(ValueError):r.sign_weights(np.zeros(3))
    Z=np.arange(10,dtype=float).reshape(5,2)/10;theta=np.array([.1,-.2,.3]);eps=1e-6
    loss,g=r.objective_gradient(theta,Z,y,w,.001)
    for j in range(3):
        step=np.eye(3)[j]*eps
        fd=(r.objective_gradient(theta+step,Z,y,w,.001)[0]-r.objective_gradient(theta-step,Z,y,w,.001)[0])/(2*eps)
        assert g[j]==pytest.approx(fd,abs=1e-8)
    assert r.objective_gradient(theta,Z,y,w,0)[1][-1]==g[-1]


def stationary(X,y,train,held,cfg,guard):
    # Analytic fixed zero stationary solution for balanced +-1 synthetic labels; NO solve/fit.
    mean,std=r.scale_train(X[train]);theta=np.zeros(X.shape[1]+1);w=r.sign_weights(y)
    final,grad=r.objective_gradient(theta,(X[train]-mean)/std,y,w,cfg['fit']['l2'])
    return dict(mean=mean.tolist(),std=std.tolist(),theta=theta.tolist(),weights=w.tolist(),train_indices=train.tolist(),held_indices=held.tolist(),initial_objective=final,final_objective=final,gradient_inf=float(abs(grad).max()),gram_residual_inf=0.,solve_count=1)


def test_synthetic_ridge_verifier_and_held_ineligible_null():
    X=np.zeros((8,12));y=np.array([1.,-1.]*3);train=np.arange(2,8);held=np.arange(2)
    model=stationary(X,y,train,held,CFG,None);r.verify_head(model,X,y,train,held,CFG)
    for key,value in [('solve_count',2),('gradient_inf',.1),('train_indices',[0]),('weights',[1]*6),('gram_residual_inf',1.)]:
        with pytest.raises(ValueError):r.verify_head(dict(model,**{key:value}),X,y,train,held,CFG)
    with pytest.raises(ValueError):r.predict_all([model],X,[(train,held)],np.ones(8,dtype=bool))
    d=fixture();folds=r.partitions(d,CFG);eligible=np.ones(8,dtype=bool);eligible[0]=False
    models=[dict(model,theta=[0.]*12+[.2])]*4
    pred=r.predict_all(models,X,folds,eligible)
    assert pred[0] is None and pred[1:]==[.2]*7


def test_direct_fitting_forbidden_on_mac():
    with pytest.raises(PermissionError):r.fit_head(None,None,None,None,CFG,None)


def test_stop_before_predictions_on_second_fit_failure(tmp_path,monkeypatch):
    d=fixture();report,_=r.preparation(d,CFG)
    monkeypatch.setattr(r,'features',lambda data:np.zeros((8,12)))
    a=SimpleNamespace(run=tmp_path)
    guard=r.Budget(tmp_path,CFG['budget'])
    calls=[]
    def fitter(*args):
        calls.append(1)
        if len(calls)==2:raise ValueError('synthetic failure')
        return stationary(*args)
    with pytest.raises(ValueError,match='synthetic failure'):r.run_models(a,CFG,d,report,guard,{},fitter=fitter)
    assert len(list(tmp_path.glob('fold_*_started.json')))==2
    assert not (tmp_path/'prediction_started.json').exists()


def test_ineligible_never_predicted_strict_parent_tie_and_nms():
    d=fixture();d['probabilities'][0]=d['originals'][0]['score']**2/.81
    eligible,_=r.eligibility(d);assert not eligible[0]
    u=[1.]*8;u[0]=None;e=r.evaluate(d,u,CFG)
    assert all(z['parent_id']!=0 for z in e['rows'][8:])
    d=fixture();old=dict(d['originals'][0],parent_id=8,candidate_id='o:8',box_xyxy=[20,0,24,10]);d['originals'].append(old)
    new=dict(old,kind='correction',candidate_id='c:8',box_xyxy=[0,0,10,10],original_box_xyxy=old['box_xyxy'])
    d['pairs'].extend([old,new]);d['probabilities']=np.r_[d['probabilities'],.9]
    e=r.evaluate(d,[1.]*9,CFG)
    assert e['rows'][:9]==d['originals'] and e['choice']['correction_duplicate_rejected']==1


def test_counterfactual_global_budget_loses_other_target_and_atomic_tie():
    def row(name,box,score):return dict(candidate_id=name,parent_id=0,image_id='im',reid='353',box_xyxy=box,score=score)
    originals=[row('a',[0,0,10,10],.9),row('fp',[40,0,50,10],.7),row('b',[20,0,30,10],.5)]
    data=dict(originals=originals,locations={'im':'353'},targets={'im':[[0,0,10,10],[20,0,30,10]]})
    context=r.counterfactual_context(data,['353'])
    assert len(context['hits'])==2
    for score in [.8,.7]:
        value=r.single_label(context,row('c',[60,0,70,10],score))
        assert value['new']==0 and value['lost']==1
        assert value['U']==(-2 if score>.7 else -1)
        assert value['admitted']==(score>.7)


def test_synthetic_complete_pipeline_replay_and_tamper_without_solve(tmp_path,monkeypatch):
    d=fixture();a=SimpleNamespace(run=tmp_path/'synthetic',cache=Path('/not-read'),metadata=Path('/not-read'),config=ROOT/r.CONTRACT/'run_config.json',lock=ROOT/r.CONTRACT/'data_lock.json',e010_run=Path('/synthetic-reference'))
    monkeypatch.setattr(r,'require_producer',lambda:None)
    monkeypatch.setattr(r,'load_cached',lambda *args:d)
    monkeypatch.setattr(r,'features',lambda data:np.zeros((8,12)))
    monkeypatch.setattr(r,'fit_head',stationary)
    lock=r.read(a.lock)
    r.execute(a,CFG,lock)
    e,_=r.verify(a,CFG,lock)
    assert e['retention']==1 and e['net_targets']==0
    assert len(list(a.run.glob('fold_*_started.json')))==4
    with pytest.raises(FileExistsError):r.execute(a,CFG,lock)
    saved=r.read(a.run/'oof_scores.json');bad=copy.deepcopy(saved);bad['predicted_utilities'][0]=1.
    r.write(a.run/'oof_scores.json',bad)
    with pytest.raises(ValueError,match='OOF'):r.verify(a,CFG,lock)
    r.write(a.run/'oof_scores.json',saved)
    decision=r.read(a.run/'decision.json');r.write(a.run/'decision.json',dict(decision,fresh_access=True))
    with pytest.raises(ValueError,match='outcome'):r.verify(a,CFG,lock)


def test_synthetic_support_stop_with_zero_models(tmp_path,monkeypatch):
    d=fixture()
    for im in d['targets']:d['targets'][im]=[]
    d['e010_reference'],d['e010_evaluation']=r10.preparation(d,CFG)
    a=SimpleNamespace(run=tmp_path/'stop',cache=Path('/none'),metadata=Path('/none'),config=ROOT/r.CONTRACT/'run_config.json',lock=ROOT/r.CONTRACT/'data_lock.json',e010_run=Path('/synthetic-reference'))
    monkeypatch.setattr(r,'require_producer',lambda:None)
    monkeypatch.setattr(r,'load_cached',lambda *args:d)
    lock=r.read(a.lock)
    r.execute(a,CFG,lock)
    assert r.verify(a,CFG,lock)[0] is None
    assert not list(a.run.glob('fold_*'))
    r.write(a.run/'prediction_started.json',{})
    with pytest.raises(ValueError,match='stop boundary'):r.verify(a,CFG,lock)


def test_exact_scalar_block_order_and_pooled_GT_invariance():
    d=fixture();X=r.features(d)
    assert X.shape==(8,12) and X.dtype==np.float64
    assert np.array_equal(X,r10.features(d)[:,576:588])
    assert r.FEATURE_NAMES==CFG['feature_names']
    d['pooled']=np.full((8,576),np.nan)
    d['e010_evaluation']={'predicted_utilities':[1e99]*8}
    for im in d['targets']:d['targets'][im]=None
    for rec in d['records']:rec['crack_boxes_xyxy']=None
    assert np.array_equal(X,r.features(d))


def test_twelve_column_boundary_and_no_real_solve(monkeypatch):
    X=np.zeros((8,12));y=np.array([1.,-1.]*3);train=np.arange(2,8);held=np.arange(2)
    model=stationary(X,y,train,held,CFG,None)
    assert len(model['theta'])==13
    r.verify_head(model,X,y,train,held,CFG)
    with pytest.raises(ValueError,match='twelve-column'):r.verify_head(model,np.zeros((8,588)),y,train,held,CFG)
    monkeypatch.setattr(r,'require_producer',lambda:None)
    with pytest.raises(ValueError,match='twelve-column'):r.fit_head(np.zeros((8,588)),y,train,held,CFG,None)


def test_reference_equivalence_rejects_changed_fit_labels_before_fitting():
    d=fixture();d['e010_reference']['folds'][0]['rows'][0]['U']=99
    with pytest.raises(ValueError,match='equivalence'):r.preparation(d,CFG)
    d=fixture();del d['e010_reference']
    with pytest.raises(KeyError):r.preparation(d,CFG)


def test_reference_hash_and_lineage_binding(tmp_path):
    import hashlib,json
    d=fixture();lock=r.read(ROOT/r.CONTRACT/'data_lock.json');cfg=copy.deepcopy(CFG)
    ref=dict(d['e010_reference'],protocol='S01-E010-v1',run_id='S01-E010-R001',cache_files=lock['cache_files'],metadata_sha256=lock['metadata_sha256'],fresh_access=False)
    ev=dict(d['e010_evaluation'],protocol='S01-E010-v1',run_id='S01-E010-R001',cache_files=lock['cache_files'],metadata_sha256=lock['metadata_sha256'],fresh_access=False)
    for name,payload in [('input_audit.json',ref),('evaluation.json',ev)]:r.write(tmp_path/name,payload)
    expected=copy.deepcopy(cfg['reference_only_e010'])
    expected['input_audit_sha256']=r.sha(tmp_path/'input_audit.json');expected['evaluation_sha256']=r.sha(tmp_path/'evaluation.json')
    cfg['reference_only_e010']=expected;lock['e010_reference']=expected
    assert r.verify_reference(tmp_path,cfg,lock)==(ref,ev)
    r.write(tmp_path/'input_audit.json',dict(ref,fresh_access=True))
    with pytest.raises(ValueError):r.verify_reference(tmp_path,cfg,lock)
    expected['input_audit_sha256']=r.sha(tmp_path/'input_audit.json')
    with pytest.raises(ValueError,match='lineage'):r.verify_reference(tmp_path,cfg,lock)


def test_supplied_contract_tampering_and_pixels_are_rejected(tmp_path):
    config=ROOT/r.CONTRACT/'run_config.json';lock=ROOT/r.CONTRACT/'data_lock.json'
    r.verify_source(config,lock)
    payload=r.read(config);payload['features']=588;r.write(tmp_path/'changed.json',payload)
    with pytest.raises(ValueError):r.verify_source(tmp_path/'changed.json',lock)
    with pytest.raises(PermissionError):r.pixel_guard('open',('/tmp/private.jpg','rb',0))
    with pytest.raises(PermissionError):r.pixel_guard('open',('/data/images/noext','rb',0))
