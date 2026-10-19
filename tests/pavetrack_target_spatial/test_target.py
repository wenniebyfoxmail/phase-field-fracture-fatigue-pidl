import importlib.util,json,sys,copy
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


g=load('target_geo','scripts/pavetrack_target_spatial/geometry.py')
e=load('target_eval','scripts/pavetrack_target_spatial/evaluate.py')
r=load('target_run','scripts/pavetrack_target_spatial/run.py')


def fixture():
    rows=[];images={};rgbs={};cache=[];masks=[]
    for site in ['24','1638','2027']:
        for j in range(3):
            i=len(rows);im=f'{site}-{j}.png';a=np.zeros((3,64,64),np.uint8);y=4+j*12;x=6+j*14;a[0,y:y+4,x:x+4]=255
            rgbs[im]=a;cache.append(np.repeat(np.repeat(a,2,axis=1),2,axis=2));images[im]=dict(width=64,height=64,location=site,image_id=im)
            rows.append(dict(index=i,image_id=im,location=site,context=[0,0,64,64]));masks.append(g.reference(a[0]//255,[0,0,64,64]))
    scope=dict(rows=rows,images=images,cases=[0,2,3,5,6,8],synthetic=True)
    cfg=json.loads((ROOT/'docs/research/S01/S01-E028/run_config.json').read_text());cfg['counts']['native_tiles']=9;cfg['counts']['cached_forwards']=9;cfg['budget']['source_image_decodes']=9
    refs={k:np.stack([x[j] for x in masks]) for j,k in enumerate(['center','any','area'])}
    return scope,np.stack(cache),rgbs,refs,cfg


def test_thin_line_observation_mismatch_without_threshold_change():
    a=np.zeros((128,128),np.float32);a[0,0]=.9
    mean,max_=g.reduce(a,[0,0,128,128]);center,any_,area=g.reference((a>0).astype(np.uint8),[0,0,128,128])
    assert mean[0,0]<.5<max_[0,0];assert center.sum()==0 and any_.sum()==1;assert area[0,0]==1/16


def test_narrow_fractional_bins_and_conservation():
    field=np.arange(14,dtype=np.float32).reshape(2,7)/14
    mean,max_=g.reduce(field,[0,0,7,2]);assert mean.shape==(32,32) and np.isfinite(mean).all();assert np.all(max_>=mean-1e-7)
    assert abs(float(mean.mean())-float(field.mean()))<1e-7
    mask=np.ones((2,7),np.uint8);assert g.reference(mask,[0,0,7,2])[1].all()


def test_aligned_reduce_matches_old_mean4_and_max4():
    a=np.random.default_rng(1).random((128,128),dtype=np.float32);mean,max_=g.reduce(a,[0,0,128,128])
    np.testing.assert_allclose(mean,a.reshape(32,4,32,4).mean((1,3)),atol=1e-7)
    np.testing.assert_array_equal(max_,a.reshape(32,4,32,4).max((1,3)))


def test_reflection_halo_stitch_native_coordinate_identity():
    a=np.random.default_rng(2).integers(0,256,(3,271,519),dtype=np.uint8);calls=[]
    def predict(x):assert x.shape==(3,512,512);return x[0].astype(np.float32)/255
    actual=g.native_predict(a,predict,calls.append);np.testing.assert_array_equal(actual,a[0].astype(np.float32)/255);assert len(calls)==6
    np.testing.assert_array_equal(g.reflect_indices(-2,8,4),[2,1,0,1,2,3,2,1])


@pytest.mark.parametrize('bad',[np.full((3,3),np.nan,np.float32),np.ones((3,3),np.float64),np.full((3,3),1.1,np.float32)])
def test_invalid_predictions_rejected(bad):
    with pytest.raises(ValueError):g.validate_probability(bad,(3,3))


def test_shared_support_including_empty_center_not_reselected():
    scope,_,_,refs,cfg=fixture();p=refs['any'].astype(np.float32)
    empty=np.zeros_like(refs['center']);x=e.one_combination(p,empty,refs['any'],scope['rows'],cfg['sites'])
    assert sum(v['common_FG'] for v in x['contexts'])==9
    assert all(v['common_contexts']==1 for v in x['images']);assert all(v['gain']<=0 for v in x['sites'])


def test_pair_admission_and_no_detection_metrics():
    scope,_,_,refs,cfg=fixture();maps={k:refs['any'].astype(np.float32).copy() for k in ['cached_mean','cached_max','native_mean','native_max']}
    maps['native_max'][6:]=0;res=e.compare(maps,refs,scope['rows'],cfg)
    assert res['primary_pass'] and [p['qualified'] for p in res['pairs']]==[False,False,True]
    assert res['OOF'] is res['retention'] is res['net_GT'] is None and res['selector'] is False
    assert res['combinations']['cached_max_any']['sites'][2]['qualified']


def test_other_component_never_rescues_primary():
    scope,_,_,refs,cfg=fixture();maps={k:refs['any'].astype(np.float32).copy() for k in ['cached_mean','cached_max','native_mean','native_max']};maps['native_max'][:]=0
    res=e.compare(maps,refs,scope['rows'],cfg);assert not res['primary_pass'];assert all(v['qualified'] for v in res['combinations']['cached_max_any']['sites'])


def test_loo_excludes_current_image_and_uses_all_contexts():
    scope,_,_,refs,cfg=fixture();rows=scope['rows'][:3];y=refs['any'][:3];p=y.astype(np.float32)
    # Duplicating a background context must affect its image prior, not site weighting.
    rows=rows+[dict(rows[0],index=99)];y=np.concatenate([y,np.zeros_like(y[:1])]);p=np.concatenate([p,np.zeros_like(p[:1])]);common=np.ones_like(y)
    res=e.one_combination(p,y,common,rows,['24']);rr=next(v for v in res['contexts'] if v['index']==1)
    expected=(y[[0,3]].mean(0)+y[2])/2
    assert rr['baseline_Dice']['loo_image_position']==e.dice(expected,y[1])
    image0=next(v for v in res['images'] if v['image_id']==rows[0]['image_id']);assert image0['contexts']==2
    assert res['sites'][0]['gain']==pytest.approx(np.mean([x['gain'] for x in res['images']]))


def test_missing_reference_support_is_inconclusive_not_zero():
    scope,_,_,refs,cfg=fixture();p=np.zeros_like(refs['any'],dtype=np.float32);refs['any'][6:]=0
    result=e.one_combination(p,refs['any'],refs['any'],scope['rows'],cfg['sites']);assert result['sites'][2]['gain'] is None and result['sites'][2]['status']=='inconclusive'


def test_reference_barrier_precedes_loader_and_native_io(tmp_path):
    scope,cache,rgbs,refs,cfg=fixture();called=[]
    with pytest.raises(PermissionError):r.finish_evaluation(scope,tmp_path,cfg,lambda:called.append(True))
    with pytest.raises(PermissionError):r.load_references(tmp_path,scope,tmp_path)
    assert not called


def synthetic(tmp_path):
    scope,cache,rgbs,refs,cfg=fixture();guard=r.Guard(cfg,tmp_path,memory=lambda:0);events=[]
    class Engine:
        def predict(self,a):events.append(a.shape);return a[0].astype(np.float32)/255
        def verify_unchanged(self):return 'synthetic_engine_no_real_model'
    r.execute_predictions(scope,cache,tmp_path,Engine(),guard,lambda rec:rgbs[rec['image_id']])
    assert guard.counts==dict(source_image_decodes=9,native_tiles=9,cached_forwards=9)
    assert len(events)==18 and (tmp_path/'prediction_freeze.json').exists()
    def references():assert len(events)==18;return refs
    result=r.finish_evaluation(scope,tmp_path,cfg,references);r.write(tmp_path/'scope.json',scope)
    assert result['primary_pass'];assert all(x['qualified'] for x in result['pairs']);return tmp_path


def test_full_fake_engine_pipeline_prediction_freeze(tmp_path):
    synthetic(tmp_path);assert 'torch' not in sys.modules


def test_frozen_config_and_budget_denials(tmp_path):
    cfg=json.loads((ROOT/'docs/research/S01/S01-E028/run_config.json').read_text());r.validate_config(cfg)
    for key,val in [('threshold',.4),('private_inputs',8)]:
        q=copy.deepcopy(cfg);q[key]=val
        with pytest.raises(ValueError):r.validate_config(q)
    q=copy.deepcopy(cfg);q['counts']['cached_forwards']=1;guard=r.Guard(q,tmp_path,memory=lambda:0);guard.take('cached_forwards')
    with pytest.raises(RuntimeError):guard.take('cached_forwards')
    g2=r.Guard(cfg,tmp_path,memory=lambda:5*1024**3)
    with pytest.raises(MemoryError):g2.check()


def test_mac_refusal_before_torch_data_or_model(monkeypatch):
    cfg=json.loads((ROOT/'docs/research/S01/S01-E028/run_config.json').read_text())
    monkeypatch.setattr(r.source.prior.runtime.os,'name','posix')
    with pytest.raises(PermissionError):r.source.prior.runtime.production_environment(cfg)
    assert 'torch' not in sys.modules


def test_windows_data_allowlist_blocks_other_runs_and_traversal():
    approved=r'C:\Users\xw436\pavetrack_runs\S01-E002-R002\prepared\train\old.jpg'
    run=r'C:\Users\xw436\pavetrack_runs\S01-E028-R001'
    audit=r.path_auditor(dict(images={'old':dict(prepared_image=approved)}),run)
    audit('open',(approved,));audit('open',(run+r'\native\0001.npy',));audit('open',(r'C:\Windows\System32\dwm.exe',))
    for forbidden in [approved.replace('old.jpg','new-confirmed.jpg'),run+r'\..\sealed\image.png',r'C:\Users\xw436\pavetrack_runs\S01-E029-R001\map.npy']:
        with pytest.raises(PermissionError):audit('open',(forbidden,))


def test_scope_is_exact_not_label_or_score_selected():
    scope,_,_,_,cfg=fixture();cfg['counts'].update(images=9,contexts=9,pixels=9*64*64,native_tiles=9)
    # Establish exact metadata closure without reading any source RGB or labels.
    for rec in scope['images'].values():rec.update(prepared_image='example/'+rec['image_id'],prepared_image_sha256='fixed')
    identities=dict(rows=[])
    for row in scope['rows']:
        rec=scope['images'][row['image_id']];identities['rows'].append({k:rec[k] for k in ['image_id','location','width','height','prepared_image','prepared_image_sha256']})
    contexts=dict(rows=[row['context'] for row in scope['rows']]);extract=dict(images=scope['images'])
    r.validate_scope(scope,identities,contexts,extract,cfg)
    altered=copy.deepcopy(scope);altered['rows'][0]['context'][0]=1
    with pytest.raises(ValueError):r.validate_scope(altered,identities,contexts,extract,cfg)
    altered=copy.deepcopy(scope);altered['cases'][0]=1
    with pytest.raises(ValueError):r.validate_scope(altered,identities,contexts,extract,cfg)


def test_prediction_tamper_denied_before_reference_loader(tmp_path):
    synthetic(tmp_path);p=tmp_path/'cached_pass0.npy'
    a=np.load(p,mmap_mode='r+');a[0,0,0]=.123;a.flush();called=[]
    scope,_,_,_,cfg=fixture()
    with pytest.raises(ValueError):r.finish_evaluation(scope,tmp_path,cfg,lambda:called.append(True))
    assert called==[]


def test_resource_sampler_ignores_exited_child_and_reads_info_once():
    import psutil
    from types import SimpleNamespace
    class Process:
        def __init__(self,peak,exited=False,name='python.exe'):self.peak=peak;self.exited=exited;self.calls=0;self.label=name
        def memory_info(self):
            self.calls+=1
            if self.exited:raise psutil.NoSuchProcess(123)
            assert self.calls==1
            return SimpleNamespace(peak_wset=self.peak,rss=self.peak-1)
        def name(self):return self.label
    root=Process(100);gone=Process(40,exited=True);live=Process(200);parent=Process(20);shell=Process(50,name='powershell.exe')
    root.children=lambda recursive:[gone,live];root.parents=lambda:[parent,shell]
    assert r.aggregate_rss(root)==320 and live.calls==1 and shell.calls==0


def test_watchdog_unreadable_state_explicitly_stops_and_records(tmp_path):
    cfg=json.loads((ROOT/'docs/research/S01/S01-E028/run_config.json').read_text())
    def inaccessible():raise RuntimeError('own memory query unavailable')
    guard=r.Guard(cfg,tmp_path,memory=inaccessible);exits=[]
    assert r.watchdog_tick(guard,die=exits.append) is True and exits==[124]
    assert json.loads((tmp_path/'watchdog_stop.json').read_text())['reason']=='resource supervision unavailable'


def test_watchdog_still_stops_if_receipt_write_fails(tmp_path,monkeypatch):
    cfg=json.loads((ROOT/'docs/research/S01/S01-E028/run_config.json').read_text());guard=r.Guard(cfg,tmp_path,memory=lambda:5*1024**3);exits=[]
    def bad_write(*a):raise OSError('disk full')
    monkeypatch.setattr(r,'write',bad_write)
    with pytest.raises(OSError):r.watchdog_tick(guard,die=exits.append)
    assert exits==[124]


def test_gpu0_mapping_cannot_admit_gpu1_or_fallback():
    cfg=json.loads((ROOT/'docs/research/S01/S01-E028/run_config.json').read_text());env=r.environment
    env.placement(cfg)
    name=cfg['producer']['gpu_name'];uuid=env.GPU_UUID
    assert env.physical_gpu(f'1, wrong, {name}, 96000\n0, {uuid}, {name}, 8192',cfg)[0]=='0'
    for text in [f'1, {uuid}, {name}, 96000',f'0, wrong, {name}, 96000',f'0, {uuid}, {name}, 8191',f'0, {uuid}, {name}, nan',f'0, {uuid}, {name}, 96000\n0, {uuid}, {name}, 96000']:
        with pytest.raises(ValueError):env.physical_gpu(text,cfg)
    for key,value in [('gpu_physical_index',1),('CUDA_VISIBLE_DEVICES','1'),('gpu_uuid','wrong'),('fallback',True)]:
        altered=copy.deepcopy(cfg);altered['producer'][key]=value
        with pytest.raises(PermissionError):r.validate_config(altered)


def test_gpu0_baseline_still_rejects_unknown_compute_or_changed_binary():
    baseline=json.loads((ROOT/'docs/research/S01/S01-E028/gpu_desktop_baseline.json').read_text());runtime=r.source.prior.runtime
    path,h=next(iter(baseline['approved_desktop_executables'].items()))
    def xml(kind='C+G',name=path,uuid=baseline['gpu_uuid']):
        return f'<nvidia_smi_log><gpu><uuid>{uuid}</uuid><driver_model><current_dm>WDDM</current_dm></driver_model><utilization><gpu_util>0 %</gpu_util></utilization><processes><process_info><pid>123</pid><type>{kind}</type><process_name>{name}</process_name></process_info></processes></gpu></nvidia_smi_log>'
    assert runtime.desktop_inventory(xml(),baseline,lambda p:h)['gpu_uuid']==r.environment.GPU_UUID
    for x in [xml(kind='C'),xml(name=r'C:\Realtek\RtkUWP.exe'),xml(uuid='GPU1')]:
        with pytest.raises((ValueError,RuntimeError)):runtime.desktop_inventory(x,baseline,lambda p:h)
    with pytest.raises(ValueError):runtime.desktop_inventory(xml(),baseline,lambda p:'changed')


def test_logical_gpu_requires_actual_uuid_even_when_both_cards_share_name():
    from types import SimpleNamespace
    cfg=json.loads((ROOT/'docs/research/S01/S01-E028/run_config.json').read_text());env=r.environment
    props=SimpleNamespace(uuid=env.GPU_UUID)
    cuda=SimpleNamespace(device_count=lambda:1,get_device_name=lambda i:cfg['producer']['gpu_name'],get_device_properties=lambda i:props)
    torch=SimpleNamespace(cuda=cuda);env.logical_gpu(torch,cfg)
    for value in ['GPU-3d74ea12-5d84-a619-90b2-c0b1f104599a',None,'']:
        props.uuid=value
        with pytest.raises(ValueError):env.logical_gpu(torch,cfg)
    del props.uuid
    with pytest.raises(ValueError):env.logical_gpu(torch,cfg)


def test_cuda_uuid_object_canonical_form_matches_nvidia_smi_gpu_prefix():
    from types import SimpleNamespace
    cfg=json.loads((ROOT/'docs/research/S01/S01-E028/run_config.json').read_text());env=r.environment
    class CUuuid:
        def __init__(self,text):self.text=text
        def __str__(self):return self.text
    props=SimpleNamespace(uuid=CUuuid(env.GPU_UUID.removeprefix('GPU-')))
    cuda=SimpleNamespace(device_count=lambda:1,get_device_name=lambda i:cfg['producer']['gpu_name'],get_device_properties=lambda i:props)
    env.logical_gpu(SimpleNamespace(cuda=cuda),cfg)
    for text in ['3d74ea12-5d84-a619-90b2-c0b1f104599a','malformed','']:
        props.uuid=CUuuid(text)
        with pytest.raises(ValueError):env.logical_gpu(SimpleNamespace(cuda=cuda),cfg)


def test_pillow_overlay_rejects_missing_extra_and_tampered_library(tmp_path):
    import hashlib
    folder=tmp_path/'PIL';folder.mkdir();file=folder/'__init__.py';file.write_bytes(b'pinned runtime')
    expected={'PIL/__init__.py':hashlib.sha256(file.read_bytes()).hexdigest()}
    assert r.environment.verify_overlay(tmp_path,expected)==1
    file.write_bytes(b'wrong runtime')
    with pytest.raises(ValueError):r.environment.verify_overlay(tmp_path,expected)
    file.write_bytes(b'pinned runtime');extra=tmp_path/'sitecustomize.py';extra.write_text('unexpected startup code')
    with pytest.raises(ValueError):r.environment.verify_overlay(tmp_path,expected)
    extra.unlink();file.unlink()
    with pytest.raises(ValueError):r.environment.verify_overlay(tmp_path,expected)
