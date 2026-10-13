#!/usr/bin/env python3
"""S01-E007 paired original-target harm/gain and train-qualified abstention."""
from __future__ import annotations
import argparse,copy,importlib.util,json,math
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('e006_pair_dependency',ROOT/'scripts/pavetrack_protected_cv/run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
read,write,sha256_file,box_iou,metrics,oracle_coverage,admitted_targets=m.read,m.write,m.sha256_file,m.box_iou,m.metrics,m.oracle_coverage,m.admitted_targets
PROTOCOL='S01-E007-v1'
GEOM=['log_aspect','log_area_fraction','width_fraction','height_fraction','center_x_fraction','center_y_fraction']
FEATURES=['original_spatial_'+str(i) for i in range(864)]+['corrected_spatial_'+str(i) for i in range(864)]+['original_'+x for x in GEOM]+['corrected_'+x for x in GEOM]+['delta_cx_over_old_width','delta_cy_over_old_height','log_width_ratio','log_height_ratio','logit_E003_score']
def verify_source():
 for p,h in read(ROOT/'docs/research/S01/S01-E007/source_manifest.json')['files'].items():m.check_hash(ROOT/p,h)
def parent_args(a):
 d=vars(a).copy();d.update(config=ROOT/'docs/research/S01/S01-E006/run_config.json',lock=ROOT/'docs/research/S01/S01-E006/data_lock.json',run=a.parent_run);return SimpleNamespace(**d)
def lineage(a):
 return dict(protocol=PROTOCOL,source_manifest_sha256=sha256_file(ROOT/'docs/research/S01/S01-E007/source_manifest.json'),config_sha256=sha256_file(a.config),lock_sha256=sha256_file(a.lock),parent_feature_receipt_sha256=sha256_file(a.parent_run/'feature_receipt.json'),parent_run_id=a.parent_run.name,inherited_lineage=m.lineage(parent_args(a)))
def load(a):
 cfg=read(a.config);lock=read(a.lock)
 if cfg['protocol']!=PROTOCOL or lock['protocol']!=PROTOCOL or cfg['features']!=FEATURES:raise ValueError('paired contract')
 oldcfg=read(parent_args(a).config);oldlock=read(parent_args(a).lock)
 if {k:v for k,v in lock.items() if k!='protocol'}!={k:v for k,v in oldlock.items() if k!='protocol'}:raise ValueError('partition mutation')
 if a.parent_run.name!=cfg['parent_run_id'] or sha256_file(a.parent_run/'feature_receipt.json')!=cfg['parent_feature_receipt_sha256']:raise ValueError('parent cache identity')
 if sha256_file(ROOT/'docs/research/S01/S01-E006/source_manifest.json')!=cfg['parent_source_manifest_sha256']:raise ValueError('parent source identity')
 m.verify_source();dev,val,train,corr,audit=m.validate_inputs(parent_args(a),oldcfg,oldlock)
 return cfg,lock,dev,val,train,corr,audit

def labels(old,new,targets):
 oi=[box_iou(old,t) for t in targets];ci=[box_iou(new,t) for t in targets]
 index=max(range(len(oi)),key=lambda i:(oi[i],-i)) if oi else None
 protected=index is not None and oi[index]>=.5
 harm=protected and ci[index]<.5
 gain=any(c>=.5 and o<.5 for o,c in zip(oi,ci,strict=True))
 return {'harm':int(harm),'gain':int(gain),'protected':bool(protected),'original_gt_index':index if protected else None}
def pair_features(bank,X):
 import numpy as np
 if X.shape!=(len(bank),872) or len(bank)%2 or not np.isfinite(X).all():raise ValueError('variant features')
 out=[]
 for i in range(0,len(bank),2):
  old,new=bank[i:i+2]
  if old['parent_id']!=new['parent_id'] or old['kind']!='original' or new['kind']!='correction':raise ValueError('pair ordering')
  a,b=old['box_xyxy'],new['box_xyxy'];ow,oh=a[2]-a[0],a[3]-a[1];nw,nh=b[2]-b[0],b[3]-b[1]
  if min(ow,oh,nw,nh)<=0:raise ValueError('nonpositive side')
  delta=[((b[0]+b[2])-(a[0]+a[2]))/(2*ow),((b[1]+b[3])-(a[1]+a[3]))/(2*oh),math.log(nw/ow),math.log(nh/oh)]
  out.append(np.concatenate([X[i,:864],X[i+1,:864],X[i,864:870],X[i+1,864:870],delta,X[i,870:871]]))
 result=np.asarray(out,dtype=np.float32)
 if result.shape!=(len(bank)//2,1745) or not np.isfinite(result).all():raise ValueError('paired feature shape')
 return result

def split_spec(lock,cfg):
 qual=cfg['qualification_locations'];fit=sorted(set(lock['train_locations'])-set(qual),key=int)
 if len(qual)!=4 or len(set(qual))!=4 or len(fit)!=12 or not set(qual)<=set(lock['train_locations']):raise ValueError('qualification partition')
 groups=[dict(fold=i,fit_locations=[l for j,l in enumerate(fit) if j%3!=i],held_locations=[l for j,l in enumerate(fit) if j%3==i]) for i in range(3)]
 return fit,qual,groups+[dict(fold=3,fit_locations=fit,held_locations=qual)]
def regression_head(X,audit,group,cfg,fit=True,stored=None):
 import torch
 from collections import Counter
 ids=[i for i,r in enumerate(audit['matches']) if r['reid'] in group['fit_locations']];ms=[audit['matches'][i] for i in ids];Y=[r['target_delta'] for r in ms];gs=[(r['image_id'],r['gt_index']) for r in ms]
 if fit:return dict(group,fit_ids=ids,**m.fit_ridge(X[ids],Y,gs,cfg['corrector_l2']))
 if {k:stored[k] for k in ['fold','fit_locations','held_locations','fit_ids']}!=dict(group,fit_ids=ids):raise ValueError('regression partition replay')
 D=torch.tensor(X[ids],dtype=torch.float64);T=torch.tensor(Y,dtype=torch.float64);mu=D.mean(0);sd=D.std(0,correction=0).clamp_min(1e-8);counts=Counter(gs);w=torch.tensor([1/(len(counts)*counts[g]) for g in gs],dtype=torch.float64)
 if not torch.allclose(mu,torch.tensor(stored['means'],dtype=torch.float64),atol=1e-12,rtol=0) or not torch.allclose(sd,torch.tensor(stored['stds'],dtype=torch.float64),atol=1e-12,rtol=0):raise ValueError('ridge scaler')
 D=torch.cat([(D-mu)/sd,torch.ones(len(D),1,dtype=torch.float64)],1);theta=torch.tensor(stored['coefficients']+[stored['intercepts']],dtype=torch.float64);R=torch.eye(D.shape[1],dtype=torch.float64)*cfg['corrector_l2'];R[-1,-1]=0
 grad=float(((D.T@(w[:,None]*D)+R)@theta-D.T@(w[:,None]*T)).abs().max());initial=float(.5*(T.square().sum(1)*w).sum());final=float(.5*((D@theta-T).square().sum(1)*w).sum()+.5*cfg['corrector_l2']*theta[:-1].square().sum())
 if not torch.isfinite(theta).all() or grad>1e-8 or max(abs(grad-stored['gradient_inf']),abs(initial-stored['initial_loss']),abs(final-stored['final_loss']))>1e-12:raise ValueError('ridge objective')
 return stored

def train_bank(originals,corrections,records,cfg):
 original,bank,counts=m.protected_bank(originals,corrections,cfg);by={r['image_id']:r for r in records};ys=[labels(bank[i]['box_xyxy'],bank[i+1]['box_xyxy'],by[bank[i]['image_id']]['crack_boxes_xyxy']) for i in range(0,len(bank),2)]
 return dict(original_rows=original,bank=bank,counts=counts,labels=ys)
def extract(a,cfg,lock,dev,train,audit):
 import numpy as np,torch
 if (a.run/'extract_started.json').exists():raise ValueError('duplicate extraction/fits')
 parentdata,_,parentX=m.verified_cache(parent_args(a),read(parent_args(a).config),dev,train,audit)
 write(a.run/'extract_started.json',lineage(a));torch.set_num_threads(1);records=[r for r in dev['records'] if r['split']=='train'];fit,qual,groups=split_spec(lock,cfg)
 with np.load(a.parent_run/'context_features.npz',allow_pickle=False) as f:Xc=f['X']
 Xm=np.load(a.old_train_features,allow_pickle=False)['X'].astype(np.float64);heads=[];corr=[None]*len(train['rows'])
 for group in groups:
  head=regression_head(Xm,audit,group,cfg);heads.append(head);pred=m.predict_corrections(parentdata['original_rows'],records,Xc,head,cfg)
  for i,r in enumerate(train['rows']):
   if r['reid'] in group['held_locations']:corr[i]=pred[i]
 if any(r is None for r in corr):raise ValueError('correction assignment')
 data=train_bank(parentdata['original_rows'],corr,records,cfg)
 model,transform,device=m.base.load_models(a,cfg)
 corrected=m.spatial_embeddings(data['bank'][1::2],records,model,transform,device,dict(cfg,features=m.FEATURES));X=np.empty((len(data['bank']),872),dtype=np.float32)
 if [r['parent_id'] for r in data['bank'][::2]]!=[r['parent_id'] for r in parentdata['bank'][::2]]:raise ValueError('parent cap drift')
 X[::2]=parentX[::2];X[1::2]=corrected;np.savez_compressed(a.run/'paired_train_features.npz',X=pair_features(data['bank'],X));write(a.run/'train_bank.json',dict(lineage(a),**data));write(a.run/'correction_heads.json',dict(lineage(a),models=heads))
 files=['paired_train_features.npz','train_bank.json','correction_heads.json'];write(a.run/'feature_receipt.json',dict(lineage(a),files={n:sha256_file(a.run/n) for n in files}))

def verified_cache(a,cfg,lock,dev,train,audit):
 import numpy as np,torch
 torch.set_num_threads(1);binding=lineage(a);receipt=read(a.run/'feature_receipt.json')
 for k,v in binding.items():
  if receipt.get(k)!=v:raise ValueError('cache lineage '+k)
 if set(receipt['files'])!={'paired_train_features.npz','train_bank.json','correction_heads.json'}:raise ValueError('cache inventory')
 for n,h in receipt['files'].items():m.check_hash(a.run/n,h)
 parentdata,_,parentX=m.verified_cache(parent_args(a),read(parent_args(a).config),dev,train,audit)
 heads=read(a.run/'correction_heads.json');data=read(a.run/'train_bank.json')
 for obj in [heads,data]:
  for k,v in binding.items():
   if obj.get(k)!=v:raise ValueError('cache payload lineage')
 fit,qual,groups=split_spec(lock,cfg)
 if len(heads['models'])!=4:raise ValueError('four heads required')
 records=[r for r in dev['records'] if r['split']=='train']
 with np.load(a.parent_run/'context_features.npz',allow_pickle=False) as f:Xc=f['X']
 Xm=np.load(a.old_train_features,allow_pickle=False)['X'].astype(np.float64);corr=[None]*len(train['rows'])
 for group,head in zip(groups,heads['models'],strict=True):
  regression_head(Xm,audit,group,cfg,False,head);pred=m.predict_corrections(parentdata['original_rows'],records,Xc,head,cfg)
  for i,r in enumerate(train['rows']):
   if r['reid'] in group['held_locations']:corr[i]=pred[i]
 expected=train_bank(parentdata['original_rows'],corr,records,cfg)
 if data!=dict(binding,**expected):raise ValueError('train banks/identity labels replay')
 with np.load(a.run/'paired_train_features.npz',allow_pickle=False) as f:X=f['X']
 if X.shape!=(len(data['labels']),1745) or not np.isfinite(X).all():raise ValueError('paired array shape')
 variants=np.empty((len(data['bank']),872),dtype=np.float32);variants[::2]=parentX[::2]
 by={r['image_id']:r for r in records}
 for j,row in enumerate(data['bank'][1::2]):variants[2*j+1]=np.concatenate([X[j,864:1728],np.asarray(m.geom(row,by[row['image_id']]),dtype=np.float32)])
 if not np.array_equal(X,pair_features(data['bank'],variants)):raise ValueError('original spatial and paired geometry replay')
 return data,X

def tensors(data,X,locs):
 import numpy as np,torch
 from collections import Counter
 ids=[i for i,r in enumerate(data['bank'][::2]) if r['reid'] in locs];rows=[data['bank'][2*i] for i in ids];Y=torch.tensor([[data['labels'][i][k] for k in ['harm','gain']] for i in ids],dtype=torch.float64)
 if not len(ids) or any(set(Y[:,k].tolist())!={0.,1.} for k in range(2)):raise ValueError('unidentifiable paired classes')
 Z=torch.tensor(X[ids],dtype=torch.float64);mu=Z.mean(0);sd=Z.std(0,correction=0).clamp_min(1e-8);Z=(Z-mu)/sd;counts=Counter(r['reid'] for r in rows)
 if set(counts)!=set(locs):raise ValueError('missing fit location')
 prior=torch.tensor([1/(len(counts)*counts[r['reid']]) for r in rows],dtype=torch.float64);W=torch.stack([torch.where(Y[:,k]==1,.5*prior/prior[Y[:,k]==1].sum(),.5*prior/prior[Y[:,k]==0].sum()) for k in range(2)],1)
 return Z,Y,W,mu,sd

def objective(Z,Y,W,theta,cfg):
 import torch
 return .5*(torch.nn.functional.binary_cross_entropy_with_logits(Z@theta[:-1]+theta[-1],Y,reduction='none')*W).sum()+.5*cfg['l2_strength']*theta[:-1].square().sum()
def fit_head(a,cfg,data,X,locs,name):
 import torch
 if (a.run/(name+'_started.json')).exists():raise ValueError('duplicate paired fit')
 Z,Y,W,mu,sd=tensors(data,X,locs);theta=torch.zeros((1746,2),dtype=torch.float64,requires_grad=True);initial=float(objective(Z,Y,W,theta,cfg).detach());write(a.run/(name+'_started.json'),dict(lineage(a),fit_locations=locs));calls=[]
 opt=torch.optim.LBFGS([theta],max_iter=cfg['max_iterations'],tolerance_grad=cfg['gradient_tolerance'],tolerance_change=1e-12,line_search_fn='strong_wolfe')
 def closure():
  opt.zero_grad();loss=objective(Z,Y,W,theta,cfg);loss.backward();calls.append(float(loss.detach()));return loss
 opt.step(closure);opt.zero_grad();loss=objective(Z,Y,W,theta,cfg);loss.backward();final=float(loss.detach());grad=float(theta.grad.abs().max())
 if not torch.isfinite(theta).all() or not math.isfinite(final) or final>initial+1e-12 or grad>1e-5:raise ValueError('paired numerical inadmissible')
 head=dict(lineage(a),fit_locations=locs,feature_receipt_sha256=sha256_file(a.run/'feature_receipt.json'),feature_names=FEATURES,means=mu.tolist(),stds=sd.tolist(),coefficients=theta[:-1].detach().tolist(),intercepts=theta[-1].detach().tolist(),initial_loss=initial,final_loss=final,gradient_inf=grad,closure_calls=len(calls));write(a.run/(name+'.json'),head);write(a.run/(name+'_history.json'),calls);return head

def verify_head(a,cfg,data,X,locs,name):
 import torch
 h=read(a.run/(name+'.json'));binding=dict(lineage(a),fit_locations=locs,feature_receipt_sha256=sha256_file(a.run/'feature_receipt.json'),feature_names=FEATURES)
 for k,v in binding.items():
  if h.get(k)!=v:raise ValueError('head lineage '+k)
 Z,Y,W,mu,sd=tensors(data,X,locs);theta=torch.tensor(h['coefficients']+[h['intercepts']],dtype=torch.float64,requires_grad=True)
 if theta.shape!=(1746,2) or not torch.isfinite(theta).all() or not torch.allclose(mu,torch.tensor(h['means'],dtype=torch.float64),atol=1e-12,rtol=0) or not torch.allclose(sd,torch.tensor(h['stds'],dtype=torch.float64),atol=1e-12,rtol=0):raise ValueError('head scaler/shape')
 loss=objective(Z,Y,W,theta,cfg);loss.backward();grad=float(theta.grad.abs().max());final=float(loss.detach());initial=float(objective(Z,Y,W,torch.zeros_like(theta),cfg))
 if grad>1e-5 or final>initial+1e-12 or max(abs(final-h['final_loss']),abs(initial-h['initial_loss']),abs(grad-h['gradient_inf']))>1e-12:raise ValueError('head objective replay')
 return h

def predict(head,X):
 import numpy as np
 z=(X.astype(np.float64)-head['means'])/head['stds'];logits=z@np.asarray(head['coefficients'])+head['intercepts']
 if not np.isfinite(logits).all():raise ValueError('nonfinite logits')
 return 1/(1+np.exp(-np.clip(logits,-700,700)))
def coordinate_choice(original,paired,probabilities,cfg):
 values=probabilities['scores'];limit=probabilities['harm_limit']
 if limit not in cfg['harm_score_limits'] or len(values)!=len(paired)//2:raise ValueError('policy contract')
 bits=[]
 for harm,gain in values:
  if not math.isfinite(harm) or not math.isfinite(gain) or not 0<=harm<=1 or not 0<=gain<=1:raise ValueError('paired scores')
  bits.extend([.5,1. if harm<=limit and gain>cfg['gain_score_minimum'] else 0.])
 return m.coordinate_choice(original,paired,bits,cfg)
def evaluate(data,records,head,X,cfg,limit):
 prob={'harm_limit':limit,'scores':predict(head,X).tolist()};original=data['original_rows'];bank=data['bank'];rows,choice=coordinate_choice(original,bank,prob,cfg);targets={r['image_id']:r['crack_boxes_xyxy'] for r in records};locations={r['image_id']:r['reid'] for r in records};bm=metrics(original,targets,locations,'score');cm=metrics(rows,targets,locations,'score');old=admitted_targets(original,targets,bm);new=admitted_targets(rows,targets,cm);ret=None if not old else len(old&new)/len(old);delta=None if bm['macro_location_recall'] is None else cm['macro_location_recall']-bm['macro_location_recall']
 return dict(baseline=bm,candidate=cm,delta=delta,retention=ret,retained_old_targets=len(old&new),lost_old_targets=len(old-new),new_detected_targets=len(new-old),protected_primary_pass=None if ret is None or delta is None else ret>=cfg['minimum_retention'] and delta>=cfg['primary_delta'],baseline_rows=original,rows=rows,pair_rows=bank,pair_probabilities=prob,choice=choice,targets=targets,image_locations=locations,baseline_oracle=oracle_coverage(original,targets,locations),oracle=oracle_coverage(rows,targets,locations))
def subset(data,X,locs):
 import numpy as np
 inds=[i for i,r in enumerate(data['bank'][::2]) if r['reid'] in locs];original=[copy.deepcopy(r) for r in data['original_rows'] if r['reid'] in locs];mapping={r['parent_id']:j for j,r in enumerate(original)}
 for j,r in enumerate(original):r['parent_id']=j;r['candidate_id']='o:'+str(j)
 bank=[]
 for i in inds:
  old,new=copy.deepcopy(data['bank'][2*i:2*i+2]);j=mapping[old['parent_id']]
  for r,k in [(old,'o'),(new,'c')]:r['parent_id']=j;r['candidate_id']=k+':'+str(j)
  bank.extend([old,new])
 return dict(original_rows=original,bank=bank,labels=[data['labels'][i] for i in inds]),X[inds]
def qualification(a,cfg,lock,dev,train,audit):
 data,X=verified_cache(a,cfg,lock,dev,train,audit);fit,qual,_=split_spec(lock,cfg)
 try:head=fit_head(a,cfg,data,X,fit,'qualification_head')
 except ValueError as ex:
  if str(ex)!='unidentifiable paired classes':raise
  write(a.run/'qualification_decision.json',dict(lineage(a),status='inconclusive_qualification_classes',fresh_access=False));return
 head=verify_head(a,cfg,data,X,fit,'qualification_head');qd,qX=subset(data,X,qual);records=[r for r in dev['records'] if r['reid'] in qual and r['split']=='train'];policies=[]
 for limit in cfg['harm_score_limits']:
  e=evaluate(qd,records,head,qX,cfg,limit);accepted={r['parent_id'] for r in e['rows'] if r.get('chosen_correction')};ls=[y for r,y in zip(qd['bank'][::2],qd['labels'],strict=True) if r['parent_id'] in accepted and y['protected']];exposures=len(ls);harms=sum(y['harm'] for y in ls);rate=None if not exposures else harms/exposures
  ok=e['retention'] is not None and e['retention']>=cfg['minimum_retention'] and e['delta'] is not None and e['delta']>cfg['qualification_minimum_delta'] and exposures>=cfg['qualification_minimum_protected_exposures'] and rate<=cfg['qualification_harm_rate_maximum'];e.update(harm_limit=limit,protected_exposures=exposures,harm_count=harms,harm_rate=rate,qualified=ok);policies.append(e)
 passed=[e for e in policies if e['qualified']];selected=sorted(passed,key=lambda e:(-e['delta'],-e['retention'],e['choice']['accepted_choices'],e['harm_limit']))[0] if passed else None
 write(a.run/'qualification_evaluation.json',dict(lineage(a),qualification_head_sha256=sha256_file(a.run/'qualification_head.json'),policies=policies))
 reason='qualified' if selected else ('inconclusive_qualification_exposure' if all(e['protected_exposures']<cfg['qualification_minimum_protected_exposures'] for e in policies) else 'stop_qualification_negative')
 write(a.run/'qualification_decision.json',dict(lineage(a),status=reason,selected_harm_limit=None if selected is None else selected['harm_limit'],qualification_evaluation_sha256=sha256_file(a.run/'qualification_evaluation.json'),fresh_access=False))

def verify_qualification(a,cfg,lock,dev,train,audit):
 data,X=verified_cache(a,cfg,lock,dev,train,audit);fit,qual,_=split_spec(lock,cfg);head=verify_head(a,cfg,data,X,fit,'qualification_head');payload=read(a.run/'qualification_evaluation.json');decision=read(a.run/'qualification_decision.json');binding=lineage(a)
 for obj in [payload,decision]:
  for k,v in binding.items():
   if obj.get(k)!=v:raise ValueError('qualification lineage')
 if payload['qualification_head_sha256']!=sha256_file(a.run/'qualification_head.json') or decision['qualification_evaluation_sha256']!=sha256_file(a.run/'qualification_evaluation.json'):raise ValueError('qualification binding')
 qd,qX=subset(data,X,qual);records=[r for r in dev['records'] if r['split']=='train' and r['reid'] in qual]
 if len(payload['policies'])!=4:raise ValueError('qualification grid')
 for limit,stored in zip(cfg['harm_score_limits'],payload['policies'],strict=True):
  e=evaluate(qd,records,head,qX,cfg,limit);accepted={r['parent_id'] for r in e['rows'] if r.get('chosen_correction')};ls=[y for r,y in zip(qd['bank'][::2],qd['labels'],strict=True) if r['parent_id'] in accepted and y['protected']];n=len(ls);harms=sum(y['harm'] for y in ls);rate=None if not n else harms/n;ok=e['retention'] is not None and e['retention']>=cfg['minimum_retention'] and e['delta'] is not None and e['delta']>0 and n>=cfg['qualification_minimum_protected_exposures'] and rate<=cfg['qualification_harm_rate_maximum'];e.update(harm_limit=limit,protected_exposures=n,harm_count=harms,harm_rate=rate,qualified=ok)
  if e!=stored:raise ValueError('qualification exact replay')
 passed=[e for e in payload['policies'] if e['qualified']];chosen=sorted(passed,key=lambda e:(-e['delta'],-e['retention'],e['choice']['accepted_choices'],e['harm_limit']))[0] if passed else None
 if decision['selected_harm_limit']!=(None if chosen is None else chosen['harm_limit']) or (decision['status']=='qualified')!=(chosen is not None):raise ValueError('selection replay')
 return decision,data,X

def development(a,cfg,lock,dev,val,train,audit):
 decision,data,X=verify_qualification(a,cfg,lock,dev,train,audit)
 if decision['status']!='qualified':raise ValueError('development blocked by qualification')
 head=fit_head(a,cfg,data,X,sorted(lock['train_locations'],key=int),'deployment_head');head=verify_head(a,cfg,data,X,sorted(lock['train_locations'],key=int),'deployment_head')
 import numpy as np
 parent=m.read(a.parent_run/'validation_bank.json')
 with np.load(a.parent_run/'selector_validation_features.npz',allow_pickle=False) as f:VX=pair_features(parent['bank'],f['X'])
 e=evaluate(parent,[r for r in dev['records'] if r['split']=='validation'],head,VX,cfg,decision['selected_harm_limit'])
 if e['baseline']!=val['candidate']:raise ValueError('E003 exact comparator')
 write(a.run/'evaluation_validation.json',dict(lineage(a),split='validation',deployment_head_sha256=sha256_file(a.run/'deployment_head.json'),qualification_decision_sha256=sha256_file(a.run/'qualification_decision.json'),**e));write(a.run/'development_decision.json',dict(lineage(a),status='inconclusive' if e['protected_primary_pass'] is None else ('protected_development_gain' if e['protected_primary_pass'] else 'stop_development_negative'),delta=e['delta'],retention=e['retention'],fresh_access=False));print(json.dumps({k:e[k] for k in ['delta','retention','retained_old_targets','lost_old_targets','new_detected_targets','protected_primary_pass']},indent=2))
def verify_development(a,cfg,lock,dev,val,train,audit):
 import numpy as np
 decision,data,X=verify_qualification(a,cfg,lock,dev,train,audit)
 if decision['status']!='qualified':raise ValueError('development not qualified')
 head=verify_head(a,cfg,data,X,sorted(lock['train_locations'],key=int),'deployment_head');parent=read(a.parent_run/'validation_bank.json')
 with np.load(a.parent_run/'selector_validation_features.npz',allow_pickle=False) as f:VX=pair_features(parent['bank'],f['X'])
 e=evaluate(parent,[r for r in dev['records'] if r['split']=='validation'],head,VX,cfg,decision['selected_harm_limit'])
 expected=dict(lineage(a),split='validation',deployment_head_sha256=sha256_file(a.run/'deployment_head.json'),qualification_decision_sha256=sha256_file(a.run/'qualification_decision.json'),**e)
 if read(a.run/'evaluation_validation.json')!=expected or e['baseline']!=val['candidate']:raise ValueError('development replay')
 status='inconclusive' if e['protected_primary_pass'] is None else ('protected_development_gain' if e['protected_primary_pass'] else 'stop_development_negative')
 if read(a.run/'development_decision.json')!=dict(lineage(a),status=status,delta=e['delta'],retention=e['retention'],fresh_access=False):raise ValueError('development decision replay')
 return e
def verify_stop(a,cfg,lock,dev,train,audit):
 d=read(a.run/'qualification_decision.json')
 if d['status']!='inconclusive_qualification_classes':return verify_qualification(a,cfg,lock,dev,train,audit)
 data,X=verified_cache(a,cfg,lock,dev,train,audit);fit,_,_=split_spec(lock,cfg)
 try:tensors(data,X,fit)
 except ValueError as ex:
  if str(ex)!='unidentifiable paired classes':raise
 else:raise ValueError('false class stop')
 if d!=dict(lineage(a),status='inconclusive_qualification_classes',fresh_access=False) or (a.run/'qualification_head_started.json').exists():raise ValueError('class stop identity')
 return d
def main():
 verify_source();p=argparse.ArgumentParser();p.add_argument('stage',choices=['extract','qualify','development','verify'])
 for n in ['config','lock','tiled','old-ranker','development','source-validation','source-train','corrector','old-audit','old-train-features','old-validation','parent-run','run']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();cfg,lock,dev,val,train,corr,audit=load(a);a.run.mkdir(parents=True,exist_ok=True)
 if a.stage=='extract':extract(a,cfg,lock,dev,train,audit)
 elif a.stage=='qualify':
  if (a.run/'qualification_decision.json').exists():raise ValueError('duplicate qualification')
  qualification(a,cfg,lock,dev,train,audit)
 elif a.stage=='development':development(a,cfg,lock,dev,val,train,audit)
 else:
  if (a.run/'evaluation_validation.json').exists():verify_development(a,cfg,lock,dev,val,train,audit)
  else:verify_stop(a,cfg,lock,dev,train,audit)
if __name__=='__main__':main()
