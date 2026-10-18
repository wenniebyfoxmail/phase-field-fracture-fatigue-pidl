"""D009: full-head first-order geometry and driver sensitivity; no correction."""
import argparse, json, time, resource, platform, subprocess
from pathlib import Path
import numpy as np
import torch
from threadpoolctl import threadpool_limits
from s04_e024_head_cone import cone_projection, common_descent, strain_adjoint, elastic_driver
from s04_e024_weak_guard import Mechanics
from s04_e024_centered_trust_region import product
from s04_e023_head_scale import physical_features
from diagnose_s04_e023_terminal_head import sha, read, write_csv, STATES
from diagnose_s04_e023_endpoints import load_endpoint
from diagnose_s04_e023_physical import observables
from s04_e024_head_tail import HEAD_LOCKS
from run_s04_e024_head_tail_screen import state_digest, US
from s04_e018_global_local import compact_window


def run(a):
    source = Path(__file__).resolve().parents[1]
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    assert commit == a.expected_commit
    torch.set_default_dtype(torch.float64); torch.set_num_threads(2)
    start = time.perf_counter(); a.out.mkdir(parents=True, exist_ok=False)
    root = a.project / 'local_archive/experiments'
    old = root/'S04-E019/producer_execution_v1/raw'
    e021 = root/'S04-E021/producer_execution_v2/raw'
    e022 = root/'S04-E022/producer_execution_v1/raw'
    e023 = root/'S04-E023/producer_execution_v1/raw'
    d007 = root/'S04-E024/weak_guard_v1'
    assert (d007/'results/receipt.json').read_bytes() == (source/'docs/research/S04/S04-E024/weak_guard_receipt.json').read_bytes()
    oldmanifest = read(d007/'archive_manifest.json')['files']
    gradients_rows, slopes_rows, cone_rows, fd_rows, baseline_rows, audits, assets = [], [], [], [], [], [], []
    for st in STATES:
        if time.perf_counter()-start > 600: raise RuntimeError('wall budget')
        model, data, base, origin, asset = load_endpoint(old, e021, e022, e023, st, 'E023')
        digest = state_digest(model)
        cp = e023/'runs'/HEAD_LOCKS[st]['run_id']
        before = {str(cp/n):sha(cp/n) for n in HEAD_LOCKS[st]['files']}
        inp = d007/'results'/f'{st}_weak_guard.npz'
        assert sha(inp) == oldmanifest[str(inp.relative_to(d007))]['sha256']
        theta = np.vstack([model.residual.output_layer.weight.detach().numpy().T,
                           model.residual.output_layer.bias.detach().numpy()[None]])
        with np.load(inp) as z:
            basis = z['basis'].copy(); np.testing.assert_array_equal(z['original_coefficients'], theta)
        radius = .02*np.linalg.norm(theta)
        features = []
        with torch.no_grad():
            for k in range(0, len(origin), 1024):
                features.append((physical_features(model, torch.tensor(data['xy'][k:k+1024])) * model.head_scale).numpy())
            window = compact_window(torch.tensor(data['xy']), model.lower, model.upper).numpy()[:,0]
        phi = np.concatenate(features); del features
        affine_gap = float(np.max(abs(base+abs(US)*product(phi,theta)-origin)))
        assert affine_gap <= 1e-12 and np.count_nonzero(phi[window==0]) == 0
        mech = Mechanics(data['xy'], data['conn'], data['damage'], origin)
        force = mech.force(origin); f2 = float(np.sum(mech.dual(force)**2))
        adj = np.zeros_like(origin); adj[mech.free] = force[mech.free]/mech.mass[mech.free,None]
        grads = dict(weak=radius*abs(US)*product(phi, mech.force(adj,tangent=True), True)/f2)
        w = data['mass']/data['mass'].sum(); error = (origin-data['equilibrated_uv'])/abs(US)
        bg = data['damage']<=.1
        nodal_masks = dict(full=np.ones(len(w),bool),damage=~bg,background=bg,inside_background=bg&(window>0))
        uv_denoms = {}
        for region,mask in nodal_masks.items():
            wr = w*mask; wr /= wr.sum(); denom = float(np.sum(wr[:,None]*error**2)); assert denom>0
            uv_denoms[region] = (wr,denom)
            grads['uv_'+region] = radius*product(phi,wr[:,None]*error,True)/denom
            baseline_rows.append(dict(state=st,quantity='uv',region=region,value=float(np.sqrt(denom)),reference_rms=None,error_conditional_rms=float(np.sqrt(denom))))
        ob = observables(data,origin); ref = observables(data,data['equilibrated_uv'])
        np.testing.assert_allclose(mech.mass, ob['mass'], rtol=1e-12, atol=1e-16)
        scale = abs(US)/data['energy_scale']
        np.testing.assert_allclose(scale*np.sqrt(f2),ob['rho_u'],rtol=1e-12)
        baseline_rows.append(dict(state=st,quantity='weak',region='full',value=ob['rho_u'],reference_rms=ref['rho_u'],error_conditional_rms=None))
        pd, dp_deps = elastic_driver(mech,origin,ob['gp_damage'])
        pref = elastic_driver(mech,data['equilibrated_uv'],ref['gp_damage'])[0]
        np.testing.assert_allclose(pd,ob['elastic_damage_driver'],rtol=1e-10,atol=1e-12)
        np.testing.assert_allclose(pref,ref['elastic_damage_driver'],rtol=1e-10,atol=1e-12)
        gd = ob['gp_damage']>.1
        dist = np.maximum(model.lower.numpy()-ob['gp_xy'],ob['gp_xy']-model.upper.numpy())
        gp_masks = dict(full=np.ones_like(gd),damage=gd,background=~gd,inside_background=(~gd)&(dist<.02).all(2))
        driver_denoms = {}
        for region,mask in gp_masks.items():
            weights = ob['weights']*mask; err = pd-pref
            denom = float(np.sum(weights*err**2)); ref2 = float(np.sum(weights*pref**2)); assert min(denom,ref2)>0
            # strain_adjoint integrates det; do not multiply det a second time.
            stress = mask[...,None]*err[...,None]*dp_deps/denom
            grads['driver_'+region] = radius*abs(US)*product(phi,strain_adjoint(mech,stress),True)
            driver_denoms[region] = (weights,denom)
            baseline_rows.append(dict(state=st,quantity='elastic_driver_error',region=region,value=float(np.sqrt(denom/ref2)),reference_rms=float(np.sqrt(ref2/weights.sum())),error_conditional_rms=float(np.sqrt(denom/weights.sum()))))
        flat = {key:value.ravel() for key,value in grads.items()}
        assert all(np.isfinite(g).all() for g in flat.values())
        bb = basis.reshape(2,-1); np.testing.assert_allclose(bb@bb.T,np.eye(2),rtol=0,atol=1e-12)
        primary_guards = np.stack([flat['weak'],flat['uv_background']])
        old_v, old_p, old_info = cone_projection(bb@flat['uv_full'],primary_guards@bb.T)
        full_v, full_p, full_info = cone_projection(flat['uv_full'],primary_guards)
        main = np.stack([flat['uv_full'],*primary_guards])
        strict_v, strict_q, strict_info = common_descent(main)
        driver_normals = np.stack([*main,flat['driver_background'],flat['driver_inside_background']])
        driver_v, driver_q, driver_info = common_descent(driver_normals)
        directions = dict(unconstrained=-flat['uv_full']/np.linalg.norm(flat['uv_full']),
                          old_plane=old_v@bb,full_projected=full_v,full_common=strict_v,full_common_driver=driver_v)
        infos = dict(old_plane=old_info,full_projected=full_info,full_common=strict_info,full_common_driver=driver_info)
        singular = np.linalg.svd(driver_normals/np.linalg.norm(driver_normals,axis=1)[:,None],compute_uv=False)
        for key,g in flat.items(): gradients_rows.append(dict(state=st,quantity=key,gradient_norm=float(np.linalg.norm(g)),old_plane_norm=float(np.linalg.norm(bb@g)),old_plane_fraction=float(np.linalg.norm(bb@g)/np.linalg.norm(g))))
        for name,info in infos.items():
            cone_rows.append(dict(state=st,direction=name,details=json.dumps(info)))
        for name,v in directions.items():
            assert np.linalg.norm(v)<=1+1e-12
            for key,g in flat.items(): slopes_rows.append(dict(state=st,direction=name,quantity=key,relative_rms_derivative=float(np.dot(g,v)),unit_gradient_derivative=float(np.dot(g,v)/np.linalg.norm(g))))
        # Fixed infinitesimal field probes verify derivatives, never accept a finite correction.
        trace = mech.strains(origin)[...,:2].sum(2)
        def values(uv):
            ee = ((uv-data['equilibrated_uv'])/abs(US))**2
            out = {'uv_'+r:.5*float(np.sum(wr[:,None]*ee))/d for r,(wr,d) in uv_denoms.items()}
            out['weak'] = .5*float(np.sum(mech.dual(mech.force(uv))**2))/f2
            pp = elastic_driver(mech,uv,ob['gp_damage'])[0]
            out.update({'driver_'+r:.5*float(np.sum(wr*(pp-pref)**2))/d for r,(wr,d) in driver_denoms.items()})
            out['_branch_changed_fraction'] = float(np.mean((mech.strains(uv)[...,:2].sum(2)>=0)!=(trace>=0)))
            return out
        for name in ('unconstrained','full_projected','full_common','full_common_driver'):
            v = directions[name]
            if np.linalg.norm(v)==0: continue
            velocity = radius*abs(US)*product(phi,v.reshape(theta.shape))
            assert np.count_nonzero(velocity[window==0])==0
            zero_touched = int(np.count_nonzero((trace==0)&(mech.strains(velocity)[...,:2].sum(2)!=0)))
            if zero_touched: raise ValueError('origin trace kink touched: classical weak gradient unresolved')
            for eps in (1e-4,1e-5,1e-6):
                plus,minus = values(origin+eps*velocity),values(origin-eps*velocity)
                for key,g in flat.items():
                    predicted = float(np.dot(g,v)); fd = (plus[key]-minus[key])/(2*eps)
                    good = abs(fd-predicted)<=1e-6+1e-3*abs(predicted)
                    fd_rows.append(dict(state=st,direction=name,quantity=key,epsilon=eps,predicted=predicted,central_difference=fd,absolute_gap=abs(fd-predicted),smallest_epsilon_pass=good if eps==1e-6 else None,
                        forward_difference=(plus[key]-.5)/eps,backward_difference=(.5-minus[key])/eps,plus_branch_change_fraction=plus['_branch_changed_fraction'],minus_branch_change_fraction=minus['_branch_changed_fraction'],origin_trace_zero_touched=zero_touched))
                    if eps==1e-6 and not good: raise ValueError('directional derivative unresolved: '+st+' '+name+' '+key)
        audits.append(dict(state=st,head_shape=list(theta.shape),parameter_dimension=int(theta.size),radius=float(radius),radius_fraction=.02,
                           affine_max_abs=affine_gap,trace_zero_gp=int(np.count_nonzero(trace==0)),min_abs_trace=float(np.min(abs(trace))),
                           driver_normal_singular_values=singular.tolist(),gradient_span_rank=int(np.count_nonzero(singular>np.finfo(float).eps*max(driver_normals.shape)*singular[0])),
                           old_plane=old_info,full_projected=full_info,full_common=strict_info,full_common_driver=driver_info))
        np.savez_compressed(a.out/f'{st}_first_order.npz',original_coefficients=theta,original_basis=basis,radius=radius,
                            **{'gradient_'+key:value for key,value in grads.items()},**{'direction_'+key:v.reshape(theta.shape) for key,v in directions.items()},
                            old_projection=old_p,full_projection=full_p,common_hull=strict_q,driver_hull=driver_q)
        assert digest==state_digest(model) and all(p.grad is None for p in model.parameters())
        assert all(sha(Path(path))==h for path,h in before.items()) and sha(inp)==oldmanifest[str(inp.relative_to(d007))]['sha256']
        assets.append(dict(**asset,original_file_hashes=before,direction_input_sha256=sha(inp),model_digest=digest))
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024)
        if peak>3*1024**3 or time.perf_counter()-start>600: raise RuntimeError('diagnostic resource cap')
        print(st,'full retained',full_info['retained_descent_fraction'],'common margin',strict_info['unit_gradient_margin'],'driver margin',driver_info['unit_gradient_margin'],flush=True)
        del phi,model,mech
    for name,rows in [('gradients.csv',gradients_rows),('directional_slopes.csv',slopes_rows),('cone_geometry.csv',cone_rows),('finite_differences.csv',fd_rows),('baseline.csv',baseline_rows)]: write_csv(a.out/name,rows)
    (a.out/'numerics.json').write_text(json.dumps(audits,indent=2)+'\n')
    (a.out/'receipt.json').write_text(json.dumps(dict(source_commit=commit,states=list(STATES),assets=assets,wall_seconds=time.perf_counter()-start,peak_rss_bytes=int(peak),
        parameter_radius_fraction=.02,neural_optimizer_steps=0,checkpoint_writes=0,accepted_corrections=0,history_fatigue_damage_updates=0,remote_actions=0,
        scope='infinitesimal fullhead/old-plane geometry and instantaneous elastic-driver sensitivity; no finite-step or evolution claim'),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--expected-commit',required=True)
    with threadpool_limits(limits=2):run(p.parse_args())
