import copy, importlib.util, json, os
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('e012_test',ROOT/'scripts/pavetrack_positive_evidence/run.py');r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
CFG=r.read(ROOT/r.CONTRACT/'run_config.json')
def dump(p,v): p.write_text(json.dumps(v),encoding='utf8')
def guard(cfg=None):return r.Guard(cfg or CFG,memory=lambda:100)
def fixture(tmp):
    cfg=copy.deepcopy(CFG);cache=tmp/'S01-E007-R001';cache.mkdir();records=[];old=[];pairs=[]
    for i,loc in enumerate(cfg['locations']):
        im='reid-'+loc+'.jpg';rec=dict(image_id=im,reid=loc,split='train',width=100,height=100,crack_boxes_xyxy=[[50,50,70,70]],prepared_image='C:/images/'+im,prepared_image_sha256='a'*64);records.append(rec)
        # Sparse stable source parent keys intentionally differ from local indices.
        row=dict(image_id=im,reid=loc,parent_id=100+i*2,candidate_id='o:'+str(100+i*2),kind='original',box_xyxy=[0,0,10,10],proposer_confidence=.25,probability=.25,score=.25,E003_score=.25)
        new=dict(row,kind='correction',candidate_id='c:'+str(row['parent_id']),original_box_xyxy=row['box_xyxy'],box_xyxy=[50,50,70,70]);old.append(row);pairs.extend([row,new])
    excluded=dict(image_id='excluded.jpg',reid='99999',split='validation',crack_boxes_xyxy=['DO_NOT_DESERIALIZE'],width=1,height=1)
    meta=tmp/'meta.json';dump(meta,dict(records=[excluded]+records))
    bank=dict(original_rows=[dict(excluded,parent_id=1)]+old,bank=[dict(excluded,parent_id=1)]+pairs,targets={**{v['image_id']:v['crack_boxes_xyxy'] for v in records},'excluded.jpg':['DO_NOT_DESERIALIZE']},image_locations={**{v['image_id']:v['reid'] for v in records},'excluded.jpg':'99999'})
    dump(cache/'train_bank.json',bank)
    heads=[dict(fold=i,held_locations=g,fit_locations=[v for v in cfg['locations'] if v not in g],fit_ids=[i]) for i,g in enumerate(cfg['held_groups'])]+[dict(fold=3,held_locations=['353','1459','2028','5982'],fit_locations=cfg['locations'])]
    dump(cache/'correction_heads.json',dict(models=heads));dump(cache/'label_audit.json',dict(excluded='DO_NOT_DESERIALIZE'))
    files={v:r.sha(cache/v) for v in ['train_bank.json','correction_heads.json','label_audit.json']};files['paired_train_features.npz']='not-opened'
    dump(cache/'feature_receipt.json',dict(protocol='S01-E007-v1',files=files))
    lock=dict(source_run=cache.name,source_receipt_sha256=r.sha(cache/'feature_receipt.json'),metadata_sha256=r.sha(meta),frozen_E003_ranker_sha256='b'*64)
    return cfg,cache,meta,lock

def test_scoped_parser_excludes_payloads_and_preserves_sparse_source_keys(tmp_path,monkeypatch):
    cfg,cache,meta,lock=fixture(tmp_path);real=r.scoped.json.loads
    def loads(value,*a,**k):
        assert 'DO_NOT_DESERIALIZE' not in (value.decode() if isinstance(value,bytes) else value)
        return real(value,*a,**k)
    monkeypatch.setattr(r.scoped.json,'loads',loads)
    records=r.metadata(meta,cfg,lock,guard());data=r.load_bank(cache,records,cfg,lock,guard())
    assert len(records)==12 and len(data['mapping'])==12
    assert data['mapping'][0]['source_parent_key']==100
    assert data['mapping'][0]['corrector_fold']==0
    assert 'excluded.jpg' not in data['targets']

@pytest.mark.parametrize('problem',['receipt','head','pair','geometry','parent_cap','metadata'])
def test_fail_closed_identity_and_mapping(tmp_path,problem):
    cfg,cache,meta,lock=fixture(tmp_path)
    if problem=='receipt': lock['source_receipt_sha256']='bad'
    elif problem=='metadata': lock['metadata_sha256']='bad'
    else:
        if problem=='head':
            p=cache/'correction_heads.json';v=r.read(p);v['models'][0]['fit_locations']=cfg['locations'];dump(p,v)
        else:
            p=cache/'train_bank.json';v=r.read(p)
            if problem=='pair':v['bank'][2]['original_box_xyxy']=[1,1,2,2]
            if problem=='geometry':v['bank'][2]['box_xyxy']=[-1,0,2,2]
            if problem=='parent_cap':v['bank']=v['bank'][:-2]
            dump(p,v)
        receipt=r.read(cache/'feature_receipt.json');receipt['files'][p.name]=r.sha(p);dump(cache/'feature_receipt.json',receipt);lock['source_receipt_sha256']=r.sha(cache/'feature_receipt.json')
    with pytest.raises(ValueError):
        records=r.metadata(meta,cfg,lock,guard());r.load_bank(cache,records,cfg,lock,guard())

def test_missing_scores_never_use_inherited_probability(tmp_path):
    cfg,cache,meta,lock=fixture(tmp_path);rec=r.metadata(meta,cfg,lock,guard());data=r.load_bank(cache,rec,cfg,lock,guard());missing=r.missing_scores(data,lock)
    assert all(v['score'] is None and v['U'] is None for v in missing)
    assert len(missing)==12 and all(v['prepared_image_sha256']=='a'*64 for v in missing)
    assert missing[0]['crop_box_xyxy']==list(r.e11.e8.m.box.context_box([50,50,70,70],rec[missing[0]['image_id']],.1))
    geo=r.geometry(data,cfg,guard());assert len(geo['new_geometry_GT'])==12 and geo['original_geometry_GT']==0

def test_dedup_scope_and_distributed_decision():
    rows=[]
    for i,g in enumerate(CFG['held_groups']):
        loc=g[0];rows.extend([dict(location=loc,U=1,new_identities=[[loc+'.jpg',0]])]*3)
    t=r.support_table(rows,'full12',CFG['locations']);assert t['positive_pairs']==9 and t['positive_GT_count']==3
    fit=[dict(positive_pairs=1,zero_pairs=1,negative_pairs=0) for _ in range(3)]
    assert r.decision(rows,fit,CFG,True)['status']=='qualified_distributed_support'
    assert r.decision(rows[:-3],fit,CFG,True)['status']=='partial_useful_support'
    assert r.decision([],fit,CFG,True)['status']=='no_qualified_positive'
    assert r.decision(rows,fit,CFG,False)['status']=='incomplete_scores'
    fit[0]['positive_pairs']=0
    assert not r.decision(rows,fit,CFG,True)['L2']

@pytest.mark.parametrize('cap',['memory','time','labels','images','corrections'])
def test_resource_stops_without_truncation(tmp_path,cap):
    cfg,cache,meta,lock=fixture(tmp_path)
    if cap=='memory':
        g=r.Guard(cfg,memory=lambda:cfg['stage_A']['peak_RSS_bytes']+1)
        with pytest.raises(RuntimeError,match='RSS_CAP'):g.check()
    elif cap=='time':
        times=iter([0,3601]);g=r.Guard(cfg,clock=lambda:next(times),memory=lambda:0)
        with pytest.raises(RuntimeError,match='WALL_CAP'):g.check()
    elif cap=='labels':
        cfg['stage_A']['max_singleton_evaluations']=0
        with pytest.raises(RuntimeError,match='SINGLETON_CAP'):guard(cfg).label()
    elif cap=='images':
        cfg['stage_A']['max_images']=11
        with pytest.raises(RuntimeError,match='IMAGE_CAP'):r.metadata(meta,cfg,lock,guard(cfg))
    else:
        cfg['stage_A']['max_corrections']=11;rec=r.metadata(meta,cfg,lock,guard(cfg))
        with pytest.raises(RuntimeError,match='CORRECTION_CAP'):r.load_bank(cache,rec,cfg,lock,guard(cfg))

def test_end_to_end_synthetic_inventory_not_a_detector_result(tmp_path,monkeypatch):
    cfg,cache,meta,lock=fixture(tmp_path);run=tmp_path/'out';run.mkdir();a=SimpleNamespace(cache=cache,metadata=meta,run=run)
    # Fail immediately if any forbidden fallback attempts a fit/model/image read.
    monkeypatch.setattr(r.e11,'fit_head',lambda *a,**k:pytest.fail('fit forbidden'))
    monkeypatch.setattr(r.e11.e8.m.base,'load_models',lambda *a,**k:pytest.fail('models forbidden'))
    expected=r.execute(a,cfg,lock,guard());launch={'synthetic_only':True};dump(run/'launch.json',launch);expected['launch.json']=launch;q=r.read(run/'qualification.json')
    assert q['status']=='incomplete_scores' and q['actual_detector_retention'] is None and not q['L2']
    assert all(t['positive_pairs'] is None and t['missing_score_pairs']==4 for t in q['held_support'])
    assert len(list((run/'analysis').glob('*.png')))==3
    assert '12 corrected crops' in (run/'stage_B_request.md').read_text()
    dump(run/'output_receipt.json',dict(protocol=r.PROTOCOL,fresh_access=False,files={str(p.relative_to(run)):r.sha(p) for p in run.rglob('*') if p.is_file()}))
    assert r.verify(run,cfg,guard(),expected)
    (run/'qualification.json').write_text('{}')
    with pytest.raises(ValueError,match='identity mismatch'):r.verify(run,cfg,guard(),expected)

def test_cursor_chunk_boundary_escaping_and_no_gt_deserialization(tmp_path):
    p=tmp_path/'long.json';record=dict(reid='24',image_id='a',value='x'*65540+'\\\"');dump(p,dict(records=[dict(reid='999',GT='excluded'),record]))
    c=r.scoped.Cursor(p)
    try:
        spans=dict(c.fields());rows=list(c.selected_rows(spans['records'],{'24'}));assert rows==[record]
    finally:c.close()

def test_pixel_guard_and_producer_environment():
    with pytest.raises(PermissionError):r.e11.pixel_guard('open',('/tmp/example.jpg','r',0))
    with pytest.raises(PermissionError):r.e11.e9.require_producer(host='Mac')

def test_cli_main_synthetic_complete_budget_and_status(tmp_path):
    # A separate interpreter contains the audit hook; no real producer/data used.
    import subprocess,sys
    code='''import importlib.util,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('f',Path('tests/pavetrack_positive_evidence/test_positive_evidence.py'));f=importlib.util.module_from_spec(s);s.loader.exec_module(f)
t=Path(sys.argv[1]);cfg,cache,meta,lock=f.fixture(t);config=t/'config.json';lk=t/'lock.json';f.dump(config,cfg);f.dump(lk,lock)
f.r.e11.require_producer=lambda:None
f.r.contract=lambda *a:(cfg,lock)
sys.argv=['run.py','--config',str(config),'--lock',str(lk),'--cache',str(cache),'--metadata',str(meta),'--run',str(t/'S01-E012-R002'),'--reviewed-commit','synthetic-only']
f.r.main()
'''
    v=subprocess.run([sys.executable,'-c',code,str(tmp_path)],cwd=ROOT,capture_output=True,text=True)
    assert v.returncode==0,v.stdout+v.stderr
    result=r.read(tmp_path/'S01-E012-R002/status.json');assert result['state']=='completed'
    assert result['resource']['model_fits']==result['resource']['new_inference']==result['resource']['singleton_evaluations']==0


def test_semantic_verification_rejects_self_rehashed_manifest_and_empty_receipt(tmp_path):
    cfg,cache,meta,lock=fixture(tmp_path);run=tmp_path/'output';run.mkdir()
    expected=r.execute(SimpleNamespace(cache=cache,metadata=meta,run=run),cfg,lock,guard());launch={'synthetic_only':True};dump(run/'launch.json',launch);expected['launch.json']=launch
    def receipt():
        dump(run/'output_receipt.json',dict(protocol=r.PROTOCOL,fresh_access=False,files={n:r.sha(run/n) for n in r.REQUIRED_FILES}))
    receipt();assert r.verify(run,cfg,guard(),expected)
    for mutation in ['crop','head','parent','score','U']:
        value=copy.deepcopy(expected['missing_scores_manifest.json']);row=value['rows'][0]
        key={'crop':'crop_box_xyxy','head':'corrector_fold','parent':'source_parent_key','score':'score','U':'U'}[mutation]
        row[key]=[0,0,1,1] if mutation=='crop' else 123
        dump(run/'missing_scores_manifest.json',value);receipt()
        with pytest.raises(ValueError,match='semantic mismatch'):r.verify(run,cfg,guard(),expected)
    dump(run/'missing_scores_manifest.json',expected['missing_scores_manifest.json']);receipt()
    dump(run/'output_receipt.json',dict(protocol=r.PROTOCOL,fresh_access=False,files={}))
    with pytest.raises(ValueError,match='exact output inventory'):r.verify(run,cfg,guard(),expected)


def test_windows_receipt_path_is_portable_and_backslash_rejected(tmp_path):
    from pathlib import PureWindowsPath
    assert PureWindowsPath('analysis/F00_support.png').as_posix()=='analysis/F00_support.png'
    dump(tmp_path/'output_receipt.json',dict(protocol=r.PROTOCOL,fresh_access=False,files={'analysis\\F00_support.png':'fake'}))
    with pytest.raises(ValueError,match='exact output inventory'):r.verify(tmp_path,CFG,guard(),{})

def fake_windows_api():
    def handle():return 1
    def memory(handle,counters,size):
        counters._obj.PeakWorkingSetSize=123456
        assert counters._obj.cb==size
        return 1
    return SimpleNamespace(GetCurrentProcess=handle),SimpleNamespace(GetProcessMemoryInfo=memory)

def test_windows_probe_10000_samples_constant_type_cache_and_exact_peak():
    import ctypes
    kernel,psapi=fake_windows_api();probe=r.mem.make_windows_probe(kernel,psapi)
    before=len(ctypes._pointer_type_cache);counter=probe.counter_type
    assert counter.PeakWorkingSetSize.offset==8
    assert ctypes.sizeof(counter)==8+8*ctypes.sizeof(ctypes.c_size_t)
    for _ in range(10000): assert probe()==123456
    assert len(ctypes._pointer_type_cache)==before

def test_windows_api_binding_singleton_and_failure_is_not_zero(monkeypatch):
    import ctypes
    kernel,psapi=fake_windows_api();calls=[]
    def dll(name,**kwargs):calls.append(name);return kernel if name=='kernel32' else psapi
    monkeypatch.setattr(ctypes,'WinDLL',dll,raising=False);r.mem.windows_probe.cache_clear()
    first=r.mem.windows_probe();second=r.mem.windows_probe()
    assert first is second and calls==['kernel32','psapi'] and first()==123456
    def fail(*a):return 0
    psapi.GetProcessMemoryInfo=fail
    with pytest.raises(OSError,match='measure peak RSS'):first()
    r.mem.windows_probe.cache_clear()

def test_resource_monitor_records_cap_without_relaxing_budget(tmp_path,monkeypatch):
    import time
    cfg=copy.deepcopy(CFG);cfg['stage_A']['peak_RSS_bytes']=100
    g=r.Guard(cfg,memory=lambda:101);exits=[]
    def stop(code):exits.append(code)
    monkeypatch.setattr(r.os,'_exit',stop)
    with g.monitor(tmp_path):
        deadline=time.monotonic()+2
        while not (tmp_path/'status.json').exists() and time.monotonic()<deadline:time.sleep(.01)
    status=r.read(tmp_path/'status.json')
    assert status['state']=='stopped_resource' and status['peak_rss_bytes']==101 and exits==[71]
