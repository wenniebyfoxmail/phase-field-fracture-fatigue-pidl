import copy,importlib.util,json,math,zipfile,hashlib
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=module('e018_test',ROOT/'scripts/pavetrack_role_probe/run.py');c=a.c;l=a.learning
old=module('e018_synthetic_only',ROOT/'tests/pavetrack_supervision_feasibility/test_audit.py')
CFG=c.read(ROOT/c.CONTRACT/'run_config.json')
def guard(cfg=CFG):return a.Guard(cfg,memory=lambda:100)

def fixture():
    d,t,_=old.cached_fixture();cfg=copy.deepcopy(CFG);d['candidates']=c.features(d['originals'],d['manifest'],d['probabilities'],cfg);d['supervision']=[];d['context']=[]
    for k,p in enumerate(d['labels']):
        own=c.scoped(d['originals'],d['candidates'],t,d['image_locations'],p['locations']);labels,_=a.audit.supervision(own,p,c.baseline(own),c,a.locality)
        d['supervision'].append(dict(fold=k,locations=p['locations'],GT_informed=True,new_singleton_U=0,rows=labels));d['context'].append(dict(fold=k,locations=p['locations'],**a.audit.context_features(own['originals'],own['candidates'],own['image_locations'],c)))
    cfg['input_counts']['images']=len(t);cfg['budget']['training_target_rows']=sum(len(p['rows']) for p in d['labels']);cfg['budget']['prediction_rows']=cfg['budget']['training_target_rows']+sum(v['eligible'] for v in d['candidates'])+sum(len(p['rows'])*n for p,n in zip(d['labels'],cfg['fit']['expected_positive_sites']))
    return d,t,cfg

def emit_for(path):
    expected={}
    def emit(n,v):expected[n]=copy.deepcopy(v);c.write(path/n,v)
    return emit,expected


def test_producer_boundary_and_private_ancestors():
    assert c.PROTOCOL=='S01-E018-v1' and old.c.PROTOCOL=='S01-E017-v1'
    assert CFG['budget']['model_fits']==39 and CFG['fit']['ridge']==.01
    with pytest.raises(PermissionError):a.execute(None,CFG,{},guard(),{})


def test_hierarchical_weights_balance_strata_sites_images_and_duplicate_rows():
    strata=[0,0,0,0,1,1];sites=['24','24','24','95','151','151'];images=['a','a','b','c','d','d'];w=l.weights(strata,sites,images)
    assert sum(w)==pytest.approx(1) and sum(w[:4])==pytest.approx(.5)
    assert sum(w[:3])==pytest.approx(.25) and w[2]==pytest.approx(.125) and w[0]==pytest.approx(.0625)
    assert sum(l.weights([0]*3,['24']*3,['a']*3))==pytest.approx(1)


def test_ridge_direct_solution_loss_and_intercept_not_penalized():
    x=np.array([[0.],[.25],[.75],[1.] ]);y=np.array([0.,0.,1.,1.]);w=np.ones(4)/4;h=l.ridge(x,y,w,.01,1e-9)
    z=np.column_stack([np.ones(4),x]);expected=np.linalg.solve(z.T@z/4+np.diag([0,.01]),z.T@y/4)
    assert h['coefficients']==pytest.approx(expected) and h['normal_residual_inf']<1e-9 and h['objective']<=h['constant_baseline_objective']
    assert l.ridge(x,np.ones(4),w,.01,1e-9)['coefficients']==pytest.approx([1.,0.])
    assert l.ridge(x,np.zeros(4),w,.01,1e-9)['coefficients']==[0.,0.]


@pytest.mark.parametrize('values',[[[0,0,0]],[[0,0,0,float('nan')]],[[0,0,-1,0]],[[2,0,0,0]],[]])
def test_feature_matrix_refuses_wrong_shape_and_nonfinite(values):
    with pytest.raises(ValueError):l.matrix(values)


def test_three_heads_seven_coefficients_no_GT_predict_interface_and_zero_class():
    d,t,cfg=fixture();rows=d['supervision'][0]['rows'];values=[[.2,.1,.1,.3] if r['cached_singleton']['U']<=0 else [.9,.9,.9,.9] for r in rows];watch=guard(cfg);model=l.fit(values,rows,cfg,watch)
    assert model['coefficient_count']==7 and watch.counts['linear_solves']==3
    out=l.predict(model,values,watch);assert out[0]['rank_score']==pytest.approx(math.prod(out[0]['roles']))
    empty=copy.deepcopy(rows)
    for r in empty:r['novel_reference']=False
    zero=l.fit(values,empty,cfg,watch);assert all(p['rank_score']==0 for p in l.predict(zero,values,watch))
    with pytest.raises(TypeError):l.predict(model,values,watch,GT=[999])


def test_learned_scores_overcome_competitors_with_actual_protected_joint_gain():
    d,t,cfg=fixture();own=c.scoped(d['originals'],d['candidates'],t,d['image_locations'],d['labels'][0]['locations']);rows=d['supervision'][0]['rows'];features=[[.9,.9,.9,.9] if r['cached_singleton']['U']>0 else [.1,.1,.1,.1] for r in rows];watch=guard(cfg);model=l.fit(features,rows,cfg,watch);pred=l.predict(model,features,watch);scores={r['parent_id']:p for r,p in zip(rows,pred)};added,trace=l.select(own['candidates'],scores,0,own['locations'],cfg,c,a.locality);q=c.compare(own,added,c.baseline(own))
    assert q['retention']==1 and q['net_GT']>=1 and any(v['reason']=='accepted' for v in trace)
    assert all(v==next(row['row'] for row in own['candidates'] if row['parent_id']==v['parent_id']) for v in added)
    assert all(sum(c.group_of(v['reid'],cfg)==g for v in added)<=3 for g in range(3))


@pytest.mark.parametrize('value',[True,.01,-1,float('nan')])
def test_no_new_gate_search(value):
    with pytest.raises(ValueError):l.select([],{},value,[],CFG,c,a.locality)


def test_zero_rank_and_abstain_admit_nothing_and_joint_harm_is_rejected():
    d,t,cfg=fixture();scores={r['parent_id']:dict(rank_score=0) for r in d['candidates'] if r['eligible']}
    assert l.select(d['candidates'],scores,0,cfg['locations'],cfg,c,a.locality)==([],[])
    assert l.select(d['candidates'],{},'abstain',cfg['locations'],cfg,c,a.locality)==([],[])
    base=dict(retention=.99,net_GT=3,macro_delta=.1,added_FP=0,appended=1)
    assert c.choose([dict(threshold=0,comparison=base)])=='abstain'
    base.update(retention=1,net_GT=0)
    assert c.choose([dict(threshold=0,comparison=base)])=='abstain'


def test_GT_free_representation_ignores_poison_metadata_and_matches_saved_context():
    d,t,cfg=fixture();own=c.scoped(d['originals'],d['candidates'],t,d['image_locations'],d['labels'][0]['locations']);context,features=a.representation(own,cfg,guard(cfg));poison=copy.deepcopy(own)
    poison['targets']='POISON'
    for row in poison['candidates']:row.update(GT='POISON',U=999,cutoff=999,novel_reference=True)
    assert a.representation(poison,cfg,guard(cfg))==(context,features)
    assert dict(fold=0,locations=own['locations'],**context)==d['context'][0]


@pytest.mark.parametrize('field',['cached','scope','gain','novel','valid','reference','fixed','quality','rows'])
def test_saved_supervision_corruptions_rejected(field):
    d,t,cfg=fixture();own=c.scoped(d['originals'],d['candidates'],t,d['image_locations'],d['labels'][0]['locations']);saved=copy.deepcopy(d['supervision'][0]);y=saved['rows'][0]
    if field=='cached':y['cached_singleton']['FP']=99
    elif field=='scope':saved['locations']=cfg['held_groups'][0]
    elif field=='gain':y['gain_same_reference']=999
    elif field=='novel':y['novel_reference']=not y['novel_reference']
    elif field=='valid':y['valid_localisation']=not y['valid_localisation']
    elif field=='reference':y['corrected_reference']=['outside',0]
    elif field=='fixed':y['fixed_admission']=not y['fixed_admission']
    elif field=='quality':y['corrected_max_IoU']=float('nan')
    else:saved['rows'].pop()
    with pytest.raises(ValueError):a.inputs.validate_supervision(saved,d['labels'][0],own,c.baseline(own),0,c,a.locality,a.audit)


def test_full_freeze_precedes_diagnostics_and_all_nine_main_heads_precede_predictions(tmp_path,monkeypatch):
    d,t,cfg=fixture();watch=guard(cfg);emit,expected=emit_for(tmp_path);monkeypatch.setattr(c,'require_producer',lambda _:None);original=l.predict;events=[]
    def predict(model,values,g):
        assert g.counts['model_fits']>=9
        if g.counts['model_fits']>9:assert (tmp_path/'prediction_freeze_receipt.json').exists()
        events.append(g.counts['model_fits']);return original(model,values,g)
    monkeypatch.setattr(l,'predict',predict);models,support,added=a.fit_and_freeze(d,t,tmp_path,cfg,watch,emit)
    assert events[:6]==[9]*6 and watch.counts['model_fits']==watch.counts['linear_solves']==39
    assert watch.counts['prediction_rows']==cfg['budget']['prediction_rows']
    assert len(expected['jackknife.json']['fits'])==10 and not expected['jackknife.json']['new_gate_calibration']
    for diag in expected['jackknife.json']['fits']:
        k=diag['main_fold'];assert diag['main_threshold']==models[k]['threshold']
        assert diag['model']['heads']['Q']['rows']==sum(y['location']!=diag['omitted_location'] for y in d['supervision'][k]['rows'])
        assert len(diag['predictions'])==len(d['labels'][k]['rows'])
    assert expected['prediction_freeze_receipt.json']['all_nine_main_heads_verified_before_predictions']


def pipeline(tmp_path,monkeypatch,real_hook=False):
    d,t,cfg=fixture();run=tmp_path/'S01-E018-synthetic';run.mkdir();snap=run/'input_snapshot';snap.mkdir();c.write(snap/'synthetic.json',dict(synthetic=True));lock=dict(original_rows_digest=c.digest(d['originals']),source_zip_sha256='synthetic',source_files={'synthetic.json':c.sha(snap/'synthetic.json')},source_B12_hits=len(c.baseline(c.scoped(d['originals'],d['candidates'],t,d['image_locations'],cfg['locations']))[1]));d['snapshot']=snap
    monkeypatch.setattr(a.inputs,'load',lambda *args:d);monkeypatch.setattr(a.legacy,'metadata',lambda *args:d['records']);monkeypatch.setattr(c,'require_producer',lambda _:None)
    if not real_hook:monkeypatch.setattr(a.sys,'addaudithook',lambda _:None)
    args=SimpleNamespace(run=run,source=tmp_path/'synthetic.zip',metadata=tmp_path/'synthetic_metadata.json');launch=dict(synthetic=True);c.write(run/'launch.json',launch);watch=guard(cfg);result=a.execute(args,cfg,lock,watch,launch);return run,result,watch,lock


def test_complete_synthetic_execute_receipt_plots_and_semantic_tamper(tmp_path,monkeypatch):
    run,result,watch,lock=pipeline(tmp_path,monkeypatch)
    assert result['learned_selection'] and not result['GT_informed_selection'] and result['originals_unchanged']
    assert watch.receipt()['linear_solves']==39 and watch.counts['calibration_policy_comparisons']==15
    assert len(list((run/'analysis').glob('*.png')))==3 and 'not rebased FIT7 U' in (run/'analysis/README_analysis.md').read_text()
    receipt=c.read(run/'output_receipt.json');expected={n:c.read(run/n) for n in receipt['files'] if n.endswith('.json') and not n.startswith('input_snapshot/')};bad=c.read(run/'model_fold_0.json');bad['heads']['Q']['coefficients'][0]+=1;c.write(run/'model_fold_0.json',bad);receipt['files']['model_fold_0.json']=c.sha(run/'model_fold_0.json')
    with pytest.raises(ValueError,match='semantic'):a.verify(run,expected,receipt,lock['source_files'])


@pytest.mark.parametrize('kind',['RSS','WALL','COUNT'])
def test_resource_caps(kind):
    g=a.Guard(CFG,memory=lambda:2**33) if kind=='RSS' else a.Guard(CFG,start=0,clock=lambda:4000,memory=lambda:0) if kind=='WALL' else guard()
    if kind=='COUNT':g.counts['linear_solves']=39
    with pytest.raises(RuntimeError):g.take('linear_solves') if kind=='COUNT' else g.check()


def test_zip_loader_checks_hash_before_any_unapproved_decode(tmp_path):
    p=tmp_path/'wrong.zip';p.write_bytes(b'wrong')
    with pytest.raises(ValueError):a.inputs.load(p,tmp_path,CFG,dict(source_zip_sha256='0'*64),guard(),c,a.legacy)


def synthetic_zip(tmp_path):
    d,t,cfg=fixture();source_commit='synthetic-E017';r004commit='synthetic-R004';oldzip='synthetic-R004-zip';digest=c.digest(d['originals']);nested={
        'qualification.json':dict(joint=dict(rows=d['originals']+[dict(kind='GT_ORACLE_POISON')]),oracle=dict(chosen='FORBIDDEN')),
        'candidate_identity.json':dict(rows=d['manifest']),
        'scores.json':dict(source_keys=[r['source_parent_key'] for r in d['manifest']],probabilities=d['probabilities']),
        'source_receipt.json':dict(original_rows_digest=digest),'scoring_receipt.json':dict(rows=len(d['candidates']),CPU_head_passes=2),'launch.json':dict(reviewed_commit=r004commit),'output_receipt.json':dict(synthetic=True),
        **{f'fit8_fold_{k}.json':d['labels'][k] for k in range(3)}}
    members={'input_snapshot/'+n:v for n,v in nested.items()};members.update({f'supervision_fold_{k}.json':d['supervision'][k] for k in range(3)});members.update({f'context_fold_{k}.json':d['context'][k] for k in range(3)});members.update({'input_audit.json':dict(source_zip_sha256=oldzip,original_rows_digest=digest),'launch.json':dict(reviewed_commit=source_commit)})
    raw={n:json.dumps(v).encode() for n,v in members.items()};raw['output_receipt.json']=json.dumps(dict(files={n:hashlib.sha256(v).hexdigest() for n,v in raw.items()})).encode();p=tmp_path/'source.zip'
    with zipfile.ZipFile(p,'w') as z:
        for n,v in raw.items():z.writestr(n,v)
        z.writestr('FIT_audit_fold_0.json',b'not JSON and must never be read');z.writestr('pooled_features.npy',b'forbidden')
    lock=dict(source_zip_sha256=c.sha(p),source_zip_bytes=p.stat().st_size,source_files={n:hashlib.sha256(v).hexdigest() for n,v in raw.items()},source_commit=source_commit,ancestor_R004_commit=r004commit,ancestor_R004_zip_sha256=oldzip,original_rows_digest=digest,source_original_count=len(d['originals']),source_correction_count=len(d['candidates']),source_eligible_count=sum(v['eligible'] for v in d['candidates']))
    return p,d,cfg,lock


def test_allowlist_loader_roundtrip_skips_oracle_tail_and_forbidden_members(tmp_path,monkeypatch):
    p,d,cfg,lock=synthetic_zip(tmp_path);run=tmp_path/'run';run.mkdir();original=c.read;read_names=[]
    def read(path):
        read_names.append(Path(path).name)
        assert Path(path).name not in ['qualification.json','FIT_audit_fold_0.json','pooled_features.npy']
        return original(path)
    monkeypatch.setattr(c,'read',read);loaded=a.inputs.load(p,run,cfg,lock,guard(cfg),c,a.legacy)
    assert loaded['originals']==d['originals'] and loaded['candidates']==d['candidates'] and loaded['supervision']==d['supervision']
    assert not (run/'input_snapshot/FIT_audit_fold_0.json').exists() and len(list((run/'input_snapshot').rglob('*.json')))==19


@pytest.mark.parametrize('kind',['size','member','launch','path','duplicate'])
def test_zip_loader_rejects_identity_or_unsafe_inventory(tmp_path,kind):
    p,d,cfg,lock=synthetic_zip(tmp_path);run=tmp_path/'run';run.mkdir()
    if kind=='size':lock['source_zip_bytes']+=1
    elif kind=='member':lock['source_files']['launch.json']='0'*64
    elif kind=='launch':lock['source_commit']='wrong'
    elif kind=='path':lock['source_files']['../escape.json']='0'*64
    else:
        with zipfile.ZipFile(p,'a') as z:
            with pytest.warns(UserWarning):z.writestr('launch.json',b'{}')
        lock['source_zip_sha256']=c.sha(p);lock['source_zip_bytes']=p.stat().st_size
    with pytest.raises(ValueError):a.inputs.load(p,run,cfg,lock,guard(cfg),c,a.legacy)
    assert not (tmp_path/'escape.json').exists()


def test_bad_fit_stops_before_any_predictions_or_freeze(tmp_path,monkeypatch):
    d,t,cfg=fixture();monkeypatch.setattr(c,'require_producer',lambda _:None);solve=l.ridge;calls=[]
    def broken(*args):
        calls.append(1)
        if len(calls)==2:raise ValueError('synthetic numerical failure')
        return solve(*args)
    monkeypatch.setattr(l,'ridge',broken);monkeypatch.setattr(l,'predict',lambda *args:pytest.fail('prediction after invalid fit'));emit,_=emit_for(tmp_path)
    with pytest.raises(ValueError,match='numerical'):a.fit_and_freeze(d,t,tmp_path,cfg,guard(cfg),emit)
    assert not (tmp_path/'OOF_predictions.json').exists()


def test_current_model_never_uses_current_held_GT(tmp_path,monkeypatch):
    d,t,cfg=fixture();monkeypatch.setattr(c,'require_producer',lambda _:None);fit=l.fit;models=[]
    def first_only(values,rows,cfg,watch):
        if models:raise RuntimeError('stop after first isolated model')
        model=fit(values,rows,cfg,watch);models.append(copy.deepcopy(model));return model
    monkeypatch.setattr(l,'fit',first_only);emit,_=emit_for(tmp_path)
    with pytest.raises((RuntimeError,ValueError)):a.fit_and_freeze(d,t,tmp_path,cfg,guard(cfg),emit)
    before=models.pop();poison=copy.deepcopy(t)
    for im,loc in d['image_locations'].items():
        if loc in cfg['held_groups'][0]:poison[im]=[]
    with pytest.raises((RuntimeError,ValueError)):a.fit_and_freeze(d,poison,tmp_path,cfg,guard(cfg),emit)
    assert models[0]==before


def test_complete_all_zero_prediction_abstains_without_fake_gain(tmp_path,monkeypatch):
    def zero(model,values,watch):
        watch.take('prediction_rows',len(values));return [dict(roles=[0.,0.,0.],rank_score=0.) for _ in values]
    monkeypatch.setattr(l,'predict',zero);run,result,watch,lock=pipeline(tmp_path,monkeypatch)
    assert result['comparison']['retention']==1 and result['comparison']['net_GT']==0 and not result['primary_pass']
    assert all(c.read(run/f'model_fold_{k}.json')['threshold']=='abstain' for k in range(3))
    assert c.read(run/'OOF_predictions.json')['folds'][0]['rows']==[]
