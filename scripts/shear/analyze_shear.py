"""Plot native or paired shear results, retaining partial coverage explicitly."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from scipy.io import loadmat
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection


def rows(path):
    if not path.exists(): return []
    with path.open() as f:
        return [{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fem',type=Path,required=True)
    p.add_argument('--pidl',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    for d in ['figures','tables']: (a.out/d).mkdir(exist_ok=True)
    mesh=loadmat(a.fem/'mesh.mat')
    nodes=mesh['nodes'][:,:2]; quad=mesh['quads'].astype(int)-1
    poly=nodes[quad]
    area=.5*np.abs(np.sum(poly[:,:,0]*np.roll(poly[:,:,1],-1,axis=1)-poly[:,:,1]*np.roll(poly[:,:,0],-1,axis=1),axis=1))
    fr=rows(a.fem/'trajectory.csv')
    pr=rows(a.pidl/'trajectory.csv') if a.pidl else []
    f_by={int(r['step']):r for r in fr}; p_by={int(r['step']):r for r in pr}
    common=sorted(f_by.keys() & p_by.keys())
    metrics=[]
    native_fields={}
    candidate_fields={}
    for step in sorted(f_by):
        s=loadmat(a.fem/f'state_{step:03d}.mat')
        native_fields[step]=s['p_field'].ravel()[quad].mean(axis=1)
    if common:
        pm=np.load(a.pidl/'mesh.npz')
        np.testing.assert_allclose(pm['nodes'],nodes,atol=1e-12,rtol=0)
        assert np.array_equal(pm['quads'],quad)
        child_area=pm['area'].reshape(-1,2)
        for step in common:
            assert abs(f_by[step]['U']-p_by[step]['U']) < 1e-7, 'State mismatch'
            s=np.load(a.pidl/f'state_{step:03d}.npz')
            assert str(s['timing'])=='post_solve_pre_history_update'
            v=s['alpha'][pm['triangles']].mean(axis=1).reshape(-1,2)
            candidate_fields[step]=(v*child_area).sum(axis=1)/child_area.sum(axis=1)
            delta=candidate_fields[step]-native_fields[step]
            metrics.append(dict(step=step,U=f_by[step]['U'],damage_MAE=float(np.average(abs(delta),weights=area)),
                damage_RMSE=float(np.sqrt(np.average(delta**2,weights=area))),
                Rx_FEM=f_by[step]['Rx_top'],Rx_PIDL=p_by[step]['Rx_top'],
                NN_residual=p_by[step]['res_u'],NN_max_healing=p_by[step]['max_healing'],
                NN_alpha_min=p_by[step]['alpha_min'],NN_alpha_max=p_by[step]['alpha_max']))
    if metrics:
        with (a.out/'tables/matched_states.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(metrics[0])); w.writeheader(); w.writerows(metrics)
    if fr:
        fig,axs=plt.subplots(1,2,figsize=(9,3.6),constrained_layout=True)
        axs[0].plot([r['U'] for r in fr],[r['Rx_top'] for r in fr],color='#0072B2',lw=1.6,label='Native FEM Q4')
        if pr: axs[0].plot([r['U'] for r in pr],[r['Rx_top'] for r in pr],color='#D55E00',lw=1.6,ls='--',label='PIDL T3, seed 1')
        axs[0].set(xlabel='Prescribed horizontal displacement U',ylabel='Direct top reaction Rx')
        axs[0].legend(frameon=False)
        if metrics:
            axs[1].plot([r['U'] for r in metrics],[r['damage_MAE'] for r in metrics],color='#009E73')
            axs[1].set(xlabel='Matched U',ylabel='Area-weighted cell damage MAE')
        else:
            axs[1].plot([r['U'] for r in fr],[r['E_el'] for r in fr],label='Elastic',color='#0072B2')
            axs[1].plot([r['U'] for r in fr],[r['E_d'] for r in fr],label='Fracture',color='#D55E00')
            axs[1].set(xlabel='U',ylabel='Native FEM energy'); axs[1].legend(frameon=False)
        for ax in axs: ax.grid(alpha=.15)
        for ext in ['png','pdf']: fig.savefig(a.out/f'figures/shear_response.{ext}',dpi=180)
        plt.close(fig)
        selected=common if common else sorted(f_by)
        selected=sorted(set(selected[i] for i in np.linspace(0,len(selected)-1,min(4,len(selected)),dtype=int)))
        columns=3 if common else 1
        fig,axs=plt.subplots(len(selected),columns,squeeze=False,figsize=(3.4*columns,3*len(selected)),constrained_layout=True)
        residual_bound=max([float(abs(candidate_fields[s]-native_fields[s]).max()) for s in selected],default=1.) if common else 1.
        residual_bound=max(residual_bound,1e-6)
        for i,step in enumerate(selected):
            fields=[native_fields[step]]
            titles=[f'FEM | U={f_by[step]["U"]:.3f}']
            if common:
                fields += [candidate_fields[step],candidate_fields[step]-native_fields[step]]
                titles += ['PIDL | seed 1','PIDL - FEM']
            for j,(values,title) in enumerate(zip(fields,titles)):
                ax=axs[i,j]
                limits=(-residual_bound,residual_bound) if j==2 else (0,1)
                artist=PolyCollection(poly,array=values,cmap='RdBu_r' if j==2 else 'viridis',edgecolors='none',rasterized=True)
                artist.set_clim(*limits); ax.add_collection(artist)
                ax.set(xlim=(-.5,.5),ylim=(-.5,.5),xlabel='x',ylabel='y',title=title,aspect='equal')
                fig.colorbar(artist,ax=ax,label='Damage difference' if j==2 else 'Damage alpha',shrink=.8,extend='both')
        for ext in ['png','pdf']: fig.savefig(a.out/f'figures/shear_damage.{ext}',dpi=180)
        plt.close(fig)
    result=dict(native_states=len(fr),pidl_states=len(pr),joint_states=len(common),prescribed_states=len(mesh['schedule']),
        FEM_completed=(a.fem/'COMPLETED.txt').exists(),PIDL_completed=(a.pidl/'COMPLETED.txt').exists() if a.pidl else False,
        mean_damage_MAE=float(np.mean([r['damage_MAE'] for r in metrics])) if metrics else None,
        scope='exploratory, one trajectory, Q4/T3 and quadrature/recovery differences retained')
    (a.out/'summary.json').write_text(json.dumps(result,indent=2))
    (a.out/'README_analysis.md').write_text(f'''# Monotonic shear analysis

Question: compare native FEM and independently optimized PIDL under matched U.
Source FEM: {a.fem}; source PIDL: {a.pidl}.
Coverage: native {len(fr)}/30, PIDL {len(pr)}/30, joint {len(common)}/30.
Read response curves first, then matched damage maps. Without PIDL, these
figures describe native FEM only and provide no agreement evidence.

Damage reduction: native Q4 nodal mean versus area-weighted two child-T3 nodal
means on each common parent cell. Errors use physical cell-area weights; the
trajectory mean treats each jointly available state equally. All common states
are retained; bounds/healing/residual violations are reported, not filtered to
improve the score. Missing coverage cannot establish full-trajectory agreement.
Initial precrack is included; one cannot infer forward crack accuracy solely
from a domain-average MAE. Nodal arrays remain available for process-zone work.

Reaction is a direct sum of elastic nodal internal forces at top DOFs, never
2E/U. NN residual and irreversibility are diagnostics and remain necessary to
interpret its force. Fixed [0,1] damage color limits and common signed residual
limits are used; no array clipping or smoothing is applied. Colorbar extensions
retain awareness of values outside the visible damage scale.

Allowed: exploratory matched-state numerical differences and execution coverage.
Blocked: physical validation, mesh convergence, generalization, cyclic fatigue,
or attributing all differences to NN representation/optimization.
''')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
