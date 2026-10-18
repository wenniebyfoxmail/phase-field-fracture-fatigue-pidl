import copy,importlib.util,json,hashlib,subprocess,sys,collections
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=module('e024_test',ROOT/'scripts/pavetrack_qualified_localizer/run.py');c=a.c;sp=a.spatial;net=a.model;old=module('e024_fixture',ROOT/'tests/pavetrack_pixel_selector/test_pixels.py');CFG=c.read(ROOT/'docs/research/S01/S01-E024/run_config.json')
def fixture(tmp_path):
 d,t,prev=old.fixture(tmp_path);cfg=copy.deepcopy(CFG);n=len(d['candidates']);cfg['input_counts']={'images':len(d['images']),'original_rows':len(d['originals']),'corrections':n};cfg['localizer'].update(steps_per_fold=2,batch_size=2,train_rows=[sum(r['location'] in cfg['localizer']['train_locations'][k] for r in d['candidates']) for k in range(3)],qual_rows=[sum(r['location'] in cfg['localizer']['qual_locations'][k] for r in d['candidates']) for k in range(3)])
 role=[sum(r['eligible'] and r['location'] not in held for r in d['candidates']) for held in cfg['held_groups']];eligible=sum(r['eligible'] for r in d['candidates']);heldrows=[sum(r['location'] in h for r in d['candidates']) for h in cfg['held_groups']]
 cfg['budget_definitions'].update(role_training_rows=role,eligible_rows=eligible,held_candidate_rows=heldrows)
 b=cfg['budget'];b.update(source_image_decodes=len(d['images']),spatial_feature_rows=n,feature_cache_bytes=n*3*128*128,localizer_mask_rows=n*2,localizer_mask_bytes=n*2*32*32,localizer_steps=6,gradient_steps=6,parameter_gradient_steps=6,localizer_training_rows=12,localizer_backward_rows=12,localizer_qualification_rows=sum(cfg['localizer']['qual_rows']),localizer_prediction_rows=n*3,pixel_map_prediction_rows=n*3,pixel_evaluation_rows=n,training_target_rows=sum(role),prediction_rows=eligible*3,pixel_reads=len(d['images'])+6,source_image_reads=len(d['images'])+6)
 return d,t,cfg

def guard(cfg):return a.Guard(cfg,memory=lambda:100)
def emit_for(run):
 expected={}
 def emit(n,v):expected[n]=copy.deepcopy(v);c.write(run/n,v)
 return emit,expected

def extracted(tmp_path):
 d,t,cfg=fixture(tmp_path/'images');run=tmp_path/'run';run.mkdir();emit,expected=emit_for(run);g=guard(cfg);d['rgb'],d['contexts']=sp.extract(d,run,cfg,g,c,emit);return d,t,cfg,run,emit,expected,g

class ToyBackend:
 def __init__(self,cfg,g,fail=()):self.cfg=cfg;self.g=g;self.fail=set(fail)
 def fit(self,rgb,bank,rows,k):
  by,p,support=net.training_scope(rows,bank,self.cfg,k)
  for _ in range(self.cfg['localizer']['steps_per_fold']):
   for key,n in [('localizer_steps',1),('gradient_steps',1),('parameter_gradient_steps',1),('localizer_training_rows',self.cfg['localizer']['batch_size']),('localizer_backward_rows',self.cfg['localizer']['batch_size'])]:self.g.take(key,n)
  state={'synthetic_color_oracle':k};return dict(fold=k,parameters=6049,verified=True,state=state,state_digest=net.digest(state),train_prevalence=p,train_support=support,synthetic=True,not_real_localisation=True)
 def predict(self,m,rgb):
  if m['fold'] in self.fail:return np.zeros((len(rgb),32,32),dtype=np.float32)
  # Synthetic fixture uses red20 background / red200 region. Actual CNN tested separately.
  return np.clip((rgb[:,0,2::4,2::4].astype(np.float32)-20)/180,0,1)

def pipeline(tmp_path,monkeypatch,fail=(),real_hook=False):
 d,t,cfg=fixture(tmp_path/'images');run=tmp_path/'S01-E024-synthetic';run.mkdir();snap=run/'input_snapshot';snap.mkdir();annotation=snap/'train_polygons.json';c.write(annotation,{'rows':[r for vals in d['annotations'].values() for r in vals]});lock=dict(source_files={},source_zip_sha256='synthetic',annotation_snapshot_sha256=c.sha(annotation),original_rows_digest=c.digest(d['originals']),source_B12_hits=len(c.baseline(c.scoped(d['originals'],d['candidates'],t,d['image_locations'],cfg['locations']))[1]))
 monkeypatch.setattr(a.inputs,'load',lambda *args:d);monkeypatch.setattr(a.legacy,'metadata',lambda *args:d['records']);monkeypatch.setattr(c,'require_producer',lambda cfg:None)
 if not real_hook:monkeypatch.setattr(a.sys,'addaudithook',lambda hook:None)
 monkeypatch.setattr(a,'backend',lambda cfg,g:ToyBackend(cfg,g,fail));g=guard(cfg);launch={'synthetic':True};c.write(run/'launch.json',launch);args=SimpleNamespace(run=run,source=tmp_path/'source',metadata=tmp_path/'metadata');result=a.execute(args,cfg,lock,g,launch);return run,result,g,lock,cfg

def test_architecture_has_spatial_output6049parameters_and_native_gradient():
 import torch
 torch.set_num_threads(1);torch.manual_seed(2);m=net.network(CFG);x=torch.rand(2,3,128,128);y=torch.zeros(2,1,32,32);y[:,:,8:20,8:20]=1;before=[v.detach().clone() for v in m.parameters()];opt=torch.optim.AdamW(m.parameters(),lr=.001);loss=net.probability_loss(m(x),y,.1);assert m(x).shape==(2,1,32,32);loss.backward();assert all(v.grad is not None and torch.isfinite(v.grad).all() for v in m.parameters());opt.step();assert any(not torch.equal(v,p) for v,p in zip(m.parameters(),before))

def test_true_train6_fit_ignores_qual_outer_labels_RGB_and_predict_has_no_GT(tmp_path):
 d,t,cfg,run,emit,expected,g=extracted(tmp_path);bank=sp.references(d,0,run,cfg,g,c,emit);engine=net.Backend(cfg,g,production=False);one=engine.fit(d['rgb'],bank,d['candidates'],0);assert one['parameters']==6049 and one['verified']
 changed=np.array(d['rgb']);labels=np.array(bank['values'])
 train=cfg['localizer']['train_locations'][0]
 for row in d['candidates']:
  if row['location'] not in train:
   changed[row['index']]=255
   if row['index'] in bank['lookup']:labels[bank['lookup'][row['index']]]=1-labels[bank['lookup'][row['index']]]
 two=net.Backend(cfg,guard(cfg),production=False).fit(changed,dict(bank,values=labels),d['candidates'],0);assert one['state']==two['state'] and one['train_prevalence']==two['train_prevalence'];p=engine.predict(one,np.asarray(d['rgb'][:2]));assert p.shape==(2,32,32)
 with pytest.raises(TypeError):engine.predict(one,np.asarray(d['rgb'][:2]),GT=[])
 bad=copy.deepcopy(one);next(iter(bad['state'].values()))[0][0][0][0]+=1
 with pytest.raises(ValueError):engine.predict(bad,np.asarray(d['rgb'][:1]))

def test_RGB_cache_context_alignment_no_E003_forward(tmp_path):
 d,t,cfg,run,emit,expected,g=extracted(tmp_path);assert d['rgb'].dtype==np.uint8 and d['rgb'].shape==(14,3,128,128);assert g.counts['source_image_decodes']==14 and g.counts['backbone_forwards']==0
 with pytest.raises(ValueError,match='duplicate'):sp.extract(d,run,cfg,g,c,emit)

def test_floor_target_geometry_and_exact_uniform_map_concentration():
 mask=np.zeros((20,20),dtype=np.uint8);mask[:10,:10]=1;y=sp.target(mask,[0,0,20,20]);assert y.shape==(32,32) and y[0,0]==1 and y[-1,-1]==0
 assert sp.describe(np.ones((32,32)),[0,0,10,10],[10,10,20,20],[0,0,20,20])['values']==pytest.approx([0,0],abs=1e-15)

@pytest.mark.parametrize('fail,expected_admitted',[([], [0,1,2]),([0],[1,2]),([0,1,2],[])])
def test_qualification_routes_partial_and_zero_preserve_originals(tmp_path,monkeypatch,fail,expected_admitted):
 run,result,g,lock,cfg=pipeline(tmp_path,monkeypatch,fail);freeze=c.read(run/'qualification_freeze.json');assert freeze['admitted_folds']==expected_admitted
 assert g.counts['gradient_steps']==6 and g.counts['model_fits']==3*len(expected_admitted) and g.counts['localizer_prediction_rows']==14*len(expected_admitted)
 if expected_admitted:
  assert result['comparison']['retention']==1 and result['originals_unchanged'];assert g.counts['final_OOF_comparisons']==1 and g.counts['held_group_comparisons']==3
  assert result['comparison']['net_GT']>=1;assert c.read(run/'pixel_evaluation.json')['covered_locations']==[v for v in cfg['locations'] if any(v in cfg['held_groups'][k] for k in expected_admitted)]
  oof=c.read(run/'OOF_predictions.json')
  for k in fail:assert oof['folds'][k]['rows']==[] and oof['folds'][k]['threshold']=='abstain'
 else:
  assert result['primary_pass'] is None and result['comparison']['net_GT'] is None and result['stageB']=='inconclusive_not_executed';assert not (run/'OOF_predictions.json').exists() and not (run/'analysis/F01_detection.png').exists();assert g.counts['final_OOF_comparisons']==g.counts['model_fits']==0
 assert g.counts['case_image_decodes']<=6 and g.counts['source_image_reads']<=20


def test_model_freeze_qual_decisions_and_all_role_heads_before_prediction(tmp_path,monkeypatch):
 old_predict=a.learning.predict;old_qual=sp.qualification
 def checked_qual(*args):
  run=args[4];assert (run/'localizer_training_freeze.json').is_file();assert len(list(run.glob('localizer_model_fold_*.json')))==3;return old_qual(*args)
 def checked_predict(m,x,g):assert g.counts['localizer_qualifications']==3 and g.counts['model_fits']==9;return old_predict(m,x,g)
 monkeypatch.setattr(sp,'qualification',checked_qual);monkeypatch.setattr(a.learning,'predict',checked_predict);pipeline(tmp_path,monkeypatch)


def test_changed_map_self_rehash_cannot_override_trusted_freeze(tmp_path,monkeypatch):
 run,result,g,lock,cfg=pipeline(tmp_path,monkeypatch);receipt=c.read(run/'output_receipt.json');expected={n:c.read(run/n) for n in receipt['files'] if n.endswith('.json') and not n.startswith('input_snapshot/')};path=run/'qualification_maps_fold_0.npy';m=np.load(path,mmap_mode='r+');m[0,0,0]=.123;m.flush();del m;receipt['files'][path.name]=c.sha(path)
 with pytest.raises(ValueError):a.verify(run,expected,receipt,lock)

@pytest.mark.parametrize('field',['localizer_steps','localizer_backward_rows','localizer_qualification_rows','localizer_prediction_rows','feature_cache_bytes','localizer_mask_bytes'])
def test_new_budget_caps_fail_closed(field):
 g=guard(CFG)
 with pytest.raises(RuntimeError,match='COUNT_CAP'):g.take(field,CFG['budget'][field]+1)

def test_Mac_production_is_denied_before_real_training():
 with pytest.raises(PermissionError):c.require_producer(CFG)


def test_zero_foreground_qualification_is_inconclusive_not_zero_gain(tmp_path):
 d,t,cfg,run,emit,expected,g=extracted(tmp_path);bank=sp.references(d,0,run,cfg,g,c,emit);engine=ToyBackend(cfg,g);m=engine.fit(d['rgb'],bank,d['candidates'],0)
 for row in d['candidates']:
  if row['location'] in cfg['localizer']['qual_locations'][0]:bank['values'][bank['lookup'][row['index']]]=0
 q,maps,rows=sp.qualification(engine,m,d,bank,run,cfg,g,c,emit,0);assert not q['qualified'] and q['status']=='inconclusive' and q['foreground_Dice_gain'] is None


def test_single_class_train_reference_stops_before_optimizer(tmp_path):
 d,t,cfg,run,emit,expected,g=extracted(tmp_path);bank=sp.references(d,0,run,cfg,g,c,emit);bank['values'][:]=0
 with pytest.raises(net.ReferenceUnavailable):net.Backend(cfg,g,production=False).fit(d['rgb'],bank,d['candidates'],0)
 assert g.counts['localizer_steps']==0


def test_real_PixelGate_end_to_end_and_extra_source_denied(tmp_path):
 script='''import importlib.util,pathlib,pytest
s=importlib.util.spec_from_file_location('fixture',r'FILE');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
mp=pytest.MonkeyPatch();run,result,g,lock,cfg=m.pipeline(pathlib.Path(r'TEMP'),mp,real_hook=True)
assert result['comparison']['retention']==1
try:open(pathlib.Path(r'TEMP')/'sealed.jpg','rb')
except PermissionError:pass
else:raise AssertionError('extra source allowed')
'''.replace('FILE',str(Path(__file__).resolve())).replace('TEMP',str(tmp_path/'child'))
 p=subprocess.run([sys.executable,'-c',script],cwd=ROOT,capture_output=True,text=True);assert p.returncode==0,p.stdout+p.stderr
