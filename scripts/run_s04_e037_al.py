"""S04-E037 r1: one legal post-recovery predecessor; conditional AL comparison.

GPU producer only. No history commit, coupled solve, continuation, or retry.
Historical physics is imported from a separately hash-locked e9dc263 snapshot.
"""
from __future__ import annotations
import argparse
import copy
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import numpy as np
import torch
from torch.nn.utils import parameters_to_vector, vector_to_parameters

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from irreversibility_constraints import phr_inequality_term, update_inequality_multiplier
from bounded_lbfgs import minimize
from numerical_checks import require_finite, finite_max, require_positive_energy
from t3_damage_reference import assemble_t3_damage, compare_physics_at_field, solve_t3_damage


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root, entries):
    for rel, digest in entries.items():
        if sha(root / rel) != digest:
            raise ValueError(f'source/input hash mismatch: {rel}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--physics-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    args = parser.parse_args()
    config = json.loads((ROOT / 'docs/research/S04/S04-E037/config.json').read_text())
    lock = json.loads((ROOT / 'docs/research/S04/S04-E037/input_lock.json').read_text())
    assert torch.cuda.is_available(), 'No CPU/Mac model execution'
    started = time.monotonic()
    args.output.mkdir(parents=True, exist_ok=False)
    verify(args.baseline, lock['baseline'])
    verify(args.physics_root, lock['physics'])
    sys.path[:0] = [str(args.physics_root / 'source'), str(args.physics_root / 'SENS_tensile')]
    from construct_model import construct_model
    from field_computation import FieldComputation
    from input_data_from_mesh import prep_input_data
    from compute_energy import compute_energy, gradients, strain_energy_with_split
    from fatigue_history import compute_fatigue_degrad
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    device = 'cuda'
    load = lambda p: torch.load(p, map_location=device, weights_only=False)
    ext = torch.tensor([[-.5,.5],[-.5,.5]], device=device)
    pff, mat, net = construct_model(
        dict(PFF_model='AT1', se_split='volumetric', tol_ir=.005, residual_stiffness=0.),
        dict(mat_E=1., mat_nu=.3, w1=1., l0=.01),
        dict(hidden_layers=8, neurons=400, seed=1, activation='TrainableReLU', init_coeff=1., compile=False), ext, device)
    field = FieldComputation(net, ext, torch.tensor(.03, device=device),
                             torch.tensor([np.pi/2], device=device), l0=.01)
    inp, conn, area, _ = prep_input_data(mat, pff,
        dict(x_init=[-.5], y_init=[0], L_crack=[.5], angle_crack=[0]),
        dict(gradient_type='numerical'),
        str(args.physics_root / 'SENS_tensile/meshed_geom_fem_soft_hist0.msh'), device)
    assert inp.shape == (45591,2) and conn.shape == (90000,3)
    ckpt = load(args.baseline / 'best_models/checkpoint_step_0.pt')
    assert ckpt['history_driver_mode'] == 'current_active' and not ckpt['lagged_stiffness_enabled']
    h = ckpt['hist_alpha'].detach().clone()
    histfat = ckpt['hist_fat'].detach().clone()
    prevpsi = ckpt['psi_plus_prev'].detach().clone()
    assert torch.isfinite(h).all() and torch.all((h >= 0) & (h <= 1))
    assert torch.equal(histfat, torch.zeros_like(histfat)) and torch.equal(prevpsi, torch.zeros_like(prevpsi))
    fatigue = compute_fatigue_degrad(histfat, dict(degrad_type='asymptotic', alpha_T=.5))
    assert torch.equal(fatigue, torch.ones_like(fatigue))
    initial = load(args.baseline / 'best_models/trained_1NN_0.pt')
    net.load_state_dict(initial, strict=True)
    named = list(net.named_parameters())
    params = [p for _,p in named]
    xinitial = parameters_to_vector(params).detach().clone()
    with torch.no_grad():
        u, v, d0 = [t.detach().clone() for t in field.fieldCalculation(inp)]
    gp_basis = torch.tensor([[4.,1.,1.],[1.,4.,1.],[1.,1.,4.]], device=device) / 6.
    gp_basis64 = torch.tensor([[4.,1.,1.],[1.,4.,1.],[1.,1.,4.]], device=device,dtype=torch.float64) / 6.
    gp = lambda d: (d[conn] @ gp_basis).reshape(-1)
    wnode = torch.zeros_like(h)
    wnode.scatter_add_(0, conn.reshape(-1), (area[:,None].expand(-1,3)/3).reshape(-1))
    wnode /= area.sum()
    wgp = (area[:,None].expand(-1,3)/3/area.sum()).reshape(-1)
    assert torch.all(wnode > 0)
    hg = gp(h)
    def constraints(d, arm):
        blocks = [(-d, wnode), (d-1., wnode)]
        if arm == 'G': blocks.append((hg-gp(d), wgp))
        if arm == 'N': blocks.append((h-d, wnode))
        return blocks
    def energies(d, uu=u, vv=v):
        return compute_energy(inp, uu, vv, d, h, mat, pff, area, conn, fatigue,
                              irreversibility_penalty_cfg=dict(enable=True, mode='fem_gp_tri3'))
    def reg_terms():
        full = 1e-5 * sum(p.square().sum() for n,p in named if 'weight' in n)
        uv = 1e-5 * net.output_layer.weight[:2].square().sum()
        return full, uv
    def flatgrad(loss, retain=False):
        gs = torch.autograd.grad(loss, params, allow_unused=True, retain_graph=retain)
        return torch.cat([(torch.zeros_like(p) if g is None else g).reshape(-1) for p,g in zip(params,gs)])
    def double_check(arm=None, dual=None, separate=False):
        n64 = copy.deepcopy(net).double()
        f64 = FieldComputation(n64, ext.double(), field.lmbda.double(), field.theta.double(), l0=.01)
        result = f64.fieldCalculation(inp.double())[2]
        require_finite(result)
        gradients64 = None
        if arm is not None:
            el,ed,eh = compute_energy(inp.double(),u.double(),v.double(),result,h.double(),mat,pff,
                area.double(),conn,fatigue.double(),irreversibility_penalty_cfg=dict(enable=True,mode='fem_gp_tri3'))
            energy=el+ed+(eh if arm=='Pstar' else 0)
            require_positive_energy(energy)
            loge=torch.log10(energy)
            reg=1e-5*sum(p.square().sum() for n,p in n64.named_parameters() if 'weight' in n)
            require_finite(loge,reg)
            ps=list(n64.parameters())
            def flatten(loss,retain=False):
                require_finite(loss)
                gs=torch.autograd.grad(loss,ps,allow_unused=True,retain_graph=retain)
                flat=torch.cat([(torch.zeros_like(p) if g is None else g).reshape(-1) for p,g in zip(ps,gs)]).detach()
                require_finite(flat)
                return flat
            if separate:
                gradients64=(flatten(loge,True),flatten(reg))
            else:
                cb=[(-result,wnode.double()),(result-1,wnode.double())]
                if arm=='G': cb.append(((h.double()[conn]@gp_basis64-result[conn]@gp_basis64).reshape(-1),wgp.double()))
                if arm=='N': cb.append((h.double()-result,wnode.double()))
                lag=loge+reg+sum((w*m.double()*c).sum() for (c,w),m in zip(cb,dual))
                gradients64=flatten(lag)
        result=result.detach()
        del n64, f64
        return result,gradients64
    d64initial, g64parts = double_check('N',separate=True)
    precision_delta = float((d64initial-d0.double()).abs().max())
    tau_c = finite_max(config['primal_floor'], 20*precision_delta)
    dump(args.output / 'input_validation.json', dict(history_min=float(h.min()), history_max=float(h.max()),
        initial_d_min=float(d0.min()), initial_d_max=float(d0.max()), precision_delta=precision_delta,
        primal_tolerance=tau_c, input_hashes=lock, history_timing='recovery postcommit step 0',
        current_state='c1/s1 j=1 U=.03', no_history_commit=True))
    if tau_c > config['primal_ceiling']:
        raise ValueError('float32/double forward discrepancy exceeds fixed precision ceiling')
    dd = d0.detach().clone().requires_grad_()
    et = energies(dd)
    e0 = et[0]+et[1]
    require_positive_energy(e0)
    gd0 = torch.autograd.grad(torch.log10(e0), dd)[0].detach()
    S = finite_max(float((gd0.abs()/wnode).max()), 1e-12)
    rho0 = S / .01
    require_finite(rho0)
    dscale=field.fieldCalculation(inp)[2]
    es=energies(dscale)
    g32physical=flatgrad(torch.log10(es[0]+es[1])).detach()
    g32reg=flatgrad(reg_terms()[0]).detach()
    parameter_scale=1+xinitial.double().abs()
    require_finite(parameter_scale,g32physical,g32reg,*g64parts)
    D0=finite_max(float((parameter_scale*g32physical.double()).abs().max()),
           float((parameter_scale*g32reg.double()).abs().max()),1e-8)
    delta_g=finite_max(float((parameter_scale*(g64parts[0]-g32physical.double())).abs().max()),
                float((parameter_scale*(g64parts[1]-g32reg.double())).abs().max()))/D0
    tau_theta=finite_max(config['stationarity_floor'],20*delta_g)
    if tau_theta>config['stationarity_ceiling']:
        raise ValueError('float32/double gradient discrepancy exceeds fixed precision ceiling')
    # Unscaled inner tolerance implies the final scaled criterion, since min(scale)>=1.
    inner_strict=tau_theta*D0/float(parameter_scale.max())
    # Independent fixed-u/f T3 QP assembly; all geometry is the same input mesh.
    with torch.no_grad():
        ex, ey, exy, _, _ = gradients(inp,u,v,d0,area,conn)
        eund, pp = strain_energy_with_split(ex,ey,exy,torch.zeros_like(area),mat,pff)
        pm = eund-pp
    cpu = lambda x: x.detach().cpu().numpy()
    np.savez_compressed(args.output/'common_state.npz', xy=cpu(inp), triangles=cpu(conn), area=cpu(area),
        u=cpu(u), v=cpu(v), d_initial=cpu(d0), h=cpu(h), hist_fat=cpu(histfat), psi_prev=cpu(prevpsi),
        fatigue=cpu(fatigue), psi_plus=cpu(pp), psi_minus=cpu(pm), node_weights=cpu(wnode))
    qp = assemble_t3_damage(cpu(inp),cpu(conn),cpu(area),cpu(pp),cpu(pm),cpu(fatigue),1.,8/3,.01)
    dcheck = d0.detach().clone().requires_grad_()
    checkterms = energies(dcheck)
    echeck = checkterms[0]+checkterms[1]
    ag = cpu(torch.autograd.grad(echeck,dcheck)[0]).astype(float)
    assembly_check=compare_physics_at_field(qp,cpu(d0).astype(float),float(echeck),ag)
    dump(args.output/'assembly_check.json',assembly_check)
    if not assembly_check['accepted']:
        raise ValueError('T3 assembly mismatch against exact historical energy')
    manifest = dict(experiment='S04-E037', protocol='r1', source_commit=args.source_commit,
        physics_commit=lock['physics_commit'], config=config, config_sha256=sha(ROOT/'docs/research/S04/S04-E037/config.json'),
        torch=torch.__version__, numpy=np.__version__, device=torch.cuda.get_device_name(0),
        parameter_count=xinitial.numel(), rho0=rho0, gradient_density_scale=S, primal_tolerance=tau_c,
        parameter_gradient_scale=D0,parameter_precision_delta=delta_g,parameter_tolerance=tau_theta,
        initialization='unchanged trained_1NN_0; all parameters trainable; cached u/v',
        objective='full original weights-only L2 1e-5; P*: log(E0+Ehist); G/N: log(E0)',
        history='fixed legal checkpoint0; no update', run_ids=['S04-E037-R001','S04-E037-R002','S04-E037-R003'])
    dump(args.output/'manifest.json',manifest)
    results=[]
    for arm in ('Pstar','G','N'):
        if time.monotonic()-started+config['arm_seconds']+60 > config['total_seconds']:
            raise RuntimeError('total budget insufficient for next arm; no partial unmatched launch')
        folder=args.output/arm
        folder.mkdir()
        vector_to_parameters(xinitial.clone(),params)
        dual=[torch.zeros_like(c) for c,w in constraints(d0,arm)]
        rho=rho0
        armstart=time.monotonic()
        deadline=armstart+config['arm_seconds']
        evalcount=0
        outer_trace=[]
        previous_violation=math.inf
        def evaluate(x):
            nonlocal evalcount
            evalcount+=1
            vector_to_parameters(x,params)
            d=field.fieldCalculation(inp)[2]
            el,ed,eh=energies(d)
            energy=el+ed+(eh if arm=='Pstar' else 0)
            if not torch.isfinite(energy) or not float(energy)>0:
                return None,None
            reg,_=reg_terms()
            loss=torch.log10(energy)+reg
            for (c,w),mu in zip(constraints(d,arm),dual):
                loss=loss+phr_inequality_term(c,mu,rho,w)
            if not torch.isfinite(loss): return None,None
            g=flatgrad(loss).detach()
            if not torch.isfinite(g).all(): return None,None
            return float(loss.detach()),g
        # Ordinary Lagrangian at the CURRENT multiplier, not PHR after another shift.
        def certify(label):
            nonlocal evalcount
            evalcount+=2 # one float32 and one independently rebuilt float64 Lagrangian
            d=field.fieldCalculation(inp)[2]
            el,ed,eh=energies(d)
            reg,uvreg=reg_terms()
            require_finite(d,el,ed,eh,reg,uvreg)
            require_positive_energy(el+ed+(eh if arm=='Pstar' else 0))
            base=torch.log10(el+ed+(eh if arm=='Pstar' else 0))+reg
            lag=base
            blocks=constraints(d,arm)
            for (c,w),mu in zip(blocks,dual): lag=lag+(w*mu*c).sum()
            gt=flatgrad(lag).detach()
            require_finite(lag,gt,*dual)
            d64,gt64=double_check(arm,dual)
            hd=h.double()
            cb64=[-d64,d64-1]
            if arm=='G': cb64.append((hd[conn]@gp_basis64-d64[conn]@gp_basis64).reshape(-1))
            if arm=='N': cb64.append(hd-d64)
            require_finite(*(c for c,w in blocks),*cb64,*(mu/S for mu in dual))
            primal=finite_max(*(float(c.clamp_min(0).max()) for c,w in blocks),*(float(c.clamp_min(0).max()) for c in cb64))
            comp=finite_max(*(float((mu*c).abs().max())/S for (c,w),mu in zip(blocks,dual)),
                            *(float((mu.double()*c).abs().max())/S for c,mu in zip(cb64,dual)))
            ncp=finite_max(*(float(torch.minimum(mu/S,-c).abs().max()) for (c,w),mu in zip(blocks,dual)),
                           *(float(torch.minimum(mu.double()/S,-c).abs().max()) for c,mu in zip(cb64,dual)))
            stationarity=finite_max(float((parameter_scale*gt.double()).abs().max()),
                             float((parameter_scale*gt64).abs().max()))/D0
            stats=dict(E_el=float(el.detach()),E_d=float(ed.detach()),E_hist=float(eh.detach()),
                L2=float(reg.detach()),L2_uv_only=float(uvreg.detach()),base_objective=float(base.detach()),
                primal_max=primal,dual_min=min(float(m.min()) for m in dual),complementarity_over_S=comp,
                normalized_NCP_inf=ncp,parameter_stationarity_scaled=stationarity,
                parameter_stationarity_inf=float(gt.abs().max()),parameter_stationarity_l2=float(gt.norm()),
                d_min=float(d.detach().min()),d_max=float(d.detach().max()),
                node_healing_max=float((h-d.detach()).clamp_min(0).max()),
                gp_healing_max=float((hg-gp(d.detach())).clamp_min(0).max()),
                double_node_healing_max=float((hd-d64).clamp_min(0).max()),
                double_gp_healing_max=float((hd[conn]@gp_basis64-d64[conn]@gp_basis64).clamp_min(0).max()),
                precision_delta=float((d64-d.detach().double()).abs().max()))
            if label:
                np.savez_compressed(folder/f'{label}.npz',d=cpu(d),d_double=cpu(d64),
                    **{f'multiplier_{i}':cpu(m) for i,m in enumerate(dual)})
            return stats
        beginning=certify('initial')
        qualified=False
        for outer in range(config['max_outer']):
            if time.monotonic()>=deadline-15 or evalcount>=config['max_evaluations']-8: break
            x=parameters_to_vector(params).detach().clone()
            inner_deadline=min(deadline-15,time.monotonic()+config['outer_seconds'])
            x,info=minimize(evaluate,x,max_calls=min(config['outer_evaluations'],config['max_evaluations']-evalcount-2),
                deadline=inner_deadline,gradient_tolerance=max(inner_strict,.01*(.2**outer)*D0/float(parameter_scale.max())))
            vector_to_parameters(x,params) # rollback from any rejected/truncated trial
            with torch.no_grad():
                d=field.fieldCalculation(inp)[2]
                dual=[update_inequality_multiplier(c,mu,rho) for (c,w),mu in zip(constraints(d,arm),dual)]
            cert=certify(None)
            qualified=(cert['primal_max']<=tau_c and cert['normalized_NCP_inf']<=tau_c
                       and cert['parameter_stationarity_scaled']<=tau_theta and cert['dual_min']>=0
                       and cert['precision_delta']<=config['primal_ceiling']/20)
            outer_trace.append(dict(outer=outer,rho=rho,elapsed_seconds=time.monotonic()-armstart,
                                    inner=info,certificate=cert,qualified=qualified))
            dump(folder/'outer_trace.json',outer_trace)
            if qualified: break
            if (cert['primal_max']>tau_c and cert['primal_max']>.5*previous_violation
                    and info['reason']=='gradient_tolerance'): rho=min(rho*10,rho0*1e5)
            previous_violation=cert['primal_max']
            if info['reason']=='line_search_stalled': break
        final=certify('final')
        qualified=(final['primal_max']<=tau_c and final['normalized_NCP_inf']<=tau_c
                   and final['parameter_stationarity_scaled']<=tau_theta and final['dual_min']>=0
                   and final['precision_delta']<=config['primal_ceiling']/20)
        # Field and mechanical diagnostics are independent of the parameter KKT label.
        d=field.fieldCalculation(inp)[2].detach()
        df=d.clone().requires_grad_(); uf=u.clone().requires_grad_(); vf=v.clone().requires_grad_()
        el,ed,eh=energies(df,uf,vf)
        gd,gu,gv=torch.autograd.grad(el+ed,(df,uf,vf)); evalcount+=1
        density=gd/wnode
        projected=df.detach()-torch.maximum(h,torch.minimum(torch.ones_like(h),df.detach()-density))
        free=(inp[:,1] > -.5+1e-7)&(inp[:,1] < .5-1e-7)
        final.update(physical_node_box_projected_density_inf=float(projected.abs().max()),
                     free_u_residual_l2=float(torch.cat([gu[free],gv[free]]).norm()),
                     physical_field_gradient_inf=float(gd.abs().max()))
        np.savez_compressed(folder/'diagnostics.npz',physical_damage_gradient=cpu(gd),
            projected_node_box=cpu(projected),free_u_residual=cpu(gu),free_v_residual=cpu(gv))
        torch.save(net.state_dict(),folder/'final.pt')
        elapsed=time.monotonic()-armstart
        budget_overrun=elapsed>config['arm_seconds'] or evalcount>config['max_evaluations']
        qualified=qualified and not budget_overrun
        receipt=dict(run_id=f'S04-E037-R{len(results)+1:03d}',arm=arm,initial=beginning,final=final,
            qualified_parameter_KKT=qualified,thresholds=dict(primal=tau_c,parameter_stationarity_scaled=tau_theta,NCP=tau_c),
            evaluations=evalcount,outer_updates=len(outer_trace),seconds=elapsed,budget_overrun=budget_overrun,
            stop_reason='numerical_KKT' if qualified else 'bounded_inexact_AL_unqualified',no_history_commit=True)
        dump(folder/'receipt.json',receipt)
        results.append(receipt); dump(args.output/'results.json',results)
        print(json.dumps(receipt,allow_nan=False),flush=True)
        assert torch.equal(h,ckpt['hist_alpha']) and torch.equal(histfat,ckpt['hist_fat']) and torch.equal(prevpsi,ckpt['psi_plus_prev'])
    # Reference jobs have separate identities and certificates; never same L2 objective.
    for mode in ('G','N'):
        if time.monotonic()-started+config['qp_seconds']+10 > config['total_seconds']:
            raise RuntimeError('total reference budget exhausted')
        reference=asdict(solve_t3_damage(qp,cpu(h).astype(float),mode=mode,time_limit=config['qp_seconds']))
        arrays={k:v for k,v in reference.items() if isinstance(v,np.ndarray)}
        metadata={k:v for k,v in reference.items() if not isinstance(v,np.ndarray)}
        np.savez_compressed(args.output/f'reference_{mode}.npz',**arrays)
        dump(args.output/f'reference_{mode}.json',metadata)
        print(json.dumps(dict(reference=mode,**metadata),allow_nan=False),flush=True)
    dump(args.output/'completed.json',dict(status='execution_completed',seconds=time.monotonic()-started,
        arms=len(results),total_budget_overrun=time.monotonic()-started>config['total_seconds'],
        qualified_parameter_KKT={r['arm']:r['qualified_parameter_KKT'] for r in results},
        no_history_commit=True))


if __name__=='__main__':
    main()
