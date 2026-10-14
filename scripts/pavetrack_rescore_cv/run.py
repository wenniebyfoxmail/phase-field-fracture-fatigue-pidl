#!/usr/bin/env python3
"""S01-E008 frozen corrected-crop scoring with immutable original branch."""
from __future__ import annotations
import argparse,copy,json,math,importlib.util
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('e007_rescore_dependency',ROOT/'scripts/pavetrack_paired_cv/run.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p);m=p.m
read,write,sha256_file,box_iou,metrics,oracle_coverage,admitted_targets=p.read,p.write,p.sha256_file,p.box_iou,p.metrics,p.oracle_coverage,p.admitted_targets
PROTOCOL='S01-E008-v1'
def verify_source():
 for name,h in read(ROOT/'docs/research/S01/S01-E008/source_manifest.json')['files'].items():m.check_hash(ROOT/name,h)
def prior_args(a):
 d=vars(a).copy();d.update(config=ROOT/'docs/research/S01/S01-E007/run_config.json',lock=ROOT/'docs/research/S01/S01-E007/data_lock.json',run=a.paired_run);return SimpleNamespace(**d)
def lineage(a):
 return dict(protocol=PROTOCOL,source_manifest_sha256=sha256_file(ROOT/'docs/research/S01/S01-E008/source_manifest.json'),config_sha256=sha256_file(a.config),lock_sha256=sha256_file(a.lock),paired_feature_receipt_sha256=sha256_file(a.paired_run/'feature_receipt.json'),paired_run_id=a.paired_run.name,inherited_lineage=p.lineage(prior_args(a)))
def load(a):
 cfg=read(a.config);lock=read(a.lock);qa=prior_args(a);oldcfg,oldlock,dev,val,train,corr,audit=p.load(qa)
 if cfg['protocol']!=PROTOCOL or lock['protocol']!=PROTOCOL or cfg['score_features']!=576:raise ValueError('rescore protocol')
 if {k:v for k,v in lock.items() if k!='protocol'}!={k:v for k,v in oldlock.items() if k!='protocol'} or cfg['qualification_locations']!=oldcfg['qualification_locations']:raise ValueError('partition mutation')
 if a.paired_run.name!=cfg['paired_run_id'] or sha256_file(a.paired_run/'feature_receipt.json')!=cfg['paired_feature_receipt_sha256']:raise ValueError('paired bank identity')
 p.verify_source();data,_=p.verified_cache(qa,oldcfg,oldlock,dev,train,audit)
 return cfg,lock,dev,val,data

def bank(a,cfg,dev,data,phase):
 import numpy as np
 if phase=='qualification':
  result,_=p.subset(data,np.empty((len(data['labels']),0)),cfg['qualification_locations']);records=[r for r in dev['records'] if r['split']=='train' and r['reid'] in cfg['qualification_locations']]
 else:result=read(a.parent_run/'validation_bank.json');records=[r for r in dev['records'] if r['split']=='validation']
 if len(result['bank'])//2>cfg['maximum_'+phase+'_corrections']:raise ValueError('correction budget')
 return result,records

def added_bank(original,paired,probabilities,cfg,ratio):
 from collections import defaultdict
 if ratio not in cfg['score_ratio_limits'] or len(paired)%2 or len(probabilities)!=len(paired)//2:raise ValueError('admission contract')
 if len({r['candidate_id'] for r in original})!=len(original) or any(r['parent_id']!=i for i,r in enumerate(original)):raise ValueError('original identity')
 by=defaultdict(list)
 for row in original:by[row['image_id']].append(row)
 proposals=[];ratio_reject=0;original_conflict=0
 for i,prob in enumerate(probabilities):
  old,new=paired[2*i:2*i+2];pid=old['parent_id']
  if not isinstance(pid,int) or not 0<=pid<len(original):raise ValueError('parent index')
  if old!=original[pid] or new['parent_id']!=pid or new['kind']!='correction' or new['original_box_xyxy']!=old['box_xyxy']:raise ValueError('pair identity')
  if not math.isfinite(prob) or not 0<=prob<=1:raise ValueError('corrected probability')
  score=math.sqrt(old['proposer_confidence']*prob)
  if score<=ratio*old['score']:ratio_reject+=1;continue
  if any(new['box_xyxy']==r['box_xyxy'] or box_iou(new['box_xyxy'],r['box_xyxy'])>cfg['original_duplicate_iou'] for r in by[old['image_id']]):original_conflict+=1;continue
  row=copy.deepcopy(new);row.update(candidate_id='c:'+str(pid),probability=float(prob),score=score,kind='correction',rescored_correction=True);proposals.append(row)
 accepted=[];images=defaultdict(list);correction_conflict=0
 for row in sorted(proposals,key=lambda r:(-r['score'],r['image_id'],tuple(r['box_xyxy']),r['parent_id'])):
  if any(box_iou(row['box_xyxy'],r['box_xyxy'])>cfg['correction_duplicate_iou'] for r in images[row['image_id']]):correction_conflict+=1;continue
  accepted.append(row);images[row['image_id']].append(row)
 result=copy.deepcopy(original)+sorted(accepted,key=lambda r:r['parent_id'])
 if result[:len(original)]!=original or len({r['candidate_id'] for r in result})!=len(result):raise ValueError('immutable original branch')
 return result,dict(original_count=len(original),scored_pairs=len(probabilities),ratio_rejected=ratio_reject,original_duplicate_rejected=original_conflict,correction_duplicate_rejected=correction_conflict,accepted_corrections=len(accepted))

def evaluate(data,records,probabilities,cfg,ratio):
 original=data['original_rows'];rows,choice=added_bank(original,data['bank'],probabilities,cfg,ratio);targets={r['image_id']:r['crack_boxes_xyxy'] for r in records};locations={r['image_id']:str(r['reid']) for r in records};bm=metrics(original,targets,locations,'score');cm=metrics(rows,targets,locations,'score');old=admitted_targets(original,targets,bm);new=admitted_targets(rows,targets,cm);ret=None if not old else len(old&new)/len(old);delta=None if bm['macro_location_recall'] is None else cm['macro_location_recall']-bm['macro_location_recall'];net=len(new)-len(old)
 primary=None if ret is None or delta is None else ret>=cfg['minimum_retention'] and delta>=cfg['primary_delta'] and net>=cfg['minimum_net_targets']
 qualified=False if ret is None or delta is None else ret>=cfg['minimum_retention'] and delta>cfg['qualification_minimum_delta'] and net>=cfg['minimum_net_targets']
 threshold=bm['global_score_threshold'];ct=cm['global_score_threshold'];gains=[(r,y) for r,y in zip(data['bank'][::2],data.get('labels',[])) if y['gain']] if 'labels' in data else []
 gain_ids={r['parent_id'] for r,_ in gains};diag=dict(geometry_gain_pairs=None if 'labels' not in data else len(gains),accepted_gain_pairs=None if 'labels' not in data else sum(r['parent_id'] in gain_ids for r in rows[len(original):]),accepted_gains_above_original_prefix=None if threshold is None or 'labels' not in data else sum(r['parent_id'] in gain_ids and r['score']>=threshold for r in rows[len(original):]),added_corrections_in_candidate_prefix=0 if ct is None else sum(r['score']>=ct for r in rows[len(original):]))
 return dict(score_ratio=ratio,baseline=bm,candidate=cm,delta=delta,retention=ret,net_targets=net,retained_old_targets=len(old&new),lost_old_targets=len(old-new),new_detected_targets=len(new-old),protected_primary_pass=primary,qualified=qualified,baseline_rows=original,rows=rows,pair_rows=data['bank'],corrected_probabilities=probabilities,choice=choice,targets=targets,image_locations=locations,baseline_oracle=oracle_coverage(original,targets,locations),oracle=oracle_coverage(rows,targets,locations),diagnostic=diag)

def decision_fields(binding,policies,cfg,evaluation_sha):
 passed=[r for r in policies if r['qualified']];chosen=sorted(passed,key=lambda r:(-r['delta'],-r['retention'],-r['net_targets'],r['choice']['accepted_corrections'],-r['score_ratio']))[0] if passed else None
 status='qualified' if chosen else ('inconclusive_qualification_metric' if any(r['retention'] is None or r['delta'] is None for r in policies) else 'stop_qualification_negative')
 return dict(binding,status=status,selected_score_ratio=None if chosen is None else chosen['score_ratio'],qualification_evaluation_sha256=evaluation_sha,fresh_access=False)

def extract(a,cfg,dev,data,phase):
 import numpy as np,torch
 if (a.run/(phase+'_extract_started.json')).exists():raise ValueError('refuse duplicate crop scoring')
 if phase=='validation':
  decision=verify_qualification(a,cfg,dev,data)
  if decision['status']!='qualified':raise ValueError('validation scoring blocked by qualification')
 d,records=bank(a,cfg,dev,data,phase);write(a.run/(phase+'_extract_started.json'),dict(lineage(a),phase=phase));image_receipts=[]
 from PIL import Image
 for record in records:
  m.check_hash(Path(record['prepared_image']),record['prepared_image_sha256'])
  with Image.open(record['prepared_image']) as im:
   if im.size!=(record['width'],record['height']):raise ValueError('image dimensions')
  image_receipts.append(dict(image_id=record['image_id'],sha256=record['prepared_image_sha256'],width=record['width'],height=record['height']))
 torch.set_num_threads(cfg['threads']);model,transform,device=m.base.load_models(a,cfg);X=m.box.embeddings(d['bank'][1::2],records,model,transform,device,cfg['crop_padding'])[:,:576];np.savez_compressed(a.run/(phase+'_pooled_features.npz'),X=X);probs=m.frozen_score_probabilities(X,a.old_ranker)
 write(a.run/(phase+'_scores.json'),dict(lineage(a),phase=phase,parent_ids=[r['parent_id'] for r in d['bank'][1::2]],probabilities=probs,image_receipts=image_receipts));files=[phase+'_pooled_features.npz',phase+'_scores.json'];write(a.run/(phase+'_scoring_receipt.json'),dict(lineage(a),phase=phase,files={name:sha256_file(a.run/name) for name in files}))

def verified_scores(a,cfg,dev,data,phase):
 import numpy as np
 d,records=bank(a,cfg,dev,data,phase);receipt=read(a.run/(phase+'_scoring_receipt.json'));scores=read(a.run/(phase+'_scores.json'));binding=dict(lineage(a),phase=phase)
 for payload in [receipt,scores]:
  for k,v in binding.items():
   if payload.get(k)!=v:raise ValueError('scoring lineage')
 expected_files={phase+'_pooled_features.npz',phase+'_scores.json'}
 if set(receipt['files'])!=expected_files:raise ValueError('scoring inventory')
 for name,h in receipt['files'].items():m.check_hash(a.run/name,h)
 expected_images=[dict(image_id=r['image_id'],sha256=r['prepared_image_sha256'],width=r['width'],height=r['height']) for r in records]
 if scores['parent_ids']!=[r['parent_id'] for r in d['bank'][1::2]] or scores['image_receipts']!=expected_images:raise ValueError('scoring parent/image identity')
 with np.load(a.run/(phase+'_pooled_features.npz'),allow_pickle=False) as f:X=f['X']
 if X.shape!=(len(d['bank'])//2,576) or X.dtype!=np.float32 or not np.isfinite(X).all() or scores['probabilities']!=m.frozen_score_probabilities(X,a.old_ranker):raise ValueError('classifier cache replay')
 return d,records,scores['probabilities']

def qualify(a,cfg,dev,data):
 if (a.run/'qualification_evaluation.json').exists() or (a.run/'qualification_decision.json').exists():raise ValueError('duplicate qualification comparison')
 d,records,probs=verified_scores(a,cfg,dev,data,'qualification');policies=[evaluate(d,records,probs,cfg,ratio) for ratio in cfg['score_ratio_limits']];write(a.run/'qualification_evaluation.json',dict(lineage(a),scoring_receipt_sha256=sha256_file(a.run/'qualification_scoring_receipt.json'),policies=policies));write(a.run/'qualification_decision.json',decision_fields(lineage(a),policies,cfg,sha256_file(a.run/'qualification_evaluation.json')))
def verify_qualification(a,cfg,dev,data):
 d,records,probs=verified_scores(a,cfg,dev,data,'qualification');expected=dict(lineage(a),scoring_receipt_sha256=sha256_file(a.run/'qualification_scoring_receipt.json'),policies=[evaluate(d,records,probs,cfg,ratio) for ratio in cfg['score_ratio_limits']]);actual=read(a.run/'qualification_evaluation.json');decision=read(a.run/'qualification_decision.json')
 if actual!=expected or decision!=decision_fields(lineage(a),expected['policies'],cfg,sha256_file(a.run/'qualification_evaluation.json')):raise ValueError('qualification/selection exact replay')
 return decision

def development(a,cfg,dev,val,data):
 if (a.run/'evaluation_validation.json').exists():raise ValueError('duplicate development comparison')
 decision=verify_qualification(a,cfg,dev,data)
 if decision['status']!='qualified':raise ValueError('development blocked')
 d,records,probs=verified_scores(a,cfg,dev,data,'validation');e=evaluate(d,records,probs,cfg,decision['selected_score_ratio'])
 if e['baseline']!=val['candidate']:raise ValueError('E003 exact comparator')
 write(a.run/'evaluation_validation.json',dict(lineage(a),split='validation',qualification_decision_sha256=sha256_file(a.run/'qualification_decision.json'),scoring_receipt_sha256=sha256_file(a.run/'validation_scoring_receipt.json'),**e));write(a.run/'development_decision.json',development_fields(a,e))
def development_fields(a,e):return dict(lineage(a),status='inconclusive' if e['protected_primary_pass'] is None else ('protected_net_gain' if e['protected_primary_pass'] else 'stop_development_negative'),validation_sha256=sha256_file(a.run/'evaluation_validation.json'),delta=e['delta'],retention=e['retention'],net_targets=e['net_targets'],fresh_access=False)
def verify_development(a,cfg,dev,val,data):
 decision=verify_qualification(a,cfg,dev,data)
 if decision['status']!='qualified':raise ValueError('development not qualified')
 d,records,probs=verified_scores(a,cfg,dev,data,'validation');e=evaluate(d,records,probs,cfg,decision['selected_score_ratio']);expected=dict(lineage(a),split='validation',qualification_decision_sha256=sha256_file(a.run/'qualification_decision.json'),scoring_receipt_sha256=sha256_file(a.run/'validation_scoring_receipt.json'),**e)
 if read(a.run/'evaluation_validation.json')!=expected or e['baseline']!=val['candidate'] or read(a.run/'development_decision.json')!=development_fields(a,e):raise ValueError('development exact replay')
 return e

def main():
 verify_source();parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['extract-qualification','qualify','extract-validation','development','verify'])
 for name in ['config','lock','tiled','old-ranker','development','source-validation','source-train','corrector','old-audit','old-train-features','old-validation','parent-run','paired-run','run']:parser.add_argument('--'+name,type=Path,required=True)
 a=parser.parse_args();cfg,lock,dev,val,data=load(a);a.run.mkdir(parents=True,exist_ok=True)
 if a.stage=='extract-qualification':extract(a,cfg,dev,data,'qualification')
 elif a.stage=='qualify':qualify(a,cfg,dev,data)
 elif a.stage=='extract-validation':extract(a,cfg,dev,data,'validation')
 elif a.stage=='development':development(a,cfg,dev,val,data)
 elif (a.run/'evaluation_validation.json').exists():verify_development(a,cfg,dev,val,data)
 else:verify_qualification(a,cfg,dev,data)
if __name__=='__main__':main()
