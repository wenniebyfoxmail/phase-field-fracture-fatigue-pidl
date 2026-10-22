"""Analyze exact retained E037 outputs, including unaccepted trials; no solve."""
import argparse,csv,json
from pathlib import Path
import numpy as np
import scipy.io as sio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import LogNorm,TwoSlopeNorm
ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
PRIOR=Path('/Users/wenxiaofang/.codex/visualizations/2026/10/21/01a15f55-6b92-7cd2-9122-de9ae13176d7/pidl_u012_state_onset')
FEM=Path('/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/griphfith/Hard5_eta0_5step_Umax_011_012_013_20260729/u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1')
MAP=ROOT/'local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701/analysis/state_mechanism_compare_20260701/projected_residuals/projected_npz/projection_map_polygon_overlap.npz'

def dump(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def metric(ref,pred,w):
    ref=np.asarray(ref,float);pred=np.asarray(pred,float);w=np.asarray(w,float)
    delta=pred-ref
    return dict(relative_l2=float(np.sqrt(np.sum(w*delta**2)/max(np.sum(w*ref**2),1e-30))),
        rms=float(np.sqrt(np.sum(w*delta**2)/w.sum())),mean_ratio=float(np.sum(w*pred)/np.sum(w*ref)) if np.sum(w*ref)!=0 else None,
        ref_max=float(ref.max()),pred_max=float(pred.max()))
def csvsave(p,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=keys);w.writeheader();w.writerows(rows)
def values(f):return [np.sqrt(f['strain_xx']**2+f['strain_yy']**2+2*f['strain_xy']**2),f['raw_psi'],f['trial_A']]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('raw',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    mesh=np.load(a.raw/'mesh.npz');xy=mesh['xy'];tri=mesh['triangles'];area=mesh['area'];cent=xy[tri].mean(1)
    paths={};records={}
    for arm in ['original','primal_dual']:
        records[arm]=json.loads((a.raw/arm/'steps.json').read_text()) if (a.raw/arm/'steps.json').exists() else []
        paths[arm]={r['step']:a.raw/arm/f"step_{r['step']:03d}" for r in records[arm]}
    rows=[];pairs=[]
    for r in records['primal_dual']:
        step=r['step']
        if step not in paths['original']:continue
        p=np.load(paths['original'][step]/'fields.npz');n=np.load(paths['primal_dual'][step]/'fields.npz')
        for quantity,x,y in zip(['strain_norm','raw_psi','A_trial'],values(p),values(n)):
            rows.append(dict(step=step,cycle=r['cycle'],substep=r['substep'],new_accepted=r['accepted'],quantity=quantity,**metric(x,y,area)))
        pairs.append((r,p,n))
    csvsave(a.output/'paired_fields.csv',rows)
    timing=[]
    for arm,rr in records.items():
        for r in rr:timing.append(dict(arm=arm,step=r['step'],accepted=r['accepted'],updates=r['updates'],seconds=r['step_elapsed_seconds'],reason=r['stop_reason']))
    csvsave(a.output/'timing.csv',timing)
    # Reuse the verified common-support map; reject differing source geometry.
    target=np.load(PRIOR/'c1_aligned_fields.npz');pr=np.load(MAP);src,dst,weight=[pr[k] for k in ['src','dst','weight']]
    assert len(tri)==90000 and len(target['area'])==len(pr['fem_area'])
    assert np.max(abs(cent[:,0]-np.load(ROOT/'Baseline/PIDL_hard_d1_u0_recovery_5step/Umax_0.12/original_case/raw/run/element_diagnostics_probe_driver/element_fields_cycle_0004.npz')['elem_x']))<1e-7
    den=np.bincount(dst,weights=weight,minlength=len(target['area']))
    def project(v):return np.bincount(dst,weights=np.asarray(v)[src]*weight,minlength=len(den))/den
    tx,ty=target['centers'].T;regions=dict(domain=np.ones(len(tx),bool),initial_tip=np.hypot(tx,ty)<=.02,forward=(tx>=0)&(tx<=.05)&(abs(ty)<=.03))
    femrows=[]
    for arm,rr in records.items():
        for r in rr:
            if r['step']!=4 and r['substep']!=5:continue
            f=np.load(paths[arm][r['step']]/'fields.npz')
            qs=[('strain_norm',target['fem_strain_norm'],values(f)[0]),('raw_psi',target['fem_raw_psi'],f['raw_psi'])] if r['step']==4 else [('A',sio.loadmat(FEM/f"psi_fields/cycle_{r['cycle']:04d}.mat")['alpha_bar_elem'].ravel(),f['trial_A'])]
            for q,ref,pred in qs:
                mapped=project(pred)
                for region,mask in regions.items():
                    femrows.append(dict(arm=arm,step=r['step'],accepted=r['accepted'],quantity=q,region=region,**metric(ref[mask],mapped[mask],target['area'][mask])))
    csvsave(a.output/'fem_metrics.csv',femrows)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    if pairs:
        # Prospective selection: c1 peak if reached, otherwise first attempted state.
        r,p,n=next((v for v in pairs if v[0]['step']==4),pairs[0]);fig,axes=plt.subplots(3,3,figsize=(13,8),layout='constrained')
        for i,(label,x,y) in enumerate(zip(['Strain norm','Raw tensile energy','Trial fatigue A'],values(p),values(n))):
            lo=max(min(float(x[x>0].min()) if np.any(x>0) else 1e-12,float(y[y>0].min()) if np.any(y>0) else 1e-12),1e-8);hi=max(float(x.max()),float(y.max()),lo*10)
            for j,z in enumerate([x,y]):
                pc=PolyCollection(xy[tri],array=np.maximum(z,lo),cmap='viridis',norm=LogNorm(lo,hi),edgecolors='none');axes[i,j].add_collection(pc);fig.colorbar(pc,ax=axes[i,j],shrink=.8);axes[i,j].set_title(['Original','Primal-dual'+(' · unaccepted trial' if not r['accepted'] else '')][j]+': '+label)
            ratio=np.log10(np.maximum(y,lo)/np.maximum(x,lo));pc=PolyCollection(xy[tri],array=ratio,cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-2,vcenter=0,vmax=2),edgecolors='none');axes[i,2].add_collection(pc);fig.colorbar(pc,ax=axes[i,2],shrink=.8);axes[i,2].set_title('log10(new / original)')
        for ax in axes.ravel():ax.set_xlim(-.05,.05);ax.set_ylim(-.03,.03);ax.set_aspect('equal');ax.set_xlabel('x');ax.set_ylabel('y')
        fig.suptitle(f"S04-E037 · c{r['cycle']}/s{r['substep']} · one seed, common physical phase\nLog display floor >=1e-8; no field smoothing; trial A is NOT committed if unaccepted")
        fig.savefig(a.output/'matched_fields.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,3.8),layout='constrained')
    for arm,color in [('original','#0072B2'),('primal_dual','#D55E00')]:
        rr=records[arm]
        if rr:
            axes[0].plot([r['step'] for r in rr],np.cumsum([r['step_elapsed_seconds'] for r in rr]),'-o',c=color,label=arm,ms=3)
            axes[1].plot([r['step'] for r in rr],[r['metrics']['retreat_max'] for r in rr],'-o',c=color,label=arm,ms=3)
    axes[0].set_ylabel('Cumulative solve + required check/export seconds');axes[1].set_ylabel('Maximum nodal damage retreat');axes[1].axhline(5e-6,c='black',ls='--',lw=1,label='new tolerance')
    for ax in axes:ax.set_xlabel('Physical substep');ax.grid(alpha=.2);ax.legend(fontsize=8)
    axes[1].set_yscale('symlog',linthresh=1e-6);fig.suptitle('S04-E037 · endpoints include explicitly unaccepted trials; early failure is not speedup')
    fig.savefig(a.output/'time_and_constraints.png',dpi=180);plt.close(fig)
    last=records['primal_dual'][-1] if records['primal_dual'] else None
    if last:
        trace=json.loads((paths['primal_dual'][last['step']]/'trace.json').read_text());trace=[t for t in trace if 'primal_max' in t]
        if trace:
            fig,axes=plt.subplots(1,3,figsize=(12,3.5),layout='constrained');xx=[t['update'] for t in trace]
            for ax,key,lim in zip(axes,['primal_max','complementarity_scaled','parameter_kkt_rms'],[5e-6,5e-5,5e-5]):
                ax.semilogy(xx,[max(t[key],1e-16) for t in trace],'-o',color='#D55E00');ax.axhline(lim,c='black',ls='--',lw=1);ax.set_xlabel('RPROP updates');ax.set_ylabel(key);ax.grid(alpha=.2)
            fig.suptitle(f"Updated-multiplier checks · new step{last['step']} · {last['stop_reason']}");fig.savefig(a.output/'dual_convergence.png',dpi=180);plt.close(fig)
    summary=dict(pairs=rows,fem=femrows,paths={arm:dict(attempted=len(rr),accepted=sum(r['accepted'] for r in rr),last_step=rr[-1]['step'] if rr else None,last_reason=rr[-1]['stop_reason'] if rr else None,total_seconds=sum(r['step_elapsed_seconds'] for r in rr)) for arm,rr in records.items()})
    dump(a.output/'summary.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
