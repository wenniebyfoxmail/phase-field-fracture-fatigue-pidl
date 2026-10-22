"""GPU-only standard-U0.12 continuous three-cycle primal/dual exploration.

No core/default edits. Both arms start from the SAME legal recovery state.
The new arm retains the original network map (no clipping or sigmoid floor).
PHR constraints are outside log(Eel+Ed); their numerical reaction is explicit.
"""
from __future__ import annotations
import argparse,json,sys,time
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'SENS_tensile')]
from construct_model import construct_model
from field_computation import FieldComputation
from input_data_from_mesh import prep_input_data
from compute_energy import compute_energy,get_psi_plus_per_elem,gradients
from fatigue_history import compute_fatigue_degrad,update_fatigue_history
from fit import fit_with_early_stopping
from optim import get_optimizer
from irreversibility_constraints import phr_inequality_term,update_inequality_multiplier
FAT=dict(loading_type='cyclic',accum_type='carrara',degrad_type='asymptotic',alpha_T=.5)
IRR=dict(enable=True,mode='fem_gp_tri3')
RED=dict(enable=True,mode='fem_gp_tri3_g_mean')
FACTORS=(.25,.5,.75,1.,0.)

def savejson(p,x):
    p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')

def load(p,device='cuda'):
    return torch.load(p,map_location=device,weights_only=False)

class Cap(Exception):pass

def lumped_weights(conn,area,n):
    w=torch.zeros(n,device=area.device,dtype=area.dtype)
    for k in range(3):w.index_add_(0,conn[:,k],area/3)
    assert bool((w>0).all())
    return (w/w.sum()).detach()

def constraint_metrics(d,h,mu):
    c=torch.stack((h-d,d-1))
    return dict(primal_max=float(c.clamp_min(0).max()),
        lower_violation=float(c[0].clamp_min(0).max()),upper_violation=float(c[1].clamp_min(0).max()),
        complementarity_unscaled=float((mu*c).abs().max()),
        lower_multiplier_max=float(mu[0].max()),upper_multiplier_max=float(mu[1].max()),
        retreat_max=float((h-d).clamp_min(0).max()),d_min=float(d.min()),d_max=float(d.max()),
        complementarity_scaled=float((mu*c).abs().max()/(1+mu.abs().max())),
        multiplier_max=float(mu.max()),lower_active_fraction=float((mu[0]>0).float().mean()),
        upper_active_fraction=float((mu[1]>0).float().mean()))

def admissible(m):
    # Strict box protects the NEXT history. No clipping/repair of saved states.
    return (m['d_min']>=0 and m['d_max']<=1 and m['retreat_max']<=5e-6
        and m['complementarity_scaled']<=5e-5 and m['parameter_kkt_rms']<=5e-5)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--source-commit',required=True)
    ap.add_argument('--step-seconds',type=float,default=240)
    ap.add_argument('--total-seconds',type=float,default=6900)
    a=ap.parse_args()
    assert 0<a.step_seconds<=240 and 0<a.total_seconds<=6900
    assert torch.cuda.is_available(),'Training is GPU producer only'
    torch.set_num_threads(4)
    a.output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();deadline=started+a.total_seconds
    extrema=torch.tensor([[-.5,.5],[-.5,.5]],device='cuda')
    pff,mat,net=construct_model(dict(PFF_model='AT1',se_split='volumetric',tol_ir=5e-3,residual_stiffness=0.),
        dict(mat_E=1.,mat_nu=.3,w1=1.,l0=.01),
        dict(hidden_layers=8,neurons=400,seed=1,activation='TrainableReLU',init_coeff=1.,compile=False),extrema,'cuda')
    field=FieldComputation(net.to('cuda'),extrema,torch.tensor(0.,device='cuda'),torch.tensor([np.pi/2],device='cuda'),l0=.01)
    inp,conn,area,_=prep_input_data(mat,pff,dict(x_init=[-.5],y_init=[0],L_crack=[.5],angle_crack=[0]),
        dict(gradient_type='numerical'),str(ROOT/'SENS_tensile/meshed_geom_fem_soft_hist0.msh'),'cuda')
    assert inp.shape==(45591,2) and conn.shape==(90000,3)
    weights=lumped_weights(conn,area,len(inp));named=list(net.named_parameters());params=[p for _,p in named]
    settings=(a.baseline/'model_settings.txt').read_text()
    for token in ('umax: 0.12','mesh_tag: hard_d1_u0_recovery','recovery_step_offset: 1','fem_gp_tri3_g_mean'):assert token in settings,token
    ck0=load(a.baseline/'best_models/checkpoint_step_0.pt')
    initial=load(a.baseline/'best_models/trained_1NN_0.pt')
    assert ck0['history_driver_mode']=='current_active' and not ck0['lagged_stiffness_enabled']
    assert bool(((ck0['hist_alpha']>=0)&(ck0['hist_alpha']<=1)).all())
    assert bool((ck0['hist_fat']==0).all()) and bool((ck0['psi_plus_prev']==0).all())
    np.savez_compressed(a.output/'mesh.npz',xy=inp.cpu().numpy(),triangles=conn.cpu().numpy(),area=area.cpu().numpy(),node_weights=weights.cpu().numpy())
    savejson(a.output/'manifest.json',dict(experiment='S04-E037',protocol='r1',source_commit=a.source_commit,
        baseline=str(a.baseline),steps=list(range(1,16)),arms=['original','primal_dual'],torch=torch.__version__,
        gpu=torch.cuda.get_device_name(0),step_seconds=a.step_seconds,total_seconds=a.total_seconds,
        weight_decay=1e-5,history='independent continuous paths from identical recovery; frozen during physical step',
        constraints='original NN map; h-d<=0,d-1<=0; strict box at commit; no clipping',
        node_weights='lumped triangle area/3 normalized to sum1',run_ids=['S04-E037-R001','S04-E037-R002']))
    results=[]
    def fields():return field.fieldCalculation(inp)
    def reg():return 1e-5*sum(p.square().sum() for n,p in named if 'weight' in n)
    def objective(h,f,mu=None,rho=None,lagrangian=False):
        u,v,d=fields();es=compute_energy(inp,u,v,d,h,mat,pff,area,conn,f,irreversibility_penalty_cfg=IRR)
        physical=es[0]+es[1]
        if not bool(torch.isfinite(physical)) or not bool(physical>0):
            raise FloatingPointError('Physical energy must be positive and finite; no energy clipping')
        loss=torch.log10(physical)+reg()
        if mu is not None:
            if lagrangian:
                loss=loss+torch.sum(weights*(mu[0]*(h-d)+mu[1]*(d-1)))
            else:
                loss=loss+phr_inequality_term(h-d,mu[0],rho,weights)+phr_inequality_term(d-1,mu[1],rho,weights)
        return loss,(u,v,d),es
    def snapshot(folder,h,hfat,prev,f,mu=None,rho=None):
        snapstart=time.monotonic()
        net.zero_grad(set_to_none=True)
        loss,(u,v,d),es=objective(h,f,mu,rho,lagrangian=True)
        gs=torch.autograd.grad(loss,params,allow_unused=True)
        diagnostics['parameter_gradient_calls']+=1
        gnorm=torch.sqrt(sum((g.square().sum() for g in gs if g is not None)))
        # Field-space diagnostics use independent nodal variables and NO L2.
        # They are not asserted to vanish for a neural parameter optimum.
        ud=u.detach().requires_grad_();vd=v.detach().requires_grad_();dd=d.detach().requires_grad_()
        e0=compute_energy(inp,ud,vd,dd,h,mat,pff,area,conn,f,irreversibility_penalty_cfg=IRR)
        ru,rv,rd=torch.autograd.grad(e0[0]+e0[1],(ud,vd,dd))
        diagnostics['field_gradient_calls']+=1
        invm=weights.reciprocal()
        bad_bounds=int((h>1).sum())
        pg_inf=None
        if bad_bounds==0:
            pg=dd.detach()-torch.maximum(h,torch.minimum(torch.ones_like(h),dd.detach()-rd.detach()*invm))
            pg_inf=float(pg.abs().max())
        free=(inp[:,1]>-.5+1e-7)&(inp[:,1]<.5-1e-7)
        m=dict(E_el=float(es[0].detach()),E_d=float(es[1].detach()),shadow_E_irr=float(es[2].detach()),
            weighted_L2=float(reg().detach()),parameter_kkt_rms=float(gnorm/np.sqrt(sum(p.numel() for p in params))),
            parameter_kkt_norm=float(gnorm),field_damage_projected_inf=pg_inf,inconsistent_bound_count=bad_bounds,
            free_uv_residual_inf=float(torch.maximum(ru[free].abs().max(),rv[free].abs().max())),
            releasable_lower_count=int(((d<=h+5e-6)&(rd<0)&(h<1)).sum()),
            releasable_upper_count=int(((d>=1-5e-6)&(rd>0)&(h<1)).sum()))
        # The same cached fields drive all diagnostics/history; no floor refresh.
        with torch.no_grad():
            active=get_psi_plus_per_elem(inp,u,v,d,mat,pff,area,conn,history_driver_reduction_dict=RED)
            trialA=update_fatigue_history(hfat,active,prev,FAT);trialf=compute_fatigue_degrad(trialA,FAT)
            ex,ey,exy,_,_=gradients(inp,u,v,d,area,conn)
            tr=ex+ey;bulk=1/(3*(1-2*.3));shear=1/2.6
            raw=.5*bulk*tr.clamp_min(0).square()+shear*(ex.square()+ey.square()+2*exy.square()-tr.square()/3)
            if mu is not None:
                m.update(constraint_metrics(d,h,mu))
                np.savez_compressed(folder/'dual_state.npz',mu=mu.cpu().numpy(),rho=np.array(rho),
                    constraints=torch.stack((h-d,d-1)).cpu().numpy())
            else:m.update(dict(d_min=float(d.min()),d_max=float(d.max()),retreat_max=float((h-d).clamp_min(0).max())))
            np.savez_compressed(folder/'fields.npz',u=u.cpu().numpy(),v=v.cpu().numpy(),d=d.cpu().numpy(),
                history_d=h.cpu().numpy(),history_A=hfat.cpu().numpy(),history_prev=prev.cpu().numpy(),
                f_solve=f.cpu().numpy(),strain_xx=ex.cpu().numpy(),strain_yy=ey.cpu().numpy(),strain_xy=exy.cpu().numpy(),
                raw_psi=raw.cpu().numpy(),active_driver=active.cpu().numpy(),trial_A=trialA.cpu().numpy(),trial_f=trialf.cpu().numpy())
        net.zero_grad(set_to_none=True)
        diagnostics['seconds']+=time.monotonic()-snapstart
        return m,(d.detach().clone(),trialA.detach().clone(),active.detach().clone())
    for arm in ['original','primal_dual']:
        folder=a.output/arm;folder.mkdir()
        net.load_state_dict(initial,strict=True)
        h=ck0['hist_alpha'].detach().clone();hfat=ck0['hist_fat'].detach().clone();prev=ck0['psi_plus_prev'].detach().clone()
        path=[];armstart=time.monotonic()
        for step in range(1,16):
            if deadline-time.monotonic()<a.step_seconds+15:
                savejson(folder/'budget_stop.json',dict(next_step=step,elapsed=time.monotonic()-started));break
            sf=folder/f'step_{step:03d}';sf.mkdir()
            field.lmbda=torch.tensor(.12*FACTORS[(step-1)%5],device='cuda')
            f=compute_fatigue_degrad(hfat,FAT);oldh=h.clone();oldA=hfat.clone();oldprev=prev.clone()
            stepstart=time.monotonic();stopat=stepstart+a.step_seconds
            trace=[];updates=0;primal_gradient_calls=0;reason='not_solved';accepted=False
            diagnostics=dict(seconds=0.,parameter_gradient_calls=0,field_gradient_calls=0)
            mu=torch.zeros((2,len(inp)),device='cuda') if arm=='primal_dual' else None
            rho=100.;outercount=0
            if arm=='original':
                optimizer=get_optimizer(field.parameters(),'RPROP');realstep=optimizer.step
                def instrumented(*args,**kw):
                    nonlocal updates,primal_gradient_calls
                    primal_gradient_calls+=1
                    if time.monotonic()>=stopat:raise Cap
                    result=realstep(*args,**kw);updates+=1
                    return result
                optimizer.step=instrumented
                class Writer:
                    def add_scalars(self,tag,data,epoch):
                        if epoch%25==0:trace.append(dict(update=epoch,loss=float(data['loss'])))
                try:
                    fit_with_early_stopping(field,[(inp,torch.zeros((len(inp),1),device='cuda'))],conn,area,h,mat,pff,1e-5,
                        num_epochs=10000,optimizer=optimizer,min_delta=5e-7,writer=Writer(),
                        training_dict={'save_model_every_n':0},f_fatigue=f,irreversibility_penalty_cfg=IRR)
                    reason='standard_early_stop' if updates<10000 else 'standard_epoch_cap';accepted=True
                except Cap:reason='wall_cap'
                m,state=snapshot(sf,h,hfat,prev,f)
                if accepted:
                    reference=load(a.baseline/f'best_models/trained_1NN_{step}.pt')
                    m['archived_parameters_bitwise_equal']=all(torch.equal(net.state_dict()[k],v) for k,v in reference.items())
                    # A control drift invalidates subsequent claims, no silent repair.
                    if not m['archived_parameters_bitwise_equal']:reason='baseline_replay_mismatch';accepted=False
            else:
                before=float('inf');m=None;state=None
                try:
                    for outer in range(8):
                        outercount=outer+1
                        optimizer=get_optimizer(field.parameters(),'RPROP')
                        last=None;patience=0
                        for inner in range(1250):
                            if time.monotonic()>=stopat:raise Cap
                            optimizer.zero_grad(set_to_none=True)
                            loss,_,_=objective(h,f,mu,rho)
                            if not bool(torch.isfinite(loss)):raise FloatingPointError('nonfinite primal objective')
                            loss.backward();primal_gradient_calls+=1
                            if not all(p.grad is None or bool(torch.isfinite(p.grad).all()) for p in params):raise FloatingPointError('nonfinite gradient')
                            val=float(loss.detach());optimizer.step();updates+=1
                            if inner%50==0:trace.append(dict(outer=outer,update=updates,seconds=time.monotonic()-stepstart,loss=val,rho=rho))
                            if last is not None:
                                patience=patience+1 if abs(val-last)<=5e-7*max(abs(last),1e-12) else 0
                            last=val
                            if patience>=10:break
                        with torch.no_grad():
                            _,_,d=fields();c=torch.stack((h-d,d-1))
                            mu=torch.stack([update_inequality_multiplier(c[k],mu[k],rho) for k in range(2)])
                        m,state=snapshot(sf,h,hfat,prev,f,mu,rho)
                        trace.append(dict(outer=outer,update=updates,seconds=time.monotonic()-stepstart,rho=rho,**m))
                        if admissible(m):reason='neural_parameter_constraint_checks_met';accepted=True;break
                        violation=m['primal_max']
                        if violation>.25*before:rho=min(rho*10,1e8)
                        before=violation
                    if not accepted:reason='outer_or_update_cap'
                except Cap:reason='wall_cap'
                m,state=snapshot(sf,h,hfat,prev,f,mu,rho)
                # Fresh same-point check under UPDATED multipliers, including L2.
                accepted=accepted and admissible(m)
            assert torch.equal(h,oldh) and torch.equal(hfat,oldA) and torch.equal(prev,oldprev)
            if arm=='original' and accepted:
                d,A,active=state
                originalck=load(a.baseline/f'best_models/checkpoint_step_{step}.pt')
                history_equal=all(torch.equal(value,originalck[key]) for key,value in
                    [('hist_alpha',torch.maximum(h,d)),('hist_fat',A),('psi_plus_prev',active)])
                m['archived_history_bitwise_equal']=history_equal
                if not history_equal:accepted=False;reason='baseline_history_replay_mismatch'
            torch.save(net.state_dict(),sf/'network.pt')
            compute_seconds=time.monotonic()-stepstart
            # Last check is immediately before the only history commit. Output
            # accounting has a separate 15s reserve inside the global budget.
            if time.monotonic()>=min(stopat,deadline):
                accepted=False;reason='wall_cap_after_final_checks'
            if accepted:
                d,A,active=state
                h=torch.maximum(h,d).detach();hfat=A;prev=active
                torch.save(dict(hist_alpha=h,hist_fat=hfat,psi_plus_prev=prev),sf/'accepted_history.pt')
            rec=dict(arm=arm,step=step,cycle=(step-1)//5+1,substep=(step-1)%5+1,load=float(field.lmbda),
                updates=updates,outer_iterations=outercount,primal_gradient_calls=primal_gradient_calls,
                diagnostics=diagnostics,solve_checks_and_network_save_seconds=compute_seconds,
                accepted=accepted,stop_reason=reason,metrics=m)
            savejson(sf/'trace.json',trace)
            rec['step_elapsed_seconds']=time.monotonic()-stepstart
            savejson(sf/'receipt.json',rec);path.append(rec);savejson(folder/'steps.json',path)
            print(json.dumps(rec,allow_nan=False),flush=True)
            if not accepted:
                if arm=='original':raise RuntimeError('Original control not accepted: '+reason)
                break
        summary=dict(arm=arm,steps_attempted=len(path),steps_accepted=sum(r['accepted'] for r in path),
            completed_three_cycles=len(path)==15 and all(r['accepted'] for r in path),elapsed_seconds=time.monotonic()-armstart)
        savejson(folder/'summary.json',summary);results.append(summary);savejson(a.output/'results.json',results)
    savejson(a.output/'completed.json',dict(execution='succeeded',elapsed_seconds=time.monotonic()-started,results=results,
        interpretation='Each failed/capped step is unaccepted; no full-trajectory or field-space KKT claim.'))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        import traceback
        if '--output' in sys.argv:
            failure=Path(sys.argv[sys.argv.index('--output')+1])
            if failure.is_dir():savejson(failure/'fatal.json',dict(error=repr(exc),traceback=traceback.format_exc()))
        raise
