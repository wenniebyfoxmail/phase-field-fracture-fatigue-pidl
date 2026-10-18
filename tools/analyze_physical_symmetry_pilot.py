"""Score the approved pilot endpoints and plot FEM/control/candidate fields."""
import argparse,csv,importlib.util,json,sys
from pathlib import Path
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).parent))
from audit_saved_physical_parity import Probe


def main(a):
    a.out.mkdir(parents=True,exist_ok=False)
    complete=json.loads((a.run/'complete.json').read_text())
    assert complete['status']=='completed' and complete['total_updates']==400
    assert all(r['updates']==200 for r in complete['arms'])
    assert complete['history_updates']==complete['FEM_solves']==0 and complete['elapsed_seconds']<3600
    owner=a.root/'local_archive/experiments/S04-E011/runs/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z/analysis/run_multicycle_cross_replay.py'
    spec=importlib.util.spec_from_file_location('existing_operator',owner);op=importlib.util.module_from_spec(spec);spec.loader.exec_module(op)
    z=np.load(a.run/'fixed_inputs.npz');points=z['node_coords'].astype(float);cells=z['connectivity'].astype(int)
    with h5py.File(a.reference) as h:
        s=h['request28_snapshot'];assert int(s['cycle'][0,0])==1 and int(s['substep'][0,0])==2
        assert np.array_equal(np.array(s['connectivity']).T.astype(int)-1,cells)
        canonical=np.array(s['node_coords']).T
        assert np.max(abs(points-canonical))<2e-8
        uv=np.array(s['u_node']);fem=dict(u=uv[0],v=uv[1],d=np.array(s['d_node']).ravel())
        assert abs(.12*float(s['load_factor'][0,0])-.05999988)<1e-14
    # One shared canonical float64 operator for FEM and BOTH endpoints; no solve.
    points=canonical;N,B,w,xy=op.q4_geometry(points,cells)
    mass=np.zeros(len(points))
    for j in range(4):np.add.at(mass,cells[:,j],np.sum(w*N[:,j],axis=1))
    fields={'FEM':fem}
    for arm in ['original','control','physical_uv']:
        q=np.load(a.run/arm/'fields.npz');fields[arm]={k:q[k].astype(float) for k in ['u','v','d']}
    for q in fields.values():
        q['raw']=op.amor_raw(q['u'],q['v'],cells,B);q['g']=(1-op.interp(q['d'],cells,N))**2;q['active']=q['raw']*q['g']
    rows=[]
    for name,q in fields.items():
        row=dict(arm=name)
        for field in ['raw','g','active']:
            ref=fem[field];value=q[field]
            row[field+'_relative_L2']=float(np.sqrt(np.sum(w*(value-ref)**2)/np.sum(w*ref**2)))
            row[field+'_integral']=float(np.sum(w*value))
        row['uv_mass_RMS_over_Uref']=float(np.sqrt(np.sum(mass*((q['u']-fem['u'])**2+(q['v']-fem['v'])**2))/mass.sum())/.12)
        row['damage_mass_RMS']=float(np.sqrt(np.sum(mass*(q['d']-fem['d'])**2)/mass.sum()))
        row.update(d_min=float(q['d'].min()),d_max=float(q['d'].max()),healing_max=float(np.maximum(z['hist_alpha']-q['d'],0).max()))
        rows.append(row)
    with (a.out/'metrics.csv').open('w') as f:
        out=csv.DictWriter(f,list(rows[0]));out.writeheader();out.writerows(rows)
    control=next(r for r in rows if r['arm']=='control');candidate=next(r for r in rows if r['arm']=='physical_uv')
    delta={k:dict(control=control[k],candidate=candidate[k],relative_change_percent=100*(candidate[k]/control[k]-1) if control[k] else None)
           for k in ['active_relative_L2','raw_relative_L2','uv_mass_RMS_over_Uref','damage_mass_RMS']}
    (a.out/'summary.json').write_text(json.dumps(dict(primary=delta['active_relative_L2'],components=delta,
       elapsed_seconds=complete['elapsed_seconds'],lambda0=complete['lambda0'],updates=400,
       interpretation='negative percent means lower same-state FEM disagreement; exploratory single-state result only',
       native_operator=str(owner),reference=str(a.reference)),indent=2)+'\n')
    x=np.linspace(-.04,.08,241);y=np.linspace(-.04,.04,161);X,Y=np.meshgrid(x,y)
    probe=Probe(points,cells,np.column_stack((X.ravel(),Y.ravel())))
    maps={name:probe.fields(q['u'],q['v'],q['d'],.05999988) for name,q in fields.items()}
    fig,axes=plt.subplots(5,5,figsize=(15,12),layout='constrained')
    for i,key in enumerate(['u','v_correction','d','raw','active']):
        scale=.12 if key in ['u','v_correction'] else 1
        f,c,p=[maps[n][key].reshape(Y.shape)/scale for n in ['FEM','control','physical_uv']]
        lo=min(f.min(),c.min(),p.min());hi=max(f.max(),c.max(),p.max());err=max(abs(c-f).max(),abs(p-f).max(),1e-15)
        for j,value in enumerate([f,c,p,c-f,p-f]):
            vmin,vmax=(lo,hi) if j<3 else (-err,err)
            im=axes[i,j].pcolormesh(x,y,value,shading='auto',vmin=vmin,vmax=vmax,cmap='magma' if j<3 and key in ['d','raw','active'] else 'coolwarm',rasterized=True)
            axes[i,j].axhline(0,color='gray',lw=.5,ls='--');axes[i,j].set(aspect='equal',xlabel='x',ylabel='y')
            axes[i,j].set_title(['Original FEM','Control 200 steps','Physical-u/v 200 steps','Control - FEM','Candidate - FEM'][j]+'\n'+key+('/Uref' if scale!=1 else ''),fontsize=8)
            fig.colorbar(im,ax=axes[i,j],shrink=.65,pad=.01).ax.tick_params(labelsize=6)
    fig.suptitle('Q4 c1s2 fixed-history pilot | original FEM numerical comparator\nNative bilinear field reconstruction; no hard symmetry, history commit or new FEM',fontsize=11)
    fig.savefig(a.out/'FEM_control_candidate_fields.png',dpi=180);plt.close(fig)
    profiles=[];fig,axs=plt.subplots(1,3,figsize=(11,4),layout='constrained')
    yy=np.linspace(-.04,.04,1601)
    for ax,xp in zip(axs,[0,.01,.02]):
        pp=Probe(points,cells,np.column_stack((np.full_like(yy,xp),yy)))
        for name,q in fields.items():
            dd=pp.value(q['d']);positive=np.maximum(dd,0);m=np.trapezoid(positive,yy)
            center=np.trapezoid(yy*positive,yy)/m if m>0 else None
            width=np.sqrt(np.trapezoid((yy-center)**2*positive,yy)/m) if m>0 else None
            profiles.append(dict(arm=name,x=xp,positive_mass=float(m),centroid=center,centered_width=width))
            if name!='original':ax.plot(yy,dd,label=name)
        ax.set(xlabel='y',ylabel='damage',title=f'x={xp:g}');ax.legend(fontsize=7)
    fig.savefig(a.out/'damage_profiles.png',dpi=180);plt.close(fig)
    with (a.out/'profiles.csv').open('w') as f:
        out=csv.DictWriter(f,list(profiles[0]));out.writeheader();out.writerows(profiles)
    extents=[]
    for name,q in fields.items():
        forward=points[:,0]>=0
        row=dict(arm=name)
        for threshold in [.25,.5,.75]:
            mask=forward&(q['d']>=threshold);row[str(threshold)]=float(points[mask,0].max()) if mask.any() else None
        extents.append(row)
    (a.out/'front_extents.json').write_text(json.dumps(extents,indent=2)+'\n')
    print(json.dumps(delta,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--run',type=Path,required=True)
    p.add_argument('--reference',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    main(p.parse_args())
