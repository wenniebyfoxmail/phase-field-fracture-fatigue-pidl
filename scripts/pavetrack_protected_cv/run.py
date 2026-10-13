#!/usr/bin/env python3
"""S01-E006 protected original candidate bank + out-of-fold correction selector."""
from __future__ import annotations
import argparse,copy,json,math,sys,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
_spec=importlib.util.spec_from_file_location('e005_protected_helpers',ROOT/'scripts/pavetrack_box_cv/run.py');box=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(box)
base=box.base
read,write,check_hash,metrics,sha256_file,box_iou,oracle_coverage=box.read,box.write,box.check_hash,box.metrics,box.sha256_file,box.box_iou,box.oracle_coverage
PROTOCOL='S01-E006-v1'
FEATURES=['spatial_'+str(i) for i in range(864)]+box.FEATURES[-6:]+['logit_frozen_E003_score','is_correction']

def verify_source():
 for path,sha in read(ROOT/'docs/research/S01/S01-E006/source_manifest.json')['files'].items():check_hash(ROOT/path,sha)

def lineage(a):
 result={'protocol':PROTOCOL,'source_manifest_sha256':sha256_file(ROOT/'docs/research/S01/S01-E006/source_manifest.json')}
 for name in ['config','lock','tiled','old_ranker','development','source_validation','source_train','corrector','old_audit','old_train_features','old_validation']:
  result[name+'_sha256']=sha256_file(getattr(a,name))
 return result

def validate_inputs(a,cfg,lock):
 if cfg['protocol']!=PROTOCOL or lock['protocol']!=PROTOCOL or cfg['features']!=FEATURES:raise ValueError('protocol/features')
 base.validate_data_lock(lock)
 for name,key in [('tiled','tiled_sha256'),('old_ranker','initial_ranker_sha256'),('development','source_development_sha256'),('source_validation','source_validation_sha256'),('source_train','source_train_sha256'),('corrector','corrector_sha256'),('old_audit','old_audit_sha256'),('old_train_features','old_train_features_sha256'),('old_validation','old_validation_sha256')]:check_hash(getattr(a,name),cfg[key])
 dev=read(a.development);val=read(a.source_validation);train=read(a.source_train);corr=read(a.corrector);prior=read(a.old_validation);audit=read(a.old_audit)
 if dev['protocol']!='S01-E002-v1' or dev['workbook_sha256']!=lock['workbook_sha256']:raise ValueError('development identity')
 for split in ['train','validation']:base.validate_members([r for r in dev['records'] if r['split']==split],lock,split)
 if val['protocol']!='S01-E003-v1' or val['split']!='validation' or train['protocol']!='S01-E003-v1' or corr['protocol']!='S01-E005-v2' or audit['protocol']!='S01-E005-v2' or prior['protocol']!='S01-E005-v2' or prior['split']!='validation':raise ValueError('inherited protocol')
 if base.validate_reranker_checkpoint(a.old_ranker)['epoch']!=val['epoch']:raise ValueError('ranker epoch')
 tr={r['image_id']:r for r in dev['records'] if r['split']=='train'}
 for row in train['rows']:
  if row['image_id'] not in tr or str(row['reid'])!=str(tr[row['image_id']]['reid']):raise ValueError('train membership')
 for payload in [val,train,corr,audit,prior]:
  if payload['source_development_sha256']!=cfg['source_development_sha256']:raise ValueError('inherited development lineage')
 records=[r for r in dev['records'] if r['split']=='validation'];targets={r['image_id']:r['crack_boxes_xyxy'] for r in records};locations={r['image_id']:str(r['reid']) for r in records}
 if val['targets']!=targets or val['image_locations']!=locations or prior['targets']!=targets or prior['image_locations']!=locations:raise ValueError('validation reference')
 if len(prior['all_corrected_rows'])!=len(val['rows']):raise ValueError('prior correction IDs')
 for i,(row,oldrow) in enumerate(zip(prior['all_corrected_rows'],val['rows'],strict=True)):
  if row['candidate_id']!=i or row['original_box_xyxy']!=oldrow['box_xyxy'] or row['score']!=math.sqrt(oldrow['proposer_confidence']*oldrow['probability']):raise ValueError('prior correction changed original lineage')
 return dev,val,train,corr,audit

def folds(lock):return {location:i%4 for i,location in enumerate(sorted(lock['train_locations'],key=int))}

def fit_ridge(X,Y,groups,l2):
 import torch
 from collections import Counter
 X=torch.tensor(X,dtype=torch.float64);Y=torch.tensor(Y,dtype=torch.float64);counts=Counter(groups);w=torch.tensor([1/(len(counts)*counts[g]) for g in groups],dtype=torch.float64)
 means=X.mean(0);stds=X.std(0,correction=0).clamp_min(1e-8);D=torch.cat(((X-means)/stds,torch.ones(len(X),1,dtype=torch.float64)),1);R=torch.eye(D.shape[1],dtype=torch.float64)*l2;R[-1,-1]=0;A=D.T@(w[:,None]*D)+R;B=D.T@(w[:,None]*Y);theta=torch.linalg.solve(A,B)
 initial=float(.5*(Y.square().sum(1)*w).sum());final=float(.5*((D@theta-Y).square().sum(1)*w).sum()+.5*l2*theta[:-1].square().sum());grad=float((A@theta-B).abs().max())
 if not bool(torch.isfinite(theta).all()) or grad>1e-8 or final>initial+1e-12:raise ValueError('crossfit numerical inadmissible')
 return {'means':means.tolist(),'stds':stds.tolist(),'coefficients':theta[:-1].tolist(),'intercepts':theta[-1].tolist(),'initial_loss':initial,'final_loss':final,'gradient_inf':grad}

def predict_corrections(rows,records,X,model,cfg):
 import numpy as np
 if X.shape!=(len(rows),582) or not np.isfinite(X).all():raise ValueError('context feature shape')
 by={r['image_id']:r for r in records};z=(X.astype(np.float64)-model['means'])/model['stds'];pred=z@np.asarray(model['coefficients'])+model['intercepts'];result=[]
 for i,row in enumerate(rows):
  r=copy.deepcopy(row);r['parent_id']=i;r['original_box_xyxy']=list(r['box_xyxy']);r['box_xyxy'],r['correction_flags']=box.decode(r['box_xyxy'],pred[i].tolist(),by[r['image_id']],cfg);result.append(r)
 return result

def protected_bank(originals,corrections,cfg):
 from collections import defaultdict
 original=[];by=defaultdict(list)
 for i,row in enumerate(originals):
  r=copy.deepcopy(row);r.update(parent_id=i,candidate_id='o:'+str(i),kind='original',E003_score=math.sqrt(r['proposer_confidence']*r['probability']));r['score']=r['E003_score'];original.append(r);by[r['image_id']].append(r)
 chosen=set()
 for rows in by.values():chosen.update(r['parent_id'] for r in sorted(rows,key=lambda r:(-r['E003_score'],tuple(r['box_xyxy']),r['parent_id']))[:cfg['parent_cap']])
 paired=[]
 for i,row in enumerate(corrections):
  if row['parent_id']!=i or row['original_box_xyxy']!=original[i]['box_xyxy']:raise ValueError('correction parent changed')
  if i not in chosen:continue
  r=copy.deepcopy(row);r.update(candidate_id='c:'+str(i),kind='correction',E003_score=original[i]['E003_score'],score=original[i]['E003_score']);r['parent_id']=i;paired.extend([original[i],r])
 return original,paired,{'protected_count':len(original),'paired_parents':len(chosen)}

def coordinate_choice(original,paired,probabilities,cfg):
 from collections import defaultdict
 if len(paired)!=len(probabilities):raise ValueError('pair probabilities shape')
 by=defaultdict(list)
 for row in original:by[row['image_id']].append(row)
 proposals={};tie=0;lower=0
 for j in range(0,len(paired),2):
  old,new=paired[j:j+2]
  if old['parent_id']!=new['parent_id'] or old['kind']!='original' or new['kind']!='correction':raise ValueError('pair order')
  po,pn=map(base.finite,probabilities[j:j+2]);i=old['parent_id']
  if pn>po:proposals[i]=new
  elif pn==po:tie+=1
  else:lower+=1
 result=[copy.deepcopy(r) for r in original];accepted=defaultdict(list);conflicts=0
 for old in sorted(original,key=lambda r:(-r['E003_score'],str(r['reid']),r['image_id'],tuple(r['box_xyxy']),r['parent_id'])):
  i=old['parent_id']
  if i not in proposals:continue
  new=proposals[i]
  if any(r['parent_id']!=i and box_iou(new['box_xyxy'],r['box_xyxy'])>cfg['refinement_nms_iou'] for r in by[old['image_id']]) or any(box_iou(new['box_xyxy'],r['box_xyxy'])>cfg['refinement_nms_iou'] for r in accepted[old['image_id']]):conflicts+=1;continue
  result[i]['box_xyxy']=list(new['box_xyxy']);result[i]['chosen_correction']=True;result[i]['correction_flags']=new.get('correction_flags',{'bounded':False,'image_clipped':False,'fallback':False});result[i]['original_box_xyxy']=list(old['box_xyxy']);accepted[old['image_id']].append(new)
 for old,new in zip(original,result,strict=True):
  if old['parent_id']!=new['parent_id'] or old['score']!=new['score'] or old['E003_score']!=new['E003_score']:raise ValueError('parent identity/score mutation')
 return result,{'proposed_choices':len(proposals),'accepted_choices':sum(len(rs) for rs in accepted.values()),'conflict_fallbacks':conflicts,'probability_ties_original':tie,'lower_probability_original':lower}

def geom(row,rec):
 f=box.features(row,rec);p=max(1e-6,min(1-1e-6,row['E003_score']));return f+[math.log(p/(1-p)),float(row['kind']=='correction')]

def spatial_embeddings(rows,records,model,transform,device,cfg):
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
     ids=indices[start:start+128];crops=[transform(im.crop(box.context_box(rows[i]['box_xyxy'],rec,cfg['crop_padding']))) for i in ids];maps=model.features[:-1](torch.stack(crops).to(device));z=torch.nn.functional.adaptive_avg_pool2d(maps,(3,3)).flatten(1).cpu().numpy()
     if z.shape!=(len(ids),864):raise ValueError('spatial node dimension')
     for j,i in enumerate(ids):X[i]=np.concatenate([z[j],np.asarray(geom(rows[i],rec),dtype=np.float32)])
   print(json.dumps({'spatial_image':rec['image_id'],'rows':len(indices)}),flush=True)
 if not np.isfinite(X).all():raise ValueError('nonfinite spatial features')
 return X

def labels(bank,records):
 by={r['image_id']:r for r in records}
 return [int(max((box_iou(row['box_xyxy'],t) for t in by[row['image_id']]['crack_boxes_xyxy']),default=0.)>=.5) for row in bank]

def frozen_score_probabilities(X,checkpoint):
 import torch,numpy as np
 from torchvision import models
 if X.ndim!=2 or X.shape[1]!=576 or not np.isfinite(X).all():raise ValueError('scorer features finite/shape')
 model=models.mobilenet_v3_small(weights=None);model.classifier[-1]=torch.nn.Linear(model.classifier[-1].in_features,2);model.load_state_dict(base.validate_reranker_checkpoint(checkpoint)['state_dict']);model.eval();result=[]
 with torch.inference_mode():
  for start in range(0,len(X),512):result.extend(model.classifier(torch.tensor(X[start:start+512],dtype=torch.float32)).softmax(1)[:,1].tolist())
 return result

def verify_train_scores(rows,X,checkpoint):
 probabilities=frozen_score_probabilities(X,checkpoint)
 if len(rows)!=len(probabilities):raise ValueError('train score length')
 for row,p in zip(rows,probabilities,strict=True):
  score=math.sqrt(row['proposer_confidence']*p)
  if row['probability']!=p or row['score']!=score or row['E003_score']!=score:raise ValueError('frozen E003 train score replay')
 return probabilities

def extract(a,cfg,lock,dev,val,train,corr,audit):
 import numpy as np,torch
 torch.set_num_threads(cfg['threads'])
 if (a.run/'extract_started.json').exists():raise ValueError('refuse duplicate extraction')
 write(a.run/'extract_started.json',lineage(a));records=[r for r in dev['records'] if r['split']=='train'];model,transform,device=base.load_models(a,cfg)
 scorer=box.embeddings(train['rows'],records,model,transform,device,cfg['crop_padding'])[:,:576];np.savez_compressed(a.run/'scorer_features.npz',X=scorer);probabilities=frozen_score_probabilities(scorer,a.old_ranker)
 rows=[dict(row,probability=p,score=math.sqrt(row['proposer_confidence']*p),E003_score=math.sqrt(row['proposer_confidence']*p)) for row,p in zip(train['rows'],probabilities,strict=True)]
 X=box.embeddings(rows,records,model,transform,device,4.);np.savez_compressed(a.run/'context_features.npz',X=X)
 with np.load(a.old_train_features,allow_pickle=False) as f:Xm=f['X']
 if Xm.shape!=(len(audit['matches']),582):raise ValueError('old train features shape')
 expected=box.audit_payload(train,records,cfg)
 if expected['matches']!=audit['matches']:raise ValueError('association replay')
 fs=folds(lock);cross=[];corrected=[None]*len(rows)
 for fold in range(4):
  inds=[i for i,m in enumerate(audit['matches']) if fs[m['reid']]!=fold];matches=[audit['matches'][i] for i in inds];foldmodel=fit_ridge(Xm[inds],[m['target_delta'] for m in matches],[(m['image_id'],m['gt_index']) for m in matches],cfg['corrector_l2'])
  held=[i for i,r in enumerate(rows) if fs[str(r['reid'])]==fold];fitloc=sorted({m['reid'] for m in matches},key=int);heldloc=sorted(k for k,v in fs.items() if v==fold)
  if set(fitloc)&set(heldloc):raise ValueError('crossfit overlap')
  temp=predict_corrections([rows[i] for i in held],records,X[held],foldmodel,cfg)
  for i,r in zip(held,temp,strict=True):r['parent_id']=i;corrected[i]=r
  cross.append(dict(fold=fold,fit_locations=fitloc,held_locations=heldloc,fit_ids=inds,**foldmodel))
 original,training_bank,counts=protected_bank(rows,corrected,cfg);by={r['image_id']:r for r in records}
 Xt=spatial_embeddings(training_bank,records,model,transform,device,cfg);np.savez_compressed(a.run/'selector_train_features.npz',X=Xt)
 write(a.run/'crossfit_models.json',dict(lineage(a),fold_assignment=fs,models=cross))
 write(a.run/'train_bank.json',dict(lineage(a),original_rows=rows,all_corrections=corrected,bank=training_bank,labels=labels(training_bank,records),counts=counts))
 vr=[r for r in dev['records'] if r['split']=='validation'];voriginal,vbank,vcounts=protected_bank(val['rows'],[dict(r,parent_id=r['candidate_id']) for r in read(a.old_validation)['all_corrected_rows']],cfg);Xv=spatial_embeddings(vbank,vr,model,transform,device,cfg);np.savez_compressed(a.run/'selector_validation_features.npz',X=Xv)
 write(a.run/'validation_bank.json',dict(lineage(a),original_rows=voriginal,bank=vbank,counts=vcounts))
 files=['scorer_features.npz','context_features.npz','selector_train_features.npz','selector_validation_features.npz','crossfit_models.json','train_bank.json','validation_bank.json'];write(a.run/'feature_receipt.json',dict(lineage(a),files={f:sha256_file(a.run/f) for f in files},feature_names=FEATURES))

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

def verified_cache(a,cfg,dev,train,audit):
 import numpy as np,torch
 torch.set_num_threads(cfg['threads']);receipt=read(a.run/'feature_receipt.json')
 for k,v in dict(lineage(a),feature_names=FEATURES).items():
  if receipt.get(k)!=v:raise ValueError('feature lineage '+k)
 if set(receipt['files'])!={'scorer_features.npz','context_features.npz','selector_train_features.npz','selector_validation_features.npz','crossfit_models.json','train_bank.json','validation_bank.json'}:raise ValueError('cache file set')
 for f,h in receipt['files'].items():check_hash(a.run/f,h)
 data=read(a.run/'train_bank.json');cross=read(a.run/'crossfit_models.json');vdata=read(a.run/'validation_bank.json');tr=[r for r in dev['records'] if r['split']=='train'];by={r['image_id']:r for r in tr};fs=folds(read(a.lock))
 if len(cross['models'])!=4 or {fm['fold'] for fm in cross['models']}!=set(range(4)) or cross['fold_assignment']!=fs or box.audit_payload(train,tr,cfg)['matches']!=audit['matches']:raise ValueError('fold/audit drift')
 for payload in [data,cross,vdata]:
  for k,v in lineage(a).items():
   if payload.get(k)!=v:raise ValueError('cache lineage '+k)
 if len(data['original_rows'])!=len(train['rows']):raise ValueError('train identity length')
 for old,new in zip(train['rows'],data['original_rows'],strict=True):
  for key in ['image_id','reid','box_xyxy','proposer_confidence']:
   if old[key]!=new[key]:raise ValueError('original train identity')
 with np.load(a.run/'scorer_features.npz',allow_pickle=False) as f:scorer=f['X']
 verify_train_scores(data['original_rows'],scorer,a.old_ranker)
 with np.load(a.old_train_features,allow_pickle=False) as f:Xm=f['X']
 with np.load(a.run/'context_features.npz',allow_pickle=False) as f:Xc=f['X']
 if Xc.shape!=(len(train['rows']),582) or not np.isfinite(Xc).all():raise ValueError('crossfit context features')
 for i,row in enumerate(data['original_rows']):
  if not np.array_equal(Xc[i,-6:],np.asarray(box.features(row,by[row['image_id']]),dtype=np.float32)):raise ValueError('context geometry/order')
 expected=[None]*len(train['rows'])
 for fm in cross['models']:
  fold=fm['fold'];inds=[i for i,m in enumerate(audit['matches']) if fs[m['reid']]!=fold];matches=[audit['matches'][i] for i in inds]
  if fm['fit_locations']!=sorted({m['reid'] for m in matches},key=int) or fm['fit_ids']!=inds or set(fm['fit_locations'])&set(fm['held_locations']) or fm['held_locations']!=sorted((k for k,v in fs.items() if v==fold),key=int):raise ValueError('crossfit training leak')
  # Replay normal equations without fitting another head.
  X=torch.tensor(Xm[inds],dtype=torch.float64);Y=torch.tensor([m['target_delta'] for m in matches],dtype=torch.float64)
  from collections import Counter
  counts=Counter((m['image_id'],m['gt_index']) for m in matches);w=torch.tensor([1/(len(counts)*counts[(m['image_id'],m['gt_index'])]) for m in matches],dtype=torch.float64);mu=X.mean(0);sd=X.std(0,correction=0).clamp_min(1e-8)
  if not torch.allclose(mu,torch.tensor(fm['means'],dtype=torch.float64),atol=1e-12,rtol=0) or not torch.allclose(sd,torch.tensor(fm['stds'],dtype=torch.float64),atol=1e-12,rtol=0):raise ValueError('crossfit scaler')
  D=torch.cat(((X-mu)/sd,torch.ones(len(X),1,dtype=torch.float64)),1);theta=torch.tensor(fm['coefficients']+[fm['intercepts']],dtype=torch.float64);R=torch.eye(D.shape[1],dtype=torch.float64)*cfg['corrector_l2'];R[-1,-1]=0;grad=float(((D.T@(w[:,None]*D)+R)@theta-D.T@(w[:,None]*Y)).abs().max());initial=float(.5*(Y.square().sum(1)*w).sum());final=float(.5*((D@theta-Y).square().sum(1)*w).sum()+.5*cfg['corrector_l2']*theta[:-1].square().sum())
  if not bool(torch.isfinite(theta).all()) or grad>1e-8 or final>initial+1e-12 or abs(final-fm['final_loss'])>1e-12 or abs(initial-fm['initial_loss'])>1e-12 or abs(grad-fm['gradient_inf'])>1e-12:raise ValueError('crossfit objective/gradient')
  held=[i for i,r in enumerate(data['original_rows']) if fs[str(r['reid'])]==fold];temp=predict_corrections([data['original_rows'][i] for i in held],tr,Xc[held],fm,cfg)
  for i,row in zip(held,temp,strict=True):row['parent_id']=i;expected[i]=row
 if expected!=data['all_corrections']:raise ValueError('OOF correction replay')
 original,bank,counts=protected_bank(data['original_rows'],expected,cfg)
 if bank!=data['bank'] or counts!=data['counts'] or labels(bank,tr)!=data['labels']:raise ValueError('train bank/labels replay')
 original,valbank,valcounts=protected_bank(read(a.source_validation)['rows'],[dict(r,parent_id=r['candidate_id']) for r in read(a.old_validation)['all_corrected_rows']],cfg)
 if original!=vdata['original_rows'] or valbank!=vdata['bank'] or valcounts!=vdata['counts']:raise ValueError('validation pair replay')
 with np.load(a.run/'selector_train_features.npz',allow_pickle=False) as f:X=f['X']
 if X.shape!=(len(bank),len(FEATURES)) or not np.isfinite(X).all():raise ValueError('selector train shape')
 for i,row in enumerate(bank):
  if not np.array_equal(X[i,-8:],np.asarray(geom(row,by[row['image_id']]),dtype=np.float32)):raise ValueError('train geometry/order')
 return data,receipt,X

def selector_weights(rows,y):
 import torch
 from collections import Counter
 # Equal location and parent-pair base masses, followed by exact .5/.5 class balance.
 parents=Counter(r['reid'] for r in rows if r['kind']=='original');prior=torch.tensor([1/(len(parents)*parents[r['reid']]*2) for r in rows],dtype=torch.float64);positive=prior[y==1].sum();negative=prior[y==0].sum()
 if min(float(positive),float(negative))<=0:raise ValueError('empty validity class')
 return torch.where(y==1,.5*prior/positive,.5*prior/negative)

def selector_tensors(data,X):
 import torch
 X=torch.tensor(X,dtype=torch.float64);y=torch.tensor(data['labels'],dtype=torch.float64);means=X.mean(0);stds=X.std(0,correction=0).clamp_min(1e-8);D=(X-means)/stds;w=selector_weights(data['bank'],y);return D,y,w,means,stds

def admitted_targets(rows,targets,metric):
 threshold=metric['global_score_threshold'];available={im:set(range(len(ts))) for im,ts in targets.items()};hits=set();fp=0;used=0
 if threshold is not None:
  for row in sorted(rows,key=lambda r:(-r['score'],str(r['reid']),r['image_id'],tuple(r['box_xyxy']))):
   if row['score']<threshold:break
   im=row['image_id'];iou,index=max(((box_iou(row['box_xyxy'],targets[im][i]),i) for i in available[im]),default=(0.,-1));used+=1
   if iou>=.5:available[im].remove(index);hits.add((im,index))
   else:fp+=1
 if used!=metric['detections_used'] or fp!=metric['false_positives'] or len(hits)!=sum(r['true_positives'] for r in metric['locations']):raise ValueError('greedy target retention replay')
 return hits

def evaluate_bank(vdata,records,model,X,cfg):
 import numpy as np
 bank=vdata['bank'];original=vdata['original_rows'];by={r['image_id']:r for r in records}
 if X.shape!=(len(bank),len(FEATURES)) or not np.isfinite(X).all():raise ValueError('evaluation feature shape')
 for i,row in enumerate(bank):
  if not np.array_equal(X[i,-8:],np.asarray(geom(row,by[row['image_id']]),dtype=np.float32)):raise ValueError('validation geometry')
 z=((X.astype(np.float64)-model['means'])/model['stds'])@np.asarray(model['coefficients'])+model['intercept'];prob=np.empty(len(z));positive=z>=0;prob[positive]=1/(1+np.exp(-z[positive]));prob[~positive]=np.exp(z[~positive])/(1+np.exp(z[~positive]));rows,choice=coordinate_choice(original,bank,prob.tolist(),cfg)
 targets={r['image_id']:r['crack_boxes_xyxy'] for r in records};locations={r['image_id']:str(r['reid']) for r in records};bm=metrics(original,targets,locations,'score');cm=metrics(rows,targets,locations,'score');oldhits=admitted_targets(original,targets,bm);newhits=admitted_targets(rows,targets,cm);ret=None if not oldhits else len(oldhits&newhits)/len(oldhits);delta=None if bm['macro_location_recall'] is None else cm['macro_location_recall']-bm['macro_location_recall'];passed=None if delta is None or ret is None else delta>=cfg['primary_delta'] and ret>=cfg['minimum_retention']
 return dict(baseline=bm,candidate=cm,delta=delta,retention=ret,retained_old_targets=len(oldhits&newhits),lost_old_targets=len(oldhits-newhits),new_detected_targets=len(newhits-oldhits),protected_primary_pass=passed,baseline_rows=original,rows=rows,pair_rows=bank,pair_probabilities=prob.tolist(),choice=choice,targets=targets,image_locations=locations,baseline_oracle=oracle_coverage(original,targets,locations),oracle=oracle_coverage(rows,targets,locations))

def fit(a,cfg,dev,train,audit):
 import torch,numpy as np
 if (a.run/'fit_started.json').exists():raise ValueError('refuse duplicate selector fit')
 data,receipt,X=verified_cache(a,cfg,dev,train,audit);D,y,w,means,stds=selector_tensors(data,X);theta=torch.zeros(len(FEATURES)+1,dtype=torch.float64,requires_grad=True)
 def objective():return (torch.nn.functional.binary_cross_entropy_with_logits(D@theta[:-1]+theta[-1],y,reduction='none')*w).sum()+.5*cfg['l2_strength']*theta[:-1].square().sum()
 initial=float(objective().detach());write(a.run/'fit_started.json',lineage(a));calls=[];opt=torch.optim.LBFGS([theta],max_iter=cfg['max_iterations'],tolerance_grad=cfg['gradient_tolerance'],tolerance_change=1e-12,line_search_fn='strong_wolfe')
 def closure():
  opt.zero_grad();loss=objective();base.finite(loss.item());loss.backward();calls.append(float(loss.detach()));return loss
 opt.step(closure);opt.zero_grad();loss=objective();loss.backward();grad=float(theta.grad.abs().max());final=float(loss.detach())
 if not bool(torch.isfinite(theta).all()) or grad>1e-5 or final>initial+1e-12:raise ValueError('selector numerical inadmissible')
 model=dict(lineage(a),feature_names=FEATURES,means=means.tolist(),stds=stds.tolist(),coefficients=theta[:-1].detach().tolist(),intercept=float(theta[-1].detach()),initial_loss=initial,final_loss=final,gradient_inf=grad,closure_calls=len(calls),feature_receipt_sha256=sha256_file(a.run/'feature_receipt.json'));write(a.run/'selector_model.json',model);write(a.run/'fit_history.json',calls)
 vdata=read(a.run/'validation_bank.json')
 with np.load(a.run/'selector_validation_features.npz',allow_pickle=False) as f:e=evaluate_bank(vdata,[r for r in dev['records'] if r['split']=='validation'],model,f['X'],cfg)
 if e['baseline']!=read(a.source_validation)['candidate']:raise ValueError('E003 exact comparator')
 write(a.run/'evaluation_validation.json',dict(lineage(a),split='validation',selector_model_sha256=sha256_file(a.run/'selector_model.json'),**e));print(json.dumps({k:v for k,v in e.items() if k not in ['baseline_rows','rows','pair_rows','pair_probabilities','targets','image_locations']},indent=2),flush=True)

def verify_model(a,cfg,dev,train,audit):
 import torch
 model=read(a.run/'selector_model.json');data,receipt,X=verified_cache(a,cfg,dev,train,audit)
 for k,v in dict(lineage(a),feature_names=FEATURES,feature_receipt_sha256=sha256_file(a.run/'feature_receipt.json')).items():
  if model.get(k)!=v:raise ValueError('selector model lineage '+k)
 D,y,w,means,stds=selector_tensors(data,X)
 if not torch.allclose(means,torch.tensor(model['means'],dtype=torch.float64),atol=1e-12,rtol=0) or not torch.allclose(stds,torch.tensor(model['stds'],dtype=torch.float64),atol=1e-12,rtol=0):raise ValueError('selector scaler')
 theta=torch.tensor(model['coefficients']+[model['intercept']],dtype=torch.float64,requires_grad=True)
 if theta.shape!=(len(FEATURES)+1,) or not bool(torch.isfinite(theta).all()):raise ValueError('selector coefficients')
 loss=(torch.nn.functional.binary_cross_entropy_with_logits(D@theta[:-1]+theta[-1],y,reduction='none')*w).sum()+.5*cfg['l2_strength']*theta[:-1].square().sum();loss.backward();grad=float(theta.grad.abs().max());initial=float((torch.nn.functional.binary_cross_entropy_with_logits(torch.zeros_like(y),y,reduction='none')*w).sum());final=float(loss.detach())
 if abs(initial-model['initial_loss'])>1e-12 or abs(final-model['final_loss'])>1e-12 or abs(grad-model['gradient_inf'])>1e-12 or grad>1e-5 or final>initial+1e-12:raise ValueError('selector objective replay')
 return model

def verify_validation(a,cfg,dev,val):
 import numpy as np
 model=verify_model(a,cfg,dev,read(a.source_train),read(a.old_audit));e=read(a.run/'evaluation_validation.json')
 with np.load(a.run/'selector_validation_features.npz',allow_pickle=False) as f:expected=evaluate_bank(read(a.run/'validation_bank.json'),[r for r in dev['records'] if r['split']=='validation'],model,f['X'],cfg)
 if e!=dict(lineage(a),split='validation',selector_model_sha256=sha256_file(a.run/'selector_model.json'),**expected) or e['baseline']!=val['candidate']:raise ValueError('validation replay')
 return e

def pending_fields(a,e):return dict(lineage(a),run_id=a.run.name,status='pending_independent_development_review',selector_model_sha256=sha256_file(a.run/'selector_model.json'),validation_sha256=sha256_file(a.run/'evaluation_validation.json'),delta=e['delta'],retention=e['retention'],fresh_test_access=False)

def review_fields(a):return dict(run_id=a.run.name,pending_sha256=sha256_file(a.run/'pending_confirmatory_review.json'),status='PASS_INDEPENDENT_DEVELOPMENT_REVIEW',protocol=PROTOCOL,source_manifest_sha256=sha256_file(ROOT/'docs/research/S01/S01-E006/source_manifest.json'),selector_model_sha256=sha256_file(a.run/'selector_model.json'),validation_sha256=sha256_file(a.run/'evaluation_validation.json'))

def authorization_fields(a,cfg,lock):return dict(lineage(a),status='authorized_after_independent_development_review',run_id=a.run.name,pending_sha256=sha256_file(a.run/'pending_confirmatory_review.json'),selector_model_sha256=sha256_file(a.run/'selector_model.json'),validation_sha256=sha256_file(a.run/'evaluation_validation.json'),independent_review_sha256=a.review_sha256,confirmatory_test_locations=lock['confirmatory_test_locations'],primary_delta=cfg['primary_delta'],minimum_retention=cfg['minimum_retention'])

def freeze(a,cfg,lock,dev,val):
 if (a.run/'pending_confirmatory_review.json').exists() or (a.run/'development_decision.json').exists():raise ValueError('freeze already exists')
 e=verify_validation(a,cfg,dev,val)
 if e['protected_primary_pass'] is True:write(a.run/'pending_confirmatory_review.json',pending_fields(a,e))
 else:write(a.run/'development_decision.json',dict(lineage(a),status='stop_development_negative' if e['protected_primary_pass'] is not None else 'inconclusive',delta=e['delta'],retention=e['retention'],fresh_test_access=False))

def reviewed_pass(a,cfg,dev,val):
 e=verify_validation(a,cfg,dev,val)
 if e['protected_primary_pass'] is not True or a.independent_review is None or a.review_sha256 is None:raise ValueError('independent development review required')
 pending=a.run/'pending_confirmatory_review.json'
 if not pending.exists() or read(pending)!=pending_fields(a,e):raise ValueError('exact pending independent-review state required')
 check_hash(a.independent_review,a.review_sha256)
 if read(a.independent_review)!=review_fields(a):raise ValueError('independent review bound fields')
 return e

def authorize(a,cfg,lock,dev,val):
 reviewed_pass(a,cfg,dev,val)
 if (a.run/'test_authorization.json').exists():raise ValueError('duplicate authorization')
 write(a.run/'test_authorization.json',authorization_fields(a,cfg,lock))

def verify_authorization(a,cfg,lock,dev,val):
 reviewed_pass(a,cfg,dev,val);auth=read(a.run/'test_authorization.json')
 if auth!=authorization_fields(a,cfg,lock):raise ValueError('complete authorization mismatch')
 return auth

def evaluate(a,cfg,lock,dev,val):
 verify_authorization(a,cfg,lock,dev,val);validate_download(a,cfg,lock)
 if (a.run/'test_evaluation_started.json').exists():raise ValueError('duplicate test evaluation')
 manifest=read(a.run/'manifest_test.json')
 for k,v in dict(lineage(a),test_authorization_sha256=sha256_file(a.run/'test_authorization.json'),download_manifest_sha256=sha256_file(a.download_manifest)).items():
  if manifest.get(k)!=v:raise ValueError('test manifest lineage')
 records=manifest['records'];base.validate_members(records,lock,'test');write(a.run/'test_evaluation_started.json',lineage(a));cnn,transform,device=base.load_models(a,cfg);rows=base.score_rows(base.infer_candidates(records,a,cfg),records,cnn,transform,device,cfg);X=box.embeddings(rows,records,cnn,transform,device,4.);corrections=predict_corrections(rows,records,X,read(a.corrector),cfg);original,bank,counts=protected_bank(rows,corrections,cfg);Xs=spatial_embeddings(bank,records,cnn,transform,device,cfg);npz=a.run/'selector_test_features.npz'
 import numpy as np
 np.savez_compressed(npz,X=Xs);np.savez_compressed(a.run/'test_context_features.npz',X=X);write(a.run/'test_corrections.json',dict(lineage(a),rows=corrections));vdata=dict(original_rows=original,bank=bank,counts=counts);write(a.run/'test_bank.json',dict(lineage(a),**vdata));model=verify_model(a,cfg,dev,read(a.source_train),read(a.old_audit));e=evaluate_bank(vdata,records,model,Xs,cfg);write(a.run/'evaluation_test.json',dict(lineage(a),split='test',selector_model_sha256=sha256_file(a.run/'selector_model.json'),authorization_sha256=sha256_file(a.run/'test_authorization.json'),download_manifest_sha256=sha256_file(a.download_manifest),manifest_sha256=sha256_file(a.run/'manifest_test.json'),**e))

def main():
 verify_source();p=argparse.ArgumentParser();p.add_argument('stage',choices=['extract','fit','freeze','authorize','check-authorization','prepare','evaluate'])
 for name in ['config','lock','tiled','old-ranker','development','source-validation','source-train','corrector','old-audit','old-train-features','old-validation','run']:p.add_argument('--'+name,type=Path,required=True)
 for name in ['download-manifest','workbook','image-root','independent-review']:p.add_argument('--'+name,type=Path)
 p.add_argument('--review-sha256');a=p.parse_args();cfg=read(a.config);lock=read(a.lock);dev,val,train,corr,audit=validate_inputs(a,cfg,lock);base.frozen_ultralytics_device(cfg,'cuda:1');a.run.mkdir(parents=True,exist_ok=True)
 if a.stage=='extract':extract(a,cfg,lock,dev,val,train,corr,audit)
 elif a.stage=='fit':fit(a,cfg,dev,train,audit)
 elif a.stage=='freeze':freeze(a,cfg,lock,dev,val)
 elif a.stage=='authorize':authorize(a,cfg,lock,dev,val)
 elif a.stage=='check-authorization':verify_authorization(a,cfg,lock,dev,val)
 elif a.stage=='prepare':prepare(a,cfg,lock,dev,val)
 else:evaluate(a,cfg,lock,dev,val)
if __name__=='__main__':main()
