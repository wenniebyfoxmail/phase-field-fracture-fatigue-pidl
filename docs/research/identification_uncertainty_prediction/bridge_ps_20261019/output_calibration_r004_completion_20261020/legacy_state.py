"""Fold-local state interface. Only callers supply arrays; no filesystem/data loaders."""
import r002_base as base
ARMS=('C_RAW','H_RAW','C_REL','H_REL','H_INNOV','H_DONOR')
DIMS=dict(C_RAW=20,H_RAW=36,C_REL=18,H_REL=30,H_INNOV=32,H_DONOR=32)
TIE=('P','S','C_REL','C_RAW')

def finite(x):
 import numpy as np
 x=np.asarray(x,dtype=np.float64)
 if not np.isfinite(x).all():raise ValueError('nonfinite array: first stop')
 return x

def relative(q):
 import numpy as np
 q=finite(q)
 if q.shape[-1]!=8:raise ValueError('response schema')
 return np.concatenate((q[...,2:4],q[...,4:6]-q[...,:2],q[...,6:8]),axis=-1)

def features(states,cases,horizon):
 import numpy as np
 states=finite(states)
 if states.shape!=(len(cases),3,138):raise ValueError('origin schema')
 b=np.asarray([base.compose_features('span_progress',c['group'],c['origin_stage'],horizon,s) for s,c in zip(states,cases)])
 q=states[:,:,2:10];r=relative(q)
 out={'C_RAW':np.c_[b,q[:,-1]],'H_RAW':np.c_[b,q.reshape(len(cases),24)],
      'C_REL':np.c_[b,r[:,-1]],'H_REL':np.c_[b,r.reshape(len(cases),18)]}
 h=(r[:,:2]-r[:,-1:]).reshape(len(cases),12)
 for k,x in out.items():
  if x.shape!=(len(cases),DIMS[k]):raise ValueError('feature dimension')
 return out,h

def weights(groups):
 import numpy as np
 counts={g:groups.count(g) for g in set(groups)}
 w=np.asarray([1./counts[g] for g in groups]);return w/w.sum()

class Fits:
 def __init__(self):self.predictor=0;self.input=0
 def fit(self,x,y,alpha,groups,role='predictor',locked_prefix=None):
  import numpy as np
  x,y=finite(x),finite(y)
  if len(x)!=len(y) or len(x)!=len(groups) or len(set(groups))<2:raise ValueError('fit grouping')
  if role not in ('predictor','input'):raise ValueError('fit role')
  if getattr(self,role)>= (912 if role=='predictor' else 76):raise RuntimeError('solve cap')
  setattr(self,role,getattr(self,role)+1)
  if locked_prefix is None:
   model=base.ridge_fit(x,y,alpha,weights(list(groups)))
  else:
   mean,scale=x.mean(0),x.std(0);scale[scale<1e-8]=1.
   k=len(locked_prefix[0]);mean[:k]=locked_prefix[0];scale[:k]=locked_prefix[1]
   z=np.c_[np.ones(len(x)),(x-mean)/scale];w=weights(list(groups));penalty=np.eye(z.shape[1])*alpha;penalty[0,0]=0
   coef=np.linalg.solve(z.T@(w[:,None]*z)+penalty,z.T@(w[:,None]*y));model=mean,scale,coef
  for a in model:finite(a)
  return model

def predict(model,x):return finite(base.ridge_predict(model,finite(x)))

def nearest(train_c,query_c,train_ids,query_ids,mean,scale):
 """IDs are (group, origin_stage, frozen_case_index); candidates never include a query group."""
 import numpy as np
 if len(set(x[0] for x in train_ids))<2:raise ValueError('donors require >=2 groups')
 tz=(finite(train_c)-mean)/scale;qz=(finite(query_c)-mean)/scale
 order=sorted(range(len(train_ids)),key=lambda j:train_ids[j]);donors=[];distances=[]
 for z,ident in zip(qz,query_ids):
  eligible=[j for j in order if train_ids[j][0]!=ident[0]]
  if not eligible:raise ValueError('no different-group training donor')
  ds=np.sum((tz[eligible]-z)**2,axis=1);k=int(np.argmin(ds));donors.append(eligible[k]);distances.append(float(ds[k]))
 return np.asarray(donors,dtype=int),finite(distances)

def innovations(fits,c,h,train,query,cases):
 """No query values participate in estimating m, normalisation, or the donor pool."""
 import numpy as np
 tids=[(cases[i]['group'],cases[i]['origin_stage'],int(i)) for i in train]
 qids=[(cases[i]['group'],cases[i]['origin_stage'],int(i)) for i in query]
 model=fits.fit(c[train],h[train],10.,[x[0] for x in tids],role='input')
 et=h[train]-predict(model,c[train]);eq=h[query]-predict(model,c[query])
 dt,dtd=nearest(c[train],c[train],tids,tids,model[0],model[1]);dq,dqd=nearest(c[train],c[query],tids,qids,model[0],model[1])
 values={'H_INNOV':(np.c_[c[train],et],np.c_[c[query],eq]),
         'H_DONOR':(np.c_[c[train],et[dt]],np.c_[c[query],et[dq]])}
 evidence={'m_mean':model[0],'m_scale':model[1],'m_coef':model[2],
           'train_indices':np.asarray(train),'query_indices':np.asarray(query),
           'train_donor_indices':np.asarray(train)[dt],'query_donor_indices':np.asarray(train)[dq],
           'train_donor_squared_distance':dtd,'query_donor_squared_distance':dqd}
 return values,evidence,(model[0],model[1])

def choose_baseline(losses):
 if set(losses)!=set(TIE):raise ValueError('baseline pool changed')
 for x in losses.values():finite(x)
 return min(TIE,key=lambda a:(losses[a],TIE.index(a)))

def pullback(model,raw_train,raw_query):
 """No solve/fit: push saved coefficients to reversible (g,r) coordinates and pull penalty."""
 import numpy as np
 mean,sq,coef=model;p=len(mean)
 if p!=36:raise ValueError('H_RAW schema')
 T=np.eye(p);Ti=np.eye(p)
 for o in (12,20,28):
  for j in (0,1):T[o+4+j,o+j]=-1.;Ti[o+4+j,o+j]=1.
 zt=finite(raw_train)@T.T;zq=finite(raw_query)@T.T;mz=mean@T.T
 sz=zt.std(0);sz[sz<1e-8]=1.
 bz=sz[:,None]*(Ti.T@(coef[1:]/sq[:,None]));cz=np.vstack([coef[:1],bz])
 P=(T@(np.diag(sq**2))@T.T)/(sz[:,None]*sz[None,:])
 pred=predict((mz,sz,cz),zq)
 return pred,{'T':T,'inverse_T':Ti,'feature_mean':mz,'feature_scale':sz,'coef':cz,'penalty':P}
