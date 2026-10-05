"""Fixed-FEM-damage UV precision diagnostic; no evolution or neural model."""
import argparse,json,time,os,hashlib,csv
from pathlib import Path
from windows_runtime import configure
configure()
import numpy as np
import h5py
import torch
from cross_residual import audit,evaluate,q4_shape_data
from weak_form import assemble,assert_native_gp_shape
from weak_history_audit import compare
from damage_conditioned_equilibrium import build_q4_kinematics,sens_displacement_boundary_conditions,solve_amor_equilibrium

PERM=[2,3,1,0]  # solver (--,+-,++,-+) -> native (++,-+,+-,--)

def relative_l2(a,b,w):
    num=float(np.sum(w*(a-b)**2));den=float(np.sum(w*b*b))
    return None if den==0 else float(np.sqrt(num/den))

def norm_report(a,b,w,nominal):
    error=float(np.sqrt(np.sum(w*(a-b)**2)));ref=float(np.sqrt(np.sum(w*b*b)))
    small=ref<=1e-12*nominal
    return dict(error_norm=error,reference_norm=ref,nominal_norm=nominal,value=error/(nominal if small else ref),kind="nominal_scale" if small else "relative_l2")

def weighted_quantile(x,w,q):
    idx=np.argsort(x.ravel(),kind='stable');s=np.cumsum(w.ravel()[idx]);return float(x.ravel()[idx[np.searchsorted(s,q*s[-1])]])

def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1);identity=audit(a.inputs)
    path=a.inputs/'qualified_fields.npz'
    assert hashlib.sha256(path.read_bytes()).hexdigest()=='ecee498054293f66c881a7bcf08a51b1b0315b4e2d11fa20a50c7bbe204f16c5'
    z=np.load(path)
    with h5py.File(a.inputs/'cycle_0083_s004_normalized.mat') as f:
        g=f['cycle_state'];xy=g['node_coords'][()].T;conn=g['connectivity_q4'][()].T.astype(int)-1;uv=g['u_node'][()].T;d=g['d_node'][()].ravel()
    assert np.array_equal(xy,z['xy']) and np.array_equal(conn,z['conn'])
    prev=z['fem_previous_damage'].copy();fat=z['fem_ftrial'].copy();saved=(d.copy(),prev.copy(),fat.copy())
    assert float(np.ptp(xy[:,1]))==1.
    us=.11999988;t=lambda v:torch.tensor(v,dtype=torch.float64)
    n,_,det=q4_shape_data(t(xy),torch.tensor(conn));w=det.numpy();es=float(w.sum())*us**2
    kin=build_q4_kinematics(xy,conn);assert_native_gp_shape(kin.shape_values[PERM]);np.testing.assert_allclose(kin.det_jacobians[:,PERM],w,rtol=1e-12,atol=1e-15)
    bc,bv=sens_displacement_boundary_conditions(xy,us);np.testing.assert_allclose(uv.ravel()[bc],bv,rtol=0,atol=1e-12)
    free=np.setdiff1d(np.arange(uv.size),bc);nativefree=z['free_uv'];mapped=(nativefree%len(xy))*2+nativefree//len(xy);assert np.array_equal(free,np.sort(mapped))
    def assess(u):
        rows,s,fields=evaluate(t(xy),torch.tensor(conn),t(u),t(d),t(prev),t(fat),us)
        weak=assemble(xy,conn,u,d);m=weak['mass'];np.testing.assert_allclose(m,fields['nodal_mass_fraction'],rtol=1e-12,atol=1e-15)
        agreement=compare(weak['force'].ravel()[free],fields['total_grad_uv'].ravel()[free],np.repeat(m,2)[free],es/us)
        assert agreement['status']=='PASS'
        pd=d-np.clip(d-fields['total_grad_damage']/es/m,0,1);fd=z['free_damage']
        result=dict(energy=rows[-1]['energy'],elastic_energy=rows[0]['energy'],fracture_energy=rows[1]['energy'],history_energy=rows[2]['energy'],rho_u=rows[-1]['rho_u'],rho_d_all=rows[-1]['box_projected_damage_residual'],rho_d_common=float(np.sqrt(np.sum(m[fd]*pd[fd]**2))),weak_gradient_agreement=agreement)
        strain=np.einsum('egij,ej->egi',kin.b_matrices,u.ravel()[kin.element_dofs])[:,PERM,:]
        active=(1-d[conn]@n.numpy().T)**2*weak['psi']
        return result,strain,active,m
    before,e0,p0,m=assess(uv)
    assert abs(before['rho_u']-.041331479715259814)<1e-10
    assert abs(before['rho_d_common']-.058073024942739936)<1e-10
    (a.out/'before.json').write_text(json.dumps(before,indent=2))
    try:
        solved=solve_amor_equilibrium(kin,d,bc,bv,residual_stiffness=0.,initial_displacement=uv.ravel(),max_iterations=50,tolerance=1e-9,residual_tolerance=1e-8,minimum_pivot_ratio=1e-14)
    except RuntimeError as ex:
        (a.out/'failure.json').write_text(json.dumps(dict(status='SOLVER_FAILED',error=str(ex),teacher='NOT_QUALIFIED',pid=os.getpid()),indent=2));raise
    u1=solved.displacement.reshape(-1,2);after,e1,p1,_=assess(u1)
    assert all(np.array_equal(x,y) for x,y in zip((d,prev,fat),saved))
    np.testing.assert_allclose(u1.ravel()[bc],bv,rtol=0,atol=1e-12)
    for key in ('fracture_energy','history_energy'):assert after[key]==before[key]
    tau=weighted_quantile(p0,w,.99);mask=(p0>0)&(p0>=tau)
    arrays=dict(xy=xy,conn=conn,original_uv=uv,equilibrated_uv=u1,damage=d,strain_before=e0,strain_after=e1,active_before=p0,active_after=p1,gp_weights=w,original_p99_mask=mask)
    assert all(np.isfinite(v).all() for v in arrays.values())
    result=dict(identity=identity,before=before,after=after,uv_block_screen='PASS' if after['rho_u']<=.001 else 'FAIL',full_teacher='NOT_QUALIFIED',scope='fixed damage UV only; original-target fatigue coefficient frozen; no coupled evolution or mesh convergence',delta_uv_mass_rms_over_Us=float(np.sqrt(np.sum(m[:,None]*(u1-uv)**2))/us),strain_tensor=norm_report(e1,e0,w[:,:,None]*np.array([1.,1.,.5]),us*np.sqrt(w.sum())),active=norm_report(p1,p0,w,us**2*np.sqrt(w.sum())),original_p99_threshold=tau,original_p99_area_fraction=float(w[mask].sum()/w.sum()),active_original_p99=norm_report(p1[mask],p0[mask],w[mask],us**2*np.sqrt(w[mask].sum())) if mask.any() else None,elastic_energy_nonincrease=after['elastic_energy']<=before['elastic_energy']+1e-12,iterations=solved.iterations,active_set_stable=solved.active_set_stable,solver_normalized_residual=solved.normalized_residual,minimum_pivot_ratio=solved.minimum_pivot_ratio,history_commits=0,damage_solves=0,training=False,pid=os.getpid(),finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    (a.out/'summary.json').write_text(json.dumps(result,indent=2));np.savez_compressed(a.out/'fields.npz',**arrays)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
