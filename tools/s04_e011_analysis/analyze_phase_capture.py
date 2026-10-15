#!/usr/bin/env python3
"""Analyze native four-state phase projection captures, without solving fields."""
import argparse,csv,json,hashlib
from pathlib import Path
import h5py,numpy as np,matplotlib.pyplot as plt
from audit_phase_tangent import assemble,phase_jvp,mechanics_jvp
from run_multicycle_cross_replay import q4_geometry,amor_raw,interp,grad
from localize_endpoint_tight import mechanics_force
from audit_fem_final_residuals import projected_gradient


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);a=ap.parse_args();out=a.run/'analysis';out.mkdir(exist_ok=True)
    rows=[];tangents=[];transitions=[];history_rows=[];maps=[];inputs=[]
    for cycle,stage in [(1,'baseline'),(1,'last_accepted'),(83,'baseline'),(83,'last_accepted')]:
        d=a.run/'retrieved/output'/f'c{cycle}_{stage}';p=d/'projection_capture.mat';s=json.loads((d/'phase_capture_result.json').read_text(encoding='utf-8-sig'));assert s['cycle']==cycle and s['stage']==stage and s['history_commits']==0
        with h5py.File(p) as h:
            vec=lambda key:np.asarray(h[key]).reshape(-1)
            points=np.asarray(h['node_coords']).T;c=np.asarray(h['connectivity']).T.astype(int)-1;n=len(points)
            material={k:float(vec('material/'+k)[0]) for k in ['Gc','ell','alpha_T','p','penalty_irrev','penalty_recov','res_stiff']}
            expected={'Gc':.01,'ell':.01,'alpha_T':.5,'p':2.,'penalty_irrev':421875.,'penalty_recov':13781.25,'res_stiff':0.}
            assert material==expected
            native_histories=[np.asarray(h[k]).transpose(2,1,0) for k in ['cached_history','h_return','h_clipped','h_refreshed']]
            native_tangents=[]
            tg=h['tangent_rows'];count=tg['epsilon'].size
            for j in range(count):
                native_tangents.append({k:float(np.asarray(h[np.asarray(tg[k]).reshape(-1)[j]]).item()) for k in tg.keys()})
            uv=vec('initial/displ');damage=vec('initial/p_field');lower=vec('frozen/p_field_old');hist=np.asarray(h['frozen/history_vars_old']).transpose(2,1,0)
            fu=vec('initial_oracle/free_dof_u').astype(int)-1;fd=vec('initial_oracle/free_dof_d').astype(int)-1
            ur=vec('u_return');dr=vec('d_return');dc=vec('d_clipped');dcached=vec('last_phase_eval/d')
            native_ru=vec('initial_oracle/R_u_free');native_rd=vec('initial_oracle/R_d_free');native_kuu=vec('native_kuu_jvp');native_kdd=vec('native_kdd_jvp')
            ru_final=vec('full_oracle/R_u_free');ru_full_final=vec('full_oracle/R_u_full');rs=[vec('last_phase_eval/r'),vec('r_return'),vec('r_clipped'),vec('full_oracle/R_d_full')]
            raw0=np.asarray(h['initial/strain_en_undgr']).T;rawret=np.asarray(h['raw_return']).T;rawnew=np.asarray(h['full_candidate/strain_en_undgr']).T
        N,B,w,xy=q4_geometry(points,c);du=ur-uv;dd=dc-damage
        mass=np.zeros(n)
        for j in range(4):np.add.at(mass,c[:,j],np.einsum('eg,g->e',w,N[:,j]))
        assert np.all(mass>0)
        assert np.sqrt(np.sum(w*(raw0-amor_raw(uv[:n],uv[n:],c,B))**2)/max(np.sum(w*raw0**2),1e-30))<=1e-10
        assert abs(np.linalg.norm(native_ru)-s['original_u_l2'])<1e-12 and abs(np.linalg.norm(ru_final)-s['direction_u_l2'])<1e-12
        assert np.count_nonzero(dr!=dc)==s['clipped_nodes'] and abs(np.max(np.abs(dr-dc))-s['clip_maxabs'])<1e-12
        assert np.array_equal(dc,np.minimum(np.maximum(dr,lower),1))
        assert np.all(np.isfinite(np.r_[uv,damage,ur,dr,dc,*rs]))
        rd0,st=assemble(damage,raw0,lower,hist,c,N,B,w,n);ru0=mechanics_force(uv,damage,c,N,B,w,n)
        if max(np.max(np.abs(rd0[fd]-native_rd)),np.max(np.abs(ru0[fu]-native_ru)))>1e-10:raise ValueError('Initial native residual admission failed')
        kuu,dpsi=mechanics_jvp(uv,damage,du,np.zeros(n),c,N,B,w,n)
        kud,_=mechanics_jvp(uv,damage,np.zeros(2*n),dd,c,N,B,w,n)
        kd=phase_jvp(dd,np.zeros_like(raw0),st,c,N,B,w,n,False);jd=phase_jvp(dd,np.zeros_like(raw0),st,c,N,B,w,n,True);ju=phase_jvp(np.zeros(n),dpsi,st,c,N,B,w,n,True)
        kdu_error=float(np.max(np.abs(kuu[fu]-native_kuu[fu])));kdd_error=float(np.max(np.abs(kd[fd]-native_kdd[fd])))
        product_equivalent=max(kdu_error,kdd_error)<=1e-10
        if not product_equivalent:
            (out/'native_product_admission_failure.json').write_text(json.dumps(dict(cycle=cycle,stage=stage,kuu_maxerr=kdu_error,kdd_maxerr=kdd_error)))
            raise ValueError('Native product mismatch; source-based tangent attribution unadmitted')
        rdata=[]
        for i,(r,ddamage,raw) in enumerate(zip(rs,[dcached,dr,dc,dc],[rawret,rawret,rawret,rawnew])):
            recomputed,info=assemble(ddamage,raw,lower,hist,c,N,B,w,n)
            err=float(np.max(np.abs(recomputed[fd]-r[fd])))
            # Cached NR may store pre-last evaluation, whose raw is the same fixed phase input.
            if err>1e-10:raise ValueError('Native phase transition replay mismatch')
            filt=projected_gradient(ddamage[fd],r[fd],lower[fd]);fr=float(np.linalg.norm(filt));rr=float(np.linalg.norm(r[fd]))
            assert abs(fr-s['rows'][i]['bound_filtered_phase_l2'])<1e-12
            assert abs(rr-s['rows'][i]['raw_phase_l2'])<1e-12
            row=dict(cycle=cycle,stage=stage,label=s['rows'][i]['label'],raw_phase_l2=rr,bound_filtered_phase_l2=fr,infeasible_nodes=int(np.count_nonzero((ddamage<lower-1e-12)|(ddamage>1+1e-12))),native_rd_replay_maxerr=err)
            transitions.append(row);rdata.append(filt)
        initial_merit=float(np.linalg.norm(native_ru)+np.linalg.norm(projected_gradient(damage[fd],native_rd,lower[fd])))
        final_merit=float(np.linalg.norm(ru_final)+np.linalg.norm(rdata[-1]))
        mech_final=mechanics_force(ur,dc,c,N,B,w,n);mech_before_d=mechanics_force(ur,damage,c,N,B,w,n)
        assert np.max(np.abs(mech_final[fu]-ru_final))<=1e-10
        row=dict(fresh_u_before_damage_l2=float(np.linalg.norm(mech_before_d[fu])),native_final_ru_replay_maxerr=float(np.max(np.abs(mech_final[fu]-ru_final))),cycle=cycle,stage=stage,phase_calls=s['phase_calls'],clipped_nodes=s['clipped_nodes'],clip_maxabs=s['clip_maxabs'],cached_phase_l2=s['rows'][0]['raw_phase_l2'],returned_raw_phase_l2=s['rows'][1]['raw_phase_l2'],clipped_feasible_phase_l2=s['rows'][2]['bound_filtered_phase_l2'],refreshed_feasible_phase_l2=s['rows'][3]['bound_filtered_phase_l2'],initial_u_l2=s['original_u_l2'],direction_u_l2=s['direction_u_l2'],initial_merit=initial_merit,direction_merit=final_merit,native_kuu_jvp_maxerr=kdu_error,native_kdd_jvp_maxerr=kdd_error,native_products_source_equivalent=product_equivalent,cached_to_return_field_maxabs=s['cached_to_return_field_maxabs'],raw_refresh_maxabs=s['raw_refresh_maxabs'],stalled_direction_reproduced=s.get('stalled_direction_reproduced',False))
        rows.append(row)
        modevals=[('u_only',du,np.zeros(n),True),('d_fixed_raw',np.zeros(2*n),dd,False),('joint',du,dd,True)]
        for mode,vu,vd,refresh in modevals:
            uder=(kuu if mode=='u_only' else kud if mode=='d_fixed_raw' else kuu+kud)[fu];dder=(ju if mode=='u_only' else jd if mode=='d_fixed_raw' else jd+ju)[fd]
            for e in [.01,.001,.0001,.00001,.000001]:
                pu=uv+e*vu;pd=damage+e*vd;pr=amor_raw(pu[:n],pu[n:],c,B) if refresh else raw0
                rp,sp=assemble(pd,pr,lower,hist,c,N,B,w,n);up=mechanics_force(pu,pd,c,N,B,w,n)
                df=(rp[fd]-rd0[fd])/e;uf=(up[fu]-ru0[fu])/e;filt=projected_gradient(pd[fd],rp[fd],lower[fd]);merit=float(np.linalg.norm(up[fu])+np.linalg.norm(filt))
                tangents.append(dict(cycle=cycle,stage=stage,mode=mode,epsilon=e,full_phase_jvp_relerr=float(np.linalg.norm(df-dder)/max(np.linalg.norm(dder),1e-30)),picard_phase_relerr=float(np.linalg.norm(df-(native_kdd[fd] if mode!='u_only' else 0))/max(np.linalg.norm(df),1e-30)),full_u_jvp_relerr=float(np.linalg.norm(uf-uder)/max(np.linalg.norm(uder),1e-30)),merit=merit,merit_secant=(merit-initial_merit)/e,fatigue_increment_switches=int(np.count_nonzero((sp['inc']>0)!=(st['inc']>0))),fatigue_threshold_switches=int(np.count_nonzero((sp['alpha']>.5)!=(st['alpha']>.5))),penalty_switches=int(np.count_nonzero(sp['pen']!=st['pen'])),recovery_switches=int(np.count_nonzero(sp['rec']!=st['rec'])),amor_trace_switches=int(np.count_nonzero((grad(pu[:n],c,B)[...,0]+grad(pu[n:],c,B)[...,1]>=0)!=(grad(uv[:n],c,B)[...,0]+grad(uv[n:],c,B)[...,1]>=0))),nodal_lower_switches=int(np.count_nonzero((pd[fd]<=lower[fd]+1e-10)!=(damage[fd]<=lower[fd]+1e-10))),nodal_upper_switches=int(np.count_nonzero((pd[fd]>=1-1e-10)!=(damage[fd]>=1-1e-10))),infeasible_nodes=int(np.count_nonzero((pd<lower-1e-12)|(pd>1+1e-12)))))
        # Verify source-equivalent differences against the actual saved native 15-evaluation table.
        recent=tangents[-15:]
        for nt,tt in zip(native_tangents,recent):
            assert int(nt['mode'])=={'u_only':1,'d_fixed_raw':2,'joint':3}[tt['mode']] and nt['epsilon']==tt['epsilon']
            native_merit=nt['mechanical_residual_l2']+nt['phase_residual_l2']
            assert abs(native_merit-tt['merit'])<1e-10
            tt['native_merit']=native_merit;tt['native_merit_secant']=(native_merit-initial_merit)/tt['epsilon']
            tt['native_phase_picard_relerr']=nt['phase_picard_relerr']
        # History channels have distinct units: never reduce slots2:4 to one physical effect.
        for j,label in enumerate(['cached_to_return','return_to_clip','clip_to_raw_refresh']):
            hr={'cycle':cycle,'stage':stage,'transition':label}
            for channel,name in [(1,'alpha_accumulator'),(2,'active_driver'),(3,'fatigue_factor')]:
                delta=native_histories[j+1][:,:,channel]-native_histories[j][:,:,channel]
                assert np.all(np.isfinite(delta))
                hr[name+'_max_abs']=float(np.max(np.abs(delta)));hr[name+'_weighted_l2']=float(np.sqrt(np.sum(w*delta**2)))
            history_rows.append(hr)
        # Exact vector transition norms, not additive scalar-norm attribution.
        row['cached_return_vector_delta']=float(np.linalg.norm((rs[1]-rs[0])[fd]));row['clip_vector_delta']=float(np.linalg.norm((rs[2]-rs[1])[fd]));row['raw_refresh_vector_delta']=float(np.linalg.norm((rs[3]-rs[2])[fd]))
        sq=rdata[-1]**2;row['phase_violation_centroid_x']=float(np.dot(sq,points[fd,0])/sq.sum());row['phase_violation_centroid_y']=float(np.dot(sq,points[fd,1])/sq.sum())
        rr=np.zeros(2*n);rr[fu]=ru_full_final[fu];node_ru_mass_dual_sq=(rr[:n]**2+rr[n:]**2)/mass
        ucenter=np.sum(node_ru_mass_dual_sq[:,None]*points,axis=0)/node_ru_mass_dual_sq.sum();clip_delta=dc-dr;cm=mass*np.abs(clip_delta);ccenter=np.sum(cm[:,None]*points,axis=0)/cm.sum();maxnode=np.argmax(np.abs(clip_delta))
        right=(points[:,0]>.48)&(np.abs(points[:,1])<=.02)
        row.update(clipped_node_fraction=s['clipped_nodes']/n,clip_max_node_x=float(points[maxnode,0]),clip_max_node_y=float(points[maxnode,1]),clip_abs_mass_centroid_x=float(ccenter[0]),clip_abs_mass_centroid_y=float(ccenter[1]),mechanical_mass_dual_centroid_x=float(ucenter[0]),mechanical_mass_dual_centroid_y=float(ucenter[1]),mechanical_mass_dual_sq_right_strip_share=float(node_ru_mass_dual_sq[right].sum()/node_ru_mass_dual_sq.sum()),phase_sq_left_half_share=float(sq[points[fd,0]<=0].sum()/sq.sum()))
        maps.append((cycle,stage,points,fd,clip_delta,rdata[-1],np.sqrt(node_ru_mass_dual_sq)));inputs.extend([p,d/'phase_capture_result.json'])
    for name,data in [('state_metrics.csv',rows),('transition_metrics.csv',transitions),('tangent_metrics.csv',tangents),('history_transition_metrics.csv',history_rows)]:
        with (out/name).open('w',newline='') as f:wr=csv.DictWriter(f,fieldnames=data[0]);wr.writeheader();wr.writerows(data)
    summary=dict(schema='native-phase-capture-comparison-v1',rows=rows,transitions=transitions,tangents=tangents,history_transitions=history_rows,history_commits=0,provenance={str(p):sha(p) for p in inputs},analysis_code_hashes={str(p):sha(p) for p in [Path(__file__),Path(__file__).with_name('audit_phase_tangent.py')]},scope='four independent saved-state block directions, not accepted outer/history updates; preclip filtered residual is not feasible KKT; native product match is state/direction specific')
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    fig,ax=plt.subplots(1,3,figsize=(15,4.5));labels=[f"c{r['cycle']} {r['stage']}" for r in rows]
    for r,label in zip(rows,labels):ax[0].semilogy(range(4),[t['bound_filtered_phase_l2'] for t in transitions if t['cycle']==r['cycle'] and t['stage']==r['stage']],'-o',label=label)
    ax[0].set_xticks(range(4),['cached','return/preclip','clipped','raw refreshed'],rotation=15);ax[0].set_ylabel('bound-filtered phase residual L2');ax[0].legend(fontsize=7)
    for r,label in zip(rows,labels):
        tr=[t for t in tangents if t['cycle']==r['cycle'] and t['stage']==r['stage'] and t['mode']=='joint'];ax[1].semilogx([t['epsilon'] for t in tr],[t['merit_secant'] for t in tr],'-o',label=label)
    ax[1].set_yscale('symlog',linthresh=1e-6);ax[1].axhline(0,color='grey',ls='--');ax[1].set_xlabel('joint-direction difference epsilon');ax[1].set_ylabel('(M_trial − M_initial)/epsilon');ax[1].legend(fontsize=7)
    last=[t for t in tangents if t['cycle']==83 and t['stage']=='last_accepted' and t['mode']=='joint'];m0=rows[-1]['initial_merit'];xx=np.array([t['epsilon'] for t in last]);yy=np.array([(t['native_merit']/m0-1)*1e6 for t in last]);threshold=-100*xx
    ax[2].semilogx(xx,yy,'-o',color='#0072B2',label='native monitor change');ax[2].semilogx(xx,threshold,'--',color='black',label='sufficient decrease boundary');ax[2].axhline(0,color='grey',ls=':');ax[2].axvline(1/64,color='grey',ls='--',label='old minimum lambda=1/64');ax[2].set_xlim(8e-7,.025);ax[2].set_yscale('symlog',linthresh=.05);ax[2].set_title('c83 last: smaller steps can decrease M');ax[2].set_xlabel('diagnostic joint step');ax[2].set_ylabel('relative native M change (ppm)');ax[2].legend(fontsize=6)
    for x in ax:x.grid(alpha=.25)
    fig.suptitle('Native four-state phase projection / coupled direction diagnostic');fig.tight_layout();fig.savefig(out/'native_phase_capture_comparison.png',dpi=180);plt.close(fig)
    (out/'native_phase_capture_comparison.md').write_text('# Native phase capture comparison\n\nQuestion: where do phase residuals change, and is the next coupled block direction descending for the monitor?\n\nData provenance: four fixed peak original baseline/last accepted c1/c83 captures under this run; exact file/code hashes and tables in summary.json. No history commit, all cases shown.\n\nHow to read: left native bound-filtered residual across cached pre-last Newton, returned preclip, clipped same raw, clipped refreshed raw. Preclip can violate bounds; its filtered quantity is only a diagnostic. Middle joint small-step merit secant (symlog y), M=free-u plus nodal-feasible-phase residual; negative descends. Frozen history/lower bound come from original accepted s3; directions start from saved peak fields. No propagated modified trajectory. Right zoom: c83-last native relative monitor change (ppm) against the original sufficient-decrease boundary; vertical line marks previous minimum1/64, smaller steps here were evaluated only, not accepted.\n\nMain numerical takeaway: c1-last cached1.99e-6 versus returned7.10e-5; c83-last returned1.84e-6 versus clipped2.56e-5. c83-last step1e-4 reduces M by1.37e-10, beyond the old grid; improvement is tiny. Exact four rows and all branch signs in CSV; native residual and native K-direction products admitted against source-equivalent assembly.\n\nLimitations: norm transitions are not additive causal shares; direction-specific tangent test is not global qualification. Nonsmooth branch counts shown in tables. No teacher, truth, or full trajectory repair claim.\n')
    fig,axs=plt.subplots(2,3,figsize=(13,8))
    selected=[m for m in maps if m[1]=='last_accepted']
    for i,(cycle,stage,pnts,idx,cl,ph,me) in enumerate(selected):
        for j,(coord,val,label,vmin,vmax) in enumerate([(pnts,cl,'|damage clipping correction|',-10,-2),(pnts[idx],ph,'|feasible phase residual|',-12,-4),(pnts,me,'free-u mass-dual residual',-10,0)]):
            artist=axs[i,j].hexbin(coord[:,0],coord[:,1],C=np.log10(np.maximum(np.abs(val),10.**vmin)),gridsize=120,reduce_C_function=np.max,cmap='viridis',vmin=vmin,vmax=vmax);axs[i,j].set_aspect('equal');axs[i,j].set_title(f'c{cycle} last: {label}',fontsize=9);fig.colorbar(artist,ax=axs[i,j],label='log10 magnitude',shrink=.7)
    fig.tight_layout();fig.savefig(out/'native_phase_spatial_maps.png',dpi=180);plt.close(fig)
    (out/'native_phase_spatial_maps.md').write_text('# Native phase/update spatial localization\n\nQuestion: where are clipping changes and residuals after the isolated native direction?\n\nData provenance: same four captures/hashes in summary.json; shown examples are the two predeclared last accepted c1/c83 states, never selected by outcome. Fields from unaccepted next block directions, frozen s3 history/lower bound.\n\nHow to read: rows c1/c83, columns absolute d_clipped minus returned-preclip damage, clipped/refreshed nodal feasible phase residual, and free displacement nodal residual divided by sqrt(Q4 lumped mass). Fixed common log colour scale per column. Hexbin displays maximum magnitude within bins, tables/centroids use original unbinned nodes. Boundary reactions removed.\n\nMain numerical takeaway: c1 phase violation lies in the initial crack wake; c83 damage/displacement coupling is near right front, exact centroids and shares in state_metrics.csv.\n\nLimitations: scales differ by column and have different units; co-location alone is not causation. These are isolated not accepted updates, no history commit or truth qualification.\n')
    print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
