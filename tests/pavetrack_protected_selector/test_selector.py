import copy,hashlib,importlib.util,json,math,zipfile
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('e013_test',ROOT/'scripts/pavetrack_protected_selector/run.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r);c=r.c
CFG=c.read(ROOT/c.CONTRACT/'run_config.json')
def guard(cfg=CFG):return r.Guard(cfg,memory=lambda:100)
def fixture():
    originals=[];manifest=[];probabilities=[];targets={};locations={};records={}
    positives={'514','1577','728','4494','2027'}
    for loc in CFG['locations']:
        for k in range(3 if loc=='514' else 1):
            im=f'{loc}-{k}';locations[im]=loc;positive=loc in positives;targets[im]=[[0,0,10,10]]+([[30,0,40,10]] if positive else []);records[im]=dict(image_id=im,reid=loc,split='train',width=100,height=100,crack_boxes_xyxy=targets[im])
            for j,(score,box) in enumerate([(.4,[0,0,10,10]),(.9,[70,70,80,80]),(.1,[90,90,100,100])]):
                pid=100+len(originals)*7;old=dict(parent_id=pid,candidate_id='o:'+str(pid),image_id=im,reid=loc,kind='original',box_xyxy=box,proposer_confidence=1.,probability=score**2,score=score,E003_score=score);originals.append(old)
                if j==0:
                    manifest.append(dict(source_parent_key=pid,image_id=im,location=loc,original_box_xyxy=box,corrected_box_xyxy=[30,0,40,10],corrector_fold=c.group_of(loc,CFG),width=100,height=100));probabilities.append((.85 if positive else .5)**2)
    candidates=c.features(originals,manifest,probabilities,CFG);labels=[]
    for k,g in enumerate(CFG['held_groups']):
        locs=[loc for loc in CFG['locations'] if loc not in g];rows=[]
        for x in candidates:
            if x['location'] not in locs:continue
            pos=x['location'] in positives;rows.append(dict(index=x['index'],parent_id=x['parent_id'],image_id=x['image_id'],location=x['location'],new=int(pos),lost=0,FP=int(not pos),U=1 if pos else -1,new_identities=[[x['image_id'],1]] if pos else [],lost_identities=[]))
        labels.append(dict(scope='fit8_fold_'+str(k),locations=locs,rows=rows))
    return dict(originals=originals,candidates=candidates,image_locations=locations,labels=labels,manifest=manifest,probabilities=probabilities,records=records),targets

def test_feature_only_probability_gain_and_GT_poison_invariance():
    d,t=fixture();before=c.features(d['originals'],d['manifest'],d['probabilities'],CFG);manifest=copy.deepcopy(d['manifest'])
    for x in manifest:x.update(GT=[[9,9,99,99]],U=999,score=999,oracle=True)
    assert before==c.features(d['originals'],manifest,d['probabilities'],CFG)
    assert all(math.isfinite(x['x']) for x in before) and all(x['eligible'] for x in before)
    bad=list(d['probabilities']);bad[0]=float('nan')
    with pytest.raises(ValueError):c.features(d['originals'],manifest,bad,CFG)

def test_policy_exact_cap_order_and_abstention_originals_immutable():
    d,t=fixture();old=copy.deepcopy(d['originals']);added=c.policy(d['candidates'],2.,CFG['locations'],CFG)
    assert len(added)==6 and d['originals']==old and c.policy(d['candidates'],'abstain',CFG['locations'],CFG)==[]
    assert len({x['image_id'] for x in added})==len(added)
    assert all(sum(c.group_of(x['reid'],CFG)==k for x in added)<=3 for k in range(3))
    assert added==sorted(added,key=lambda x:x['parent_id'])
    with pytest.raises(ValueError):c.policy(d['candidates'],3.14159,CFG['locations'],CFG)

def test_duplicate_rejection_does_not_consume_capacity():
    d,t=fixture();candidates=copy.deepcopy(d['candidates']);first=candidates[0];dup=copy.deepcopy(first);dup['parent_id']=99999;dup['row']=dict(dup['row'],parent_id=99999);dup['row']['score']-=.00001;candidates.insert(1,dup)
    expected=c.policy(d['candidates'],0.,CFG['locations'],CFG)
    assert c.policy(candidates,0.,CFG['locations'],CFG)==expected

def summary(tau,net=1,fp=0,n=1,ret=1,delta=.1):return dict(threshold=tau,comparison=dict(net_GT=net,added_FP=fp,appended=n,retention=ret,macro_delta=delta))
@pytest.mark.parametrize('table,expected',[
    ([summary(0,ret=.99),summary(.5,net=0)],'abstain'),
    ([summary(0),summary(2)],2),([summary(0,fp=1),summary(.5,fp=0)],.5),
    ([summary(0,n=2),summary(.5,n=1)],.5),([summary(0,net=2),summary(.5,net=1)],0),
    ([summary(0,delta=0)],'abstain')])
def test_joint_objective_ties_and_protected_abstention(table,expected):assert c.choose(table)==expected

def test_actual_synthetic_joint_objective_and_canonical_added_FP(monkeypatch):
    d,t=fixture();own=c.scoped(d['originals'],d['candidates'],t,d['image_locations'],CFG['locations']);ref=c.baseline(own);good=c.policy(d['candidates'],2.,CFG['locations'],CFG);positive=c.compare(own,good,ref)
    assert positive['retention']==1 and positive['new_GT']==positive['net_GT']==6 and positive['added_FP']==0
    negative=c.compare(own,c.policy(d['candidates'],0.,CFG['locations'],CFG),ref)
    assert negative['added_FP']==0 and negative['lost_old']>0  # rejected FP tie group still cuts off old TP
    altered=copy.deepcopy(d['candidates'])
    for x in altered:
        if x['location'] not in {'514','1577','728','4494','2027'}:x['row']['score']=.95
    actual_fp=c.compare(own,c.policy(altered,0.,CFG['locations'],CFG),ref)
    assert actual_fp['added_FP']>0 and actual_fp['lost_old']>0
    monkeypatch.setattr(c,'require_producer',lambda cfg:None);fit=[x for x in CFG['locations'] if x not in CFG['held_groups'][0]];scope=c.scoped(d['originals'],d['candidates'],t,d['image_locations'],fit);g=guard();model=c.calibrate(scope,CFG,g)
    assert model['threshold']==2 and g.counts['threshold_fits']==1 and g.counts['calibration_policy_comparisons']==7

def test_real_calibrator_denied_on_Mac_before_metrics(monkeypatch):
    monkeypatch.setattr(c,'baseline',lambda *a:pytest.fail('baseline must not run'))
    with pytest.raises(PermissionError):c.calibrate({},CFG,guard())

def recording_emitter(run):
    expected={}
    def emit(name,value):expected[name]=copy.deepcopy(value);c.write(run/name,value)
    return expected,emit

def test_main_fits_freeze_then_jackknife_and_fold_GT_isolation(tmp_path,monkeypatch):
    monkeypatch.setattr(c,'require_producer',lambda cfg:None);d,t=fixture();saved=copy.deepcopy(d);cfg=copy.deepcopy(CFG);cfg['input_counts']['images']=len(t);g=guard();expected,emit=recording_emitter(tmp_path);models,support,added=r.fit_and_freeze(d,t,tmp_path,cfg,g,emit)
    assert [m['threshold'] for m in models]==[2,2,2] and len(added)==6 and d==saved
    assert g.counts['threshold_fits']==13 and g.counts['calibration_policy_comparisons']==91
    assert [s['positive_GT_count'] for s in support]==[3,5,6]
    poisoned=copy.deepcopy(t)
    for im,loc in d['image_locations'].items():
        if loc in cfg['held_groups'][0]:poisoned[im]=[]
    other=tmp_path/'poison';other.mkdir();ex2,emit2=recording_emitter(other);models2,_,_=r.fit_and_freeze(d,poisoned,other,cfg,guard(),emit2)
    assert models2[0]==models[0] and ex2['OOF_predictions.json']['folds'][0]==expected['OOF_predictions.json']['folds'][0]

def test_diagnostic_payload_mutation_cannot_change_main_predictions(tmp_path):
    d,t=fixture();saved=copy.deepcopy(d);expected,emit=recording_emitter(tmp_path)
    def fake(own,cfg,g):
        if len(own['locations'])<8:
            for row in own['originals']:row['score']=-999
            for row in own['candidates']:row['row']['score']=-999
            return dict(threshold='abstain',abstained=True)
        return dict(threshold=2.,abstained=False)
    models,_,added=r.fit_and_freeze(d,t,tmp_path,CFG,guard(),emit,calibrator=fake)
    assert d==saved and len(added)==6 and all(row['score']>0 for row in added) and [m['threshold'] for m in models]==[2,2,2]

@pytest.mark.parametrize('kind',['scope','incomplete','identity','algebra'])
def test_support_lineage_rejects_cross_scope_and_tampering(kind):
    d,t=fixture();p=copy.deepcopy(d['labels'][0])
    if kind=='scope':p['locations']=CFG['held_groups'][0]
    elif kind=='incomplete':p['rows'].pop()
    elif kind=='identity':p['rows'][0]['parent_id']+=1
    else:p['rows'][0]['U']=999
    with pytest.raises((ValueError,KeyError)):c.support_labels(p,d['candidates'],[x for x in CFG['locations'] if x not in CFG['held_groups'][0]])

def test_evaluation_requires_frozen_predictions_before_held_GT(tmp_path,monkeypatch):
    d,t=fixture();monkeypatch.setattr(c,'baseline',lambda *a:pytest.fail('no evaluation before freeze'))
    with pytest.raises(FileNotFoundError):r.evaluate(d,t,[],tmp_path,CFG,{'source_B12_hits':14},guard(),lambda *a:None)

@pytest.mark.parametrize('kind',['RSS','WALL','COUNT'])
def test_resource_stops(kind):
    if kind=='RSS':g=r.Guard(CFG,memory=lambda:2**33)
    elif kind=='WALL':g=r.Guard(CFG,start=0,clock=lambda:4000,memory=lambda:0)
    else:g=guard();g.counts['threshold_fits']=13
    with pytest.raises(RuntimeError):g.take('threshold_fits') if kind=='COUNT' else g.check()

def test_oracle_json_fields_and_correction_tail_not_decoded(tmp_path,monkeypatch):
    d,t=fixture();path=tmp_path/'oracle.json';q=dict(held_support='SEALED_PAYLOAD',joint=dict(new_identities='SEALED_PAYLOAD',rows=d['originals']+[dict(kind='correction',GT='SEALED_PAYLOAD')]),full12_U='SEALED_PAYLOAD');path.write_text(json.dumps(q));original=json.loads
    def checked(raw,*a,**kw):
        text=raw.decode() if isinstance(raw,bytes) else raw
        if 'SEALED_PAYLOAD' in text:pytest.fail('oracle payload decoded')
        return original(raw,*a,**kw)
    monkeypatch.setattr(json,'loads',checked);assert r.inputs.originals_from_file(path,len(d['originals']),c.e12.a.scoped.Cursor)==d['originals']

def test_complete_fake_pipeline_analysis_and_semantic_tamper(tmp_path,monkeypatch):
    d,t=fixture();cfg=copy.deepcopy(CFG);cfg['input_counts']['images']=len(t);run=tmp_path/'run';run.mkdir();snapshot=run/'input_snapshot';snapshot.mkdir();raw=dict(status='reference_only',joint=dict(retained_old=14,net_targets=7),held_support=[]);c.write(snapshot/'qualification.json',raw);d['snapshot']=snapshot;lock=dict(original_rows_digest=c.digest(d['originals']),source_B12_hits=14,source_zip_sha256='synthetic',source_files={'qualification.json':c.sha(snapshot/'qualification.json')})
    monkeypatch.setattr(r.inputs,'load',lambda *a:d);monkeypatch.setattr(r.inputs,'metadata',lambda *a:d['records']);monkeypatch.setattr(c,'require_producer',lambda cfg:None);monkeypatch.setattr(r.sys,'addaudithook',lambda hook:None)
    args=SimpleNamespace(source=tmp_path/'source.zip',metadata=tmp_path/'meta.json',run=run);launch={'synthetic':True};c.write(run/'launch.json',launch);g=guard();result=r.execute(args,cfg,lock,g,launch)
    assert result['primary_pass'] and result['comparison']['net_GT']==6 and result['comparison']['retention']==1 and len(list((run/'analysis').glob('*.png')))==3
    receipt=c.read(run/'output_receipt.json');expected={n:c.read(run/n) for n in receipt['files'] if n.endswith('.json') and not n.startswith('input_snapshot/')}
    bad=c.read(run/'result.json');bad['comparison']['net_GT']=999;c.write(run/'result.json',bad);receipt['files']['result.json']=c.sha(run/'result.json')
    with pytest.raises(ValueError,match='semantic'):r.verify(run,expected,receipt,lock['source_files'])

def test_pixel_reader_blocks_dataset_images():
    gate=c.e12.PixelGate([])
    with pytest.raises(PermissionError):gate('open',('/sealed/new_location.jpg','r',0))

def zip_fixture(tmp_path):
    d,t=fixture();original=d['originals'];members={
        'qualification.json':dict(ignored_oracle='DO_NOT_USE',joint=dict(rows=original+[dict(kind='correction',oracle=True)])),
        'source_receipt.json':dict(original_rows_digest=c.digest(original)),
        'scoring_receipt.json':dict(rows=len(d['manifest']),CPU_head_passes=2),
        'launch.json':dict(reviewed_commit='synthetic'),
        'candidate_identity.json':dict(rows=d['manifest']),
        'scores.json':dict(source_keys=[v['source_parent_key'] for v in d['manifest']],probabilities=d['probabilities'])}
    members.update({f'fit8_fold_{k}.json':v for k,v in enumerate(d['labels'])});raw={n:json.dumps(v).encode() for n,v in members.items()};zip_path=tmp_path/'source.zip'
    with zipfile.ZipFile(zip_path,'w') as src:
        for n,b in raw.items():src.writestr(n,b)
        src.writestr('pooled_features.npy',b'NEVER_DECOMPRESS')
    cfg=copy.deepcopy(CFG);cfg['input_counts']['images']=len(t)
    lock=dict(source_zip_sha256=c.sha(zip_path),source_files={n:hashlib.sha256(v).hexdigest() for n,v in raw.items()},original_rows_digest=c.digest(original),source_original_count=len(original),source_correction_count=len(d['manifest']),source_eligible_count=len(d['manifest']),source_commit='synthetic')
    run=tmp_path/'run';run.mkdir();return d,t,cfg,lock,run,zip_path

def test_pinned_loader_complete_identity_without_opening_pooled_member(tmp_path,monkeypatch):
    d,t,cfg,lock,run,z=zip_fixture(tmp_path);original=zipfile.ZipFile.read;opened=[]
    def checked(self,name,*a,**kw):
        opened.append(name)
        if name=='pooled_features.npy':pytest.fail('pooled feature opened')
        return original(self,name,*a,**kw)
    monkeypatch.setattr(zipfile.ZipFile,'read',checked);loaded=r.inputs.load(z,run,cfg,lock,guard(),c)
    assert loaded['originals']==d['originals'] and loaded['candidates']==d['candidates'] and loaded['labels']==d['labels']
    assert set(opened)==set(lock['source_files'])

@pytest.mark.parametrize('kind',['zip','member','original','score','eligibility'])
def test_loader_rejects_source_tampering(tmp_path,kind):
    d,t,cfg,lock,run,z=zip_fixture(tmp_path)
    if kind=='zip':lock['source_zip_sha256']='bad'
    elif kind=='member':lock['source_files']['scores.json']='bad'
    elif kind=='original':lock['original_rows_digest']='bad'
    elif kind=='score':lock['source_correction_count']+=1
    else:lock['source_eligible_count']+=1
    with pytest.raises((ValueError,AssertionError)):r.inputs.load(z,run,cfg,lock,guard(),c)
