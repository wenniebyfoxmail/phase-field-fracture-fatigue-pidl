import copy,importlib.util,json,hashlib
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=module('e023_test',ROOT/'scripts/pavetrack_pixel_selector/run.py');c=a.c;p=a.spatial;l=a.learning;pixel=a.pixel
old=module('e023_fixture',ROOT/'tests/pavetrack_semantic_selector/test_semantic_selector.py');CFG=c.read(ROOT/c.CONTRACT/'run_config.json')
def guard(cfg=CFG):return a.Guard(cfg,memory=lambda:100)
def emit_for(run):
 saved={}
 def emit(n,v):saved[n]=copy.deepcopy(v);c.write(run/n,v)
 return emit,saved

def fixture(root):
 d,t,prior=old.fixture(root);cfg=copy.deepcopy(CFG);cfg['input_counts']=prior['input_counts'];cfg['budget'].update({k:v for k,v in prior['budget'].items() if k in ['source_image_decodes','spatial_feature_rows','pixel_reads','source_image_reads','training_target_rows']});n=len(d['candidates']);eligible=sum(r['eligible'] for r in d['candidates']);cfg['budget'].update(backbone_forwards=n,pixel_training_sample_rows=n*2*16,pixel_map_prediction_rows=n*3,pixel_evaluation_rows=n,prediction_rows=eligible*3,feature_cache_bytes=n*40*14*14*4)
 annotations={}
 for j,(im,rec) in enumerate(d['images'].items()):
  rows=[];image=Image.new('RGB',(rec['width'],rec['height']),(20,20,20));draw=ImageDraw.Draw(image)
  for z,b in enumerate(t[im]):
   poly=[[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]]];rows.append(dict(workbook_row=j*10+z,image_id=im,location=rec['location'],width=rec['width'],height=rec['height'],category='Transverse Crack',box_xyxy=b,polygon=poly));draw.polygon([tuple(v) for v in poly],fill=(200,20,20))
  if not rows:rows=[dict(workbook_row=j*10,image_id=im,location=rec['location'],width=rec['width'],height=rec['height'],category='Patch',box_xyxy=[0,0,2,2],polygon=[[0,0],[2,0],[2,2],[0,2]])]
  annotations[im]=rows;path=Path(rec['prepared_image']);image.save(path,format='PNG');rec['prepared_image_sha256']=c.sha(path)
  for m in d['manifest']:
   if m['image_id']==im:m['prepared_image_sha256']=rec['prepared_image_sha256']
 d['annotations']=annotations;return d,t,cfg

class SyntheticBackend:
 identity={'synthetic':True,'not_real_E003':True,'feature_shape':[40,14,14]}
 def __init__(self,g):self.g=g
 def features(self,image,contexts):
  self.g.take('max_semantic_batches');self.g.take('backbone_forwards',len(contexts));out=np.zeros((len(contexts),40,14,14),dtype=np.float32)
  pixels=np.asarray(image)
  for j,ctx in enumerate(contexts):
   xs,ys=pixel.centers(ctx,14);out[j,0]=(pixels[np.ix_(ys,xs)][:,:,0].astype(float)-20)/180
  return out


def test_native_random_backbone_shape_no_training_or_checkpoint():
 import torch
 from torchvision.models import mobilenet_v3_small
 torch.set_num_threads(1);model=mobilenet_v3_small(weights=None).eval()
 with torch.no_grad():z=model.features[:6](torch.zeros(1,3,224,224))
 assert z.shape==(1,40,14,14)


def test_region_raster_union_excludes_noncrack_and_fixed_floor_centers():
 rows=[dict(category='Transverse Crack',polygon=[[0,0],[10,0],[10,10],[0,10]]),dict(category='Patch',polygon=[[15,15],[19,15],[19,19],[15,19]])];mask=pixel.raster(rows,dict(width=20,height=20));y=pixel.labels(mask,[0,0,20,20]);xs,ys=pixel.centers([0,0,20,20],14)
 assert y.shape==(14,14) and y[0,0]==1 and y[-1,-1]==0
 assert pixel.labels(mask,[0,0,20,20],[1,5,8,12]).tolist()==y[np.ix_([1,5,8,12],[1,5,8,12])].tolist()
 mask.close()

@pytest.mark.parametrize('field',['image','dimensions','class','polygon','bbox','duplicate','coverage'])
def test_annotation_loader_rejects_out_of_scope_or_invalid_refs(tmp_path,field):
 d,t,cfg=fixture(tmp_path/'images');rows=[r for values in d['annotations'].values() for r in values];a.inputs.validate_annotations({'rows':rows},d['images'],len(rows));bad=copy.deepcopy(rows)
 if field=='image':bad[0]['image_id']='sealed'
 elif field=='dimensions':bad[0]['width']+=1
 elif field=='class':bad[0]['category']='unknown'
 elif field=='polygon':bad[0]['polygon'][0][0]=float('nan')
 elif field=='bbox':bad[0]['box_xyxy']=[0,0,0,1]
 elif field=='duplicate':bad[1]['workbook_row']=bad[0]['workbook_row']
 else:bad=bad[1:]
 with pytest.raises(ValueError):a.inputs.validate_annotations({'rows':bad},d['images'],len(rows))


def extracted(tmp_path):
 d,t,cfg=fixture(tmp_path/'images');run=tmp_path/'run';run.mkdir();emit,saved=emit_for(run);g=guard(cfg);d['pixel_features'],d['contexts']=p.extract(d,run,cfg,g,c,emit,SyntheticBackend(g));return d,t,cfg,run,emit,saved,g


def test_stream_cache_counts_and_exact_candidate_identity(tmp_path):
 d,t,cfg,run,emit,saved,g=extracted(tmp_path)
 assert isinstance(d['pixel_features'],np.memmap) and d['pixel_features'].shape==(14,40,14,14)
 assert g.counts['backbone_forwards']==14 and g.counts['source_image_decodes']==14 and g.counts['head_forwards']==0
 with pytest.raises(ValueError,match='duplicate'):p.extract(d,run,cfg,g,c,emit,SyntheticBackend(g))


def test_supervised_pixel_fit41_parameters_hierarchy_and_no_GT_in_prediction(tmp_path):
 d,t,cfg,run,emit,saved,g=extracted(tmp_path);held=cfg['held_groups'][0];locs=[x for x in cfg['locations'] if x not in held];anns={im:rows for im,rows in d['annotations'].items() if d['image_locations'][im] in locs}
 m=pixel.fit(d['pixel_features'],d['contexts'],d['candidates'],anns,d['images'],locs,cfg,g,l.ridge)
 assert m['coefficient_count']==41 and len(m['coefficients'])==41 and m['positive_samples']>0 and m['negative_samples']>0
 assert m['FIT_foreground_rate']==m['positive_samples']/m['sample_rows']
 out=pixel.predict(m,d['pixel_features'][:1]);assert out.shape==(1,14,14) and np.isfinite(out).all() and out.max()>out.min()
 with pytest.raises(TypeError):pixel.predict(m,d['pixel_features'][:1],GT=[])
 with pytest.raises(ValueError,match='scope'):pixel.fit(d['pixel_features'],d['contexts'],d['candidates'],d['annotations'],d['images'],locs,cfg,g,l.ridge)


def test_pixel_component_threshold_empty_and_constant_definitions():
 y=np.zeros((14,14),dtype=np.uint8);v=pixel.component(np.zeros_like(y),y,.1);assert v['Dice']==1 and v['constant_Dice']==1 and v['all_foreground_Dice']==0 and v['constant_Brier']==pytest.approx(.01)
 y[0,0]=1;p=np.zeros_like(y,dtype=float);p[0,0]=.5;v=pixel.component(p,y,.2);assert v['Dice']==1 and v['has_reference_foreground'] and v['Brier']==pytest.approx(.25/196)


def test_exact_area_coverage_and_uniform_map_zero_concentration():
 cov=p.coverage([9.9,19.9,10.1,20.1],[0,0,140,140]);assert cov.sum()==pytest.approx(.04/100)
 d=p.describe(np.ones((14,14)),[0,0,10,10],[20,0,30,10],[0,0,140,140]);assert d['values']==pytest.approx([0,0],abs=1e-16)
 assert p.describe(np.zeros((14,14)),[0,0,10,10],[20,0,30,10],[0,0,140,140])['degenerate']=='zero_mass'


def pipeline(tmp_path,monkeypatch,real_hook=False):
 d,t,cfg=fixture(tmp_path/'images');run=tmp_path/'S01-E023-synthetic';run.mkdir();snap=run/'input_snapshot';snap.mkdir();c.write(snap/'synthetic.json',dict(synthetic=True));c.write(snap/'train_polygons.json',{'rows':[r for rows in d['annotations'].values() for r in rows]});lock=dict(original_rows_digest=c.digest(d['originals']),source_zip_sha256='synthetic',source_files={'synthetic.json':c.sha(snap/'synthetic.json')},annotation_snapshot_sha256=c.sha(snap/'train_polygons.json'),source_B12_hits=len(c.baseline(c.scoped(d['originals'],d['candidates'],t,d['image_locations'],cfg['locations']))[1]))
 monkeypatch.setattr(a.inputs,'load',lambda *args:d);monkeypatch.setattr(a.legacy,'metadata',lambda *args:d['records']);monkeypatch.setattr(c,'require_producer',lambda _:None);monkeypatch.setattr(p,'backend',lambda cfg,lock,g,core:SyntheticBackend(g))
 if not real_hook:monkeypatch.setattr(a.sys,'addaudithook',lambda _:None)
 args=SimpleNamespace(run=run,source=tmp_path/'source.zip',metadata=tmp_path/'metadata.json');launch=dict(synthetic=True);c.write(run/'launch.json',launch);g=guard(cfg);result=a.execute(args,cfg,lock,g,launch);return run,result,g,lock


def test_complete_synthetic_mask_supervision_and_policy_chain(tmp_path,monkeypatch):
 run,result,g,lock=pipeline(tmp_path,monkeypatch)
 assert result['comparison']['retention']==1 and result['comparison']['net_GT']>=1
 assert g.counts['pixel_head_fits']==3 and g.counts['model_fits']==9 and g.counts['linear_solves']==12
 assert g.counts['pixel_training_sample_rows']==448 and g.counts['pixel_map_prediction_rows']==42 and g.counts['pixel_evaluation_rows']==14
 assert len(list((run/'analysis').glob('*.png')))==4 and not (run/'jackknife.json').exists()
 freeze=c.read(run/'prediction_freeze_receipt.json');assert all(c.sha(run/n)==h for n,h in freeze['files'].items())
 assert not c.read(run/'pixel_evaluation.json')['used_to_choose_model_or_gate']
 cases=c.read(run/'cases.json');assert cases['kind']=='OOF_appended' and all(v['map_scope']=='OOF held' for v in cases['cases'])


def test_abstain_cases_are_labelled_FIT_model_maps_and_no_extra_forward(tmp_path,monkeypatch):
 def zero(model,values,g):g.take('prediction_rows',len(values));return [dict(roles=[0,0,0],rank_score=0.) for _ in values]
 monkeypatch.setattr(l,'predict',zero);run,result,g,lock=pipeline(tmp_path,monkeypatch);assert result['comparison']['net_GT']==0 and result['comparison']['retention']==1
 cases=c.read(run/'cases.json');assert cases['kind']=='FIT_opportunity_not_selected' and all(v['map_scope'].startswith('FIT own-model') for v in cases['cases']);assert g.counts['backbone_forwards']==14 and g.counts['pixel_reads']==14+len(cases['cases'])


def test_held_annotations_and_features_do_not_change_own_pixel_fit(tmp_path):
 d,t,cfg,run,emit,saved,g=extracted(tmp_path);held=cfg['held_groups'][0];locs=[x for x in cfg['locations'] if x not in held];anns={im:rows for im,rows in d['annotations'].items() if d['image_locations'][im] in locs}
 first=pixel.fit(d['pixel_features'],d['contexts'],d['candidates'],anns,d['images'],locs,cfg,g,l.ridge);cache=np.array(d['pixel_features'])
 for row in d['candidates']:
  if row['location'] in held:cache[row['index']]=999
 second=pixel.fit(cache,d['contexts'],d['candidates'],anns,d['images'],locs,cfg,guard(cfg),l.ridge);assert first==second


def test_all12_heads_verify_before_roles_and_pixel_evaluation_after_freeze(tmp_path,monkeypatch):
 predict=l.predict;evaluate=pixel.evaluate
 def checked(model,values,g):assert g.counts['pixel_head_fits']==3 and g.counts['model_fits']==9;return predict(model,values,g)
 def checked_evaluate(data,models,maps,cfg,g):
  # Entire OOF bank was already committed by fit_and_freeze.
  assert g.counts['final_OOF_comparisons']==1
  return evaluate(data,models,maps,cfg,g)
 monkeypatch.setattr(l,'predict',checked);monkeypatch.setattr(pixel,'evaluate',checked_evaluate);pipeline(tmp_path,monkeypatch)

@pytest.mark.parametrize('counter',['pixel_head_fits','pixel_training_sample_rows','pixel_map_prediction_rows','pixel_evaluation_rows','linear_solves','backbone_forwards'])
def test_new_work_counters_fail_closed(counter):
 g=guard();g.counts[counter]=CFG['budget'][counter]
 with pytest.raises(RuntimeError):g.take(counter)


def test_Mac_and_GPU_budget_boundaries():
 with pytest.raises(PermissionError):a.execute(None,CFG,{},guard(),{})
 g=guard();g.gpu=lambda:(4294967297,0)
 with pytest.raises(RuntimeError,match='GPU_CAP'):g.check()


def test_pixel_single_class_fails_without_fabricating_support(tmp_path):
 d,t,cfg,run,emit,saved,g=extracted(tmp_path);locs=cfg['locations'];anns=copy.deepcopy(d['annotations'])
 for rows in anns.values():
  for row in rows:row['category']='Patch'
 with pytest.raises(ValueError,match='both region classes'):pixel.fit(d['pixel_features'],d['contexts'],d['candidates'],anns,d['images'],locs,cfg,g,l.ridge)
 assert g.counts['pixel_head_fits']==0 and g.counts['model_fits']==0


def test_failed_pixel_fit_stops_before_any_role_prediction(tmp_path,monkeypatch):
 d,t,cfg,run,emit,saved,g=extracted(tmp_path);fit=pixel.fit;calls=[]
 def broken(*args):
  calls.append(1)
  if len(calls)==2:raise ValueError('synthetic pixel failure')
  return fit(*args)
 monkeypatch.setattr(c,'require_producer',lambda _:None);monkeypatch.setattr(pixel,'fit',broken);monkeypatch.setattr(l,'predict',lambda *args:pytest.fail('role prediction before pixel validation'))
 with pytest.raises(ValueError,match='pixel failure'):a.fit_and_freeze(d,t,run,cfg,g,emit)
 assert not (run/'OOF_predictions.json').exists() and g.counts['model_fits']==0


def test_per_image_aggregation_and_FIT_constant_are_saved(tmp_path,monkeypatch):
 run,result,g,lock=pipeline(tmp_path,monkeypatch);component=c.read(run/'pixel_evaluation.json');assert len(component['locations'])==12
 for k in range(3):
  model=c.read(run/f'pixel_model_fold_{k}.json');assert model['FIT_foreground_rate']==model['positive_samples']/model['sample_rows']
  assert [s['weight_mass'] for s in model['strata_support']]==pytest.approx([.5,.5])
 for site in component['locations']:
  ims=[r for r in component['images'] if r['location']==site['location']]
  assert site['Brier']==pytest.approx(np.mean([r['Brier'] for r in ims]))
 assert component['macro']['Brier']==pytest.approx(np.mean([r['Brier'] for r in component['locations']]))


def test_strict_saved_semantics_reject_rehashed_pixel_component_tamper(tmp_path,monkeypatch):
 run,result,g,lock=pipeline(tmp_path,monkeypatch);receipt=c.read(run/'output_receipt.json');expected={n:c.read(run/n) for n in receipt['files'] if n.endswith('.json') and not n.startswith('input_snapshot/')};bad=c.read(run/'pixel_evaluation.json');bad['macro']['Brier']=.999;c.write(run/'pixel_evaluation.json',bad);receipt['files']['pixel_evaluation.json']=c.sha(run/'pixel_evaluation.json')
 with pytest.raises(ValueError,match='semantic'):a.verify(run,expected,receipt,lock)


def test_combined_input_loader_private_polygon_hash_and_bank_alignment(tmp_path):
 import zipfile
 probe=module('e023_source_zip_fixture',ROOT/'tests/pavetrack_role_probe/test_probe.py');source,rawdata,oldcfg,lock=probe.synthetic_zip(tmp_path);d,t,cfg=fixture(tmp_path/'images');lock.update(source_image_root=str(tmp_path/'images'),source_images=len(t),image_identity_member='input_snapshot/candidate_identity.json')
 with zipfile.ZipFile(source) as z:raw={n:z.read(n) for n in z.namelist()}
 raw['input_snapshot/candidate_identity.json']=json.dumps(dict(rows=d['manifest'])).encode();selected=set(lock['source_files'])-{'output_receipt.json'};raw['output_receipt.json']=json.dumps(dict(files={n:hashlib.sha256(raw[n]).hexdigest() for n in selected})).encode()
 with zipfile.ZipFile(source,'w') as z:
  for n,v in raw.items():z.writestr(n,v)
 annotations=tmp_path/'private_polygons.json';rows=[r for vals in d['annotations'].values() for r in vals];c.write(annotations,{'rows':rows});lock.update(source_zip_sha256=c.sha(source),source_zip_bytes=source.stat().st_size,source_files={n:hashlib.sha256(raw[n]).hexdigest() for n in lock['source_files']},annotation_snapshot=str(annotations),annotation_snapshot_sha256=c.sha(annotations),annotation_snapshot_rows=len(rows));run=tmp_path/'loaded';run.mkdir();g=guard(cfg)
 loaded=a.inputs.load(source,run,cfg,lock,g,c,a.legacy,a.prior_inputs)
 assert loaded['annotations']==d['annotations'] and loaded['candidates']==d['candidates'] and not g.counts
 assert not (run/'input_snapshot/pooled_features.npy').exists() and c.sha(run/'input_snapshot/train_polygons.json')==lock['annotation_snapshot_sha256']


def test_changed_map_rehashed_by_output_receipt_cannot_override_trusted_freeze(tmp_path,monkeypatch):
 run,result,g,lock=pipeline(tmp_path,monkeypatch);receipt=c.read(run/'output_receipt.json');expected={n:c.read(run/n) for n in receipt['files'] if n.endswith('.json') and not n.startswith('input_snapshot/')}
 path=run/'pixel_maps_fold_0.npy';mapping=np.load(path,mmap_mode='r+');mapping[0,0,0]=.456789;mapping.flush();del mapping;receipt['files']['pixel_maps_fold_0.npy']=c.sha(path)
 with pytest.raises(ValueError):a.verify(run,expected,receipt,lock)
