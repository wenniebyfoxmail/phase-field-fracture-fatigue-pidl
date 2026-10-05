"""Compare archived MATLAB weak residual, independent assembly and PIDL derivative.
Qualified FEM histories are read from pre_phase_input, never postcommit.
"""
import argparse,json,csv,time,os,hashlib
from pathlib import Path
from windows_runtime import configure
configure()
import numpy as np
import h5py
import torch
from weak_form import assemble
from cross_residual import audit,evaluate,compute_fatigue_degrad,CFG

def blocked_uv(x):
    x=np.asarray(x).reshape(-1)
    return x.reshape(2,-1).T.copy()

def norm_mass(x,m):
    return float(np.sqrt(np.sum(x*x/m)))

def compare(a,b,m,force_scale):
    err=norm_mass(a-b,m);ref=norm_mass(b,m)
    return dict(max_abs=float(np.max(np.abs(a-b))),l2_diff=float(np.linalg.norm(a-b)),mass_dual_diff=err,mass_dual_ref=ref,scaled_difference=err/max(ref,force_scale),threshold=1e-9,status='PASS' if err<=1e-9*max(ref,force_scale) else 'FAIL')

def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    torch.set_num_threads(1);a.out.mkdir(parents=True,exist_ok=False)
    identity=audit(a.inputs)
    if max(identity['bottom_uv_max'],identity['top_u_max'],abs(identity['top_v_min']-.11999988),abs(identity['top_v_max']-.11999988))>1e-12:raise ValueError('BC mismatch')
    with h5py.File(a.inputs/'cycle_0083_s004_normalized.mat') as f:
        g=f['cycle_state'];xy=g['node_coords'][()].T;conn=g['connectivity_q4'][()].T.astype(np.int64)-1;uv=g['u_node'][()].T;d=g['d_node'][()].ravel();post_f=g['f_alpha_gp'][()].T
    if hashlib.sha256(a.native.read_bytes()).hexdigest()!='e4270ebd45bf35703dffa8375c2d9b474bdceb303448ddfa6d5fc453956309d4':raise ValueError('Native capture identity mismatch')
    with h5py.File(a.native) as f:
        c=f['converged_peak_solution'];p=f['pre_phase_input'];o=f['matlab_residual']
        assert int(c['cycle'][0,0])==83 and int(c['step'][0,0])==4
        for name,val in [('u',uv[:,0]),('v',uv[:,1]),('d',d)]:assert np.array_equal(c[name][()].ravel(),val)
        assert int(p['cycle'][0,0])==83 and int(p['step'][0,0])==4 and int(p['staggered_iteration'][0,0])==int(c['staggered_iteration'][0,0])
        assert np.array_equal(p['p_field_old'][()],o['p_field_old'][()]) and np.array_equal(p['history_vars_old'][()],o['history_vars_old'][()])
        prev=p['p_field_old'][()].ravel();hist=p['history_vars_old'][()].transpose(2,1,0)
        ru=blocked_uv(o['R_u_full'][()]);rd=o['R_d_full'][()].ravel()
        freeu=o['free_dof_u'][()].ravel().astype(int)-1;freed=o['free_dof_d'][()].ravel().astype(int)-1
        assert np.array_equal(o['R_u_free'][()].ravel(),ru.T.ravel()[freeu])
        assert np.array_equal(o['R_d_free'][()].ravel(),rd[freed])
    assert hist.shape==(len(conn),4,4)
    assert np.isfinite(hist).all() and np.isfinite(prev).all() and np.isfinite(ru).all() and np.isfinite(rd).all()
    t=lambda x:torch.tensor(x,dtype=torch.float64)
    ck=torch.load(a.inputs/'checkpoint_step_413.pt',map_location='cpu',weights_only=False)
    pp=ck['hist_alpha'].clamp(0,1).double();pf=compute_fatigue_degrad(ck['hist_fat'],CFG).detach().double()
    # Independent weak form and matched GP ordering. No external traction in locked SENS source.
    weak=assemble(xy,conn,uv,d);mass=weak['mass'];us=.11999988;es=float(weak['det'].sum())*us**2;scale=es/us
    mask=np.flatnonzero((xy[:,1]!=xy[:,1].min())&(xy[:,1]!=xy[:,1].max()))
    expected=np.r_[mask,mask+len(xy)]
    assert np.array_equal(np.sort(freeu),expected)
    assert len(freeu)==172916 and len(freed)==86505
    assert len(np.unique(freed))==len(freed) and np.all((freed>=0)&(freed<len(d)))
    mf=np.tile(mass,2)[freeu]
    alpha=hist[:,:,1];previous_driver=hist[:,:,2]
    assert (alpha>=0).all()
    ff=np.minimum(1.,(1-(alpha-.5)/(alpha+.5))**2)
    active=(1-d[conn]@weak['shape'].T)**2*weak['psi']
    atrial=alpha+np.maximum(active-previous_driver,0.)
    ft=np.minimum(1.,(1-(atrial-.5)/(atrial+.5))**2)
    cases=[('P_d_P_f',pp,pf),('F_d_P_f',t(prev),pf),('P_d_Fprev_f',pp,t(ff)),('F_d_Fprev_f',t(prev),t(ff)),('F_d_Ftrial_f',t(prev),t(ft))]
    rows=[];arrays={};comparisons={}
    for name,d0,f0 in cases:
        r,s,z=evaluate(t(xy),torch.tensor(conn),t(uv),t(d),d0,f0,us)
        total=r[-1];gd=z['total_grad_damage'];gu=z['total_grad_uv']
        np.testing.assert_allclose(z['nodal_mass_fraction'],mass,rtol=1e-12,atol=1e-15)
        assert abs(s['energy_scale']-es)<1e-12
        assert np.array_equal(z['free_uv_mask'],(xy[:,1]!=xy[:,1].min())&(xy[:,1]!=xy[:,1].max()))
        pd=d-np.clip(d-gd/es/mass,0,1)
        rows.append(dict(case=name,energy=total['energy'],rho_u=total['rho_u'],box_rho_d_all=total['box_projected_damage_residual'],box_rho_d_common_free=float(np.sqrt(np.sum(mass[freed]*pd[freed]**2))),healing_gp_max=s['healing_gp_max'],healing_gp_rms=s['healing_gp_rms'],penalty_energy=r[2]['energy']))
        arrays[name+'_gd']=gd
        if arrays.get('pidl_grad_uv') is not None:np.testing.assert_allclose(gu,arrays['pidl_grad_uv'],rtol=0,atol=1e-14)
        if name=='P_d_P_f':
            comparisons['pidl_vs_matlab_free_uv']=compare(gu.T.ravel()[freeu],ru.T.ravel()[freeu],mf,scale)
            comparisons['numpy_vs_matlab_free_uv']=compare(weak['force'].T.ravel()[freeu],ru.T.ravel()[freeu],mf,scale)
            comparisons['numpy_vs_pidl_free_uv']=compare(weak['force'].T.ravel()[freeu],gu.T.ravel()[freeu],mf,scale)
            comparisons['pidl_vs_matlab_full_uv']=compare(gu.T.ravel(),ru.T.ravel(),np.tile(mass,2),scale)
            arrays['pidl_grad_uv']=gu
        if name=='F_d_Ftrial_f':
            diagnostic=compare(gd[freed],rd[freed],mass[freed],es)
            diagnostic.pop('status');diagnostic.pop('threshold')
            diagnostic['interpretation']='Diagnostic only: penalty, fixed DOFs and trial coefficient semantics differ.'
            comparisons['frozen_trial_damage_vs_matlab_common_free']=diagnostic
    arrays.update(xy=xy,conn=conn,mass=mass,matlab_ru=ru,matlab_rd=rd,numpy_force=weak['force'],free_uv=freeu,free_damage=freed,fem_previous_damage=prev,fem_fprev=ff,fem_ftrial=ft)
    interaction=arrays['F_d_Fprev_f_gd']-arrays['F_d_P_f_gd']-arrays['P_d_Fprev_f_gd']+arrays['P_d_P_f_gd']
    np.testing.assert_allclose(interaction,0,rtol=0,atol=1e-10)
    assert all(np.isfinite(v).all() for v in arrays.values())
    summary=dict(identity=identity,comparisons=comparisons,matlab_rho_u=norm_mass(ru.T.ravel()[freeu]*us/es,mf),matlab_free_uv_l2=float(np.linalg.norm(ru.T.ravel()[freeu])),fprev_formula_vs_stored_max=float(np.max(np.abs(ff-hist[:,:,3]))),ftrial_vs_fprev_max=float(np.max(np.abs(ft-ff))),numpy_energy=weak['energy'],history_control='QUALIFIED_SAME_REPLAY_PRECOMMIT',damage_free_dofs=len(freed),pidl_damage_dofs=len(d),fem_penalty_source_default=421875.,fem_penalty_runtime='not independently serialized/verified',pidl_penalty_coefficient=16875.,primary='pidl_vs_matlab_free_uv',stationarity_screen=.001,pid=os.getpid(),training=False,history_commits=0,readonly_trial_coefficient_evaluations=1,gradient_interaction_max=float(abs(interaction).max()),trial_vs_postcommit_f_max=float(abs(ft-post_f).max()),external_load_status='zero reconstructed from locked source BC path; not separately serialized',coefficient_hashes={k:hashlib.sha256(v.detach().numpy().tobytes()).hexdigest() for k,_,v in cases},finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2))
    with (a.out/'history_controls.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    np.savez_compressed(a.out/'fields.npz',**arrays)
    print(json.dumps(summary,indent=2));print(rows)
if __name__=='__main__':main()
