"""Read-only physical-state audit. No solver/NN evaluation or training."""
from pathlib import Path
import sys,json,csv
import h5py,meshio,numpy as np,scipy.io as sio,torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import LogNorm,TwoSlopeNorm

ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
OUT=Path('/Users/wenxiaofang/.codex/visualizations/2026/10/21/01a15f55-6b92-7cd2-9122-de9ae13176d7/pidl_u012_state_onset')
FEM=Path('/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/griphfith/Hard5_eta0_5step_Umax_011_012_013_20260729/u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1')
PIDL=ROOT/'Baseline/PIDL_hard_d1_u0_recovery_5step/Umax_0.12/original_case/raw/run'
OLD=ROOT/'local_archive/after_strict_setting_alignment/fem/three_case_compare_20260701'
MAP=OLD/'analysis/state_mechanism_compare_20260701/projected_residuals/projected_npz/projection_map_polygon_overlap.npz'
HELPER=ROOT/'worktrees/synthetic-memory-mechanism-20261020/source'
sys.path.insert(0,str(HELPER))
from damage_conditioned_equilibrium import build_q4_kinematics,tensile_energy

def raw_psi(ex,ey,exy):
    mu=1/2.6;bulk=1/(3*(1-2*.3));tr=ex+ey
    return .5*bulk*np.maximum(tr,0)**2+mu*(ex**2+ey**2+2*exy**2-tr**2/3)

def metrics(a,b,area,mask):
    a=np.asarray(a)[mask];b=np.asarray(b)[mask];w=area[mask]
    ma=np.sum(w*a)/w.sum();mb=np.sum(w*b)/w.sum()
    return dict(fem_mean=float(ma),pidl_mean=float(mb),mean_ratio=float(mb/ma) if ma else None,
        relative_l2=float(np.sqrt(np.sum(w*(b-a)**2)/np.sum(w*a*a))) if np.any(a) else None,
        fem_max=float(a.max()),pidl_max=float(b.max()),
        signed_mean_log10_ratio=float(np.sum(w*(np.log10(np.maximum(b,1e-12))-np.log10(np.maximum(a,1e-12))))/w.sum()))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    mesh=meshio.read(FEM/'peak_load_c1.vtk');xy=mesh.points[:,:2];cells=mesh.cells[0].data
    old=meshio.read(OLD/'extracted/SENS_brittle_base_cyclic_u012_recovery_fatigueon_pidlstop_newtontol4em4/fields_000001_008.vtk')
    assert np.array_equal(mesh.points,old.points) and np.array_equal(cells,old.cells[0].data),'Target-map mesh identity failed'
    del old
    kin=build_q4_kinematics(xy,cells);area=kin.det_jacobians.sum(axis=1);centers=xy[cells].mean(axis=1);verts=xy[cells]
    proj=np.load(MAP);src,dst,weight=[proj[k] for k in ['src','dst','weight']];den=np.bincount(dst,weights=weight,minlength=len(cells))
    assert np.allclose(area,proj['fem_area'],rtol=5e-5,atol=2e-9) and np.all(den>0)
    def project(v):return np.bincount(dst,weights=np.asarray(v)[src]*weight,minlength=len(cells))/den
    pd=np.load(PIDL/'element_diagnostics_probe_driver/element_fields_cycle_0004.npz')
    # Verify source triangle order from the actual unchanged Gmsh source.
    tri=meshio.read(ROOT/'upload code/SENS_tensile/meshed_geom_fem_soft_hist0.msh')
    tc=next(c.data for c in tri.cells if c.type=='triangle');txy=tri.points[:,:2][tc].mean(axis=1)
    assert np.max(np.abs(txy-np.column_stack([pd['elem_x'],pd['elem_y']])))<1e-7
    uv=mesh.point_data['u'][:,:2].reshape(-1)
    eps=np.einsum('egij,ej->egi',kin.b_matrices,uv[kin.element_dofs]);gpraw,rawmean=tensile_energy(kin,uv)
    assert np.allclose(gpraw,raw_psi(eps[:,:,0],eps[:,:,1],eps[:,:,2]/2),rtol=1e-12,atol=1e-12)
    dnode=mesh.point_data['d'].ravel();dgp=np.einsum('gi,ei->eg',kin.shape_values,dnode[cells])
    active=((1-dgp)**2*gpraw).mean(axis=1)
    strain=np.sqrt(eps[:,:,0]**2+eps[:,:,1]**2+.5*eps[:,:,2]**2).mean(axis=1)
    praw=raw_psi(pd['eps_xx_elem'].astype(float),pd['eps_yy_elem'].astype(float),pd['eps_xy_elem'].astype(float))
    pstrain=pd['eps_eq_elem'].astype(float)
    femfields={'strain_norm':strain,'raw_psi':rawmean,'active_driver':active,'damage':dnode[cells].mean(axis=1)}
    pidlfields={'strain_norm':project(pstrain),'raw_psi':project(praw),'active_driver':project(pd['psi_active_elem']),'damage':project(pd['alpha_elem'])}
    x,y=centers.T
    regions={'domain':np.ones(len(cells),bool),'wake':(x<0)&(abs(y)<.03),'initial_tip':np.hypot(x,y)<=.02,'forward':(x>=0)&(x<=.05)&(abs(y)<=.03)}
    order=np.argsort(active);q=active[order[np.searchsorted(np.cumsum(area[order]),.99*area.sum())]];regions['fem_active_top1pct']=active>=q
    rows=[]
    for field in femfields:
        for region,mask in regions.items():rows.append(dict(state='c1_peak',pidl_step=4,fem_substep=4,field=field,region=region,**metrics(femfields[field],pidlfields[field],area,mask)))
    # Initial damage mismatch is retained; both fatigue states are exactly zero.
    with h5py.File(FEM/'state0_analysis.mat') as h:
        initialxy=h['state0_node'][()].T;initiald=h['state0_p_field'][()].ravel()
    assert np.max(abs(initialxy-xy))<5e-8
    p0=np.load(PIDL/'element_diagnostics_probe_driver/element_fields_cycle_0000.npz')
    initial=metrics(initiald[cells].mean(axis=1),project(p0['alpha_elem']),area,regions['domain'])
    timeline=[];previous_fem=np.zeros(len(cells));previous_pidl=np.zeros(len(cells))
    for cycle in range(1,83):
        f=sio.loadmat(FEM/f'psi_fields/cycle_{cycle:04d}.mat')
        ck=torch.load(PIDL/f'best_models/checkpoint_step_{5*cycle}.pt',map_location='cpu',weights_only=False)
        a=project(ck['hist_fat'].numpy().ravel());fa=f['alpha_bar_elem'].ravel();ff=f['f_alpha_elem'].ravel();pa=ck['hist_fat'].numpy().ravel();pf=np.where(pa<=.5,1.,(1/(pa+.5))**2)
        row=dict(cycle=cycle,pidl_step=5*cycle,fem_substep=5,phase='unloaded_post_commit',fem_f_min=float(ff.min()),pidl_f_min=float(pf.min()),fem_A_max=float(fa.max()),pidl_A_max_native=float(pa.max()),pidl_A_max_projected=float(a.max()))
        for region,mask in regions.items():
            for k,v in metrics(fa,a,area,mask).items():row[f'{region}_{k}']=v
        timeline.append(row);previous_fem,previous_pidl=fa,a
    cyclemax=sio.loadmat(FEM/'psi_fields/cycle_0001.mat')['psi_elem'].ravel()
    with h5py.File(FEM/'initial_state_metadata.mat') as h:
        fem_initial_A=float(h['initial_state_metadata/alpha_bar_initial'][0,0])
    audit=dict(initial_damage=initial,pidl_initial_saved_fatigue_zero=bool(np.max(p0['hist_fat_elem'])==0),
        fem_initial_fatigue_zero_from_metadata=bool(fem_initial_A==0),
        first_cycle_fatigue_degradation_unity_both=bool(timeline[0]['fem_f_min']==1 and timeline[0]['pidl_f_min']==1),
        fem_cycle_max_raw_vs_exact_c1_peak_relative_l2=float(np.linalg.norm(cyclemax-rawmean)/np.linalg.norm(rawmean)),
        pidl_exported_raw_vs_strain_reconstructed_relative_l2=float(np.linalg.norm(pd['psi_raw_elem']-praw)/np.linalg.norm(praw)),
        pidl_exported_raw_max=float(pd['psi_raw_elem'].max()),pidl_true_raw_max=float(praw.max()),
        earliest_retained_exact_peak='c1/s4; original FEM c1/s1-s3 displacement snapshots not retained in canonical package',
        restrictions='Cycle-end A/f compared only to cycle-end PIDL checkpoint. FEM cycle-peak maxima never combined with cycle-end d to manufacture active drivers. No cross-solver causal intervention; recovery, discretization, state update and optimizer differ.',
        pidl_driver_definition='triangle mean of g(d at tri3 GP) times raw psi, not g(mean d) times psi',
        geometry='Original polygon-map target mesh points and connectivity exactly match canonical c1 VTK. Source triangle centroid order verified <1e-7.',
        state_rows=rows)
    (OUT/'state_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    for name,rr in [('c1_peak_metrics.csv',rows),('cycle_end_history.csv',timeline)]:
        with (OUT/name).open('w',newline='') as h:w=csv.DictWriter(h,fieldnames=rr[0]);w.writeheader();w.writerows(rr)
    np.savez_compressed(OUT/'c1_aligned_fields.npz',centers=centers,area=area,vertices=verts,**{f'fem_{k}':v for k,v in femfields.items()},**{f'pidl_{k}':v for k,v in pidlfields.items()})
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(3,3,figsize=(10,8),constrained_layout=True)
    for i,(field,label) in enumerate([('strain_norm','Strain norm'),('raw_psi','Raw tensile energy'),('active_driver','Active fatigue driver')]):
        f,p=femfields[field],pidlfields[field];norm=LogNorm(vmin=1e-3 if field=='strain_norm' else 1e-5,vmax=100 if field=='strain_norm' else (1e4 if field=='raw_psi' else 1))
        for ax,v,title in [(axes[i,0],f,'FEM'),(axes[i,1],p,'PIDL')]:
            pc=PolyCollection(verts,array=np.maximum(v,1e-16),norm=norm,cmap='viridis',edgecolors='none');ax.add_collection(pc);ax.set_title(f'{title}: {label}');fig.colorbar(pc,ax=ax,shrink=.75)
        diff=np.log10(np.maximum(p,1e-12)/np.maximum(f,1e-12));pc=PolyCollection(verts,array=diff,norm=TwoSlopeNorm(vcenter=0,vmin=-2,vmax=2),cmap='RdBu_r',edgecolors='none');axes[i,2].add_collection(pc);axes[i,2].set_title('log10(PIDL/FEM)');fig.colorbar(pc,ax=axes[i,2],shrink=.75)
    for ax in axes.ravel():ax.set_xlim(-.25,.10);ax.set_ylim(-.05,.05);ax.set_aspect('equal');ax.set_xlabel('x');ax.set_ylabel('y')
    fig.suptitle('First retained matched peak: c1/s4 (both fatigue degradation = 1)');fig.savefig(OUT/'c1_local_fields.png',dpi=170);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,3.8),constrained_layout=True)
    for region,color in [('domain','#2274A5'),('wake','#D07625'),('initial_tip','#A33B58'),('forward','#397553')]:axes[0].plot([r['cycle'] for r in timeline],[r[f'{region}_mean_ratio'] for r in timeline],label=region,color=color)
    axes[0].axhline(1,color='black',ls='--',lw=.8);axes[0].set_ylabel('Mean accumulated fatigue: PIDL / FEM');axes[0].set_xlabel('Physical cycle (unloaded/post-commit)');axes[0].legend(fontsize=8)
    axes[1].plot([r['cycle'] for r in timeline],[r['fem_f_min'] for r in timeline],label='FEM min element-mean f');axes[1].plot([r['cycle'] for r in timeline],[r['pidl_f_min'] for r in timeline],label='PIDL min native-element f');axes[1].set_yscale('log');axes[1].set_xlabel('Physical cycle');axes[1].set_ylabel('Fatigue degradation (different native support)');axes[1].legend(fontsize=8)
    fig.savefig(OUT/'history_evolution.png',dpi=170);plt.close(fig)
    print(json.dumps(audit,indent=2));print('cycle end selected',json.dumps([r for r in timeline if r['cycle'] in [1,2,3,20,40,60,82]],indent=2))

if __name__=='__main__':main()
