"""Shared scientific path for artificial fixtures and a future disabled producer.
No data loader, CLI, subprocess or import-time I/O. No selected-alpha R003 replay.
"""
from dataclasses import dataclass
import hashlib,json
import numpy as np
import r002_base as base

U=tuple((k/24,k/24) for k in range(25))
A=tuple((g,s) for g in (0.,.25,.5,.75,1.) for s in (0.,.25,.5,.75,1.))
C=U+((1.,0.),(0.,1.))
PAIRS=tuple(sorted(set(U)|set(A)))
ARMS=('CURRENT','HISTORY','GLOBAL_ONLY','SPATIAL_ONLY','SELECT_U','SELECT_C','SELECT_A')
FIXED=((0.,0.),(1.,1.),(1.,0.),(0.,1.))

def finite(x,label):
 x=np.asarray(x)
 if not np.isfinite(x).all():raise ValueError('nonfinite '+label)
 return x

def pair_key(w):return (sum(w),abs(w[0]-w[1]),w)

def select(losses,family):
 if set(losses)!=set(PAIRS):raise ValueError('candidate support changed')
 for v in losses.values():finite(v,'candidate loss')
 return min(family,key=lambda w:(float(losses[w]),*pair_key(w)))

def work_plan(groups,cases,horizons):
 if groups<4 or cases<groups or horizons<1:raise ValueError('cohort geometry')
 sets=groups*horizons*groups
 return dict(training_sets=sets,predictor=2*sets,residualizer=sets,
             inner_rows=cases*(groups-1)*horizons,outer_rows=cases*horizons,
             inner_scores=cases*(groups-1)*horizons*len(PAIRS),outer_scores=cases*horizons*len(ARMS))

@dataclass(frozen=True)
class Fold:
 outer:str
 inner:str|None
 train:tuple
 query:tuple
 horizon:int
 def validate(self,groups):
  if self.outer not in set(groups) or (self.inner is not None and (self.inner not in set(groups) or self.inner==self.outer)):raise ValueError('held group identity')
  if len(set(self.train))!=len(self.train) or len(set(self.query))!=len(self.query) or set(self.train)&set(self.query):raise ValueError('case overlap')
  tg={groups[i] for i in self.train};qg={groups[i] for i in self.query}
  expected=set(groups)-{self.outer}-({self.inner} if self.inner is not None else set())
  if tg!=expected or qg!={self.inner if self.inner is not None else self.outer}:raise ValueError('group leakage or missing train/query group')
  if self.outer in tg or tg&qg:raise ValueError('held group leakage')
  if set(self.train)!={i for i,g in enumerate(groups) if g in expected}:raise ValueError('train cases not complete')
  if set(self.query)!={i for i,g in enumerate(groups) if g in qg}:raise ValueError('query cases not complete')

def fold_key(f):return dict(outer=f.outer,inner=f.inner,H=f.horizon,train=list(f.train),query=list(f.query))

def group_weights(labels):
 counts={g:labels.count(g) for g in set(labels)}
 w=np.asarray([1./counts[g] for g in labels]);return w/w.sum()

def ridge(x,y,labels,alpha=10.,prefix=None):
 # Same unweighted training-origin scaling and equal-total-group objective as legacy ridge.
 # einsum avoids an optional BLAS product path; no warnings are suppressed.
 if alpha!=10.:raise ValueError('fixed alpha10 required')
 x=finite(np.asarray(x,dtype=np.float64),'train x');y=finite(np.asarray(y,dtype=np.float64),'train y')
 if x.ndim!=2 or y.ndim!=2 or len(x)!=len(y) or len(labels)!=len(x) or len(set(labels))<2:raise ValueError('ridge schema')
 mean=x.mean(0);scale=x.std(0);scale[scale<1e-8]=1.
 if prefix is not None:
  k=len(prefix[0]);mean[:k]=prefix[0];scale[:k]=prefix[1]
 z=np.c_[np.ones(len(x)),(x-mean)/scale];w=group_weights(labels);penalty=np.eye(z.shape[1])*alpha;penalty[0,0]=0.
 coef=np.linalg.solve(np.einsum('ni,n,nj->ij',z,w,z)+penalty,np.einsum('ni,n,nj->ij',z,w,y))
 finite(coef,'coefficients');return (mean,scale,coef)

def predict(model,x):
 x=finite(np.asarray(x,dtype=np.float64),'query x');m,s,b=model
 return finite(np.einsum('ni,ij->nj',np.c_[np.ones(len(x)),(x-m)/s],b),'prediction')

def model_hash(m):
 h=hashlib.sha256()
 for a in m:h.update(np.ascontiguousarray(a,dtype='<f8').tobytes())
 return h.hexdigest()

@dataclass
class Models:
 current:tuple
 history:tuple
 residualizer:tuple
 normalizer:np.ndarray
 fold:Fold
 provenance:dict

def fit_pair(data,fold,counters,audit):
 fold.validate(data.groups);audit.enter('fit_pair',**fold_key(fold))
 c,h=data.observations(fold.train,fold.horizon)
 y,amplitude,returned_ids=data.training_targets(fold.train,fold)
 if tuple(returned_ids)!=fold.train:raise ValueError('target identity/provenance mismatch')
 finite(amplitude,'training target amplitude');finite(y,'pooled training increment')
 if amplitude.shape!=(len(fold.train),2) or y.shape!=(len(fold.train),2*data.coarse_side**2):raise ValueError('training target shape')
 labels=[data.groups[i] for i in fold.train]
 def solve(x,target,role,prefix=None):
  counters[role]+=1 # Counts attempts, including a first failed solve; no retries.
  audit.enter('solve_attempt',**fold_key(fold),role=role,attempt=counters[role])
  return ridge(x,target,labels,prefix=prefix)
 m=solve(c,h,'residualizer')
 e=h-predict(m,c)
 current=solve(c,y,'predictor')
 history=solve(np.c_[c,e],y,'predictor',prefix=m[:2])
 norm=np.maximum(amplitude.mean(0),1e-6)
 if not np.array_equal(current[0],m[0]) or not np.array_equal(current[1],m[1]):raise ValueError('current prefix normalization identity')
 prov={**fold_key(fold),'alpha':10.,'normalizer_train_ids':list(fold.train),'normalizer':norm.tolist(),'target_chain':'target32-current32 before16x16 mean pooling; native metric separate','model_hashes':{k:model_hash(v) for k,v in [('current',current),('history',history),('m',m)]}}
 audit.enter('fit_pair_complete',**prov)
 return Models(current,history,m,norm,fold,prov)

def predict_pair(models,query_c,query_h,query_current,query_ids,coarse_side):
 """No query future target parameter. The shared current anchor is observable."""
 if query_current.dtype!=np.float32:raise ValueError('current anchor must be float32')
 if tuple(query_ids)!=models.fold.query:raise ValueError('query identity mismatch')
 pc=predict(models.current,query_c);e=query_h-predict(models.residualizer,query_c)
 ph=predict(models.history,np.c_[query_c,e]);fields=[]
 for x in (pc,ph):
  q=x.reshape(len(query_ids),2,coarse_side,coarse_side)
  repeat=query_current.shape[-1]//coarse_side
  if repeat*coarse_side!=query_current.shape[-1] or query_current.shape[1:3]!=(2,query_current.shape[-1]):raise ValueError('native/coarse geometry')
  fields.append(finite(query_current+q.repeat(repeat,2).repeat(repeat,3),'native prediction64'))
 return pc,ph,fields[0],fields[1]

def decoded_fields(current,coarse_c,coarse_h,weights,coarse_side):
 """Lossless recipe for all native fields: float32 anchor + two float64 coarse bases.
Uses the same addition/subtraction/centering order as scoring; no model forward.
"""
 repeat=current.shape[-1]//coarse_side
 pc=current+coarse_c.reshape(2,coarse_side,coarse_side).repeat(repeat,1).repeat(repeat,2)
 ph=current+coarse_h.reshape(2,coarse_side,coarse_side).repeat(repeat,1).repeat(repeat,2)
 return blend(pc,ph,weights)

def blend(pc,ph,weights):
 d=np.asarray(ph,dtype=np.float64)-np.asarray(pc,dtype=np.float64)
 g=d.mean((1,2),keepdims=True);s=d-g;w=np.asarray(weights,dtype=np.float64)
 out=pc[None]+w[:,0,None,None,None]*g[None]+w[:,1,None,None,None]*s[None]
 # Preserve native fixed-base endpoint bits; all families use this same rule.
 for j,pair in enumerate(weights):
  if tuple(pair)==(0.,0.):out[j]=pc
  elif tuple(pair)==(1.,1.):out[j]=ph
 return finite(out,'calibrated native fields')

def native_losses(preds,target,normalizer,center,half_height):
 """The original native float64 prediction minus float32 target metric chain."""
 if target.dtype!=np.float32 or preds.dtype!=np.float64:raise ValueError('native metric dtype')
 finite(preds,'native scores prediction');finite(target,'native score target');finite(normalizer,'native normalizer')
 if preds.shape[1:]!=target.shape or target.shape[0]!=2 or np.any(normalizer<=0):raise ValueError('native score schema')
 lo,hi=max(0,int(center)-half_height),min(target.shape[-2],int(center)+half_height+1)
 if lo>=hi:raise ValueError('native local band')
 err=np.abs(preds-target)/normalizer[None,:,None,None]
 full=err.mean((1,2,3));local=err[:,:,lo:hi].mean((1,2,3));v=np.c_[.5*full+.5*local,full,local]
 return finite(v,'native loss triples')

def run_comparison(data,sink,audit,horizons,expected_groups=None,expected_cases=None):
 """Actual nested driver. Small fixtures and future production use THIS path."""
 groups=sorted(set(data.groups));N=len(data.groups);G=len(groups)
 if expected_groups is not None and G!=expected_groups:raise ValueError('frozen group count')
 if expected_cases is not None and N!=expected_cases:raise ValueError('frozen case count')
 plan=work_plan(G,N,len(horizons));counts={k:0 for k in ('predictor','residualizer','inner_rows','outer_rows','inner_scores','outer_scores')}
 try:
  sink.begin(plan,groups,horizons,N)
  for outer in groups:
   dev=[g for g in groups if g!=outer]
   for horizon in horizons:
    candidate_group_losses=[]
    for inner in dev:
     fold=Fold(outer,inner,tuple(i for i,g in enumerate(data.groups) if g not in (outer,inner)),tuple(i for i,g in enumerate(data.groups) if g==inner),horizon)
     models=fit_pair(data,fold,counts,audit);sink.model(models,final=False)
     # Stream one query at a time, not an all-query native prediction cache.
     sums=np.zeros((len(PAIRS),3))
     for i in fold.query:
      one=Models(models.current,models.history,models.residualizer,models.normalizer,Fold(outer,inner,fold.train,(i,),horizon),models.provenance)
      audit.enter('inner_query',outer=outer,inner=inner,H=horizon,case=i,candidates=PAIRS,normalizer_train_ids=fold.train)
      qc,qh=data.observations((i,),horizon);anchor=data.current(i)
      _,_,pc,ph=predict_pair(one,qc,qh,anchor[None],(i,),data.coarse_side)
      values=native_losses(blend(pc[0],ph[0],PAIRS),data.evaluation_target(i,fold),models.normalizer,data.centers[i],data.half_height)
      sink.inner(fold,i,values);sums+=values;counts['inner_rows']+=1;counts['inner_scores']+=len(PAIRS)
     candidate_group_losses.append(sums/len(fold.query));del models
    means=np.mean(candidate_group_losses,axis=0)[:,0];losses=dict(zip(PAIRS,means))
    chosen=[select(losses,family) for family in (U,C,A)];weights=FIXED+tuple(chosen)
    fold=Fold(outer,None,tuple(i for i,g in enumerate(data.groups) if g!=outer),tuple(i for i,g in enumerate(data.groups) if g==outer),horizon)
    models=fit_pair(data,fold,counts,audit);sink.model(models,final=True);sink.selection(outer,horizon,chosen,means)
    for i in fold.query:
     one=Models(models.current,models.history,models.residualizer,models.normalizer,Fold(outer,None,fold.train,(i,),horizon),models.provenance)
     audit.enter('outer_query',outer=outer,H=horizon,case=i,weights=weights,normalizer_train_ids=fold.train)
     qc,qh=data.observations((i,),horizon);anchor=data.current(i)
     cc,ch,pc,ph=predict_pair(one,qc,qh,anchor[None],(i,),data.coarse_side)
     fields=blend(pc[0],ph[0],weights);target=data.evaluation_target(i,fold)
     values=native_losses(fields,target,models.normalizer,data.centers[i],data.half_height)
     sink.outer(fold,i,values,cc[0],ch[0],weights,fields,target,anchor,models.normalizer)
     counts['outer_rows']+=1;counts['outer_scores']+=len(ARMS)
    del models
   sink.progress(counts)
  for k,v in counts.items():
   if v!=plan[k]:raise ValueError('actual work count mismatch '+k)
  sink.finish(counts,plan)
  return counts
 except BaseException as exc:
  audit.fail(exc)
  raise
