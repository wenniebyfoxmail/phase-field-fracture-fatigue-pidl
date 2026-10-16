#!/usr/bin/env python3
"""Offline localization of an original-arm c1 regression miss; never solves."""
import argparse,csv,hashlib,json
from pathlib import Path
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_multicycle_cross_replay import q4_geometry,amor_raw,interp


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def array(group,key):return np.asarray(group[key])
def vector(group,key):return array(group,key).reshape(-1)
def scalar(group,key):return array(group,key).item()
def scaled(x,y):return np.abs(x-y)/np.maximum(1,np.abs(y))
def rel(x,y,w):
    den=float(np.sum(w*y*y))
    return float(np.sqrt(np.sum(w*(x-y)**2)/den)) if den>1e-30 else None


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',required=True,type=Path);a=ap.parse_args()
    root=a.run/'retrieved';base=root/'output/c1_commit';out=a.run/'analysis';out.mkdir(exist_ok=True)
    receipt=json.loads((a.run/'retrieval_verification.json').read_text())
    assert receipt['all_hashes_and_sizes_match']
    for x in receipt['manifest']:
        path=root/Path(x['relative'].replace('\\','/'))
        assert path.stat().st_size==x['bytes'] and sha(path)==x['sha256']
    failure=json.loads((base/'original/failure.json').read_text());assert failure['identifier']=='E011:BaselineRegression'
    failed_step=int(failure['step']);assert 1<=failed_step<=5
    with h5py.File(base/'common_initial.mat') as h:
        points=array(h,'node_coords').T;c=array(h,'connectivity').T.astype(int)-1
        initial=dict(state0_d_maxerr=float(scalar(h['common_meta'],'state0_maxerr')),recovery_phase_calls=int(scalar(h['common_meta'],'recovery_phase_calls')))
    N,B,w,xy=q4_geometry(points,c);n=len(points);rows=[];inputs=[base/'common_initial.mat',base/'original/failure.json']
    reference_raw_checks=[]
    for ref_step in range(1,6):
        refs=list((root/'inputs').glob(f'*c0001_s{ref_step:03d}_post_commit.mat'));assert len(refs)==1
        with h5py.File(refs[0]) as f:
            z=f['request28_snapshot'];uv=array(z,'u_node').T.reshape(-1,order='F');raw_ref=array(z,'psi_raw_gp').T
            own=amor_raw(uv[:n],uv[n:],c,B)
            reference_raw_checks.append(dict(step=ref_step,raw_self_scaled_maxerr=float(np.max(scaled(raw_ref,own))),raw_self_weighted_relative_L2=rel(raw_ref,own,w)))
        inputs.append(refs[0])
    for step in range(1,failed_step+1):
        path=base/f'original/s{step}/precommit.mat'
        ref=list((root/'inputs').glob(f'*c0001_s{step:03d}_post_commit.mat'));assert len(ref)==1
        with h5py.File(path) as h,h5py.File(ref[0]) as f:
            z=f['request28_snapshot'];proof=h['proof'];native=h['out']
            u=vector(h['candidate'],'u');d=vector(h['candidate'],'d');raw=array(h['candidate'],'raw').T
            ur=array(z,'u_node').T.reshape(-1,order='F');dr=vector(z,'d_node');rr=array(z,'psi_raw_gp').T
            proposal_path=base/f'original/s{step}/accepted_commit.mat'
            if not proposal_path.exists():proposal_path=base/'original/failure_state.mat'
            with h5py.File(proposal_path) as proposal:
                ht=array(proposal['proposed'],'history').transpose(2,1,0)[:,:,1:]
            assert np.max(abs(ht-array(proof,'history234').transpose(2,1,0)))<=1e-10
            inputs.append(proposal_path)
            hr=array(z,'history_vars_old').transpose(2,1,0)[:,:,1:]
            pn=amor_raw(u[:n],u[n:],c,B);pr=amor_raw(ur[:n],ur[n:],c,B)
            # Recompute each stored raw from ITS OWN u. Then compare the two
            # energy responses; this diagnoses amplification, not solver cause.
            es=scaled(raw,rr);idx=np.unravel_index(np.argmax(es),es.shape)
            active=(1-interp(d,c,N))**2*raw;ar=(1-interp(dr,c,N))**2*rr
            row=dict(step=step,durable_accepted=(base/f'original/s{step}/accepted_commit.mat').exists(),
                outer=int(scalar(native,'completed_outer')),reference_outer=int(scalar(z,'staggered_iterations')),
                u_maxerr=float(np.max(abs(u-ur))),d_maxerr=float(np.max(abs(d-dr))),
                raw_scaled_maxerr=float(np.max(es)),history234_scaled_maxerr=float(np.max(scaled(ht,hr))),
                raw_weighted_relative_L2=rel(raw,rr,w),active_weighted_relative_L2=rel(active,ar,w),
                candidate_raw_self_scaled_maxerr=float(np.max(scaled(raw,pn))),reference_raw_self_scaled_maxerr=float(np.max(scaled(rr,pr))),
                raw_difference_explanation_scaled_maxerr=float(np.max(abs((raw-rr)-(pn-pr))/np.maximum(1,abs(rr)))),
                offending_gp_count=int(np.count_nonzero(es>1e-10)),total_gp=es.size,
                max_error_element_zero_based=int(idx[0]),max_error_gp_zero_based=int(idx[1]),
                max_error_x=float(xy[idx][0]),max_error_y=float(xy[idx][1]),
                max_error_native_candidate=float(raw[idx]),max_error_native_reference=float(rr[idx]),
                max_error_native_delta=float(raw[idx]-rr[idx]),max_error_replayed_delta=float(pn[idx]-pr[idx]),
                C=float(scalar(proof,'criterion')),Ru=float(scalar(proof,'u_l2')),Rd=float(scalar(proof,'d_feasible_l2')))
            row['frozen_reference_pass']=bool(row['u_maxerr']<=1e-10 and row['d_maxerr']<=1e-10 and row['raw_scaled_maxerr']<=1e-10 and row['history234_scaled_maxerr']<=1e-10 and row['outer']==row['reference_outer'])
            rows.append(row);inputs.extend([path,ref[0]])
    with h5py.File(base/'original/failure_state.mat') as h:
        versions=dict(accepted=int(scalar(h['accepted'],'version')),pre=int(scalar(h['pre'],'version')),proposed=int(scalar(h['proposed'],'version')))
    assert versions['pre']==versions['accepted']==failure['history_commits']==failed_step-1
    assert versions['proposed']==failed_step
    assert not (base/f'original/s{failed_step}/accepted_commit.mat').exists() and not (base/'repaired').exists()
    with (out/'regression_localization.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    files=[Path(__file__).resolve(),Path(amor_raw.__code__.co_filename)]
    result=dict(status='offline_diagnostic_original_regression_not_passed',frozen_tolerance=1e-10,initial=initial,
        producer_failure=failure,versions=versions,repaired_started=False,rows=rows,reference_raw_checks=reference_raw_checks,
        claim_boundary='Explains raw sensitivity to u differences; does not identify their upstream floating/runtime source or relax the failed gate.',
        input_files=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in dict.fromkeys(inputs+[base/'original/failure_state.mat',a.run/'retrieval_verification.json'])],
        code=[dict(path=str(p),sha256=sha(p)) for p in files])
    (out/'regression_localization.json').write_text(json.dumps(result,indent=2)+'\n')
    fig,ax=plt.subplots(1,3,figsize=(14,4.3));steps=[r['step'] for r in rows]
    for key,label in [('u_maxerr','nodal u'),('d_maxerr','nodal damage'),('raw_scaled_maxerr','raw energy'),('history234_scaled_maxerr','history 2:4')]:
        ax[0].semilogy(steps,[max(r[key]/1e-10,1e-8) for r in rows],'-o',label=label)
    ax[0].axhline(1,color='black',ls='--');ax[0].set_ylabel('Frozen regression error / tolerance');ax[0].set_title('A  Original archive regression');ax[0].legend(fontsize=8)
    for key,label in [('raw_scaled_maxerr','candidate vs archive raw'),('candidate_raw_self_scaled_maxerr','candidate raw vs own-u replay'),('reference_raw_self_scaled_maxerr','archive raw vs own-u replay')]:
        ax[1].semilogy(steps,[max(r[key],1e-18) for r in rows],'-o',label=label)
    ax[1].axhline(1e-10,color='black',ls='--');ax[1].set_ylabel('Max |delta raw| / max(1, |reference|)');ax[1].set_title('B  Common-Q4 raw consistency');ax[1].legend(fontsize=7)
    ax[2].semilogy(steps,[r['C'] for r in rows],'-',color='tab:blue')
    for r in rows:ax[2].plot(r['step'],r['C'],'o' if r['durable_accepted'] else 'x',color='tab:blue',ms=8)
    ax[2].plot([],[],'o',color='tab:blue',label='durable accepted');ax[2].plot([],[],'x',color='tab:blue',label='unaccepted proposal')
    ax[2].axhline(1,color='black',ls='--',label='fresh joint C=1');ax[2].set_ylabel('PRE-COMMIT C, old lower/history');ax[2].set_title('C  Native acceptance vs fresh C');ax[2].legend(fontsize=8)
    for x in ax:x.set_xticks(range(1,6));x.set_xlim(.75,5.25);x.set_xlabel('c1 substep; 4/5 and repaired absent');x.grid(alpha=.2)
    fig.suptitle('Synthetic c1 | original arm only | '+a.run.name,fontsize=10);fig.tight_layout();fig.savefig(out/'regression_localization.png',dpi=180);plt.close(fig)
    last=rows[-1]
    (out/'regression_localization.md').write_text(f'''# Original c1 regression and raw-field localization

Question: why did the original arm stop before a paired repaired comparison?
Data provenance: every retrieved file size/SHA verified; exact run/source/failure identities are in regression_localization.json. All observed substeps1–{failed_step} are shown, no selection. No new producer solve. Table regression_localization.csv is authoritative. Synthetic development diagnostic, no independent physical/holdout axis.

How to read: Panel A: every frozen field-error reduction divided by its original1e-10 tolerance; u/d use absolute nodal maximum, raw/history use max|candidate-reference|/max(1,|reference|). Dashed1 is the unchanged gate, not a new fit. Panel B: stored candidate/archive raw compared, then each raw replayed from its own nodal u using the same native-Q4/2x2GP/Amor operator. Dashed1e-10 is shown for scale. Panel C: fresh PRE-COMMIT C under old lower/history; circles are durable versions, x is the candidate that did not advance accepted state. C=1 was required for the repaired arm, which never ran; native original cached acceptance remains separate. Missing4/5 and repaired states are deliberately blank. Display floors1e-8/error-ratio and1e-18/scaled raw are plotting only.

At s{failed_step}, raw scaled max error={last['raw_scaled_maxerr']:.10g}; raw weighted relativeL2={last['raw_weighted_relative_L2']:.10g}. Only {last['offending_gp_count']}/{last['total_gp']}GPs exceed the frozen raw tolerance. The maximum is zero-based element{last['max_error_element_zero_based']}/GP{last['max_error_gp_zero_based']} at({last['max_error_x']:.8g},{last['max_error_y']:.8g}), in the initial left crack wake. The native raw delta there={last['max_error_native_delta']:.10g}; own-u common-operator replay delta={last['max_error_replayed_delta']:.10g}. Tiny differing u inputs explain this raw response. Upstream causes of u differences (runtime/roundoff/linear algebra/cache effects) are NOT isolated by this replay.

Limitations: one partial original c1. Frozen regression failed; no threshold relaxed and no repaired primary evaluated. Version{versions['proposed']} is an unaccepted proposal; accepted stays{versions['accepted']}. This supports neither full-cycle repair nor PIDL/FEM agreement/teacher/physical validation. Existing production verdicts are unchanged.
''')
    print(json.dumps(dict(status=result['status'],versions=versions,failed_step=failed_step,rows=rows),indent=2))

if __name__=='__main__':main()
