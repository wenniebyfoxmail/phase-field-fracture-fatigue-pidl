"""D010: first feasible actual finite step in the saved three-axis combination."""
import argparse,json,time,resource,platform,subprocess
from pathlib import Path
import numpy as np
import torch
from threadpoolctl import threadpool_limits
from s04_e024_three_head import enrich_basis,admit_finite,uv_safe_fraction,GUARDS
from s04_e024_head_cone import elastic_driver
from s04_e024_weak_guard import Mechanics
from diagnose_s04_e023_terminal_head import scores,network_order,sha,read,write_csv,STATES
from diagnose_s04_e023_endpoints import load_endpoint
from diagnose_s04_e023_physical import observables,compare
from s04_e024_head_tail import HEAD_LOCKS
from run_s04_e024_head_tail_screen import state_digest,US
from s04_e018_global_local import compact_window


def run(a):
    source=Path(__file__).resolve().parents[1]
    commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    assert commit==a.expected_commit
    torch.set_default_dtype(torch.float64);torch.set_num_threads(2)
    start=time.perf_counter();a.out.mkdir(parents=True,exist_ok=False)
    root=a.project/'local_archive/experiments'
    old=root/'S04-E019/producer_execution_v1/raw';e021=root/'S04-E021/producer_execution_v2/raw'
    e022=root/'S04-E022/producer_execution_v1/raw';e023=root/'S04-E023/producer_execution_v1/raw'
    prior=root/'S04-E024/fullhead_feasible_v1';control=root/'S04-E024/background_guard_v1'
    assert (prior/'results/receipt.json').read_bytes()==(source/'docs/research/S04/S04-E024/fullhead_cone_receipt.json').read_bytes()
    assert (control/'results/receipt.json').read_bytes()==(source/'docs/research/S04/S04-E024/background_guard_receipt.json').read_bytes()
    manifests={p:read(p/'archive_manifest.json')['files'] for p in (prior,control)}
    prior_compute=0.
    if a.step_rule=='uv-curvature':
        first=root/'S04-E024/three_head_finite_v1/results/receipt.json'
        assert first.read_bytes()==(source/'docs/research/S04/S04-E024/three_head_r1_receipt.json').read_bytes()
        first_receipt=read(first)
        assert first_receipt['source_commit']=='a7a9305c026f23295bd2354f5cefb81e35c9e97c' and first_receipt['accepted_external_fields']==0
        prior_compute=first_receipt['wall_seconds']
    metrics=[];physical=[];trials=[];guards=[];audits=[];assets=[];derivatives=[];quadratics=[]
    for st in STATES:
        if time.perf_counter()-start+prior_compute>600:raise RuntimeError('combined compute cap')
        model,data,base,origin,asset=load_endpoint(old,e021,e022,e023,st,'E023')
        digest=state_digest(model);cp=e023/'runs'/HEAD_LOCKS[st]['run_id']
        before={str(cp/n):sha(cp/n) for n in HEAD_LOCKS[st]['files']}
        ip=prior/'results'/f'{st}_first_order.npz';ic=control/'results'/f'{st}_background_guard.npz'
        input_hashes={str(p):sha(p) for p in (ip,ic)}
        for parent,p in ((prior,ip),(control,ic)):assert sha(p)==manifests[parent][str(p.relative_to(parent))]['sha256']
        theta=np.vstack([model.residual.output_layer.weight.detach().numpy().T,model.residual.output_layer.bias.detach().numpy()[None]])
        with np.load(ip) as z:
            np.testing.assert_array_equal(theta,z['original_coefficients'])
            old_basis=z['original_basis'].copy();v=z['direction_full_common_driver'].copy()
            slopes={key.removeprefix('gradient_'):float(np.einsum('ij,ij',z[key],v)) for key in z.files if key.startswith('gradient_')}
            radius=float(z['radius']);assert radius==.02*np.linalg.norm(theta)
        with np.load(ic) as z:
            np.testing.assert_array_equal(theta,z['original_coefficients']);d008=z['uv'].copy()
        assert all(slopes[key]<0 for key in ('uv_full','uv_damage','weak','uv_background','driver_background','driver_inside_background'))
        basis,coordinates,realised,geometry=enrich_basis(old_basis,v)
        mech=Mechanics(data['xy'],data['conn'],data['damage'],origin)
        ref=observables(data,data['equilibrated_uv']);native_origin=observables(data,origin)
        with torch.no_grad():window=compact_window(torch.tensor(data['xy']),model.lower,model.upper).numpy()[:,0]
        w=data['mass']/data['mass'].sum();bg=data['damage']<=.1
        node_masks=dict(full=np.ones(len(w),bool),damage=~bg,background=bg,inside_background=bg&(window>0))
        weights={key:w*mask/np.sum(w*mask) for key,mask in node_masks.items()}
        gd=ref['gp_damage']>.1;dist=np.maximum(model.lower.numpy()-ref['gp_xy'],ref['gp_xy']-model.upper.numpy())
        gp_masks=dict(full=np.ones_like(gd),damage=gd,background=~gd,inside_background=(~gd)&(dist<.02).all(2))
        pref=elastic_driver(mech,data['equilibrated_uv'],ref['gp_damage'])[0]
        np.testing.assert_allclose(pref,ref['elastic_damage_driver'],rtol=1e-10,atol=1e-12)

        def actual_values(uv):
            err=((uv-data['equilibrated_uv'])/abs(US))**2
            vals={'uv_'+key:float(np.sum(wt[:,None]*err)) for key,wt in weights.items()}
            vals['weak_squared']=float(np.sum(mech.dual(mech.force(uv))**2))
            p=elastic_driver(mech,uv,ref['gp_damage'])[0]
            vals.update({'driver_'+key:float(np.sum(ref['weights']*gp_masks[key]*(p-pref)**2)) for key in ('background','inside_background')})
            if not np.isfinite(list(vals.values())).all():raise ValueError('nonfinite actual score')
            return vals

        origin_values=actual_values(origin);assert min(origin_values.values())>0
        velocity=radius*network_order(model,data['xy'],np.zeros_like(base),realised,1024)
        seed=1.
        if a.step_rule=='uv-curvature':
            seed,terms=uv_safe_fraction((origin-data['equilibrated_uv'])/abs(US),velocity/abs(US),weights)
            for region,values in terms.items():quadratics.append(dict(state=st,region=region,seed_fraction=seed,**values))
        accepted=False;chosen=theta.copy();uv=origin.copy();fraction=0.;accepted_k=None
        for k in range(9):
            t=seed*2.**(-k);coef=theta+radius*t*realised
            candidate=network_order(model,data['xy'],base,coef,1024)
            np.testing.assert_array_equal(candidate[window==0],origin[window==0])
            bc=(data['xy'][:,1]==-.5)|(data['xy'][:,1]==.5)
            np.testing.assert_array_equal(candidate[bc],origin[bc])
            vals=actual_values(candidate);delta_relative=float(np.linalg.norm(coef-theta)/np.linalg.norm(theta))
            ok,reasons=admit_finite(vals,origin_values,delta_relative)
            branch=float(np.mean((mech.strains(candidate)[...,:2].sum(2)>=0)!=mech.branches))
            for key in GUARDS:
                gap=vals[key]-origin_values[key];ratio=vals[key]/origin_values[key]
                trials.append(dict(state=st,k=k,seed_fraction=seed,fraction=t,guard=key,origin=origin_values[key],candidate=vals[key],difference=gap,ratio=ratio,
                    rejected=bool(vals[key]>origin_values[key]),increase_scale='numerical-scale' if 0<ratio-1<=1e-12 else ('resolved_increase' if ratio>1 else 'no_increase'),
                    trial_accepted=ok,rejected_names=';'.join(reasons),delta_relative=delta_relative,branch_changed_gp_fraction=branch))
            if ok:accepted=True;chosen=coef;uv=candidate;fraction=t;accepted_k=k;break
        final_values=actual_values(uv)
        final_ok,why=admit_finite(final_values,origin_values,float(np.linalg.norm(chosen-theta)/np.linalg.norm(theta)))
        assert final_ok,why
        for arm,field in [('E023',origin),('D008',d008),('three_head',uv)]:
            value=actual_values(field)
            for key in GUARDS:guards.append(dict(state=st,arm=arm,guard=key,value=value[key],own_E023=origin_values[key],ratio=value[key]/origin_values[key]))
            metrics.append(dict(state=st,arm=arm,**scores(field,data,window)))
            ob=observables(data,field)
            scale=abs(US)/data['energy_scale'];np.testing.assert_allclose(ob['rho_u'],scale*np.sqrt(value['weak_squared']),rtol=1e-12)
            pd=elastic_driver(mech,field,ref['gp_damage'])[0]
            np.testing.assert_allclose(pd,ob['elastic_damage_driver'],rtol=1e-10,atol=1e-12)
            for region,mask in gp_masks.items():
                physical.append(dict(state=st,arm=arm,region=region,strain_error=compare(ob,ref,mask,'strain'),elastic_driver_error=compare(ob,ref,mask,'elastic_damage_driver'),active_energy_error=compare(ob,ref,mask,'active_energy'),rho_u=ob['rho_u']))
        for quantity,slope in slopes.items():
            if quantity.startswith('uv_'):
                get=lambda arm:next(row[quantity[3:]] for row in metrics if row['state']==st and row['arm']==arm)
            elif quantity=='weak':
                get=lambda arm:next(row['rho_u'] for row in physical if row['state']==st and row['arm']==arm and row['region']=='full')
            else:
                get=lambda arm:next(row['elastic_driver_error'] for row in physical if row['state']==st and row['arm']==arm and row['region']==quantity[7:])
            derivatives.append(dict(state=st,quantity=quantity,relative_rms_derivative=slope,fraction=fraction,first_order_percent=100*fraction*slope,actual_percent=100*(get('three_head')/get('E023')-1)))
        affinity=origin+fraction*velocity
        affine_gap=float(np.max(abs(uv-affinity)));assert affine_gap<=1e-12
        np.testing.assert_array_equal(uv[window==0],origin[window==0])
        audits.append(dict(state=st,dimension=3,step_rule=a.step_rule,seed_fraction=seed,accepted=accepted,accepted_k=accepted_k,accepted_fraction=fraction,visited_candidates=k+1,
            radius=radius,delta_relative=float(np.linalg.norm(chosen-theta)/np.linalg.norm(theta)),affine_max_abs=affine_gap,outside_max_abs=0.,bc_max_abs=0.,
            branch_changed_gp_fraction=float(np.mean((mech.strains(uv)[...,:2].sum(2)>=0)!=mech.branches)),coordinates=coordinates.tolist(),**geometry))
        np.savez_compressed(a.out/f'{st}_three_head.npz',uv=uv,head_coefficients=chosen,original_coefficients=theta,delta=chosen-theta,
            original_basis=old_basis,basis=basis,coordinates=coordinates,verified_direction=v,realised_direction=realised,accepted_fraction=fraction)
        assert digest==state_digest(model) and all(p.grad is None for p in model.parameters())
        assert all(sha(Path(p))==h for p,h in before.items()) and all(sha(Path(p))==h for p,h in input_hashes.items())
        assets.append(dict(**asset,original_file_hashes=before,input_hashes=input_hashes,model_digest=digest))
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024)
        if peak>3*1024**3 or time.perf_counter()-start+prior_compute>600:raise RuntimeError('resource cap')
        print(st,audits[-1],flush=True)
        del model,mech
    for name,rows in [('uv_metrics.csv',metrics),('physical_metrics.csv',physical),('line_search.csv',trials),('guard_values.csv',guards),('first_order_comparison.csv',derivatives)]:write_csv(a.out/name,rows)
    if quadratics:write_csv(a.out/'uv_quadratics.csv',quadratics)
    (a.out/'numerics.json').write_text(json.dumps(audits,indent=2)+'\n')
    (a.out/'receipt.json').write_text(json.dumps(dict(source_commit=commit,states=list(STATES),assets=assets,wall_seconds=time.perf_counter()-start,peak_rss_bytes=int(peak),
        step_rule=a.step_rule,prior_r1_compute_seconds=prior_compute,combined_compute_seconds=prior_compute+time.perf_counter()-start,
        parameter_radius_fraction=.02,accepted_external_fields=sum(row['accepted'] for row in audits),neural_optimizer_steps=0,new_direction_solves=0,three_dimensional_optimisations=0,
        original_checkpoint_writes=0,history_fatigue_damage_updates=0,remote_actions=0,scope='first feasible finite step along verified combination in one-axis enriched3D; not3Doptimum or coupled evolution'),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--expected-commit',required=True);p.add_argument('--step-rule',choices=('budget','uv-curvature'),default='budget')
    with threadpool_limits(limits=2):run(p.parse_args())
