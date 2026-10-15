#!/usr/bin/env python3
"""Offline admission/comparison of fixed-u native damage repairs; no solve."""
import argparse,csv,hashlib,json
from pathlib import Path
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from audit_phase_tangent import assemble
from run_multicycle_cross_replay import q4_geometry,interp,amor_raw,comp
from audit_fem_final_residuals import projected_gradient
from localize_endpoint_tight import mechanics_force


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--capture-run',type=Path,required=True);ap.add_argument('--mesh',type=Path,required=True);ap.add_argument('--pidl',type=Path);a=ap.parse_args()
    out=a.run/'analysis';out.mkdir(exist_ok=True)
    with h5py.File(a.mesh) as h:
        points=np.asarray(h['node_coords']).T;conn=np.asarray(h['connectivity_q4']).T.astype(int)-1
    N,B,w,xy=q4_geometry(points,conn);n=len(points);rows=[];missing=[];provenance=[a.mesh];fields={};maps=[]
    mass=np.zeros(n);np.add.at(mass,conn.reshape(-1),np.einsum("eg,gi->ei",w,N).reshape(-1))
    pidl={}
    if a.pidl:
        pm=a.pidl.with_suffix('.json');metadata=json.loads(pm.read_text());assert metadata['output_sha256']==sha(a.pidl)
        assert metadata['state']=='peak checkpoint/model at step 5*c-1, U=0.12'
        provenance.append(pm)
        with np.load(a.pidl) as z:
            assert str(z['topology'][0])=='q4' and np.max(np.abs(z['node_coords']-points))<2e-8
            for cycle in [1,83]:
                ii=np.flatnonzero(z['cycles']==cycle);assert len(ii)==1;ii=int(ii[0]);assert z['steps'][ii]==5*cycle-1
                assert all(np.all(np.isfinite(z[k][ii])) for k in ['u_node','v_node','d_node'])
                pidl[cycle]=amor_raw(z['u_node'][ii],z['v_node'][ii],conn,B)*(1-interp(z['d_node'][ii],conn,N))**2
                assert np.all(np.isfinite(pidl[cycle]))
        provenance.append(a.pidl)
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
                old_ru=np.asarray(h['full_oracle/R_u_full']).reshape(-1)
            rr,oldst=assemble(oldd,raw,lower,hist,conn,N,B,w,n)
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
                    accepted=int(np.asarray(h['out/accepted']).item());iterations=int(np.asarray(h['out/iterations']).item())
                    native_ru=np.asarray(h['ru']).reshape(-1)
                    newhist=np.asarray(h['h_clip']).transpose(2,1,0)
                    raw_check=np.asarray(h['raw_check']).T
                    assert np.array_equal(uv,np.asarray(h['fixed_u']).reshape(-1))
                    assert np.array_equal(raw,np.asarray(h['fixed_raw']).T)
                    assert np.array_equal(hist,np.asarray(h['frozen/history_vars_old']).transpose(2,1,0))
                    assert np.array_equal(lower,np.asarray(h['frozen/p_field_old']).reshape(-1))
                assert all(np.all(np.isfinite(v)) for v in [d,dc,native,native_clip,native_ru,newhist[:,:,1:4],raw_check])
                expected_raw=amor_raw(uv[:n],uv[n:],conn,B)
                raw_identity_error=float(np.max(np.abs(raw_check-expected_raw)/np.maximum(1,np.abs(expected_raw))))
                assert raw_identity_error<1e-10,'Independent refreshed-raw identity mismatch'
                assert np.array_equal(dc,np.clip(d,lower,1))
                assert actual_calls+2==s['total_phase_calls']
                infeasible=int(np.count_nonzero((d<lower-1e-12)|(d>1+1e-12)))
                assert infeasible==s['infeasible_nodes']
                r,_=assemble(d,raw,lower,hist,conn,N,B,w,n);rc,st=assemble(dc,raw,lower,hist,conn,N,B,w,n)
                err=max(np.max(np.abs(r-native)),np.max(np.abs(rc-native_clip)))
                mechanics_error=float(np.max(np.abs(mechanics_force(uv,dc,conn,N,B,w,n)[fu]-native_ru[fu])))
                assert mechanics_error<1e-10
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
                row=dict(cycle=cycle,stage=stage,mode=mode,native_fresh_bound_filtered_l2=s['fresh_filtered_l2'],native_clipped_phase_l2=s['clipped_filtered_l2'],stop=s['stop'],phase_pass=s['phase_pass'],phase_calls=s['total_phase_calls'],optimization_calls=actual_calls,accepted_updates=accepted,iterations=iterations,legacy_phase_l2=legacy_phase,fresh_phase_l2=float(fresh),clipped_phase_l2=float(clipped),ratio_vs_legacy=float(clipped/max(legacy_phase,1e-30)),infeasible_nodes=s['infeasible_nodes'],mechanical_l2=s['mechanical_l2'],active_integral=float(np.sum(w*active)),legacy_active_integral=float(np.sum(w*active_old)),active_weighted_relL2_vs_legacy=float(rel),active_weighted_correlation_vs_legacy=float(corr),native_replay_maxerr=float(err))
                old_u=float(np.linalg.norm(old_ru[fu]));sum_old=old_u+legacy_phase;sum_new=s['mechanical_l2']+clipped
                r_refreshed,_=assemble(dc,raw_check,lower,hist,conn,N,B,w,n)
                ref_phase=float(np.linalg.norm(projected_gradient(dc[idx],r_refreshed[idx],lower[idx])))
                delta=dc-oldd;imax=int(np.argmax(np.abs(delta)))
                row.update(native_mechanics_replay_maxerr=mechanics_error,raw_check_scaled_identity_error=raw_identity_error,fatigue_factor_change_maxabs=float(np.max(np.abs(st['f']-oldst['f']))),alpha_accumulator_change_maxabs=float(np.max(np.abs(st['alpha']-oldst['alpha']))),active_driver_change_maxabs=float(np.max(np.abs(st['active']-oldst['active']))),legacy_mechanical_l2=old_u,mechanical_ratio_vs_legacy=s['mechanical_l2']/old_u,descriptive_sum_l2=float(sum_new),legacy_descriptive_sum_l2=float(sum_old),sum_ratio_vs_legacy=float(sum_new/sum_old),source_refreshed_phase_l2=ref_phase,source_refresh_phase_vector_maxdelta=float(np.max(np.abs(r_refreshed-rc))),damage_maxabs=float(abs(delta[imax])),damage_max_x=float(points[imax,0]),damage_max_y=float(points[imax,1]))
                assert abs(row['damage_maxabs']-s['d_vs_old_clipped_maxabs'])<1e-12
                if mode=='constrained' and stage=='last_accepted':
                    vo=np.zeros(2*n);vn=np.zeros(2*n);vo[fu]=old_ru[fu];vn[fu]=native_ru[fu]
                    mo=np.sqrt((vo[:n]**2+vo[n:]**2)/np.maximum(mass,1e-30));mn=np.sqrt((vn[:n]**2+vn[n:]**2)/np.maximum(mass,1e-30))
                    maps.append((cycle,delta,np.sum(w*(active-active_old),axis=1)/w.sum(axis=1),mn-mo))
                if pidl:
                    pc=comp(active,pidl[cycle],w);po=comp(active_old,pidl[cycle],w)
                    pnorm=max(float(np.sum(w*pidl[cycle]**2)),1e-30)
                    row.update(pidl_global_step=5*cycle-1,pidl_active_integral=pc['pidl_integral'],pidl_integral_delta_pct=pc['delta_pct'],legacy_pidl_integral_delta_pct=po['delta_pct'],pidl_relative_l2=pc['relative_l2'],legacy_pidl_relative_l2=po['relative_l2'],pidl_correlation=pc['correlation'],legacy_pidl_correlation=po['correlation'],pidl_fixednorm_gap=float(np.sqrt(np.sum(w*(active-pidl[cycle])**2)/pnorm)),legacy_pidl_fixednorm_gap=float(np.sqrt(np.sum(w*(active_old-pidl[cycle])**2)/pnorm)))
                rows.append(row);provenance.extend([p,root/'result.json']);fields[f'c{cycle}_{stage}_{mode}_d']=dc;fields[f'c{cycle}_{stage}_{mode}_active']=active
    assert rows,'No retrieved arm outputs'
    with (out/'comparison.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (out/'summary.json').write_text(json.dumps(dict(rows=rows,missing_or_failed_arms=missing,scope='fixed captured u/raw, independent subproblem endpoints; no coupled convergence/teacher claim',provenance={str(p):sha(p) for p in provenance},analysis_code_hashes={str(p):sha(p) for p in [Path(__file__),Path(__file__).with_name("audit_phase_tangent.py"),Path(__file__).with_name("run_multicycle_cross_replay.py"),Path(__file__).with_name("audit_fem_final_residuals.py"),Path(__file__).with_name("localize_endpoint_tight.py")]}),indent=2)+'\n')
    np.savez_compressed(out/'comparison_fields.npz',**fields)
    fig,ax=plt.subplots(figsize=(10,4.5));x=np.arange(len(rows));ax.bar(x,[r['clipped_phase_l2'] for r in rows],color=['#0072B2' if r['mode']=='constrained' else '#888888' for r in rows],label='new endpoint, after bounds')
    ax.set_ylim(1e-8,1e-4)
    for i,r in enumerate(rows):
        if r['clipped_phase_l2']<1e-8:
            ax.plot(i,1.05e-8,'v',color='#0072B2');ax.annotate(f"{r['clipped_phase_l2']:.2e}\nbelow display",(i,1.4e-8),ha='center',fontsize=7)
    ax.scatter(x,[r['legacy_phase_l2'] for r in rows],marker='_',color='black',label='v2 native + clip')
    ax.axhline(4e-6,color='red',linestyle='--',label='fixed phase screen 4e-6');ax.set_yscale('log');ax.set_ylabel('fresh nodal feasible phase residual L2')
    ax.set_xticks(x,[f"c{r['cycle']} {r['stage']}\n{r['mode']}" for r in rows],rotation=25,ha='right',fontsize=7);ax.legend(fontsize=8,loc='upper left');fig.suptitle('Fixed-u phase repair: all four saved peak states (synthetic)',fontsize=11);fig.tight_layout();fig.savefig(out/'damage_repair_comparison.png',dpi=170);plt.close(fig)
    (out/'damage_repair_comparison.md').write_text('# Fixed-u damage repair comparison\n\nQuestion: does fresh stopping alone or true nodal-bound solving close the phase subproblem?\n\nData provenance: exact run, capture and mesh hashes in summary.json; all available predeclared states shown; absent c83 after a c1 stop remains unavailable. How to read: bars: new post-bounds endpoints; black markers: v2 native/clipped baseline; red: predeclared 4e-6 phase screen. Log y with lower display limit1e-8; the below-range c1-last value is explicitly marked with its exact value, not raised numerically. Same units. Blue constrained, grey fresh-only. Tables contain pre-clip feasibility, actual assembly counts, mechanical imbalance and active-field changes.\n\nNumerical takeaway: exact pass counts and per-state values follow below and in comparison.csv/summary.json; raw low residual at an infeasible endpoint is not constrained convergence.\n\nLimitations: each state freezes captured u/raw and original s3 history, independent outputs not propagated. The continuous projected line-search merit is not the primary residual. Passing damage does not qualify coupled mechanics, teacher or trajectory.\n')
    if maps:
        fig,axes=plt.subplots(len(maps),3,figsize=(12,2.8*len(maps)),squeeze=False)
        limits=[max(float(np.max(np.abs(v[j+1]))) for v in maps) for j in range(3)]
        titles=['damage change vs v2 clip','GP cell-mean active change','mechanical mass-dual norm change']
        for i,(cycle,dd,da,dm) in enumerate(maps):
            for j,(coords,value) in enumerate([(points,dd),(points[conn].mean(axis=1),da),(points,dm)]):
                ax=axes[i,j];lim=max(limits[j],1e-30)
                artist=ax.scatter(coords[:,0],coords[:,1],c=value,s=2,cmap='RdBu_r',norm=Normalize(-lim,lim),rasterized=True)
                ax.set_xlim(-.5,.5);ax.set_ylim(-.03,.03);ax.set_xlabel('x');ax.set_ylabel('y')
                ax.set_title(f'c{cycle} last: '+titles[j],fontsize=9);fig.colorbar(artist,ax=ax,shrink=.75)
        fig.suptitle('Constrained minus v2 clipped endpoint; fixed captured u/raw; crack band only',fontsize=11)
        fig.tight_layout();fig.savefig(out/'damage_repair_spatial.png',dpi=180);plt.close(fig)
        (out/'damage_repair_spatial.md').write_text('# Damage and mechanical imbalance changes\n\nQuestion: where does the constrained endpoint differ from the v2 clipped endpoint? Data provenance: exact paired fields/hashes in summary.json; comparison_fields.npz retains all four states. Predetermined examples are c1/c83 last accepted saved peaks; both independent, not propagated.\n\nHow to read: rows c1/c83; columns signed nodal damage change, quadrature-weighted cell-mean active-driver change, change of nodal mechanical mass-dual norm (boundary reactions removed, free force components divided by sqrt Q4 lumped nodal mass before vector norm). Positive/red means higher, blue lower. Each column shares symmetric full-field max limits across both rows. Display crops y to[-.03,.03],x[-.5,.5] and magnifies the vertical direction (unequal aspect); coordinates are in the original nondimensional mesh frame. Metrics use full mesh. Active cell mean is a visualization reduction; integrals and errors use original GP weights. Units/scales differ by column.\n\nNumerical takeaway: damage stationary endpoints can coexist with mechanical imbalance; read scalar Ru ratios and exact damage maxima/coordinates in comparison.csv. Primary phase outcomes are tabulated below; no joint equilibrium is established. Limitations: spatial co-location alone is not a causal attribution. No teacher, physical validation or accepted history propagation.\n')
    if pidl:
        fig,ax=plt.subplots(1,2,figsize=(12,4));x=np.arange(len(rows));labels=[f"c{r['cycle']} {r['stage']}\n{r['mode']}" for r in rows]
        for k,(new,old,label) in enumerate([('pidl_relative_l2','legacy_pidl_relative_l2','weighted relL2 (FEM variant denominator)'),('pidl_fixednorm_gap','legacy_pidl_fixednorm_gap','weighted gap / fixed PIDL norm')]):
            ax[k].bar(x,[r[new] for r in rows],color=['#0072B2' if r['mode']=='constrained' else '#888888' for r in rows],label='new unaccepted endpoint')
            ax[k].scatter(x,[r[old] for r in rows],marker='_',color='black',label='v2 clipped endpoint')
            ax[k].set_xticks(x,labels,rotation=30,ha='right',fontsize=7);ax[k].set_ylabel(label);ax[k].legend(fontsize=7)
        fig.suptitle('Post-hoc description vs existing paired Q4 PIDL peaks; no new trajectory',fontsize=10)
        fig.tight_layout();fig.savefig(out/'damage_repair_pidl_gap.png',dpi=170);plt.close(fig)
        (out/'damage_repair_pidl_gap.md').write_text('# Existing PIDL field-gap description\n\nQuestion: does the fixed-u damage endpoint incidentally approach the existing PIDL active field? This is post-hoc descriptive comparison added after remote primary residual outcomes were viewed; no primary rule changes or new holdout. Data provenance: exact PIDL NPZ hash in summary.json. All four states and both arms shown. This paired run retains recovery at global step0; global_step(c,s)=5(c-1)+s. Checkpoints4/414 are c1s4/c83s4 peaks, not unloaded states; no generic index subtraction is used. Same Q4 GP assembly. The FEM candidates are unaccepted independent fixed-captured-u/raw endpoints; the PIDL states are from the frozen existing paired run.\n\nHow to read: blue constrained/grey fresh-only bars versus black v2-clipped markers. Left uses legacy comparison convention, ||PIDL-FEM||w/||FEM variant||w. Right fixes denominator to ||PIDL||w to expose denominator effects. Both use physical GP Jacobian weights over full mesh. Correlations/integrals are in comparison.csv. See exact table below for numerical changes.\n\nLimitations: lower field gap does not imply equilibrium or teacher qualification; the four phase screens cannot rescue worsening mechanical imbalance. No retraining, propagated updated trajectory or physical validation.\n')
    numeric='\n\nExact numerical comparison (table authoritative):\n\n|state|arm|fresh bound-filtered phase|infeasible nodes|post-clipped phase|native mechanical Ru|phase pass|\n|---|---|---:|---:|---:|---:|---|\n'
    for r in rows:numeric+=f"|c{r['cycle']} {r['stage']}|{r['mode']}|{r['fresh_phase_l2']:.12g}|{r['infeasible_nodes']}|{r['clipped_phase_l2']:.12g}|{r['mechanical_l2']:.12g}|{r['phase_pass']}|\n"
    for stem in ['damage_repair_comparison','damage_repair_spatial','damage_repair_pidl_gap']:
        sidecar=out/(stem+'.md')
        if sidecar.exists():
            extra=numeric
            if stem=='damage_repair_pidl_gap':
                extra+='\n\n|state|arm|old relL2|new relL2|old fixed-PIDL gap|new fixed-PIDL gap|\n|---|---|---:|---:|---:|---:|\n'
                for r in rows:extra+=f"|c{r['cycle']} {r['stage']}|{r['mode']}|{r['legacy_pidl_relative_l2']:.12g}|{r['pidl_relative_l2']:.12g}|{r['legacy_pidl_fixednorm_gap']:.12g}|{r['pidl_fixednorm_gap']:.12g}|\n"
            sidecar.write_text(sidecar.read_text()+extra)
    print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
