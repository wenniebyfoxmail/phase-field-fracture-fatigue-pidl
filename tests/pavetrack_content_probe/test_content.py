import copy,importlib.util,json,hashlib
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=module('e019_test',ROOT/'scripts/pavetrack_content_probe/run.py');c=a.c;p=a.content;l=a.learning
old=module('e019_synthetic_only',ROOT/'tests/pavetrack_role_probe/test_probe.py')
CFG=c.read(ROOT/c.CONTRACT/'run_config.json')
def guard(cfg=CFG):return a.Guard(cfg,memory=lambda:100)

def fixture():
    d,t,_=old.fixture();cfg=copy.deepcopy(CFG);n=len(d['candidates']);positive={r['parent_id'] for payload in d['labels'] for r in payload['rows'] if r['U']>0};d['candidates']=c.features(d['originals'],d['manifest'],d['probabilities'],cfg)
    # Pure synthetic content: useful and nuisance directions, never true cached values.
    X=np.zeros((n,576),dtype=np.float32)
    for i,row in enumerate(d['candidates']):X[i,:288]=1 if row['parent_id'] in positive else -1;X[i,288:]=((i%3)-1)
    d['content']=X;cfg['input_counts']['images']=len(t);cfg['budget']['training_target_rows']=sum(len(v['rows']) for v in d['labels']);cfg['budget']['covariance_rows']=cfg['budget']['training_target_rows'];cfg['budget']['content_projection_rows']=cfg['budget']['training_target_rows']+sum(v['eligible'] for v in d['candidates']);cfg['budget']['prediction_rows']=cfg['budget']['content_projection_rows']+sum(len(v['rows'])*n for v,n in zip(d['labels'],cfg['fit']['expected_positive_sites']))
    return d,t,cfg

def emit_for(path):
    expected={}
    def emit(n,v):expected[n]=copy.deepcopy(v);c.write(path/n,v)
    return emit,expected


def tiny():
    cfg=copy.deepcopy(CFG);cfg['content']['dimensions']=4;cfg['content']['covariance_batch']=2
    X=np.array([[0,1,2,1],[1,0,0,1],[2,1,-1,1],[3,2,1,1],[99,99,99,99]],dtype=np.float32)
    return X,[0,1,2,3],['24','24','95','95'],['a','a','b','c'],cfg


def test_producer_gate_and_private_ancestors():
    assert c.PROTOCOL=='S01-E019-v1' and old.c.PROTOCOL=='S01-E018-v1'
    with pytest.raises(PermissionError):a.execute(None,CFG,{},guard(),{})
    assert CFG['budget']['PCA_fits']==3 and CFG['budget']['linear_solves']==39


def test_content_weights_are_GT_free_and_balance_site_image_row():
    w=p.weights(['24','24','24','95'],['a','a','b','c']);assert w.tolist()==pytest.approx([.125,.125,.25,.5])
    assert list(__import__('inspect').signature(p.fit).parameters)==['X','indices','locations','images','cfg','guard']


def test_weighted_PCA_matches_reference_statistics_eigenspace_and_sign():
    X,ids,locs,ims,cfg=tiny();watch=guard(cfg);m=p.fit(X,ids,locs,ims,cfg,watch);w=p.weights(locs,ims);mean=np.sum(w[:,None]*X[ids],axis=0);scale=np.maximum(np.sqrt(np.sum(w[:,None]*(X[ids]-mean)**2,axis=0)),1e-6);z=(X[ids]-mean)/scale;cov=z.T@(w[:,None]*z);e,V=np.linalg.eigh(cov);basis=np.asarray(m['basis']);expected=V[:,-2:]
    assert m['mean']==pytest.approx(mean) and m['scale']==pytest.approx(scale)
    assert basis@basis.T==pytest.approx(expected@expected.T,abs=1e-10)
    assert m['projection_eigenvalues']==pytest.approx(e[-2:][::-1]);assert m['scale_floor_columns']==1
    assert all(basis[np.argmax(np.abs(basis[:,j])),j]>=0 for j in range(2))
    assert watch.counts==dict(PCA_fits=1,covariance_rows=4,eigendecompositions=1)


def test_held_content_extremes_do_not_change_fit_statistics_or_basis():
    X,ids,locs,ims,cfg=tiny();m=p.fit(X,ids,locs,ims,cfg,guard(cfg));bad=X.copy();bad[4]=1e20
    assert p.fit(bad,ids,locs,ims,cfg,guard(cfg))==m
    assert np.isfinite(p.project(m,bad,[4],cfg,guard(cfg))).all()


def test_zero_rank_and_negative_content_coordinates_are_valid():
    cfg=copy.deepcopy(CFG);cfg['content']['dimensions']=4;X=np.ones((4,4),dtype=np.float32);m=p.fit(X,[0,1,2,3],['24']*4,['a']*4,cfg,guard(cfg));assert m['effective_components']==0 and p.project(m,X,[0,1,2,3],cfg,guard(cfg))==[[0.,0.]]*4
    X,ids,locs,ims,cfg=tiny();m=p.fit(X,ids,locs,ims,cfg,guard(cfg));z=p.project(m,X,ids,cfg,guard(cfg));assert min(min(v) for v in z)<0 and all(-1<=v<=1 for row in z for v in row)
    assert l.matrix([[.5,.5,.5,.5,-.9,.9]]).shape==(1,6)


@pytest.mark.parametrize('kind',['duplicate','range','identity','dimensions','nonfinite'])
def test_content_invalid_scope_or_values_stop(kind):
    X,ids,locs,ims,cfg=tiny()
    if kind=='duplicate':ids[-1]=ids[0]
    elif kind=='range':ids[-1]=999
    elif kind=='identity':locs[1]='95'
    elif kind=='dimensions':cfg['content']['dimensions']=5
    else:X[1,0]=np.nan
    with pytest.raises(ValueError):p.fit(X,ids,locs,ims,cfg,guard(cfg))


@pytest.mark.parametrize('kind',['indefinite','bad_basis','nonfinite'])
def test_invalid_decomposition_fails_before_projection(monkeypatch,kind):
    X,ids,locs,ims,cfg=tiny();eigh=np.linalg.eigh
    def broken(C):
        e,V=eigh(C)
        if kind=='indefinite':e[0]=-99
        elif kind=='bad_basis':V[:,-1]=V[:,-2]
        else:e[-1]=np.nan
        return e,V
    monkeypatch.setattr(p.np.linalg,'eigh',broken)
    with pytest.raises(ValueError):p.fit(X,ids,locs,ims,cfg,guard(cfg))


@pytest.mark.parametrize('values',[[[0]*5],[[0,0,0,0,-2,0]],[[0,0,-.1,0,0,0]],[[0,0,0,0,float('nan'),0]],[[0,0,0,0,2,0]]])
def test_six_column_predictor_bounds_and_nonfinite(values):
    with pytest.raises(ValueError):l.matrix(values)


def test_eleven_coefficients_and_content_breaks_scalar_ties_for_actual_gain():
    d,t,cfg=fixture();fit=d['labels'][0]['locations'];own=c.scoped(d['originals'],d['candidates'],t,d['image_locations'],fit);cand=[r for r in own['candidates'] if r['eligible']];ids=[r['index'] for r in cand];watch=guard(cfg);m=p.fit(d['content'],ids,[r['location'] for r in cand],[r['image_id'] for r in cand],cfg,watch);z=p.project(m,d['content'],ids,cfg,watch);values=[[.5,.3,1.,.5]+v for v in z];model=l.fit(values,d['supervision'][0]['rows'],cfg,watch);pred=l.predict(model,values,watch);assert model['coefficient_count']==11 and model['coefficient_count_excludes_unsupervised_PCA']
    scores={r['parent_id']:v for r,v in zip(cand,pred)};added,trace=l.select(cand,scores,0,fit,cfg,c,a.locality);q=c.compare(own,added,c.baseline(own));assert q['retention']==1 and q['net_GT']>=1
    assert any(v['values'][4]<0 for v in [dict(values=v) for v in values])
    assert all(r==next(v['row'] for v in cand if r['parent_id']==v['parent_id']) for r in added)


def test_freeze_all_main_models_before_role_predictions_and_no_PCA_diagnostic_refit(tmp_path,monkeypatch):
    d,t,cfg=fixture();watch=guard(cfg);emit,expected=emit_for(tmp_path);monkeypatch.setattr(c,'require_producer',lambda _:None);predict=l.predict
    def checked(model,values,g):
        assert g.counts['model_fits']>=9 and g.counts['PCA_fits']==3
        if g.counts['model_fits']>9:assert (tmp_path/'prediction_freeze_receipt.json').exists()
        return predict(model,values,g)
    monkeypatch.setattr(l,'predict',checked);models,support,added=a.fit_and_freeze(d,t,tmp_path,cfg,watch,emit)
    assert watch.counts['PCA_fits']==watch.counts['eigendecompositions']==3 and watch.counts['model_fits']==39
    assert watch.counts['content_projection_rows']==cfg['budget']['content_projection_rows'] and watch.counts['content_transform_calls']==6
    assert watch.counts['prediction_rows']==cfg['budget']['prediction_rows'] and expected['jackknife.json']['PCA_refits']==0
    for diag in expected['jackknife.json']['fits']:
        k=diag['main_fold'];assert diag['fixed_content_model_digest']==c.digest(models[k]['content_model']) and diag['main_threshold']==models[k]['threshold']
        assert len(diag['predictions'])==len(d['labels'][k]['rows'])
        assert diag['model']['heads']['Q']['rows']==sum(r['location']!=diag['omitted_location'] for r in d['supervision'][k]['rows'])


def pipeline(tmp_path,monkeypatch,real_hook=False):
    d,t,cfg=fixture();run=tmp_path/'S01-E019-synthetic';run.mkdir();snap=run/'input_snapshot';snap.mkdir();c.write(snap/'synthetic.json',dict(synthetic=True));contentdir=run/'content_snapshot';contentdir.mkdir();np.save(contentdir/'pooled_features.npy',d['content'],allow_pickle=False)
    lock=dict(original_rows_digest=c.digest(d['originals']),source_zip_sha256='synthetic',source_files={'synthetic.json':c.sha(snap/'synthetic.json')},source_B12_hits=len(c.baseline(c.scoped(d['originals'],d['candidates'],t,d['image_locations'],cfg['locations']))[1]),content_cache=dict(copy_to_run='content_snapshot/pooled_features.npy',sha256=c.sha(contentdir/'pooled_features.npy'),shape=list(d['content'].shape),dtype='float32'))
    monkeypatch.setattr(a.inputs,'load',lambda *args:d);monkeypatch.setattr(a.legacy,'metadata',lambda *args:d['records']);monkeypatch.setattr(c,'require_producer',lambda _:None)
    if not real_hook:monkeypatch.setattr(a.sys,'addaudithook',lambda _:None)
    args=SimpleNamespace(run=run,source=tmp_path/'synthetic.zip',metadata=tmp_path/'synthetic_metadata.json');launch=dict(synthetic=True);c.write(run/'launch.json',launch);watch=guard(cfg);result=a.execute(args,cfg,lock,watch,launch);return run,result,watch,lock


def test_complete_synthetic_pipeline_actual_net_gain_and_strict_receipt(tmp_path,monkeypatch):
    run,result,watch,lock=pipeline(tmp_path,monkeypatch)
    assert result['comparison']['retention']==1 and result['comparison']['net_GT']>=1 and result['primary_pass']
    assert watch.receipt()['PCA_fits']==3 and watch.receipt()['linear_solves']==39
    assert len(list((run/'analysis').glob('*.png')))==3 and 'Eleven supervised coefficients excludes PCA' in (run/'analysis/README_analysis.md').read_text()
    receipt=c.read(run/'output_receipt.json');expected={n:c.read(run/n) for n in receipt['files'] if n.endswith('.json') and not n.startswith('input_snapshot/')};bad=c.read(run/'model_fold_0.json');bad['content_model']['basis'][0][0]+=1;c.write(run/'model_fold_0.json',bad);receipt['files']['model_fold_0.json']=c.sha(run/'model_fold_0.json')
    with pytest.raises(ValueError,match='semantic'):a.verify(run,expected,receipt,lock)


def test_all_zero_predictions_complete_OOF_with_abstention(tmp_path,monkeypatch):
    def zero(model,values,g):g.take('prediction_rows',len(values));return [dict(roles=[0.,0.,0.],rank_score=0.) for _ in values]
    monkeypatch.setattr(l,'predict',zero);run,result,watch,lock=pipeline(tmp_path,monkeypatch);assert not result['primary_pass'] and result['comparison']['net_GT']==0 and result['comparison']['retention']==1
    assert all(c.read(run/f'model_fold_{i}.json')['threshold']=='abstain' for i in range(3))


def test_invalid_main_PCA_stops_before_role_predictions_or_freeze(tmp_path,monkeypatch):
    d,t,cfg=fixture();monkeypatch.setattr(c,'require_producer',lambda _:None);fit=p.fit;calls=[]
    def broken(*args):
        calls.append(1)
        if len(calls)==2:raise ValueError('synthetic PCA failure')
        return fit(*args)
    monkeypatch.setattr(p,'fit',broken);monkeypatch.setattr(l,'predict',lambda *args:pytest.fail('prediction after invalid PCA'));emit,_=emit_for(tmp_path)
    with pytest.raises(ValueError,match='PCA'):a.fit_and_freeze(d,t,tmp_path,cfg,guard(cfg),emit)
    assert not (tmp_path/'OOF_predictions.json').exists()


def content_source(tmp_path):
    cfg=copy.deepcopy(CFG);src=tmp_path/'source.npy';np.save(src,np.arange(4*576,dtype=np.float32).reshape(4,576),allow_pickle=False);run=tmp_path/'run';(run/'input_snapshot/input_snapshot').mkdir(parents=True);pin=dict(path=str(src),sha256=c.sha(src),bytes=src.stat().st_size,shape=[4,576],dtype='float32',copy_to_run='content_snapshot/pooled_features.npy',scoring_receipt_member='input_snapshot/scoring_receipt.json');c.write(run/'input_snapshot/input_snapshot/scoring_receipt.json',dict(files={'pooled_features.npy':pin['sha256']}));return src,run,cfg,dict(content_cache=pin)


def test_pinned_NPY_snapshot_has_exact_bytes_and_readonly_mapping(tmp_path):
    src,run,cfg,lock=content_source(tmp_path);X=a.inputs.content_snapshot(run,cfg,lock,guard(cfg),c);assert isinstance(X,np.memmap) and not X.flags.writeable and c.sha(run/'content_snapshot/pooled_features.npy')==c.sha(src)
    with pytest.raises(ValueError):X[0,0]=99


@pytest.mark.parametrize('kind',['sha','bytes','shape','type','receipt'])
def test_pinned_content_identity_type_and_scoring_receipt_rejected(tmp_path,kind):
    src,run,cfg,lock=content_source(tmp_path);pin=lock['content_cache']
    if kind=='sha':pin['sha256']='0'*64
    elif kind=='bytes':pin['bytes']+=1
    elif kind=='shape':pin['shape']=[3,576]
    elif kind=='receipt':c.write(run/'input_snapshot/input_snapshot/scoring_receipt.json',dict(files={'pooled_features.npy':'wrong'}))
    else:
        np.save(src,np.ones((4,576),dtype=np.float64));pin.update(sha256=c.sha(src),bytes=src.stat().st_size);c.write(run/'input_snapshot/input_snapshot/scoring_receipt.json',dict(files={'pooled_features.npy':pin['sha256']}))
    with pytest.raises(ValueError):a.inputs.content_snapshot(run,cfg,lock,guard(cfg),c)


def test_loader_checks_source_row_identity_before_any_content_mapping(tmp_path,monkeypatch):
    d,t,cfg=fixture();run=tmp_path/'run';(run/'input_snapshot/input_snapshot').mkdir(parents=True);identity=copy.deepcopy(d['manifest']);identity[0]['source_parent_key']=-999;c.write(run/'input_snapshot/input_snapshot/candidate_identity.json',dict(rows=identity));lock=dict(content_cache=dict(row_identity_member='input_snapshot/candidate_identity.json',shape=list(d['content'].shape)));prior=SimpleNamespace(load=lambda *args:d);monkeypatch.setattr(c,'require_producer',lambda _:None);monkeypatch.setattr(a.inputs,'content_snapshot',lambda *args:pytest.fail('opened misaligned content'))
    with pytest.raises(ValueError,match='identity'):a.inputs.load(None,run,cfg,lock,guard(cfg),c,a.legacy,prior)


@pytest.mark.parametrize('kind',['RSS','WALL','PCA','projection','solve'])
def test_resource_and_all_learning_budgets(kind):
    g=a.Guard(CFG,memory=lambda:2**33) if kind=='RSS' else a.Guard(CFG,start=0,clock=lambda:4000,memory=lambda:0) if kind=='WALL' else guard()
    key={'PCA':'PCA_fits','projection':'content_projection_rows','solve':'linear_solves'}.get(kind)
    if key:g.counts[key]=CFG['budget'][key]
    with pytest.raises(RuntimeError):g.take(key) if key else g.check()


def test_serialized_PCA_projection_identical_and_unverified_model_stops():
    X,ids,locs,ims,cfg=tiny();model=p.fit(X,ids,locs,ims,cfg,guard(cfg));frozen=json.loads(json.dumps(model));assert p.project(frozen,X,ids,cfg,guard(cfg))==p.project(model,X,ids,cfg,guard(cfg))
    frozen['verified']=False
    with pytest.raises(ValueError,match='unverified'):p.project(frozen,X,ids,cfg,guard(cfg))


def test_rank_is_fixed_and_no_label_argument_can_enter_PCA():
    X,ids,locs,ims,cfg=tiny();cfg['content']['rank']=3
    with pytest.raises(ValueError):p.fit(X,ids,locs,ims,cfg,guard(cfg))
    cfg['content']['rank']=2
    with pytest.raises(TypeError):p.fit(X,ids,locs,ims,cfg,guard(cfg),GT=[1])


def test_six_columns_only_no_GT_can_enter_ridge_prediction():
    d,t,cfg=fixture();rows=d['supervision'][0]['rows'];values=[[.5,.5,.5,.5,-.5,.5] for r in rows];model=l.fit(values,rows,cfg,guard(cfg))
    with pytest.raises(TypeError):l.predict(model,values,guard(cfg),GT=[999])


def test_fixed_content_snapshot_tamper_cannot_be_self_rehashed(tmp_path,monkeypatch):
    run,result,watch,lock=pipeline(tmp_path,monkeypatch);receipt=c.read(run/'output_receipt.json');expected={n:c.read(run/n) for n in receipt['files'] if n.endswith('.json') and not n.startswith('input_snapshot/')};file=run/lock['content_cache']['copy_to_run'];raw=bytearray(file.read_bytes());raw[-1]^=1;file.write_bytes(raw);receipt['files'][lock['content_cache']['copy_to_run']]=c.sha(file)
    with pytest.raises(ValueError):a.verify(run,expected,receipt,lock)


def test_combined_E017_allowlist_plus_content_loader_roundtrip(tmp_path,monkeypatch):
    import zipfile
    path,d,oldcfg,lock=old.synthetic_zip(tmp_path);cfg=copy.deepcopy(CFG);cfg['input_counts']=oldcfg['input_counts'];X=np.arange(len(d['candidates'])*576,dtype=np.float32).reshape(-1,576);cache=tmp_path/'pooled.npy';np.save(cache,X,allow_pickle=False);h=c.sha(cache)
    with zipfile.ZipFile(path) as z:raw={n:z.read(n) for n in z.namelist()}
    name='input_snapshot/scoring_receipt.json';receipt=json.loads(raw[name]);receipt['files']={'pooled_features.npy':h};raw[name]=json.dumps(receipt).encode()
    selected=set(lock['source_files'])-{'output_receipt.json'};raw['output_receipt.json']=json.dumps(dict(files={n:hashlib.sha256(raw[n]).hexdigest() for n in selected})).encode()
    with zipfile.ZipFile(path,'w') as z:
        for n,value in raw.items():z.writestr(n,value)
    lock.update(source_zip_sha256=c.sha(path),source_zip_bytes=path.stat().st_size,source_files={n:hashlib.sha256(raw[n]).hexdigest() for n in lock['source_files']},content_cache=dict(path=str(cache),sha256=h,bytes=cache.stat().st_size,shape=list(X.shape),dtype='float32',copy_to_run='content_snapshot/pooled_features.npy',row_identity_member='input_snapshot/candidate_identity.json',scoring_receipt_member='input_snapshot/scoring_receipt.json'))
    run=tmp_path/'combined';run.mkdir();monkeypatch.setattr(c,'require_producer',lambda _:None);watch=guard(cfg);loaded=a.inputs.load(path,run,cfg,lock,watch,c,a.legacy,a.prior_inputs)
    assert loaded['originals']==d['originals'] and loaded['candidates']==d['candidates'] and np.array_equal(loaded['content'],X) and not loaded['content'].flags.writeable
    assert len(list((run/'input_snapshot').rglob('*.json')))==19 and not watch.counts


def test_CPU1_entry_requires_OpenBLAS_thread_limit_as_well_as_legacy_checks(monkeypatch):
    called=[];monkeypatch.setattr(a,'InheritedRequire',lambda cfg:called.append(True));monkeypatch.delenv('OPENBLAS_NUM_THREADS',raising=False)
    with pytest.raises(PermissionError,match='OPENBLAS'):a.require_producer(CFG)
    monkeypatch.setenv('OPENBLAS_NUM_THREADS','1');a.require_producer(CFG);assert called==[True,True]
