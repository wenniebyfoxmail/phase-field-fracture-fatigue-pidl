#!/usr/bin/env python3
"""Fixed-state PIDL optimization/representation diagnostics; never a rollout."""
import argparse,copy,datetime as dt,hashlib,json,math,os,sys,time
from pathlib import Path
import numpy as np
import torch
from scipy.optimize import minimize
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'SENS_tensile'),str(ROOT/'source'),str(Path(__file__).parent)]
from run_native_q4_one_step_matrix import make_field
from run_native_q4_smooth_b0_picard import AnchoredSmoothDamage
from q4_quadrature import q4_shape_data,q4_interpolate,q4_gradient
from compute_energy import compute_energy,strain_energy_with_split
from material_properties import MaterialProperties
from pff_model import PFFModel
from plateau_head_fit import fit_uv_head,fit_smooth_damage_head

PROTOCOL='S04-E011-PBD-r1'
class BudgetStop(Exception):pass
class ObjectiveDomainError(Exception):pass
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def dump(p,v):
 def scalar(x):
  if isinstance(x,np.generic):return x.item()
  raise TypeError(type(x).__name__)
 p.write_text(json.dumps(v,indent=2,allow_nan=False,default=scalar)+'\n')
def clone_params(net):return [p.detach().clone() for p in net.parameters()]
def restore(net,values):
 with torch.no_grad():
  for p,v in zip(net.parameters(),values):p.copy_(v)
def tensor_hash(x):return hashlib.sha256(x.detach().cpu().contiguous().numpy().tobytes()).hexdigest()

class LocalProblem:
 def __init__(self,z,device):
  self.device=device;self.n=len(z['nodes']);self.data=z
  t=lambda x:torch.as_tensor(x,device=device,dtype=torch.float64)
  self.x=t(z['nodes']);self.cells=torch.as_tensor(z['cells'],device=device,dtype=torch.long)
  self.N,self.B,self.w=q4_shape_data(self.x,self.cells);self.area=self.w.sum(1)
  self.uf,self.vf,self.df=[t(z[k]) for k in ['u_fem','v_fem','d_fem']]
  self.hist=t(z['pidl_hist_alpha_pre']);self.f=t(z['pidl_f_pre'])
  self.hgp=q4_interpolate(self.hist,self.cells,self.N)
  self.fu=torch.as_tensor(z['freeu'],device=device,dtype=torch.long)
  self.mass=torch.zeros(self.n,device=device,dtype=torch.float64)
  for j in range(4):self.mass.scatter_add_(0,self.cells[:,j],(self.w*self.N[:,j]).sum(1))
  self.mat=MaterialProperties(1.,.3,1.,.01);self.model=PFFModel('AT1','volumetric',.005,residual_stiffness=0.)
  assert self.model.irrPenalty()==16875
  self.ref_grad=torch.stack([self.grad(self.uf),self.grad(self.vf)])
  self.uv_denom=(self.w*self.ref_grad.square().sum((0,3))).sum().detach()
 def grad(self,x):return q4_gradient(x,self.cells,self.B)
 def fields(self,field):return field.fieldCalculation(self.x)
 def parts(self,u,v,d):
  gu,gv,gd=self.grad(u),self.grad(v),self.grad(d);dg=q4_interpolate(d,self.cells,self.N)
  observer=getattr(self,'trace_observer',None)
  if observer is not None:observer((gu[:,:,0]+gv[:,:,1]).detach())
  el,_=strain_energy_with_split(gu[:,:,0],gv[:,:,1],.5*(gu[:,:,1]+gv[:,:,0]),dg,self.mat,self.model)
  ee=(self.w*el).sum();ed=(self.w*self.f*.375*(dg+.0001*gd.square().sum(2))).sum()
  eh=(self.w*.5*16875*torch.relu(self.hgp-dg).square()).sum()
  return ee,ed,eh
 def loss(self,field,block,kind,target=None):
  u,v,d=self.fields(field)
  if block=='U':
   if kind=='energy':return self.parts(u,v,self.df)[0]
   return (self.w*(self.grad(u-self.uf).square().sum(2)+self.grad(v-self.vf).square().sum(2))).sum()/self.uv_denom
  if kind=='energy':return sum(self.parts(self.uf,self.vf,d))
  assert target is not None
  delta=d-target
  return ((self.mass*delta.square()).sum()+.0001*(self.w*self.grad(delta).square().sum(2)).sum())/((self.mass*target.square()).sum()+.0001*(self.w*self.grad(target).square().sum(2)).sum())
 def measures(self,u,v,d):
  u=u.detach().to(torch.float64).clone().requires_grad_(True);v=v.detach().to(torch.float64).clone().requires_grad_(True);d=d.detach().to(torch.float64).clone().requires_grad_(True)
  parts=self.parts(u,v,d);gu,gv,gd=torch.autograd.grad(sum(parts),(u,v,d))
  force=torch.cat([gu,gv])[self.fu];proj=d.detach()-torch.clamp(d.detach()-gd.detach(),0,1)
  uv_err=(self.mass*((u.detach()-self.uf)**2+(v.detach()-self.vf)**2)).sum()
  uv_norm=(self.mass*(self.uf**2+self.vf**2)).sum()
  h1=(self.w*(self.grad(u.detach()-self.uf).square().sum(2)+self.grad(v.detach()-self.vf).square().sum(2))).sum()/self.uv_denom
  dg=q4_interpolate(d.detach(),self.cells,self.N)
  out=dict(E_el=float(parts[0]),E_d=float(parts[1]),E_hist=float(parts[2]),physical_energy=float(sum(parts)),free_u_l2=float(torch.linalg.vector_norm(force)),
   box_projected_damage_l2=float(torch.linalg.vector_norm(proj)),box_projected_damage_inf=float(proj.abs().max()),
   uv_mass_rel_L2=float(torch.sqrt(uv_err/uv_norm)),uv_H1_rel=float(torch.sqrt(h1)),d_min=float(d.min()),d_max=float(d.max()),gp_healing_max=float(torch.relu(self.hgp-dg).max()))
  assert all(math.isfinite(x) for x in out.values());return out
 def contract(self):
  parts=self.parts(self.uf,self.vf,self.df)
  ref=compute_energy(self.x,self.uf,self.vf,self.df,self.hist,self.mat,self.model,self.area,self.cells,f_fatigue=self.f,irreversibility_penalty_cfg={'enable':True,'mode':'fem_gp_q4'})
  error=max(abs(float(a-b))/max(1,abs(float(b))) for a,b in zip(parts,ref));assert error<1e-10
  u=self.uf.clone().requires_grad_(True);v=self.vf.clone().requires_grad_(True)
  gu,gv=torch.autograd.grad(self.parts(u,v,self.df)[0],(u,v));force=torch.cat([gu,gv]);native=torch.as_tensor(self.data['ru_fem'],dtype=torch.float64,device=self.device)
  re=float((force-native).abs().max());assert re<1e-10 and float(torch.linalg.vector_norm(force[self.fu]))<1e-8
  d=self.df.clone().requires_grad_(True);auto=torch.autograd.grad(sum(self.parts(self.uf,self.vf,d)),d)[0]
  from run_native_q4_direct_q4_damage import analytic_damage_gradient
  analytic=analytic_damage_gradient(self.x,self.cells,self.uf,self.vf,self.df,self.hist,self.f,self.mat,self.model)
  ge=float((auto-analytic).abs().max());assert ge<1e-10
  return dict(cached_source_energy_maxscaled=error,native_fem_u_force_maxabs=re,fem_free_u_l2=float(torch.linalg.vector_norm(force[self.fu])),analytic_damage_gradient_maxabs=ge,PIDL_penalty=16875,FEM_penalty=421875)

def make_smooth(state,problem):
 f=make_field(state,problem.device,.11999988,'bounded_nonsmooth');f.net=f.net.double();f.domain_extrema=f.domain_extrema.double();f.lmbda=torch.tensor([.11999988],device=problem.device,dtype=torch.float64);f.theta=torch.tensor([math.pi/2],device=problem.device,dtype=torch.float64)
 with torch.no_grad():r=f.net(problem.x)[:,2]
 f.alpha_constraint=AnchoredSmoothDamage(r,1e-7).to(problem.device)
 return f

def b0_contract(problem,field):
 with torch.no_grad():
  raw=field.net(problem.x)[:,2];d=field.alpha_constraint(raw);a=field.alpha_constraint
  diag=a.diagnostics(raw);hard=a.hard_b0
  assert all(torch.isfinite(v).all() for v in list(a.state_dict().values())+list(diag.values())+[d])
  nodal=float((d-hard).abs().max());gp=float(q4_interpolate(d-hard,problem.cells,problem.N).abs().max())
  slope=float(((diag['derivative']-a.legacy_slope).abs()/a.legacy_slope).max())
  legacy=torch.where(raw.abs()<=2,raw/4+.5,torch.where(raw>2,1+.001*(raw-2),.001*(raw+2)))
  assert nodal<=2e-7 and gp<=2e-7 and slope<=2e-5 and float(d.min())>=0 and float(d.max())<=1
  return dict(smooth_bounded_nodal_maxabs=nodal,smooth_bounded_gp_maxabs=gp,initial_derivative_maxrelative=slope,legacy_to_box_maxabs=float((legacy-hard).abs().max()),all_finite=True,damage_min=float(d.min()),damage_max=float(d.max()))

def replay_head(problem,state,head,block,expected,folder,target=None):
 field=make_smooth(state,problem)
 with torch.no_grad():
  h=torch.as_tensor(head,device=problem.device,dtype=torch.float64)
  rows=slice(0,2) if block=='U' else slice(2,3)
  if h.ndim==1:h=h[None,:]
  field.net.output_layer.weight[rows].copy_(h[:,:-1]);field.net.output_layer.bias[rows].copy_(h[:,-1])
  u,v,d=problem.fields(field)
  actual=[u,v] if block=='U' else [d]
  errors=[float((a-torch.as_tensor(e,device=problem.device)).abs().max()) for a,e in zip(actual,expected)]
 return save_arm(problem,field,block,folder,dict(role='actual_Torch_frozen_head_witness',numpy_replay_maxabs=errors,head_maxabs=float(h.abs().max())),target)

def fd_check(problem,field,block):
 params=list(field.net.parameters());original=clone_params(field.net);field.net.zero_grad(set_to_none=True)
 loss=problem.loss(field,block,'energy');loss.backward();gr=[p.grad.detach().clone() if p.grad is not None else torch.zeros_like(p) for p in params]
 gen=torch.Generator(device=problem.device);gen.manual_seed(173);rows=[]
 try:
  for label in ['negative_gradient','seeded_random']:
   vec=[-g for g in gr] if label=='negative_gradient' else [torch.randn(p.shape,dtype=p.dtype,device=p.device,generator=gen) for p in params]
   norm=torch.sqrt(sum(x.square().sum() for x in vec));vec=[x/norm for x in vec];ad=float(sum((g*x).sum() for g,x in zip(gr,vec)))
   for h in [1e-4,1e-5,1e-6,1e-7,1e-8]:
    vals=[]
    for sign in [1,-1]:
     with torch.no_grad():
      for p,p0,x in zip(params,original,vec):p.copy_(p0+sign*h*x)
      vals.append(float(problem.loss(field,block,'energy')))
    fd=(vals[0]-vals[1])/(2*h);rows.append(dict(direction=label,h=h,ad=ad,fd=fd,abs_error=abs(fd-ad),scaled_error=abs(fd-ad)/max(abs(ad),1e-12)))
 finally:restore(field.net,original)
 for label in ['negative_gradient','seeded_random']:
  q=[r for r in rows if r['direction']==label];assert min(r['abs_error'] for r in q)<=1e-8+1e-4*abs(q[0]['ad']),('FD contract',block,q)
 return rows

def optimize(field,objective,folder,*,cap=200,deadline_seconds=1800):
 folder.mkdir();net=field.net;params=list(net.parameters());start=time.monotonic();trace=[];accepted=[];evals=0
 def evaluate(backward):
  nonlocal evals
  if evals>=cap-1 or time.monotonic()-start>=deadline_seconds:raise BudgetStop()
  net.zero_grad(set_to_none=True);evals+=1
  try:loss=objective()
  except ObjectiveDomainError:
   trace.append(dict(evaluation=evals,loss=None,backward=backward,invalid_original_domain=True));raise
  assert torch.isfinite(loss)
  if backward:
   loss.backward();assert all(p.grad is None or torch.isfinite(p.grad).all() for p in params)
  trace.append(dict(evaluation=evals,loss=float(loss.detach()),backward=backward));return loss
 initial=float(evaluate(False));last=initial;state=clone_params(net);reason='evaluation_budget'
 opt=torch.optim.LBFGS(params,lr=1.,max_iter=1,max_eval=20,history_size=5,tolerance_grad=0.,tolerance_change=0.,line_search_fn='strong_wolfe')
 try:
  while evals<cap-2:
   before=clone_params(net)
   opt.step(lambda:evaluate(True))
   value=float(evaluate(False));assert value<=last+max(1e-10,64*torch.finfo(params[0].dtype).eps)*max(1,abs(last)),('accepted loss increase',last,value)
   change=max(float((p-p0).abs().max()) for p,p0 in zip(params,before));last=value;state=clone_params(net)
   accepted.append(dict(accepted=len(accepted)+1,evaluations=evals,loss=value,param_delta_inf=change))
   if change==0:reason='exact_parameter_stagnation';break
 except ObjectiveDomainError:
  restore(net,state);reason='original_objective_domain_failure'
 except BudgetStop:
  restore(net,state);reason='evaluation_budget' if evals>=cap-3 else 'wall_deadline'
 except Exception:
  restore(net,state);dump(folder/'trace.json',trace);dump(folder/'accepted.json',accepted);raise
 restore(net,state)
 assert abs(float(objective().detach())-last)<=max(1e-10,64*torch.finfo(params[0].dtype).eps)*max(1,abs(last))
 torch.save(net.state_dict(),folder/'accepted_network.pt');dump(folder/'trace.json',trace);dump(folder/'accepted.json',accepted)
 result=dict(initial_loss=initial,final_loss=last,evaluations=evals,accepted_updates=len(accepted),stop=reason,elapsed_seconds=time.monotonic()-start,cap=cap,post_restore_readout_evaluations=1)
 dump(folder/'optimizer.json',result);return result

def direct_q4(problem,initial,folder,cap=800):
 folder.mkdir();trace=[];accepted=[];start=time.monotonic();last_x=initial.detach().cpu().numpy().copy();ncall=0;cache={}
 def fun(x):
  nonlocal ncall
  if ncall>=cap-1 or time.monotonic()-start>=1800:raise BudgetStop()
  d=torch.as_tensor(np.asarray(x),device=problem.device,dtype=torch.float64).clone().requires_grad_(True)
  value=sum(problem.parts(problem.uf,problem.vf,d));g=torch.autograd.grad(value,d)[0];assert torch.isfinite(value) and torch.isfinite(g).all()
  ncall+=1;val=float(value);grad=g.detach().cpu().numpy();cache.update(x=np.asarray(x).copy(),value=val,gradient=grad.copy());trace.append(dict(evaluation=ncall,energy=val));return val,grad
 def callback(x):
  nonlocal last_x
  last_x=np.asarray(x).copy();accepted.append(dict(iteration=len(accepted)+1,evaluations=ncall))
 reason='library_exit';res=None
 try:
  res=minimize(fun,last_x,method='L-BFGS-B',jac=True,bounds=[(0.,1.)]*len(last_x),callback=callback,options=dict(maxiter=cap,maxfun=cap,maxls=30,maxcor=10,ftol=1e-14,gtol=1e-10))
  last_x=res.x.copy();reason=str(res.message)
 except BudgetStop:reason='evaluation_budget' if ncall>=cap-1 else 'wall_deadline'
 d=torch.as_tensor(last_x,device=problem.device,dtype=torch.float64)
 report=problem.measures(problem.uf,problem.vf,d);report.update(evaluations=ncall,accepted_iterations=len(accepted),stop=reason,elapsed_seconds=time.monotonic()-start,closed_box_KKT=report['box_projected_damage_l2']<=4e-6,cap=cap)
 np.save(folder/'accepted_damage.npy',last_x);dump(folder/'trace.json',trace);dump(folder/'result.json',report);return d,report

def save_arm(problem,field,block,folder,result,target=None):
 with torch.no_grad():u,v,d=problem.fields(field)
 if block=='U':d=problem.df
 else:u,v=problem.uf,problem.vf
 measures=problem.measures(u,v,d);result.update(measures)
 if target is not None:
  result['damage_target_mass_rel_L2']=float(torch.sqrt((problem.mass*(d-target).square()).sum()/(problem.mass*target.square()).sum()))
 np.savez_compressed(folder/'fields.npz',u=u.detach().cpu().numpy(),v=v.detach().cpu().numpy(),d=d.detach().cpu().numpy())
 dump(folder/'result.json',result);return result

def main(z):
 assert not z.out.exists();z.out.mkdir(parents=True)
 torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.manual_seed(1)
 contract=json.loads(z.contract.read_text());assert contract['protocol']==PROTOCOL
 for item in contract['files']:
  p=Path(item['path']);assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],str(p)
 device=torch.device(z.device);assert device.type=='cuda' and torch.cuda.is_available()
 receipt=dict(protocol=PROTOCOL,phase=z.phase,commit=contract['commit'],pid=os.getpid(),host=os.uname().nodename,device=str(device),gpu_visible=os.environ.get('CUDA_VISIBLE_DEVICES'),command=sys.argv,started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),history_commits=0,rollout_steps=0)
 dump(z.out/'receipt.json',receipt);allrows=[]
 try:
  for item in contract['states']:
   cycle=item['cycle'];a=np.load(item['input']);data={k:a[k] for k in a.files};assert data['nodes'].shape==(86756,2) and data['cells'].shape==(86408,4);problem=LocalProblem(data,device)
   assert cycle in [1,20] and item['step']==5*(cycle-1)+4
   state=torch.load(item['model'],map_location=device,weights_only=True)
   folder=z.out/f'c{cycle}_s4';folder.mkdir();dump(folder/'operator_contract.json',problem.contract())
   field=make_smooth(state,problem);anchor={k:v.detach().clone() for k,v in field.alpha_constraint.state_dict().items()};anchor_id={k:tensor_hash(v) for k,v in anchor.items()}
   with torch.no_grad():u0,v0,d0=problem.fields(field)
   np.savez_compressed(folder/'b0_fields.npz',u=u0.cpu().numpy(),v=v0.cpu().numpy(),d=d0.cpu().numpy())
   dump(folder/'anchor.json',anchor_id);dump(folder/'b0_contract.json',b0_contract(problem,field))
   if z.phase=='probe':
    torch.cuda.reset_peak_memory_stats()
    for block in ['U','D']:
     field.net.zero_grad(set_to_none=True);probe_loss=problem.loss(field,block,'energy');assert torch.isfinite(probe_loss);probe_loss.backward()
     assert all(p.grad is None or torch.isfinite(p.grad).all() for p in field.net.parameters())
    free,total=torch.cuda.mem_get_info();peak=torch.cuda.max_memory_allocated()
    assert free>=3*1024**3
    dump(z.out/'probe_pass.json',dict(status='passed',cycle=cycle,dtype='float64',network='8x400',fullbatch_nodes=problem.n,backwards=2,peak_allocated=peak,free_after=free,total=total,history_size=5,optimizer_steps=0,history_commits=0));return
   # Exact original float32 joint objective is a separate control; never
   # conflate it with the new float64 bounded conditional blocks.
   legacy=make_field(state,device,.11999988,'legacy_nonsmooth');x32=problem.x.float();h32=problem.hist.float();f32=problem.f.float();area32=q4_shape_data(x32,problem.cells)[2].sum(1)
   def original_parts():
    u,v,d=legacy.fieldCalculation(x32)
    return compute_energy(x32,u,v,d,h32,problem.mat,problem.model,area32,problem.cells,f_fatigue=f32,irreversibility_penalty_cfg={'enable':True,'mode':'fem_gp_q4'})
   def original_loss():
    parts=original_parts();reg=sum(p.square().sum() for name,p in legacy.net.named_parameters() if 'weight' in name)
    total=sum(parts)
    if not bool(torch.isfinite(total)) or float(total.detach())<=0:raise ObjectiveDomainError('Original unbounded-damage log-energy domain failed')
    return torch.log10(total)+1e-5*reg
   original_base=[float(x.detach()) for x in original_parts()];recorded=np.load(contract['energy_table'])[item['step'],1:4]
   errors=[abs(a-float(b))/max(abs(float(b)),1e-10) for a,b in zip(original_base,recorded)]
   original_gate=bool(max(errors)<=1e-4)
   dump(folder/'original_objective_reproduction.json',dict(parts=original_base,recorded=recorded.tolist(),relative_errors=errors,passed=original_gate,threshold=1e-4,changed_original_gate=False))
   if original_gate:
    arm=folder/'original_joint_LBFGS';res=optimize(legacy,original_loss,arm)
    with torch.no_grad():lu,lv,ld=legacy.fieldCalculation(x32)
    res.update(problem.measures(lu,lv,ld));res.update(cycle=cycle,substep=4,step=item['step'],block='original_joint',kind='original_logE_weight_regularizer',weight_regularizer=1e-5,source_objective_pass=True,fresh_theta0=True)
    np.savez_compressed(arm/'fields.npz',u=lu.cpu().numpy(),v=lv.cpu().numpy(),d=ld.cpu().numpy());dump(arm/'result.json',res);allrows.append(res);dump(z.out/'rows.json',allrows)
   del legacy
   dump(folder/'fd_U.json',fd_check(problem,field,'U'));dump(folder/'fd_D.json',fd_check(problem,field,'D'))
   save_arm(problem,field,'U',folder,{'role':'initial_U_B0'});initial_d=problem.measures(problem.uf,problem.vf,d0)
   dump(folder/'initial_D.json',initial_d)
   with torch.no_grad():features=field.net.encode(problem.x).detach().cpu().numpy()
   uv=fit_uv_head(features,data['nodes'],.11999988,math.pi/2,data['u_fem'],data['v_fem'],problem.mass.cpu().numpy())
   np.savez_compressed(folder/'head_U.npz',head=uv['head'],u=uv['u'],v=uv['v'])
   report={k:v for k,v in uv.items() if k not in ['head','u','v']};witness=folder/'head_U_actual';witness.mkdir();report['actual_Torch']=replay_head(problem,state,uv['head'],'U',[uv['u'],uv['v']],witness);dump(folder/'head_U.json',report)
   qc,qreport=direct_q4(problem,d0,folder/'direct_Q4')
   dh=fit_smooth_damage_head(features,qc.detach().cpu().numpy(),problem.mass.cpu().numpy(),anchor)
   np.savez_compressed(folder/'head_D.npz',head=dh['head'],raw=dh['raw'],d=dh['d'])
   witness=folder/'head_D_actual';witness.mkdir();dr={k:v for k,v in dh.items() if k not in ['head','raw','d']};dr['actual_Torch']=replay_head(problem,state,dh['head'],'D',[dh['d']],witness,qc);dump(folder/'head_D.json',dr)
   del features,uv,dh,field
   for block,kind in [('U','energy'),('U','supervised'),('D','energy'),('D','supervised')]:
    field=make_smooth(state,problem)
    assert {k:tensor_hash(v) for k,v in field.alpha_constraint.state_dict().items()}==anchor_id
    arm=folder/(block+'_'+kind);target=qc if block=='D' and kind=='supervised' else None
    initial=float(problem.loss(field,block,kind,target).detach());scale=initial if kind=='energy' else 1.
    objective=lambda:problem.loss(field,block,kind,target)/scale
    result=optimize(field,objective,arm);result.update(block=block,kind=kind,objective_scale=scale,weight_regularizer=0.,fresh_theta0=True,conditional_Q4_target_closed=qreport['closed_box_KKT'] if block=='D' else None)
    row=save_arm(problem,field,block,arm,result,qc if block=='D' else None);row.update(cycle=cycle,substep=4,step=item['step']);allrows.append(row);dump(z.out/'rows.json',allrows)
    assert {k:tensor_hash(v) for k,v in field.alpha_constraint.state_dict().items()}==anchor_id
    del field;torch.cuda.empty_cache()
   del problem,state,qc;torch.cuda.empty_cache()
  for item in contract['files']:assert sha(item['path'])==item['sha256'],'Original input changed'
  dump(z.out/'complete.json',dict(status='completed',states=2,neural_arms=len(allrows),history_commits=0,finished_utc=dt.datetime.now(dt.timezone.utc).isoformat()))
 except Exception as e:
  dump(z.out/'failure.json',dict(type=type(e).__name__,message=str(e),completed_arms=len(allrows),history_commits=0));raise

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--contract',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--phase',choices=['probe','production'],required=True);ap.add_argument('--device',default='cuda:0');main(ap.parse_args())
