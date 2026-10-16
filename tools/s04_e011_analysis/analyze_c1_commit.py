#!/usr/bin/env python3
"""Offline audit of c1 durable commits and common-Q4 residual/history mappings."""
import argparse,csv,hashlib,json,subprocess
from pathlib import Path
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from audit_phase_tangent import assemble
from run_multicycle_cross_replay import q4_geometry,amor_raw,interp
from localize_endpoint_tight import mechanics_force
from audit_fem_final_residuals import projected_gradient
from audit_raw_response_bound import admission as raw_admission,stencil as raw_stencil


def a(g,k):return np.asarray(g[k])
def v(g,k):return a(g,k).reshape(-1)
def scalar(g,k):return a(g,k).item()
def text(g,k):
    ds=g[k];assert ds.attrs.get('MATLAB_class') in [b'char','char']
    return ''.join(chr(int(x)) for x in np.asarray(ds).reshape(-1))
def state(g):return dict(u=v(g,'u'),d=v(g,'d'),lower=v(g,'lower'),raw=a(g,'raw').T,history=a(g,'history').transpose(2,1,0),version=int(scalar(g,'version')))
def same(x,y):
    for k in x:
        assert np.array_equal(x[k],y[k],equal_nan=True) if isinstance(x[k],np.ndarray) else x[k]==y[k],k

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);arg=p.parse_args()
    receipt=json.loads((arg.run/'retrieval_verification.json').read_text());assert receipt['all_hashes_and_sizes_match']
    root=arg.run/'retrieved';base=root/'output/c1_commit';out=arg.run/'analysis';out.mkdir(exist_ok=True)
    assert receipt['files']==len(receipt['manifest']) and receipt['bytes']==sum(x['bytes'] for x in receipt['manifest'])
    for item in receipt['manifest']:
        path=root/Path(item['relative'].replace('\\','/'))
        assert path.is_file() and path.stat().st_size==item['bytes'] and sha(path)==item['sha256']
    launch=json.loads((root/'launch_receipt.json').read_text(encoding='utf-8-sig'))
    tests=json.loads((root/'selftest.json').read_text(encoding='utf-8-sig'))
    for name,cases in [('damage',6),('coupled',6),('commit',10)]:
        assert tests[name]['status']=='passed' and tests[name]['cases']==cases and tests[name]['native_field_solves']==0
    assert tests['commit']['file_io_cases']==2

    manifest=json.loads((root/'input_manifest.json').read_text());sources={x['role']:root/'inputs'/Path(x['target'].replace('\\','/')).name for x in manifest['staging']}
    assert manifest['source_commit']==launch['commit'] and len(launch['commit'])==40
    raw_r4=manifest.get('raw_admission')=='q4_amor_response_r4'
    if raw_r4:
        assert tests['raw']['status']=='passed' and tests['raw']['cases']==12 and tests['raw']['native_field_solves']==0
        io=json.loads((root/'io_preflight.json').read_text(encoding='utf-8-sig'))
        assert io['status']=='passed' and io['unique_inputs']==8 and len(io['raw_reference_checks'])==5
        assert all(x['passed'] and x['own_scaled_maxerr']<=1e-10 for x in io['raw_reference_checks'])
    for row in manifest['staging']:
        assert sources[row['role']].stat().st_size==row['bytes'] and sha(sources[row['role']])==row['sha256']
    with h5py.File(base/'common_initial.mat') as h:
        assert text(h['common_meta'],'source_commit')==launch['commit']
        if raw_r4:assert text(h['common_meta'],'reference_raw_admission')=='q4_amor_response_r4'
        common=state(h['common']);points=a(h,'node_coords').T;c=a(h,'connectivity').T.astype(int)-1
        fu=v(h,'free_dof_u').astype(int)-1;fd=v(h,'free_dof_d').astype(int)-1
        assert common['version']==0 and np.all(common['u']==0) and np.all(common['raw']==0)
        assert np.array_equal(common['d'],common['lower'])
        assert np.all(common['history'][:,:,1:3]==0) and np.all(common['history'][:,:,3]==1)
        assert scalar(h['common_meta'],'initialization_resets')==1 and scalar(h['common_meta'],'shared_setup_initial_assemblies')==1
        recovery_calls=int(scalar(h['common_meta'],'recovery_phase_calls'));assert recovery_calls<=250
    with h5py.File(sources['state0']) as h:
        assert np.array_equal(points,a(h,'state0_node').T[:,:2])
        assert np.max(np.abs(common['d']-v(h,'state0_p_field')))<=1e-10
    assert len(points)==86756 and len(c)==86408
    N,B,w,_=q4_geometry(points,c);n=len(points);raw_B=raw_stencil(points,c) if raw_r4 else None;rows=[];missing=[];paths=[base/'common_initial.mat',root/'input_manifest.json',root/'launch_receipt.json',root/'selftest.json',arg.run/'retrieval_verification.json',*sources.values()];complete={};terminal={};field_cache={}
    for arm in ['original','repaired']:
        if arm=='repaired' and list((base/arm).glob('s*/accepted_commit.mat')):
            assert complete.get('original',False),'Original five-step archive regression must pass before any repaired evidence'
        previous=common
        for step,uy in enumerate([.02999988,.05999988,.08999988,.11999988,0],1):
            path=base/arm/f's{step}/accepted_commit.mat'
            if not path.exists():missing.append(f'{arm}:s{step}');break
            with h5py.File(path) as h:
                pre=state(h['pre']);post=state(h['proposed']);same(pre,previous)
                assert pre['version']==step-1 and post['version']==step
                candidate=dict(u=v(h['candidate'],'u'),d=v(h['candidate'],'d'),raw=a(h['candidate'],'raw').T)
                proof=h['proof'];event=h['event'];counts=h['counts'];native=h['out']
                assert np.array_equal(v(proof,'lower'),pre['lower'])
                assert np.array_equal(a(proof,'history').transpose(2,1,0),pre['history'],equal_nan=True)
                assert text(event,'arm')==arm and bool(scalar(proof,'native_accepted'))==bool(scalar(event,'native_accepted'))
                assert int(scalar(event,'substep'))==step and int(scalar(event,'cycle'))==1 and int(scalar(event,'commits'))==1
                assert int(scalar(event,'pre_version'))==step-1 and int(scalar(event,'post_version'))==step
                assert not bool(scalar(event,'history_reset')) and bool(scalar(event,'native_accepted'))
                for k in ['u','d']:assert np.array_equal(v(proof,k),candidate[k])
                assert np.array_equal(a(proof,'raw').T,candidate['raw'])
                assert np.array_equal(post['u'],candidate['u']) and np.array_equal(post['d'],candidate['d']) and np.array_equal(post['lower'],candidate['d'])
                assert np.array_equal(post['raw'],candidate['raw'])
                u=candidate['u'];d=candidate['d'];raw=candidate['raw']
                assert all(np.isfinite(x).all() for x in [u,d,raw,post['history'][:,:,1:]])
                assert np.all(d>=pre['lower']-1e-12) and np.all(d<=1+1e-12)
                fixed_u=np.setdiff1d(np.arange(2*n),fu);fixed_d=np.setdiff1d(np.arange(n),fd)
                target=np.zeros(2*n);target[n+np.flatnonzero(points[:,1]==points[:,1].max())]=uy
                assert np.max(np.abs(u[fixed_u]-target[fixed_u]))<=1e-12 and np.array_equal(d[fixed_d],pre['d'][fixed_d])
                expected_raw=amor_raw(u[:n],u[n:],c,B);rd,trial=assemble(d,raw,pre['lower'],pre['history'],c,N,B,w,n);ru=mechanics_force(u,d,c,N,B,w,n)
                assert np.max(np.abs(raw-expected_raw)/np.maximum(1,np.abs(expected_raw)))<1e-10
                replay=max(float(np.max(np.abs(rd-v(proof,'rd')))),float(np.max(np.abs(ru-v(proof,'ru')))))
                assert replay<1e-10
                ht=np.stack([trial['alpha'],trial['active'],trial['f']],axis=2)
                assert np.max(np.abs(a(proof,'history234').transpose(2,1,0)-ht))<1e-10
                assert np.max(np.abs(post['history'][:,:,1:]-ht))<1e-10
                assert np.all(post['history'][:,:,1]>=pre['history'][:,:,1]-1e-12)
                ur=float(np.linalg.norm(ru[fu]));dr=float(np.linalg.norm(projected_gradient(d[fd],rd[fd],pre['lower'][fd])));C=max((ur+dr)/4e-6,ur/1e-8)
                assert abs(C-scalar(proof,'criterion'))<1e-8*max(1,C)
                assert bool(scalar(proof,'joint_pass'))==(C<=1) and bool(scalar(event,'precommit_joint_pass'))==(C<=1)
                # New-lower/new-history audit is descriptive, never a replacement acceptance test.
                pr,ph=assemble(d,raw,post['lower'],post['history'],c,N,B,w,n);postproof=h['post']
                assert np.array_equal(v(postproof,'lower'),post['lower'])
                assert np.array_equal(a(postproof,'history').transpose(2,1,0),post['history'],equal_nan=True)
                assert np.max(np.abs(pr-v(postproof,'rd')))<1e-10
                assert np.max(np.abs(a(postproof,'history234').transpose(2,1,0)-post['history'][:,:,1:]))<1e-10
                assert np.max(np.abs(ph['alpha']-post['history'][:,:,1]))<1e-10
                uc=int(scalar(counts,'u'));dc=int(scalar(counts,'d'));blocks=int(scalar(native,'completed_outer'))
                assert uc==int(scalar(event,'u_calls')) and dc==int(scalar(event,'d_calls'))
                assert scalar(event,'predictor_solves')==1
                if arm=='repaired':
                    assert np.array_equal(v(native['final'],'u'),u) and np.array_equal(v(native['final'],'d'),d)
                    assert C<=1 and bool(scalar(native,'joint_pass')) and blocks<=20 and uc<=250 and dc<=250
                    assert uc==scalar(native['counts'],'u')+2 and dc==scalar(native['counts'],'d')+3
                else:
                    assert bool(scalar(native,'native_accepted')) and blocks<=1000 and uc<=251002 and dc<=250003
                    trace=native['trace']
                    def last(k):
                        ds=trace[k];x=ds[()].reshape(-1)[-1]
                        return np.asarray(h[x]).item() if isinstance(x,h5py.Reference) else x.item()
                    assert uc==last('native_u_calls')+2 and dc==last('native_d_calls')+3
                    assert bool(scalar(h['reference'],'pass'))
                    with h5py.File(sources[f'substep{step}']) as ref:
                        z=ref['request28_snapshot'];ref_u=a(z,'u_node').T.reshape(-1,order='F');ref_h=a(z,'history_vars_old').transpose(2,1,0)
                        assert np.max(np.abs(u-ref_u))<=1e-10 and np.max(np.abs(d-v(z,'d_node')))<=1e-10
                        ref_raw=a(z,'psi_raw_gp').T
                        if raw_r4:
                            assert text(h['reference'],'admission_revision')=='q4_amor_response_r4'
                            rc,rdetail=raw_admission(u,raw,ref_u,ref_raw,c,raw_B,n)
                            nr=h['reference/raw_admission'];assert text(nr,'schema')=='raw_response_r4'
                            assert rc['pass_new'] and bool(scalar(nr,'pass'))
                            assert scalar(nr,'tau')==1e-10 and abs(scalar(nr,'L')-(2/2.6+2/1.2))<1e-14
                            for k in ['candidate_own_pass','reference_own_pass','response_pass']:assert bool(scalar(nr,k))
                            for k,expected in [('candidate_replayed',rdetail['pc']),('reference_replayed',rdetail['pr']),('analytic_response_bound',rdetail['bound'])]:
                                assert np.max(np.abs(a(nr,k).T-expected)/np.maximum(1,np.abs(expected)))<=1e-10
                            assert bool(scalar(h['reference'],'legacy_raw_pass'))==(rc['legacy_raw_max']<=1e-10)
                        else:
                            assert np.max(np.abs(raw-ref_raw)/np.maximum(1,np.abs(ref_raw)))<=1e-10
                        assert np.max(np.abs(post['history'][:,:,1:]-ref_h[:,:,1:])/np.maximum(1,np.abs(ref_h[:,:,1:])))<=1e-10
                        assert blocks==scalar(z,'staggered_iterations')
                active=trial['active'];r=dict(arm=arm,step=step,uy=uy,commits=1,version=post['version'],precommit_joint_pass=C<=1,u_l2=ur,feasible_phase_l2=dr,C=C,completed_outer=blocks,u_calls=uc,d_calls=dc,active_integral=float(np.sum(w*active)),alpha_mean=float(np.sum(w*ht[:,:,0])/w.sum()),f_mean=float(np.sum(w*ht[:,:,2])/w.sum()),max_damage_increment=float(np.max(d-pre['d'])),residual_replay_maxerr=replay,H_nonfinite_count=int(np.count_nonzero(~np.isfinite(post['history'][:,:,0]))))
                r['raw_admission_revision']='q4_amor_response_r4' if raw_r4 and arm=='original' else 'legacy_or_not_required'
                r['legacy_raw_scaled_maxerr']=float(scalar(h['reference'],'raw_scaled_maxerr')) if arm=='original' else None
                r['legacy_raw_pass']=(r['legacy_raw_scaled_maxerr']<=1e-10) if arm=='original' else None
                field_cache[arm,step]=dict(u=u,d=d,active=active,alpha=ht[:,:,0],f=ht[:,:,2])
                rows.append(r);previous=post;paths.append(path)
        assert len(list((base/arm).glob('s*/accepted_commit.mat')))==previous['version']
        complete[arm]=previous['version']==5
        if complete[arm]:
            with h5py.File(base/arm/'arm_result.mat') as h:
                same(state(h['accepted']),previous)
                assert scalar(h['result'],'history_commits')==5 and scalar(h['result'],'steps')==5
                assert scalar(h['result'],'total_u_calls')==sum(x['u_calls'] for x in rows if x['arm']==arm)
                assert scalar(h['result'],'total_d_calls')==sum(x['d_calls'] for x in rows if x['arm']==arm)
                assert scalar(h['result'],'predictor_solves')==5
                paths.append(base/arm/'arm_result.mat')
        terminal[arm]=previous
    success=root/'sequence_finished.json';failure=root/'sequence_failure.json'
    if success.exists():
        result=json.loads(success.read_text(encoding='utf-8-sig'));assert result['status']=='completed' and result['history_commits']==10
        assert all(complete.values()) and not missing and not failure.exists()
        if raw_r4:assert result['raw_admission']=='q4_amor_response_r4'
        assert result['initialization_resets']==1 and result['recovery_phase_calls']==recovery_calls
        assert result['original']['history_commits']==5 and result['repaired']['history_commits']==5
        paths.append(success)
    else:result=None
    with (out/'commit_trace.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['arm','step'],lineterminator='\n');writer.writeheader();writer.writerows(rows)
    paired=[]
    for step in range(1,6):
        q={r['arm']:r for r in rows if r['step']==step}
        if len(q)==2:
            old=field_cache['original',step];new=field_cache['repaired',step]
            row=dict(step=step,active_integral_repaired_minus_original=q['repaired']['active_integral']-q['original']['active_integral'],alpha_mean_repaired_minus_original=q['repaired']['alpha_mean']-q['original']['alpha_mean'],u_nodal_maxabs=float(np.max(np.abs(new['u']-old['u']))),d_nodal_maxabs=float(np.max(np.abs(new['d']-old['d']))))
            for channel in ['d','active','alpha','f']:
                x=interp(old[channel],c,N) if channel=='d' else old[channel]
                y=interp(new[channel],c,N) if channel=='d' else new[channel]
                den=float(np.sum(w*x*x));num=float(np.sum(w*(y-x)**2))
                row[channel+'_gp_absolute_L2']=float(np.sqrt(num))
                row[channel+'_gp_relative_L2']=float(np.sqrt(num/den)) if den>1e-30 else None
            paired.append(row)
    (out/'paired_reductions.json').write_text(json.dumps(paired,indent=2)+'\n')
    code_files=[Path(__file__).resolve(),Path(assemble.__code__.co_filename),Path(q4_geometry.__code__.co_filename),Path(mechanics_force.__code__.co_filename),Path(projected_gradient.__code__.co_filename),Path(raw_admission.__code__.co_filename)]
    analysis=dict(raw_admission_revision='q4_amor_response_r4' if raw_r4 else 'legacy',producer_commit=launch['commit'],analysis_git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[2],text=True).strip(),analysis_code=[dict(path=str(x),sha256=sha(x),bytes=x.stat().st_size) for x in dict.fromkeys(code_files)],status='complete_offline_checked' if result else 'partial_no_terminal_success',completed_arms=complete,missing=missing,recovery_phase_calls=recovery_calls,shared_initial_assemblies=1,terminal=result,producer_failure=failure.exists(),scope='one c1 sequence only; accepted commit primary uses precommit predecessor',inputs=[dict(path=str(x),sha256=sha(x),bytes=x.stat().st_size) for x in dict.fromkeys(paths)])
    (out/'c1_commit_analysis.json').write_text(json.dumps(analysis,indent=2)+'\n')
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    for arm in ['original','repaired']:
        rr=[r for r in rows if r['arm']==arm]
        if rr:
            axs[0].semilogy([r['step'] for r in rr],[max(r['C'],1e-12) for r in rr],'-o',label=arm)
            axs[1].plot([r['step'] for r in rr],[r['alpha_mean'] for r in rr],'-o',label=arm)
    axs[0].axhline(1,color='black',ls='--',label='precommit C=1');axs[0].set_ylabel('Joint C (display floor 1e-12)');axs[1].set_ylabel('GP-weighted committed alpha mean')
    for ax in axs:ax.set_xlabel('c1 substep (1–4 loading, 5 unload)');ax.set_xticks(range(1,6));ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Synthetic c1 | original vs repaired | saved accepted commits only\n'+arg.run.name,fontsize=10);fig.tight_layout();fig.savefig(out/'c1_commit_decision.png',dpi=180);plt.close(fig)
    (out/'c1_commit_decision.md').write_text('''# Sequential c1 numerical diagnostic\n\nData provenance: verified native accepted_commit.mat files, exact source identities in c1_commit_analysis.json; all scored rows in commit_trace.csv. Both arms start from the identical recovered u/d/lower/history and original predictor stiffness cache.\n\nHow to read: left compares fresh PRE-COMMIT C under OLD accepted history/lower, with C=1 threshold. The logarithmic plot displays max(C,1e-12); CSV retains the exact computed C, including zero/below-range values. Original arm accepts under its original cached rule and may commit above this threshold. Repaired arm must pass C before one durable commit. Right shows physical-GP-weighted committed fatigue accumulator means through the same five substeps, with unloading distinct. Missing transactions are not plotted as successes.\n\nLimitations: one synthetic c1, composite solver-control and history-feedback change, not a new physical reference or fatigue-life trajectory. Postcommit residuals cannot rescue a precommit miss; trial evaluations do not count as commits. The legacy AT1 penalty kernel does not define/read history channel1; it is preserved/reported but only channels2:4 enter numerical history qualification. Independent ledger, source and guard tests are needed because duplicate writes at identical fields can be numerically idempotent.\n''')
    (out/'README_analysis.md').write_text('''# c1 commit analysis\n\nQuestion: does a repaired five-substep c1 sequence commit accepted history exactly once only after fresh joint acceptance, and how does it differ from the original archived process? Read commit_trace.csv and c1_commit_analysis.json first, then c1_commit_decision.png and its sidecar. Every durable substep is included; no missing/failed point is substituted. Paired active/alpha reductions are secondary. GP/Jacobian weights define all integrals/means; native nodal fields are not resampled.\n\nAcceptance is measured before commit using OLD lower/history. Original acceptance stays native; its archive regression is a prerequisite for paired interpretation. Repaired per-step joint acceptance and exactly-one durable version advance are necessary for the bounded sequential claim. H(channel1) is inactive/unassigned in this native penalty kernel; all channels are retained, finite status reported, active channels2:4 replayed.\n\nAllowed conclusion: one-cycle numerical/state-transition consistency only. Blocked: unique energy branch, qualified teacher, physical truth, or c83 onset/linear-versus-exponential accumulation across a new trajectory. Relative field L2 uses each original GP norm, omitted when squared norm<=1e-30 (near-zero unloading); absolute L2 remains reported. Full-cycle evidence and independent review remain required; a partial archive stays partial.\n''')
    if raw_r4:
        note='\n\nRaw admission revision: q4_amor_response_r4. The original cross-state raw equality clause is replaced prospectively by two own-u operator checks (tau1e-10) plus an analytic input-response budget. u/d/history/count clauses stay fixed. commit_trace.csv retains legacy raw error/pass; a new admission pass never means the old raw gate passed or retroactively rescues v3. The response bound is not independent equivalence evidence.\n'
        for leaf in ['README_analysis.md','c1_commit_decision.md']:
            with (out/leaf).open('a') as f:f.write(note)
    print(json.dumps(analysis,indent=2))

if __name__=='__main__':main()
