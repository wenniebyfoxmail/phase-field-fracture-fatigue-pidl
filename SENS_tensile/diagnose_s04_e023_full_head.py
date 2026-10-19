"""D012: complete fixed-output-head reachability with unchanged true-field guards."""
import argparse,json,time,resource,platform,subprocess
from pathlib import Path
import numpy as np
import torch
from threadpoolctl import threadpool_limits
from s04_e024_three_head import admit_finite,GUARDS
from s04_e024_joint_head import write_trials
from s04_e024_full_head import build_proxies,solve_full
from s04_e023_head_scale import physical_features
from scipy.linalg.blas import dgemm
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
    previous=root/'S04-E024/joint_head_curvature_v1'
    assert (previous/'results/receipt.json').read_bytes()==(source/'docs/research/S04/S04-E024/joint_head_receipt.json').read_bytes()
    pin=read(source/'docs/research/S04/S04-E024/joint_head_archive.json')
    assert sha(previous/'archive_manifest.json')==pin['manifest_sha256']
    manifest=read(previous/'archive_manifest.json')['files']
    metrics=[];physical=[];trials=[];guards=[];audits=[];assets=[];solver_traces={}
    for st in STATES:
        if time.perf_counter()-start>900:raise RuntimeError('compute cap')
        model,data,base,origin,asset=load_endpoint(old,e021,e022,e023,st,'E023')
        digest=state_digest(model);cp=e023/'runs'/HEAD_LOCKS[st]['run_id']
        before={str(cp/n):sha(cp/n) for n in HEAD_LOCKS[st]['files']}
        ip=previous/'results'/f'{st}_joint_head.npz'
        input_hashes={str(ip):sha(ip)}
        assert sha(ip)==manifest[str(ip.relative_to(previous))]['sha256']
        theta=np.vstack([model.residual.output_layer.weight.detach().numpy().T,model.residual.output_layer.bias.detach().numpy()[None]])
        with np.load(ip) as z:
            np.testing.assert_array_equal(theta,z['original_coefficients'])
            basis=z['basis'].copy();d011=z['uv'].copy();previous_z=z['accepted_z'].copy()
            old_g=z['quadratic_gradients'].copy();old_h=z['quadratic_hessians'].copy()
        assert basis.shape==(3,)+theta.shape
        np.testing.assert_allclose(np.einsum('ijk,ljk->il',basis,basis),np.eye(3),rtol=0,atol=1e-12)
        radius=.02*np.linalg.norm(theta)
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
        phi=[]
        with torch.no_grad():
            for offset in range(0,len(origin),1024):
                phi.append((physical_features(model,torch.tensor(data['xy'][offset:offset+1024]))*model.head_scale).numpy())
        phi=np.concatenate(phi)
        p0,stress=elastic_driver(mech,origin,ref['gp_damage'])
        basis_flat=basis.reshape(3,-1)
        info=dict(US=US,origin_force=mech.force(origin),basis_flat=basis_flat,weights=ref['weights'],
            driver_reference=pref,driver_masks=[gp_masks[key] for key in ('background','inside_background')])
        cc,gg,hh,operator=build_proxies(phi,(origin-data['equilibrated_uv'])/abs(US),weights,mech,info,radius*abs(US),p0,stress)
        np.testing.assert_allclose(cc,np.array([origin_values[x] for x in GUARDS]),rtol=1e-12,atol=0)
        projected_g=np.einsum('ki,ji->kj',gg,basis_flat)
        projected_h=np.einsum('ai,kij,bj->kab',basis_flat,hh,basis_flat)
        np.testing.assert_allclose(projected_g,old_g,rtol=1e-8,atol=1e-8)
        np.testing.assert_allclose(projected_h,old_h,rtol=1e-8,atol=1e-8)
        projection=dict(gradient_max_abs=float(abs(projected_g-old_g).max()),hessian_max_abs=float(abs(projected_h-old_h).max()))
        full_z,raw_z,solve,trace=solve_full(gg,hh);solver_traces[st]=trace
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024)>3*1024**3 or time.perf_counter()-start>900:
            raise RuntimeError('full proxy build/solve resource cap')
        accepted=False;chosen=theta.copy();uv=origin.copy();fraction=0.;accepted_k=None
        visited=0;k=-1
        for k in (range(9) if solve['feasible'] else []):
            visited+=1
            t=2.**(-k);coef=theta+radius*t*full_z.reshape(theta.shape)
            candidate=network_order(model,data['xy'],base,coef,1024)
            np.testing.assert_array_equal(candidate[window==0],origin[window==0])
            bc=(data['xy'][:,1]==-.5)|(data['xy'][:,1]==.5)
            np.testing.assert_array_equal(candidate[bc],origin[bc])
            vals=actual_values(candidate);delta_relative=float(np.linalg.norm(coef-theta)/np.linalg.norm(theta))
            ok,reasons=admit_finite(vals,origin_values,delta_relative)
            branch=float(np.mean((mech.strains(candidate)[...,:2].sum(2)>=0)!=mech.branches))
            for key in GUARDS:
                gap=vals[key]-origin_values[key];ratio=vals[key]/origin_values[key]
                trials.append(dict(state=st,k=k,fraction=t,guard=key,origin=origin_values[key],candidate=vals[key],difference=gap,ratio=ratio,
                    rejected=bool(vals[key]>origin_values[key]),increase_scale='numerical-scale' if 0<ratio-1<=1e-12 else ('resolved_increase' if ratio>1 else 'no_increase'),
                    trial_accepted=ok,rejected_names=';'.join(reasons),delta_relative=delta_relative,branch_changed_gp_fraction=branch))
            if ok:accepted=True;chosen=coef;uv=candidate;fraction=t;accepted_k=k;break
        final_values=actual_values(uv)
        final_ok,why=admit_finite(final_values,origin_values,float(np.linalg.norm(chosen-theta)/np.linalg.norm(theta)))
        assert final_ok,why
        for arm,field in [('E023',origin),('D011',d011),('full_head',uv)]:
            value=actual_values(field)
            for key in GUARDS:guards.append(dict(state=st,arm=arm,guard=key,value=value[key],own_E023=origin_values[key],ratio=value[key]/origin_values[key]))
            metrics.append(dict(state=st,arm=arm,**scores(field,data,window)))
            ob=observables(data,field)
            scale=abs(US)/data['energy_scale'];np.testing.assert_allclose(ob['rho_u'],scale*np.sqrt(value['weak_squared']),rtol=1e-12)
            pd=elastic_driver(mech,field,ref['gp_damage'])[0]
            np.testing.assert_allclose(pd,ob['elastic_damage_driver'],rtol=1e-10,atol=1e-12)
            for region,mask in gp_masks.items():
                physical.append(dict(state=st,arm=arm,region=region,strain_error=compare(ob,ref,mask,'strain'),elastic_driver_error=compare(ob,ref,mask,'elastic_damage_driver'),active_energy_error=compare(ob,ref,mask,'active_energy'),rho_u=ob['rho_u']))
        affinity=origin+radius*abs(US)*dgemm(1.,np.asarray(phi,order='F'),(fraction*full_z).reshape(theta.shape))
        affine_gap=float(np.max(abs(uv-affinity)));assert affine_gap<=1e-12
        np.testing.assert_array_equal(uv[window==0],origin[window==0])
        audits.append(dict(state=st,dimension=theta.size,accepted=accepted,accepted_k=accepted_k,accepted_fraction=fraction,visited_candidates=visited,
            radius=radius,delta_relative=float(np.linalg.norm(chosen-theta)/np.linalg.norm(theta)),affine_max_abs=affine_gap,outside_max_abs=0.,bc_max_abs=0.,
            branch_changed_gp_fraction=float(np.mean((mech.strains(uv)[...,:2].sum(2)>=0)!=mech.branches)),full_z_norm=float(np.linalg.norm(full_z)),
            outside_old3D_norm_fraction=float(np.linalg.norm(full_z-np.einsum('i,ij->j',np.einsum('ij,j->i',basis_flat,full_z),basis_flat))/max(np.linalg.norm(full_z),1e-300)),
            operator=operator,D011_projection=projection,solver=solve))
        np.savez_compressed(a.out/f'{st}_full_head.npz',uv=uv,head_coefficients=chosen,original_coefficients=theta,delta=chosen-theta,
            original_basis=basis,full_z=full_z,raw_z=raw_z,accepted_z=fraction*full_z,previous_3D_z=previous_z,
            quadratic_constants=cc,quadratic_gradients=gg,quadratic_hessians=hh,accepted_fraction=fraction)
        assert digest==state_digest(model) and all(p.grad is None for p in model.parameters())
        assert all(sha(Path(p))==h for p,h in before.items()) and all(sha(Path(p))==h for p,h in input_hashes.items())
        assets.append(dict(**asset,original_file_hashes=before,input_hashes=input_hashes,model_digest=digest))
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024)
        if peak>3*1024**3 or time.perf_counter()-start>900:raise RuntimeError('resource cap')
        print(st,audits[-1],flush=True)
        del model,mech,phi,info,hh
    for name,rows in [('uv_metrics.csv',metrics),('physical_metrics.csv',physical),('guard_values.csv',guards)]:write_csv(a.out/name,rows)
    write_trials(a.out/'line_search.csv',trials)
    (a.out/'solver_trace.json').write_text(json.dumps(solver_traces,indent=2)+'\n')
    (a.out/'numerics.json').write_text(json.dumps(audits,indent=2)+'\n')
    (a.out/'receipt.json').write_text(json.dumps(dict(source_commit=commit,states=list(STATES),assets=assets,wall_seconds=time.perf_counter()-start,peak_rss_bytes=int(peak),
        parameter_radius_fraction=.02,accepted_external_fields=sum(row['accepted'] for row in audits),neural_optimizer_steps=0,new_direction_solves=0,offline_full_head_solves=3,
        original_checkpoint_writes=0,history_fatigue_damage_updates=0,remote_actions=0,scope='complete fixed-head convex proxy plus true finite seven-guard witness; not nonlinear/evolution ceiling'),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--expected-commit',required=True)
    with threadpool_limits(limits=2):run(p.parse_args())
