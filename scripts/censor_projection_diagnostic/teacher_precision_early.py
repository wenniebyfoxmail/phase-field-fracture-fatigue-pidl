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

def run(a):
    a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
    from hard_kkt_audit import LOCKS
    LATE_LOCKS={20: "cccd3eb2c9b9c1fd8ba8d13574e6b5199f1f13dd13ab7bde6936ee2c94fb1af7", 40: "bb772c07439ddbfa4c8cc75f415431fe0fd549f9ba2ce47ebbad1f62558539be"}
    from hard_kkt import assess as hard_assess
    path=a.inputs/'qualified_fields.npz'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==LOCKS['qualified']
    native=a.inputs/f'cycle_{a.cycle:04d}_peak_native_q4.mat'
    assert hashlib.sha256(native.read_bytes()).hexdigest()==LATE_LOCKS[a.cycle]
    z=np.load(path);xy=z['xy'].copy();conn=z['conn'].copy()
    with h5py.File(native) as f:
        c=f['converged_peak_solution'];pr=f['pre_phase_input'];o=f['matlab_residual']
        for g in (c,pr):assert int(g['cycle'][0,0])==a.cycle and int(g['step'][0,0])==4
        assert int(c['staggered_iteration'][0,0])==int(pr['staggered_iteration'][0,0])
        uv=np.column_stack((c['u'][()].ravel(),c['v'][()].ravel()));d=c['d'][()].ravel()
        prev=pr['p_field_old'][()].ravel();hist=pr['history_vars_old'][()].transpose(2,1,0)
        assert np.array_equal(prev,o['p_field_old'][()].ravel())
        assert np.array_equal(pr['history_vars_old'][()],o['history_vars_old'][()])
        native_ru=o['R_u_full'][()].ravel();native_rd=o['R_d_full'][()].ravel()
        for key,name in [('free_uv','free_dof_u'),('free_damage','free_dof_d')]:
            assert np.array_equal(z[key],o[name][()].ravel().astype(int)-1)
        assert np.array_equal(native_ru[z['free_uv']],o['R_u_free'][()].ravel())
        assert np.array_equal(native_rd[z['free_damage']],o['R_d_free'][()].ravel())
    assert hist.shape==(86408,4,4) and (prev>=0).all() and (d>=prev).all() and (d<=1).all()
    assert np.isfinite(hist).all()
    original_weak=assemble(xy,conn,uv,d)
    original_active=(1-d[conn]@original_weak['shape'].T)**2*original_weak['psi']
    atrial=hist[:,:,1]+np.maximum(original_active-hist[:,:,2],0.)
    assert (hist[:,:,1]>=0).all()
    fat=np.minimum(1.,(1-(atrial-.5)/(atrial+.5))**2)
    saved=(d.copy(),prev.copy(),fat.copy())
    identity={'cycle':a.cycle,'substep':4,'native_sha':LATE_LOCKS[a.cycle],
              'qualified_sha':LOCKS['qualified'],'state':'original FEM peak','prior':'own accepted pre_phase_input','replay':'request29_fixed_calendar_20260819_v2/u012; c0 to c40; solver cdf4e337' }
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
        pd=d-np.clip(d-fields['total_grad_damage']/es/m,0,1);fd=z['free_damage']
        result=dict(energy=rows[-1]['energy'],elastic_energy=rows[0]['energy'],fracture_energy=rows[1]['energy'],history_energy=rows[2]['energy'],rho_u=rows[-1]['rho_u'],rho_d_all=rows[-1]['box_projected_damage_residual'],rho_d_common=float(np.sqrt(np.sum(m[fd]*pd[fd]**2))),weak_gradient_agreement=agreement)
        result['hard_kkt']=hard_assess(fields['total_grad_damage'],d,prev,fd,m,es)[0]
        if np.array_equal(u,uv):
            result['native_uv_agreement']=compare(fields['total_grad_uv'].T.ravel()[nativefree],native_ru[nativefree],np.tile(m,2)[nativefree],es/us)
            result['native_damage_agreement']=compare(fields['total_grad_damage'][fd],native_rd[fd],m[fd],es)
        strain=np.einsum('egij,ej->egi',kin.b_matrices,u.ravel()[kin.element_dofs])[:,PERM,:]
        active=(1-d[conn]@n.numpy().T)**2*weak['psi']
        return result,strain,active,m
    before,e0,p0,m=assess(uv)
    (a.out/'before.json').write_text(json.dumps(before,indent=2))
    assert all(before[k]['status']=='PASS' for k in ('weak_gradient_agreement','native_uv_agreement','native_damage_agreement'))
    if before['rho_u']<=.001:
        result=dict(identity=identity,before=before,after=None,uv_block_screen='UV_SCREEN_PASS_NO_SOLVE',full_teacher='NOT_QUALIFIED',scope='original FEM UV screen only; no solve or correction estimate',delta_uv_mass_rms_over_Us=None,strain_tensor=None,active=None,active_original_p99=None,iterations=0,history_commits=0,damage_solves=0,training=False,pid=os.getpid(),finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
        (a.out/'summary.json').write_text(json.dumps(result,indent=2))
        np.savez_compressed(a.out/'fields.npz',xy=xy,conn=conn,original_uv=uv,damage=d,strain_before=e0,active_before=p0,gp_weights=w)
        print(json.dumps(result,indent=2));return
    try:
        solved=solve_amor_equilibrium(kin,d,bc,bv,residual_stiffness=0.,initial_displacement=uv.ravel(),max_iterations=50,tolerance=1e-9,residual_tolerance=1e-8,minimum_pivot_ratio=1e-14)
    except RuntimeError as ex:
        (a.out/'failure.json').write_text(json.dumps(dict(status='SOLVER_FAILED',error=str(ex),teacher='NOT_QUALIFIED',pid=os.getpid()),indent=2));raise
    u1=solved.displacement.reshape(-1,2);after,e1,p1,_=assess(u1)
    (a.out/'after.json').write_text(json.dumps(after,indent=2))
    assert after['weak_gradient_agreement']['status']=='PASS'
    assert all(np.array_equal(x,y) for x,y in zip((d,prev,fat),saved))
    np.testing.assert_allclose(u1.ravel()[bc],bv,rtol=0,atol=1e-12)
    for key in ('fracture_energy','history_energy'):assert after[key]==before[key]
    tau=weighted_quantile(p0,w,.99);mask=(p0>0)&(p0>=tau)
    arrays=dict(xy=xy,conn=conn,original_uv=uv,equilibrated_uv=u1,damage=d,strain_before=e0,strain_after=e1,active_before=p0,active_after=p1,gp_weights=w,original_p99_mask=mask)
    assert all(np.isfinite(v).all() for v in arrays.values())
    result=dict(identity=identity,before=before,after=after,uv_block_screen='PASS' if after['rho_u']<=.001 else 'FAIL',full_teacher='NOT_QUALIFIED',scope='fixed damage UV only; original-target fatigue coefficient frozen; no coupled evolution or mesh convergence',delta_uv_mass_rms_over_Us=float(np.sqrt(np.sum(m[:,None]*(u1-uv)**2))/us),strain_tensor=norm_report(e1,e0,w[:,:,None]*np.array([1.,1.,.5]),us*np.sqrt(w.sum())),active=norm_report(p1,p0,w,us**2*np.sqrt(w.sum())),original_p99_threshold=tau,original_p99_area_fraction=float(w[mask].sum()/w.sum()),active_original_p99=norm_report(p1[mask],p0[mask],w[mask],us**2*np.sqrt(w[mask].sum())) if mask.any() else None,elastic_energy_nonincrease=after['elastic_energy']<=before['elastic_energy']+1e-12,iterations=solved.iterations,active_set_stable=solved.active_set_stable,solver_normalized_residual=solved.normalized_residual,minimum_pivot_ratio=solved.minimum_pivot_ratio,history_commits=0,damage_solves=0,training=False,pid=os.getpid(),finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    (a.out/'summary.json').write_text(json.dumps(result,indent=2));np.savez_compressed(a.out/'fields.npz',**arrays)
    print(json.dumps(result,indent=2))
def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--cycle',type=int,choices=[20,40],required=True);a=p.parse_args()
    if a.out.resolve()==a.inputs.resolve() or a.out.resolve() in a.inputs.resolve().parents or a.inputs.resolve() in a.out.resolve().parents:raise ValueError('Input/output trees must be disjoint')
    if a.out.exists():raise FileExistsError(a.out)
    try:run(a)
    except Exception as e:
        if a.out.exists() and not (a.out/'summary.json').exists():
            (a.out/'failure.json').write_text(json.dumps({'status':'FAILED','error':repr(e),'cycle':a.cycle,'full_teacher':'NOT_QUALIFIED','pid':os.getpid()},indent=2))
        raise
if __name__=='__main__':main()
