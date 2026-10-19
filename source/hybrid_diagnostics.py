"""Common posthoc diagnostics only; never inputs or checkpoint selection."""
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from damage_conditioned_equilibrium import tensile_energy,plane_strain_tensors
from hybrid_producer_common import write_json


def fields(backend,state,previous):
    k=backend.kin;w=k.det_jacobians;area=w.sum();u=state.displacement
    psi,_=tensile_energy(k,u,youngs_modulus=backend.material['youngs_modulus'],poisson_ratio=backend.material['poisson_ratio'])
    strain=np.einsum('egij,ej->egi',k.b_matrices,u[k.element_dofs])
    C,*_=plane_strain_tensors(backend.material['youngs_modulus'],backend.material['poisson_ratio'])
    total=.5*np.einsum('egi,ij,egj->eg',strain,C,strain);minus=total-psi
    dg=(backend.gp@state.damage).reshape(-1,4);oldgp=(backend.gp@previous.damage).reshape(-1,4)
    active=(1-dg)**2*psi
    dx=np.einsum('egj,ej->eg',k.b_matrices[:,:,0,0::2],state.damage[k.cells])
    dy=np.einsum('egj,ej->eg',k.b_matrices[:,:,1,1::2],state.damage[k.cells])
    fracture=state.fatigue*(backend.gc/backend.length_scale)/(8/3)*(dg+backend.length_scale**2*(dx*dx+dy*dy))
    elastic=active+minus
    mixed=(state.damage[k.cells].min(axis=1)<.5)&(state.damage[k.cells].max(axis=1)>=.5)
    front=k.points[np.unique(k.cells[mixed])]
    support=dg>=.5
    gp_xy=np.einsum('gn,end->egd',k.shape_values,k.points[k.cells])
    tip=float(np.max(gp_xy[:,:,0][support])) if np.any(support) else None
    diag=dict(elastic_energy=float(np.sum(w*elastic)),fracture_energy=float(np.sum(w*fracture)),
              total_energy=float(np.sum(w*(elastic+fracture))),trace_positive_fraction=float(np.sum(w*(strain[:,:,0]+strain[:,:,1]>=0))/area),
              min_damage=float(state.damage.min()),negative_amplitude=float(max(0.,-state.damage.min())),
              box_violation=float(max(0.,state.damage.max()-1.,-state.damage.min())),
              nodal_healing=float(max(0.,np.max(previous.damage-state.damage))),
              gp_healing=float(max(0.,np.max(oldgp-dg))),crack_support_area=float(w[support].sum()),tip_x=tip)
    return dict(raw=psi,active=active,sign=strain[:,:,0]+strain[:,:,1]>=0,damage_gp=dg,front=front,diag=diag)


def compare_diagnostics(backend,candidate,reference,previous_candidate,previous_reference):
    a=fields(backend,candidate,previous_candidate);b=fields(backend,reference,previous_reference)
    w=backend.kin.det_jacobians;area=w.sum();result=dict(candidate=a['diag'],reference=b['diag'])
    # Reference-defined diffuse zone is diagnostic, used only AFTER sealed rollouts.
    zone=(b['damage_gp']>=.05)&(b['damage_gp']<=.95)
    xy=np.einsum('gn,end->egd',backend.kin.shape_values,backend.kin.points[backend.kin.cells])
    fixed=(xy[:,:,0]>=-.02)&(xy[:,:,0]<=.12)&(abs(xy[:,:,1])<=3*backend.length_scale)
    for name in ('raw','active'):
        error=(a[name]-b[name])**2
        result[name+'_rms']=float(np.sqrt(np.sum(w*error)/area))
        for suffix,mask in [('diffuse_zone',zone),('fixed_tip_window',fixed)]:
            result[name+'_'+suffix+'_rms']=float(np.sqrt(np.sum(w[mask]*error[mask])/w[mask].sum())) if np.any(mask) else None
    result['trace_branch_mismatch_area_fraction']=float(w[a['sign']!=b['sign']].sum()/area)
    ca=a['damage_gp']>=.5;cb=b['damage_gp']>=.5;union=w[ca|cb].sum()
    result['support_iou']=float(w[ca&cb].sum()/union) if union else 1.
    fa,fb=a['front'],b['front']
    result['front_hausdorff']=float(max(cKDTree(fa).query(fb)[0].max(),cKDTree(fb).query(fa)[0].max())) if len(fa) and len(fb) else (0. if len(fa)==len(fb) else None)
    result['front_definition']='all nodes of Q4 cells crossing d=.5; no mesh interpolation claim'
    for key in ('elastic_energy','fracture_energy','total_energy'):
        result[key+'_relative_error']=abs(a['diag'][key]-b['diag'][key])/max(abs(b['diag'][key]),1e-8)
    return result


def plot_fields(backend,states,step,out,provenance):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.tri as mtri
    k=backend.kin;tri=np.concatenate((k.cells[:,[0,1,2]],k.cells[:,[0,2,3]]))
    # Triangles are a display of nodal Q4 fields; GP scores remain native Q4.
    mesh=mtri.Triangulation(k.points[:,0],k.points[:,1],tri)
    channels=('u','v','d');getters=(lambda s:s.displacement[0::2],lambda s:s.displacement[1::2],lambda s:s.damage)
    fig,axes=plt.subplots(3,6,figsize=(17,8),constrained_layout=True)
    for j,(ch,get) in enumerate(zip(channels,getters)):
        vals=[get(s) for s in states];lo=min(v.min() for v in vals);hi=max(v.max() for v in vals)
        if hi==lo:hi=lo+1e-15
        err=max(float(np.max(abs(v-vals[0]))) for v in vals);err=max(err,1e-15)
        for i,(name,v) in enumerate(zip(('reference','classical','hybrid'),vals)):
            a=axes[i,2*j];h=a.tripcolor(mesh,v,shading='gouraud',cmap='viridis',vmin=lo,vmax=hi,rasterized=True)
            a.set_title(f'{name} {ch}');fig.colorbar(h,ax=a,shrink=.7)
            a=axes[i,2*j+1];h=a.tripcolor(mesh,v-vals[0],shading='gouraud',cmap='RdBu_r',vmin=-err,vmax=err,rasterized=True)
            a.set_title(f'{name} {ch} error');fig.colorbar(h,ax=a,shrink=.7)
    for a in axes.flat:a.set_aspect('equal');a.set_xlabel('x (nondimensional)');a.set_ylabel('y')
    fig.suptitle(f"{provenance.get('scope','Sealed same-problem comparison')}\nStep {step}; common scales per channel")
    out=Path(out);out.mkdir(parents=True,exist_ok=True);stem=out/f'fields_step{step:04d}'
    fig.savefig(str(stem)+'.png',dpi=160);fig.savefig(str(stem)+'.pdf');plt.close(fig)
    stem.with_suffix('.md').write_text(f'''# Aligned fields at fixed step {step}\n\nQuestion: do sealed classical and hybrid fields match the same-problem numerical reference?\nSource: {provenance}\nRows: reference/classical/hybrid. Column pairs: nondimensional u,v,d values and signed errors. Shared limits per channel across all rows; error limits zero-centred. All geometry shown. Q4 nodal data displayed with a fixed triangle split and linear colour interpolation; exact scores use native2x2GP. No smoothing of arrays or physical-truth claim. Selection fixed before results: steps4,304,599,600. Values and errors are posthoc only.\n\nSee: use common scales to locate differences. Therefore: numerical field agreement must be assessed with the frozen aggregate criteria. Does not show: physical or geometry/material generalization.\n''')
    write_json(str(stem)+'.json',dict(step=step,provenance=provenance,selection='fixed4,304,599,600',state_ids=[s.fingerprint() for s in states]))
    plot_gp_fields(backend,states,step,out,provenance)


def plot_gp_fields(backend,states,step,out,provenance):
    import matplotlib.pyplot as plt
    import matplotlib.tri as mtri
    k=backend.kin;tri=np.concatenate((k.cells[:,[0,1,2]],k.cells[:,[0,2,3]]))
    mesh=mtri.Triangulation(k.points[:,0],k.points[:,1],tri);w=k.det_jacobians
    data=[fields(backend,s,s) for s in states]
    fig,axes=plt.subplots(3,4,figsize=(13,8),constrained_layout=True)
    for j,ch in enumerate(('raw','active')):
        vals=[(w*d[ch]).sum(axis=1)/w.sum(axis=1) for d in data]
        errs=[np.sqrt((w*(d[ch]-data[0][ch])**2).sum(axis=1)/w.sum(axis=1)) for d in data]
        lo=min(v.min() for v in vals);hi=max(v.max() for v in vals);hi=max(hi,lo+1e-15);emax=max(max(e.max() for e in errs),1e-15)
        for i,name in enumerate(('reference','classical','hybrid')):
            for col,v,cmap,vmin,vmax,label in ((2*j,vals[i],'viridis',lo,hi,ch+' GP cell mean'),(2*j+1,errs[i],'magma',0.,emax,ch+' GP error RMS')):
                a=axes[i,col];h=a.tripcolor(mesh,facecolors=np.tile(v,2),cmap=cmap,vmin=vmin,vmax=vmax,rasterized=True)
                a.set_title(name+' '+label);a.set_aspect('equal');a.set_xlabel('x');a.set_ylabel('y');fig.colorbar(h,ax=a,shrink=.7)
    fig.suptitle(f"{provenance.get('scope','Sealed same-problem comparison')}\nStep{step}: native GP raw and active driver, common scales")
    stem=Path(out)/f'raw_active_step{step:04d}';fig.savefig(str(stem)+'.png',dpi=160);fig.savefig(str(stem)+'.pdf');plt.close(fig)
    stem.with_suffix('.md').write_text(f"# Raw and active GP fields at fixed step{step}\n\nSource: {provenance}. Rows reference/classical/hybrid; column pairs raw tensile energy and Carrara active driver=(1-d_GP)^2 raw, plus reference error. Values are native2x2 GP Jacobian-weighted cell means displayed with a fixed triangle split; errors are GP cell RMS (not signed means). Common limits across methods, no smoothing of scored arrays. All variables nondimensional; selection4,304,599,600 fixed before outcomes. This is posthoc numerical same-family comparison; no physical/generalization conclusion. See differences on common scales; assess frozen criteria jointly; raw alone cannot rescue quality/energy/history failure.\n")
