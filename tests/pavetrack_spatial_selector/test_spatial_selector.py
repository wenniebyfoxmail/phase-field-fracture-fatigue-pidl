import copy,importlib.util,json,hashlib,io
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=module('e021_test',ROOT/'scripts/pavetrack_spatial_selector/run.py');c=a.c;p=a.spatial;l=a.learning
old=module('e021_fixture_only',ROOT/'tests/pavetrack_role_probe/test_probe.py');CFG=c.read(ROOT/c.CONTRACT/'run_config.json')
def guard(cfg=CFG):return a.Guard(cfg,memory=lambda:100)
def emit_for(run):
 expected={}
 def emit(n,v):expected[n]=copy.deepcopy(v);c.write(run/n,v)
 return emit,expected

def fixture(root):
 d,t,_=old.fixture();cfg=copy.deepcopy(CFG);positive={r['parent_id'] for payload in d['labels'] for r in payload['rows'] if r['U']>0};d['candidates']=c.features(d['originals'],d['manifest'],d['probabilities'],cfg);images={};root.mkdir(exist_ok=True)
 for m,row in zip(d['manifest'],d['candidates']):
  im=m['image_id'];path=root/im;arr=np.full((100,100),220,dtype=np.uint8);b=row['row']['box_xyxy'];x=int(b[2]-1) if row['parent_id'] in positive else 1;arr[1:10,x]=10;Image.fromarray(arr).save(path,format='PNG');m.update(prepared_image=str(path),prepared_image_sha256=c.sha(path));images[im]={k:m[k] for k in ['image_id','location','prepared_image','prepared_image_sha256','width','height']}
 d['images']=images;main=sum(len(v['rows']) for v in d['labels']);cfg['input_counts']['images']=len(t);cfg['budget'].update(source_image_decodes=len(t),spatial_feature_rows=len(d['candidates']),pixel_reads=len(t)+6,source_image_reads=len(t)+6,training_target_rows=main,prediction_rows=main+sum(r['eligible'] for r in d['candidates'])+sum(len(v['rows'])*n for v,n in zip(d['labels'],cfg['fit']['expected_positive_sites'])));return d,t,cfg

def test_response_matches_slow_independent_four_direction_definition():
 g=np.random.default_rng(21).uniform(size=(128,128));r=p.response(g)
 for y,x in [(1,1),(40,80),(126,126),(60,20)]:
  expected=max([0.]+[(g[y-dy,x-dx]+g[y+dy,x+dx])/2-g[y,x] for dx,dy in [(1,0),(0,1),(1,1),(1,-1)]])
  assert r[y,x]==expected
 assert not r[0].any() and not r[-1].any() and not r[:,0].any()

def test_shared_context_center_masks_and_area_corrected_mass_reference():
 arr=np.full((100,100),220,dtype=np.uint8);arr[30:70,60]=0;image=Image.fromarray(arr);b0=[10,20,45,80];b1=[40,20,75,80];d=p.describe(image,b0,b1,CFG);ctx=p.context_box([b0,b1],100,100)
 with image.crop(ctx).resize((128,128),Image.Resampling.BILINEAR) as crop:r=p.response(np.asarray(crop,dtype=float)/255)
 xs=ctx[0]+(np.arange(128)+.5)*(ctx[2]-ctx[0])/128;ys=ctx[1]+(np.arange(128)+.5)*(ctx[3]-ctx[1])/128;zs=[]
 for b in [b0,b1]:
  mask=np.array([[b[0]<=x<b[2] and b[1]<=y<b[3] for x in xs] for y in ys]);zs.append(float(r[mask].sum()/r.sum()-mask.mean()))
 assert d['values']==pytest.approx([zs[1],(zs[1]-zs[0])/2]);assert d['values'][1]>0 and d['context']==ctx

def test_equal_boxes_uniform_and_empty_context_degenerate_values_are_zero():
 image=Image.new('L',(50,50),220);d=p.describe(image,[1,1,10,10],[1,1,10,10],CFG);assert d['values']==[0.,0.] and d['degenerate']=='zero_mass'
 d=p.describe(image,[200,200,210,210],[205,200,215,210],CFG);assert d['values']==[0.,0.] and d['degenerate']=='empty_context'

@pytest.mark.parametrize('b',[[0,0,0,1],[0,0,1,float('nan')],[0,0,1],[2,2,1,1]])
def test_bad_spatial_geometry_fails(b):
 with pytest.raises(ValueError):p.describe(Image.new('L',(20,20)),b,[1,1,5,5],CFG)

def test_no_GT_or_model_can_enter_fixed_descriptor():
 with pytest.raises(TypeError):p.describe(Image.new('L',(20,20)),[0,0,5,5],[1,0,6,5],CFG,GT=[])
 with pytest.raises(TypeError):l.predict({},[],guard(),GT=[])

@pytest.mark.parametrize('field',['path','parent','hash','size','location','conflict','coverage'])
def test_image_identity_validation_rejects_unapproved_or_ambiguous_sources(tmp_path,field):
 d,t,cfg=fixture(tmp_path/'images');rows=copy.deepcopy(d['manifest']);lock=dict(source_image_root=str(tmp_path/'images'),source_images=len(t));locs=d['image_locations'];a.inputs.images_from_manifest(rows,locs,cfg,lock)
 if field=='path':rows[0]['prepared_image']=str(tmp_path/'outside'/rows[0]['image_id'])
 elif field=='parent':rows[0]['prepared_image']=str(tmp_path/'images/../outside'/rows[0]['image_id'])
 elif field=='hash':rows[0]['prepared_image_sha256']='notsha'
 elif field=='size':rows[0]['width']=0
 elif field=='location':rows[0]['location']='sealed'
 elif field=='conflict':rows.append(dict(rows[0],width=99))
 else:rows.pop()
 with pytest.raises(ValueError):a.inputs.images_from_manifest(rows,locs,cfg,lock)

def test_hash_checked_before_decode_and_dimension_mismatch_stops(tmp_path,monkeypatch):
 d,t,cfg=fixture(tmp_path/'images');row=next(iter(d['images'].values()));bad=dict(row,prepared_image_sha256='0'*64);g=guard(cfg)
 with pytest.raises(ValueError,match='hash'):p.image_bytes(bad,g)
 assert g.counts['source_image_decodes']==0
 raw=p.image_bytes(row,g)
 with pytest.raises(ValueError,match='dimensions'):p.decode(raw,dict(row,width=101),g,'source_image_decodes')

def test_source_decode_once_per_image_row_order_no_representation_fit(tmp_path):
 d,t,cfg=fixture(tmp_path/'images');run=tmp_path/'run';run.mkdir();emit,saved=emit_for(run);g=guard(cfg);d['spatial']=p.extract(d,run,cfg,g,c,emit)
 assert len(d['spatial'])==len(d['candidates']);assert g.counts['source_image_decodes']==len(t) and g.counts['spatial_feature_rows']==len(d['candidates']);assert saved['spatial_features.json']['fitted_parameters']==0
 assert all(r['index']==i and all(-1<=v<=1 for v in r['values']) for i,r in enumerate(d['spatial']))
 with pytest.raises(ValueError,match='duplicate'):p.extract(d,run,cfg,g,c,emit)

def fit_fixture(tmp_path,monkeypatch):
 d,t,cfg=fixture(tmp_path/'images');run=tmp_path/'run';run.mkdir();emit,saved=emit_for(run);g=guard(cfg);d['spatial']=p.extract(d,run,cfg,g,c,emit);monkeypatch.setattr(c,'require_producer',lambda _:None);return d,t,cfg,run,emit,saved,g

def test_nine_main_heads_before_prediction_freeze_precedes_deletion_and39solves(tmp_path,monkeypatch):
 d,t,cfg,run,emit,saved,g=fit_fixture(tmp_path,monkeypatch);predict=l.predict
 def checked(model,values,watch):
  assert watch.counts['model_fits']>=9
  if watch.counts['model_fits']>9:assert (run/'prediction_freeze_receipt.json').exists()
  return predict(model,values,watch)
 monkeypatch.setattr(l,'predict',checked);models,support,added=a.fit_and_freeze(d,t,run,cfg,g,emit);assert g.counts['linear_solves']==39 and g.counts['prediction_rows']==cfg['budget']['prediction_rows'];assert all(m['coefficient_count']==11 for m in models);assert len(saved['jackknife.json']['fits'])==10
 assert all(r==next(v['row'] for v in d['candidates'] if v['parent_id']==r['parent_id']) for r in added)

def pipeline(tmp_path,monkeypatch,real_hook=False):
 d,t,cfg=fixture(tmp_path/'images');run=tmp_path/'S01-E021-synthetic';run.mkdir();snap=run/'input_snapshot';snap.mkdir();c.write(snap/'synthetic.json',dict(synthetic=True));lock=dict(original_rows_digest=c.digest(d['originals']),source_zip_sha256='synthetic',source_files={'synthetic.json':c.sha(snap/'synthetic.json')},source_B12_hits=len(c.baseline(c.scoped(d['originals'],d['candidates'],t,d['image_locations'],cfg['locations']))[1]))
 monkeypatch.setattr(a.inputs,'load',lambda *args:d);monkeypatch.setattr(a.legacy,'metadata',lambda *args:d['records']);monkeypatch.setattr(c,'require_producer',lambda _:None)
 if not real_hook:monkeypatch.setattr(a.sys,'addaudithook',lambda _:None)
 args=SimpleNamespace(run=run,source=tmp_path/'source.zip',metadata=tmp_path/'metadata.json');launch=dict(synthetic=True);c.write(run/'launch.json',launch);g=guard(cfg);result=a.execute(args,cfg,lock,g,launch);return run,result,g,lock

def test_complete_real_synthetic_pixels_path_counts_snapshots_and_actual_gain(tmp_path,monkeypatch):
 run,result,g,lock=pipeline(tmp_path,monkeypatch);assert result['comparison']['retention']==1 and result['comparison']['net_GT']>=1 and result['primary_pass'];assert g.counts['linear_solves']==39 and 0<g.receipt()['pixel_reads']<=20
 cases=c.read(run/'cases.json');assert cases['kind']=='OOF_appended' and len(cases['cases'])<=6 and g.counts['case_image_decodes']==len(cases['cases']);assert g.counts['source_image_reads']==14+len(cases['cases'])
 assert len(list((run/'analysis').glob('*.png')))==3 and 'actual image overlays' in (run/'analysis/README_analysis.md').read_text()
 for row in cases['cases']:assert c.sha(run/row['snapshot'])==row['sha256']
 receipt=c.read(run/'output_receipt.json');expected={n:c.read(run/n) for n in receipt['files'] if n.endswith('.json') and not n.startswith('input_snapshot/')};bad=c.read(run/'spatial_features.json');bad['rows'][0]['values'][0]=.99;c.write(run/'spatial_features.json',bad);receipt['files']['spatial_features.json']=c.sha(run/'spatial_features.json')
 with pytest.raises(ValueError,match='semantic'):a.verify(run,expected,receipt,lock)

def test_all_abstain_uses_deduplicated_FIT_opportunities_only_after_freeze(tmp_path,monkeypatch):
 def zero(model,values,g):g.take('prediction_rows',len(values));return [dict(roles=[0.,0.,0.],rank_score=0.) for _ in values]
 monkeypatch.setattr(l,'predict',zero);run,result,g,lock=pipeline(tmp_path,monkeypatch);assert not result['primary_pass'] and result['comparison']['net_GT']==0 and result['comparison']['retention']==1
 cases=c.read(run/'cases.json');assert cases['kind']=='FIT_opportunity_not_selected' and not cases['used_for_learning'];keys=[r['parent_id'] for r in cases['cases']];assert len(keys)==len(set(keys))<=6

def test_failed_main_fit_stops_before_prediction_and_frozen_output(tmp_path,monkeypatch):
 d,t,cfg,run,emit,saved,g=fit_fixture(tmp_path,monkeypatch);fit=l.fit;calls=[]
 def broken(*args):
  calls.append(1)
  if len(calls)==2:raise ValueError('synthetic failed main fit')
  return fit(*args)
 monkeypatch.setattr(l,'fit',broken);monkeypatch.setattr(l,'predict',lambda *args:pytest.fail('premature role prediction'))
 with pytest.raises(ValueError,match='main fit'):a.fit_and_freeze(d,t,run,cfg,g,emit)
 assert not (run/'OOF_predictions.json').exists()

@pytest.mark.parametrize('counter',['source_image_decodes','spatial_feature_rows','case_image_decodes','source_image_reads','pixel_reads','linear_solves'])
def test_pixel_and_learning_caps_fail_closed(counter):
 g=guard();g.counts[counter]=CFG['budget'][counter]
 with pytest.raises(RuntimeError):g.take(counter)

def test_Mac_boundary_and_CPU1_thread_guard(monkeypatch):
 with pytest.raises(PermissionError):a.execute(None,CFG,{},guard(),{})
 monkeypatch.setattr(a,'InheritedRequire',lambda _:None);monkeypatch.delenv('OPENBLAS_NUM_THREADS',raising=False)
 with pytest.raises(PermissionError,match='OPENBLAS'):a.require_producer(CFG)

def test_first_model_invariant_to_current_held_GT_and_spatial_values(tmp_path,monkeypatch):
 d,t,cfg,run,emit,saved,g=fit_fixture(tmp_path,monkeypatch);fit=l.fit;models=[]
 def first(values,labels,cfg,watch):
  if models:raise RuntimeError('end first fit')
  m=fit(values,labels,cfg,watch);models.append(copy.deepcopy(m));return m
 monkeypatch.setattr(l,'fit',first)
 with pytest.raises(RuntimeError):a.fit_and_freeze(d,t,run,cfg,g,emit)
 before=models.pop();bad=copy.deepcopy(d);targets=copy.deepcopy(t)
 for im,loc in bad['image_locations'].items():
  if loc in cfg['held_groups'][0]:targets[im]=[]
 for row in bad['spatial']:
  if row['location'] in cfg['held_groups'][0]:row['values']=[-1.,1.]
 with pytest.raises((RuntimeError,ValueError)):a.fit_and_freeze(bad,targets,run,cfg,guard(cfg),emit)
 assert models[0]==before

def test_combined_allowlist_loader_with_new_image_identities_skips_pooled_array(tmp_path):
 import zipfile
 source,rawdata,oldcfg,lock=old.synthetic_zip(tmp_path);d,t,cfg=fixture(tmp_path/'images');lock.update(source_image_root=str(tmp_path/'images'),source_images=len(t))
 with zipfile.ZipFile(source) as z:raw={n:z.read(n) for n in z.namelist()}
 raw['input_snapshot/candidate_identity.json']=json.dumps(dict(rows=d['manifest'])).encode();selected=set(lock['source_files'])-{'output_receipt.json'};raw['output_receipt.json']=json.dumps(dict(files={n:hashlib.sha256(raw[n]).hexdigest() for n in selected})).encode()
 with zipfile.ZipFile(source,'w') as z:
  for n,v in raw.items():z.writestr(n,v)
 lock.update(source_zip_sha256=c.sha(source),source_zip_bytes=source.stat().st_size,source_files={n:hashlib.sha256(raw[n]).hexdigest() for n in lock['source_files']});lock['image_identity_member']='input_snapshot/candidate_identity.json';run=tmp_path/'loaded';run.mkdir();g=guard(cfg);loaded=a.inputs.load(source,run,cfg,lock,g,c,a.legacy,a.prior_inputs)
 assert loaded['images']==d['images'] and loaded['candidates']==d['candidates'] and not g.counts
 assert not (run/'input_snapshot/pooled_features.npy').exists()

def test_case_selection_cannot_run_before_freeze_or_evaluation(tmp_path):
 d,t,cfg=fixture(tmp_path/'images');emit,_=emit_for(tmp_path)
 with pytest.raises(FileNotFoundError):p.cases(d,t,[],tmp_path,cfg,guard(cfg),c,emit)
