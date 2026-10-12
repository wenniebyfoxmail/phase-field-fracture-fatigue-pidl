#!/usr/bin/env python3
"""S01-E004 valid-detection quality head; producer-only fitting/inference."""
from __future__ import annotations
import argparse,copy,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/pavetrack_ranker_cv'))
import importlib.util
_spec=importlib.util.spec_from_file_location('e003_helpers',ROOT/'scripts/pavetrack_ranker_cv/run.py')
base=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(base)
PROTOCOL='S01-E004-v1'
FEATURES=['logit_proposer','logit_crack','log_aspect','log_area_fraction','width_fraction','height_fraction','center_x_fraction','center_y_fraction']
read,write,check_hash,metrics=base.read,base.write,base.check_hash,base.metrics
box_iou,oracle_coverage,sha256_file=base.box_iou,base.oracle_coverage,base.sha256_file

def verify_source():
 for path,sha in read(ROOT/'docs/research/S01/S01-E004/source_manifest.json')['files'].items():check_hash(ROOT/path,sha)

def features(row,record):
 x1,y1,x2,y2=map(float,row['box_xyxy']);w,h=x2-x1,y2-y1;W,H=record['width'],record['height']
 if not 0<=x1<x2<=W or not 0<=y1<y2<=H:raise ValueError('invalid full-image box')
 def logit(p):
  p=base.finite(p)
  if not 0<=p<=1:raise ValueError('invalid probability')
  p=max(1e-6,min(1-1e-6,p));return math.log(p/(1-p))
 result=[logit(row['proposer_confidence']),logit(row['probability']),math.log(w/h),math.log(w*h/(W*H)),w/W,h/H,(x1+x2)/(2*W),(y1+y2)/(2*H)]
 for v in result:base.finite(v)
 return result

def valid_label(row,record):return int(max((base.box_iou(row['box_xyxy'],t) for t in record['crack_boxes_xyxy']),default=0.)>=.5)

def lineage(a):
 return {'protocol':PROTOCOL,'config_sha256':base.sha256_file(a.config),'lock_sha256':base.sha256_file(a.lock),'tiled_sha256':base.sha256_file(a.tiled),'ranker_sha256':base.sha256_file(a.old_ranker),'source_development_sha256':base.sha256_file(a.development),'source_validation_sha256':base.sha256_file(a.source_validation),'source_train_sha256':base.sha256_file(a.source_train),'source_manifest_sha256':base.sha256_file(ROOT/'docs/research/S01/S01-E004/source_manifest.json')}

def validate_inputs(a,cfg,lock):
 if cfg['protocol']!=PROTOCOL or lock['protocol']!=PROTOCOL or cfg['features']!=FEATURES:raise ValueError('protocol/feature identity')
 base.validate_data_lock(lock)
 for arg,key in [(a.tiled,'tiled_sha256'),(a.old_ranker,'initial_ranker_sha256'),(a.development,'source_development_sha256'),(a.source_validation,'source_validation_sha256'),(a.source_train,'source_train_sha256')]:check_hash(arg,cfg[key])
 dev=read(a.development);val=read(a.source_validation);train=read(a.source_train)
 if dev['protocol']!='S01-E002-v1' or set(dev['splits'])!={'train','validation'} or dev['workbook_sha256']!=lock['workbook_sha256']:raise ValueError('source development invalid')
 if val['protocol']!='S01-E003-v1' or val['split']!='validation' or val['source_development_sha256']!=base.sha256_file(a.development):raise ValueError('source validation invalid')
 if train['protocol']!='S01-E003-v1' or train['source_development_sha256']!=base.sha256_file(a.development) or train['tiled_sha256']!=cfg['tiled_sha256']:raise ValueError('source proposals invalid')
 for split in ('train','validation'):base.validate_members([r for r in dev['records'] if r['split']==split],lock,split)
 vr={r['image_id']:r for r in dev['records'] if r['split']=='validation'}
 if val['targets']!={k:r['crack_boxes_xyxy'] for k,r in vr.items()} or val['image_locations']!={k:str(r['reid']) for k,r in vr.items()}:raise ValueError('source validation truth/membership')
 tr={r['image_id']:r for r in dev['records'] if r['split']=='train'}
 for row in train['rows']:
  if row['image_id'] not in tr or str(row['reid'])!=str(tr[row['image_id']]['reid']):raise ValueError('source train membership')
 checkpoint=base.validate_reranker_checkpoint(a.old_ranker)
 if checkpoint['epoch']!=val['epoch']:raise ValueError('E003 epoch identity mismatch')
 return dev,val,train

def extract(a,cfg,lock,dev,val,train):
 if (a.run/'extract_started.json').exists():raise ValueError('refuse duplicate extraction')
 write(a.run/'extract_started.json',lineage(a))
 records=[r for r in dev['records'] if r['split']=='train'];by={r['image_id']:r for r in records}
 model,transform,device=base.load_models(a,cfg)
 rows=base.score_rows(train['rows'],records,model,transform,device,cfg)
 data=[{'image_id':r['image_id'],'reid':r['reid'],'box_xyxy':r['box_xyxy'],'proposer_confidence':r['proposer_confidence'],'probability':r['probability'],'baseline_score':r['score'],'features':features(r,by[r['image_id']]),'valid_label':valid_label(r,by[r['image_id']])} for r in rows]
 write(a.run/'train_features.json',dict(lineage(a),feature_names=FEATURES,rows=data))


def quality_score(row,record,model):
 f=features(row,record)
 logit=model['intercept']+sum(w*(v-mean)/std for w,v,mean,std in zip(model['coefficients'],f,model['means'],model['stds'],strict=True))
 base.finite(logit)
 return 1/(1+math.exp(-logit)) if logit>=0 else math.exp(logit)/(1+math.exp(logit))

def evaluate_rows(rows,records,model):
 by={r['image_id']:r for r in records};new=[]
 for row in rows:
  if row['image_id'] not in by or str(row['reid'])!=str(by[row['image_id']]['reid']):raise ValueError('scoring membership')
  r=copy.deepcopy(row);r['old_score']=math.sqrt(r['proposer_confidence']*r['probability']);r['score']=quality_score(r,by[r['image_id']],model);new.append(r)
 targets={r['image_id']:r['crack_boxes_xyxy'] for r in records};locations={r['image_id']:str(r['reid']) for r in records}
 old=metrics(new,targets,locations,'old_score');candidate=metrics(new,targets,locations,'score')
 delta=None if old['macro_location_recall'] is None else candidate['macro_location_recall']-old['macro_location_recall']
 return dict(baseline=old,candidate=candidate,delta=delta,rows=new,targets=targets,image_locations=locations,oracle=base.oracle_coverage(new,targets,locations))

def fit(a,cfg,lock,dev,val,train):
 import torch
 torch.set_num_threads(cfg['threads']);torch.manual_seed(cfg['seed'])
 if (a.run/'fit_started.json').exists():raise ValueError('refuse duplicate fit')
 data=read(a.run/'train_features.json')
 for k,v in lineage(a).items():
  if data.get(k)!=v:raise ValueError(f'feature lineage {k}')
 tr={r['image_id']:r for r in dev['records'] if r['split']=='train'}
 if data['feature_names']!=FEATURES or len(data['rows'])!=len(train['rows']):raise ValueError('feature membership')
 for row,original in zip(data['rows'],train['rows'],strict=True):
  for key in ('image_id','reid','box_xyxy','proposer_confidence'):
   if row[key]!=original[key]:raise ValueError('train candidates changed')
  if row['valid_label']!=valid_label(row,tr[row['image_id']]) or row['features']!=features(row,tr[row['image_id']]):raise ValueError('train labels/features changed')
 X=torch.tensor([r['features'] for r in data['rows']],dtype=torch.float64);y=torch.tensor([r['valid_label'] for r in data['rows']],dtype=torch.float64)
 positive=int(y.sum());negative=len(y)-positive
 if min(positive,negative)<=0:raise ValueError('empty validity class')
 means=X.mean(0);stds=X.std(0,correction=0).clamp_min(1e-8);X=(X-means)/stds
 weights=torch.where(y==1,.5/positive,.5/negative)
 theta=torch.zeros(len(FEATURES)+1,dtype=torch.float64,requires_grad=True)
 def objective():return (torch.nn.functional.binary_cross_entropy_with_logits(X@theta[:-1]+theta[-1],y,reduction='none')*weights).sum()+.5*cfg['l2_strength']*theta[:-1].square().sum()
 initial=float(objective().detach());calls=[]
 write(a.run/'fit_started.json',dict(lineage(a),positive=positive,negative=negative))
 optimizer=torch.optim.LBFGS([theta],max_iter=cfg['max_iterations'],tolerance_grad=cfg['gradient_tolerance'],tolerance_change=1e-12,line_search_fn='strong_wolfe')
 def closure():
  optimizer.zero_grad();loss=objective();base.finite(loss.item());loss.backward();calls.append(float(loss.detach()));return loss
 optimizer.step(closure);optimizer.zero_grad();loss=objective();loss.backward();grad=float(theta.grad.abs().max());final=float(loss.detach())
 if not bool(torch.isfinite(theta).all()) or grad>1e-5 or final>initial+1e-12:
  write(a.run/'numerical_stop.json',dict(lineage(a),final_loss=base.finite(final),gradient_inf=base.finite(grad),status='numerical_inconclusive_no_validation_or_test'));return
 model=dict(lineage(a),feature_names=FEATURES,coefficients=theta[:-1].detach().tolist(),intercept=float(theta[-1].detach()),means=means.tolist(),stds=stds.tolist(),initial_loss=initial,final_loss=final,gradient_inf=grad,closure_calls=len(calls),train_features_sha256=base.sha256_file(a.run/'train_features.json'))
 write(a.run/'quality_model.json',model);write(a.run/'fit_history.json',calls)
 records=[r for r in dev['records'] if r['split']=='validation'];evaluation=evaluate_rows(val['rows'],records,model)
 if evaluation['baseline']!=val['candidate']:raise ValueError('E003 comparator no longer reproduces')
 write(a.run/'evaluation_validation.json',dict(lineage(a),split='validation',quality_model_sha256=base.sha256_file(a.run/'quality_model.json'),primary_pass=None,**evaluation));print(json.dumps({k:v for k,v in evaluation.items() if k not in ('rows','targets','image_locations')},indent=2),flush=True)


def verify_model(a,cfg):
 model=read(a.run/'quality_model.json')
 for k,v in lineage(a).items():
  if model.get(k)!=v:raise ValueError(f'model lineage {k}')
 if model['feature_names']!=FEATURES or any(len(model[k])!=len(FEATURES) for k in ['coefficients','means','stds']):raise ValueError('model dimensions/order')
 if any(base.finite(v)<=0 for v in model['stds']):raise ValueError('model scaling')
 for k in ['coefficients','means']:
  for v in model[k]:base.finite(v)
 if model['gradient_inf']>1e-5 or model['final_loss']>model['initial_loss']+1e-12:raise ValueError('numerical model not admissible')
 check_hash(a.run/'train_features.json',model['train_features_sha256'])
 import torch
 torch.set_num_threads(cfg['threads']);data=read(a.run/'train_features.json')
 X=torch.tensor([r['features'] for r in data['rows']],dtype=torch.float64);y=torch.tensor([r['valid_label'] for r in data['rows']],dtype=torch.float64)
 means=X.mean(0);stds=X.std(0,correction=0).clamp_min(1e-8)
 if not torch.allclose(means,torch.tensor(model['means'],dtype=torch.float64),atol=1e-12,rtol=0) or not torch.allclose(stds,torch.tensor(model['stds'],dtype=torch.float64),atol=1e-12,rtol=0):raise ValueError('statistics not from train only')
 X=(X-means)/stds;pos=int(y.sum());neg=len(y)-pos
 if min(pos,neg)<=0 or any(r['valid_label'] not in (0,1) for r in data['rows']):raise ValueError('invalid labels')
 weights=torch.where(y==1,.5/pos,.5/neg)
 theta=torch.tensor(model['coefficients']+[model['intercept']],dtype=torch.float64,requires_grad=True)
 loss=(torch.nn.functional.binary_cross_entropy_with_logits(X@theta[:-1]+theta[-1],y,reduction='none')*weights).sum()+.5*cfg['l2_strength']*theta[:-1].square().sum();loss.backward();grad=float(theta.grad.abs().max())
 if abs(float(loss.detach())-model['final_loss'])>1e-12 or abs(grad-model['gradient_inf'])>1e-12:raise ValueError('fit loss/gradient recompute mismatch')
 return model

def verify_validation(a,cfg,dev,val):
 model=verify_model(a,cfg);e=read(a.run/'evaluation_validation.json');expected=evaluate_rows(val['rows'],[r for r in dev['records'] if r['split']=='validation'],model)
 for k,v in dict(lineage(a),split='validation',quality_model_sha256=base.sha256_file(a.run/'quality_model.json'),primary_pass=None,**expected).items():
  if e.get(k)!=v:raise ValueError(f'validation recompute/lineage mismatch {k}')
 if e['baseline']!=val['candidate']:raise ValueError('comparator mismatch')
 return e

def authorization_fields(a,cfg,lock):return dict(lineage(a),status='authorized_after_model_and_validation_freeze',quality_model_sha256=base.sha256_file(a.run/'quality_model.json'),validation_sha256=base.sha256_file(a.run/'evaluation_validation.json'),confirmatory_test_locations=lock['confirmatory_test_locations'],score=cfg['score'],primary_delta=cfg['primary_delta'])

def freeze(a,cfg,lock,dev,val):
 if (a.run/'test_authorization.json').exists():raise ValueError('authorization already exists')
 e=verify_validation(a,cfg,dev,val)
 if e['delta'] is None or e['delta']<cfg['development_delta_to_access_test']:
  write(a.run/'development_decision.json',dict(protocol=PROTOCOL,status='stop_development_negative' if e['delta'] is not None else 'inconclusive',delta=e['delta'],fresh_test_access=False));return
 write(a.run/'test_authorization.json',authorization_fields(a,cfg,lock))

def verify_authorization(a,cfg,lock,dev,val):
 e=verify_validation(a,cfg,dev,val);auth=read(a.run/'test_authorization.json')
 if e['delta'] is None or e['delta']<cfg['development_delta_to_access_test'] or auth!=authorization_fields(a,cfg,lock):raise ValueError('invalid complete test authorization')
 return auth

def prepare(a,cfg,lock,dev,val):
 verify_authorization(a,cfg,lock,dev,val);check_hash(a.workbook,lock['workbook_sha256'])
 import pandas as pd
 from PIL import Image
 from prepare_dataset import find_source,materialize
 from common import CRACK_CLASSES,clip_xyxy,xywh_to_xyxy,parse_numeric_list
 if (a.run/'manifest_test.json').exists():raise ValueError('test manifest exists')
 frame=pd.read_excel(a.workbook);frame['reid']=frame['reid'].astype(str);frame=frame[frame['reid'].isin(lock['confirmatory_test_locations'])];records=[]
 for (reid,name),group in frame.groupby(['reid','img_name'],sort=True):
  source=find_source([a.image_root],reid,name)
  if source is None:raise FileNotFoundError(f'{reid}/{name}')
  with Image.open(source) as im:w,h=im.size
  annotations=[{'category':str(r.category),'box_xyxy':clip_xyxy(xywh_to_xyxy(parse_numeric_list(r.bbox)),w,h)} for r in group.itertuples(index=False)]
  identity=f'reid-{reid}__{name}';p=a.run/'prepared/images/test'/identity;materialize(source,p,'copy')
  records.append({'image_id':identity,'reid':reid,'split':'test','prepared_image':str(p.resolve()),'prepared_image_sha256':base.sha256_file(p),'width':w,'height':h,'crack_boxes_xyxy':[r['box_xyxy'] for r in annotations if r['category'] in CRACK_CLASSES],'all_annotations':annotations})
 base.validate_members(records,lock,'test');write(a.run/'manifest_test.json',dict(lineage(a),test_authorization_sha256=base.sha256_file(a.run/'test_authorization.json'),records=records))

def evaluate(a,cfg,lock,dev,val):
 verify_authorization(a,cfg,lock,dev,val)
 if (a.run/'evaluation_test.json').exists():raise ValueError('refuse duplicate test evaluation')
 manifest=read(a.run/'manifest_test.json')
 for k,v in dict(lineage(a),test_authorization_sha256=base.sha256_file(a.run/'test_authorization.json')).items():
  if manifest.get(k)!=v:raise ValueError('test manifest lineage')
 records=manifest['records'];base.validate_members(records,lock,'test');model,transform,device=base.load_models(a,cfg)
 rows=base.infer_candidates(records,a,cfg);rows=base.score_rows(rows,records,model,transform,device,cfg);quality=verify_model(a,cfg);e=evaluate_rows(rows,records,quality)
 write(a.run/'evaluation_test.json',dict(lineage(a),split='test',quality_model_sha256=base.sha256_file(a.run/'quality_model.json'),manifest_sha256=base.sha256_file(a.run/'manifest_test.json'),authorization_sha256=base.sha256_file(a.run/'test_authorization.json'),primary_pass=None if e['delta'] is None else e['delta']>=cfg['primary_delta'],**e));print(json.dumps({k:v for k,v in e.items() if k not in ('rows','targets','image_locations')},indent=2),flush=True)

def main():
 verify_source();p=argparse.ArgumentParser();p.add_argument('stage',choices=['extract','fit','freeze','check-authorization','prepare','evaluate'])
 for name in ['config','lock','tiled','old-ranker','development','source-validation','source-train','run']:p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--workbook',type=Path);p.add_argument('--image-root',type=Path);a=p.parse_args();cfg=read(a.config);lock=read(a.lock);dev,val,train=validate_inputs(a,cfg,lock);base.frozen_ultralytics_device(cfg,'cuda:1');a.run.mkdir(parents=True,exist_ok=True)
 if a.stage=='extract':extract(a,cfg,lock,dev,val,train)
 elif a.stage=='fit':fit(a,cfg,lock,dev,val,train)
 elif a.stage=='freeze':freeze(a,cfg,lock,dev,val)
 elif a.stage=='check-authorization':verify_authorization(a,cfg,lock,dev,val)
 elif a.stage=='prepare':prepare(a,cfg,lock,dev,val)
 else:evaluate(a,cfg,lock,dev,val)
if __name__=='__main__':main()
