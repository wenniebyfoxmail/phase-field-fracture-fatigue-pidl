#!/usr/bin/env python3
"""Offline admission/comparison of fixed-u native damage repairs; no solve."""
import argparse,csv,hashlib,json
from pathlib import Path
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from audit_phase_tangent import assemble
from run_multicycle_cross_replay import q4_geometry,interp
from audit_fem_final_residuals import projected_gradient
from localize_endpoint_tight import mechanics_force


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--capture-run',type=Path,required=True);ap.add_argument('--mesh',type=Path,required=True);a=ap.parse_args()
    out=a.run/'analysis';out.mkdir(exist_ok=True)
    with h5py.File(a.mesh) as h:
        points=np.asarray(h['node_coords']).T;conn=np.asarray(h['connectivity_q4']).T.astype(int)-1
    N,B,w,xy=q4_geometry(points,conn);n=len(points);rows=[];missing=[];provenance=[a.mesh];fields={}
    for cycle in [1,83]:
        for stage in ['baseline','last_accepted']:
            old=a.capture_run/'retrieved/output'/f'c{cycle}_{stage}'/'projection_capture.mat'
            with h5py.File(old) as h:
                assert np.array_equal(points,np.asarray(h['node_coords']).T)
                uv=np.asarray(h['u_return']).reshape(-1);raw=np.asarray(h['raw_return']).T
                lower=np.asarray(h['frozen/p_field_old']).reshape(-1);hist=np.asarray(h['frozen/history_vars_old']).transpose(2,1,0)
                idx=np.asarray(h['initial_oracle/free_dof_d']).reshape(-1).astype(int)-1
                fu=np.asarray(h['initial_oracle/free_dof_u']).reshape(-1).astype(int)-1
                oldd=np.asarray(h['d_clipped']).reshape(-1)
                oldr=np.asarray(h['r_clipped']).reshape(-1)
            rr,_=assemble(oldd,raw,lower,hist,conn,N,B,w,n)
            assert np.max(np.abs(rr-oldr))<1e-10
            legacy_phase=np.linalg.norm(projected_gradient(oldd[idx],oldr[idx],lower[idx]))
            active_old=(1-interp(oldd,conn,N))**2*raw
            provenance.append(old)
            for mode in ['fresh_only','constrained']:
                root=a.run/'retrieved/output'/f'c{cycle}_{stage}'/mode
                if not (root/'result.json').exists():
                    missing.append(str(root));continue
                s=json.loads((root/'result.json').read_text(encoding='utf-8-sig'));p=root/'damage_repair.mat'
                with h5py.File(p) as h:
                    d=np.asarray(h['out/d']).reshape(-1);dc=np.asarray(h['dc']).reshape(-1)
                    native=np.asarray(h['r_fresh']).reshape(-1);native_clip=np.asarray(h['r_clip']).reshape(-1)
                    actual_calls=int(np.asarray(h['out/calls']).item())
                    native_ru=np.asarray(h['ru']).reshape(-1)
                    newhist=np.asarray(h['h_clip']).transpose(2,1,0)
                    assert np.array_equal(uv,np.asarray(h['fixed_u']).reshape(-1))
                    assert np.array_equal(raw,np.asarray(h['fixed_raw']).T)
                    assert np.array_equal(hist,np.asarray(h['frozen/history_vars_old']).transpose(2,1,0))
                    assert np.array_equal(lower,np.asarray(h['frozen/p_field_old']).reshape(-1))
                assert np.array_equal(dc,np.clip(d,lower,1))
                assert actual_calls+2==s['total_phase_calls']
                infeasible=int(np.count_nonzero((d<lower-1e-12)|(d>1+1e-12)))
                assert infeasible==s['infeasible_nodes']
                r,_=assemble(d,raw,lower,hist,conn,N,B,w,n);rc,st=assemble(dc,raw,lower,hist,conn,N,B,w,n)
                err=max(np.max(np.abs(r-native)),np.max(np.abs(rc-native_clip)))
                assert np.max(np.abs(mechanics_force(uv,dc,conn,N,B,w,n)[fu]-native_ru[fu]))<1e-10
                assert abs(np.linalg.norm(native_ru[fu])-s['mechanical_l2'])<1e-10
                assert np.max(np.abs(newhist[:,:,1]-st['alpha']))<1e-10
                assert np.max(np.abs(newhist[:,:,2]-st['active']))<1e-10
                assert np.max(np.abs(newhist[:,:,3]-st['f']))<1e-10
                assert err<1e-10 and s['history_commits']==0 and s['total_phase_calls']<=250
                fresh=np.linalg.norm(projected_gradient(d[idx],r[idx],lower[idx]));clipped=np.linalg.norm(projected_gradient(dc[idx],rc[idx],lower[idx]))
                assert bool(s['phase_pass'])==bool(infeasible==0 and fresh<=4e-6 and not s['failure'])
                if mode=='constrained':assert infeasible==0 and np.array_equal(d,dc)
                assert abs(fresh-s['fresh_filtered_l2'])<1e-10 and abs(clipped-s['clipped_filtered_l2'])<1e-10
                active=(1-interp(dc,conn,N))**2*raw
                rel=np.sqrt(np.sum(w*(active-active_old)**2)/max(np.sum(w*active_old**2),1e-30))
                xa=active-np.sum(w*active)/w.sum();xb=active_old-np.sum(w*active_old)/w.sum()
                corr=np.sum(w*xa*xb)/max(np.sqrt(np.sum(w*xa**2)*np.sum(w*xb**2)),1e-30)
                row=dict(cycle=cycle,stage=stage,mode=mode,stop=s['stop'],phase_pass=s['phase_pass'],phase_calls=s['total_phase_calls'],legacy_phase_l2=legacy_phase,fresh_phase_l2=float(fresh),clipped_phase_l2=float(clipped),ratio_vs_legacy=float(clipped/max(legacy_phase,1e-30)),infeasible_nodes=s['infeasible_nodes'],mechanical_l2=s['mechanical_l2'],active_integral=float(np.sum(w*active)),legacy_active_integral=float(np.sum(w*active_old)),active_weighted_relL2_vs_legacy=float(rel),active_weighted_correlation_vs_legacy=float(corr),native_replay_maxerr=float(err))
                rows.append(row);provenance.extend([p,root/'result.json']);fields[f'c{cycle}_{stage}_{mode}_d']=dc;fields[f'c{cycle}_{stage}_{mode}_active']=active
    assert rows,'No retrieved arm outputs'
    with (out/'comparison.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (out/'summary.json').write_text(json.dumps(dict(rows=rows,missing_or_failed_arms=missing,scope='fixed captured u/raw, independent subproblem endpoints; no coupled convergence/teacher claim',provenance={str(p):sha(p) for p in provenance},analysis_code_sha256=sha(Path(__file__))),indent=2)+'\n')
    np.savez_compressed(out/'comparison_fields.npz',**fields)
    fig,ax=plt.subplots(figsize=(9,4));x=np.arange(len(rows));ax.bar(x,[r['clipped_phase_l2'] for r in rows],label='new endpoint, after bounds')
    ax.scatter(x,[r['legacy_phase_l2'] for r in rows],marker='_',color='black',label='v2 native + clip')
    ax.axhline(4e-6,color='red',linestyle='--',label='fixed phase screen 4e-6');ax.set_yscale('log');ax.set_ylabel('fresh nodal feasible phase residual L2')
    ax.set_xticks(x,[f"c{r['cycle']} {r['stage']}\n{r['mode']}" for r in rows],rotation=25,ha='right',fontsize=7);ax.legend(fontsize=8);fig.tight_layout();fig.savefig(out/'damage_repair_comparison.png',dpi=170);plt.close(fig)
    (out/'damage_repair_comparison.md').write_text('# Fixed-u damage repair comparison\n\nQuestion: does fresh stopping alone or true nodal-bound solving close the phase subproblem?\n\nProvenance: exact run, capture and mesh hashes in summary.json; all available predeclared states shown; absent c83 after a c1 stop remains unavailable. Bars: new post-bounds endpoints; black markers: v2 native/clipped baseline; red: predeclared 4e-6 phase screen. Log y, same units. Tables contain pre-clip feasibility, actual assembly counts, mechanical imbalance and active-field changes.\n\nNumerical takeaway: see authoritative comparison.csv and summary.json; raw low residual at an infeasible endpoint is not constrained convergence.\n\nLimitations: each state freezes captured u/raw and original s3 history, independent outputs not propagated. The continuous projected line-search merit is not the primary residual. Passing damage does not qualify coupled mechanics, teacher or trajectory.\n')
    print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
