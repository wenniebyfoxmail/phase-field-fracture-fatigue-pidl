"""HQ published-reference diagnostic. No execution on import."""
import hashlib,json,math,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
import torch
from torch import nn
from torch.nn import functional as F
from tiling import reconstruct
SEED=20261009
class BudgetExpired(Exception):pass

def check_time(deadline):
 if time.monotonic()>=deadline:raise BudgetExpired()

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class Block(nn.Sequential):
 def __init__(self,a,b):
  super().__init__(nn.Conv2d(a,b,3,padding=1,bias=False),nn.GroupNorm(8,b),nn.ReLU(),nn.Conv2d(b,b,3,padding=1,bias=False),nn.GroupNorm(8,b),nn.ReLU())
class UNet(nn.Module):
 def __init__(self):
  super().__init__();self.enc=nn.ModuleList([Block(a,b) for a,b in [(3,16),(16,32),(32,64),(64,128)]]);self.middle=Block(128,256)
  self.dec=nn.ModuleList([Block(a,b) for a,b in [(384,128),(192,64),(96,32),(48,16)]]);self.out=nn.Conv2d(16,1,1)
  for m in self.modules():
   if isinstance(m,nn.Conv2d):
    nn.init.kaiming_normal_(m.weight,mode='fan_in',nonlinearity='relu')
    if m.bias is not None:nn.init.zeros_(m.bias)
   elif isinstance(m,nn.GroupNorm):nn.init.ones_(m.weight);nn.init.zeros_(m.bias)
 def forward(self,x):
  skips=[]
  for layer in self.enc:x=layer(x);skips.append(x);x=F.max_pool2d(x,2)
  x=self.middle(x)
  for layer,skip in zip(self.dec,reversed(skips)):x=layer(torch.cat([F.interpolate(x,scale_factor=2,mode='bilinear',align_corners=False),skip],dim=1))
  return self.out(x)

def loss_fn(logits,target,valid):
 dims=(1,2,3);counts=valid.sum(dims)
 if (counts<=0).any():raise ValueError('No valid loss pixels')
 bce=(F.binary_cross_entropy_with_logits(logits,target,reduction='none')*valid).sum(dims)/counts
 p=torch.sigmoid(logits);dice=(2*(p*target*valid).sum(dims)+1)/((p*valid).sum(dims)+(target*valid).sum(dims)+1)
 return (.5*bce+.5*(1-dice)).mean()

def pair(row,roots,threshold=128):
 root=Path(roots[row['source']])
 with Image.open(root/row['image']) as im:rgb=np.array(ImageOps.exif_transpose(im).convert('RGB'))
 with Image.open(root/row['mask']) as im:
  if im.getexif().get(274,1)!=1:raise ValueError('Unexpected mask orientation')
  gray=np.array(im.convert('L'))
 if rgb.shape[:2]!=gray.shape or list(gray.shape)!=row['shape']:raise ValueError('Changed pair dimensions')
 if row['source']=='BuildCrack':
  if not set(np.unique(gray)).issubset({0,255}):raise ValueError('Changed binary reference')
  target=gray>0
 else:target=gray>=threshold
 return rgb,target

def crop_plan(rows,rng):
 if any(r['role']!='train' or r['source']!='METU' for r in rows):raise ValueError('Training leakage')
 plan=[]
 for r in sorted(rows,key=lambda x:x['id']):
  h,w=r['shape']
  for _ in range(4):plan.append((r,int(rng.integers(max(h-448,0)+1)),int(rng.integers(max(w-448,0)+1))))
 rng.shuffle(plan);return plan

def crop_arrays(rgb,target,y,x):
 a=rgb[y:y+448,x:x+448];b=target[y:y+448,x:x+448];h,w=b.shape
 valid=np.zeros((448,448),np.float32);valid[:h,:w]=1
 a=np.pad(a,((0,448-h),(0,448-w),(0,0)),mode='edge');b=np.pad(b,((0,448-h),(0,448-w)),mode='constant')
 return a.transpose(2,0,1).astype(np.float32)/255,b[None].astype(np.float32),valid[None]

def error(p,y):
 pred=p>=.5;den=int(pred.sum())+int(y.sum())
 return 0. if den==0 else 1-2*int((pred&y).sum())/den

def scores(p):
 if not np.isfinite(p).all() or np.any((p<0)|(p>1)):raise ValueError('Invalid probability')
 q=p.astype(np.float64);ent=np.zeros_like(q);mask=(q>0)&(q<1);v=q[mask];ent[mask]=-v*np.log(v)-(1-v)*np.log1p(-v)
 return float(np.minimum(q,1-q).mean()),float(ent.mean())

def risk_curve(rows,key):
 if not rows:raise ValueError('Empty score set')
 ordered=sorted(rows,key=lambda r:(r[key],r['id']));e=np.array([r['error'] for r in ordered],np.float64)
 risk=np.cumsum(e)/np.arange(1,len(e)+1);return [{'k':i+1,'coverage':(i+1)/len(e),'risk':float(v),'id':ordered[i]['id']} for i,v in enumerate(risk)]

def predict(model,rgb,device,deadline):
 model.eval()
 @torch.no_grad()
 def tile(a):
  check_time(deadline);x=torch.from_numpy(a.transpose(2,0,1).copy()).unsqueeze(0).to(device,dtype=torch.float32)/255
  p=torch.sigmoid(model(x))[0,0].cpu().numpy();check_time(deadline);return p
 return reconstruct(rgb,tile)

def validation(model,rows,roots,device,deadline):
 if not rows or any(r['source']!='METU' or r['role']!='validation' for r in rows):raise ValueError('Invalid validation role')
 values=[]
 for r in rows:
  a,y=pair(r,roots);p=predict(model,a,device,deadline);values.append(error(p,y))
 check_time(deadline);return float(np.mean(values,dtype=np.float64))

def better(score,best):
 if not math.isfinite(score):raise ValueError('Invalid validation score')
 return score<best

def fit(rows,roots,out,device):
 deadline=time.monotonic()+6*3600
 torch.manual_seed(SEED);torch.cuda.manual_seed_all(SEED);rng=np.random.default_rng(SEED)
 model=UNet().to(device);optimizer=torch.optim.Adam(model.parameters(),lr=1e-3,betas=(.9,.999),eps=1e-8,weight_decay=0)
 train=[r for r in rows if r['role']=='train'];val=[r for r in rows if r['role']=='validation'];best=math.inf;history=[];completed=0;position={"epoch":0,"batch_start":None,"phase":"prepared"}
 try:
  for epoch in range(1,41):
   position={"epoch":epoch,"batch_start":None,"phase":"train"};check_time(deadline);plan=crop_plan(train,rng);model.train()
   for start in range(0,len(plan),4):
    position["batch_start"]=start;check_time(deadline);batch=[crop_arrays(*pair(r,roots),y,x) for r,y,x in plan[start:start+4]]
    a,t,v=[torch.from_numpy(np.stack([s[i] for s in batch])).to(device) for i in range(3)]
    optimizer.zero_grad(set_to_none=True);loss=loss_fn(model(a),t,v)
    if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
    loss.backward()
    if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):raise ValueError('Nonfinite gradient')
    optimizer.step()
    if any(not torch.isfinite(p).all() for p in model.parameters()):raise ValueError('Nonfinite parameters')
    check_time(deadline)
   position["phase"]="validation";score=validation(model,val,roots,device,deadline);completed=epoch;position["phase"]="validated"
   state={'model':model.state_dict(),'epoch':epoch,'validation_error':score}
   torch.save(state,out/'last.pt')
   selected=better(score,best)
   if selected:best=score;torch.save(state,out/'best.pt')
   history.append({'epoch':epoch,'validation_error':score,'selected':selected});(out/'selection.json').write_text(json.dumps(history,indent=2))
 except BudgetExpired:
  pass
 finally:
  torch.save({'model':model.state_dict(),'position':position,'selectable':False},out/'stop_state_nonselectable.pt')
  (out/'fit_status.json').write_text(json.dumps({'position':position,'completed_epoch':completed,'has_valid_checkpoint':(out/'best.pt').exists(),'history':history},indent=2))
 if not (out/'best.pt').exists():raise BudgetExpired('No fully validated checkpoint')
 return out/'best.pt'

def final_evaluate(checkpoint,rows,roots,out,device):
 deadline=time.monotonic()+3600;model=UNet().to(device);state=torch.load(checkpoint,map_location=device,weights_only=True);model.load_state_dict(state['model']);all_scores=[]
 final=[r for r in rows if r['role'] in {'internal_test','external_diagnostic'}]
 if len(final)!=438:raise ValueError('Incomplete final inventory')
 for r in final:
  check_time(deadline);a,y=pair(r,roots);p=predict(model,a,device,deadline);lc,h=scores(p)
  path=out/r['source'];path.mkdir(exist_ok=True)
  np.save(path/(r['id']+'.prob.npy'),p);Image.fromarray(((p>=.5)*255).astype(np.uint8)).save(path/(r['id']+'.pred.png'))
  row={'id':r['id'],'source':r['source'],'group':r['group'],'nonempty':bool(y.any()),'error':error(p,y),'U_LC':lc,'U_H':h}
  if r['source']=='METU':
   for threshold in [1,250]:row[f'error_threshold_{threshold}']=error(p,pair(r,roots,threshold)[1])
  all_scores.append(row)
  (out/'partial_scores.json').write_text(json.dumps(all_scores,indent=2))
 check_time(deadline)
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 report={}
 for name,selected in [('METU_internal',[r for r in all_scores if r['source']=='METU']),('BuildCrack_nonempty',[r for r in all_scores if r['source']=='BuildCrack' and r['nonempty']]),('BuildCrack_all',[r for r in all_scores if r['source']=='BuildCrack'])]:
  curves={key:risk_curve(selected,key) for key in ['U_LC','U_H']};aurc={key:float(np.mean([p['risk'] for p in curve])) for key,curve in curves.items()}
  report[name]={'n':len(selected),'aurc':aurc,'delta':aurc['U_H']-aurc['U_LC']}
  (out/(name+'_curves.json')).write_text(json.dumps(curves,indent=2))
  fig,ax=plt.subplots()
  for key,curve in curves.items():ax.plot([x['coverage'] for x in curve],[x['risk'] for x in curve],label=key)
  ax.set(xlabel='Accepted image fraction',ylabel='Mean 1-Dice against published labels',title=f'{name}; run={out.name}; delta={report[name]["delta"]:.6g}');ax.legend();fig.savefig(out/(name+'_risk.png'));plt.close(fig)
 check_time(deadline)
 empty=[r for r in all_scores if r['source']=='BuildCrack' and not r['nonempty']]
 if len(empty)!=3 or len([r for r in all_scores if r['source']=='BuildCrack' and r['nonempty']])!=355:raise ValueError('Reference cohort changed')
 (out/'empty_reference_cases.json').write_text(json.dumps(empty,indent=2))
 families={}
 for r in all_scores:families.setdefault((r['source'],r['group']),[]).append(r)
 group_rows=[{'source':s,'group':g,'n_images':len(rs),'mean_error':float(np.mean([r['error'] for r in rs]))} for (s,g),rs in sorted(families.items())]
 (out/'candidate_group_diagnostics.json').write_text(json.dumps(group_rows,indent=2))
 for source in ['METU','BuildCrack']:
  chosen=sorted([r for r in all_scores if r['source']==source],key=lambda r:(-r['error'],r['id']))[:3]
  fig,axs=plt.subplots(len(chosen),3,figsize=(12,4*len(chosen)),squeeze=False)
  for i,r in enumerate(chosen):
   row=next(x for x in final if x['source']==source and x['id']==r['id']);rgb,y=pair(row,roots);prob=np.load(out/source/(r['id']+'.prob.npy'))
   for ax,a,title in zip(axs[i],[rgb,y,prob>=.5],['RGB','published reference','prediction']):ax.imshow(a);ax.set_title(r['id']+' '+title);ax.axis('off')
  fig.savefig(out/(source+'_highest_reference_error.png'));plt.close(fig);check_time(deadline)
 (out/'README_analysis.md').write_text('Finite published-label diagnostic; not physical crack truth. Read result.json then source-specific risk curves, empty_reference_cases.json, candidate_group_diagnostics.json and fixed top-three highest-reference-error examples. No independent-site confidence claim. Run '+out.name)
 report['checkpoint_epoch']=state['epoch'];report['scope']='finite published-label diagnostic; not independent-site inference'
 (out/'final_scores.json').write_text(json.dumps(all_scores,indent=2));(out/'result.json').write_text(json.dumps(report,indent=2));return report
