"""One fixed-damage UV-head correction with prospective common-descent guards."""
import argparse
import csv
import json
import os
from pathlib import Path
import platform
import resource
import signal
import subprocess
import sys
import time
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
import s04_e027 as old
import s04_e028 as scored
import s04_e033 as m
from run_s04_e027 import initializer_compatibility,deadline_signal
from run_s04_e028 import device_admission
LOCK=ROOT/'docs/research/S04/S04-E033/data_lock.json'
dump=lambda p,v:p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')


def admit(lock,grant,out):
    if platform.system()=='Darwin':raise PermissionError('Mac training prohibited')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True) or head!=grant.get('approved_commit'):raise PermissionError('clean exact source required')
    if lock['protocol']!=m.PROTOCOL or grant.get('protocol')!=m.PROTOCOL:raise PermissionError('protocol mismatch')
    if grant.get('execution_authorized') is not True or not grant.get('review_reference') or not grant.get('human_approval_reference'):raise PermissionError('authorization/review references required')
    if (grant.get('gpu_hours_cap'),grant.get('ram_gib_cap'),grant.get('output_gib_cap'))!=(.5,32,2):raise PermissionError('budget mismatch')
    if grant.get('hostname')!=platform.node() or grant.get('output')!=str(out.resolve()):raise PermissionError('host/output mismatch')
    uuid=device_admission(grant)
    if out.exists():raise FileExistsError('fresh output required; no retry')
    return head,uuid


def render(p,pred,scores,trials,out,receipt):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    polygons=p.xy[p.conn].cpu().numpy();display={}
    with torch.no_grad():
        for key,value in pred.items():
            q=torch.as_tensor(value,device=p.xy.device,dtype=torch.float64);parts=p.parts(*q.unbind(1))
            gp=[old.q4_interpolate(q[:,j],p.conn,p.N) for j in range(3)]+[parts[3],parts[4]]
            display[key]=[((v*p.w).sum(1)/p.w.sum(1)).cpu().numpy() for v in gp]
    for errors,stem in [(False,'fields'),(True,'errors')]:
        names=list(pred)[1:] if errors else list(pred)
        fig,axes=plt.subplots(5,len(names),figsize=(3.3*len(names),14),squeeze=False,layout='constrained')
        for j,label in enumerate(['u','v','d','raw','active']):
            vals=[display[k][j]-display['reference'][j] if errors else display[k][j] for k in names]
            if errors:hi=max(float(abs(v).max()) for v in vals) or 1e-30;lo=-hi
            else:lo=min(float(v.min()) for v in vals);hi=max(float(v.max()) for v in vals)
            for ax,key,val in zip(axes[j],names,vals):
                artist=PolyCollection(polygons,array=val,cmap='RdBu_r' if errors else 'viridis',edgecolors='none',antialiased=False)
                artist.set_clim(lo,hi);ax.add_collection(artist);ax.autoscale_view();ax.set_aspect('equal');ax.set(title=f'{label}: {key}'+('-FEM' if errors else ''),xlabel='x',ylabel='y')
            fig.colorbar(artist,ax=list(axes[j]),shrink=.8)
        fig.suptitle('E033 | full-head diagnostic / conditional one-axis correction | exposed c20s4 / horizon0 / seed1')
        fig.savefig(out/f'{stem}.png',dpi=130);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4.8),layout='constrained')
    for key in m.METRICS:
        ax.plot([0]+[r['index'] for r in trials],[1]+[r['ratios'][key] for r in trials],marker='o',label=key)
    ax.axhline(1,c='#999999',ls=':');ax.set(xlabel='proposed finite-head candidate, not optimizer time',ylabel='squared metric / own zero',title='All visited candidate values; first admitted only');ax.legend(ncol=4,fontsize=8)
    fig.savefig(out/'candidates.png',dpi=160);plt.close(fig)
    for stem in ['fields','errors','candidates']:
        guide={'fields':'Rows physical u/v/d, native raw and active; columns FEM reference, old E030 zero, E030, E031, E032 (own start), conditional one-axis endpoint. Common unclipped scale per row; native Q4 Jacobian-weighted element means.',
               'errors':'Same five rows, prediction minus exact FEM, one symmetric signed scale per row. Damage error columns E030_R, E031_R, E032_R and endpoint must be identical.',
               'candidates':'All visited candidates on the one joint-proxy proposal and predeclared halving rule. Lines are squared metrics divided by own start, not physical time or optimizer updates. First admitted candidate only; no selected best state. Reference ratio1 marks no change.'}[stem]
        (out/f'{stem}.md').write_text(f'''# How to read {stem}.png
\n## Figure question
Does full802 head geometry justify one extra axis, and can its correction improve FEM UV/raw while preserving fixed E030 damage, active and force costs?
\n## Data provenance
Run {out.parent.name}, exact source {receipt['commit']}, protocol {m.PROTOCOL}. fields.npz/scores.json/trials.json and locked four MATs. Source SENS_tensile/run_s04_e033.py. Exposed synthetic c20s4 / horizon0 / seed1; physical d is actual E030 endpoint, UV starts from actual E032 accepted endpoint with original S1500 hidden features. No algebraic FEM-UV substitution is included as an actual method.
\n## Visual grammar and panel guide
{guide}
\n## Key numerical takeaway
{json.dumps(scores['decision'])}. See metrics.csv for all global/Z primitive/driver/force/constraint values; original E030 zero keeps the earlier global cost visible. Parameter direction certificate is only first order; actual finite admission decides. All archived visited candidates retained.
\n## Limitations and claim boundary
One exposed synthetic state, a diagnostic with at most one conditional finite head correction, not full training/physical evolution or generalization. The full-head certificate is first order at one endpoint; no nonlinear capacity or FEM-truth claim. A no-axis result is diagnostic-only, with exact original fields and no correction. Tiny head changes can look unchanged; scalar magnitudes must accompany shared-scale images. No inferred crack width. Native scoring uses GP4 Z while image values are element means. If no candidate admitted, endpoint is exactly own start and is not scientific improvement.
''')


def run(lock,grant,out):
    head,uuid=admit(lock,grant,out);free,total=torch.cuda.mem_get_info()
    if free<20*1024**3:raise MemoryError('20GiB initial free required')
    cap=free-1024**3;torch.cuda.set_per_process_memory_fraction(cap/total,0)
    started=time.monotonic();out.mkdir(parents=True);diagnostic_phase=True;signal.signal(signal.SIGALRM,deadline_signal);signal.alarm(900)
    receipt=dict(protocol=m.PROTOCOL,commit=head,execution='preflight',host=platform.node(),pid=os.getpid(),gpu_uuid=uuid,gpu=torch.cuda.get_device_name(0),cuda_visible_devices=os.environ['CUDA_VISIBLE_DEVICES'],command=sys.argv,optimizer_steps=0,accepted_head_updates=0,head_candidate_evals=0,metric_gradient_evals=0,history_commits=0,retry=False,source_dirty=False,cuda_cap_bytes=cap)
    def guard():
        torch.cuda.synchronize()
        if time.monotonic()-started>1800:raise TimeoutError('.5GPU-hour cap')
        if diagnostic_phase and time.monotonic()-started>900:raise TimeoutError('15-minute diagnostic cap')
        if torch.cuda.max_memory_reserved()>cap or torch.cuda.mem_get_info()[0]<1024**3:raise MemoryError('GPU cap/headroom')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>32*1024**3:raise MemoryError('RSS cap')
        if sum(v.stat().st_size for v in out.rglob('*') if v.is_file())>2*1024**3:raise OSError('output cap')
    try:
        dump(out/'data_lock.json',lock)
        state,compat=initializer_compatibility(Path(grant['s0']),{'initializer':lock['s0']});dump(out/'start_compatibility.json',compat)
        control=Path(grant['control_output'])
        for row in lock['control_payloads'].values():old.verify_payload(control,row)
        arrays=old.load_reference(Path(grant['data_root']),lock['reference_lock']);p=old.Problem(arrays,'cuda:0');scored.validate_current_lower(p)
        frozen=np.load(control/'fields.npz');endpoint=np.load(control/'head_endpoint.npz')
        saved_geometry=np.load(control/'head_geometry.npz')
        parent_receipt=json.loads((control/'receipt.json').read_text())
        if parent_receipt['commit']!=lock['expected_control_runtime_commit'] or parent_receipt['accepted_head_updates']!=1:raise ValueError('exact accepted E032 parent required')
        old_basis_np=saved_geometry['basis']
        if old_basis_np.shape!=(7,2,401):raise ValueError('exact E032 frozen seven-axis plane required')
        flat_old=old_basis_np.reshape(7,802)
        if not np.allclose(np.einsum('ij,kj->ik',flat_old,flat_old),np.eye(7),atol=1e-12,rtol=0):raise ValueError('frozen old plane not orthonormal')
        model=old.make_model(state,'cuda:0')
        for param in model.parameters():param.requires_grad_(False)
        theta_saved=torch.as_tensor(endpoint['theta'],device=p.xy.device,dtype=torch.float64)
        if theta_saved.shape!=(2,401):raise ValueError('parent UV head schema')
        with torch.no_grad():
            features=model.encode(p.xy).detach()
            model.output_layer.weight[:2].copy_(theta_saved[:,:-1]);model.output_layer.bias[:2].copy_(theta_saved[:,-1])
            legacy=old.fields(model,p.xy)
        if not np.allclose(legacy[:,:2].cpu().numpy(),frozen['UVjoint'][:,:2],atol=1e-10,rtol=1e-10):raise ValueError('E032 actual UV replay mismatch')
        if not np.array_equal(frozen['reference'],arrays['ref']):raise ValueError('reference mismatch')
        damage=torch.as_tensor(frozen['UVjoint'][:,2].copy(),device=p.xy.device,dtype=torch.float64);damage_saved=damage.clone();lower=p.previous.clone();fatigue=p.f.clone()
        theta0=m.head_state(model)
        if not torch.equal(theta0,theta_saved):raise ValueError('parent head exact identity')
        radius=m.RADIUS_FRACTION*float(theta0.norm())
        theta=theta0.clone().requires_grad_(True)
        q0=m.fields(theta,features,p,damage);scored.check_physical(p,q0)
        if not np.allclose(q0.detach().cpu().numpy(),frozen['UVjoint'],atol=1e-10,rtol=1e-10):raise ValueError('complete E032 start replay mismatch')
        initial_score=scored.component_scores(p,q0)
        for key,value in lock['expected_zero_scores'].items():
            if not np.isclose(initial_score[key],value,atol=1e-10,rtol=1e-10):raise ValueError('zero score mismatch '+key)
        before={k:v.detach().clone() for k,v in model.state_dict().items()}
        with torch.no_grad():reference=tuple(x.detach() for x in p.parts(*p.ref.unbind(1)))
        force_norm=initial_score['free_force']
        if force_norm<=1e-12:raise ValueError('force scale unavailable')
        metrics=m.metric_values(p,q0,reference,force_norm,True);baseline={k:float(v.detach()) for k,v in metrics.items()}
        dump(out/'zero_metrics.json',baseline)
        gradients=[]
        for name in m.METRICS:
            guard();g=torch.autograd.grad(metrics[name],theta,retain_graph=True)[0]
            gradients.append(g.detach().cpu().numpy().ravel())
            np.savez_compressed(out/'full_gradient_progress.npz',metric_names=np.asarray(m.METRICS[:len(gradients)]),gradients=np.stack(gradients))
            old.finite(g,'full original head gradient');receipt['metric_gradient_evals']+=1
        full_gradients=np.stack(gradients)
        full_direction,_,certificate=m.common_descent(full_gradients,guard)
        dump(out/'full_reachability.json',certificate)
        projected_old=np.einsum('ij,kj->ik',full_gradients,flat_old)
        inside=np.einsum('ik,kj->ij',projected_old,flat_old);outside=full_gradients-inside
        old_direction,_,old_certificate=m.common_descent(projected_old,guard)
        dump(out/'old_plane_reachability.json',old_certificate)
        rows=[]
        for index,name in enumerate(m.METRICS):
            nf=float(np.linalg.norm(full_gradients[index]));ni=float(np.linalg.norm(inside[index]));no=float(np.linalg.norm(outside[index]))
            rows.append(dict(metric=name,full_norm=nf,inside_norm=ni,outside_norm=no,outside_fraction=no/nf if nf>0 else None))
        np.savez_compressed(out/'diagnostic_geometry.npz',theta0=theta0.cpu().numpy(),old_basis=old_basis_np,
            full_gradients=full_gradients,old_projected_gradients=projected_old,gradient_inside=inside,gradient_outside=outside,
            full_direction=full_direction.reshape(2,401),old_plane_direction=old_direction)
        receipt['joint_solve_calls']=0;receipt['coefficient_proxy_iterations']=0;receipt['single_added_axis']=0
        basis_np=old_basis_np.copy();basis_coordinates=None
        axis_info=dict(eligible=False,reason='no resolved strict full-head direction')
        if certificate['resolved_strict']:
            enriched,basis_coordinates,axis_info=m.enrich_one_axis(old_basis_np,full_direction.reshape(2,401))
            if axis_info['eligible']:
                basis_np=enriched;receipt['single_added_axis']=1
        else:
            if old_certificate['resolved_strict']:
                realized_old=np.einsum('i,ijk->jk',old_direction,old_basis_np).ravel()
                unit_full,_=m.base.unit_rows(full_gradients)
                if np.einsum('ij,j->i',unit_full,realized_old).max()< -1e-8:raise ValueError('full/old plane certificates inconsistent')
        dump(out/'axis_eligibility.json',axis_info)
        diagnostic=dict(metric_count=11,original_head_coordinates=802,old_plane_dimension=7,
            full_certificate=certificate,old_plane_certificate=old_certificate,metric_projection_norms=rows,
            one_axis=axis_info,optimizer_steps=0,FEM_solves=0,history_commits=0,
            elapsed_seconds=time.monotonic()-started,scope='current E032 endpoint first-order local head geometry, no nonlinear capacity claim')
        dump(out/'diagnostic.json',diagnostic)
        guard();receipt['diagnostic_seconds']=time.monotonic()-started
        signal.alarm(0);diagnostic_phase=False
        del q0,theta,metrics
        basis=torch.as_tensor(basis_np,device=p.xy.device,dtype=torch.float64)
        gradients=radius*np.einsum('ij,kj->ik',full_gradients,basis_np.reshape(len(basis_np),802))
        direction=old_direction
        if axis_info['eligible']:
            direction=basis_coordinates
            unit_plane,_=m.base.unit_rows(gradients)
            slopes=np.einsum('ij,j->i',unit_plane,direction)
            margin=-float(slopes.max())
            if margin<=1e-8:raise ValueError('reconstructed full direction loses strict metric descent')
            plane_certificate=dict(resolved_strict=True,unit_gradient_margin=margin,largest_unit_slope=float(slopes.max()),
                source='exact full-head direction reconstructed by one-axis enrichment')
        else:
            plane_certificate=dict(resolved_strict=False,unit_gradient_margin=0.,reason=axis_info['reason'])
        dump(out/'plane_direction_certificate.json',plane_certificate)
        receipt['basis_dimension']=len(basis);receipt['full_metric_count']=11
        geometry=dict(theta0=theta0.cpu().numpy(),basis=basis_np,gradients=gradients,direction=direction)
        np.savez_compressed(out/'head_geometry.npz',**geometry)
        trials=[];winner=theta0.clone();accepted=False
        if axis_info['eligible']:
            with torch.no_grad():
                base_uv=m.fields(theta0,features,p,damage)[:,:2]
                velocities=torch.stack([(m.fields(theta0+radius*b,features,p,damage)[:,:2]-base_uv) for b in basis])
            velocity_np=velocities.cpu().numpy();error=frozen['UVjoint'][:,:2]-arrays['ref'][:,:2]
            weights={'UV_global':p.mass.cpu().numpy(),'UV_Z':(p.mass*p.zone).cpu().numpy()}
            terms=m.component_quadratics(error,velocity_np,weights)
            fraction,curvature=m.curvature_seed(terms,direction);seed=fraction*direction
            geometry.update(basis_UV_velocities=velocity_np,seed=seed)
            for name in m.UV_TERMS:geometry.update({name+'_b':terms[name]['b'],name+'_Q':terms[name]['q']})
            np.savez_compressed(out/'head_geometry.npz',**geometry)
            dump(out/'curvature.json',dict(seed_fraction=fraction,regions=curvature,radius=radius,relative_head_radius=m.RADIUS_FRACTION))
            receipt['joint_solve_calls']=1
            proposal,proxy=m.joint_coefficients(gradients,baseline,terms,seed,plane_certificate['unit_gradient_margin'],guard)
            dump(out/'joint_proxy.json',proxy);receipt['coefficient_proxy_iterations']=proxy['iterations']
            np.savez_compressed(out/'joint_proposal.npz',coefficient=proposal,seed=seed)
            if proxy['epigraph']<1-1e-8:
                proposal_t=torch.as_tensor(proposal,device=p.xy.device,dtype=torch.float64)
                for index in range(1,m.MAX_CANDIDATES+1):
                    guard();step_fraction=2.**(-(index-1))
                    candidate=(theta0+radius*step_fraction*torch.einsum('i,ijk->jk',proposal_t,basis)).detach().requires_grad_(True)
                    q=m.fields(candidate,features,p,damage);scored.check_physical(p,q)
                    if not torch.equal(q[:,2],damage_saved):raise ValueError('physical damage changed')
                    values={k:float(v.detach()) for k,v in m.metric_values(p,q,reference,force_norm,False).items()}
                    relative=float((candidate.detach()-theta0).norm())/float(theta0.norm());ok,failures=m.admit_candidate(values,baseline,relative)
                    primary=max(np.sqrt(values['UV_global']/baseline['UV_global']),np.sqrt(values['raw_global']/baseline['raw_global']))
                    if primary>=1-1e-8:ok=False;failures.append('UV/raw decrease unresolved')
                    trials.append(dict(index=index,fraction=step_fraction,relative_head_change=relative,values=values,
                        ratios={k:values[k]/baseline[k] for k in m.METRICS},UV_raw_max_ratio=float(primary),admitted=ok,reasons=failures))
                    receipt['head_candidate_evals']+=1;dump(out/'trials.json',trials)
                    if ok:winner=candidate.detach().clone();accepted=True;break
        if not trials:dump(out/'trials.json',trials)
        with torch.no_grad():
            model.output_layer.weight[:2].copy_(winner[:,:-1]);model.output_layer.bias[:2].copy_(winner[:,-1])
            actual_uv=old.fields(model,p.xy)[:,:2];actual=torch.cat((actual_uv,damage[:,None]),1)
            predicted=m.fields(winner,features,p,damage)
        gap=float((actual-predicted).abs().max())
        if gap>1e-10:raise ValueError('actual network forward/linear head mismatch')
        own_start_gap=None
        if not accepted:
            exact_start=torch.as_tensor(frozen['UVjoint'].copy(),device=p.xy.device,dtype=torch.float64)
            own_start_gap=float((actual-exact_start).abs().max())
            if own_start_gap>1e-10:raise ValueError('unchanged actual network/start mismatch')
            # The no-correction wrapper returns its exact cached physical start.
            # Actual unchanged-network forward has still been checked above.
            actual=exact_start
        np.savez_compressed(out/'head_endpoint.npz',theta0=theta0.cpu().numpy(),theta=winner.cpu().numpy())
        scored.check_physical(p,actual)
        if not torch.equal(actual[:,2],damage_saved) or not torch.equal(p.previous,lower) or not torch.equal(p.f,fatigue):raise ValueError('damage/history/fatigue changed')
        for name,value in model.state_dict().items():
            if name=='output_layer.weight':unchanged=torch.equal(value[2:],before[name][2:])
            elif name=='output_layer.bias':unchanged=torch.equal(value[2:],before[name][2:])
            else:unchanged=torch.equal(value,before[name])
            if not unchanged:raise ValueError('backbone/unused damage head changed '+name)
        if any(param.grad is not None for param in model.parameters()):raise ValueError('frozen model gradient unexpectedly populated')
        actual_leaf=actual.detach().requires_grad_(True);final_metrics={k:float(v.detach()) for k,v in m.metric_values(p,actual_leaf,reference,force_norm,False).items()}
        if accepted and not m.admit_candidate(final_metrics,baseline,float((winner-theta0).norm()/theta0.norm()))[0]:raise ValueError('actual forward fails finite guards')
        receipt['accepted_head_updates']=int(accepted)
        pred=dict(reference=frozen['reference'],E030_zero=frozen['E030_zero'],E030_R=frozen['E030_R'],E031_R=frozen['E031_R'],E032_R=frozen['UVjoint'],endpoint=actual.cpu().numpy())
        scores={k:scored.component_scores(p,torch.as_tensor(v,device=p.xy.device,dtype=torch.float64)) for k,v in pred.items()}
        uv_ratio=scores['endpoint']['global_uv_RMS_Us']/scores['E032_R']['global_uv_RMS_Us'];raw_ratio=scores['endpoint']['global_raw_RMSE']/scores['E032_R']['global_raw_RMSE']
        primary=max(uv_ratio,raw_ratio)
        if accepted and primary>=1-1e-8:raise ValueError('actual primary improvement unresolved')
        scores['decision']=dict(primary_raw_RMSE_ratio=raw_ratio,target_raw_ratio=.999,primary_met=bool(accepted and raw_ratio<=.999),protected_UV_raw_max_ratio=primary,UV_global_ratio=uv_ratio,raw_global_ratio=raw_ratio,status=('RAW_GAIN_TARGET_MET' if raw_ratio<=.999 else 'COMPONENT_GAIN_BELOW_RAW_TARGET') if accepted else 'NO_ADMITTED_CORRECTION',accepted_head_updates=int(accepted),single_added_axis=receipt['single_added_axis'],full_direction_resolved=certificate['resolved_strict'],scope='full eleven-metric head diagnostic; conditional single-axis correction with separate u/v guards')
        np.savez_compressed(out/'fields.npz',**pred);dump(out/'scores.json',scores);dump(out/'final_metrics.json',final_metrics);dump(out/'forward_identity.json',dict(actual_network_head_max_abs_gap=gap,unchanged_network_cached_start_max_abs_gap=own_start_gap,no_correction_uses_exact_cached_start=not accepted,physical_damage_bitwise_equal=True,hidden_and_damage_head_unchanged=True,original_head_dimension=theta0.numel()))
        torch.save(dict(model=model.state_dict(),physical_damage=damage,theta0=theta0,theta=winner,protocol=m.PROTOCOL),out/'endpoint.pt')
        with (out/'metrics.csv').open('w') as f:
            writer=csv.DictWriter(f,fieldnames=['state']+list(initial_score),lineterminator='\n');writer.writeheader()
            for key,value in scores.items():
                if key!='decision':writer.writerow(dict(state=key,**value))
        guard();render(p,pred,scores,trials,out,receipt);guard();receipt['execution']='completed_pending_retrieval_review'
    except BaseException as error:receipt.update(execution='stopped_no_retry',error=f'{type(error).__name__}: {error}');raise
    finally:
        signal.alarm(0)
        receipt.update(elapsed_seconds=time.monotonic()-started,peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved(),max_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024);dump(out/'receipt.json',receipt)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--grant',type=Path);ap.add_argument('--out',type=Path);args=ap.parse_args()
    if not args.execute:print('Preparation only; no inputs/model/GPU read.')
    else:
        if not args.grant or not args.out:ap.error('execute requires exact grant and fresh output')
        signal.signal(signal.SIGTERM,deadline_signal);signal.signal(signal.SIGINT,deadline_signal)
        run(json.loads(LOCK.read_text()),json.loads(args.grant.read_text()),args.out)
