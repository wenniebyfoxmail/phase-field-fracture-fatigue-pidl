import copy,importlib.util,json,math,random
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('stage_b_test',ROOT/'scripts/pavetrack_positive_evidence/stage_b.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
CFG=r.read(ROOT/r.CONTRACT/'run_config.json')
def guard(cfg=CFG):return r.Guard(cfg,memory=lambda:100)
def fixture(seed=1,images=6):
    rng=random.Random(seed);original=[];pairs=[];targets={};locations={};manifest=[];records={};probs=[]
    for k in range(images):
        loc=CFG['locations'][k%12];im=f'im-{k}';locations[im]=loc;targets[im]=[[10,10,30,30],[25,10,45,30]] if k%3 else [];records[im]=dict(width=100,height=100)
        for j in range(6):
            pid=100+len(original)*7;box=rng.choice([[10,10,30,30],[20,10,40,30],[40,40,60,60],[60,10,80,30]]);score=rng.choice([.1,.2,.4,.6,.8]);old=dict(parent_id=pid,candidate_id='o:'+str(pid),image_id=im,reid=loc,kind='original',box_xyxy=box,proposer_confidence=1.,probability=score*score,score=score,E003_score=score)
            new=dict(old,candidate_id='c:'+str(pid),kind='correction',original_box_xyxy=box,box_xyxy=rng.choice([[10,10,30,30],[25,10,45,30],[0,0,10,10]]));original.append(old);pairs.extend([old,new]);probs.append(rng.choice([.09,.25,.49,.81]))
    return dict(originals=original,pairs=pairs,targets=targets,locations=locations,records=records,manifest=manifest),probs

@pytest.mark.parametrize('seed',range(20))
def test_fast_singleton_matches_full_reference_with_ties_sparse_ids_and_FP_cost(seed):
    d,probs=fixture(seed);locations=list(set(d['locations'].values()));ctx=r.fast.Context(d,locations,r.a.e11.e8.metrics,r.a.e11.e8.box_iou)
    reference=r.a.e11.counterfactual_context(d,locations)
    for i,row in enumerate(d['pairs'][1::2]):
        new=dict(row,score=math.sqrt(probs[i]),probability=probs[i],rescored_correction=True)
        assert ctx.label(new)==r.a.e11.single_label(reference,new)
    # A correction exactly on the first excluded score must not take a shortcut.
    if ctx.first_excluded is not None:
        new=dict(d['pairs'][1],score=ctx.first_excluded)
        assert ctx.label(new)==r.a.e11.single_label(reference,new)

def test_eligibility_GT_free_originals_unchanged_and_static_conflicts():
    d,p=fixture();saved=copy.deepcopy(d['originals']);rows,e=r.eligibility(d,p,CFG);d['targets']={k:[[0,0,1,1]] for k in d['targets']};assert (rows,e)==r.eligibility(d,p,CFG);assert d['originals']==saved
    assert not all(e) and any(e)

def test_joint_matches_reference_order_and_keeps_originals():
    d,p=fixture(18);rows,eligible=r.eligibility(d,p,CFG);chosen=[i for i,v in enumerate(eligible) if v];saved=copy.deepcopy(d['originals']);g=guard();j=r.joint(d,rows,chosen,CFG,g)
    assert j['rows'][:len(saved)]==saved and d['originals']==saved and g.counts['joint_comparisons']==1
    for row in j['rows'][len(saved):]:assert row['score']==rows[next(i for i,x in enumerate(rows) if x['parent_id']==row['parent_id'])]['score']
    with pytest.raises(RuntimeError,match='COUNT_CAP'):r.joint(d,rows,chosen,CFG,g)

class FakeImage:
    def close(self):pass
class FakeBackend:
    def __init__(self):self.features_calls=0;self.head_calls=0
    def image(self,raw,record):assert raw==b'synthetic';return FakeImage()
    def features(self,image,rows):self.features_calls+=1;return np.full((len(rows),576),.125,dtype=np.float32)
    def probabilities(self,X):self.head_calls+=1;return [float(.75)]*len(X)

def scoring_fixture(tmp_path):
    path=tmp_path/'synthetic.jpg';path.write_bytes(b'synthetic');h=r.sha(path);rows=[dict(image_id='i',prepared_image=str(path),prepared_image_sha256=h,width=10,height=10,crop_box_xyxy=[0,0,10,10],source_parent_key=i) for i in range(3)]
    cfg=copy.deepcopy(CFG);cfg['budget'].update(source_image_decodes=1,new_unique_backbone_crop_rows=3,max_backbone_batches=1,head_scoring_rows=3,head_verification_rows=3,total_head_rows=6);run=tmp_path/'run';run.mkdir();return dict(manifest=rows),cfg,run

def test_scoring_single_decode_backbone_two_head_passes_and_no_repeat(tmp_path):
    d,c,run=scoring_fixture(tmp_path);backend=FakeBackend();g=guard(c);expected={};p=r.score(d,run,c,dict(E003_checkpoint_sha256='fixed'),g,backend,expected)
    assert p==[.75]*3 and backend.features_calls==1 and backend.head_calls==2
    assert g.counts['source_image_decodes']==1 and g.counts['total_head_rows']==6
    assert expected['scoring_receipt.json']['CPU_head_passes']==2
    with pytest.raises(ValueError,match='duplicate scoring'):r.score(d,run,c,dict(E003_checkpoint_sha256='fixed'),g,backend)
    with pytest.raises(RuntimeError,match='COUNT_CAP'):g.take('head_verification_rows')

def test_failure_after_feature_cache_keeps_valid_completed_journal(tmp_path):
    d,c,run=scoring_fixture(tmp_path);backend=FakeBackend()
    def bad(X):raise RuntimeError('head failure')
    backend.probabilities=bad
    with pytest.raises(RuntimeError,match='head failure'):r.score(d,run,c,dict(E003_checkpoint_sha256='fixed'),guard(c),backend)
    journal=[json.loads(x) for x in (run/'image_progress.jsonl').read_text().splitlines()];assert len(journal)==1
    X=np.load(run/'pooled_features.npy',allow_pickle=False);assert r.hashlib.sha256(np.ascontiguousarray(X[journal[0]['indices']]).tobytes()).hexdigest()==journal[0]['features_sha256']
    assert not (run/'scoring_receipt.json').exists()

@pytest.mark.parametrize('kind',['image','features','replay'])
def test_bad_hash_feature_or_head_replay_fails_closed(tmp_path,kind):
    d,c,run=scoring_fixture(tmp_path);backend=FakeBackend()
    if kind=='image':d['manifest'][0]['prepared_image_sha256']='wrong'
    elif kind=='features':backend.features=lambda *args:np.full((3,576),np.nan,dtype=np.float32)
    else:
        calls=[]
        def changing(X):calls.append(1);return [.5 if len(calls)==1 else .6]*len(X)
        backend.probabilities=changing
    with pytest.raises(ValueError):r.score(d,run,c,dict(E003_checkpoint_sha256='fixed'),guard(c),backend)
    assert not (run/'scoring_receipt.json').exists()

def test_full_qualification_synthetic_and_analysis_no_model_or_U_replay(tmp_path,monkeypatch):
    d,p=fixture(images=12);before=copy.deepcopy(d['originals']);g=guard();expected={};result,reports=r.qualify(d,p,tmp_path,CFG,g,expected)
    assert d['originals']==before and len(reports)==4
    assert sum(len(v['rows']) for v in reports)<=3*len(p)
    assert result['joint']['GT_informed'] and not result['learned_detection_result']
    analysis=r.module('analysis_test',ROOT/'scripts/pavetrack_positive_evidence/stage_b_analyze.py')
    monkeypatch.setattr(r.fast.Context,'label',lambda *x:pytest.fail('no label replay'))
    analysis.render(tmp_path,result,reports,r.read(tmp_path/'cases.json'),g)
    assert len(list((tmp_path/'analysis').glob('*.png')))==3

@pytest.mark.parametrize('kind',['RSS','GPU','WALL'])
def test_frozen_resource_caps(kind):
    if kind=='RSS':g=r.Guard(CFG,memory=lambda:2**33)
    elif kind=='GPU':g=guard();g.gpu=lambda:(2**33,0)
    else:
        ticks=iter([0,3601]);g=r.Guard(CFG,clock=lambda:next(ticks),memory=lambda:0)
    with pytest.raises(RuntimeError,match=kind):g.check()

def test_real_backend_cannot_open_model_on_Mac():
    with pytest.raises(PermissionError):r.runtime.TorchBackend(CFG,Path('/forbidden.pt'),guard(),lambda *x:pytest.fail('checkpoint must not open'))

def test_pixel_gate_exact_allowlist(tmp_path):
    gate=r.PixelGate([dict(prepared_image=str(tmp_path/'allowed.jpg'))]);gate('open',(str(tmp_path/'allowed.jpg'),'r',0))
    with pytest.raises(PermissionError):gate('open',(str(tmp_path/'fresh.jpg'),'r',0))

def test_complete_synthetic_pipeline_semantics_reject_rehashed_outputs(tmp_path,monkeypatch):
    d,p=fixture(images=12);raw=tmp_path/'generated.jpg';raw.write_bytes(b'synthetic')
    d['manifest']=[dict(source_run='synthetic',source_parent_key=old['parent_id'],image_id=old['image_id'],location=old['reid'],corrector_fold=0,prepared_image=str(raw),prepared_image_sha256=r.sha(raw),width=100,height=100,crop_box_xyxy=[0,0,10,10]) for old in d['pairs'][::2]]
    d['stage_A']={};checkpoint=tmp_path/'fake.pt';checkpoint.write_bytes(b'not a model');run=tmp_path/'run';run.mkdir();launch={'synthetic':True};r.write(run/'launch.json',launch)
    cfg=copy.deepcopy(CFG);N=len(p);cfg['budget'].update(source_image_decodes=12,new_unique_backbone_crop_rows=N,max_backbone_batches=12,head_scoring_rows=N,head_verification_rows=N,total_head_rows=2*N)
    lock=dict(E003_checkpoint_sha256=r.sha(checkpoint),stage_A_files={'missing_scores_manifest.json':'synthetic'})
    backend=FakeBackend();monkeypatch.setattr(r,'inputs',lambda *args:d);monkeypatch.setattr(r.runtime,'TorchBackend',lambda *args:backend);monkeypatch.setattr(r.sys,'addaudithook',lambda *args:None)
    # Hold trusted expected objects returned to verifier; not output re-reading.
    saved={};real=r.verify
    def capture(run,cfg,lock,expected,receipt):saved.update(expected=copy.deepcopy(expected),receipt=copy.deepcopy(receipt));return real(run,cfg,lock,expected,receipt)
    monkeypatch.setattr(r,'verify',capture)
    result=r.execute(SimpleNamespace(run=run,checkpoint=checkpoint),cfg,lock,guard(cfg),launch)
    assert backend.features_calls==12 and backend.head_calls==2 and result['scope'].startswith('conditional')
    q=r.read(run/'qualification.json');q['joint']['net_targets']=999;r.write(run/'qualification.json',q);saved['receipt']['files']['qualification.json']=r.sha(run/'qualification.json')
    with pytest.raises(ValueError,match='semantic mismatch'):real(run,cfg,lock,saved['expected'],saved['receipt'])
    saved['receipt']['files']={}
    with pytest.raises(ValueError,match='strict output inventory'):real(run,cfg,lock,saved['expected'],saved['receipt'])


def test_FAST_matching_random_boxes_multiple_gt_and_boundary_groups():
    rng=random.Random(991)
    for trial in range(80):
        targets={};locs={};old=[]
        for im in ['A','B','C']:
            locs[im]='24';targets[im]=[[rng.randrange(15),0,rng.randrange(20,36),20] for _ in range(3)]
            for j in range(10):old.append(dict(image_id=im,reid='24',candidate_id=f'o:{len(old)*9}',parent_id=len(old)*9,score=rng.choice([.1,.2,.3,.5,.8]),box_xyxy=[rng.randrange(15),0,rng.randrange(20,36),20]))
        d=dict(originals=old,targets=targets,locations=locs);ctx=r.fast.Context(d,['24'],r.a.e11.e8.metrics,r.a.e11.e8.box_iou);ref=r.a.e11.counterfactual_context(d,['24'])
        for j in range(10):
            row=dict(image_id=rng.choice(list(targets)),reid='24',candidate_id='c:999',parent_id=999,score=rng.choice([.05,.1,.2,.3,.5,.8,.9]),box_xyxy=[rng.randrange(15),0,rng.randrange(20,36),20])
            assert ctx.label(row)==r.a.e11.single_label(ref,row)

def test_producer_account_version_mask_and_executable_guard_with_fake_environment(monkeypatch):
    import os,socket
    runtime=r.runtime;cfg=copy.deepcopy(CFG)
    monkeypatch.setattr(runtime,'os',SimpleNamespace(name='nt',environ=dict(CUDA_VISIBLE_DEVICES='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1'),path=os.path))
    monkeypatch.setattr(runtime,'sys',SimpleNamespace(executable=cfg['producer']['python'],version='3.12.14 synthetic'))
    monkeypatch.setattr(socket,'gethostname',lambda:'D-26-09')
    monkeypatch.setattr(runtime.subprocess,'check_output',lambda *a,**k:'ad\\xw436\n')
    runtime.production_environment(cfg)
    runtime.os.environ['CUDA_VISIBLE_DEVICES']='0'
    with pytest.raises(PermissionError,match='environment'):runtime.production_environment(cfg)
    runtime.os.environ['CUDA_VISIBLE_DEVICES']='1';runtime.sys.version='3.12.2'
    with pytest.raises(PermissionError,match='runtime'):runtime.production_environment(cfg)

def test_descendant_RSS_accounting(monkeypatch):
    import sys
    child=SimpleNamespace(memory_info=lambda:SimpleNamespace(rss=200,peak_wset=300))
    fake=SimpleNamespace(Process=lambda:SimpleNamespace(children=lambda recursive:[child]),NoSuchProcess=RuntimeError)
    monkeypatch.setitem(sys.modules,'psutil',fake)
    assert r.runtime.aggregate_memory(lambda:100)==400

def desktop_xml(path=r'C:\Windows\System32\dwm.exe',kind='C+G',util='0 %',uuid='fixed',process=True):
    from xml.sax.saxutils import escape
    row=f'<process_info><pid>42</pid><type>{escape(kind)}</type><process_name>{escape(path)}</process_name></process_info>' if process else ''
    return f'<nvidia_smi_log><gpu><uuid>{uuid}</uuid><driver_model><current_dm>WDDM</current_dm></driver_model><utilization><gpu_util>{util}</gpu_util></utilization><processes>{row}</processes></gpu></nvidia_smi_log>'

def desktop_lock():return dict(gpu_uuid='fixed',maximum_sampled_GPU_utilization_percent=0,approved_desktop_executables={r'C:\Windows\System32\dwm.exe':'digest'})

def test_WDDM_exact_desktop_inventory_and_receipt():
    calls=[]
    def digest(p):calls.append(p);return 'digest'
    out=r.runtime.desktop_inventory(desktop_xml(),desktop_lock(),digest)
    assert out['processes'][0]['pid']==42 and out['processes'][0]['sha256']=='digest' and len(calls)==1
    assert r.runtime.desktop_inventory(desktop_xml(process=False),desktop_lock(),digest)['processes']==[]

@pytest.mark.parametrize('change',[dict(path=r'C:\Temp\dwm.exe'),dict(path=r'C:\Windows\System32\python.exe'),dict(kind='C'),dict(kind='G'),dict(kind=''),dict(util='1 %'),dict(util='N/A'),dict(util='nan %'),dict(uuid='other')])
def test_WDDM_unknown_compute_paths_types_utilization_and_device_stop(change):
    with pytest.raises((ValueError,RuntimeError)):r.runtime.desktop_inventory(desktop_xml(**change),desktop_lock(),lambda p:'digest')

def test_WDDM_changed_executable_and_unreadable_identity_stop():
    with pytest.raises(ValueError,match='identity'):r.runtime.desktop_inventory(desktop_xml(),desktop_lock(),lambda p:'changed')
    def denied(p):raise PermissionError('file unreadable')
    with pytest.raises(PermissionError):r.runtime.desktop_inventory(desktop_xml(),desktop_lock(),denied)

@pytest.mark.parametrize('replace',[('<processes>','<missing>'),('<current_dm>WDDM</current_dm>','<current_dm>TCC</current_dm>')])
def test_WDDM_missing_process_inventory_or_changed_driver_stop(replace):
    xml=desktop_xml().replace(*replace)
    if replace[0]=='<processes>':xml=xml.replace('</processes>','</missing>')
    with pytest.raises(ValueError):r.runtime.desktop_inventory(xml,desktop_lock(),lambda p:'digest')
