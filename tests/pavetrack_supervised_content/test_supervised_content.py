import copy,importlib.util,json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=module('e020_test',ROOT/'scripts/pavetrack_supervised_content/run.py');c=a.c;p=a.content;l=a.learning
old=module('e020_synthetic_only',ROOT/'tests/pavetrack_role_probe/test_probe.py')
cache=module('e020_existing_cache_tests',ROOT/'tests/pavetrack_content_probe/test_content.py')
CFG=c.read(ROOT/c.CONTRACT/'run_config.json')
def guard(cfg=CFG):return a.Guard(cfg,memory=lambda:100)
def emit_for(path):
    expected={}
    def emit(n,v):expected[n]=copy.deepcopy(v);c.write(path/n,v)
    return emit,expected

def fixture():
    d,t,_=old.fixture();cfg=copy.deepcopy(CFG);positive={r['parent_id'] for payload in d['labels'] for r in payload['rows'] if r['U']>0};d['candidates']=c.features(d['originals'],d['manifest'],d['probabilities'],cfg)
    X=np.zeros((len(d['candidates']),576),dtype=np.float32)
    for i,row in enumerate(d['candidates']):X[i,0]=(1 if row['parent_id'] in positive else -1)*np.sqrt(72);X[i,1]=((i%3)-1)*np.sqrt(72)
    d['content']=X;cfg['input_counts']['images']=len(t);main=sum(len(v['rows']) for v in d['labels']);diag=sum(len(v['rows'])*n for v,n in zip(d['labels'],cfg['fit']['expected_positive_sites']));cfg['budget']['training_target_rows']=main;cfg['budget']['content_statistics_rows']=main;cfg['budget']['content_direction_training_rows']=main+diag;cfg['budget']['content_projection_rows']=main+sum(v['eligible'] for v in d['candidates'])+diag;cfg['budget']['prediction_rows']=cfg['budget']['content_projection_rows'];return d,t,cfg

def ownfit():
    d,t,cfg=fixture();labels=d['supervision'][0]['rows'];ids=[r['index'] for r in labels];locs=[r['location'] for r in labels];ims=[r['image_id'] for r in labels];return d,t,cfg,labels,ids,locs,ims

def fit(d,cfg,labels,ids,locs,ims):return p.fit(d['content'],ids,locs,ims,labels,cfg,guard(cfg))

def test_fixed_sketch_orthonormal_map_and_no_seed_or_selection():
    S=p.sketch(CFG);assert S.shape==(576,8) and np.array([[sum(float(S[k,i])*float(S[k,j]) for k in range(576)) for j in range(8)] for i in range(8)])==pytest.approx(np.eye(8),abs=1e-12)
    for j in range(576):assert np.count_nonzero(S[j])==1 and S[j,j%8]==pytest.approx((-1)**((j//8).bit_count())/np.sqrt(72))
    bad=copy.deepcopy(CFG);bad['content']['sketch_dimensions']=16
    with pytest.raises(ValueError):p.sketch(bad)

def test_weighted_statistics_and_both_directions_match_independent_normal_equations():
    d,t,cfg,labels,ids,locs,ims=ownfit();m=fit(d,cfg,labels,ids,locs,ims);raw=np.asarray([[sum(float(v)*float(s) for v,s in zip(row,p.sketch(cfg)[:,j])) for j in range(8)] for row in d['content'][ids]]);w=p.prior.weights(locs,ims);mean=(raw*w[:,None]).sum(0);scale=np.maximum(np.sqrt(((raw-mean)**2*w[:,None]).sum(0)),1e-6)
    assert m['statistics']['mean']==pytest.approx(mean) and m['statistics']['scale']==pytest.approx(scale)
    Z=np.column_stack([np.ones(len(raw)),(raw-mean)/scale]);targets=l.target_columns(labels)
    for name in ['Q','N']:
        y=np.asarray(targets[name]);w=l.weights([int(v>=.5) for v in y],locs,ims);reg=np.diag([0]+[.01]*8);normal=np.asarray([[sum(float(w[k]*Z[k,i]*Z[k,j]) for k in range(len(Z))) for j in range(9)] for i in range(9)])+reg;rhs=np.asarray([sum(float(w[k]*Z[k,i]*y[k]) for k in range(len(Z))) for i in range(9)]);b=np.linalg.solve(normal,rhs)
        assert m['directions'][name]['coefficients']==pytest.approx(b,abs=1e-12)
    assert m['supervised_coefficient_count']==18

def test_held_values_labels_and_GT_cannot_fit_or_enter_projection_interface():
    d,t,cfg,labels,ids,locs,ims=ownfit();m=fit(d,cfg,labels,ids,locs,ims);bad=copy.deepcopy(d);held=sorted(set(range(len(d['content'])))-set(ids));bad['content'][held]=1e20
    assert fit(bad,cfg,labels,ids,locs,ims)==m
    with pytest.raises(TypeError):p.project(m,d['content'],ids,cfg,guard(cfg),GT=[1])
    assert np.isfinite(p.project(m,bad['content'],held,cfg,guard(cfg))).all()

def test_targets_change_direction_but_not_GT_free_statistics():
    d,t,cfg,labels,ids,locs,ims=ownfit();m=fit(d,cfg,labels,ids,locs,ims);bad=copy.deepcopy(labels)
    for r in bad:r['corrected_max_IoU']=1-r['corrected_max_IoU'];r['novel_reference']=False
    n=fit(d,cfg,bad,ids,locs,ims);assert n['statistics']==m['statistics'] and n['directions']!=m['directions']
    assert n['directions']['N']['active'] is False

def test_serialized_model_identical_negative_bounded_coordinates_and_total29():
    d,t,cfg,labels,ids,locs,ims=ownfit();m=fit(d,cfg,labels,ids,locs,ims);z=p.project(m,d['content'],ids,cfg,guard(cfg));assert z==p.project(json.loads(json.dumps(m)),d['content'],ids,cfg,guard(cfg));assert np.min(z)<0 and np.max(np.abs(z))<=1
    h=l.fit([[.5,.3,1.,.5]+v for v in z],labels,cfg,guard(cfg));assert h['coefficient_count']==11 and m['supervised_coefficient_count']+h['coefficient_count']==29

@pytest.mark.parametrize('kind',['duplicate','range','row','site','image','nan','dimension'])
def test_invalid_direction_data_stops(kind):
    d,t,cfg,labels,ids,locs,ims=ownfit()
    if kind=='duplicate':ids[-1]=ids[0]
    elif kind=='range':ids[-1]=9999
    elif kind=='row':labels[0]['index']=-1
    elif kind=='site':labels[0]['location']='999'
    elif kind=='image':labels[0]['image_id']='outside'
    elif kind=='nan':d['content'][ids[0],0]=np.nan
    else:cfg['content']['dimensions']=575
    with pytest.raises(ValueError):fit(d,cfg,labels,ids,locs,ims)

def test_zero_content_and_constant_targets_have_zero_directions():
    d,t,cfg,labels,ids,locs,ims=ownfit();d['content'][:]=0;m=fit(d,cfg,labels,ids,locs,ims);assert all(not v['active'] for v in m['directions'].values());assert p.project(m,d['content'],ids,cfg,guard(cfg))==[[0.,0.]]*len(ids)

@pytest.mark.parametrize('kind',['unverified','norm','coefficients','statistics','map'])
def test_bad_saved_model_rejected(kind):
    d,t,cfg,labels,ids,locs,ims=ownfit();m=fit(d,cfg,labels,ids,locs,ims)
    if kind=='unverified':m['verified']=False
    elif kind=='norm':m['directions']['Q']['norm']+=1
    elif kind=='coefficients':m['directions']['Q']['coefficients'][1]=float('nan')
    elif kind=='statistics':m['statistics']['scale'][0]=0
    else:m['sketch'][0][0]+=1
    with pytest.raises(ValueError):p.project(m,d['content'],ids,cfg,guard(cfg))

def test_freeze_before_diagnostics_refits_both_supervised_stages_and_exact_counts(tmp_path,monkeypatch):
    d,t,cfg=fixture();g=guard(cfg);emit,saved=emit_for(tmp_path);monkeypatch.setattr(c,'require_producer',lambda _:None);original=l.predict
    def predict(model,values,watch):
        assert watch.counts['model_fits']>=9 and watch.counts['content_direction_fits']>=6
        if watch.counts['model_fits']>9:assert (tmp_path/'prediction_freeze_receipt.json').exists()
        return original(model,values,watch)
    monkeypatch.setattr(l,'predict',predict);models,support,added=a.fit_and_freeze(d,t,tmp_path,cfg,g,emit)
    for key in ['model_sets','model_fits','linear_solves','content_statistics_fits','content_statistics_rows','content_direction_fits','content_transform_calls','content_projection_rows','prediction_rows','training_target_rows']:
        assert g.counts[key]==cfg['budget'][key],key
    assert g.counts['content_direction_training_rows']<cfg['budget']['content_direction_training_rows'] and g.counts['linear_solves']==65
    for diag in saved['jackknife.json']['fits']:
        m=diag['model'];k=diag['main_fold'];omitted=diag['omitted_location'];assert omitted not in m['content_model']['fit_locations'];assert m['content_model']['statistics']==models[k]['content_model']['statistics'];assert diag['main_threshold']==models[k]['threshold']
        assert m['heads']['Q']['rows']==m['content_model']['fit_rows'] and len(diag['predictions'])==len(d['labels'][k]['rows'])
    assert saved['jackknife.json']['supervised_direction_refits']==20

def pipeline(tmp_path,monkeypatch):
    d,t,cfg=fixture();run=tmp_path/'S01-E020-synthetic';run.mkdir();snap=run/'input_snapshot';snap.mkdir();c.write(snap/'synthetic.json',dict(synthetic=True));cs=run/'content_snapshot';cs.mkdir();np.save(cs/'pooled_features.npy',d['content'],allow_pickle=False)
    lock=dict(original_rows_digest=c.digest(d['originals']),source_zip_sha256='synthetic',source_files={'synthetic.json':c.sha(snap/'synthetic.json')},source_B12_hits=len(c.baseline(c.scoped(d['originals'],d['candidates'],t,d['image_locations'],cfg['locations']))[1]),content_cache=dict(copy_to_run='content_snapshot/pooled_features.npy',sha256=c.sha(cs/'pooled_features.npy'),shape=list(d['content'].shape),dtype='float32'))
    monkeypatch.setattr(a.inputs,'load',lambda *args:d);monkeypatch.setattr(a.legacy,'metadata',lambda *args:d['records']);monkeypatch.setattr(c,'require_producer',lambda _:None);monkeypatch.setattr(a.sys,'addaudithook',lambda _:None)
    args=SimpleNamespace(run=run,source=tmp_path/'synthetic.zip',metadata=tmp_path/'synthetic_metadata.json');launch=dict(synthetic=True);c.write(run/'launch.json',launch);g=guard(cfg);result=a.execute(args,cfg,lock,g,launch);return run,result,g,lock

def test_complete_synthetic_path_actual_protected_gain_and_strict_inventory(tmp_path,monkeypatch):
    run,result,g,lock=pipeline(tmp_path,monkeypatch);assert result['comparison']['retention']==1 and result['comparison']['net_GT']>=1 and result['primary_pass'];assert g.receipt()['linear_solves']==65
    assert len(list((run/'analysis').glob('*.png')))==3 and 'Total29 supervised coefficients' in (run/'analysis/README_analysis.md').read_text()
    receipt=c.read(run/'output_receipt.json');expected={n:c.read(run/n) for n in receipt['files'] if n.endswith('.json') and not n.startswith('input_snapshot/')};bad=c.read(run/'model_fold_0.json');bad['content_model']['directions']['Q']['coefficients'][0]+=1;c.write(run/'model_fold_0.json',bad);receipt['files']['model_fold_0.json']=c.sha(run/'model_fold_0.json')
    with pytest.raises(ValueError,match='semantic'):a.verify(run,expected,receipt,lock)

def test_all_abstain_finishes_without_claiming_gain(tmp_path,monkeypatch):
    def zero(model,values,g):g.take('prediction_rows',len(values));return [dict(roles=[0.,0.,0.],rank_score=0.) for _ in values]
    monkeypatch.setattr(l,'predict',zero);run,result,g,lock=pipeline(tmp_path,monkeypatch);assert not result['primary_pass'] and result['comparison']['net_GT']==0 and result['comparison']['retention']==1
    assert all(c.read(run/f'model_fold_{i}.json')['threshold']=='abstain' for i in range(3))

def test_invalid_second_main_direction_stops_before_predictions(tmp_path,monkeypatch):
    d,t,cfg=fixture();monkeypatch.setattr(c,'require_producer',lambda _:None);original=p.fit;calls=[]
    def broken(*args,**kw):
        calls.append(1)
        if len(calls)==2:raise ValueError('synthetic direction failure')
        return original(*args,**kw)
    monkeypatch.setattr(p,'fit',broken);monkeypatch.setattr(l,'predict',lambda *args:pytest.fail('premature prediction'));emit,_=emit_for(tmp_path)
    with pytest.raises(ValueError,match='direction'):a.fit_and_freeze(d,t,tmp_path,cfg,guard(cfg),emit)
    assert not (tmp_path/'OOF_predictions.json').exists()

@pytest.mark.parametrize('counter',['content_direction_fits','content_direction_training_rows','linear_solves','content_projection_rows','content_statistics_fits'])
def test_all_new_fit_and_projection_budgets_fail_closed(counter):
    g=guard();g.counts[counter]=CFG['budget'][counter]
    with pytest.raises(RuntimeError):g.take(counter)

def test_CPU1_boundary_refuses_Mac_and_OpenBLAS_limit_missing(monkeypatch):
    with pytest.raises(PermissionError):a.execute(None,CFG,{},guard(),{})
    monkeypatch.setattr(a,'InheritedRequire',lambda _:None);monkeypatch.delenv('OPENBLAS_NUM_THREADS',raising=False)
    with pytest.raises(PermissionError,match='OPENBLAS'):a.require_producer(CFG)

# The unchanged pinned loader still has to round-trip E017 allowlist plus exact NPY.
def test_new_runner_uses_same_pinned_content_loader_and_row_checks():
    assert a.inputs.content_snapshot.__code__.co_code==cache.a.inputs.content_snapshot.__code__.co_code
    assert a.inputs.load.__code__.co_code==cache.a.inputs.load.__code__.co_code
