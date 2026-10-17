import copy,importlib.util,json,hashlib,io
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=module('e022_test',ROOT/'scripts/pavetrack_semantic_selector/run.py');c=a.c;p=a.spatial;l=a.learning
old=module('e022_fixture_only',ROOT/'tests/pavetrack_spatial_selector/test_spatial_selector.py')
CFG=c.read(ROOT/c.CONTRACT/'run_config.json')
def guard(cfg=CFG):return a.Guard(cfg,memory=lambda:100)
def emit_for(run):
 saved={}
 def emit(n,v):saved[n]=copy.deepcopy(v);c.write(run/n,v)
 return emit,saved

def fixture(root):
 d,t,prior=old.fixture(root);cfg=copy.deepcopy(CFG)
 cfg['input_counts']=prior['input_counts'];cfg['budget'].update({k:v for k,v in prior['budget'].items() if k in ['source_image_decodes','spatial_feature_rows','pixel_reads','source_image_reads','training_target_rows','prediction_rows']})
 for k in ['backbone_forwards','head_forwards','head_input_gradient_rows']:cfg['budget'][k]=len(d['candidates'])
 return d,t,cfg

class SyntheticBackend:
 identity={'synthetic':True,'not_real_E003':True}
 def __init__(self,g):self.g=g
 def maps(self,image,contexts):
  self.g.take('max_semantic_batches')
  for key in ['backbone_forwards','head_forwards','head_input_gradient_rows']:self.g.take(key,len(contexts))
  rows=[]
  for ctx in contexts:
   with image.crop(ctx) as crop:arr=np.asarray(crop.convert('L'))
   # Synthetic pixel decoder, not a simulation of real E003 performance.
   heat=np.zeros((7,7))
   for y,x in np.argwhere(arr<100):heat[min(6,int(y*7/len(arr))),min(6,int(x*7/arr.shape[1]))]+=1
   rows.append(dict(heatmap=heat.tolist(),logits=[0.,1.],input_gradient_inf=1.,parameter_gradients=False,backbone_gradients=False))
  return rows

def test_independent_exact_coverage_short_boxes_and_uniform_mass():
 ctx=[0,0,70,70];b=[9.9,19.9,10.1,20.1];cov=p.coverage(b,ctx)
 assert cov.sum()==pytest.approx(.04/100) and np.count_nonzero(cov)==4
 d=p.describe_map(np.ones((7,7)),b,[30,30,45,45],ctx)
 assert d['values']==pytest.approx([0,0],abs=1e-16)
 h=np.zeros((7,7));h[2,3]=2;d=p.describe_map(h,[0,0,10,10],[30,20,40,30],ctx)
 assert d['values']==pytest.approx([48/49,.5])

@pytest.mark.parametrize('heat',[np.zeros((6,7)),np.full((7,7),np.nan),-np.ones((7,7))])
def test_invalid_map_fails(heat):
 with pytest.raises(ValueError):p.describe_map(heat,[0,0,5,5],[1,0,6,5],[0,0,10,10])

def test_zero_mass_equal_boxes_and_gt_not_predictor_input():
 d=p.describe_map(np.zeros((7,7)),[0,0,5,5],[0,0,5,5],[0,0,10,10]);assert d['values']==[0,0] and d['degenerate']=='zero_mass'
 with pytest.raises(TypeError):p.describe_map(np.ones((7,7)),[0,0,5,5],[0,0,5,5],[0,0,10,10],GT=[])
 with pytest.raises(TypeError):l.predict({},[],guard(),GT=[])

def test_margin_map_matches_full_feature_gradient_up_to49_and_class_sign():
 import torch
 torch.set_num_threads(1);torch.manual_seed(22)
 head=torch.nn.Sequential(torch.nn.Linear(576,8),torch.nn.Hardswish(),torch.nn.Linear(8,2)).eval()
 for par in head.parameters():par.requires_grad_(False)
 f=torch.rand(2,576,7,7)
 rows=p.margin_attribution(head,f)
 z=f.clone().requires_grad_(True);logits=head(z.mean((2,3)));df=torch.autograd.grad((logits[:,1]-logits[:,0]).sum(),z)[0]
 expected=torch.relu((df.mean((2,3))[:,:,None,None]*z.detach()).sum(1))*49
 assert np.asarray([r['heatmap'] for r in rows])==pytest.approx(expected.numpy(),abs=1e-6)
 assert all(par.grad is None for par in head.parameters()) and f.grad is None
 # Reversing class logits must change the signed class evidence, not generic texture.
 reverse=copy.deepcopy(head)
 with torch.no_grad():reverse[-1].weight.copy_(head[-1].weight.flip(0));reverse[-1].bias.copy_(head[-1].bias.flip(0))
 negative=p.margin_attribution(reverse,f)
 assert not np.allclose([r['heatmap'] for r in rows],[r['heatmap'] for r in negative])


def test_inference_tensor_bridge_makes_ordinary_leaf_and_batch_is_row_separable():
 import torch
 head=torch.nn.Linear(576,2).eval()
 with torch.no_grad():head.weight.zero_();head.weight[1,0]=1;head.bias.zero_()
 for par in head.parameters():par.requires_grad_(False)
 with torch.inference_mode():f=torch.ones(2,576,7,7)
 batch=p.margin_attribution(head,f)
 assert batch==p.margin_attribution(head,f[:1])+p.margin_attribution(head,f[1:])
 assert np.asarray(batch[0]['heatmap'])==pytest.approx(np.ones((7,7)))


def test_head_training_trainable_or_existing_parameter_gradient_rejected():
 import torch
 head=torch.nn.Linear(576,2);f=torch.ones(1,576,7,7)
 with pytest.raises(ValueError,match='frozen'):p.margin_attribution(head,f)
 head.eval()
 for par in head.parameters():par.requires_grad_(False)
 head.weight.grad=torch.ones_like(head.weight)
 with pytest.raises(ValueError,match='frozen'):p.margin_attribution(head,f)


def test_random_real_architecture_shape_without_checkpoint_or_training():
 import torch
 from torchvision.models import mobilenet_v3_small
 torch.set_num_threads(1);torch.manual_seed(220)
 model=mobilenet_v3_small(weights=None).eval();model.classifier[-1]=torch.nn.Linear(1024,2)
 for par in model.parameters():par.requires_grad_(False)
 with torch.no_grad():f=model.features(torch.ones(1,3,224,224))
 assert f.shape==(1,576,7,7)
 rows=p.margin_attribution(model.classifier,f)
 assert np.isfinite(rows[0]['heatmap']).all() and all(par.grad is None for par in model.parameters())


def test_semantic_extract_decodes_once_counts_all_work_and_never_refits(tmp_path):
 d,t,cfg=fixture(tmp_path/'images');run=tmp_path/'run';run.mkdir();emit,saved=emit_for(run);g=guard(cfg);rows=p.extract(d,run,cfg,g,c,emit,SyntheticBackend(g))
 assert len(rows)==len(d['candidates']) and g.counts['source_image_decodes']==14
 assert all(g.counts[k]==len(rows) for k in ['backbone_forwards','head_forwards','head_input_gradient_rows'])
 assert all(r['index']==i and np.asarray(r['heatmap']).shape==(7,7) for i,r in enumerate(rows))
 with pytest.raises(ValueError,match='duplicate'):p.extract(d,run,cfg,g,c,emit,SyntheticBackend(g))


def pipeline(tmp_path,monkeypatch,real_hook=False):
 d,t,cfg=fixture(tmp_path/'images');run=tmp_path/'S01-E022-synthetic';run.mkdir();snap=run/'input_snapshot';snap.mkdir();c.write(snap/'synthetic.json',dict(synthetic=True));lock=dict(original_rows_digest=c.digest(d['originals']),source_zip_sha256='synthetic',source_files={'synthetic.json':c.sha(snap/'synthetic.json')},source_B12_hits=len(c.baseline(c.scoped(d['originals'],d['candidates'],t,d['image_locations'],cfg['locations']))[1]))
 monkeypatch.setattr(a.inputs,'load',lambda *args:d);monkeypatch.setattr(a.legacy,'metadata',lambda *args:d['records']);monkeypatch.setattr(c,'require_producer',lambda _:None);monkeypatch.setattr(p,'backend',lambda cfg,lock,g,core:SyntheticBackend(g))
 if not real_hook:monkeypatch.setattr(a.sys,'addaudithook',lambda _:None)
 args=SimpleNamespace(run=run,source=tmp_path/'source.zip',metadata=tmp_path/'metadata.json');launch=dict(synthetic=True);c.write(run/'launch.json',launch);g=guard(cfg);result=a.execute(args,cfg,lock,g,launch);return run,result,g,lock


def test_complete_synthetic_path_immutable_originals_frozen_OOF_maps_and_three_figures(tmp_path,monkeypatch):
 run,result,g,lock=pipeline(tmp_path,monkeypatch)
 assert result['comparison']['retention']==1 and result['comparison']['net_GT']>=1
 assert g.counts['linear_solves']==39 and g.counts['head_input_gradient_rows']==14 and g.counts['case_image_decodes']<=6
 assert len(list((run/'analysis').glob('*.png')))==3
 assert c.read(run/'spatial_extraction_receipt.json')['runtime']['synthetic']
 assert 'NOT GT' in (run/'analysis/README_analysis.md').read_text()
 cases=c.read(run/'cases.json');assert cases['kind']=='OOF_appended'
 for row in cases['cases']:assert c.sha(run/row['snapshot'])==row['sha256']


def test_abstain_uses_only_saved_unselected_FIT_maps_after_freeze_no_extra_forward(tmp_path,monkeypatch):
 def zero(model,values,g):g.take('prediction_rows',len(values));return [dict(roles=[0.,0.,0.],rank_score=0.) for _ in values]
 monkeypatch.setattr(l,'predict',zero);run,result,g,lock=pipeline(tmp_path,monkeypatch)
 assert not result['primary_pass'] and result['comparison']['net_GT']==0 and result['comparison']['retention']==1
 cases=c.read(run/'cases.json');assert cases['kind']=='FIT_opportunity_not_selected' and not cases['used_for_learning']
 assert g.counts['head_input_gradient_rows']==14 and g.counts['pixel_reads']==14+len(cases['cases'])


def test_no_main_prediction_before9heads_freeze_before_diagnostics_and39fits(tmp_path,monkeypatch):
 d,t,cfg=fixture(tmp_path/'images');run=tmp_path/'run';run.mkdir();emit,saved=emit_for(run);g=guard(cfg);d['spatial']=p.extract(d,run,cfg,g,c,emit,SyntheticBackend(g));monkeypatch.setattr(c,'require_producer',lambda _:None);predict=l.predict
 def checked(model,values,g):
  assert g.counts['model_fits']>=9
  if g.counts['model_fits']>9:assert (run/'prediction_freeze_receipt.json').exists()
  return predict(model,values,g)
 monkeypatch.setattr(l,'predict',checked);models,support,added=a.fit_and_freeze(d,t,run,cfg,g,emit)
 assert g.counts['linear_solves']==39 and len(saved['jackknife.json']['fits'])==10 and all(m['coefficient_count']==11 for m in models)


def test_current_held_features_and_GT_do_not_change_own_fit(tmp_path,monkeypatch):
 d,t,cfg=fixture(tmp_path/'images');run=tmp_path/'run';run.mkdir();emit,saved=emit_for(run);g=guard(cfg);d['spatial']=p.extract(d,run,cfg,g,c,emit,SyntheticBackend(g));monkeypatch.setattr(c,'require_producer',lambda _:None);fit=l.fit;models=[]
 def first(values,labels,cfg,g):
  if models:raise RuntimeError('stop first fit')
  m=fit(values,labels,cfg,g);models.append(copy.deepcopy(m));return m
 monkeypatch.setattr(l,'fit',first)
 with pytest.raises(RuntimeError):a.fit_and_freeze(d,t,run,cfg,g,emit)
 before=models.pop();bad=copy.deepcopy(d);targets=copy.deepcopy(t)
 for im,loc in bad['image_locations'].items():
  if loc in cfg['held_groups'][0]:targets[im]=[]
 for row in bad['spatial']:
  if row['location'] in cfg['held_groups'][0]:row['values']=[-1.,1.]
 with pytest.raises((RuntimeError,ValueError)):a.fit_and_freeze(bad,targets,run,cfg,guard(cfg),emit)
 assert models[0]==before

@pytest.mark.parametrize('counter',['backbone_forwards','head_forwards','head_input_gradient_rows','max_semantic_batches','pixel_reads','linear_solves'])
def test_new_caps_fail_closed(counter):
 g=guard();g.counts[counter]=CFG['budget'][counter]
 with pytest.raises(RuntimeError):g.take(counter)

@pytest.mark.parametrize('usage',[(4294967297,0),(0,4294967297)])
def test_GPU_peaks_fail_closed(usage):
 g=guard();g.gpu=lambda:usage
 with pytest.raises(RuntimeError,match='GPU_CAP'):g.check()


def test_Mac_boundary_and_required_thread_environment(monkeypatch):
 with pytest.raises(PermissionError):a.execute(None,CFG,{},guard(),{})
 monkeypatch.setattr(c.e12.runtime,'production_environment',lambda _:None);monkeypatch.delenv('OPENBLAS_NUM_THREADS',raising=False)
 with pytest.raises(PermissionError,match='OPENBLAS'):a.require_producer(CFG)


def test_strict_saved_semantics_reject_rehashed_map_change(tmp_path,monkeypatch):
 run,result,g,lock=pipeline(tmp_path,monkeypatch);receipt=c.read(run/'output_receipt.json');expected={n:c.read(run/n) for n in receipt['files'] if n.endswith('.json') and not n.startswith('input_snapshot/')};bad=c.read(run/'spatial_features.json');bad['rows'][0]['heatmap'][0][0]+=.2;c.write(run/'spatial_features.json',bad);receipt['files']['spatial_features.json']=c.sha(run/'spatial_features.json')
 with pytest.raises(ValueError,match='semantic'):a.verify(run,expected,receipt,lock)


def test_exact_checkpoint_allowlist_hash_and_validator_are_enforced(tmp_path,monkeypatch):
 path=tmp_path/'model.pt';path.write_bytes(b'synthetic model bytes, not a torch checkpoint');digest=c.sha(path);cfg=copy.deepcopy(CFG);cfg['spatial'].update(checkpoint=str(path),checkpoint_sha256=digest);lock=dict(E003_checkpoint=str(path),E003_checkpoint_sha256=digest);calls=[]
 def bridge(cfg,path,g,validate):
  assert validate is c.e8.m.base.validate_reranker_checkpoint
  calls.append(path);return SimpleNamespace(identity={'synthetic':True})
 monkeypatch.setattr(p,'SemanticBackend',bridge);p.backend(cfg,lock,guard(cfg),c);assert calls==[path]
 path.write_bytes(b'changed')
 with pytest.raises(ValueError):p.backend(cfg,lock,guard(cfg),c)
 assert calls==[path]


def test_new_GPU_receipt_never_hides_forward_or_input_gradient_work():
 g=guard();g.gpu=lambda:(1000,2000);g.take('backbone_forwards',3);g.take('head_forwards',3);g.take('head_input_gradient_rows',3);r=g.receipt()
 assert r['backbone_forwards']==r['head_forwards']==r['head_input_gradient_rows']==3
 assert r['peak_GPU_allocated_bytes']==1000 and r['peak_GPU_reserved_bytes']==2000
 assert r['parameter_gradient_steps']==r['backbone_backward_rows']==0
