#!/usr/bin/env python3
"""One-step native-Q4 discriminator; budgets are trajectory prefixes."""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sys,time
from pathlib import Path
import numpy as np
import torch
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent/"source")]
from compute_energy import compute_energy_per_elem,get_psi_plus_per_elem,strain_energy_with_split
from fatigue_history import compute_fatigue_degrad
from field_computation import FieldComputation
from input_data_from_mesh import prep_input_data
from material_properties import MaterialProperties
from network import NeuralNet
from pff_model import PFFModel
from q4_quadrature import q4_gradient,q4_interpolate,q4_shape_data

METHODS=("joint_shared","joint_split","alternating_split")
MODES=("committed","trial")

def args():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ("mesh-file","checkpoint","network","out"): p.add_argument("--"+name,type=Path,required=True)
 p.add_argument("--peak-displacement",type=float,default=.11999988)
 p.add_argument("--budgets",default="600,1200,2400");p.add_argument("--refresh-interval",type=int,default=200)
 p.add_argument("--methods",default=",".join(METHODS));p.add_argument("--fatigue-modes",default=",".join(MODES))
 p.add_argument("--damage-map",choices=("legacy_nonsmooth","bounded_nonsmooth"),default="legacy_nonsmooth")
 p.add_argument("--seed",type=int,default=1);p.add_argument("--device",default="cuda")
 return p.parse_args()

def digest(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""): h.update(b)
 return h.hexdigest()

def fatigue_cfg(): return {"fatigue_on":True,"loading_type":"cyclic","accum_type":"carrara","degrad_type":"asymptotic","alpha_T":.5,"spatial_alpha_T":{"enable":False}}

def make_field(state,device,peak,damage_map):
 net=NeuralNet(2,3,8,400,"TrainableReLU",1.).to(device);net.load_state_dict(state)
 constraint="bounded_nonsmooth" if damage_map=="bounded_nonsmooth" else "nonsmooth"
 f=FieldComputation(net=net,domain_extrema=torch.tensor([[-.5,.5],[-.5,.5]],device=device),lmbda=torch.tensor([peak],device=device),theta=torch.tensor([math.pi/2],device=device),alpha_constraint=constraint,williams_dict={"enable":False},ansatz_dict={"enable":False},l0=.01,symmetry_prior=False,exact_bc_dict={"enable":False},local_patch_dict={"enable":False})
 f.net=f.net.to(device);return f

def energies(inp,cells,area,u,v,d,accepted,fatigue,mat,model):
 x=compute_energy_per_elem(inp,u,v,d,accepted,mat,model,area,cells,f_fatigue=fatigue,irreversibility_penalty_cfg={"enable":True,"mode":"fem_gp_q4"})
 return tuple(v.sum() for v in x)

def reg(*fields):
 z=torch.zeros((),device=next(fields[0].net.parameters()).device)
 for f in fields:
  for n,p in f.net.named_parameters():
   if "weight" in n:z=z+p.square().sum()
 return z

def mean_reg(*fields): return reg(*fields)/len(fields)

def strict_loss(parts,regularizer):
 total=sum(parts)
 if not torch.isfinite(total) or total<=0:
  raise RuntimeError(f"non-positive/non-finite total energy: {float(total.detach().cpu())}")
 return torch.log10(total)+1e-5*regularizer

def damage_energy_parts(inp,cells,d,fatigue,mat,model):
 shape,dshape,det=q4_shape_data(inp,cells);dgp=q4_interpolate(d,cells,shape);gd=q4_gradient(d,cells,dshape)
 damage_fn,_,cw=model.damageFun(dgp)
 ff=fatigue if fatigue.ndim==2 else fatigue[:,None]
 local=(ff*(mat.w1/cw)*damage_fn*det).sum()
 gradient=(ff*(mat.w1/cw)*mat.l0**2*gd.square().sum(dim=2)*det).sum()
 return local,gradient,dgp

def weak_residuals(inp,cells,area,u,v,d,accepted,fatigue,mat,model):
 uu=u.detach().clone().requires_grad_(True);vv=v.detach().clone().requires_grad_(True);dd=d.detach().clone().requires_grad_(True)
 parts=energies(inp,cells,area,uu,vv,dd,accepted,fatigue,mat,model);total=sum(parts)
 gu,gv,gd=torch.autograd.grad(total,(uu,vv,dd))
 y=inp[:,1];free=(y>y.min()+1e-7)&(y<y.max()-1e-7)
 rms=lambda x: float(torch.sqrt(torch.mean(x.square())).detach().cpu())
 shape,_,_=q4_shape_data(inp,cells);dgp=q4_interpolate(dd,cells,shape);d0gp=q4_interpolate(accepted,cells,shape)
 return {"weak_uv_free_rms":rms(torch.cat((gu[free],gv[free]))),"weak_damage_rms":rms(gd),"irreversibility_gp_rms":rms(torch.relu(d0gp-dgp)),"irreversibility_gp_max":float(torch.relu(d0gp-dgp).max().detach().cpu())}

def sync(device):
 if device.type=="cuda":torch.cuda.synchronize(device)

def split_gradient_contract(uv,df,inp,cells,area,d0,f,mat,model):
 """Verify block losses are exact partial gradients of the joint split loss."""
 up=list(uv.parameters());dp=list(df.parameters())
 u,v,_=uv.fieldCalculation(inp);_,_,d=df.fieldCalculation(inp)
 joint=strict_loss(energies(inp,cells,area,u,v,d,d0,f,mat,model),mean_reg(uv,df))
 jgu=torch.autograd.grad(joint,up,retain_graph=True);jgd=torch.autograd.grad(joint,dp)
 u,v,_=uv.fieldCalculation(inp)
 with torch.no_grad():_,_,d=df.fieldCalculation(inp);d=d.detach();rd=reg(df).detach()
 uloss=strict_loss(energies(inp,cells,area,u,v,d,d0,f,mat,model),.5*(reg(uv)+rd))
 agu=torch.autograd.grad(uloss,up)
 with torch.no_grad():u,v,_=uv.fieldCalculation(inp);u,v=u.detach(),v.detach();ru=reg(uv).detach()
 _,_,d=df.fieldCalculation(inp)
 dloss=strict_loss(energies(inp,cells,area,u,v,d,d0,f,mat,model),.5*(ru+reg(df)))
 agd=torch.autograd.grad(dloss,dp)
 def err(a,b):
  absolute=max(float((x-y).abs().max().detach().cpu()) for x,y in zip(a,b))
  scale=max(max(float(x.abs().max().detach().cpu()) for x in a),1e-30)
  return absolute,absolute/scale
 ua,ur=err(jgu,agu);da,dr=err(jgd,agd)
 if max(ur,dr)>2e-5:raise RuntimeError(f"split gradient contract failed: uv={ur} damage={dr}")
 return {"uv_max_abs":ua,"uv_max_rel":ur,"damage_max_abs":da,"damage_max_rel":dr}

def step(opt,closure,n,trace):
 for i in range(n):
  opt.zero_grad(set_to_none=True);loss=closure()
  if not torch.isfinite(loss):raise RuntimeError(f"non-finite loss at local epoch {i}")
  loss.backward();opt.step();trace.append(float(loss.detach().cpu()))

@torch.no_grad()
def trial(inp,cells,area,u,v,d,h0,driver,mat,model,cfg):
 active=get_psi_plus_per_elem(inp,u,v,d,mat,model,area,cells,history_driver_reduction_dict={"enable":True,"mode":"native_q4_gp4"})
 h=h0+torch.relu(active-driver);return h.detach(),compute_fatigue_degrad(h,cfg).detach()

@torch.no_grad()
def fields(method,shared,uv,df,inp):
 if method=="joint_shared":return shared.fieldCalculation(inp)
 u,v,_=uv.fieldCalculation(inp);_,_,d=df.fieldCalculation(inp);return u,v,d

@torch.no_grad()
def export(inp,cells,u,v,d,h,f,mat,model):
 shape,dshape,det=q4_shape_data(inp,cells);gu=q4_gradient(u,cells,dshape);gv=q4_gradient(v,cells,dshape);dgp=q4_interpolate(d,cells,shape)
 exx,eyy=gu[:,:,0],gv[:,:,1];exy=.5*(gu[:,:,1]+gv[:,:,0]);_,raw=strain_energy_with_split(exx,eyy,exy,dgp,mat,model);g,_=model.Edegrade(dgp);active=g*raw
 cpu=lambda x,dtype: x.detach().cpu().numpy().astype(dtype)
 return {"u_node":cpu(u,np.float32),"v_node":cpu(v,np.float32),"damage_node":cpu(d,np.float32),"damage_gp":cpu(dgp,np.float32),"hist_fat_gp":cpu(h,np.float32),"f_fatigue_gp":cpu(f,np.float32),"psi_raw_gp":cpu(raw,np.float32),"g_gp":cpu(g,np.float32),"psi_active_gp":cpu(active,np.float32),"eps_xx_gp":cpu(exx,np.float32),"eps_yy_gp":cpu(eyy,np.float32),"engineering_shear_gamma_xy_gp":cpu(2*exy,np.float32),"det_j":cpu(det,np.float64)}

def trajectory(method,mode,budgets,interval,state,inp,cells,area,d0,h0,driver,f0,mat,model,cfg,peak,device,out,damage_map):
 shared=uv=df=None
 if method=="joint_shared":
  shared=make_field(state,device,peak,damage_map);opt=torch.optim.Rprop(shared.parameters(),lr=1e-5,step_sizes=(1e-10,50.))
 else:
  uv=make_field(state,device,peak,damage_map);df=make_field(state,device,peak,damage_map)
  if method=="joint_split":opt=torch.optim.Rprop(list(uv.parameters())+list(df.parameters()),lr=1e-5,step_sizes=(1e-10,50.))
  else:
   uopt=torch.optim.Rprop(uv.parameters(),lr=1e-5,step_sizes=(1e-10,50.));dopt=torch.optim.Rprop(df.parameters(),lr=1e-5,step_sizes=(1e-10,50.))
 h,f=h0.detach(),f0.detach();u,v,d=fields(method,shared,uv,df,inp)
 if mode=="trial":h,f=trial(inp,cells,area,u,v,d,h0,driver,mat,model,cfg)
 grad_contract=None if method=="joint_shared" else split_gradient_contract(uv,df,inp,cells,area,d0,f,mat,model)
 accepted_clones=(d0.clone(),h0.clone(),driver.clone(),f0.clone())
 total=0;trace=[];refresh=[];rows=[];outer_rounds=0;optimizer_calls=0;f_refreshes=0
 sync(device);started=time.perf_counter()
 while total<budgets[-1]:
  block=min(interval,budgets[-1]-total)
  h_solve,f_solve=h,f
  if method=="joint_shared":
   def closure():
    cu,cv,cd=shared.fieldCalculation(inp);ee,ed,eh=energies(inp,cells,area,cu,cv,cd,d0,f,mat,model)
    return strict_loss((ee,ed,eh),mean_reg(shared))
   step(opt,closure,block,trace)
  elif method=="joint_split":
   def closure():
    cu,cv,_=uv.fieldCalculation(inp);_,_,cd=df.fieldCalculation(inp);ee,ed,eh=energies(inp,cells,area,cu,cv,cd,d0,f,mat,model)
    return strict_loss((ee,ed,eh),mean_reg(uv,df))
   step(opt,closure,block,trace)
  else:
   nu=nd=block
   with torch.no_grad():_,_,fd=df.fieldCalculation(inp);fd=fd.detach();frozen_d_before=fd.clone()
   def uclosure():
    cu,cv,_=uv.fieldCalculation(inp);ee,ed,eh=energies(inp,cells,area,cu,cv,fd,d0,f,mat,model)
    frozen_reg=reg(df).detach()
    return strict_loss((ee,ed,eh),.5*(reg(uv)+frozen_reg))
   step(uopt,uclosure,nu,trace)
   with torch.no_grad():
    _,_,frozen_d_after=df.fieldCalculation(inp);freeze_d_err=float((frozen_d_after-frozen_d_before).abs().max().cpu())
    if freeze_d_err!=0.:raise RuntimeError(f"damage field changed during UV block: {freeze_d_err}")
    fu,fv,_=uv.fieldCalculation(inp);fu,fv=fu.detach(),fv.detach();frozen_u_before=fu.clone();frozen_v_before=fv.clone()
   def dclosure():
    _,_,cd=df.fieldCalculation(inp);ee,ed,eh=energies(inp,cells,area,fu,fv,cd,d0,f,mat,model)
    frozen_reg=reg(uv).detach()
    return strict_loss((ee,ed,eh),.5*(frozen_reg+reg(df)))
   step(dopt,dclosure,nd,trace)
   with torch.no_grad():
    frozen_u_after,frozen_v_after,_=uv.fieldCalculation(inp);freeze_uv_err=max(float((frozen_u_after-frozen_u_before).abs().max().cpu()),float((frozen_v_after-frozen_v_before).abs().max().cpu()))
    if freeze_uv_err!=0.:raise RuntimeError(f"UV field changed during damage block: {freeze_uv_err}")
  optimizer_calls+=block if method!="alternating_split" else 2*block
  total+=block;outer_rounds+=1;u,v,d=fields(method,shared,uv,df,inp)
  used_parts=energies(inp,cells,area,u,v,d,d0,f_solve,mat,model)
  if mode=="trial":h,f=trial(inp,cells,area,u,v,d,h0,driver,mat,model,cfg);f_refreshes+=1
  else:h,f=h0,f0
  candidate_parts=energies(inp,cells,area,u,v,d,d0,f,mat,model)
  f_gap=float((torch.linalg.vector_norm(f-f_solve)/torch.linalg.vector_norm(f_solve).clamp(min=1e-30)).cpu())
  local_used,grad_used,dgp=damage_energy_parts(inp,cells,d,f_solve,mat,model)
  local_candidate,grad_candidate,_=damage_energy_parts(inp,cells,d,f,mat,model)
  used_res=weak_residuals(inp,cells,area,u,v,d,d0,f_solve,mat,model);candidate_res=weak_residuals(inp,cells,area,u,v,d,d0,f,mat,model)
  for original,clone,label in zip((d0,h0,driver,f0),accepted_clones,("damage_lower_bound","history","previous_driver","committed_f")):
   if not torch.equal(original,clone):raise RuntimeError(f"accepted state mutated: {label}")
  sync(device);elapsed=time.perf_counter()-started
  used=[float(x.detach().cpu()) for x in used_parts];candidate=[float(x.detach().cpu()) for x in candidate_parts]
  refresh.append({"updates_per_field":total,"optimizer_calls":optimizer_calls,"outer_rounds":outer_rounds,"f_refreshes":f_refreshes,"E_used":used,"E_candidate":candidate,"f_min_used":float(f_solve.min().cpu()),"f_min_candidate":float(f.min().cpu()),"hist_max_candidate":float(h.max().cpu()),"trial_f_fixed_point_rel_gap":f_gap,"gpu_wall_seconds":elapsed})
  if total in budgets:
   if damage_map=="bounded_nonsmooth":
    if bool((d<0).any()) or bool((d>1).any()) or bool((dgp<0).any()) or bool((dgp>1).any()):
     raise RuntimeError("bounded damage-map contract violated at node or Q4 GP")
   data=export(inp,cells,u,v,d,h,f,mat,model);data["hist_solve_gp"]=h_solve.detach().cpu().numpy().astype(np.float32);data["hist_candidate_gp"]=h.detach().cpu().numpy().astype(np.float32);data["f_solve_gp"]=f_solve.detach().cpu().numpy().astype(np.float32);data["f_candidate_gp"]=f.detach().cpu().numpy().astype(np.float32);data["loss_trace"]=np.asarray(trace,np.float64);tag=f"{mode}_{method}_B{total}";np.savez_compressed(out/f"{tag}.npz",**data)
   s={"method":method,"fatigue_mode":mode,"budget_per_field":total,"optimizer_calls":optimizer_calls,"outer_rounds":outer_rounds,"f_refreshes":f_refreshes,"loss_first":trace[0],"loss_last":trace[-1],"E_el_used":used[0],"E_d_used":used[1],"E_hist_used":used[2],"E_el_candidate":candidate[0],"E_d_candidate":candidate[1],"E_hist_candidate":candidate[2],"E_d_local_used":float(local_used.detach().cpu()),"E_d_gradient_used":float(grad_used.detach().cpu()),"E_d_local_candidate":float(local_candidate.detach().cpu()),"E_d_gradient_candidate":float(grad_candidate.detach().cpu()),"f_min_used":float(f_solve.min().cpu()),"f_min_candidate":float(f.min().cpu()),"hist_max_candidate":float(h.max().cpu()),"trial_f_fixed_point_rel_gap":f_gap,"damage_node_min":float(d.min().cpu()),"damage_node_max":float(d.max().cpu()),"damage_node_negative_fraction":float((d<0).float().mean().cpu()),"damage_node_above_one_fraction":float((d>1).float().mean().cpu()),"damage_gp_min":float(dgp.min().cpu()),"damage_gp_max":float(dgp.max().cpu()),"damage_gp_negative_fraction":float((dgp<0).float().mean().cpu()),"damage_gp_above_one_fraction":float((dgp>1).float().mean().cpu()),"active_integral":float(np.sum(data["det_j"]*data["psi_active_gp"])),"gpu_wall_seconds":elapsed,"split_gradient_contract":grad_contract,"fixed_point_label":"COMMITTED_FIXED" if mode=="committed" else "BUDGET_EXHAUSTED_NOT_FIXED_POINT_UNLESS_RESIDUALS_PASS",**{f"used_{k}":v for k,v in used_res.items()},**{f"candidate_{k}":v for k,v in candidate_res.items()},"refresh_trace":list(refresh)}
   (out/f"{tag}.json").write_text(json.dumps(s,indent=2)+"\n");rows.append({k:v for k,v in s.items() if k!="refresh_trace"});print(f"[Matrix] snapshot {tag}: {rows[-1]}",flush=True)
 return rows

def main():
 a=args();torch.manual_seed(a.seed);np.random.seed(a.seed);device=torch.device(a.device)
 if device.type=="cuda" and not torch.cuda.is_available():raise RuntimeError("CUDA requested but unavailable")
 budgets=[int(x) for x in a.budgets.split(",") if x.strip()]
 if not budgets or budgets!=sorted(set(budgets)) or budgets[0]<=0 or a.refresh_interval<=0 or any(x%a.refresh_interval for x in budgets):raise ValueError("budgets must be unique positive ascending multiples of refresh-interval")
 methods=[x.strip() for x in a.methods.split(",") if x.strip()];modes=[x.strip() for x in a.fatigue_modes.split(",") if x.strip()]
 if len(set(methods))!=len(methods) or not methods or any(x not in METHODS for x in methods):raise ValueError(f"methods must be unique members of {METHODS}")
 if len(set(modes))!=len(modes) or not modes or any(x not in MODES for x in modes):raise ValueError(f"fatigue modes must be unique members of {MODES}")
 if a.checkpoint.name!="checkpoint_step_412.pt" or a.network.name!="trained_1NN_412.pt":raise ValueError("target step 413 must start from exact accepted step-412 checkpoint and network")
 a.out.mkdir(parents=True,exist_ok=False);mat=MaterialProperties(1.,.3,1.,.01);model=PFFModel("AT1","volumetric",5e-3,residual_stiffness=0.)
 numr={"alpha_constraint":"nonsmooth","gradient_type":"numerical","irreversibility_penalty":{"enable":True,"mode":"fem_gp_q4"}};crack={"x_init":[-.5],"y_init":[0.],"L_crack":[.5],"angle_crack":[0.]}
 inp,cells,area,_=prep_input_data(mat,model,crack,numr,mesh_file=str(a.mesh_file),device=device)
 if cells.ndim!=2 or cells.shape[1]!=4:raise ValueError(f"expected native Q4 connectivity, got {tuple(cells.shape)}")
 ck=torch.load(a.checkpoint,map_location=device,weights_only=False);d0_raw=ck["hist_alpha"].to(device).detach();d0=d0_raw.clamp(0.,1.) if a.damage_map=="bounded_nonsmooth" else d0_raw;h0=ck["hist_fat"].to(device).detach();driver=ck["psi_plus_prev"].to(device).detach()
 if h0.shape!=(len(cells),4):raise ValueError(f"unexpected hist_fat shape {tuple(h0.shape)}")
 state={k:v.to(device) for k,v in torch.load(a.network,map_location=device,weights_only=True).items()};cfg=fatigue_cfg();f0=compute_fatigue_degrad(h0,cfg).detach();rows=[]
 legacy0=make_field(state,device,a.peak_displacement,"legacy_nonsmooth");active0=make_field(state,device,a.peak_displacement,a.damage_map)
 with torch.no_grad():
  _,_,legacy_d=legacy0.fieldCalculation(inp);_,_,active_d=active0.fieldCalculation(inp)
  expected=legacy_d.clamp(0.,1.) if a.damage_map=="bounded_nonsmooth" else legacy_d
  map_error=float((active_d-expected).abs().max().cpu())
  if map_error!=0.:raise RuntimeError(f"damage-map projection contract failed: {map_error}")
  b0={"damage_map":a.damage_map,"network_map_vs_declared_projection_max_abs":map_error,"legacy_network_damage_min":float(legacy_d.min().cpu()),"legacy_network_damage_max":float(legacy_d.max().cpu()),"active_network_damage_min":float(active_d.min().cpu()),"active_network_damage_max":float(active_d.max().cpu()),"accepted_damage_projection_max_abs":float((d0-d0_raw).abs().max().cpu()),"accepted_damage_negative_fraction_before":float((d0_raw<0).float().mean().cpu()),"accepted_damage_above_one_fraction_before":float((d0_raw>1).float().mean().cpu()),"accepted_history_unchanged":True,"accepted_previous_driver_unchanged":True}
 (a.out/"b0_contract.json").write_text(json.dumps(b0,indent=2)+"\n")
 for method in methods:
  for mode in modes:
   print(f"[Matrix] start {mode}_{method}; budgets={budgets}",flush=True);rows+=trajectory(method,mode,budgets,a.refresh_interval,state,inp,cells,area,d0,h0,driver,f0,mat,model,cfg,a.peak_displacement,device,a.out,a.damage_map)
 with (a.out/"matrix_summary.csv").open("w",newline="") as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 damage_semantics=("bounded_nonsmooth = clamp of the legacy central affine map to [0,1]; accepted hist_alpha is projected once to [0,1]; hist_fat and previous driver remain byte-identical to the same legacy step-412 checkpoint; this is a one-step projected-state counterfactual, not a fully retrained bounded history" if a.damage_map=="bounded_nonsmooth" else "legacy NonsmoothSigmoid retained in all arms; no clipping; node/GP violations and fracture local/gradient energy terms recorded")
 manifest={"schema":"hard5-native-q4-one-step-matrix-v4","source_state":"PIDL step 412 post-fit/post-history-commit accepted state (true pre-step state for target step 413)","target_state":"PIDL step 413 = c83 peak displacement 0.11999988","methods":methods,"fatigue_modes":modes,"budgets":budgets,"budget_unit":"optimizer updates per active field block","budget_rule":"each budget is a prefix of one persistent optimizer trajectory; at equal B joint updates both field blocks B times while alternating performs B UV plus B damage calls","refresh_interval_per_field":a.refresh_interval,"outer_refresh_rule":"one f refresh after each interval updates per field; therefore joint and alternating have equal per-field updates and equal refresh counts, but different optimizer-call counts and wall time","trial_rule":"hist_candidate=hist_accepted+relu(active(current target-load fields)-driver_accepted); rebuilt from frozen accepted state; f detached; f_solve and f_candidate stored separately","regularization":"shared: 1e-5 R; split: 1e-5*0.5*(R_uv+R_d), preserving equality at copied initialization; joint_split and alternating_split share this exact objective","optimizer":"fresh torch Rprop in every arm; lr=1e-5, default etas=(0.5,1.2), step_sizes=(1e-10,50); state persistent within an arm","bridge_rule":"joint_shared vs joint_split is parameterisation bridge only; joint_split vs alternating_split is finite-budget simultaneous-vs-block update under common split parameterisation","alternating_rule":"independent UV/damage networks; exact frozen counterpart fields; same full loss; persistent separate optimizers; runtime gradient-equivalence and frozen-field assertions","damage_map":a.damage_map,"damage_semantics":damage_semantics,"operator":"native Q4 2x2 GP, q4_gp4 history, fem_gp_q4 irreversibility, eta=0, current_active","inputs":{"mesh":str(a.mesh_file),"mesh_sha256":digest(a.mesh_file),"checkpoint":str(a.checkpoint),"checkpoint_sha256":digest(a.checkpoint),"network":str(a.network),"network_sha256":digest(a.network)}}
 (a.out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n");print(json.dumps(manifest,indent=2),flush=True)
if __name__=="__main__":main()
