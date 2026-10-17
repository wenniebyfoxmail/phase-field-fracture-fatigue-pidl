#!/usr/bin/env python3
"""Producer CPU checkpoint readout and independent directional evaluations; no fit."""
import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')


def plateau(values):
    x=np.asarray(values,dtype=np.float32).reshape(-1)
    assert len(x)>1 and np.isfinite(x).all()
    q=abs(np.diff(x))/(abs(x[:-1])+np.float32(np.finfo(float).eps))
    return dict(epochs=len(x),last_preupdate_loss=float(x[-1]),last10_relative_changes=q[-10:].tolist(),
                trailing10_relative_stop=bool(len(q)>=10 and np.all(q[-10:]<=np.float32(5e-7))),budget_exhausted=len(x)>=10000)


def main(z):
    assert not z.out.exists()
    z.out.mkdir(parents=True)
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    assert not torch.cuda.is_available(), 'CPU-only readout must hide CUDA'
    contract=json.loads(z.contract.read_text());code=Path(contract['code']);archive=Path(contract['archive'])
    paths={}
    for item in contract['files']:
        p=Path(item['path']);assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'];paths[str(p)]=item['sha256']
    sys.path[:0]=[str(code/'SENS_tensile'),str(code/'source')]
    from export_pidl_element_diagnostics import build_field_computation,safe_torch_load,parse_settings
    from compute_energy import compute_energy
    from fatigue_history import compute_fatigue_degrad
    import config
    settings=parse_settings(archive/'model_settings.txt')
    assert settings['runner_git_commit']=='ad749c8bbba8120b3961add989b11427fab86254'
    assert settings['history_storage']=='q4_gp4' and settings['damage_history_storage']=='previous_accepted_nodal'
    assert settings['history_driver_mode']=='current_active' and float(settings['residual_stiffness'])==0
    assert settings['supervision']=='physics_only_no_FEM_field_targets' and settings['representation']=='coordinate_MLP'
    config.PFF_model_dict['residual_stiffness']=0.0
    fc,pff,mat,inp,conn,area=build_field_computation(archive,torch.device('cpu'),.12)
    assert inp.shape==(86756,2) and conn.shape==(86408,4)
    assert not fc.williams_enabled and not fc.ansatz_enabled and not fc.exact_bc_enabled
    assert not getattr(fc,'symmetry_prior',False)
    fc.net.eval();params=[p for p in fc.net.parameters() if p.requires_grad]
    named=list(fc.net.named_parameters());assert len(params)==len(named)
    penalty={'enable':True,'mode':'fem_gp_q4','spatial_integration':'native_q4_gp4'}
    recorded=np.load(archive/'best_models/energy_gradient_terms_vs_cycle.npy')
    assert recorded.shape==(601,7) and np.array_equal(recorded[:,0],np.arange(601))
    start=time.monotonic();rows=[];trials=[];fieldsdir=z.out/'fields';fieldsdir.mkdir()
    np.savez_compressed(z.out/'mesh.npz',node_coords=inp.numpy(),connectivity=conn.numpy())
    dump(z.out/'receipt.json',dict(protocol='S04-E011-NCP-r1',analysis_commit=contract['analysis_commit'],source_commit=settings['runner_git_commit'],
         pid=os.getpid(),host=os.uname().nodename,device='cpu',threads=1,command=sys.argv,started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
         original_archive=str(archive),optimizer_steps=0,history_commits=0))
    def budget_check():
        if time.monotonic()-start>=1800:raise TimeoutError('no_new_evaluation_after_30min')
    def objective(hist,ff,backward=False):
        budget_check()
        fc.net.zero_grad(set_to_none=True)
        with torch.set_grad_enabled(backward):
            u,v,d=fc.fieldCalculation(inp)
            if backward:
                for q in [u,v,d]:q.retain_grad()
            ee,ed,eh=compute_energy(inp,u,v,d,hist,mat,pff,area,conn,f_fatigue=ff,irreversibility_penalty_cfg=penalty)
            energy=ee+ed+eh
            if not bool(torch.isfinite(energy)) or float(energy.detach())<=0:return None,None
            reg=sum(p.square().sum() for name,p in named if 'weight' in name)
            loss=torch.log10(energy)+1e-5*reg
            if not bool(torch.isfinite(loss)):return None,None
            data=dict(loss=float(loss.detach()),log_energy=float(torch.log10(energy).detach()),reg=float((1e-5*reg).detach()),
                      E_el=float(ee.detach()),E_d=float(ed.detach()),E_hist=float(eh.detach()))
            extra=dict(u=u.detach().numpy().copy(),v=v.detach().numpy().copy(),d=d.detach().numpy().copy())
            if backward:
                # These are gradients in nodal field space, not parameter space.
                components=[]
                for term in [ee,ed,eh]:
                    gd=torch.autograd.grad(term,d,retain_graph=True,allow_unused=True)[0]
                    components.append(torch.zeros_like(d) if gd is None else gd.detach())
                data['nodal_damage_component_gradient_norms']=[float(torch.linalg.vector_norm(q)) for q in components]
                # autograd.grad(term,d) also fills retained nonleaf d.grad.
                # Clear retained field buffers before the actual objective backward.
                for q in [u,v,d]:q.grad=None
                loss.backward()
                factor=float(energy.detach())*np.log(10.)
                for key,q in [('u',u),('v',v),('d',d)]:
                    assert q.grad is not None and torch.isfinite(q.grad).all()
                    extra['own_energy_gradient_'+key]=(q.grad.detach()*factor).numpy().copy()
        return data,extra
    try:
      for cycle in [1,20,60,80,83]:
          for substep,load in [(2,.05999988),(4,.11999988)]:
              budget_check()
              k=5*(cycle-1)+substep;best=archive/'best_models'
              model=best/f'trained_1NN_{k}.pt';prev=safe_torch_load(best/f'checkpoint_step_{k-1}.pt',torch.device('cpu'))
              cur=safe_torch_load(best/f'checkpoint_step_{k}.pt',torch.device('cpu'))
              for h in [prev,cur]:
                  assert h['mesh_connectivity_arity']==4 and h['history_storage']=='q4_gp4'
                  assert h['damage_history_storage']=='previous_accepted_nodal' and h['history_driver_mode']=='current_active'
                  assert not h['lagged_stiffness_enabled'] and h['hist_alpha'].shape==(86756,) and h['hist_fat'].shape==(86408,4)
                  assert float(h.get('lambda_hist_weight',1))==1
              assert prev['mesh_state_signature']==cur['mesh_state_signature']==contract['mesh_state_signature']
              fc.net.load_state_dict(safe_torch_load(model,torch.device('cpu')));fc.lmbda=torch.tensor([load])
              hist=prev['hist_alpha'];ff=compute_fatigue_degrad(prev['hist_fat'],{'degrad_type':'asymptotic','alpha_T':.5})
              assert torch.isfinite(hist).all() and torch.isfinite(ff).all()
              original=[p.detach().clone() for p in params]
              repeat,_=objective(hist,ff);base,field=objective(hist,ff,True)
              assert base is not None and repeat is not None
              gt=[p.grad.detach().clone() if p.grad is not None else torch.zeros_like(p) for p in params]
              assert all(torch.isfinite(g).all() for g in gt)
              gr=[2e-5*p.detach() if 'weight' in name else torch.zeros_like(p) for name,p in named]
              gp=[g-r for g,r in zip(gt,gr)]
              l2=lambda gg:float(torch.sqrt(sum(g.double().square().sum() for g in gg)))
              gn=l2(gt);pn=l2(original);pg=l2(gp);rg=l2(gr)
              row=dict(cycle=cycle,substep=substep,step=k,load=load,**base,**plateau(np.load(best/f'trainLoss_1NN_{k}.npy')),
                 parameter_gradient_l2=gn,physical_log_parameter_gradient_l2=pg,reg_parameter_gradient_l2=rg,
                 physical_reg_gradient_cosine=float(sum((x.double()*y.double()).sum() for x,y in zip(gp,gr))/(pg*rg)) if pg*rg else None,
                 parameter_l2=pn,repeat_loss_difference=abs(base['loss']-repeat['loss']),f_pre_min=float(ff.min()),
                 d_min=float(field['d'].min()),d_max=float(field['d'].max()),negative_nodes=int((field['d']<0).sum()),above_one_nodes=int((field['d']>1).sum()),
                 nodal_lower_violation_max=float(np.maximum(hist.numpy()-field['d'],0).max()),optimizer_state_saved=False)
              errors=[float(abs(base[key]-recorded[k,j])/max(abs(recorded[k,j]),1e-10)) for j,key in enumerate(['E_el','E_d','E_hist'],1)]
              row['original_poststep_component_relative_errors']=errors
              row['source_objective_readout_pass']=bool(max(errors)<=1e-4)
              # Readout arrays retain actual pre-optimization history, not current commit.
              field.update(hist_alpha_pre=hist.numpy(),hist_fat_pre=prev['hist_fat'].numpy(),f_pre=ff.numpy(),hist_fat_post=cur['hist_fat'].numpy())
              np.savez_compressed(fieldsdir/f'c{cycle}_s{substep}.npz',**field)
              floor=abs(base['loss']-repeat['loss'])+32*np.finfo(np.float32).eps*max(1,abs(base['loss']))
              row['direction_loss_roundoff_floor']=float(floor)
              local=[]
              if row['source_objective_readout_pass'] and gn>0:
                  try:
                      for t in [1e-7,3e-7,1e-6,3e-6,1e-5,3e-5,1e-4,3e-4]:
                          with torch.no_grad():
                              for p,p0,g in zip(params,original,gt):p.copy_(p0-t*max(1,pn)*g/gn)
                          q,_=objective(hist,ff)
                          entry=dict(cycle=cycle,substep=substep,step=k,fraction=t,valid=q is not None,
                                     loss=q['loss'] if q else None,loss_drop=base['loss']-q['loss'] if q else None)
                          local.append(entry);trials.append(entry)
                  finally:
                      with torch.no_grad():
                          for p,p0 in zip(params,original):p.copy_(p0)
              assert all(torch.equal(p,p0) for p,p0 in zip(params,original))
              row['best_tested_loss_drop']=max([q['loss_drop'] for q in local if q['valid']]+[0.])
              row['lower_fixed_objective_found']=bool(row['best_tested_loss_drop']>floor)
              rows.append(row);dump(z.out/'rows.json',rows);dump(z.out/'trials.json',trials)
              print('READOUT',cycle,substep,'source',row['source_objective_readout_pass'],'g',gn,'drop',row['best_tested_loss_drop'],flush=True)
              del field,prev,cur,original,gt,gp,gr,hist,ff
    except TimeoutError as err:
        dump(z.out/'rows.json',rows);dump(z.out/'trials.json',trials)
        dump(z.out/'partial.json',dict(reason=str(err),completed=len(rows),elapsed_seconds=time.monotonic()-start,
             budget='No new evaluation after 30min; evaluation already running may finish',optimizer_steps=0,history_commits=0))
        return
    # Scalar evolution and all stored loss stopping traces are original trajectory evidence.
    evolution={}
    for leaf in ['E_el_vs_cycle.npy','x_tip_alpha_vs_cycle.npy','x_tip_vs_cycle.npy','alpha_bar_vs_cycle.npy','time_vs_cycle.npy','energy_gradient_terms_vs_cycle.npy']:
        evolution[leaf.removesuffix('.npy')]=np.load(archive/'best_models'/leaf)
    np.savez_compressed(z.out/'original_evolution.npz',**evolution)
    dump(z.out/'all_loss_stops.json',[dict(step=k,**plateau(np.load(archive/'best_models'/f'trainLoss_1NN_{k}.npy'))) for k in range(1,601)])
    for path,digest in paths.items():assert sha(Path(path))==digest,'Original input changed'
    dump(z.out/'complete.json',dict(status='completed',states=len(rows),history_commits=0,optimizer_steps=0,finished_utc=dt.datetime.now(dt.timezone.utc).isoformat()))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--contract',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);main(ap.parse_args())
