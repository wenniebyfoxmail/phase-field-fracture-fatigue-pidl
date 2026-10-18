"""Offline frozen c1s1 scoring; target FEM never enters the producer runner."""
import argparse,csv,importlib.util,json,sys
from pathlib import Path
import numpy as np,h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).parent))
from audit_saved_physical_parity import Probe,grid


def write_csv(path,rows):
    with path.open('w') as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)


def main(a):
    a.out.mkdir(parents=True,exist_ok=False)
    complete=json.loads((a.run/'complete.json').read_text())
    assert complete['status']=='completed' and complete['total_updates']==600
    assert [q['arm'] for q in complete['arms']]==['A','B','C']
    assert all(q['updates']==200 for q in complete['arms'])
    assert complete['elapsed_seconds']<3600 and complete['history_updates']==complete['FEM_solves']==0
    owner=a.root/'local_archive/experiments/S04-E011/runs/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z/analysis/run_multicycle_cross_replay.py'
    spec=importlib.util.spec_from_file_location('frozen_q4',owner);op=importlib.util.module_from_spec(spec);spec.loader.exec_module(op)
    z=np.load(a.run/'fixed_inputs.npz');points=z['node_coords'];cells=z['connectivity'];line=z['crack_mask']
    with h5py.File(a.reference) as h:
        s=h['request28_snapshot']
        assert int(s['cycle'][0,0])==int(s['substep'][0,0])==1
        assert abs(.12*float(s['load_factor'][0,0])-.02999988)<1e-14
        assert np.array_equal(points,np.array(s['node_coords']).T)
        assert np.array_equal(cells,np.array(s['connectivity']).T.astype(int)-1)
        uv=np.array(s['u_node']);fem=dict(u=uv[0],v=uv[1],d=np.array(s['d_node']).ravel())
    N,B,w,xy=op.q4_geometry(points,cells)
    assert np.all(w>0)
    mass=np.zeros(len(points))
    for j in range(4):np.add.at(mass,cells[:,j],np.sum(w*N[:,j],axis=1))
    assert np.all(mass>0) and abs(mass.sum()-1)<1e-9
    roi=(points[:,0]>=0)&(points[:,0]<=.08)&(abs(points[:,1])<=.04)
    fields={'FEM':fem};rows=[]
    for arm in ['A','B','C']:
        for k in [0,200]:
            q=np.load(a.run/arm/f'update{k:03d}/fields.npz')
            fields[f'{arm}{k}']={s:q[s].astype(float) for s in ['u','v','d']}
    for name,q in fields.items():
        assert all(np.isfinite(v).all() for v in q.values())
        q['raw']=op.amor_raw(q['u'],q['v'],cells,B)
        q['active']=q['raw']*(1-op.interp(q['d'],cells,N))**2
    for name,q in fields.items():
        err=np.stack(((q['u']-fem['u'])/.12,(q['v']-fem['v'])/.12,q['d']-fem['d']))
        mse=np.sum(err**2*mass,axis=1)/mass.sum();den=mse.sum()
        row=dict(arm_stage=name,J_field=float(np.sqrt(mse.mean())),
            u_RMS_over_Uref=float(np.sqrt(mse[0])),v_RMS_over_Uref=float(np.sqrt(mse[1])),d_RMS=float(np.sqrt(mse[2])),
            u_squared_fraction=float(mse[0]/den) if den else None,v_squared_fraction=float(mse[1]/den) if den else None,
            d_squared_fraction=float(mse[2]/den) if den else None,
            ROI_J_field=float(np.sqrt(np.sum(mass[roi]*err[:,roi]**2)/(3*mass[roi].sum()))),
            line_d_RMS=float(np.sqrt(np.sum(mass[line]*err[2,line]**2)/mass[line].sum())),
            free_d_RMS=float(np.sqrt(np.sum(mass[~line]*err[2,~line]**2)/mass[~line].sum())),
            d_min=float(q['d'].min()),d_max=float(q['d'].max()))
        for key in ['raw','active']:
            absolute=float(np.sqrt(np.sum(w*(q[key]-fem[key])**2)));refnorm=float(np.sqrt(np.sum(w*fem[key]**2)))
            row[key+'_absolute_L2']=absolute;row[key+'_relative_L2']=absolute/refnorm if refnorm else None
        rows.append(row)
    write_csv(a.out/'metrics.csv',rows);by={r['arm_stage']:r for r in rows}
    contrasts=[]
    for stage in [0,200]:
        for earlier,later,meaning in [('A','B','hard line/current+history conditional effect'),('B','C','FEM initial field/history/representation bundle; not pure initialization'),('A','C','combined alignment')]:
            before=by[f'{earlier}{stage}']['J_field'];after=by[f'{later}{stage}']['J_field']
            contrasts.append(dict(comparison=f'{later}-{earlier}',update=stage,before=before,after=after,
                error_reduction_percent=100*(1-after/before),meaning=meaning))
    optimization=[];initial=[];energy=[]
    for arm in ['A','B','C']:
        before=by[f'{arm}0']['J_field'];after=by[f'{arm}200']['J_field']
        optimization.append(dict(arm=arm,before=before,after=after,error_reduction_percent=100*(1-after/before)))
        q=np.load(a.run/arm/'U0_initial.npz');e=q['d'].astype(float)-z['FEM_initial_damage'].astype(float)
        initial.append(dict(arm=arm,damage_RMS_to_FEM_U0_float32=float(np.sqrt(np.sum(mass*e**2)/mass.sum())),
            damage_Linf_to_FEM_U0_float32=float(abs(e).max()),line_Linf=float(abs(q['d'][line]-1).max())))
        trace=json.loads((a.run/arm/'trace.json').read_text());assert len(trace)==200
        totals=[sum(q['energies']) for q in trace]+[sum(complete['arms'][ord(arm)-65]['after']['energies'])]
        energy.append(dict(arm=arm,initial=totals[0],after_first=totals[1],first_ratio=totals[1]/totals[0],
            maximum=max(totals),endpoint=totals[-1]))
    summary=dict(primary='mass-weighted joint u/v/d RMS: scales .12,.12,1',reference=str(a.reference),native_operator=str(owner),
        run=str(a.run),elapsed_seconds=complete['elapsed_seconds'],initial=initial,optimization=optimization,contrasts=contrasts,energy=energy,
        interpretation='negative reduction means worse; one seen synthetic development state; no convergence/generalization/physical-validity claim',
        validity='same canonical Q4 nodes; frozen histories; no FEM loss or best-FEM checkpoint selection; no symmetry',
        remaining_model_differences='FEM trial-fatigue/staggered/gamma421875/hard constraints versus PIDL committed-f/joint/gamma16875')
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    # All predeclared arms and endpoints, on shared scales. Maps use native bilinear reconstruction.
    names=list(fields)
    def field_plot(bounds,nx,ny,filename,errors=False):
        gx,gy,query=grid(bounds,nx,ny);p=Probe(points,cells,query)
        maps={n:{k:p.value(fields[n][k]).reshape(ny,nx) for k in ['u','v','d']} for n in names}
        columns=names[1:] if errors else names
        fig,axs=plt.subplots(3,len(columns),figsize=(18,8),layout='constrained',squeeze=False)
        for i,k in enumerate(['u','v','d']):
            scale=.12 if k in ['u','v'] else 1
            values=[(maps[n][k]-maps['FEM'][k])/scale if errors else maps[n][k]/scale for n in columns]
            lo,hi=min(q.min() for q in values),max(q.max() for q in values)
            if errors:hi=max(abs(lo),abs(hi),1e-15);lo=-hi
            for j,(n,val) in enumerate(zip(columns,values)):
                im=axs[i,j].pcolormesh(gx,gy,val,shading='auto',cmap='coolwarm' if errors or k!='d' else 'magma',vmin=lo,vmax=hi,rasterized=True)
                axs[i,j].set(aspect='equal',xlabel='x',ylabel='y',title=f'{n}'+(' - FEM' if errors else '')+f' | {k}'+('/.12' if scale!=1 else ''))
            fig.colorbar(im,ax=axs[i,:].tolist(),shrink=.8)
        fig.suptitle('c1s1 U=.02999988 | A legacy; B hard precrack line; C FEM-initial anchored map\n0/200 = optimizer updates | synthetic development diagnostic; fixed histories; symmetry off',fontsize=11)
        fig.savefig(a.out/filename,dpi=160);plt.close(fig)
    field_plot((-.5,.5,-.5,.5),401,401,'primitive_fields.png')
    field_plot((-.5,.5,-.5,.5),401,401,'primitive_errors.png',True)
    field_plot((-.04,.08,-.04,.04),241,161,'front_fields.png')
    field_plot((-.04,.08,-.04,.04),241,161,'front_errors.png',True)
    fig,axs=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for arm,color in zip(['A','B','C'],['#666666','#d55e00','#0072b2']):
        axs[0].plot([0,200],[by[f'{arm}{k}']['J_field'] for k in [0,200]],'o-',label=arm,color=color)
    axs[0].set(xlabel='Optimizer updates',ylabel='Joint FEM field error (lower is better)',xticks=[0,200]);axs[0].legend()
    positions=np.arange(3);width=.25
    for j,(k,label) in enumerate([('u_RMS_over_Uref','u/.12'),('v_RMS_over_Uref','v/.12'),('d_RMS','d')]):
        axs[1].bar(positions+(j-1)*width,[by[f'{arm}200'][k] for arm in ['A','B','C']],width,label=label)
    axs[1].set(xticks=positions,xticklabels=['A200','B200','C200'],ylabel='Component FEM RMS');axs[1].legend()
    fig.suptitle('One c1s1 synthetic development state | update0 / fixed update200; no uncertainty estimate')
    fig.savefig(a.out/'error_stages.png',dpi=180);plt.close(fig)
    profiles=[];fig,axs=plt.subplots(1,4,figsize=(14,4),layout='constrained');yy=np.linspace(-.04,.04,1601)
    for ax,xp in zip(axs,[-.25,0,.01,.02]):
        p=Probe(points,cells,np.column_stack((np.full_like(yy,xp),yy)))
        for name,q in fields.items():
            dd=p.value(q['d']);positive=np.maximum(dd,0);m=np.trapezoid(positive,yy)
            center=float(np.trapezoid(yy*positive,yy)/m) if m>0 else None
            width=float(np.sqrt(np.trapezoid((yy-center)**2*positive,yy)/m)) if m>0 else None
            profiles.append(dict(arm_stage=name,x=xp,positive_mass=float(m),centroid=center,centered_width=width))
            ax.plot(yy,dd,label=name,ls='--' if name.endswith('0') and not name.endswith('200') else '-')
        ax.set(xlabel='y',ylabel='damage',title=f'x={xp:g}')
    axs[-1].legend(fontsize=6);fig.savefig(a.out/'damage_profiles.png',dpi=180);plt.close(fig);write_csv(a.out/'profiles.csv',profiles)
    extents=[]
    for name,q in fields.items():
        row=dict(arm_stage=name)
        for threshold in [.25,.5,.75]:
            mask=(points[:,0]>=0)&(q['d']>=threshold);row[str(threshold)]=float(points[mask,0].max()) if mask.any() else None
        extents.append(row)
    (a.out/'front_extents.json').write_text(json.dumps(extents,indent=2)+'\n')
    readme=f'''# A/B/C c1s1 FEM field comparison

Question: separate conditional hard precrack-line change, FEM initial-field/history/representation change, and within-arm optimization change.

Data provenance: `{a.run}`; reference `{a.reference}`; operator `{owner}`. Full canonical native Q4 nodal mass scoring; all six endpoints scored. Source run complete in {complete['elapsed_seconds']:.3f}s, 600 total updates; no new FEM or history commit. FEM target is scoring-only.

How to read: start with `error_stages.png` with `metrics.csv`, then `primitive_fields.png` and `primitive_errors.png` (u/.12,v/.12,d; rows; FEM then A0,A200,B0,B200,C0,C200). `front_fields.png`/`front_errors.png` use the fixed display window x[-.04,.08],y[-.04,.04]; scoring ROI remains x[0,.08],abs(y)<=.04. Fields have common row scales; signed errors have symmetric common row scales. No clipping, mirroring, smoothing or fitted color limits. `damage_profiles.png` compares all fields at four frozen x sections; `profiles.csv` uses positive-part damage only for morphology integrals, never for field scores.

Primary result and conditional differences: see `summary.json`. Initial U0 mapping checks are separate from loaded update0 accuracy; endpoint minus update0 is optimization within an arm. B-A is line/current+history; C-B is an initial field/history/representation bundle with changed tangent, not pure initialization. Limitations: one seen synthetic development state has no independent-case uncertainty and is not a trajectory or convergence test. No physical truth, FEM equivalence, generalization, or baseline promotion is claimed. FEM trial-fatigue, staggered algorithm and constraint differences remain.

Storyline S04/E011: retain the original negative results; this bounded diagnostic selects the next repair without changing an old verdict.
'''
    (a.out/'README_analysis.md').write_text(readme)
    for path in a.out.glob('*.png'):(path.with_suffix('.md')).write_text(f'# {path.stem}\n\n'+readme+'\nExact stage metrics:\n```json\n'+json.dumps(optimization,indent=2)+'\n```\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--run',type=Path,required=True)
    p.add_argument('--reference',type=Path,required=True);p.add_argument('--out',type=Path,required=True);main(p.parse_args())
