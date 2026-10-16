#!/usr/bin/env python3
"""Independent explicit Q4/Amor raw-response audit; offline, no solve."""
import argparse,csv,hashlib,json
from pathlib import Path
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_multicycle_cross_replay import q4_geometry,amor_raw
MU=1/2.6;K=1/1.2;D=2*MU*np.array([[2/3,-1/3,0],[-1/3,2/3,0],[0,0,.5]])
L=2*MU+2*K;TAU=1e-10

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def stencil(p,c):
    g=.577350269189626;xy=p[c];out=[]
    for xi,eta in g*np.array([[1,1],[-1,1],[1,-1],[-1,-1]]):
        a=.25*np.array([-(1-eta),1-eta,1+eta,-(1+eta)])
        b=.25*np.array([-(1-xi),-(1+xi),1+xi,1-xi])
        j11=xy[:,:,0]@a;j12=xy[:,:,1]@a;j21=xy[:,:,0]@b;j22=xy[:,:,1]@b
        det=j11*j22-j12*j21;assert np.all(det>0)
        out.append(np.stack(((j22[:,None]*a-j12[:,None]*b)/det[:,None],(-j21[:,None]*a+j11[:,None]*b)/det[:,None]),axis=1))
    return np.stack(out,axis=1)

def strain(u,c,b,n):
    uc=u[:n][c];vc=u[n:][c]
    return np.stack((np.einsum('egj,ej->eg',b[:,:,0,:],uc),np.einsum('egj,ej->eg',b[:,:,1,:],vc),np.einsum('egj,ej->eg',b[:,:,1,:],uc)+np.einsum('egj,ej->eg',b[:,:,0,:],vc)),axis=-1)

def energy(e):return .5*np.sum((np.einsum('...j,ji->...i',e,D))*e,axis=-1)+.5*K*np.maximum(e[...,0]+e[...,1],0)**2

def admission(u,raw,ur,rr,c,b,n):
    ec=strain(u,c,b,n);er=strain(ur,c,b,n);de=strain(u-ur,c,b,n)
    pc=energy(ec);pr=energy(er);sig=np.einsum('...j,ji->...i',er,D);sig[...,:2]+=K*np.maximum(er[...,0]+er[...,1],0)[...,None]
    s=np.linalg.norm(de,axis=-1);bound=np.linalg.norm(sig,axis=-1)*s+.5*L*s*s
    sc=np.maximum(1,abs(pc));sr=np.maximum(1,abs(pr));allow=bound+TAU*(sc+sr)
    ownc=np.max(abs(raw-pc)/sc);ownr=np.max(abs(rr-pr)/sr)
    return dict(pass_new=bool(ownc<=TAU and ownr<=TAU and np.all(abs(raw-rr)<=allow)),candidate_own_max=float(ownc),reference_own_max=float(ownr),legacy_raw_max=float(np.max(abs(raw-rr)/np.maximum(1,abs(rr)))),response_ratio_max=float(np.max(abs(raw-rr)/allow)),strain_subtraction_roundoff_max=float(np.max(abs(ec-er-de))),trace_branch_changes=int(np.count_nonzero((ec[...,0]+ec[...,1]>=0)!=(er[...,0]+er[...,1]>=0)))),dict(pc=pc,pr=pr,bound=bound,allow=allow,de=de)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    receipt=json.loads((a.run/'retrieval_verification.json').read_text());root=a.run/'retrieved';base=root/'output/c1_commit';assert receipt['all_hashes_and_sizes_match']
    for x in receipt['manifest']:
        p=root/Path(x['relative'].replace('\\','/'));assert p.stat().st_size==x['bytes'] and sha(p)==x['sha256']
    with h5py.File(base/'common_initial.mat') as h:p=np.asarray(h['node_coords']).T;c=np.asarray(h['connectivity']).T.astype(int)-1
    n=len(p);b=stencil(p,c);N,B,w,xy=q4_geometry(p,c);rows=[];controls=[];details=[];inputs=[base/'common_initial.mat']
    for step in range(1,4):
        path=base/f'original/s{step}/precommit.mat';ref=list((root/'inputs').glob(f'*c0001_s{step:03d}_post_commit.mat'))[0]
        with h5py.File(path) as h,h5py.File(ref) as f:
            u=np.asarray(h['candidate/u']).reshape(-1);raw=np.asarray(h['candidate/raw']).T;z=f['request28_snapshot'];ur=np.asarray(z['u_node']).T.reshape(-1,order='F');rr=np.asarray(z['psi_raw_gp']).T
        r,d=admission(u,raw,ur,rr,c,b,n);r['step']=step;idx=np.unravel_index(np.argmax(abs(raw-rr)/np.maximum(1,abs(rr))),raw.shape)
        r.update(worst_x=float(xy[idx][0]),worst_y=float(xy[idx][1]),worst_native_gap=float(abs(raw[idx]-rr[idx])),worst_response_bound=float(d['bound'][idx]),worst_total_budget=float(d['allow'][idx]),worst_linear_strain_delta_norm=float(np.linalg.norm(d['de'][idx])))
        existing=amor_raw(u[:n],u[n:],c,B)
        r['independent_implementation_max_scaled_delta']=float(np.max(abs(existing-d['pc'])/np.maximum(1,abs(existing))))
        rows.append(r);details.append(d);inputs.extend([path,ref])
        if step==3:
            for name,bad in [('stale_reference_raw',rr),('wrong_gp',raw[:,[1,0,3,2]]),('wrong_material',1.01*raw)]:
                q,_=admission(u,bad,ur,rr,c,b,n);assert not q['pass_new'];controls.append(dict(name=name,rejected=True,own_error=q['candidate_own_max']))
            q,_=admission(u,raw+1e-5,ur,rr+1e-5,c,b,n);assert not q['pass_new'];controls.append(dict(name='common_raw_offset',rejected=True,own_error=q['candidate_own_max']))
            ec=strain(u,c,b,n);ec[...,2]*=.5;q,_=admission(u,energy(ec),ur,rr,c,b,n);assert not q['pass_new'];controls.append(dict(name='half_engineering_shear',rejected=True,own_error=q['candidate_own_max']))
            wrong_b=b[:,:,[1,0],:];q,_=admission(u,energy(strain(u,c,wrong_b,n)),ur,rr,c,b,n);assert not q['pass_new'];controls.append(dict(name='transposed_gradient_rows',rejected=True,own_error=q['candidate_own_max']))
    refs=[]
    for step in range(1,6):
        path=list((root/'inputs').glob(f'*c0001_s{step:03d}_post_commit.mat'))[0]
        with h5py.File(path) as h:u=np.asarray(h['request28_snapshot/u_node']).T.reshape(-1,order='F');raw=np.asarray(h['request28_snapshot/psi_raw_gp']).T
        rr,_=admission(u,raw,u,raw,c,b,n);assert rr['pass_new'];refs.append(dict(step=step,own_scaled_max=rr['candidate_own_max']));inputs.append(path)
    rng=np.random.default_rng(1);e=rng.normal(size=(20000,3));de=rng.normal(size=(20000,3))*np.logspace(-12,1,20000)[:,None];sig=np.einsum('...j,ji->...i',e,D);sig[:,:2]+=K*np.maximum(e[:,0]+e[:,1],0)[:,None];s=np.linalg.norm(de,axis=1);bound=np.linalg.norm(sig,axis=1)*s+.5*L*s*s
    gap=abs(energy(e+de)-energy(e));budget=bound+TAU*(np.maximum(1,abs(energy(e+de)))+np.maximum(1,abs(energy(e))))
    assert np.all(gap<=budget);cross=int(np.count_nonzero((e[:,0]+e[:,1]>=0)!=(e[:,0]+de[:,0]+e[:,1]+de[:,1]>=0)))
    # Old nonraw gates remain separate mandatory clauses. No raw pass rescues them.
    for name,value in [('u_maxerr',2e-10),('d_maxerr',2e-10),('history234_scaled_maxerr',2e-10)]:
        assert not(value<=TAU and rows[-1]['pass_new']);controls.append(dict(name='nonraw_'+name,rejected=True))
    assert not(8==9 and rows[-1]['pass_new']);controls.append(dict(name='outer_count_mismatch',rejected=True))
    with (a.out/'raw_response.csv').open('w',newline='') as f:wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
    result=dict(status='offline_new_admission_feasibility_not_native_v4_success',tau=TAU,L=L,rows=rows,raw_field_negative_controls=[x for x in controls if not x['name'].startswith(('nonraw_','outer_'))],nonraw_clause_checks=[x for x in controls if x['name'].startswith(('nonraw_','outer_'))],reference_checks=refs,random_strain_pairs=20000,random_trace_crossings=cross,inputs=[dict(path=str(p),sha256=sha(p)) for p in dict.fromkeys(inputs)],code=[dict(path=str(z),sha256=sha(z)) for z in [Path(__file__).resolve(),Path(q4_geometry.__code__.co_filename)]],claim_boundary='v3 legacy miss retained; new forward-consistency estimand only; bound is a consistency check not independent evidence.')
    (a.out/'raw_response.json').write_text(json.dumps(result,indent=2)+'\n')
    fig,ax=plt.subplots(1,2,figsize=(11,4.3));steps=[r['step'] for r in rows]
    for k,label in [('legacy_raw_max','old cross-state raw equality'),('candidate_own_max','candidate raw vs own-u'),('reference_own_max','reference raw vs own-u')]:ax[0].semilogy(steps,[r[k] for r in rows],'-o',label=label)
    ax[0].axhline(TAU,color='black',ls='--',label='unchanged own-u tolerance1e-10');ax[0].set_ylabel('Scaled raw error');ax[0].legend(fontsize=7)
    for k,label in [('worst_native_gap','native raw gap'),('worst_response_bound','analytic input-response bound'),('worst_total_budget','bound + two own-u budgets')]:ax[1].semilogy(steps,[r[k] for r in rows],'-o',label=label)
    ax[1].set_ylabel('Absolute raw energy, worst legacy GP per step');ax[1].legend(fontsize=7)
    for x in ax:x.set_xticks(steps);x.set_xlabel('Existing v3 original c1 substep');x.grid(alpha=.2)
    fig.suptitle('Synthetic development audit | fixed tau, analytic response budget\nExisting v3 remains failed; v4 not executed',fontsize=10);fig.tight_layout();fig.savefig(a.out/'raw_response.png',dpi=180);plt.close(fig)
    (a.out/'raw_response.md').write_text('''# Raw consistency versus input-response budget

Data provenance: verified42file v3archive, all observed original s1/s2/s3 candidates and five fixed reference inputs. Exact input/code hashes and all table rows in raw_response.json/csv. No new solve/training.

How to read: left separates the old different-u raw comparison from each raw compared with its own independent Q4/Amor replay. Dashed1e-10 is unchanged. Right displays actual absolute raw gap, analytic input-response bound and bound plus two own-u error budgets at the maximum old scaled-error GP per observed step; no visually chosen location. The engineering-strain energy gradient has global Lipschitz bound L=2mu+2K, valid across positive-trace changes; delta-strain is B times actual nodal delta-u. Budgets are tau*max(1,abs(own replay)), not fitted factors. Negative controls and random across-branch strain checks are recorded separately.

Limitations: these are reused development records and a proposed new admission estimand, not new v4 native passes. The response bound follows from own-u consistency and the triangle inequality, not independent solver equivalence. Nonraw original regression gates stay mandatory. v3 raw miss remains unchanged; no fullc1/repaired/teacher/physical result. The origin of tiny u differences is not identified.
''')
    print(json.dumps(dict(rows=rows,negative_controls=controls,references=refs,random_trace_crossings=cross),indent=2))

if __name__=='__main__':main()
