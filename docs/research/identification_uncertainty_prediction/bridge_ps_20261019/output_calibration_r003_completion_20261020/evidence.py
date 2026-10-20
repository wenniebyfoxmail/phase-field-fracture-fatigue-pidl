"""Bounded streamed evidence and first-failure context. No scientific source access."""
from pathlib import Path
import csv,json,os,hashlib
import numpy as np
from engine import ARMS,PAIRS,finite

def write(path,obj,exclusive=False):
 path=Path(path);dest=path if exclusive else path.with_suffix(path.suffix+'.partial')
 with dest.open('x' if exclusive else 'w') as f:json.dump(obj,f,sort_keys=True,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
 if not exclusive:dest.replace(path)

class Audit:
 def __init__(self,root):self.root=Path(root);self.context={};self.failed=False;self.enter('startup')
 def enter(self,stage,**details):
  self.context={'stage':stage,**details};write(self.root/'last_context.json',self.context)
 def fail(self,exc):
  if not self.failed:
   self.failed=True;write(self.root/'first_failure.json',{'status':'STOPPED_BEFORE_RAISE','context':self.context,'type':type(exc).__name__,'message':str(exc)[:2048]},exclusive=True)

def mapped(path,shape,dtype='<f8'):
 # Fresh exact-size files; never silently truncate an existing evidence file.
 n=int(np.prod(shape))*np.dtype(dtype).itemsize
 with Path(path).open('xb') as f:f.truncate(n)
 a=np.memmap(path,dtype=dtype,mode='r+',shape=shape);a[:]=np.nan;return a

class DiskSink:
 def __init__(self,root,data):
  self.root=Path(root);self.data=data;self.handles=[];self.i=0;self.o=0;self.groups=None;self.cells={};self.selections={};self.outer_lookup={};self.worst={}
 def begin(self,plan,groups,horizons,N):
  self.plan=plan;self.groups=groups;self.horizons=horizons;self.root.mkdir(exist_ok=False)
  self.anchor_cases=[i for i,g in enumerate(self.data.groups) if g in groups];self.anchor_index={case:row for row,case in enumerate(self.anchor_cases)}
  self.loss=mapped(self.root/'inner_losses.f64',(plan['inner_rows'],len(PAIRS),3))
  self.bases=mapped(self.root/'outer_bases.f64',(plan['outer_rows'],2,2*self.data.coarse_side**2))
  self.anchors=mapped(self.root/'current_anchors.f32',(len(self.anchor_cases),2,self.data.native_side,self.data.native_side),'<f4')
  self.targets=mapped(self.root/'outer_targets.f32',(plan['outer_rows'],2,self.data.native_side,self.data.native_side),'<f4')
  self.anchor_written=set()
  for name in ('inner_index.jsonl','model_provenance.jsonl','outer_fields.jsonl','selections.jsonl'):
   h=(self.root/name).open('x');self.handles.append(h)
  self.inner_index,self.prov,self.field_index,self.selection_file=self.handles
  self.rows=(self.root/'outer_scores.csv').open('x',newline='');self.handles.append(self.rows);self.writer=None
  write(self.root/'array_schema.json',{'loss_shape':list(self.loss.shape),'loss_dtype':'<f8','loss_order':'outer sorted group, H configured order, inner sorted group, ascending case','loss_columns':['balanced','full','band'],'candidate_order':PAIRS,'outer_base_shape':list(self.bases.shape),'base_dtype':'<f8','base_order':['CURRENT','HISTORY'],'arms':ARMS,'native_field_recipe':'float32 current identified by original manifest +float64 base coarse arrays; engine.decoded_fields preserves native arithmetic order','coarse_side':self.data.coarse_side,'anchor_cases':self.anchor_cases,'anchor_shape':list(self.anchors.shape),'target_shape':list(self.targets.shape),'native_dtype':'<f4','input_identity':getattr(self.data,'identity',{'kind':'ARTIFICIAL'})},True)
 def model(self,models,final):
  self.prov.write(json.dumps({**models.provenance,'final':final})+'\n');self.prov.flush()
  if final:
   arrays={f'{name}_{j}':v for name,m in [('current',models.current),('history',models.history),('m',models.residualizer)] for j,v in enumerate(m)}
   p=self.root/f'model_{self.groups.index(models.fold.outer)}_{models.fold.horizon}.npz'
   with p.open('xb') as f:np.savez(f,**arrays,normalizer=models.normalizer)
 def inner(self,fold,i,values):
  if self.i>=len(self.loss) or values.shape!=(len(PAIRS),3):raise ValueError('inner stream bounds')
  finite(values,'streamed inner values');self.loss[self.i]=values
  self.inner_index.write(json.dumps({'row':self.i,'case':i,'outer':fold.outer,'inner':fold.inner,'H':fold.horizon})+'\n');self.i+=1
 def selection(self,outer,h,chosen,means):
  self.selections[outer,h]=tuple(chosen)
  self.selection_file.write(json.dumps({'outer':outer,'H':h,'chosen_U_C_A':chosen,'candidate_group_mean_balanced':means.tolist()})+'\n');self.selection_file.flush()
 def outer(self,fold,i,values,cc,ch,weights,fields,target,anchor,norm):
  if self.o>=len(self.bases) or values.shape!=(7,3):raise ValueError('outer stream bounds')
  self.bases[self.o,0]=cc;self.bases[self.o,1]=ch
  if i in self.anchor_written and not np.array_equal(self.anchors[self.anchor_index[i]],anchor):raise ValueError('current anchor changed across H')
  self.anchors[self.anchor_index[i]]=anchor;self.anchor_written.add(i);self.targets[self.o]=target
  self.field_index.write(json.dumps({'row':self.o,'case':i,'group':fold.outer,'H':fold.horizon,'weights':weights,'normalizer':norm.tolist()})+'\n')
  self.outer_lookup[i,fold.horizon]={'row':self.o,'weights':weights,'normalizer':norm.tolist()}
  for j,arm in enumerate(ARMS):
   row={'case':i,'group':fold.outer,'H':fold.horizon,'arm':arm,'balanced':float(values[j,0]),'full':float(values[j,1]),'band':float(values[j,2]),'lambda_g':weights[j][0],'lambda_s':weights[j][1]}
   # Separate saved increment diagnostics; no native-error decomposition/bound.
   pd=fields[j]-anchor;td=(target-anchor).astype(np.float64)
   for channel in (0,1):
    p,t=pd[channel],td[channel]
    row[f'G_increment_{channel}']=float(abs(p.mean()-t.mean())/norm[channel])
    row[f'S_increment_{channel}']=float(np.abs((p-p.mean())-(t-t.mean())).mean()/norm[channel])
    row[f'pred_mean_increment_{channel}']=float(p.mean()/norm[channel]);row[f'ref_mean_increment_{channel}']=float(t.mean()/norm[channel])
    pm=float(np.abs(p).mean()/norm[channel]);tm=float(np.abs(t).mean()/norm[channel]);lo=max(0,self.data.centers[i]-self.data.half_height);hi=min(self.data.native_side,self.data.centers[i]+self.data.half_height+1)
    row[f'pred_mass_{channel}']=pm;row[f'ref_mass_{channel}']=tm;row[f'mass_ratio_{channel}']=None if tm==0 else pm/tm
    row[f'sign_mismatch_{channel}']=None if p.mean()==0 or t.mean()==0 else int(p.mean()*t.mean()<0)
    row[f'ref_exact_zero_{channel}']=int(tm==0)
    ep=fields[j,channel]-target[channel];row[f'native_full_{channel}']=float(np.abs(ep).mean()/norm[channel]);row[f'native_band_{channel}']=float(np.abs(ep[lo:hi]).mean()/norm[channel])
    pp=np.unravel_index(np.argmax(abs(p[lo:hi])),p[lo:hi].shape);tp=np.unravel_index(np.argmax(abs(t[lo:hi])),t[lo:hi].shape)
    row[f'peak_grid_distance_{channel}']=None if pm==0 or tm==0 else float(np.hypot(pp[0]-tp[0],pp[1]-tp[1]))

   finite(list(v for v in row.values() if isinstance(v,(int,float))),'outer row')
   if self.writer is None:self.writer=csv.DictWriter(self.rows,fieldnames=list(row));self.writer.writeheader()
   self.writer.writerow(row);self.cells.setdefault((fold.outer,fold.horizon,arm),[]).append(row)
  key=(fold.outer,fold.horizon);candidate=(float(values[-1,0]),-i)
  if key not in self.worst or candidate>self.worst[key][0]:self.worst[key]=(candidate,i)
  self.o+=1
 def progress(self,counts):
  self.loss.flush();self.bases.flush();self.anchors.flush();self.targets.flush()
  for h in self.handles:h.flush()
  write(self.root/'progress.json',counts)
 def finish(self,counts,plan):
  if self.i!=plan['inner_rows'] or self.o!=plan['outer_rows']:raise ValueError('evidence incomplete')
  finite(self.loss,'complete saved inner losses');finite(self.bases,'complete outer bases');finite(self.anchors,'complete anchors');finite(self.targets,'complete outer native targets');self.progress(counts)
  group=[]
  for (g,h,arm),rows in self.cells.items():
   group.append({'group':g,'H':h,'arm':arm,'n':len(rows),**{k:(None if all(r[k] is None for r in rows) else float(np.mean([r[k] for r in rows if r[k] is not None]))) for k in rows[0] if k not in ('case','group','H','arm')}})
  for summary in group:
   rows=self.cells[summary['group'],summary['H'],summary['arm']]
   for channel in (0,1):
    for k in ('sign_mismatch','peak_grid_distance','mass_ratio'):summary[f'{k}_valid_n_{channel}']=sum(r[f'{k}_{channel}'] is not None for r in rows)
  lookup={(r['group'],r['H'],r['arm']):r for r in group};pairs=[]
  for g in self.groups:
   for h in self.horizons:
    pairs.append({'group':g,'H':h,'primary_C_minus_A':lookup[g,h,'SELECT_C']['balanced']-lookup[g,h,'SELECT_A']['balanced'],**{a:lookup[g,h,a]['balanced'] for a in ARMS},'worst_selected_A_case':self.worst[g,h][1]})
  write(self.root/'group_horizon_results.json',{'group_scores':group,'paired':pairs,'primary_mean':float(np.mean([r['primary_C_minus_A'] for r in pairs])),'counts':counts,'precision':'E native prediction64-target32 promoted; G/S separate increment chain, no additive fraction','limits':'development exposed groups; unknown specimen independence; release steps/current anchor; R003 original warning breach remains; not causal/road validation'},True)
  for h in self.handles:h.close()
 def close(self):
  for h in self.handles:
   if not h.closed:h.close()
  for name in ('loss','bases','anchors','targets'):
   obj=getattr(self,name,None)
   if obj is not None:obj.flush();obj._mmap.close();setattr(self,name,None)


def read_fields(root,case,horizon):
 """Self-contained exact reconstruction of ALL seven native fields, no estimator or source data."""
 from engine import decoded_fields
 root=Path(root)
 if (root/'component_sources.json').is_file():
  sources=json.loads((root/'component_sources.json').read_text())
  key=str(case)+':'+str(horizon)
  if key not in sources['case_horizon_source']:raise ValueError('missing virtual field identity')
  return read_fields(Path(sources['case_horizon_source'][key]),case,horizon)
 schema=json.loads((root/'array_schema.json').read_text());entry=None
 with (root/'outer_fields.jsonl').open() as f:
  for line in f:
   e=json.loads(line)
   if (e['case'],e['H'])==(case,horizon):entry=e;break
 if entry is None:raise ValueError('missing field identity')
 maps=[]
 try:
  for name,dtype,shape in [('outer_bases.f64','<f8',schema['outer_base_shape']),('current_anchors.f32','<f4',schema['anchor_shape']),('outer_targets.f32','<f4',schema['target_shape'])]:
   maps.append(np.memmap(root/name,dtype=dtype,mode='r',shape=tuple(shape)))
  bases,anchors,targets=maps;row=entry['row']
  anchor_row=schema.get('anchor_cases',list(range(len(anchors)))).index(case)
  fields=decoded_fields(anchors[anchor_row],bases[row,0],bases[row,1],entry['weights'],schema['coarse_side'])
  return fields,targets[row].copy(),anchors[anchor_row].copy(),entry
 finally:
  for m in maps:m._mmap.close()
