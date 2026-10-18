"""Approved fixed c1s2 pilot: two fresh RPROP arms, <=200 updates each.

Producer-only execution. No config/main import, history commit, FEM solve or
trajectory continuation. A fresh output directory and an immutable recipe are
mandatory. Run under the package's external <1-hour watchdog as well.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'SENS_tensile')]
from network import NeuralNet
from field_computation import FieldComputation
from material_properties import MaterialProperties
from pff_model import PFFModel
from compute_energy import compute_energy
from fatigue_history import compute_fatigue_degrad
from physical_symmetry import physical_symmetry_terms
from q4_quadrature import q4_shape_data,q4_gradient,q4_interpolate


class BudgetStop(Exception):pass


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def dump(path,data):
    temp=Path(str(path)+'.tmp')
    temp.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n');temp.replace(path)


def probes(device):
    points=[];weights=[]
    for xb,yb,nx,ny in [((-.49,.49),(0,.49),81,40),((0,.5),(0,.04),151,40)]:
        x=np.linspace(*xb,nx+1);y=np.linspace(*yb,ny+1)
        x,y=np.meshgrid((x[:-1]+x[1:])/2,(y[:-1]+y[1:])/2)
        points.append(np.column_stack((x.ravel(),y.ravel())))
        weights.append(np.full(nx*ny,.5/(nx*ny)))
    return (torch.tensor(np.concatenate(points),device=device,dtype=torch.float32),
            torch.tensor(np.concatenate(weights),device=device,dtype=torch.float32))


def make_field(state,device):
    net=NeuralNet(2,3,8,400,'TrainableReLU',1.).to(device);net.load_state_dict(state)
    return FieldComputation(net,torch.tensor([[-.5,.5],[-.5,.5]],device=device),
       torch.tensor([.05999988],device=device),torch.tensor([math.pi/2],device=device),
       alpha_constraint='nonsmooth',symmetry_prior=False,exact_bc_dict={'enable':False},
       williams_dict={'enable':False},ansatz_dict={'enable':False},local_patch_dict={'enable':False})


def norm(grads):
    return math.sqrt(sum(float(g.detach().double().square().sum()) for g in grads if g is not None))


def main(args):
    if not torch.cuda.is_available() or os.environ.get('CUDA_VISIBLE_DEVICES') is None:
        raise RuntimeError('producer-only CUDA execution with an explicit GPU required')
    recipe=json.loads(args.recipe.read_text());out=args.out;out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();torch.set_num_threads(1);torch.manual_seed(1)
    device=torch.device('cuda:0');torch.cuda.set_device(device)
    for item in recipe['inputs']:
        p=Path(item['path']);assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],str(p)
    for rel,digest in recipe['code_files'].items():assert sha(ROOT/rel)==digest,rel
    assert recipe['updates_per_arm']==200 and recipe['total_gpu_seconds_cap']==3600
    mesh=np.load(recipe['mesh']);x=torch.as_tensor(mesh['node_coords'],device=device,dtype=torch.float32)
    cells=torch.as_tensor(mesh['connectivity'],device=device,dtype=torch.long)
    assert x.shape==(86756,2) and cells.shape==(86408,4)
    state=torch.load(recipe['network'],map_location='cpu',weights_only=True)
    checkpoint=torch.load(recipe['history'],map_location=device,weights_only=False)
    assert checkpoint['history_storage']=='q4_gp4' and checkpoint['damage_history_storage']=='previous_accepted_nodal'
    assert checkpoint['mesh_connectivity_arity']==4 and checkpoint['history_driver_mode']=='current_active'
    hist=checkpoint['hist_alpha'].detach().clone();fat=checkpoint['hist_fat'].detach().clone()
    assert hist.shape==(86756,) and fat.shape==(86408,4)
    frozen_hist=hist.clone();frozen_fat=fat.clone()
    ff=compute_fatigue_degrad(fat,{'degrad_type':'asymptotic','alpha_T':.5}).detach()
    N,B,w=q4_shape_data(x,cells);area=w.sum(1)
    mat=MaterialProperties(1.,.3,1.,.01);model=PFFModel('AT1','volumetric',.005,residual_stiffness=0.)
    assert model.irrPenalty()==16875
    support,pair_weights=probes(device)
    penalty_cfg={'enable':True,'mode':'fem_gp_q4','spatial_integration':'native_q4_gp4'}
    np.savez_compressed(out/'fixed_inputs.npz',node_coords=x.cpu().numpy(),connectivity=cells.cpu().numpy(),
                        hist_alpha=hist.cpu().numpy(),hist_fat=fat.cpu().numpy(),f=ff.cpu().numpy())
    dump(out/'receipt.json',dict(protocol='S04-E011-PHYSICAL-PARITY-PILOT-r1',recipe_sha256=sha(args.recipe),
      commit=recipe['commit'],pid=os.getpid(),host=os.uname().nodename,gpu=os.environ['CUDA_VISIBLE_DEVICES'],
      started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),command=sys.argv,optimizer='fresh Rprop in both arms',
      history_updates=0,FEM_solves=0,updates_per_arm=200,total_gpu_seconds_cap=3600))
    def budget(arm_start=None):
        torch.cuda.synchronize()
        if time.monotonic()-started>=3500 or (arm_start and time.monotonic()-arm_start>=1800):raise BudgetStop()
    def parts(field):
        u,v,d=field.fieldCalculation(x)
        energies=compute_energy(x,u,v,d,hist,mat,model,area,cells,f_fatigue=ff,irreversibility_penalty_cfg=penalty_cfg)
        total=sum(energies)
        if not bool(torch.isfinite(total)) or float(total.detach())<=0:raise RuntimeError('invalid original energy domain')
        return u,v,d,energies,torch.log10(total)
    def physical_penalty(field):
        z=physical_symmetry_terms(field,support,pair_weights,.12)
        return z['u']+z['v']
    initial=make_field(state,device);params=list(initial.net.parameters())
    budget();*_,jphys=parts(initial)
    ng=norm(torch.autograd.grad(jphys,params,allow_unused=True));del jphys
    budget();ps=physical_penalty(initial);npgrad=norm(torch.autograd.grad(ps,params,allow_unused=True));del ps
    if not (math.isfinite(ng) and math.isfinite(npgrad) and ng>0 and npgrad>0):raise RuntimeError('uncalibratable frozen gradients')
    lam=.01*ng/npgrad
    dump(out/'calibration.json',dict(physical_log_gradient_l2=ng,parity_uv_gradient_l2=npgrad,lambda0=lam,
        lambda_alpha=0,displacement_scale=.12,seeds=len(support),paired_evaluations=2*len(support),
        rule='one percent initial log-physical gradient L2; frozen across both arms; no weight decay in numerator'))
    del initial,params
    def readout(field,folder,meta,arm_start=None):
        budget(arm_start)
        with torch.no_grad():u,v,d,ee,jp=parts(field)
        gu,gv=q4_gradient(u,cells,B),q4_gradient(v,cells,B)
        ex,ey,gamma=gu[:,:,0],gv[:,:,1],gu[:,:,1]+gv[:,:,0]
        raw=.5*(1/(3*.4))*torch.relu(ex+ey).square()+(1/(2*1.3))*((2/3)*(ex.square()+ey.square()-ex*ey)+.5*gamma.square())
        dg=q4_interpolate(d,cells,N);g=(1-dg).square();active=g*raw
        uu=u.detach().clone().requires_grad_(True);vv=v.detach().clone().requires_grad_(True)
        force=torch.autograd.grad(compute_energy(x,uu,vv,d.detach(),hist,mat,model,area,cells,f_fatigue=ff,irreversibility_penalty_cfg=penalty_cfg)[0],(uu,vv))
        free=(x[:,1]>-.5+1e-7)&(x[:,1]<.5-1e-7)
        meta.update(E_el=float(ee[0]),E_d=float(ee[1]),E_hist=float(ee[2]),log_physical=float(jp),
          d_min=float(d.min()),d_max=float(d.max()),nodal_healing_max=float(torch.relu(hist-d).max()),
          free_u_l2=float(torch.linalg.vector_norm(torch.cat((force[0][free],force[1][free])))),
          elapsed_total_seconds=time.monotonic()-started)
        np.savez_compressed(folder/'fields.npz',u=u.cpu().numpy(),v=v.cpu().numpy(),d=d.cpu().numpy(),
           raw_gp=raw.detach().cpu().numpy(),g_gp=g.detach().cpu().numpy(),active_gp=active.detach().cpu().numpy())
        dump(folder/'result.json',meta);torch.save(field.net.state_dict(),folder/'network.pt')
    originals=out/'original';originals.mkdir();readout(make_field(state,device),originals,dict(role='unchanged accepted theta0'))
    summary=[]
    for arm in ['control','physical_uv']:
        budget();arm_start=time.monotonic();folder=out/arm;folder.mkdir()
        field=make_field(state,device);params=list(field.net.parameters())
        opt=torch.optim.Rprop(params,lr=1e-5,etas=(.5,1.2),step_sizes=(1e-10,50))
        trace=[];updates=0;reason='200_updates';previous=None
        try:
            for k in range(200):
                budget(arm_start);opt.zero_grad(set_to_none=True)
                *_,ee,jp=parts(field)
                reg=sum(p.square().sum() for name,p in field.net.named_parameters() if 'weight' in name)
                penalty=physical_penalty(field) if arm=='physical_uv' else jp.new_zeros(())
                loss=jp+1e-5*reg+(lam*penalty if arm=='physical_uv' else 0)
                if not bool(torch.isfinite(loss)):raise RuntimeError('nonfinite objective')
                loss.backward()
                if any(p.grad is not None and not bool(torch.isfinite(p.grad).all()) for p in params):raise RuntimeError('nonfinite gradient')
                previous=[p.detach().clone() for p in params]
                trace.append(dict(before_update=k,objective=float(loss.detach()),physical_log=float(jp.detach()),
                    energies=[float(t.detach()) for t in ee],parity_uv=float(penalty.detach()),lambda0=lam if arm=='physical_uv' else 0))
                opt.step();updates+=1
                if updates%20==0:print(json.dumps(dict(arm=arm,updates=updates,loss=trace[-1]['objective'],seconds=time.monotonic()-started)),flush=True)
            meta=dict(arm=arm,updates=updates,stop=reason,elapsed_arm_seconds=time.monotonic()-arm_start)
            readout(field,folder,meta,arm_start);summary.append(meta)
        except BudgetStop:
            reason='time_budget';dump(folder/'partial.json',dict(arm=arm,updates=updates,stop=reason));raise
        except Exception:
            if previous is not None:
                with torch.no_grad():
                    for p,q in zip(params,previous):p.copy_(q)
            torch.save(field.net.state_dict(),folder/'restored_last_preupdate_network.pt')
            dump(folder/'failure.json',dict(arm=arm,attempted_updates=updates,last_preupdate_saved=True));raise
        finally:dump(folder/'trace.json',trace)
        assert torch.equal(hist,frozen_hist) and torch.equal(fat,frozen_fat)
        del field,params,opt
    torch.cuda.synchronize()
    dump(out/'complete.json',dict(status='completed',arms=summary,total_updates=sum(a['updates'] for a in summary),
        elapsed_seconds=time.monotonic()-started,history_updates=0,FEM_solves=0,lambda0=lam,
        peak_allocated_bytes=torch.cuda.max_memory_allocated()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--recipe',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    try:main(a)
    except BaseException as exc:
        if a.out.is_dir():dump(a.out/'terminal_failure.json',dict(error=type(exc).__name__,message=str(exc),utc=dt.datetime.now(dt.timezone.utc).isoformat()))
        raise
