#!/usr/bin/env python3
"""Read-only native-equivalent Q4 residual/JVP audit, without a solve."""
import argparse,csv,json,hashlib
from pathlib import Path
import h5py,numpy as np,matplotlib.pyplot as plt
from run_multicycle_cross_replay import q4_geometry,interp,grad,amor_raw
from localize_endpoint_tight import mechanics_force
from audit_fem_final_residuals import projected_gradient


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def assemble(d,raw,lower,h,c,N,B,w,n,coefficient=None):
    dg=interp(d,c,N);og=interp(lower,c,N);gd=grad(d,c,B)
    active=(1-dg)**2*raw;inc=np.maximum(active-h[:,:,2],0);alpha=h[:,:,1]+inc
    f=np.minimum(1,(1-(alpha-.5)/(alpha+.5))**2)
    if coefficient is not None:f=coefficient
    pen=421875.*(dg<og);rec=13781.25*(dg<0)
    fracture=.000075*np.einsum('egd,egdi->egi',gd,B)+.375*N[None,:,:]
    val=(2*raw*(dg-1)+pen*(dg-og)+rec*dg)[...,None]*N[None,:,:]+f[...,None]*fracture
    r=np.zeros(n);np.add.at(r,c.reshape(-1),np.sum(w[...,None]*val,axis=1).reshape(-1))
    return r,dict(dg=dg,raw=raw,active=active,inc=inc,alpha=alpha,f=f,fracture=fracture,pen=pen,rec=rec)


def phase_jvp(dd,dpsi,s,c,N,B,w,n,full=True):
    ddg=interp(dd,c,N);gdd=grad(dd,c,B)
    val=((2*s['raw']+s['pen']+s['rec'])*ddg+2*(s['dg']-1)*dpsi)[...,None]*N[None,:,:]
    val+=.000075*s['f'][...,None]*np.einsum('egd,egdi->egi',gdd,B)
    if full:
        da=-2*(1-s['dg'])*s['raw']*ddg+(1-s['dg'])**2*dpsi
        df=np.where((s['inc']>0)&(s['alpha']>.5),-2*s['f']/(s['alpha']+.5)*da,0)
        val+=df[...,None]*s['fracture']
    r=np.zeros(n);np.add.at(r,c.reshape(-1),np.sum(w[...,None]*val,axis=1).reshape(-1));return r


def mechanics_jvp(uv,d,du,dd,c,N,B,w,n):
    def strains(x):
        gu=grad(x[:n],c,B);gv=grad(x[n:],c,B)
        return np.stack((gu[...,0],gv[...,1],gu[...,1]+gv[...,0]),axis=-1)
    e=strains(uv);de=strains(du);tr=e[...,:2].sum(-1);dt=de[...,:2].sum(-1)
    mu=1/2.6;bulk=1/1.2;dev=np.array([[2/3,-1/3,0],[-1/3,2/3,0],[0,0,.5]])
    sp=2*mu*np.einsum('ij,egj->egi',dev,e);sp[...,:2]+=bulk*np.maximum(tr,0)[...,None]
    dsp=2*mu*np.einsum('ij,egj->egi',dev,de);dsp[...,:2]+=bulk*np.where(tr>=0,dt,0)[...,None]
    dg=interp(d,c,N);ddg=interp(dd,c,N)
    ds=(1-dg)[...,None]**2*dsp-2*(1-dg)[...,None]*ddg[...,None]*sp
    ds[...,:2]+=bulk*np.where(tr<0,dt,0)[...,None]
    fx=np.sum(w[...,None]*(ds[...,0,None]*B[:,:,0,:]+ds[...,2,None]*B[:,:,1,:]),axis=1)
    fy=np.sum(w[...,None]*(ds[...,2,None]*B[:,:,0,:]+ds[...,1,None]*B[:,:,1,:]),axis=1)
    r=np.zeros(2*n);np.add.at(r,c.reshape(-1),fx.reshape(-1));np.add.at(r,n+c.reshape(-1),fy.reshape(-1))
    return r,np.sum(sp*de,axis=-1)


def read(path,key,ok):
    with h5py.File(path) as h:
        z={k:np.asarray(h[key+'/'+k]).reshape(-1) for k in ['displ','p_field']}
        z['raw']=np.asarray(h[key+'/strain_en_undgr']).T;z['lower']=np.asarray(h['frozen/p_field_old']).reshape(-1)
        z['history']=np.asarray(h['frozen/history_vars_old']).transpose(2,1,0)
        for k in ['R_u_free','R_d_free']:z[k]=np.asarray(h[ok+'/'+k]).reshape(-1)
        for k in ['free_dof_u','free_dof_d']:z[k]=np.asarray(h[ok+'/'+k]).reshape(-1).astype(int)-1
    return z


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--grid',type=Path,required=True);ap.add_argument('--mesh',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    with h5py.File(a.mesh) as h:p=np.asarray(h['node_coords']).T;c=np.asarray(h['connectivity_q4']).T.astype(int)-1
    N,B,w,xy=q4_geometry(p,c);n=len(p);rows=[];fdrows=[];maps=[];inputs=[a.mesh]
    for cycle in [1,83]:
        root=a.grid/f'states/c{cycle}/retrieved';last=10 if cycle==1 else 8
        def get(path):return read(path,'converged' if path.name=='baseline_endpoint.mat' else 'candidate','oracle' if path.name=='baseline_endpoint.mat' else 'candidate_oracle')
        for stage,path in [('baseline',root/'baseline_endpoint.mat'),('last_accepted',root/f'tight_outer_{last:02d}.mat')]:
            z=get(path);assert all(np.all(np.isfinite(z[k])) for k in ['displ','p_field','raw','lower','R_u_free','R_d_free']);assert np.all(z['p_field']>=z['lower']-1e-12) and np.all(z['p_field']<=1+1e-12);otherpath=root/'tight_outer_01.mat' if stage=='baseline' else root/f'tight_outer_{last-1:02d}.mat';other=get(otherpath);assert np.array_equal(z['lower'],other['lower']) and np.array_equal(z['history'],other['history'])
            du=other['displ']-z['displ'] if stage=='baseline' else z['displ']-other['displ'];dd=other['p_field']-z['p_field'] if stage=='baseline' else z['p_field']-other['p_field']
            fu=z['free_dof_u'];fd=z['free_dof_d'];raw=amor_raw(z['displ'][:n],z['displ'][n:],c,B)
            rd,s=assemble(z['p_field'],raw,z['lower'],z['history'],c,N,B,w,n);ru=mechanics_force(z['displ'],z['p_field'],c,N,B,w,n)
            errd=float(np.max(np.abs(rd[fd]-z['R_d_free'])));erru=float(np.max(np.abs(ru[fu]-z['R_u_free'])))
            if max(errd,erru)>1e-10:raise ValueError(f'Native admission failed ru={erru}, rd={errd}')
            proj=projected_gradient(z['p_field'][fd],rd[fd],z['lower'][fd])
            committed,_=assemble(z['p_field'],raw,z['lower'],z['history'],c,N,B,w,n,z['history'][:,:,3])
            staged=z['history'].copy();staged[:,:,1]=s['alpha'];staged[:,:,2]=s['active'];staged[:,:,3]=s['f']
            stagedrd,_=assemble(z['p_field'],raw,z['lower'],staged,c,N,B,w,n)
            kuu,dpsi=mechanics_jvp(z['displ'],z['p_field'],du,np.zeros(n),c,N,B,w,n)
            kud,_=mechanics_jvp(z['displ'],z['p_field'],np.zeros(2*n),dd,c,N,B,w,n)
            kdd=phase_jvp(dd,np.zeros_like(raw),s,c,N,B,w,n,False);jd=phase_jvp(dd,np.zeros_like(raw),s,c,N,B,w,n,True);jdu=phase_jvp(np.zeros(n),dpsi,s,c,N,B,w,n,True)
            for mode,vu,vd,refresh in [('u_only',du,np.zeros(n),True),('d_fixed_raw',np.zeros(2*n),dd,False),('joint',du,dd,True)]:
                ju=(kuu if mode=='u_only' else kud if mode=='d_fixed_raw' else kuu+kud)[fu];jphase=(jdu if mode=='u_only' else jd if mode=='d_fixed_raw' else jd+jdu)[fd]
                bu=kuu[fu] if mode!='d_fixed_raw' else np.zeros(len(fu));bd=kdd[fd] if mode!='u_only' else np.zeros(len(fd))
                for eps in [.01,.001,.0001,.00001,.000001]:
                    u=z['displ']+eps*vu;d=z['p_field']+eps*vd;rp=amor_raw(u[:n],u[n:],c,B) if refresh else raw
                    rdp,sp=assemble(d,rp,z['lower'],z['history'],c,N,B,w,n);rup=mechanics_force(u,d,c,N,B,w,n)
                    ddu=(rup[fu]-ru[fu])/eps;ddd=(rdp[fd]-rd[fd])/eps
                    fdrows.append(dict(cycle=cycle,stage=stage,mode=mode,epsilon=eps,
                        full_u_jvp_relerr=float(np.linalg.norm(ddu-ju)/max(np.linalg.norm(ju),1e-30)),full_d_jvp_relerr=float(np.linalg.norm(ddd-jphase)/max(np.linalg.norm(jphase),1e-30)),
                        block_u_jvp_relerr=float(np.linalg.norm(ddu-bu)/max(np.linalg.norm(ddu),1e-30)),block_d_jvp_relerr=float(np.linalg.norm(ddd-bd)/max(np.linalg.norm(ddd),1e-30)),
                        fatigue_branch_changes=int(np.count_nonzero((s['inc']>0)!=(sp['inc']>0))),fatigue_threshold_changes=int(np.count_nonzero((s['alpha']>.5)!=(sp['alpha']>.5))),penalty_branch_changes=int(np.count_nonzero(s['pen']!=sp['pen'])),recovery_branch_changes=int(np.count_nonzero(s['rec']!=sp['rec'])),amor_trace_branch_changes=int(np.count_nonzero((grad(z['displ'][:n],c,B)[...,0]+grad(z['displ'][n:],c,B)[...,1]>=0)!=(grad(u[:n],c,B)[...,0]+grad(u[n:],c,B)[...,1]>=0))),nodal_lower_mask_changes=int(np.count_nonzero((z['p_field'][fd]<=z['lower'][fd]+1e-10)!=(d[fd]<=z['lower'][fd]+1e-10))),nodal_upper_mask_changes=int(np.count_nonzero((z['p_field'][fd]>=1-1e-10)!=(d[fd]>=1-1e-10))),
                        infeasible_nodes=int(np.count_nonzero((d<z['lower']-1e-12)|(d>1+1e-12))),merit=float(np.linalg.norm(rup[fu])+np.linalg.norm(projected_gradient(d[fd],rdp[fd],z['lower'][fd])))))
            sq=proj**2;lo=z['p_field'][fd]<=z['lower'][fd]+1e-10;hi=z['p_field'][fd]>=1-1e-10;centroid=(sq[:,None]*p[fd]).sum(0)/sq.sum()
            rows.append(dict(cycle=cycle,stage=stage,native_ru_maxerr=erru,native_rd_maxerr=errd,ru_l2=float(np.linalg.norm(ru[fu])),raw_rd_l2=float(np.linalg.norm(rd[fd])),feasible_rd_l2=float(np.linalg.norm(proj)),feasible_rd_sq_lower_share=float(sq[lo].sum()/sq.sum()),feasible_rd_sq_interior_share=float(sq[~(lo|hi)].sum()/sq.sum()),feasible_rd_sq_precrack_share=float(sq[p[fd,0]<=0].sum()/sq.sum()),feasible_rd_centroid_x=float(centroid[0]),feasible_rd_centroid_y=float(centroid[1]),trial_f_change_max=float(np.max(np.abs(s['f']-z['history'][:,:,3]))),committed_f_feasible_rd_l2=float(np.linalg.norm(projected_gradient(z['p_field'][fd],committed[fd],z['lower'][fd]))),same_state_staged_history_rd_maxdelta=float(np.max(np.abs(stagedrd-rd))),source_equivalent_kdd_chain_term_norm=float(np.linalg.norm((jd-kdd)[fd])),source_equivalent_kdd_picard_jvp_norm=float(np.linalg.norm(kdd[fd])),cross_u_due_d_norm=float(np.linalg.norm(kud[fu])),cross_d_due_u_norm=float(np.linalg.norm(jdu[fd])),direction='first accepted delta' if stage=='baseline' else 'last accepted delta extended from final; not next stalled block direction'))
            maps.append((p[fd],proj));inputs.extend([path,otherpath])
    for name,data in [('endpoint_components.csv',rows),('directional_checks.csv',fdrows)]:
        with (a.out/name).open('w',newline='') as f:wr=csv.DictWriter(f,fieldnames=data[0]);wr.writeheader();wr.writerows(data)
    summary=dict(schema='phase-coupled-offline-audit-v1',rows=rows,directional_checks=fdrows,provenance={str(p):sha(p) for p in set(inputs)},analysis_code_hashes={str(p):sha(p) for p in [Path(__file__),Path(__file__).with_name('run_multicycle_cross_replay.py'),Path(__file__).with_name('localize_endpoint_tight.py'),Path(__file__).with_name('audit_fem_final_residuals.py')]},scope='local source-equivalent assembly; native residual admission does not qualify native MEX tangent; no solve/history commit; inner pre-clamp field unavailable, needs producer capture',parameters=dict(E=1,nu=.3,Gc=.01,ell=.01,alpha_T=.5,p=2,eta=0,penalty_irrev=421875,penalty_recov=13781.25))
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    fig,ax=plt.subplots(2,2,figsize=(12,7));labels=[f"c{r['cycle']} {r['stage']}" for r in rows];x=np.arange(4)
    for k,label in [('ru_l2','free u'),('feasible_rd_l2','feasible d'),('committed_f_feasible_rd_l2','frozen committed f d')]:ax[0,0].semilogy(x,[r[k] for r in rows],'o-',label=label)
    ax[0,0].axhline(4e-6,ls='--',color='grey');ax[0,0].set_xticks(x,labels,rotation=15);ax[0,0].legend(fontsize=8);ax[0,0].set_ylabel('residual L2')
    for i,r in enumerate(rows):
        rr=[t for t in fdrows if t['cycle']==r['cycle'] and t['stage']==r['stage'] and t['mode']=='d_fixed_raw']
        ax[0,1].loglog([t['epsilon'] for t in rr],[t['full_d_jvp_relerr'] for t in rr],'o-',label=labels[i]+' full');ax[0,1].loglog([t['epsilon'] for t in rr],[t['block_d_jvp_relerr'] for t in rr],'--',label=labels[i]+' Picard')
    ax[0,1].set_xlabel('one-sided difference epsilon');ax[0,1].set_ylabel('phase JVP relative discrepancy');ax[0,1].legend(fontsize=6);ax[0,1].set_title('c1 final: penalty switches near roundoff',fontsize=9)
    for i in [0,2]:
        xy,val=maps[i];im=ax[1,i//2].scatter(xy[:,0],xy[:,1],c=np.log10(np.maximum(np.abs(val),1e-12)),s=1,vmin=-12,vmax=-4,cmap='viridis');ax[1,i//2].set_aspect('equal');ax[1,i//2].set_title(labels[i]+' feasible phase residual');fig.colorbar(im,ax=ax[1,i//2],label='log10 |nodal residual|')
    fig.suptitle('c1/c83 native-equivalent saved-state audit: no new solve');fig.tight_layout();fig.savefig(a.out/'phase_tangent_audit.png',dpi=170);plt.close(fig)
    (a.out/'phase_tangent_audit.md').write_text('# c1/c83 phase/tangent audit\n\nQuestion: quantify fatigue refresh, phase feasible residual and missing derivative terms. Data provenance: exact four predeclared saved peak endpoints, native residual admission errors, hashes and branch counts in summary.json; tables authoritative.\n\nHow to read: upper left free u/feasible d and artificial frozen committed-f comparator, residual L2; dashed4e-6 previous screen. Upper right one-sided difference epsilon vs full/Picard phase directional derivative discrepancy; four fixed states, saved accepted deltas. Lower panels original c1/c83 feasible nodal phase residual, common log colour scale. No interpolation in tables.\n\nLimitations: artificial coefficient/history replay not solved equilibrium; last accepted delta not next stalled direction. Branch crossings recorded separately. Pre-clamp inner field absent; numerical projection attribution pending native capture. No solve/factorization/history commit on Mac, no teacher/truth claim. Numerical takeaway in summary.json and task report.\n')
    print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
