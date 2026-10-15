#!/usr/bin/env python3
"""Offline coupled-repair admission and frozen-state comparisons; no field solve."""
import argparse,csv,hashlib,json
from pathlib import Path
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from audit_phase_tangent import assemble
from run_multicycle_cross_replay import q4_geometry,interp,amor_raw
from audit_fem_final_residuals import projected_gradient
from localize_endpoint_tight import mechanics_force


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def arr(group,key):return np.asarray(group[key])
def vec(group,key):return arr(group,key).reshape(-1)
def scalar(group,key):return arr(group,key).item()
def decode(group,key):
    value=group[key];assert value.attrs.get('MATLAB_class') in [b'char','char'], 'Require explicit MATLAB char, never opaque string'
    if empty(value):return ''
    return ''.join(chr(int(v)) for v in np.asarray(value).reshape(-1))
def empty(obj):return bool(obj.attrs.get('MATLAB_empty',0)) if isinstance(obj,h5py.Dataset) else False

def csv_write(path,rows):
    if rows:
        with path.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def compare(ref,cand,w):
    ir=float(np.sum(w*ref));ic=float(np.sum(w*cand));ar=ref-ir/w.sum();ac=cand-ic/w.sum()
    den=float(np.sqrt(np.sum(w*ar**2)*np.sum(w*ac**2)))
    return dict(reference_integral=ir,candidate_integral=ic,candidate_over_reference=ic/ir,
        relative_l2=float(np.sqrt(np.sum(w*(cand-ref)**2)/np.sum(w*ref**2))),
        correlation=float(np.sum(w*ar*ac)/den) if den else None)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--prior-run',type=Path,required=True);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--pidl',type=Path);a=p.parse_args()
    out=a.run/'analysis';out.mkdir(exist_ok=True)
    rows=[];traces=[];missing=[];inputs=[a.mesh];case_pass={};pidl={}
    with h5py.File(a.mesh) as h:
        points=arr(h,'node_coords').T;c=arr(h,'connectivity_q4').T.astype(int)-1
    n=len(points);N,B,w,xy=q4_geometry(points,c)
    assert n==86756 and len(c)==86408
    if a.pidl:
        meta=a.pidl.with_suffix('.json');m=json.loads(meta.read_text());assert m['output_sha256']==sha(a.pidl)
        assert m['state']=='peak checkpoint/model at step 5*c-1, U=0.12'
        with np.load(a.pidl) as z:
            assert str(z['topology'][0])=='q4' and np.max(np.abs(z['node_coords']-points))<2e-8
            for cycle in [1,83]:
                ii=np.flatnonzero(z['cycles']==cycle);assert len(ii)==1;ii=int(ii[0]);assert z['steps'][ii]==5*cycle-1
                pidl[cycle]=amor_raw(z['u_node'][ii],z['v_node'][ii],c,B)*(1-interp(z['d_node'][ii],c,N))**2
                assert np.isfinite(pidl[cycle]).all()
        inputs.extend([a.pidl,meta])
    for cycle in [1,83]:
        for stage in ['baseline','last_accepted']:
            name=f'c{cycle}_{stage}';root=a.run/'retrieved/output'/name
            path=root/'coupled_result.mat';sj=root/'coupled_result.json'
            if not path.exists() or not sj.exists():missing.append(name);continue
            if cycle==83:assert all(case_pass.get(f'c1_{s}',False) for s in ['baseline','last_accepted']),'c1 prerequisite absent'
            prior=a.prior_run/'retrieved/output'/name/'constrained/damage_repair.mat'
            s=json.loads(sj.read_text(encoding='utf-8-sig'));assert s['cycle']==cycle and s['stage']==stage
            with h5py.File(prior) as old,h5py.File(path) as h:
                assert decode(h['source_identity'],'prior_repair_sha256')==sha(prior)
                assert scalar(h['source_identity'],'cycle')==cycle and decode(h['source_identity'],'stage')==stage
                lower=vec(h,'frozen/p_field_old');hist=arr(h,'frozen/history_vars_old').transpose(2,1,0)
                assert np.array_equal(lower,vec(old,'frozen/p_field_old')) and np.array_equal(hist,arr(old,'frozen/history_vars_old').transpose(2,1,0))
                fu=vec(h,'free_dof_u').astype(int)-1;fd=vec(h,'free_dof_d').astype(int)-1
                fixed_u=np.setdiff1d(np.arange(2*n),fu);fixed_d=np.setdiff1d(np.arange(n),fd)
                old_u=vec(old,'fixed_u');old_d=vec(old,'dc');old_raw=arr(old,'fixed_raw').T
                old_active=(1-interp(old_d,c,N))**2*old_raw
                old_ru=float(np.linalg.norm(vec(old,'ru')[fu]));old_phase=float(np.linalg.norm(projected_gradient(old_d[fd],vec(old,'r_clip')[fd],lower[fd])))
                assert s['history_commits']==0 and scalar(h['out'],'history_commits')==0
                assert s['total_u_calls']==scalar(h['out/counts'],'u')+1<=250
                assert s['total_d_calls']==scalar(h['out/counts'],'d')+1<=250
                assert s['admission_u_calls']==1 and s['admission_d_calls']==2
                assert s['completed_outer']==scalar(h['out'],'completed_outer')<=20
                assert s['stop']==decode(h['out'],'stop_char') and s['failure']==decode(h['out'],'failure_char')
                for label in ['initial','first_u','first_block','final']:
                    g=h['out/'+label]
                    if empty(g):continue
                    u=vec(g,'u');d=vec(g,'d');raw=arr(g,'raw').T;ru=vec(g,'ru');rd=vec(g,'rd');ht=arr(g,'history234').transpose(2,1,0)
                    assert all(np.isfinite(x).all() for x in [u,d,raw,ru,rd,ht])
                    assert np.all(d>=lower-1e-12) and np.all(d<=1+1e-12)
                    assert np.array_equal(u[fixed_u],old_u[fixed_u]) and np.array_equal(d[fixed_d],old_d[fixed_d])
                    if label=='initial':assert np.array_equal(u,old_u) and np.array_equal(d,old_d)
                    rr,st=assemble(d,raw,lower,hist,c,N,B,w,n);rf=mechanics_force(u,d,c,N,B,w,n);expected_raw=amor_raw(u[:n],u[n:],c,B)
                    rawerr=float(np.max(np.abs(raw-expected_raw)/np.maximum(1,np.abs(expected_raw))))
                    err=float(max(np.max(np.abs(rr-rd)),np.max(np.abs(rf-ru))))
                    assert max(rawerr,err)<1e-10
                    assert max(np.max(np.abs(ht[:,:,j]-st[k])) for j,k in enumerate(['alpha','active','f']))<1e-10
                    ur=float(np.linalg.norm(ru[fu]));dr=float(np.linalg.norm(projected_gradient(d[fd],rd[fd],lower[fd])));criterion=max((ur+dr)/4e-6,ur/1e-8)
                    assert abs(ur-scalar(g,'u_l2'))<1e-10 and abs(dr-scalar(g,'d_feasible_l2'))<1e-10
                    assert abs(criterion-scalar(g,'criterion'))<1e-8*max(1,criterion)
                    assert bool(scalar(g,'joint_pass'))==(criterion<=1)
                    active=st['active'];replay_dr=float(np.linalg.norm(projected_gradient(d[fd],rr[fd],lower[fd])))
                    row=dict(cycle=cycle,stage=stage,snapshot=label,completed_joint=label!='first_u',outer=int(scalar(g,'outer')),native_u_l2=ur,native_d_feasible_l2=dr,replay_u_l2=float(np.linalg.norm(rf[fu])),replay_d_feasible_l2=replay_dr,sum_l2=ur+dr,criterion=criterion,joint_field_pass=criterion<=1,prior_fixed_u_l2=old_ru,prior_fixed_raw_phase_l2=old_phase,u_maxdelta_vs_prior=float(np.max(np.abs(u-old_u))),d_maxdelta_vs_prior=float(np.max(np.abs(d-old_d))),active_integral=float(np.sum(w*active)),prior_active_integral=float(np.sum(w*old_active)),native_replay_maxerr=err,raw_scaled_maxerr=rawerr,**{'active_vs_prior_'+k:v for k,v in compare(old_active,active,w).items()})
                    di=int(np.argmax(np.abs(d-old_d)));ui=int(np.argmax(np.hypot(u[:n]-old_u[:n],u[n:]-old_u[n:])))
                    # A constrained x component must not discard a node's free y component.
                    ru_free=ru.copy();ru_free[fixed_u]=0;fi=int(np.argmax(np.hypot(ru_free[:n],ru_free[n:])))
                    row.update(d_maxdelta_x=float(points[di,0]),d_maxdelta_y=float(points[di,1]),u_maxdelta_x=float(points[ui,0]),u_maxdelta_y=float(points[ui,1]),ru_peak_x=float(points[fi,0]),ru_peak_y=float(points[fi,1]))
                    if cycle in pidl:
                        row.update({'active_vs_pidl_'+k:v for k,v in compare(pidl[cycle],active,w).items()})
                        row['active_relL2_fem_denominator_vs_pidl']=float(np.sqrt(np.sum(w*(active-pidl[cycle])**2)/max(np.sum(w*active**2),1e-30)))
                        row['pidl_over_fem_integral_minus1']=float(np.sum(w*pidl[cycle])/max(np.sum(w*active),1e-30)-1)
                    if label=='final':
                        assert abs(ur-s['u_l2'])<1e-10 and abs(dr-s['d_feasible_l2'])<1e-10
                        assert np.array_equal(ru,vec(h,'audited_final/ru')) and np.array_equal(rd,vec(h,'audited_final/rd'))
                        assert bool(s['joint_pass'])==bool(criterion<=1 and s['stop']=='joint_tolerance' and not s['failure'])
                    rows.append(row)
                # Scalar traces are MATLAB struct arrays (references for >1 item).
                t=h['out/trace'];length=s['completed_outer']
                if length:
                    assert isinstance(t,h5py.Group)
                    assert all(np.asarray(t[k]).size==length for k in t.keys())
                    for i in range(length):
                        r=dict(cycle=cycle,stage=stage)
                        for k in ['outer','u_l2','d_feasible_l2','sum_l2','criterion','calls_u','calls_d','u_delta_max','d_delta_max']:
                            ds=t[k];value=ds[()].reshape(-1)[i]
                            r[k]=np.asarray(h[value]).item() if isinstance(value,h5py.Reference) else value.item()
                        assert r['calls_u']<=249 and r['calls_d']<=249 and np.isfinite(list(r.values())[2:]).all()
                        assert abs(r['sum_l2']-r['u_l2']-r['d_feasible_l2'])<1e-10
                        assert abs(r['criterion']-max(r['sum_l2']/4e-6,r['u_l2']/1e-8))<1e-8*max(1,r['criterion'])
                        assert int(r['outer'])==i+1
                        traces.append(r)
                if length:
                    final=h['out/final'];last=traces[-1]
                    assert last['outer']==scalar(final,'outer')==length
                    for key in ['u_l2','d_feasible_l2','sum_l2','criterion']:
                        assert abs(last[key]-scalar(final,key))<1e-10*max(1,abs(last[key]))
                    assert last['calls_u']==scalar(final['calls'],'u') and last['calls_d']==scalar(final['calls'],'d')
                case_pass[name]=bool(s['joint_pass'])
            inputs.extend([path,sj,prior])
    csv_write(out/'coupled_snapshots.csv',rows);csv_write(out/'coupled_outer_trace.csv',traces)
    terminal=a.run/'retrieved/coupled_finished.json';failure=a.run/'retrieved/coupled_failure.json'
    terminal_state=json.loads(terminal.read_text(encoding='utf-8-sig')) if terminal.exists() else None
    if terminal_state:
        inputs.append(terminal);assert terminal_state['states']==len(case_pass) and terminal_state['history_commits']==0
        assert bool(terminal_state['c1_pass'])==all(case_pass.get(f'c1_{s}',False) for s in ['baseline','last_accepted'])
        if terminal_state['status']=='completed':assert len(case_pass)==4 and not missing
        else:assert terminal_state['status']=='c1_negative_c83_skipped' and len(case_pass)==2 and not terminal_state['c1_pass']
    result=dict(status='offline_checked' if terminal_state else 'partial_no_terminal_success',case_pass=case_pass,missing=missing,terminal=terminal_state,producer_failure_marker=failure.exists(),history_commits=0,inputs=[dict(path=str(f),sha256=sha(f),bytes=f.stat().st_size) for f in dict.fromkeys(inputs)])
    (out/'coupled_analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    if rows:
        fig,axs=plt.subplots(2,2,figsize=(10,7),sharex=True)
        for ax,(cycle,stage) in zip(axs.flat,[(1,'baseline'),(1,'last_accepted'),(83,'baseline'),(83,'last_accepted')]):
            initial=[r for r in rows if r['cycle']==cycle and r['stage']==stage and r['snapshot']=='initial'];rr=[r for r in traces if r['cycle']==cycle and r['stage']==stage]
            if initial:
                x=[0]+[r['outer'] for r in rr]
                ax.semilogy(x,[initial[0]['criterion']]+[r['criterion'] for r in rr],'-o',label='joint criterion C')
                ax.axhline(1,color='black',ls='--',label='C = 1')
            else:ax.text(.1,.5,'Not executed / unavailable',transform=ax.transAxes)
            ax.set_title(f'c{cycle} {stage}');ax.set_xlabel('Completed u→d blocks');ax.set_ylabel('C (dimensionless)');ax.grid(alpha=.2)
        fig.tight_layout();fig.savefig(out/'coupled_closure.png',dpi=180);plt.close(fig)
        (out/'coupled_closure.md').write_text('# Coupled closure diagnostic\n\nData provenance: coupled_snapshots.csv and coupled_outer_trace.csv; exact input SHA256 in coupled_analysis.json.\n\nHow to read: C=max((Ru+Rd_feasible)/4e-6,Ru/1e-8). Only full same-field blocks are connected; u-only/failed trials are excluded. Missing c83 is shown explicitly.\n\nLimitations: frozen s3 history; no trajectory propagation, teacher qualification or physical truth. Strict coupled criterion differs from prior phase-only test.\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
