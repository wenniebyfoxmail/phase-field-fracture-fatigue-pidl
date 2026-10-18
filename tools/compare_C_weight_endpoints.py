"""Offline native-Q4 C/W0/W25 comparison; same frozen FEM c1s1 score."""
import argparse,csv,importlib.util,json,sys
from pathlib import Path
import numpy as np,h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).parent))
from audit_saved_physical_parity import Probe,grid


def main(a):
    a.out.mkdir(parents=True,exist_ok=False)
    done=json.loads((a.run/'complete.json').read_text());assert done['total_updates']==400 and done['status']=='completed'
    assert all(q['updates']==200 for q in done['arms']) and done['history_updates']==done['FEM_solves']==0
    z=np.load(a.run/'fixed_inputs.npz');zc=np.load(a.C/'fixed_inputs.npz');points=z['node_coords'];cells=z['connectivity']
    assert np.array_equal(points,zc['node_coords']) and np.array_equal(cells,zc['connectivity'])
    assert np.array_equal(z['FEM_initial_damage'],zc['FEM_initial_damage'])
    with h5py.File(a.reference) as h:
        s=h['request28_snapshot'];assert int(s['cycle'][0,0])==int(s['substep'][0,0])==1
        assert abs(float(s['load_factor'][0,0])*.12-.02999988)<1e-14
        assert np.array_equal(points,np.array(s['node_coords']).T) and np.array_equal(cells,np.array(s['connectivity']).T.astype(int)-1)
        uv=np.array(s['u_node']);fem=dict(u=uv[0],v=uv[1],d=np.array(s['d_node']).ravel())
    owner=a.root/'local_archive/experiments/S04-E011/runs/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z/analysis/run_multicycle_cross_replay.py'
    spec=importlib.util.spec_from_file_location('common_q4',owner);op=importlib.util.module_from_spec(spec);spec.loader.exec_module(op)
    N,B,w,xy=op.q4_geometry(points,cells);mass=np.zeros(len(points))
    for j in range(4):np.add.at(mass,cells[:,j],np.sum(w*N[:,j],axis=1))
    assert np.all(mass>0) and np.all(w>0)
    fields={'FEM':fem};rows=[];lower=z['FEM_initial_damage'].astype(float);hgp=op.interp(lower,cells,N)
    roi=(points[:,0]>=0)&(points[:,0]<=.08)&(abs(points[:,1])<=.04)
    for name,base,arm in [('C',a.C,'C'),('W0',a.run,'W0'),('W25',a.run,'W25')]:
        for k in [0,200]:
            q=np.load(base/arm/f'update{k:03d}/fields.npz');value={s:q[s].astype(float) for s in ['u','v','d']};fields[f'{name}{k}']=value
            err=np.array([(value['u']-fem['u'])/.12,(value['v']-fem['v'])/.12,value['d']-fem['d']]);mse=np.sum(mass*err**2,axis=1)/mass.sum()
            dg=op.interp(value['d'],cells,N);raw=op.amor_raw(value['u'],value['v'],cells,B);active=(1-dg)**2*raw
            fr=op.amor_raw(fem['u'],fem['v'],cells,B);fa=fr*(1-op.interp(fem['d'],cells,N))**2
            row=dict(arm=name,updates=k,J_field=float(np.sqrt(mse.mean())),u_RMS_over_Uref=float(np.sqrt(mse[0])),v_RMS_over_Uref=float(np.sqrt(mse[1])),d_RMS=float(np.sqrt(mse[2])),
                ROI_J_field=float(np.sqrt(np.sum(mass[roi]*err[:,roi]**2)/(3*mass[roi].sum()))),
                nodal_d_min=float(value['d'].min()),GP_d_min=float(dg.min()),nodal_retreat_max=float(np.maximum(lower-value['d'],0).max()),GP_retreat_max=float(np.maximum(hgp-dg,0).max()),
                GP_negative_area_above_unit_epsilon=float(w[dg<-np.finfo(np.float32).eps].sum()/w.sum()),
                GP_retreat_positive_initial_area=float(w[(hgp>np.finfo(np.float32).eps)&((hgp-dg)>np.finfo(np.float32).eps)].sum()/w.sum()))
            for key,v,ref in [('raw',raw,fr),('active',active,fa)]:
                den=np.sum(w*ref**2);row[key+'_relative_L2']=float(np.sqrt(np.sum(w*(v-ref)**2)/den)) if den else None
            rows.append(row)
    with (a.out/'metrics.csv').open('w') as f:
        writer=csv.DictWriter(f,list(rows[0]));writer.writeheader();writer.writerows(rows)
    end={q['arm']:q for q in rows if q['updates']==200}
    contrasts={name:{key:100*(1-end[name][key]/end['C'][key]) if end['C'][key] else None for key in ['J_field','u_RMS_over_Uref','v_RMS_over_Uref','d_RMS','raw_relative_L2','active_relative_L2']} for name in ['W0','W25']}
    (a.out/'summary.json').write_text(json.dumps(dict(endpoints=end,reduction_percent_vs_C=contrasts,
        W25_J_reduction_percent_vs_W0=100*(1-end['W25']['J_field']/end['W0']['J_field']),reference=str(a.reference),operator=str(owner),
        C_source=str(a.C),pair_source=str(a.run),scope='same seen synthetic c1s1; frozen histories/no hard lower-box; no clipping/selection/newFEM; C is historical, W0/W25 is paired gamma-only effect'),indent=2)+'\n')
    gx,gy,query=grid((-.04,.08,-.04,.04),241,161);probe=Probe(points,cells,query)
    names=['FEM','C200','W0200','W25200'];maps={n:{k:probe.value(fields[n][k]).reshape(161,241) for k in ['u','v','d']} for n in names}
    for errors,filename in [(False,'FEM_C_W0_W25_fields.png'),(True,'C_W0_W25_signed_errors.png')]:
        columns=names[1:] if errors else names;fig,axs=plt.subplots(3,len(columns),figsize=(12,7),layout='constrained',squeeze=False)
        for i,key in enumerate(['u','v','d']):
            scale=.12 if key!='d' else 1
            vals=[(maps[n][key]-maps['FEM'][key])/scale if errors else maps[n][key]/scale for n in columns]
            lo=min(v.min() for v in vals);hi=max(v.max() for v in vals)
            if errors:hi=max(abs(lo),abs(hi),1e-15);lo=-hi
            for j,(name,value) in enumerate(zip(columns,vals)):
                im=axs[i,j].pcolormesh(gx,gy,value,shading='auto',cmap='coolwarm' if errors or key!='d' else 'magma',vmin=lo,vmax=hi,rasterized=True)
                axs[i,j].set(aspect='equal',xlabel='x',ylabel='y',title=name+(' - FEM' if errors else '')+' | '+key+('/.12' if scale!=1 else ''))
            fig.colorbar(im,ax=axs[i,:].tolist(),shrink=.8)
        fig.suptitle('c1s1 U=.02999988 | fixed200 updates | C historical; W0/W25 paired gamma1/25\nSame C initial field; hard precrack line; no hard lower-box or symmetry')
        fig.savefig(a.out/filename,dpi=170);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4),layout='constrained');labels=['C','W0','W25']
    bars=ax.bar(labels,[end[n]['J_field'] for n in labels],color=['#777777','#0072b2','#d55e00'])
    ax.bar_label(bars,fmt='%.6f');ax.set(ylabel='Joint normalized FEM field RMS (lower is better)',title='Fixed200 endpoint | one seen synthetic c1s1 state')
    fig.savefig(a.out/'joint_field_error.png',dpi=170);plt.close(fig)
    readme=f'''# C / W0 / W25 actual endpoint comparison

Question: joint FEM field agreement and physical bound changes under gamma25 at fixed C origin.

Data provenance: C `{a.C}`, pair `{a.run}`, existing FEM `{a.reference}`, common nativeQ4 operator `{owner}`. J=sqrt(sum(m*((du/.12)^2+(dv/.12)^2+dd^2))/(3*sum(m))). Positive lumped Q4 nodal mass; GP metrics Jacobian weighted. All0/200 outputs scored; no best-point selection or field clipping.

How to read: joint_field_error shows primary score; maps show FEM/C/W0/W25 fixed200 u/.12,v/.12,d with common row scales. Signed errors have symmetric common row scales. Fixed display x[-.04,.08],y[-.04,.04]; ROI score x[0,.08],abs(y)<=.04. Bound areas use full-domain GP4 weights, not pixel/node fractions. See metrics.csv/summary.json for exact values.

Limitations: one seen synthetic state, no case variation/trajectory/generalization/physical truth claim. W0/W25 is the paired gamma effect; C is historical and numerical replay differences must be reported. Lower penalty/bound violation alone is not lower FEM error. Hard precrack line remains; no hard lower-box option is activated. Matched gamma alone does not make FEM/PIDL algorithms identical.
'''
    (a.out/'README_analysis.md').write_text(readme)
    for p in a.out.glob('*.png'):p.with_suffix('.md').write_text('# '+p.stem+'\n\n'+readme+'\nEndpoint metrics:\n```json\n'+json.dumps(end,indent=2)+'\n```\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--run',type=Path,required=True)
    p.add_argument('--C',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--out',type=Path,required=True);main(p.parse_args())
