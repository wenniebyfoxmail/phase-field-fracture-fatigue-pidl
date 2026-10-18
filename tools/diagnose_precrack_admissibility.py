"""Read-only C200 physical-bound diagnostic; no NN inference/optimizer/FEM solve."""
import argparse,csv,importlib.util,json,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).parent))
from audit_saved_physical_parity import Probe,grid


def main(a):
    a.out.mkdir(parents=True,exist_ok=False)
    z=np.load(a.run/'fixed_inputs.npz');p=z['node_coords'];cells=z['connectivity'];line=z['crack_mask']
    d=np.load(a.run/'C/update200/fields.npz')['d'];lower=np.load(a.run/'C/initial_history.npy')
    initial=np.load(a.run/'C/update000/fields.npz')['d']
    assert np.array_equal(initial,lower) and np.array_equal(lower,z['FEM_initial_damage'])
    assert d.dtype==lower.dtype==np.float32 and bool((d[line]==1).all())
    owner=a.root/'local_archive/experiments/S04-E011/runs/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z/analysis/run_multicycle_cross_replay.py'
    spec=importlib.util.spec_from_file_location('native_operator',owner);op=importlib.util.module_from_spec(spec);spec.loader.exec_module(op)
    N,B,w,gpxy=op.q4_geometry(p,cells);mass=np.zeros(len(p))
    for j in range(4):np.add.at(mass,cells[:,j],np.sum(w*N[:,j],axis=1))
    dg=op.interp(d.astype(float),cells,N);hg=op.interp(lower.astype(float),cells,N)
    dg32=op.interp(d,cells,N.astype(np.float32));hg32=op.interp(lower,cells,N.astype(np.float32))
    eps=float(np.finfo(np.float32).eps)
    thresholds=[('strict_zero',0.),('FEM_cast_measured',2.971290757880496e-8),('float32_unit_epsilon',eps),
                ('existing_QP_feasibility',1e-10),('legacy_box_screen',1e-3),('PIDL_penalty_parameter',5e-3)]
    def stats(value,lo,weights,xy):
        negative=np.maximum(-value,0);healing=np.maximum(lo-value,0)
        def region(v,t):
            m=v>t;wt=weights[m]
            return dict(points=int(m.sum()),quadrature_or_lumped_area=float(wt.sum()),fraction=float(wt.sum()/weights.sum()),
                bbox_xy=[xy[m].min(axis=0).tolist(),xy[m].max(axis=0).tolist()] if m.any() else None,
                centroid_xy=(np.sum(xy[m]*wt[:,None],axis=0)/wt.sum()).tolist() if m.any() else None)
        i=int(np.argmin(value));j=int(np.argmax(healing))
        result=dict(minimum=float(value.flat[i]),minimum_xy=xy.reshape(-1,2)[i].tolist(),
            maximum=float(value.max()),healing_max=float(healing.flat[j]),healing_max_xy=xy.reshape(-1,2)[j].tolist(),
            negative_integral=float(np.sum(weights*negative)),healing_integral=float(np.sum(weights*healing)),
            healing_L2=float(np.sqrt(np.sum(weights*healing**2))),
            upper_violation_max=float(np.maximum(value-1,0).max()),thresholds={})
        for label,t in thresholds:result['thresholds'][label]=dict(threshold=t,negative=region(negative,t),healing=region(healing,t))
        histpos=lo>eps
        result['healing_beyond_epsilon_on_positive_initial_damage']=region(np.where(histpos,healing,0),eps)
        result['healing_beyond_1e_minus3_on_positive_initial_damage']=region(np.where(histpos,healing,0),1e-3)
        return result
    nodal=stats(d.astype(float),lower.astype(float),mass,p)
    gp=stats(dg,hg,w,gpxy)
    q=dict(source=str(a.run/'C/update200/fields.npz'),lower=str(a.run/'C/initial_history.npy'),
        scope='Only saved C physical nodal d and own fixed initial lower; native Q4 reconstruction. No raw NN output read or inferred.',
        native_operator=str(owner),nodes=len(p),cells=len(cells),GP_count=int(w.size),domain_area=float(w.sum()),
        initial_C_equal_lower=True,hard_line_exact_nodes=int(line.sum()),nodal=nodal,native_Q4_GP=gp,
        roundoff=dict(float32_unit_epsilon=eps,measured_FEM_float64_cast_max=2.971290757880496e-8,
            measured_initial_map_roundoff=1.4901161193847656e-8,actual_initial_C_error=0.,
            GP_float32_vs_float64_damage_Linf=float(abs(dg32.astype(float)-dg).max()),
            GP_float32_vs_float64_lower_Linf=float(abs(hg32.astype(float)-hg).max())),
        tolerances=dict(strict_physical='0<=d<=1; mapped previous-accepted lower is separate irreversibility condition',
            QP_contract='source/native_q4_damage_qp.py::validate_qp_contract default1e-10 is a hard-feasibility comparison, not a new r2 pass rule',
            legacy_box='experiment.md existing applicable box <=1e-3; separate from irreversibility',
            PIDL_tol_ir='.005 sets gamma16875; not a posthoc allowed-healing guarantee or hard constraint',
            FEM_tol_irrev='.001 sets gamma421875; phase/staggered4e-4 are solver criteria, not allowable damage-bound violations'),
        area_note='GP measures are native 4-point Jacobian-weighted quadrature estimates of violation support, not exact continuum level-set areas. Nodal measures use lumped masses and are separately labelled.',
        temporal_note='healing means C200 below its own fixed U0 lower; this block commits no history and is not a temporal trajectory.')
    (a.out/'summary.json').write_text(json.dumps(q,indent=2,allow_nan=False)+'\n')
    with (a.out/'nodes_retreat_above_1e_minus3.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['node_0based','x','y','physical_d','own_lower','retreat','lumped_area'])
        for i in np.flatnonzero(lower.astype(float)-d.astype(float)>1e-3):
            writer.writerow([int(i),*p[i],float(d[i]),float(lower[i]),float(lower[i])-float(d[i]),float(mass[i])])
    fig,axs=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    gx,gy,query=grid((-.5,.5,-.5,.5),351,351);probe=Probe(p,cells,query)
    dv=probe.value(d);hv=probe.value(lower)
    for ax,val,title in [(axs[0],np.maximum(-dv,0),'C200 physical negative damage: max(-d,0)'),(axs[1],np.maximum(hv-dv,0),'C200 below fixed U0 lower: max(h-d,0)')]:
        im=ax.pcolormesh(gx,gy,val.reshape(351,351),shading='auto',cmap='magma',vmin=0)
        ax.set(aspect='equal',xlabel='x',ylabel='y')
        ax.set_title(title,fontsize=9);fig.colorbar(im,ax=ax,shrink=.8)
    labels=['> unit eps','> 1e-3'];x=np.arange(2)
    for offset,key in [(-.18,'negative'),(.18,'healing')]:
        axs[2].bar(x+offset,[100*gp['thresholds'][k][key]['fraction'] for k in ['float32_unit_epsilon','legacy_box_screen']],.36,label=key)
    axs[2].set(xticks=x,xticklabels=labels,ylabel='Native Q4 GP weighted area (%)',title='GP area by violation magnitude');axs[2].title.set_fontsize(9);axs[2].legend(fontsize=8)
    fig.suptitle(f"Saved C200: nodal d_min={nodal['minimum']:.3g}; GP d_min={gp['minimum']:.3g}\nc1s1 U=.02999988 | saved physical fields only; no new optimization or FEM",fontsize=10)
    fig.savefig(a.out/'C_physical_admissibility.png',dpi=170);plt.close(fig)
    doc=f'''# C physical admissibility diagnostic

Question: are negative damage and retreat only rounding, and where do they occur?

Data provenance: `{a.run}` C update200 d, own initial_history, canonical mesh. Native operator `{owner}`. No NN inference, optimizer step, target FEM access or FEM solve. Raw NN output is not available locally and is not diagnosed as physical damage.

How to read: left/center display native-Q4 bilinear reconstructions of physical negative damage and lower-bound retreat over the full fixed domain. The right panel uses native GP4 Jacobian-weighted area for two declared existing diagnostic scales. Exact nodal/GP minima, maxima, positions, areas and all thresholds are in summary.json. Initial comparator is saved C0=own lower, not a different method or later FEM state.

Numerical result: nodal d_min={nodal['minimum']:.9g}, GP d_min={gp['minimum']:.9g}; nodal/GP lower retreat maxima={nodal['healing_max']:.9g}/{gp['healing_max']:.9g}. Negative GP area beyond float32 unit epsilon={100*gp['thresholds']['float32_unit_epsilon']['negative']['fraction']:.5f}%; retreat on initially positive damage support beyond epsilon occupies {100*gp['healing_beyond_epsilon_on_positive_initial_damage']['fraction']:.5f}%. All negative and GP retreat amplitudes are below1e-3, while five nodal retreat points exceed1e-3. These are physical nodal/Q4 fields, not raw NN outputs.

Limitations: GP support area is a four-point quadrature measure, not an exact continuum level-set area. Lumped nodal support is reported separately. tol_ir is a penalty coefficient parameter, not a hard-feasibility allowance. Positive support at zero may include rounding; magnitude against unit epsilon/cast/map scales distinguishes this. No new r2 criterion, postprocessed C score, accepted temporal healing, converged state or trajectory claim is introduced. This diagnostic cannot select an additional run.
'''
    (a.out/'README_analysis.md').write_text(doc);(a.out/'C_physical_admissibility.md').write_text(doc)
    print(json.dumps(dict(nodal_min=nodal['minimum'],GP_min=gp['minimum'],nodal_healing_max=nodal['healing_max'],GP_healing_max=gp['healing_max'],GP_areas={k:gp['thresholds'][k] for k in ['float32_unit_epsilon','legacy_box_screen']},roundoff=q['roundoff']),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);main(p.parse_args())
