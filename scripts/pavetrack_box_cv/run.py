#!/usr/bin/env python3
"""S01-E005 frozen-feature bounding-box refinement; producer-only fitting/inference."""
from __future__ import annotations
import argparse,copy,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/pavetrack_ranker_cv'))
import importlib.util
_spec=importlib.util.spec_from_file_location('e003_helpers',ROOT/'scripts/pavetrack_ranker_cv/run.py')
base=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(base)
PROTOCOL='S01-E005-v2'
FEATURES=['cnn_avgpool_'+str(i) for i in range(576)]+['log_aspect','log_area_fraction','width_fraction','height_fraction','center_x_fraction','center_y_fraction']
read,write,check_hash,metrics=base.read,base.write,base.check_hash,base.metrics
box_iou,oracle_coverage,sha256_file=base.box_iou,base.oracle_coverage,base.sha256_file

def verify_source():
 for path,sha in read(ROOT/'docs/research/S01/S01-E005/source_manifest.json')['files'].items():check_hash(ROOT/path,sha)

def features(row,record):
 x1,y1,x2,y2=map(float,row['box_xyxy']);w,h=x2-x1,y2-y1;W,H=record['width'],record['height']
 if not 0<=x1<x2<=W or not 0<=y1<y2<=H:raise ValueError('invalid box')
 return [math.log(w/h),math.log(w*h/(W*H)),w/W,h/H,(x1+x2)/(2*W),(y1+y2)/(2*H)]

def associate(box,targets):
 if not targets:return None
 # Earliest GT index breaks equal-IoU ties.
 index=max(range(len(targets)),key=lambda i:(box_iou(box,targets[i]),-i))
 return index if box_iou(box,targets[index])>=.05 else None

def context_box(box,record,padding):
 return tuple(round(v) for v in base.pad_box(box,record['width'],record['height'],padding))

def contains(crop,target):return crop[0]<=target[0] and crop[1]<=target[1] and crop[2]>=target[2] and crop[3]>=target[3]

def encode(box,target,cfg):
 x1,y1,x2,y2=box;a,b,c,d=target;w,h=x2-x1,y2-y1;tw,th=c-a,d-b
 if min(w,h,tw,th)<=0:raise ValueError('degenerate reference')
 raw=[((a+c)-(x1+x2))/(2*w),((b+d)-(y1+y2))/(2*h),math.log(tw/w),math.log(th/h)]
 bounds=[(-cfg['offset_bound'],cfg['offset_bound'])]*2+[(math.log(cfg['scale_bounds'][0]),math.log(cfg['scale_bounds'][1]))]*2
 clipped=[min(hi,max(lo,v)) for v,(lo,hi) in zip(raw,bounds,strict=True)]
 return clipped,raw!=clipped

def decode(box,delta,record,cfg):
 x1,y1,x2,y2=box;w,h=x2-x1,y2-y1;bounds=[(-cfg['offset_bound'],cfg['offset_bound'])]*2+[(math.log(cfg['scale_bounds'][0]),math.log(cfg['scale_bounds'][1]))]*2
 d=[min(hi,max(lo,base.finite(v))) for v,(lo,hi) in zip(delta,bounds,strict=True)]
 cx=(x1+x2)/2+d[0]*w;cy=(y1+y2)/2+d[1]*h;nw=w*math.exp(d[2]);nh=h*math.exp(d[3]);W,H=record['width'],record['height']
 result=[max(0,min(W,cx-nw/2)),max(0,min(H,cy-nh/2)),max(0,min(W,cx+nw/2)),max(0,min(H,cy+nh/2))]
 fallback=result[2]-result[0]<1 or result[3]-result[1]<1
 return list(box) if fallback else result,{'bounded':list(delta)!=d,'image_clipped':result!=[cx-nw/2,cy-nh/2,cx+nw/2,cy+nh/2],'fallback':fallback}

def suppress(rows,iou):
 result=[];by={}
 for row in sorted(rows,key=lambda r:(-r['score'],str(r['reid']),r['image_id'],tuple(r['box_xyxy']),r['candidate_id'])):
  if not any(box_iou(k['box_xyxy'],row['box_xyxy'])>iou for k in by.get(row['image_id'],[])):
   result.append(row);by.setdefault(row['image_id'],[]).append(row)
 kept={r['candidate_id'] for r in result}
 return [r for r in rows if r['candidate_id'] in kept]

def audit_payload(train,records,cfg):
 by={r['image_id']:r for r in records};matches=[];rates=[]
 for i,row in enumerate(train['rows']):
  rec=by[row['image_id']];index=associate(row['box_xyxy'],rec['crack_boxes_xyxy'])
  if index is not None:
   target=rec['crack_boxes_xyxy'][index];y,clipped=encode(row['box_xyxy'],target,cfg)
   matches.append({'candidate_id':i,'image_id':row['image_id'],'reid':str(row['reid']),'gt_index':index,'target':target,'target_delta':y,'target_clipped':clipped})
 if not matches:raise ValueError('no associated train proposals')
 from collections import Counter
 groups=Counter((m['image_id'],m['gt_index']) for m in matches)
 all_gt=sum(len(r['crack_boxes_xyxy']) for r in records)
 for padding in cfg['context_padding_choices']:
  balanced=sum(float(contains(context_box(train['rows'][m['candidate_id']]['box_xyxy'],by[m['image_id']],padding),m['target']))/(len(groups)*groups[(m['image_id'],m['gt_index'])]) for m in matches)
  hits=sum(contains(context_box(train['rows'][m['candidate_id']]['box_xyxy'],by[m['image_id']],padding),m['target']) for m in matches)
  rates.append({'padding':padding,'contained':hits,'matched':len(matches),'fraction':hits/len(matches),'target_balanced_fraction':balanced})
 selected=next((v['padding'] for v in rates if v['target_balanced_fraction']>=cfg['minimum_context_containment']),None)
 return {'matches':matches,'context_rates':rates,'selected_padding':selected,'status':'ready' if selected is not None else 'stop_input_unobservable','represented_gt':len(groups),'all_train_gt':all_gt,'unrepresented_gt':all_gt-len(groups),'target_clipped_count':sum(m['target_clipped'] for m in matches)}

def embeddings(rows,records,model,transform,device,padding):
 import torch,numpy as np
 from PIL import Image
 from collections import defaultdict
 by=defaultdict(list)
 for i,row in enumerate(rows):by[row['image_id']].append(i)
 X=np.empty((len(rows),len(FEATURES)),dtype=np.float32);model.eval()
 with torch.inference_mode():
  for rec in records:
   with Image.open(rec['prepared_image']) as im:
    im=im.convert('RGB');indices=by[rec['image_id']]
    for start in range(0,len(indices),128):
     ids=indices[start:start+128];crops=[transform(im.crop(context_box(rows[i]['box_xyxy'],rec,padding))) for i in ids]
     z=model.avgpool(model.features(torch.stack(crops).to(device))).flatten(1).cpu().numpy()
     if z.shape!=(len(ids),576):raise ValueError('CNN embedding dimension')
     for j,i in enumerate(ids):X[i]=np.concatenate([z[j],np.asarray(features(rows[i],rec),dtype=np.float32)])
   print(json.dumps({'embedding_image':rec['image_id'],'rows':len(indices)}),flush=True)
 if not np.isfinite(X).all():raise ValueError('nonfinite embedding')
 return X

def lineage(a):
 return {'protocol':PROTOCOL,'config_sha256':base.sha256_file(a.config),'lock_sha256':base.sha256_file(a.lock),'tiled_sha256':base.sha256_file(a.tiled),'ranker_sha256':base.sha256_file(a.old_ranker),'source_development_sha256':base.sha256_file(a.development),'source_validation_sha256':base.sha256_file(a.source_validation),'source_train_sha256':base.sha256_file(a.source_train),'source_manifest_sha256':base.sha256_file(ROOT/'docs/research/S01/S01-E005/source_manifest.json')}

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
 import numpy as np
 if (a.run/'extract_started.json').exists():raise ValueError('refuse duplicate extraction')
 records=[r for r in dev['records'] if r['split']=='train'];audit=audit_payload(train,records,cfg)
 write(a.run/'extract_started.json',lineage(a));write(a.run/'context_audit.json',dict(lineage(a),**audit))
 if audit['selected_padding'] is None:return
 model,transform,device=base.load_models(a,cfg)
 rows=[train['rows'][m['candidate_id']] for m in audit['matches']]
 X=embeddings(rows,records,model,transform,device,audit['selected_padding']);np.savez_compressed(a.run/'train_features.npz',X=X)
 Xv=embeddings(val['rows'],[r for r in dev['records'] if r['split']=='validation'],model,transform,device,audit['selected_padding']);np.savez_compressed(a.run/'validation_features.npz',X=Xv)
 write(a.run/'feature_receipt.json',dict(lineage(a),context_audit_sha256=sha256_file(a.run/'context_audit.json'),train_features_sha256=sha256_file(a.run/'train_features.npz'),validation_features_sha256=sha256_file(a.run/'validation_features.npz'),feature_names=FEATURES,train_rows=len(rows),validation_rows=len(val['rows'])))

def tensors(a,cfg,dev,train):
 import torch,numpy as np
 torch.set_num_threads(cfg['threads']);audit=read(a.run/'context_audit.json');expected=audit_payload(train,[r for r in dev['records'] if r['split']=='train'],cfg)
 if audit!=dict(lineage(a),**expected) or audit['selected_padding'] is None:raise ValueError('train context audit mismatch')
 receipt=read(a.run/'feature_receipt.json')
 for k,v in dict(lineage(a),context_audit_sha256=sha256_file(a.run/'context_audit.json'),feature_names=FEATURES,train_rows=len(audit['matches']),validation_rows=len(read(a.source_validation)['rows'])).items():
  if receipt.get(k)!=v:raise ValueError('feature lineage '+k)
 for split in ['train','validation']:check_hash(a.run/(split+'_features.npz'),receipt[split+'_features_sha256'])
 with np.load(a.run/'train_features.npz',allow_pickle=False) as data:X=torch.tensor(data['X'],dtype=torch.float64)
 if X.shape!=(len(audit['matches']),len(FEATURES)) or not bool(torch.isfinite(X).all()):raise ValueError('feature shape/finite')
 by={r['image_id']:r for r in dev['records'] if r['split']=='train'}
 geom=torch.tensor([features(train['rows'][m['candidate_id']],by[m['image_id']]) for m in audit['matches']],dtype=torch.float32).double()
 if not torch.equal(X[:,-6:],geom):raise ValueError('train geometry feature mismatch')
 Y=torch.tensor([m['target_delta'] for m in audit['matches']],dtype=torch.float64)
 from collections import Counter
 groups=Counter((m['image_id'],m['gt_index']) for m in audit['matches']);weights=torch.tensor([1/(len(groups)*groups[(m['image_id'],m['gt_index'])]) for m in audit['matches']],dtype=torch.float64)
 means=X.mean(0);stds=X.std(0,correction=0).clamp_min(1e-8);D=torch.cat(((X-means)/stds,torch.ones(len(X),1,dtype=torch.float64)),1)
 return D,Y,weights,means,stds,receipt

def evaluate_rows(rows,records,model,X,cfg):
 import numpy as np
 if X.shape!=(len(rows),len(FEATURES)) or not np.isfinite(X).all():raise ValueError('evaluation features invalid')
 by={r['image_id']:r for r in records};coef=np.asarray(model['coefficients']);z=(X.astype(np.float64)-model['means'])/model['stds'];pred=z@coef+model['intercepts'];old=[];corrected=[]
 for i,row in enumerate(rows):
  rec=by[row['image_id']]
  if str(row['reid'])!=str(rec['reid']):raise ValueError('evaluation location')
  if not np.array_equal(X[i,-6:],np.asarray(features(row,rec),dtype=np.float32)):raise ValueError('evaluation geometry mismatch')
  r=copy.deepcopy(row);r['candidate_id']=i;r['score']=math.sqrt(r['proposer_confidence']*r['probability']);old.append(r)
  nr=copy.deepcopy(r);nr['original_box_xyxy']=list(r['box_xyxy']);nr['box_xyxy'],nr['correction_flags']=decode(r['box_xyxy'],pred[i].tolist(),rec,cfg);corrected.append(nr)
 baseline_rows=suppress(old,cfg['refinement_nms_iou']);new=suppress(corrected,cfg['refinement_nms_iou'])
 if baseline_rows!=old:raise ValueError('baseline additional NMS changed original E003 set')
 targets={r['image_id']:r['crack_boxes_xyxy'] for r in records};locations={r['image_id']:str(r['reid']) for r in records};bm=metrics(old,targets,locations,'score');cm=metrics(new,targets,locations,'score');delta=None if bm['macro_location_recall'] is None else cm['macro_location_recall']-bm['macro_location_recall']
 return dict(baseline=bm,candidate=cm,delta=delta,baseline_rows=old,rows=new,all_corrected_rows=corrected,targets=targets,image_locations=locations,baseline_oracle=oracle_coverage(old,targets,locations),oracle=oracle_coverage(new,targets,locations),suppressed_count=len(corrected)-len(new))

def fit(a,cfg,lock,dev,val,train):
 import torch,numpy as np
 if (a.run/'fit_started.json').exists():raise ValueError('refuse duplicate fit')
 D,Y,w,means,stds,receipt=tensors(a,cfg,dev,train);write(a.run/'fit_started.json',lineage(a))
 reg=torch.eye(D.shape[1],dtype=torch.float64)*cfg['l2_strength'];reg[-1,-1]=0
 A=D.T@(w[:,None]*D)+reg;B=D.T@(w[:,None]*Y);theta=torch.linalg.solve(A,B)
 def objective(t):return .5*((D@t-Y).square().sum(1)*w).sum()+.5*cfg['l2_strength']*t[:-1].square().sum()
 initial=float(objective(torch.zeros_like(theta)));final=float(objective(theta));grad=float((A@theta-B).abs().max())
 if not bool(torch.isfinite(theta).all()) or grad>1e-8 or final>initial+1e-12:raise ValueError('numerical ridge inadmissible')
 model=dict(lineage(a),feature_names=FEATURES,coefficients=theta[:-1].tolist(),intercepts=theta[-1].tolist(),means=means.tolist(),stds=stds.tolist(),initial_loss=initial,final_loss=final,gradient_inf=grad,selected_padding=read(a.run/'context_audit.json')['selected_padding'],feature_receipt_sha256=sha256_file(a.run/'feature_receipt.json'))
 write(a.run/'box_model.json',model)
 with np.load(a.run/'validation_features.npz',allow_pickle=False) as data:e=evaluate_rows(val['rows'],[r for r in dev['records'] if r['split']=='validation'],model,data['X'],cfg)
 if e['baseline']!=val['candidate']:raise ValueError('E003 comparator mismatch')
 write(a.run/'evaluation_validation.json',dict(lineage(a),split='validation',box_model_sha256=sha256_file(a.run/'box_model.json'),primary_pass=None,**e));print(json.dumps({k:v for k,v in e.items() if k not in ('rows','baseline_rows','all_corrected_rows','targets','image_locations')},indent=2),flush=True)

def verify_model(a,cfg,dev,train):
 import torch
 model=read(a.run/'box_model.json')
 for k,v in dict(lineage(a),feature_names=FEATURES,feature_receipt_sha256=sha256_file(a.run/'feature_receipt.json'),selected_padding=read(a.run/'context_audit.json')['selected_padding']).items():
  if model.get(k)!=v:raise ValueError('model lineage '+k)
 D,Y,w,means,stds,receipt=tensors(a,cfg,dev,train)
 if not torch.equal(means,torch.tensor(model['means'],dtype=torch.float64)) or not torch.equal(stds,torch.tensor(model['stds'],dtype=torch.float64)):raise ValueError('train scaler mismatch')
 theta=torch.tensor(model['coefficients']+[model['intercepts']],dtype=torch.float64)
 if theta.shape!=(len(FEATURES)+1,4) or not bool(torch.isfinite(theta).all()):raise ValueError('model shape/finite')
 reg=torch.eye(D.shape[1],dtype=torch.float64)*cfg['l2_strength'];reg[-1,-1]=0;A=D.T@(w[:,None]*D)+reg;B=D.T@(w[:,None]*Y)
 initial=float(.5*(Y.square().sum(1)*w).sum());final=float(.5*((D@theta-Y).square().sum(1)*w).sum()+.5*cfg['l2_strength']*theta[:-1].square().sum());grad=float((A@theta-B).abs().max())
 for key,value in [('initial_loss',initial),('final_loss',final),('gradient_inf',grad)]:
  if abs(base.finite(model[key])-value)>1e-12:raise ValueError('model objective replay '+key)
 if final>initial+1e-12 or grad>1e-8:raise ValueError('numerical model inadmissible')
 return model

def verify_validation(a,cfg,dev,val):
 import numpy as np
 model=verify_model(a,cfg,dev,read(a.source_train));e=read(a.run/'evaluation_validation.json')
 with np.load(a.run/'validation_features.npz',allow_pickle=False) as data:expected=evaluate_rows(val['rows'],[r for r in dev['records'] if r['split']=='validation'],model,data['X'],cfg)
 if e!=dict(lineage(a),split='validation',box_model_sha256=sha256_file(a.run/'box_model.json'),primary_pass=None,**expected):raise ValueError('validation recompute/lineage mismatch')
 if e['baseline']!=val['candidate']:raise ValueError('comparator mismatch')
 return e

def authorization_fields(a,cfg,lock):return dict(lineage(a),status='authorized_after_model_and_validation_freeze',box_model_sha256=base.sha256_file(a.run/'box_model.json'),validation_sha256=base.sha256_file(a.run/'evaluation_validation.json'),confirmatory_test_locations=lock['confirmatory_test_locations'],score=cfg['score'],primary_delta=cfg['primary_delta'])

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

def validate_download_payload(payload,lock,url):
 if payload.get('url')!=url or payload.get('remote_size')!=lock['archive_bytes']:raise ValueError('download URL/size mismatch')
 locations=payload.get('requested_locations',[])
 if len(locations)!=len(set(locations)) or set(locations)!=set(lock['confirmatory_test_locations']):raise ValueError('download locations mismatch')
 selected=payload.get('selected_files',0)
 if selected<=0 or payload.get('extracted_files')!=selected or payload.get('failed_files')!=0 or payload.get('failures')!=[] or len(payload.get('files',[]))!=selected:raise ValueError('incomplete download manifest')
 if {f['location'] for f in payload['files']}!=set(locations):raise ValueError('download missing locations')
 if len({f['target'] for f in payload['files']})!=selected:raise ValueError('duplicate acquired images')
 if any(f['status'] not in ('downloaded_crc_verified','already_complete_crc_verified') for f in payload['files']):raise ValueError('unverified download CRC')

def validate_download(a,cfg,lock):
 import binascii
 if a.download_manifest is None:raise ValueError('download manifest required')
 payload=read(a.download_manifest);validate_download_payload(payload,lock,cfg['archive_url'])
 by_source={};total=0
 for item in payload['files']:
  path=Path(item['target']);root=(a.run/'confirmatory_download/images').resolve()
  if path.resolve()!=root/item['location']/Path(item['member']).name:raise ValueError('download path outside exact location root')
  data=path.read_bytes()
  if len(data)!=item['bytes'] or (binascii.crc32(data)&0xffffffff)!=item['crc']:raise ValueError('acquired image CRC/size changed')
  by_source[str(path.resolve())]=item;total+=len(data)
 if total!=payload['extracted_bytes']:raise ValueError('extracted total bytes mismatch')
 return by_source

def prepare(a,cfg,lock,dev,val):
 verify_authorization(a,cfg,lock,dev,val);acquired=validate_download(a,cfg,lock);check_hash(a.workbook,lock['workbook_sha256'])
 import pandas as pd
 from PIL import Image
 from prepare_dataset import find_source,materialize
 from common import CRACK_CLASSES,clip_xyxy,xywh_to_xyxy,parse_numeric_list
 if (a.run/'manifest_test.json').exists():raise ValueError('test manifest exists')
 frame=pd.read_excel(a.workbook);frame['reid']=frame['reid'].astype(str);frame=frame[frame['reid'].isin(lock['confirmatory_test_locations'])];records=[]
 for (reid,name),group in frame.groupby(['reid','img_name'],sort=True):
  source=find_source([a.image_root],reid,name)
  if source is None:raise FileNotFoundError(f'{reid}/{name}')
  if str(source.resolve()) not in acquired:raise ValueError('prepared source absent from acquisition receipt')
  with Image.open(source) as im:w,h=im.size
  annotations=[{'category':str(r.category),'box_xyxy':clip_xyxy(xywh_to_xyxy(parse_numeric_list(r.bbox)),w,h)} for r in group.itertuples(index=False)]
  identity=f'reid-{reid}__{name}';p=a.run/'prepared/images/test'/identity;materialize(source,p,'copy')
  records.append({'image_id':identity,'reid':reid,'split':'test','prepared_image':str(p.resolve()),'prepared_image_sha256':base.sha256_file(p),'width':w,'height':h,'crack_boxes_xyxy':[r['box_xyxy'] for r in annotations if r['category'] in CRACK_CLASSES],'all_annotations':annotations})
 base.validate_members(records,lock,'test');write(a.run/'manifest_test.json',dict(lineage(a),test_authorization_sha256=base.sha256_file(a.run/'test_authorization.json'),download_manifest_sha256=base.sha256_file(a.download_manifest),records=records))

def evaluate(a,cfg,lock,dev,val):
 auth=verify_authorization(a,cfg,lock,dev,val);validate_download(a,cfg,lock)
 if (a.run/'evaluation_test.json').exists() or (a.run/'test_evaluation_started.json').exists():raise ValueError('refuse duplicate test evaluation')
 manifest=read(a.run/'manifest_test.json')
 for k,v in dict(lineage(a),test_authorization_sha256=sha256_file(a.run/'test_authorization.json'),download_manifest_sha256=sha256_file(a.download_manifest)).items():
  if manifest.get(k)!=v:raise ValueError('test manifest lineage')
 records=manifest['records'];base.validate_members(records,lock,'test');write(a.run/'test_evaluation_started.json',dict(lineage(a),authorization_sha256=sha256_file(a.run/'test_authorization.json')))
 model,transform,device=base.load_models(a,cfg);rows=base.infer_candidates(records,a,cfg);rows=base.score_rows(rows,records,model,transform,device,cfg);boxmodel=verify_model(a,cfg,dev,read(a.source_train));X=embeddings(rows,records,model,transform,device,boxmodel['selected_padding']);e=evaluate_rows(rows,records,boxmodel,X,cfg)
 write(a.run/'evaluation_test.json',dict(lineage(a),split='test',box_model_sha256=sha256_file(a.run/'box_model.json'),manifest_sha256=sha256_file(a.run/'manifest_test.json'),authorization_sha256=sha256_file(a.run/'test_authorization.json'),download_manifest_sha256=sha256_file(a.download_manifest),primary_pass=None if e['delta'] is None else e['delta']>=cfg['primary_delta'],**e));print(json.dumps({k:v for k,v in e.items() if k not in ('rows','baseline_rows','all_corrected_rows','targets','image_locations')},indent=2),flush=True)

def main():
 verify_source();p=argparse.ArgumentParser();p.add_argument('stage',choices=['extract','fit','freeze','check-authorization','prepare','evaluate'])
 for name in ['config','lock','tiled','old-ranker','development','source-validation','source-train','run']:p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--download-manifest',type=Path);p.add_argument('--workbook',type=Path);p.add_argument('--image-root',type=Path);a=p.parse_args();cfg=read(a.config);lock=read(a.lock);dev,val,train=validate_inputs(a,cfg,lock);base.frozen_ultralytics_device(cfg,'cuda:1');a.run.mkdir(parents=True,exist_ok=True)
 if a.stage=='extract':extract(a,cfg,lock,dev,val,train)
 elif a.stage=='fit':fit(a,cfg,lock,dev,val,train)
 elif a.stage=='freeze':freeze(a,cfg,lock,dev,val)
 elif a.stage=='check-authorization':verify_authorization(a,cfg,lock,dev,val)
 elif a.stage=='prepare':prepare(a,cfg,lock,dev,val)
 else:evaluate(a,cfg,lock,dev,val)
if __name__=='__main__':main()
