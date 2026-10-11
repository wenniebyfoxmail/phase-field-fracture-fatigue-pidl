#!/usr/bin/env python3
"""S01-E003 frozen tile-native ranking repair; all heavy stages run on producer."""
from __future__ import annotations
import argparse, json, math, random, sys, platform
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/pavetrack_cv'))
sys.path.insert(0, str(ROOT/'scripts/pavetrack_tiled_cv'))
from common import (sha256_file, pad_box, boxes_overlap, box_iou, Detection,
                    recall_at_fp_per_image, validate_reranker_checkpoint,
                    frozen_ultralytics_device, validate_proposer_checkpoint)
from contracts import validate_data_lock
from geometry import Candidate, tile_origins, to_full_image, deterministic_nms
from evaluate_development import oracle_coverage
PROTOCOL='S01-E003-v1'

def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def check_hash(p,expected):
 if sha256_file(Path(p))!=expected: raise ValueError(f'content identity mismatch: {p}')
def finite(x):
 if not math.isfinite(float(x)): raise ValueError('non-finite value')
 return float(x)
def metrics(rows,targets,locations,field):
 return recall_at_fp_per_image([Detection(r['image_id'],r['reid'],r['box_xyxy'],finite(r[field])) for r in rows],targets,locations)
def mining_choice(rows,targets,width,height,cfg):
 positive=[];negative=[]
 for r in sorted(rows,key=lambda r:(-r['old_score'],tuple(r['box_xyxy']))):
  overlap=max((box_iou(r['box_xyxy'],t) for t in targets),default=0.)
  crop=pad_box(r['box_xyxy'],width,height,cfg['crop_padding'])
  if overlap>=cfg['positive_iou'] and len(positive)<cfg['positive_cap']: positive.append((crop,1,'proposal_positive'))
  elif overlap<=cfg['negative_iou'] and len(negative)<cfg['negative_cap'] and not any(boxes_overlap(crop,t) for t in targets): negative.append((crop,0,'old_score_hard_negative'))
 return [(pad_box(t,width,height,cfg['crop_padding']),1,'ground_truth') for t in targets]+positive+negative

def validate_members(records,lock,split):
 expected=set(lock[{'train':'train_locations','validation':'validation_locations','test':'confirmatory_test_locations'}[split]])
 if not records or {str(r['reid']) for r in records}!=expected: raise ValueError(f'{split} membership mismatch')
 if any(r['split']!=split for r in records): raise ValueError('cross-split record')
 if len({r['image_id'] for r in records})!=len(records): raise ValueError('duplicate images')
 for r in records: check_hash(r['prepared_image'],r['prepared_image_sha256'])

def lineage(a):
 return {'protocol':PROTOCOL,'config_sha256':sha256_file(a.config),'lock_sha256':sha256_file(a.lock),'tiled_sha256':sha256_file(a.tiled),'initial_ranker_sha256':sha256_file(a.old_ranker),'source_development_sha256':sha256_file(a.development),'source_validation_sha256':sha256_file(a.source_validation),'source_manifest_sha256':sha256_file(ROOT/'docs/research/S01/S01-E003/source_manifest.json')}

def validate_inputs(a,cfg,lock):
 if cfg['protocol']!=PROTOCOL or lock['protocol']!=PROTOCOL: raise ValueError('wrong protocol')
 validate_data_lock(lock)
 check_hash(a.tiled,cfg['tiled_sha256']);check_hash(a.old_ranker,cfg['initial_ranker_sha256'])
 check_hash(a.development,cfg['source_development_sha256']);check_hash(a.source_validation,cfg['source_validation_sha256'])
 dev=read(a.development);val=read(a.source_validation)
 if dev['protocol']!='S01-E002-v1' or set(dev['splits'])!={'train','validation'}:raise ValueError('invalid source development')
 if dev['workbook_sha256']!=lock['workbook_sha256']:raise ValueError('wrong workbook')
 if val['split']!='validation' or val['manifest_sha256']!=sha256_file(a.development) or val['tiled_proposer_sha256']!=cfg['tiled_sha256'] or val['reranker_sha256']!=cfg['initial_ranker_sha256']:raise ValueError('invalid source validation')
 for split in ('train','validation'):
  validate_members([r for r in dev['records'] if r['split']==split],lock,split)
 expected={r['image_id'] for r in dev['records'] if r['split']=='validation'}
 if set(val['targets'])!=expected or set(val['image_locations'])!=expected:raise ValueError('validation rows membership')
 return dev,val

def load_models(a,cfg):
 import torch
 from torchvision import models,transforms
 device=frozen_ultralytics_device(cfg,'cuda:1')
 validate_proposer_checkpoint(a.tiled,cfg)
 old=validate_reranker_checkpoint(a.old_ranker)
 def classifier(checkpoint):
  m=models.mobilenet_v3_small(weights=None);m.classifier[-1]=torch.nn.Linear(m.classifier[-1].in_features,2);m.load_state_dict(checkpoint['state_dict']);return m.to(device)
 model=classifier(old)
 transform=transforms.Compose([transforms.Resize((224,224)),transforms.ToTensor(),transforms.Normalize([.485,.456,.406],[.229,.224,.225])])
 return model,transform,device

def infer_candidates(records,a,cfg):
 from PIL import Image
 from ultralytics import YOLO
 device=frozen_ultralytics_device(cfg,'cuda:1');model=YOLO(str(a.tiled));rows=[]
 for record in records:
  with Image.open(record['prepared_image']) as im:
   im=im.convert('RGB');w,h=im.size;size=cfg['tile']['size']
   origins=[(x,y) for y in tile_origins(h,size,cfg['tile']['stride']) for x in tile_origins(w,size,cfg['tile']['stride'])]
   predictions=model.predict(source=[im.crop((x,y,x+size,y+size)) for x,y in origins],imgsz=640,conf=cfg['proposer']['proposal_confidence_minimum'],iou=cfg['proposer']['within_tile_nms_iou'],max_det=cfg['proposer']['maximum_detections_per_tile'],device=device,verbose=False)
   candidates=[]
   for (x,y),p in zip(origins,predictions,strict=True):
    for b,s in zip(p.boxes.xyxy.cpu().tolist(),p.boxes.conf.cpu().tolist(),strict=True):
     mapped=to_full_image(b,x,y,w,h)
     if mapped is not None:candidates.append(Candidate(mapped,finite(s),x,y))
   candidates=deterministic_nms(candidates,cfg['tile']['cross_tile_nms_iou'],cfg['tile']['maximum_reconstructed_candidates_per_image'])
   rows.extend({'image_id':record['image_id'],'reid':str(record['reid']),'box_xyxy':list(c.box),'proposer_confidence':c.score} for c in candidates)
  print(json.dumps({'candidate_image':record['image_id'],'candidates':len(candidates)}),flush=True)
 return rows

def score_rows(rows,records,model,transform,device,cfg):
 import torch
 from PIL import Image
 by=defaultdict(list)
 for i,r in enumerate(rows):by[r['image_id']].append(i)
 result=[dict(r) for r in rows];model.eval()
 with torch.inference_mode():
  for record in records:
   with Image.open(record['prepared_image']) as im:
    im=im.convert('RGB');indices=by[record['image_id']]
    for start in range(0,len(indices),128):
     ids=indices[start:start+128]
     crops=[transform(im.crop(tuple(round(v) for v in pad_box(rows[i]['box_xyxy'],*im.size,cfg['crop_padding'])))) for i in ids]
     probs=model(torch.stack(crops).to(device)).softmax(1)[:,1].cpu().tolist()
     for i,p in zip(ids,probs,strict=True):result[i]['probability']=finite(p);result[i]['score']=math.sqrt(result[i]['proposer_confidence']*p)
 return result

def validation_rows(val):
 return [dict(r,old_score=math.sqrt(r['proposer_confidence']*r['reranker_crack_probability'])) for r in val['repaired_proposals']]

def mine(a,cfg,lock,dev,val):
 from PIL import Image
 if (a.run/'crop_manifest.json').exists():raise ValueError('refuse duplicate mining')
 records=[r for r in dev['records'] if r['split']=='train'];model,transform,device=load_models(a,cfg)
 rows=infer_candidates(records,a,cfg);rows=score_rows(rows,records,model,transform,device,cfg)
 for r in rows:r['old_score']=r.pop('score');r['old_probability']=r.pop('probability')
 write(a.run/'train_proposals.json',dict(lineage(a),rows=rows))
 by=defaultdict(list)
 for r in rows:by[r['image_id']].append(r)
 crops=[]
 for record in records:
  with Image.open(record['prepared_image']) as im:
   for i,(box,label,kind) in enumerate(mining_choice(by[record['image_id']],record['crack_boxes_xyxy'],record['width'],record['height'],cfg)):
    p=a.run/'crops'/('crack' if label else 'background')/f"{Path(record['image_id']).stem}__{i:04}.jpg";p.parent.mkdir(parents=True,exist_ok=True)
    im.crop(tuple(round(v) for v in box)).convert('RGB').save(p,quality=92)
    crops.append({'image_id':record['image_id'],'reid':record['reid'],'split':'train','source_kind':kind,'box':list(box),'label':label,'path':str(p.resolve()),'sha256':sha256_file(p)})
 write(a.run/'crop_manifest.json',dict(lineage(a),records=crops,train_proposals_sha256=sha256_file(a.run/'train_proposals.json')))


def validation_loss(rows,targets,records,cfg):
 # Unbalanced proposal loss on clear positives/negatives only, tie-breaker.
 total=0.;count=0
 dimensions={r['image_id']:(r['width'],r['height']) for r in records}
 for r in rows:
  overlap=max((box_iou(r['box_xyxy'],t) for t in targets[r['image_id']]),default=0.)
  if overlap>=.5:y=1
  elif overlap<=.05:
   padded=pad_box(r['box_xyxy'],*dimensions[r['image_id']],cfg['crop_padding'])
   if any(boxes_overlap(padded,t) for t in targets[r['image_id']]):continue
   y=0
  else:continue
  p=min(1-1e-7,max(1e-7,r['probability']));total-=math.log(p if y else 1-p);count+=1
 if not count:raise ValueError('no validation labels')
 return total/count

def train(a,cfg,lock,dev,val):
 import numpy as np,torch
 from torch.utils.data import DataLoader,WeightedRandomSampler
 from torchvision import datasets
 if (a.run/'training_started.json').exists():raise ValueError('refuse duplicate training')
 crop=read(a.run/'crop_manifest.json')
 for k,v in lineage(a).items():
  if crop.get(k)!=v:raise ValueError(f'crop lineage {k}')
 allowed={r['image_id'] for r in dev['records'] if r['split']=='train'}
 paths=set()
 for r in crop['records']:
  if r['split']!='train' or r['image_id'] not in allowed:raise ValueError('crop split leak')
  check_hash(r['path'],r['sha256']);paths.add(Path(r['path']).resolve())
 actual={p.resolve() for p in (a.run/'crops').glob('*/*.jpg')}
 if actual!=paths:raise ValueError('crop membership mismatch')
 seed=cfg['seed'];random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed);torch.use_deterministic_algorithms(True,warn_only=True)
 model,transform,device=load_models(a,cfg);dataset=datasets.ImageFolder(a.run/'crops',transform=transform)
 if dataset.class_to_idx!={'background':0,'crack':1}:raise ValueError('wrong classes')
 counts={i:dataset.targets.count(i) for i in (0,1)}
 if min(counts.values())<=0:raise ValueError('empty class')
 generator=torch.Generator().manual_seed(seed)
 sampler=WeightedRandomSampler([1/counts[t] for t in dataset.targets],len(dataset),replacement=True,generator=generator)
 loader=DataLoader(dataset,batch_size=cfg['batch'],sampler=sampler,num_workers=0)
 optimizer=torch.optim.AdamW(model.parameters(),lr=cfg['learning_rate'],weight_decay=cfg['weight_decay'])
 criterion=torch.nn.CrossEntropyLoss();best=(-float('inf'),-float('inf'));history=[]
 vrecords=[r for r in dev['records'] if r['split']=='validation'];vrows=validation_rows(val)
 baseline=metrics(vrows,val['targets'],val['image_locations'],'old_score')
 write(a.run/'training_started.json',dict(lineage(a),hostname=platform.node(),counts=counts))
 for epoch in range(1,cfg['epochs']+1):
  model.train();total=0.;n=0
  for images,labels in loader:
   optimizer.zero_grad(set_to_none=True);loss=criterion(model(images.to(device)),labels.to(device));finite(loss.item());loss.backward();optimizer.step();total+=loss.item()*len(labels);n+=len(labels)
  scored=score_rows(vrows,vrecords,model,transform,device,cfg)
  measurement=metrics(scored,val['targets'],val['image_locations'],'score');vl=validation_loss(scored,val['targets'],vrecords,cfg);recall=measurement['macro_location_recall']
  if recall is None:raise ValueError('validation recall unidentified')
  row={'epoch':epoch,'train_loss':total/n,'validation_loss':vl,'validation_macro_recall':recall,'delta':recall-baseline['macro_location_recall']};history.append(row);write(a.run/'history.json',history);print(json.dumps(row),flush=True)
  key=(recall,-vl)
  if key>best:
   best=key
   torch.save({'state_dict':model.state_dict(),'class_to_idx':dataset.class_to_idx,'epoch':epoch,'validation_loss':vl,'lineage':dict(lineage(a),crop_manifest_sha256=sha256_file(a.run/'crop_manifest.json'))},a.run/'best_ranker.pt')
   write(a.run/'evaluation_validation.json',dict(lineage(a),split='validation',epoch=epoch,baseline=baseline,candidate=measurement,delta=row['delta'],rows=scored,targets=val['targets'],image_locations=val['image_locations']))
 validate_reranker_checkpoint(a.run/'best_ranker.pt')
 write(a.run/'training_receipt.json',dict(lineage(a),best_sha256=sha256_file(a.run/'best_ranker.pt'),history_sha256=sha256_file(a.run/'history.json'),crop_manifest_sha256=sha256_file(a.run/'crop_manifest.json'),epochs=cfg['epochs'],device='cuda:1',hostname=platform.node()))

def verify_validation(a,cfg):
 e=read(a.run/'evaluation_validation.json');receipt=read(a.run/'training_receipt.json');model=validate_reranker_checkpoint(a.run/'best_ranker.pt')
 for k,v in lineage(a).items():
  if e.get(k)!=v or receipt.get(k)!=v or model['lineage'].get(k)!=v:raise ValueError(f'freeze lineage {k}')
 check_hash(a.run/'best_ranker.pt',receipt['best_sha256']);check_hash(a.run/'history.json',receipt['history_sha256']);check_hash(a.run/'crop_manifest.json',receipt['crop_manifest_sha256'])
 val=read(a.source_validation);expected=validation_rows(val)
 if len(expected)!=len(e['rows']):raise ValueError('validation candidate count')
 for old,new in zip(expected,e['rows'],strict=True):
  for k in ('image_id','reid','box_xyxy','proposer_confidence','old_score'):
   if old[k]!=new[k]:raise ValueError('validation candidates changed')
  if abs(new['score']-math.sqrt(new['proposer_confidence']*new['probability']))>1e-12:raise ValueError('fusion changed')
 if e['targets']!=val['targets'] or e['image_locations']!=val['image_locations']:raise ValueError('validation truth changed')
 if e['baseline']!=metrics(e['rows'],e['targets'],e['image_locations'],'old_score') or e['candidate']!=metrics(e['rows'],e['targets'],e['image_locations'],'score'):raise ValueError('metric recompute mismatch')
 delta=e['candidate']['macro_location_recall']-e['baseline']['macro_location_recall']
 if e['delta']!=delta or e['epoch']!=model['epoch']:raise ValueError('selection mismatch')
 history=read(a.run/'history.json')
 selected=max(history,key=lambda r:(r['validation_macro_recall'],-r['validation_loss'],-r['epoch']))
 if selected['epoch']!=e['epoch']:raise ValueError('wrong best epoch')
 return e

def freeze(a,cfg,lock):
 if (a.run/'test_authorization.json').exists():raise ValueError('freeze exists')
 e=verify_validation(a,cfg)
 if e['delta']<cfg['development_delta_to_access_test']:
  write(a.run/'development_decision.json',{'protocol':PROTOCOL,'status':'stop_development_negative','delta':e['delta'],'fresh_test_access':False});return
 write(a.run/'test_authorization.json',dict(lineage(a),status='authorized_after_model_and_validation_freeze',ranker_sha256=sha256_file(a.run/'best_ranker.pt'),training_receipt_sha256=sha256_file(a.run/'training_receipt.json'),validation_sha256=sha256_file(a.run/'evaluation_validation.json'),confirmatory_test_locations=lock['confirmatory_test_locations'],primary_delta=cfg['primary_delta'],score=cfg['score']))

def verify_authorization(a,cfg,lock):
 auth=read(a.run/'test_authorization.json');e=verify_validation(a,cfg)
 required=dict(lineage(a),status='authorized_after_model_and_validation_freeze',ranker_sha256=sha256_file(a.run/'best_ranker.pt'),training_receipt_sha256=sha256_file(a.run/'training_receipt.json'),validation_sha256=sha256_file(a.run/'evaluation_validation.json'),confirmatory_test_locations=lock['confirmatory_test_locations'],primary_delta=cfg['primary_delta'],score=cfg['score'])
 if any(auth.get(k)!=v for k,v in required.items()) or e['delta']<cfg['development_delta_to_access_test']:raise ValueError('authorization chain invalid')
 return auth

def prepare(a,cfg,lock):
 # Must verify before workbook readers or image paths are touched.
 verify_authorization(a,cfg,lock);check_hash(a.workbook,lock['workbook_sha256'])
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
  records.append({'image_id':identity,'reid':reid,'split':'test','prepared_image':str(p.resolve()),'prepared_image_sha256':sha256_file(p),'width':w,'height':h,'crack_boxes_xyxy':[r['box_xyxy'] for r in annotations if r['category'] in CRACK_CLASSES],'all_annotations':annotations})
 validate_members(records,lock,'test')
 write(a.run/'manifest_test.json',dict(lineage(a),test_authorization_sha256=sha256_file(a.run/'test_authorization.json'),records=records))

def evaluate(a,cfg,lock):
 verify_authorization(a,cfg,lock)
 if (a.run/'evaluation_test.json').exists():raise ValueError('test evaluation already exists')
 manifest=read(a.run/'manifest_test.json')
 for k,v in dict(lineage(a),test_authorization_sha256=sha256_file(a.run/'test_authorization.json')).items():
  if manifest.get(k)!=v:raise ValueError('test manifest lineage')
 records=manifest['records'];validate_members(records,lock,'test');model,transform,device=load_models(a,cfg)
 rows=infer_candidates(records,a,cfg);oldrows=score_rows(rows,records,model,transform,device,cfg)
 import torch
 model.load_state_dict(validate_reranker_checkpoint(a.run/'best_ranker.pt')['state_dict'])
 newrows=score_rows(rows,records,model,transform,device,cfg)
 for old,new in zip(oldrows,newrows,strict=True):new['old_probability']=old['probability'];new['old_score']=old['score']
 targets={r['image_id']:r['crack_boxes_xyxy'] for r in records};locations={r['image_id']:str(r['reid']) for r in records}
 baseline=metrics(newrows,targets,locations,'old_score');candidate=metrics(newrows,targets,locations,'score');delta=None if baseline['macro_location_recall'] is None else candidate['macro_location_recall']-baseline['macro_location_recall']
 write(a.run/'evaluation_test.json',dict(lineage(a),split='test',manifest_sha256=sha256_file(a.run/'manifest_test.json'),authorization_sha256=sha256_file(a.run/'test_authorization.json'),ranker_sha256=sha256_file(a.run/'best_ranker.pt'),baseline=baseline,candidate=candidate,delta=delta,primary_pass=None if delta is None else delta>=cfg['primary_delta'],oracle=oracle_coverage(newrows,targets,locations),rows=newrows,targets=targets,image_locations=locations))
 print(json.dumps({'delta':delta,'baseline':baseline,'candidate':candidate}),flush=True)

def verify_source():
 manifest=read(ROOT/'docs/research/S01/S01-E003/source_manifest.json')
 for relative,expected in manifest['files'].items():check_hash(ROOT/relative,expected)

def main():
 verify_source()
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['mine','train','freeze','check-authorization','prepare','evaluate'])
 for name in ['config','lock','tiled','old-ranker','development','source-validation','run']:p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--workbook',type=Path);p.add_argument('--image-root',type=Path);a=p.parse_args();cfg=read(a.config);lock=read(a.lock);dev,val=validate_inputs(a,cfg,lock);a.run.mkdir(parents=True,exist_ok=True)
 if a.stage=='mine':mine(a,cfg,lock,dev,val)
 elif a.stage=='train':train(a,cfg,lock,dev,val)
 elif a.stage=='freeze':freeze(a,cfg,lock)
 elif a.stage=='check-authorization':verify_authorization(a,cfg,lock)
 elif a.stage=='prepare':prepare(a,cfg,lock)
 elif a.stage=='evaluate':evaluate(a,cfg,lock)
if __name__=='__main__':main()
