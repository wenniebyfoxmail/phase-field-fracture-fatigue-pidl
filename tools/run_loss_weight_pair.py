"""Frozen W0/W25 single-block producer run, with no-step GPU admission.

C construction/readouts derived from run_precrack_alignment.py at a0794cb4.
No loaded FEM target is accepted by this program. No history refresh exists.
"""
import argparse
import datetime as dt
import importlib
import inspect
import json
import math
import os
from pathlib import Path
import socket
import sys
import time
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'SENS_tensile'),str(ROOT/'tools')]
from run_physical_symmetry_pilot import dump,BudgetStop
from network import NeuralNet
from field_computation import FieldComputation
from nodal_damage_alignment import NodalDamageAlignment
from material_properties import MaterialProperties
from pff_model import PFFModel
from compute_energy import compute_energy
from q4_quadrature import q4_shape_data,q4_gradient,q4_interpolate
from loss_weight_diagnostics import gradient_probe,sign_stats,rprop_state_summary,GradientDecompositionError


def make_field(state,device,adapter=None,load=.02999988):
    net=NeuralNet(2,3,8,400,'TrainableReLU',1.).to(device)
    net.load_state_dict(state);net.eval()
    return FieldComputation(net,torch.tensor([[-.5,.5],[-.5,.5]],device=device),
        torch.tensor([load],device=device),torch.tensor([math.pi/2],device=device),
        alpha_constraint='nonsmooth',symmetry_prior=False,exact_bc_dict={'enable':False},
        williams_dict={'enable':False},ansatz_dict={'enable':False},local_patch_dict={'enable':False},
        nodal_damage_alignment=adapter)


def main(a):
    started=time.monotonic()
    if not torch.cuda.is_available() or os.environ.get('CUDA_VISIBLE_DEVICES') is None:
        raise RuntimeError('explicit producer GPU required; never train on Mac')
    r=json.loads(a.recipe.read_text())
    assert r['protocol']=='loss-weight-gamma-execution-r3-20261018'
    assert r['arms']==['W0','W25'] and r['betas']==[1,25]
    assert r['updates_per_arm']==200 and r['total_gpu_seconds_cap']==3600
    assert r['weight_decay']==1e-5 and r['symmetry_weight']==r['FEM_supervision']==0
    assert r['load']==.02999988 and r['torch_version']==torch.__version__
    assert r['GPU']==os.environ['CUDA_VISIBLE_DEVICES']
    assert r['GPU_memory_cap_GiB']==22 and r['per_arm_seconds_cap']==1800
    for q in r['inputs']:assert Path(q['path']).stat().st_size==q['bytes'],q
    provenance=json.loads((ROOT/'RUN_PROVENANCE.json').read_text())
    assert provenance['commit']==r['commit'] and provenance['dirty']==False
    a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1);torch.manual_seed(1)
    device=torch.device('cuda:0');torch.cuda.set_device(device)
    torch.cuda.set_per_process_memory_fraction(22*1024**3/torch.cuda.get_device_properties(0).total_memory)
    def budget(arm_start=None):
        torch.cuda.synchronize()
        if time.monotonic()-started>=3500:raise BudgetStop('global3500s internal cap')
        if arm_start and time.monotonic()-arm_start>=1800:raise BudgetStop('per-arm1800s cap')
    dump(a.out/'receipt.json',dict(protocol=r['protocol'],run_id=r['run_id'],commit=r['commit'],
        pid=os.getpid(),host=socket.gethostname(),gpu=r['GPU'],torch=torch.__version__,
        command=sys.argv,started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        history_commits=0,FEM_solves=0,total_gpu_seconds_cap=3600,per_arm_seconds_cap=1800,
        GPU_memory_cap_GiB=22,updates_per_arm=200,symmetry_weight=0,FEM_supervision=0))
    implementation=inspect.getsource(importlib.import_module('torch.optim.rprop')._single_tensor_rprop)
    (a.out/'Rprop_implementation.txt').write_text(implementation)
    z=np.load(r['initial_inputs']);x=torch.tensor(z['node_coords'],device=device)
    cells=torch.tensor(z['connectivity'],device=device,dtype=torch.long)
    d0=torch.tensor(z['FEM_initial_damage'],device=device)
    mask=torch.tensor(z['crack_mask'],device=device)
    assert x.shape==(86756,2) and cells.shape==(86408,4) and x.dtype==torch.float32
    assert int(mask.sum())==251 and d0.dtype==torch.float32
    state=torch.load(r['network'],map_location='cpu',weights_only=True)
    ck=torch.load(r['history'],map_location=device,weights_only=False)
    assert ck['history_storage']=='q4_gp4' and ck['damage_history_storage']=='previous_accepted_nodal'
    assert ck['mesh_connectivity_arity']==4 and ck['history_driver_mode']=='current_active'
    assert not ck.get('lagged_stiffness',False)
    for key in ('hist_fat','psi_plus_prev','psi_history_elem'):
        assert int(torch.count_nonzero(ck[key]))==0,key
    assert ck['hist_fat'].shape==(86408,4) and ck['hist_alpha'].shape==(86756,)
    assert np.array_equal(ck['hist_alpha'].cpu().numpy(),z['PIDL_U0_history'])
    frozen_history={k:ck[k].clone() for k in ('hist_alpha','hist_fat','psi_plus_prev','psi_history_elem')}
    N,B,w=q4_shape_data(x,cells);area=w.sum(1)
    mat=MaterialProperties(1.,.3,1.,.01);model=PFFModel('AT1','volumetric',.005,residual_stiffness=0.)
    assert model.irrPenalty()==16875
    pcfg={'enable':True,'mode':'fem_gp_q4','spatial_integration':'native_q4_gp4'}
    origin=make_field(state,device);capture=[]
    handle=origin.net.register_forward_hook(lambda m,i,o:capture.append(o[:,2].detach().clone()))
    with torch.no_grad():origin_uvd=origin.fieldCalculation(x)
    handle.remove();assert len(capture)==1
    rawref=capture[0].clone()
    def new_adapter():return NodalDamageAlignment(x,mode='fem_initial',initial_damage=d0,
        raw_reference=rawref,expected_crack_mask=mask)
    adapter=new_adapter();frozen_buffers={k:v.clone() for k,v in adapter.named_buffers()}
    hist=adapter.initial_history(ck['hist_alpha']);hist_frozen=hist.clone()
    assert torch.equal(hist,d0)
    def evaluate(field):
        u,v,d=field.fieldCalculation(x)
        if not all(bool(torch.isfinite(q).all()) for q in (u,v,d)):raise RuntimeError('nonfinite field')
        if not bool((d[mask]==1).all()):raise RuntimeError('hard crack line violation')
        ee=compute_energy(x,u,v,d,hist,mat,model,area,cells,f_fatigue=1.,irreversibility_penalty_cfg=pcfg)
        if any(not bool(torch.isfinite(q)) for q in ee):raise RuntimeError('nonfinite energy part')
        if any(float((ee[0]+ee[1]+beta*ee[2]).detach())<=0 for beta in (1,25)):
            raise RuntimeError('nonpositive log domain')
        return u,v,d,ee
    def regularizer(field):return sum(p.square().sum() for n,p in field.net.named_parameters() if 'weight' in n)
    def optimizer(params):return torch.optim.Rprop(params,lr=1e-5,etas=(.5,1.2),step_sizes=(1e-10,50),
        foreach=False,maximize=False,capturable=False,differentiable=False)
    def invariant(field):
        assert torch.equal(hist,hist_frozen)
        for k,v in frozen_history.items():assert torch.equal(ck[k],v)
        for k,v in field.nodal_damage_alignment.named_buffers():assert torch.equal(v,frozen_buffers[k])
    def probe(field,path,arm_start=None):
        budget(arm_start);*_,ee=evaluate(field)
        try:info,vectors=gradient_probe(ee,regularizer(field),list(field.net.parameters()))
        except GradientDecompositionError as exc:
            index=exc.diagnostics['largest_difference_flat_index'];offset=0
            for name,p in field.net.named_parameters():
                if offset<=index<offset+p.numel():
                    exc.diagnostics['largest_difference_parameter']=name
                    exc.diagnostics['parameter_local_flat_index']=index-offset
                    exc.diagnostics['parameter_shape']=list(p.shape)
                    break
                offset+=p.numel()
            dump(path.with_suffix('.failure.json'),exc.diagnostics)
            torch.save({k:v.cpu() for k,v in exc.vectors.items()},path.with_suffix('.failure.pt'))
            raise
        dump(path,info)
        budget(arm_start)
        return info,vectors
    # No optimizer step is called until ALL admission checks have passed.
    check=make_field(state,device,adapter)
    with torch.no_grad():uvd=evaluate(check)[:3]
    assert torch.equal(uvd[2],d0) and torch.equal(uvd[0],origin_uvd[0]) and torch.equal(uvd[1],origin_uvd[1])
    torch.save({'network':check.net.state_dict(),'mapper':adapter.state_dict()},a.out/'initial_bundle.pt')
    loaded=torch.load(a.out/'initial_bundle.pt',map_location=device,weights_only=False)
    restored_adapter=new_adapter();restored_adapter.load_state_dict(loaded['mapper'])
    restored=make_field(loaded['network'],device,restored_adapter)
    with torch.no_grad():uvd2=evaluate(restored)[:3]
    assert all(torch.equal(v1,v2) for v1,v2 in zip(uvd,uvd2));invariant(restored)
    pre,vectors=probe(check,a.out/'preflight_origin_gradients.json')
    assert pre['energies'][2]==0 and pre['zero_Eh_parameter_gradient']
    assert pre['same_snapshot_beta_signs']['bitwise_equal']
    assert optimizer(list(check.net.parameters())).state_dict()==optimizer(list(restored.net.parameters())).state_dict()
    torch.save({b:g.cpu() for b,g in vectors.items()},a.out/'preflight_origin_gradients.pt')
    # Reversible prescribed parameter perturbation, never an optimization update.
    before_state={k:v.detach().clone() for k,v in check.net.state_dict().items()}
    with torch.no_grad():check.net.output_layer.bias[2]-=1e-3
    pert,_=probe(check,a.out/'preflight_perturbed_gradients.json')
    assert pert['energies'][2]>0 and not pert['zero_Eh_parameter_gradient']
    check.net.load_state_dict(before_state)
    assert all(torch.equal(v,before_state[k]) for k,v in check.net.state_dict().items())
    with torch.no_grad():uvd3=evaluate(check)[:3]
    assert all(torch.equal(v1,v2) for v1,v2 in zip(uvd,uvd3));invariant(check)
    dump(a.out/'preflight_complete.json',dict(status='passed_no_optimizer_step',optimizer_updates=0,
        initial_fullNN_gradients_bitwise_equal=True,initial_Eh=0,initial_Eh_gradient_zero=True,
        serialize_reload_bitwise_equal=True,perturbation='output_layer.bias[2]-=1e-3',
        perturbed_Eh=pert['energies'][2],network_and_buffers_restored=True,
        elapsed_seconds=time.monotonic()-started,torch=torch.__version__,Rprop='single_tensor foreachFalse'))
    if a.preflight_only:
        dump(a.out/'preflight_only_terminal.json',dict(status='no_step_audit_complete',optimizer_updates=0,
            history_commits=0,FEM_solves=0,elapsed_seconds=time.monotonic()-started))
        return
    np.savez_compressed(a.out/'fixed_inputs.npz',node_coords=z['canonical_node_coords'],connectivity=z['connectivity'],
        FEM_initial_damage=z['FEM_initial_damage'],crack_mask=z['crack_mask'],hist_alpha=hist.cpu().numpy())
    del origin,check,restored,vectors,uvd,uvd2,uvd3,origin_uvd,capture,loaded,before_state
    summary=[];initial_gradient=None;first_parameters=None
    for arm,beta in zip(r['arms'],r['betas']):
        budget();t0=time.monotonic();folder=a.out/arm;folder.mkdir()
        field=make_field(state,device,new_adapter());params=list(field.net.parameters());opt=optimizer(params)
        previous_gradient=None
        def readout(k):
            budget(t0);dest=folder/f'update{k:03d}';dest.mkdir()
            with torch.no_grad():u,v,d,ee=evaluate(field)
            gu,gv=q4_gradient(u,cells,B),q4_gradient(v,cells,B)
            ex,ey,gamma=gu[:,:,0],gv[:,:,1],gu[:,:,1]+gv[:,:,0]
            raw=.5*(1/(3*.4))*torch.relu(ex+ey).square()+(1/(2*1.3))*((2/3)*(ex.square()+ey.square()-ex*ey)+.5*gamma.square())
            dg=q4_interpolate(d,cells,N);hg=q4_interpolate(hist,cells,N);active=(1-dg).square()*raw
            uu=u.detach().clone().requires_grad_(True);vv=v.detach().clone().requires_grad_(True)
            force=torch.autograd.grad(compute_energy(x,uu,vv,d.detach(),hist,mat,model,area,cells,
                f_fatigue=1.,irreversibility_penalty_cfg=pcfg)[0],(uu,vv))
            free=(x[:,1]>-.5+1e-7)&(x[:,1]<.5-1e-7)
            total1=sum(ee);totalb=ee[0]+ee[1]+beta*ee[2];reg=regularizer(field).detach()
            meta=dict(arm=arm,beta=beta,updates=k,U=.02999988,energies=[float(q) for q in ee],
                weighted_Ehist=float(beta*ee[2]),S1=float(total1),Sbeta=float(totalb),R=float(reg),
                optimized_loss=float(torch.log10(totalb)+1e-5*reg),
                d_min=float(d.min()),d_max=float(d.max()),healing_max=float(torch.relu(hist-d).max()),
                healing_GP_max=float(torch.relu(hg-dg).max()),healing_GP_count=int((hg>dg).sum()),
                line_min=float(d[mask].min()),line_max=float(d[mask].max()),
                free_u_l2=float(torch.linalg.vector_norm(torch.cat((force[0][free],force[1][free])))),
                Rprop_state=rprop_state_summary(opt))
            np.savez_compressed(dest/'fields.npz',u=u.cpu().numpy(),v=v.cpu().numpy(),d=d.cpu().numpy(),
                raw_gp=raw.cpu().numpy(),active_gp=active.cpu().numpy(),
                strain_gp=torch.stack((ex,ey,.5*gamma),-1).cpu().numpy())
            torch.save({'network':field.net.state_dict(),'mapper':field.nodal_damage_alignment.state_dict(),
                'hist_alpha':hist,'hist_fat':ck['hist_fat'],'psi_plus_prev':ck['psi_plus_prev'],
                'psi_history_elem':ck['psi_history_elem'],'optimizer':opt.state_dict(),'updates':k},dest/'checkpoint.pt')
            dump(dest/'result.json',meta);invariant(field);budget(t0);return meta
        with torch.no_grad():
            initial=make_field(state,device,field.nodal_damage_alignment,load=0).fieldCalculation(x)
            np.savez_compressed(folder/'U0_initial.npz',u=initial[0].cpu().numpy(),v=initial[1].cpu().numpy(),d=initial[2].cpu().numpy())
        before=readout(0)
        info,gg=probe(field,folder/'gradients_update000.json',t0)
        assert info['same_snapshot_beta_signs']['bitwise_equal']
        if initial_gradient is None:initial_gradient=gg[1.].cpu().clone()
        else:assert torch.equal(initial_gradient,gg[1.].cpu())
        del gg
        trace=[]
        try:
            for k in range(200):
                budget(t0);opt.zero_grad(set_to_none=True)
                *_,ee=evaluate(field);reg=regularizer(field);s1=sum(ee);sb=ee[0]+ee[1]+beta*ee[2]
                loss=torch.log10(sb)+1e-5*reg
                if not bool(torch.isfinite(loss)):raise RuntimeError('nonfinite loss')
                loss.backward()
                current=torch.cat([(torch.zeros_like(p) if p.grad is None else p.grad).reshape(-1) for p in params]).detach()
                if not bool(torch.isfinite(current).all()):raise RuntimeError('nonfinite training gradient')
                if k==0:assert torch.equal(current.cpu(),initial_gradient)
                flips=sign_stats(previous_gradient,current) if previous_gradient is not None else None
                previous_gradient=current.clone()
                trace.append(dict(before_update=k,energies=[float(q.detach()) for q in ee],
                    S1=float(s1.detach()),Sbeta=float(sb.detach()),weighted_Ehist=float((beta*ee[2]).detach()),
                    R=float(reg.detach()),objective=float(loss.detach()),
                    adjacent_update_gradient_signs=flips,elapsed_seconds=time.monotonic()-t0))
                budget(t0);opt.step();invariant(field)
                if k==0:
                    now=torch.cat([p.detach().reshape(-1) for p in params]).cpu()
                    if first_parameters is None:first_parameters=now.clone()
                    else:assert torch.equal(first_parameters,now)
                    readout(1);probe(field,folder/'gradients_update001.json',t0)
                if (k+1)%20==0:print(json.dumps(dict(arm=arm,updates=k+1,seconds=time.monotonic()-started)),flush=True)
            after=readout(200);probe(field,folder/'gradients_update200.json',t0)
        finally:dump(folder/'trace.json',trace)
        budget(t0)
        summary.append(dict(arm=arm,beta=beta,updates=200,before=before,after=after,seconds=time.monotonic()-t0))
        del field,opt,params,previous_gradient,initial
    budget()
    dump(a.out/'complete.json',dict(status='completed',run_id=r['run_id'],commit=r['commit'],arms=summary,
        total_updates=400,elapsed_seconds=time.monotonic()-started,history_updates=0,FEM_solves=0,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),symmetry_weight=0,
        initial_gradient_equality=True,first_update_parameters_bitwise_equal=True,preflight_passed=True))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--recipe',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--preflight-only',action='store_true')
    args=p.parse_args()
    try:main(args)
    except BaseException as exc:
        if args.out.is_dir():dump(args.out/'terminal_failure.json',dict(error=type(exc).__name__,message=str(exc)))
        raise
