#!/usr/bin/env python3
"""Offline spatial and exact active-field cross replay of completed outer iterates."""
import argparse,json,csv
from pathlib import Path
import numpy as np,h5py,matplotlib.pyplot as plt
from run_multicycle_cross_replay import q4_geometry,interp,comp,grad
from analyze_endpoint_tight import endpoint,digest


def centroid(value,xy,w):
    weight=w*np.abs(value);total=weight.sum()
    return (np.sum(weight[...,None]*xy,axis=tuple(range(weight.ndim)))/total).tolist() if total else None


def mechanics_force(uv,damage,c,shape,deriv,w,n):
    gu=grad(uv[:n],c,deriv);gv=grad(uv[n:],c,deriv)
    eps=np.stack((gu[...,0],gv[...,1],gu[...,1]+gv[...,0]),axis=-1)
    mu=1/(2*1.3);bulk=1/(3*.4);trace=eps[...,0]+eps[...,1]
    dev=np.array([[2/3,-1/3,0],[-1/3,2/3,0],[0,0,.5]])
    sig=2*mu*np.einsum('ij,egj->egi',dev,eps)
    sig[...,:2]+=bulk*np.maximum(trace,0)[...,None]
    sig*=(1-interp(damage,c,shape))[...,None]**2
    sig[...,:2]+=bulk*np.minimum(trace,0)[...,None]
    fx=np.sum(w[...,None]*(sig[...,0,None]*deriv[:,:,0,:]+sig[...,2,None]*deriv[:,:,1,:]),axis=1)
    fy=np.sum(w[...,None]*(sig[...,2,None]*deriv[:,:,0,:]+sig[...,1,None]*deriv[:,:,1,:]),axis=1)
    ru=np.zeros(2*n);np.add.at(ru,c.reshape(-1),fx.reshape(-1));np.add.at(ru,n+c.reshape(-1),fy.reshape(-1));return ru


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--mesh',type=Path,required=True);ap.add_argument('--pidl',type=Path,required=True);ap.add_argument('--cycle',type=int,default=83);args=ap.parse_args()
    baseline_result=json.loads((args.run/'retrieved/result.json').read_text())
    if not baseline_result['baseline_pass'] or baseline_result['physical_cycle']!=args.cycle:raise ValueError('Baseline state identity')
    base_iteration=baseline_result['iterations']
    out=args.run/'localization';out.mkdir(exist_ok=True);data=args.run/'retrieved'
    with h5py.File(args.mesh) as h:p=np.asarray(h['node_coords']).T;c=np.asarray(h['connectivity_q4']).T.astype(int)-1
    shape,deriv,w,xy=q4_geometry(p,c);n=len(p);mass=np.zeros(n)
    for j in range(4):np.add.at(mass,c[:,j],np.einsum('eg,g->e',w,shape[:,j]))
    with np.load(args.pidl) as z:
        if str(z['topology'][0])!='q4' or np.max(np.abs(z['node_coords']-p))>2e-8:raise ValueError('PIDL mesh identity')
        ii=int(np.flatnonzero(z['cycles']==args.cycle)[0]);assert z['steps'][ii]==5*args.cycle-1
        from run_multicycle_cross_replay import amor_raw
        pa=amor_raw(z['u_node'][ii],z['v_node'][ii],c,deriv)*(1-interp(z['d_node'][ii],c,shape))**2
    b=endpoint(data/'baseline_endpoint.mat','converged','oracle',n,c,shape,deriv,w)
    with h5py.File(data/'baseline_endpoint.mat') as h:br=np.asarray(h['converged/strain_en_undgr']).T
    bg=(1-interp(b['d'],c,shape))**2
    rows=[];maps={}
    paths=[data/'baseline_endpoint.mat']+sorted(data.glob('tight_outer_*.mat'))
    for k,path in enumerate(paths):
        key='converged' if k==0 else 'candidate';ok='oracle' if k==0 else 'candidate_oracle';e=endpoint(path,key,ok,n,c,shape,deriv,w)
        if k and (path.name!=f'tight_outer_{k:02d}.mat' or e['iteration']!=base_iteration+k):raise ValueError('Iteration identity')
        if not all(np.array_equal(e[z],b[z]) for z in ('lower','history','load')):raise ValueError('Frozen state identity')
        with h5py.File(path) as h:
            raw=np.asarray(h[key+'/strain_en_undgr']).T;ru=np.asarray(h[ok+'/R_u_full']).reshape(-1);free=np.asarray(h[ok+'/free_dof_u']).reshape(-1).astype(int)-1
        ruf=np.zeros(2*n);ruf[free]=ru[free];node_ru_sq=ruf[:n]**2+ruf[n:]**2
        native_replay=mechanics_force(e['uv'],e['d'],c,shape,deriv,w,n)
        if np.max(np.abs(native_replay[free]-ru[free]))>1e-10:raise ValueError('Native free-u replay mismatch')
        fixed_d_force=mechanics_force(e['uv'],b['d'],c,shape,deriv,w,n)
        fixed_u_force=mechanics_force(b['uv'],e['d'],c,shape,deriv,w,n)
        g=(1-interp(e['d'],c,shape))**2;ua=raw*bg;da=br*g;a=raw*g
        mech=.5*(raw-br)*(g+bg);dmg=.5*(g-bg)*(raw+br)
        assert np.max(np.abs(mech+dmg-(a-b['active'])))<1e-12
        dd=e['d']-b['d'];q=np.quantile(np.abs(dd),.99);mask=np.abs(dd)>=q if q else np.zeros(n,dtype=bool)
        forward=(p[:,0]>.48)&(np.abs(p[:,1])<=.02);gpf=(xy[...,0]>.48)&(np.abs(xy[...,1])<=.02)
        row={'outer':base_iteration+k,'native_ru_replay_maxabs':float(np.max(np.abs(native_replay[free]-ru[free]))),
             'ru_l2_at_current_uv_baseline_damage':float(np.linalg.norm(fixed_d_force[free])),
             'ru_l2_at_baseline_uv_current_damage':float(np.linalg.norm(fixed_u_force[free])),
             'damage_induced_force_change_l2_at_current_uv':float(np.linalg.norm((native_replay-fixed_d_force)[free])),'uv_fixed_damage_gap':comp(ua,pa,w)['relative_l2'],'damage_fixed_uv_gap':comp(da,pa,w)['relative_l2'],
             'joint_gap':comp(a,pa,w)['relative_l2'],'mech_delta_l2':float(np.sqrt(np.sum(w*mech**2))),
             'damage_delta_l2':float(np.sqrt(np.sum(w*dmg**2))),
             'mech_delta_integral':float(np.sum(w*mech)),'damage_delta_integral':float(np.sum(w*dmg)),
             'damage_positive_mass':float(np.sum(mass*np.maximum(dd,0))),'damage_negative_mass':float(np.sum(mass*np.maximum(-dd,0))),
             'ru_sq_in_damage_change_top1_nodes':float(node_ru_sq[mask].sum()/node_ru_sq.sum()),
             'ru_mass_dual_sq_forward_share':float((node_ru_sq/mass)[forward].sum()/(node_ru_sq/mass).sum()),
             'damage_change_mass_forward_share':float(np.sum(mass[forward]*np.abs(dd[forward]))/np.sum(mass*np.abs(dd))) if np.any(dd) else None,
             'active_change_sq_forward_share':float(np.sum(w[gpf]*(a-b['active'])[gpf]**2)/np.sum(w*(a-b['active'])**2)) if k else None,
             'damage_change_centroid':centroid(dd,p,mass),'ru_mass_dual_centroid':centroid(node_ru_sq/mass,p,np.ones(n)),
             'active_gap_sq_centroid':centroid((a-pa)**2,xy,w)}
        rows.append(row);maps[k]=(dd,np.sqrt(node_ru_sq/mass),a-pa,mech,dmg)
    summary={'schema':'outer-spatial-cross-replay-v2','physical_cycle':args.cycle,'rows':rows,'regions':'right-boundary strip x>.48, |y|<=2ell=.02 fixed geometry; top1% nodes is unweighted descriptive rank, not a claim gate',
      'decomposition':'delta active = .5 delta_raw*(g_k+g_20) + .5 delta_g*(raw_k+raw_20), exact symmetric two-factor decomposition, not solved counterfactuals',
      'analysis_code_hashes':{str(x):digest(x) for x in [Path(__file__),Path(__file__).with_name('run_multicycle_cross_replay.py'),Path(__file__).with_name('analyze_endpoint_tight.py')]},
      'provenance':{str(x):digest(x) for x in paths+[args.mesh,args.pidl]},'scope':'offline localization/cross replay; co-location is not causal evidence'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    with (out/'metrics.csv').open('w',newline='') as h:wr=csv.DictWriter(h,fieldnames=rows[0]);wr.writeheader();wr.writerows(rows)
    fig,ax=plt.subplots(3,3,figsize=(13,10));chosen=(min(1,len(paths)-1),min(5,len(paths)-1),len(paths)-1)
    for col,k in enumerate(chosen):
        dd,rr,gap,_,_=maps[k]
        for row,coord,val,label in [(0,p,dd,f'damage minus outer{base_iteration}'),(1,p,rr,'free-u residual / sqrt(lumped mass)'),(2,xy.reshape(-1,2),gap.reshape(-1),'active FEM minus unchanged PIDL')]:
            limits=np.quantile(np.abs(maps[len(paths)-1][row]),.995);limits=max(limits,1e-12)
            hb=ax[row,col].hexbin(coord[:,0],coord[:,1],C=np.clip(val,0 if row==1 else -limits,limits),gridsize=100,reduce_C_function=np.mean,cmap='viridis' if row==1 else 'coolwarm',vmin=0 if row==1 else -limits,vmax=limits)
            ax[row,col].set_title(f'outer{base_iteration+k}: {label}',fontsize=9);ax[row,col].set_aspect('equal');fig.colorbar(hb,ax=ax[row,col],shrink=.7)
    fig.tight_layout();fig.savefig(out/'outer_spatial_maps.png',dpi=190);plt.close(fig)
    note=f'''# Cycle{args.cycle} outer-iterate spatial localization\n\nQuestion: where do damage, mechanical imbalance and active disagreement change?\n\nData provenance: exact endpoints and mesh/PIDL SHA256 in summary.json; FEM cycle{args.cycle}s4 outer{base_iteration}–{base_iteration+len(paths)-1}, immutable s3 history, original PIDL Q4 c{args.cycle}step{5*args.cycle-1}.\n\nHow to read: columns early, middle and last complete extra iterate (labels on panels); rows nodal damage change from the archived baseline, free displacement residual divided by sqrt lumped Q4 mass, and active FEM−PIDL. Hexbin uses mean within display bins; common row scales fixed to final99.5th magnitude, clipped for visibility. Reaction DOFs are zeroed. Tables use unbinned native fields/GP weights.\n\nMain numerical takeaway: {json.dumps(rows[-1])}. Exact two-factor terms in metrics.csv separate raw displacement and damage degradation, including their symmetric interaction.\n\nLimitations and claim boundary: cross fields are deterministic replay, not re-solved equilibria; native residual maps cannot alone isolate damage causality. Top1% damage-change rank is unweighted diagnostic; right-boundary strip is geometric and not a promotion threshold. Native nodal feasible residual is not GP-KKT qualification. No state history commit or truth claim.\n'''
    (out/'outer_spatial_maps.md').write_text(note);print(json.dumps(rows[-1],indent=2))
if __name__=='__main__':main()
