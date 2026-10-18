"""Producer-only frozen r2 A/B/C c1s1 diagnostic; never loads target FEM."""
import argparse, datetime as dt, json, math, os, sys, time
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'SENS_tensile'),str(ROOT/'tools')]
from run_physical_symmetry_pilot import dump, BudgetStop
from network import NeuralNet
from field_computation import FieldComputation
from nodal_damage_alignment import NodalDamageAlignment
from material_properties import MaterialProperties
from pff_model import PFFModel
from compute_energy import compute_energy
from fatigue_history import compute_fatigue_degrad
from q4_quadrature import q4_shape_data,q4_gradient,q4_interpolate


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
        raise RuntimeError('explicit producer GPU required; no Mac training')
    recipe=json.loads(a.recipe.read_text())
    assert recipe['protocol']=='precrack-initial-alignment-r2-20261018'
    assert recipe['arms']==['A','B','C'] and recipe['updates_per_arm']==200
    assert recipe['total_gpu_seconds_cap']==3600 and recipe['load']==.02999988
    assert recipe['symmetry_weight']==0 and recipe['weight_decay']==1e-5
    assert recipe['energy_weights']==[1,1,1] and recipe['FEM_supervision']==0
    for item in recipe['inputs']:
        assert Path(item['path']).stat().st_size==item['bytes'],item
    assert (ROOT/'RUN_PROVENANCE.json').exists()
    provenance=json.loads((ROOT/'RUN_PROVENANCE.json').read_text())
    assert provenance['commit']==recipe['commit'] and provenance['dirty']==False
    a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1);torch.manual_seed(1)
    device=torch.device('cuda:0');torch.cuda.set_device(device)
    z=np.load(recipe['initial_inputs']);x=torch.tensor(z['node_coords'],device=device)
    cells=torch.tensor(z['connectivity'],device=device,dtype=torch.long)
    d0=torch.tensor(z['FEM_initial_damage'],device=device)
    mask=torch.tensor(z['crack_mask'],device=device)
    assert x.shape==(86756,2) and cells.shape==(86408,4) and x.dtype==torch.float32
    assert int(mask.sum())==251 and torch.isfinite(d0).all()
    state=torch.load(recipe['network'],map_location='cpu',weights_only=True)
    ck=torch.load(recipe['history'],map_location=device,weights_only=False)
    assert ck['history_storage']=='q4_gp4' and ck['damage_history_storage']=='previous_accepted_nodal'
    assert ck['mesh_connectivity_arity']==4 and ck['history_driver_mode']=='current_active'
    assert not ck.get('lagged_stiffness',False)
    for key in ['hist_fat','psi_plus_prev','psi_history_elem']:
        assert int(torch.count_nonzero(ck[key]))==0,key
    h0=ck['hist_alpha'].detach().clone();fat=ck['hist_fat'].detach().clone()
    assert h0.shape==(86756,) and fat.shape==(86408,4)
    assert np.array_equal(h0.cpu().numpy(),z['PIDL_U0_history'])
    frozen={k:ck[k].clone() for k in ['hist_alpha','hist_fat','psi_plus_prev','psi_history_elem']}
    ff=compute_fatigue_degrad(fat,{'degrad_type':'asymptotic','alpha_T':.5}).detach()
    assert bool((ff==1).all())
    N,B,w=q4_shape_data(x,cells);area=w.sum(1)
    mat=MaterialProperties(1.,.3,1.,.01);model=PFFModel('AT1','volumetric',.005,residual_stiffness=0.)
    assert model.irrPenalty()==16875
    pcfg={'enable':True,'mode':'fem_gp_q4','spatial_integration':'native_q4_gp4'}
    dump(a.out/'receipt.json',dict(protocol=recipe['protocol'],commit=recipe['commit'],run_id=recipe['run_id'],
        pid=os.getpid(),host=os.uname().nodename,gpu=os.environ['CUDA_VISIBLE_DEVICES'],command=sys.argv,
        started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),history_updates=0,FEM_solves=0,
        updates_per_arm=200,total_gpu_seconds_cap=3600,loss='log10(Eel+Ed+Ehist)+1e-5*named_weight_L2',
        optimizer='fresh Rprop lr1e-5 etas(.5,1.2) step_sizes(1e-10,50)',symmetry_weight=0))
    def budget():
        torch.cuda.synchronize()
        if time.monotonic()-started>=3500:raise BudgetStop('global 3500s internal cap')
    origin=make_field(state,device);capture=[]
    hook=origin.net.register_forward_hook(lambda m,i,o:capture.append(o[:,2].detach().clone()))
    with torch.no_grad():uvd=origin.fieldCalculation(x)
    hook.remove();assert len(capture)==1
    rawref=capture[0]
    adapters={'A':None,'B':NodalDamageAlignment(x,mode='hard_line',expected_crack_mask=mask),
        'C':NodalDamageAlignment(x,mode='fem_initial',initial_damage=d0,raw_reference=rawref,expected_crack_mask=mask)}
    with torch.no_grad():check=make_field(state,device,adapters['C']).fieldCalculation(x)
    assert torch.equal(check[2],d0) and torch.equal(uvd[0],check[0]) and torch.equal(uvd[1],check[1])
    assert float((uvd[2]-h0).abs().max())<1e-5
    np.savez_compressed(a.out/'fixed_inputs.npz',node_coords=z['canonical_node_coords'],connectivity=z['connectivity'],
        FEM_initial_damage=z['FEM_initial_damage'],crack_mask=z['crack_mask'],hist_alpha=h0.cpu().numpy())
    dump(a.out/'anchor_checks.json',dict(C_initial_Linf_to_FEM_float32=0,UV_bitwise_unchanged=True,
        full_batch_nodes=len(x),device=str(device),dtype=str(x.dtype),crack_nodes=251,
        original_history_vs_GPU_output_Linf=float((uvd[2]-h0).abs().max()),reanchor_after_training=False))
    del origin,capture,uvd,check
    summary=[]
    for arm in recipe['arms']:
        budget();t0=time.monotonic();folder=a.out/arm;folder.mkdir()
        adapter=adapters[arm];field=make_field(state,device,adapter)
        hist=h0.clone() if adapter is None else adapter.initial_history(h0)
        hist_frozen=hist.clone()
        adapter_frozen={k:v.clone() for k,v in adapter.named_buffers()} if adapter else {}
        np.save(folder/'initial_history.npy',hist.cpu().numpy())
        def parts():
            u,v,d=field.fieldCalculation(x)
            if not all(bool(torch.isfinite(q).all()) for q in (u,v,d)):raise RuntimeError('nonfinite field')
            if adapter is not None and not bool((d[mask]==1).all()):raise RuntimeError('crack line contract')
            ee=compute_energy(x,u,v,d,hist,mat,model,area,cells,f_fatigue=ff,irreversibility_penalty_cfg=pcfg)
            energy=sum(ee)
            if not bool(torch.isfinite(energy)) or float(energy.detach())<=0:raise RuntimeError('invalid energy domain')
            return u,v,d,ee,torch.log10(energy)
        def readout(k):
            budget();dest=folder/f'update{k:03d}';dest.mkdir()
            with torch.no_grad():u,v,d,ee,jp=parts()
            gu,gv=q4_gradient(u,cells,B),q4_gradient(v,cells,B)
            ex,ey,gamma=gu[:,:,0],gv[:,:,1],gu[:,:,1]+gv[:,:,0]
            raw=.5*(1/(3*.4))*torch.relu(ex+ey).square()+(1/(2*1.3))*((2/3)*(ex.square()+ey.square()-ex*ey)+.5*gamma.square())
            dg=q4_interpolate(d,cells,N);active=(1-dg).square()*raw
            uu=u.detach().clone().requires_grad_(True);vv=v.detach().clone().requires_grad_(True)
            force=torch.autograd.grad(compute_energy(x,uu,vv,d.detach(),hist,mat,model,area,cells,f_fatigue=ff,irreversibility_penalty_cfg=pcfg)[0],(uu,vv))
            free=(x[:,1]>-.5+1e-7)&(x[:,1]<.5-1e-7)
            meta=dict(arm=arm,updates=k,U=.02999988,energies=[float(q) for q in ee],log_physical=float(jp),
                d_min=float(d.min()),d_max=float(d.max()),healing_max=float(torch.relu(hist-d).max()),
                line_min=float(d[mask].min()),line_max=float(d[mask].max()),
                free_u_l2=float(torch.linalg.vector_norm(torch.cat((force[0][free],force[1][free])))))
            np.savez_compressed(dest/'fields.npz',u=u.cpu().numpy(),v=v.cpu().numpy(),d=d.cpu().numpy(),
                raw_gp=raw.cpu().numpy(),active_gp=active.cpu().numpy())
            torch.save({'network':field.net.state_dict(),'mapper':adapter.state_dict() if adapter else None,
                'hist_alpha':hist,'hist_fat':fat,'psi_plus_prev':ck['psi_plus_prev'],'psi_history_elem':ck['psi_history_elem'],
                'optimizer':opt.state_dict(),'updates':k},dest/'checkpoint.pt')
            dump(dest/'result.json',meta);return meta
        params=list(field.net.parameters())
        opt=torch.optim.Rprop(params,lr=1e-5,etas=(.5,1.2),step_sizes=(1e-10,50))
        with torch.no_grad():
            initial=make_field(state,device,adapter,load=0).fieldCalculation(x)
            np.savez_compressed(folder/'U0_initial.npz',u=initial[0].cpu().numpy(),v=initial[1].cpu().numpy(),d=initial[2].cpu().numpy())
        before=readout(0);trace=[]
        try:
            for k in range(200):
                budget();opt.zero_grad(set_to_none=True)
                *_,ee,jp=parts()
                reg=sum(p.square().sum() for name,p in field.net.named_parameters() if 'weight' in name)
                loss=jp+1e-5*reg
                if not bool(torch.isfinite(loss)):raise RuntimeError('nonfinite loss')
                loss.backward()
                if any(p.grad is not None and not bool(torch.isfinite(p.grad).all()) for p in params):raise RuntimeError('nonfinite gradients')
                trace.append(dict(before_update=k,energies=[float(q.detach()) for q in ee],objective=float(loss.detach())))
                opt.step()
                if (k+1)%20==0:print(json.dumps(dict(arm=arm,updates=k+1,seconds=time.monotonic()-started)),flush=True)
            after=readout(200)
        finally:dump(folder/'trace.json',trace)
        assert torch.equal(hist,hist_frozen)
        for key,val in frozen.items():assert torch.equal(ck[key],val)
        if adapter:
            for key,val in adapter.named_buffers():assert torch.equal(val,adapter_frozen[key])
        summary.append(dict(arm=arm,updates=200,before=before,after=after,seconds=time.monotonic()-t0))
        del field,opt,params,initial
    budget()
    dump(a.out/'complete.json',dict(status='completed',arms=summary,total_updates=600,
        elapsed_seconds=time.monotonic()-started,history_updates=0,FEM_solves=0,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),symmetry_weight=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--recipe',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    try:main(a)
    except BaseException as exc:
        if a.out.is_dir():dump(a.out/'terminal_failure.json',dict(error=type(exc).__name__,message=str(exc)))
        raise
