"""Verify and visualize saved C/W0/W25 fields only; no model/solver execution."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def plot_bounds(points,cells,lower,fields,out):
    # Full native mesh cell maxima retain isolated nodal violations visually.
    fig,axs=plt.subplots(2,2,figsize=(10,10),layout='constrained')
    quantities={};maxima={}
    for name in ['W0','W25']:
        d=fields[name,200][2].astype(float)
        quantities[name,0]=np.maximum(-d,0);quantities[name,1]=np.maximum(lower-d,0)
    labels=['Negative-damage depth max(-d,0)','Retreat relative to d0: max(d0-d,0)']
    for i in range(2):
        vmax=max(float(quantities[n,i].max()) for n in ['W0','W25'])
        for j,name in enumerate(['W0','W25']):
            ax=axs[i,j];values=quantities[name,i];cellmax=values[cells].max(axis=1)
            pc=PolyCollection(points[cells],array=cellmax,cmap='magma',clim=(0,vmax),edgecolors='none',antialiaseds=False,rasterized=True)
            ax.add_collection(pc);ax.set(xlim=(-.5,.5),ylim=(-.5,.5),aspect='equal',xlabel='x',ylabel='y',title=('C = W0' if name=='W0' else 'W25')+' | '+labels[i])
            idx=int(values.argmax());xy=points[idx];maxima[name,str(i)]={'node_index0':idx,'xy':xy.tolist(),'value':float(values[idx])}
            ax.plot(*xy,'o',mfc='none',mec='#0072B2',ms=9,mew=1.5)
            if i==1:
                inset=ax.inset_axes([.57,.61,.40,.35])
                zoom=PolyCollection(points[cells],array=cellmax,cmap='magma',clim=(0,vmax),edgecolors='none',antialiaseds=False,rasterized=True)
                inset.add_collection(zoom)
                inset.set(xlim=(xy[0]-.01,xy[0]+.01),ylim=(xy[1]-.01,xy[1]+.01),aspect='equal',xticks=[],yticks=[])
                for spine in inset.spines.values():spine.set(edgecolor='white',linewidth=1.2)
                inset.text(.03,.97,'LOCAL ZOOM +/-0.01',transform=inset.transAxes,va='top',fontsize=7,color='white',bbox=dict(facecolor='black',alpha=.7,edgecolor='none'))
                ax.indicate_inset_zoom(inset,edgecolor='#0072B2',linewidth=.8)
                inset.plot(*xy,'o',mfc='none',mec='#0072B2',ms=6,mew=1.)
            ax.text(.025,.035,f'max={values[idx]:.5g}\n(x,y)=({xy[0]:.4f},{xy[1]:.4f})',transform=ax.transAxes,fontsize=8,color='white',bbox=dict(facecolor='black',alpha=.65,edgecolor='none'))
        fig.colorbar(pc,ax=axs[i,:].tolist(),shrink=.8,label='Nodal depth displayed as max over each Q4 cell')
    fig.suptitle('Saved fixed200 fields | same full native mesh, common row scales\nCell colour = maximum of its 4 nodal violation values; blue ring = exact worst node',fontsize=12)
    fig.savefig(out/'negative_damage_and_retreat.png',dpi=180);plt.close(fig)
    return maxima


def main(a):
    a.out.mkdir(parents=True, exist_ok=False)
    pair=a.pair/'retrieved/readout'; C=a.C/'retrieved/readout'
    manifest=json.loads((a.pair/'retrieved/retrieval_manifest.json').read_text())
    verified=[]; remote=[]
    for f in manifest['files']:
        if 'retrieved_sha256' not in f:
            remote.append(f['path']); continue
        p=pair/f['path']
        assert p.stat().st_size==f['retrieved_bytes'] and sha(p)==f['retrieved_sha256'],p
        verified.append(f['path'])
    cm=json.loads((a.pair/'comparison_manifest.json').read_text())
    for item in [cm['reference'],cm['native_operator'],*cm['outputs']]:
        p=Path(item['path']); assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],p
    done=json.loads((pair/'complete.json').read_text())
    assert done['total_updates']==400 and done['history_updates']==done['FEM_solves']==0
    assert {q['arm']:q['updates'] for q in done['arms']}=={'W0':200,'W25':200}
    for arm in ['W0','W25']:
        trace=json.loads((pair/arm/'trace.json').read_text())
        assert [q['before_update'] for q in trace]==list(range(200))
    z=np.load(pair/'fixed_inputs.npz');zc=np.load(C/'fixed_inputs.npz')
    points=z['node_coords'];cells=z['connectivity'];lower=z['FEM_initial_damage'].astype(float)
    for key in ['node_coords','connectivity','FEM_initial_damage']:
        assert np.array_equal(z[key],zc[key]),key
    assert np.array_equal(np.load(C/'C/initial_history.npy'),z['hist_alpha'])
    assert np.array_equal(z['hist_alpha'],z['FEM_initial_damage'])
    with h5py.File(cm['reference']['path']) as h:
        s=h['request28_snapshot'];assert int(s['cycle'][0,0])==int(s['substep'][0,0])==1
        load=float(s['load_factor'][0,0])*.12;assert abs(load-.02999988)<1e-14
        assert np.array_equal(points,np.asarray(s['node_coords']).T)
        assert np.array_equal(cells,np.asarray(s['connectivity']).T.astype(int)-1)
        uv=np.asarray(s['u_node']); ref=np.vstack([uv[0],uv[1],np.asarray(s['d_node']).ravel()])
    spec=importlib.util.spec_from_file_location('saved_q4',cm['native_operator']['path'])
    op=importlib.util.module_from_spec(spec);spec.loader.exec_module(op)
    N,B,w,_=op.q4_geometry(points,cells);mass=np.zeros(len(points))
    for j in range(4):np.add.at(mass,cells[:,j],np.sum(w*N[:,j],axis=1))
    assert np.all(mass>0) and np.all(w>0)
    hgp=op.interp(lower,cells,N);eps=np.finfo(np.float32).eps
    raw_ref=op.amor_raw(ref[0],ref[1],cells,B);active_ref=raw_ref*(1-op.interp(ref[2],cells,N))**2
    expected={(q['arm'],int(q['updates'])):q for q in csv.DictReader((a.pair/'comparison/metrics.csv').open())}
    fields={};rows=[];largest_discrepancy=0.
    for name,base,arm in [('C',C,'C'),('W0',pair,'W0'),('W25',pair,'W25')]:
        for k in [0,200]:
            with np.load(base/arm/f'update{k:03d}/fields.npz') as q:
                value=np.vstack([q[s] for s in ['u','v','d']])
            assert np.isfinite(value).all() and value.shape==(3,len(points))
            fields[name,k]=value
            d=value[2].astype(float);dg=op.interp(d,cells,N);delta=value.astype(float)-ref
            delta[:2]/=.12;rms=np.sqrt(np.sum(mass*delta**2,axis=1)/mass.sum())
            raw=op.amor_raw(value[0].astype(float),value[1].astype(float),cells,B)
            active=raw*(1-dg)**2
            metrics={'J_field':float(np.sqrt(np.mean(rms**2))),'u_RMS_over_Uref':float(rms[0]),'v_RMS_over_Uref':float(rms[1]),'d_RMS':float(rms[2]),
                'nodal_d_min':float(d.min()),'GP_d_min':float(dg.min()),
                'nodal_retreat_max':float(np.maximum(lower-d,0).max()),'GP_retreat_max':float(np.maximum(hgp-dg,0).max()),
                'GP_negative_area_above_unit_epsilon':float(w[dg < -eps].sum()/w.sum()),
                'GP_retreat_positive_initial_area':float(w[(hgp>eps)&((hgp-dg)>eps)].sum()/w.sum())}
            for key,v,r in [('raw',raw,raw_ref),('active',active,active_ref)]:
                metrics[key+'_relative_L2']=float(np.sqrt(np.sum(w*(v-r)**2)/np.sum(w*r**2)))
            for key,v in metrics.items():
                target=float(expected[name,k][key]);largest_discrepancy=max(largest_discrepancy,abs(v-target))
                assert np.isclose(v,target,rtol=1e-12,atol=1e-15),(name,k,key,v,target)
            rows.append(dict(arm=name,updates=k,**metrics))
    assert np.array_equal(fields['C',0],fields['W0',0]) and np.array_equal(fields['C',200],fields['W0',200])
    assert np.array_equal(fields['W0',0],fields['W25',0])
    mask=(points[:,0]>=-.5-1e-12)&(points[:,0]<=1e-12)&(abs(points[:,1])<=1e-12)
    assert mask.sum()==251 and all(np.all(q[2,mask]==1) for q in fields.values())
    for arm in ['W0','W25']:
        with np.load(pair/arm/'update001/fields.npz') as q:
            if arm=='W0':first={k:q[k] for k in ['u','v','d']}
            else:assert all(np.array_equal(q[k],first[k]) for k in first)
    end={q['arm']:q for q in rows if q['updates']==200}
    checks=dict(run_id=cm['run'],producer_source=cm['source_commit'],reused_comparison_source=cm['comparison_code_commit'],
        local_compact_files_verified=len(verified),remote_only_checkpoints_or_vectors=remote,
        reference_and_operator_and_outputs_hash_verified=True,metric_rows_recomputed=len(rows),maximum_absolute_metric_discrepancy=largest_discrepancy,
        mesh_nodes=len(points),Q4_cells=len(cells),positive_mass_sum=float(mass.sum()),
        same_FEM_state='c1s1/post_commit; U=.02999988; frozen history',C_W0_bitwise_equal_at_0_200=True,pair_first_step_fields_bitwise_equal=True,
        same_initial_history_and_damage=True,hard_crack_line_nodes=int(mask.sum()),endpoint_metrics=end,
        new_NN_forward=0,new_autograd=0,new_optimizer_steps=0,new_FEM_solves=0,new_producer_invocations=0,supplemental_FP64_model_replay=False,
        limitation='Only saved nodal fields and compact receipts verified locally. Checkpoints/full gradient vectors/raw GP arrays remain remote. Native float64 offline integration is the original scoring convention, not model FP64 replay.')
    (a.out/'verification.json').write_text(json.dumps(checks,indent=2)+'\n')
    with (a.out/'metrics.csv').open('w') as f:
        writer=csv.DictWriter(f,list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    maxima=plot_bounds(points,cells,lower,fields,a.out)
    checks['plot_extrema']={f'{n}_{i}':v for (n,i),v in maxima.items()}
    (a.out/'verification.json').write_text(json.dumps(checks,indent=2)+'\n')
    text=f'''# Saved-field negative damage and retreat

Question: does gamma25 remove negative damage and fixed-initial-lower violations?

Data provenance: unchanged saved C/W0/W25 fixed200 arrays under `{a.C}` and `{a.pair}`; same source and FEM metric in verification.json. No NN/model/optimizer/FEM execution. Original comparisons and rendered fields reused, not regenerated here.

How to read: rows show positive violation depths max(-d,0) and max(d0-d,0). Columns are C=W0 and W25; C and W0 are bitwise identical at0/200. Each native Q4 cell is coloured by the maximum nodal violation of its four nodes, to retain isolated extrema. This is a display reduction, not a cell-average or GP-area measure. Both panels in each row use the same scale, on the full x/y[-.5,.5] domain. Blue ring marks the exact worst saved node; text gives its actual depth and coordinates. Bottom-row insets show +/-0.01 around each panel's own worst node, with the same row colour scale; these centres differ and are explicitly marked. No original u/v/d values are clipped or altered.

Takeaway: W25 reduces negative damage depth but its maximum nodal retreat increases; neither is zero. Nodal maxima and the GP-integrated penalty can move in opposite directions. GP minima/area statistics in metrics.csv use native2x2 Q4 Jacobian weights, never coloured cell/pixel area. Negative area threshold is d<-float32 epsilon; positive-initial-support retreat area uses d0_GP>epsilon and d0_GP-d_GP>epsilon, denominator full-domain GP area.

Limitations: one seen synthetic c1s1 state, fixed200 updates; no convergence/generalization or physical truth. Full-domain maps may visually emphasize the precrack/isolated cells. Positive-part violation maps are derived observables, not a postprocessed improved prediction. Raw checkpoints and producer GP arrays remain remote; offline GP reconstruction from saved nodal arrays uses original scorer precision, not supplemental FP64 model replay.
'''
    (a.out/'negative_damage_and_retreat.md').write_text(text)
    (a.out/'README_analysis.md').write_text(text)
    print(json.dumps({k:v for k,v in checks.items() if k not in ('endpoint_metrics','plot_extrema')},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pair',type=Path,required=True);p.add_argument('--C',type=Path,required=True);p.add_argument('--out',type=Path,required=True);main(p.parse_args())
