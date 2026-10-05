"""E010: immutable accepted-state reconstruction, never a stored MATLAB oracle."""
import argparse,csv,hashlib,json,os,time
from pathlib import Path
from windows_runtime import configure
configure()
import h5py
import numpy as np
import torch
from weak_form import assemble,assert_native_gp_shape
from damage_weak_form import assemble_damage
from cross_residual import evaluate
from weak_history_audit import compare
from hard_kkt import assess as hard_assess
from damage_conditioned_equilibrium import sens_displacement_boundary_conditions

MANIFEST_SHA='307c22703d8e20d224c250563f9a47297fa7e3b3a3ce1a6edef167d944b41679'
US=.11999988


def run(a):
    a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
    mp=a.inputs/'input_manifest.json'
    assert hashlib.sha256(mp.read_bytes()).hexdigest()==MANIFEST_SHA
    manifest=json.loads(mp.read_text())
    for name,sha in manifest['files'].items():
        assert hashlib.sha256((a.inputs/name).read_bytes()).hexdigest()==sha,name
    index={r['state_key']:r for r in csv.DictReader((a.inputs/'state_index.csv').open())}
    z=np.load(a.inputs/'qualified_fields.npz');xy=z['xy'];conn=z['conn'];fu=z['free_uv'];fd=z['free_damage']
    with h5py.File(a.inputs/'native_q4_mesh_dofs_quadrature.mat') as f:
        g=f['stage0b_static'];np.testing.assert_array_equal(g['mesh/node_coordinates'][()].T,xy)
        np.testing.assert_array_equal(g['mesh/cells_0based'][()].T,conn)
        np.testing.assert_array_equal(g['dofs/active_dof'][()].ravel()-1,fu)
        np.testing.assert_array_equal(g['dofs/active_dof_pf'][()].ravel()-1,fd)
        assert_native_gp_shape(g['quadrature/Nxi'][()])
        for k,v in dict(E=1.,ni=.3,Gc=.01,ell=.01,alpha_T=.5,res_stiff=0.,p=2.).items():
            assert float(g['material_parameters'][k][0,0])==v
        for k in ('tx_increment','ty_increment'):
            assert not g['boundary_conditions'][k][()].any()
        schedule=g['case_config/effective_uy'][()].ravel()
    assert np.ptp(xy[:,1])==1.
    t=lambda x:torch.tensor(x,dtype=torch.float64)
    allrows=[]

    def load(c,s):
        key=f'c{c:04d}_s{s:02d}';meta=index[key]
        assert meta['timing']=='post_history_commit' and meta['converged']=='1'
        assert int(meta['cycle'])==c and int(meta['substep'])==s
        assert meta['payload_sha256']==manifest['files']['states/'+key+'.mat']
        with h5py.File(a.inputs/'states'/f'{key}.mat') as f:
            g=f['state_metadata'];assert int(g['cycle'][0,0])==c and int(g['substep'][0,0])==s
            imposed=float(g['imposed_displacement'][0,0])
            assert abs(imposed-float(meta['imposed_displacement']))<1e-15
            assert abs(imposed-schedule[s-1])<1e-15
            values=(f['u_node'][()].T,f['d_node'][()].ravel(),f['history_gp'][()].transpose(2,1,0))
        assert all(np.isfinite(v).all() for v in values)
        return (*values,imposed)

    def state(c,s,bridge=False):
        uv,d,post,uy=load(c,s);_,prev,hist,_=load(c,s-1)
        assert (prev>=0).all() and (prev<=d).all() and (d<=1).all()
        assert hist.shape==(86408,4,4) and (hist[:,:,1]>=0).all()
        bc,bv=sens_displacement_boundary_conditions(xy,uy)
        np.testing.assert_allclose(uv.ravel()[bc],bv,rtol=0,atol=1e-12)
        free=np.setdiff1d(np.arange(uv.size),bc)
        np.testing.assert_array_equal(free,np.sort((fu%len(xy))*2+fu//len(xy)))
        weak=assemble(xy,conn,uv,d);mass=weak['mass'];es=weak['det'].sum()*US**2
        active=(1-d[conn]@weak['shape'].T)**2*weak['psi']
        atrial=hist[:,:,1]+np.maximum(active-hist[:,:,2],0.)
        fatigue=np.minimum(1.,(1-(atrial-.5)/(atrial+.5))**2)
        rd,_=assemble_damage(xy,conn,d,prev,weak['psi'],fatigue)
        assert all(np.isfinite(v).all() for v in (weak['force'],mass,rd,fatigue))
        rows,_,fields=evaluate(t(xy),torch.tensor(conn),t(uv),t(d),t(prev),t(fatigue),US)
        np.testing.assert_allclose(mass,fields['nodal_mass_fraction'],rtol=1e-12,atol=1e-15)
        agreements={
            'numpy_torch_uv':compare(weak['force'].ravel()[free],fields['total_grad_uv'].ravel()[free],np.repeat(mass,2)[free],es/US),
            'numpy_torch_damage':compare(rd[fd],fields['total_grad_damage'][fd],mass[fd],es)}
        if bridge:
            with h5py.File(a.inputs/'native'/f'cycle_{c:04d}_peak_native_q4.mat') as f:
                cur=f['converged_peak_solution'];pr=f['pre_phase_input'];o=f['matlab_residual']
                for g in (cur,pr):assert int(g['cycle'][0,0])==c and int(g['step'][0,0])==4
                assert int(cur['staggered_iteration'][0,0])==int(pr['staggered_iteration'][0,0])
                np.testing.assert_array_equal(d,cur['d'][()].ravel())
                np.testing.assert_array_equal(uv,np.column_stack([cur['u'][()].ravel(),cur['v'][()].ravel()]))
                np.testing.assert_array_equal(prev,pr['p_field_old'][()].ravel())
                # Slot1 has explicitly different archival semantics and is unused.
                np.testing.assert_array_equal(hist[:,:,1:],pr['history_vars_old'][()].transpose(2,1,0)[:,:,1:])
                np.testing.assert_array_equal(pr['history_vars_old'][()],o['history_vars_old'][()])
                np.testing.assert_array_equal(prev,o['p_field_old'][()].ravel())
                np.testing.assert_array_equal(fu,o['free_dof_u'][()].ravel()-1)
                np.testing.assert_array_equal(fd,o['free_dof_d'][()].ravel()-1)
                ru=o['R_u_full'][()].ravel();nd=o['R_d_full'][()].ravel()
                np.testing.assert_array_equal(ru[fu],o['R_u_free'][()].ravel())
                np.testing.assert_array_equal(nd[fd],o['R_d_free'][()].ravel())
            for name,value,ref,m,scale in [('numpy_native_uv',weak['force'].T.ravel()[fu],ru[fu],np.tile(mass,2)[fu],es/US),('torch_native_uv',fields['total_grad_uv'].T.ravel()[fu],ru[fu],np.tile(mass,2)[fu],es/US),('numpy_native_damage',rd[fd],nd[fd],mass[fd],es),('torch_native_damage',fields['total_grad_damage'][fd],nd[fd],mass[fd],es)]:
                agreements[name]=compare(value,ref,m,scale)
        hard,filtered,_=hard_assess(fields['total_grad_damage'],d,prev,fd,mass,es)
        row=dict(cycle=c,substep=s,previous_substep=s-1,imposed_displacement=uy,normalization_Us=US,energy_scale=float(es),rho_u=rows[-1]['rho_u'],box=hard['box_mass_rms_free'],hard_kkt=hard,agreements=agreements,oracle_kind='archived_MATLAB_bridge' if bridge else 'reconstructed_not_archived_MATLAB',archived_oracle_gate='PASS' if bridge and all(v['status']=='PASS' for v in agreements.values()) else ('FAIL' if bridge else 'NOT_AVAILABLE'),full_teacher='NOT_QUALIFIED',slot1_used=False,uv_screen='PASS' if rows[-1]['rho_u']<=.001 else 'FAIL',box_screen='PASS' if hard['box_mass_rms_free']<=.001 else 'FAIL',history_energy=rows[2]['energy'])
        key=f'c{c:04d}_s{s:02d}'
        row['original_stopping_scalars']={k:float(index[key][k]) for k in ('equilibrium_residual','phase_residual','staggered_iterations')}
        (a.out/f'{key}.json').write_text(json.dumps(row,indent=2))
        np.savez_compressed(a.out/f'{key}.npz',grad_uv=fields['total_grad_uv'],grad_damage=fields['total_grad_damage'],hard_filtered=filtered,box_map=fields['projected_damage_residual'],mass=mass)
        allrows.append(row);(a.out/'rows.json').write_text(json.dumps(allrows,indent=2))
        assert all(v['status']=='PASS' for v in agreements.values()),key
        assert hard['exactly_feasible'] and rows[2]['energy']==0.
        print(key,row['rho_u'],row['box'],hard['hard_kkt_raw_l2'],flush=True)

    # No new-state calculation until ALL five bridge states passed.
    for c in manifest['bridge_cycles']:state(c,4,True)
    (a.out/'bridge_gate.json').write_text(json.dumps({'status':'PASS','cycles':manifest['bridge_cycles']}))
    for c in manifest['cycles']:
        for s in manifest['substeps']:
            if s==4 and c in manifest['bridge_cycles']:continue
            state(c,s)
    np.savez_compressed(a.out/'geometry.npz',xy=xy,conn=conn,free_uv=fu,free_damage=fd)
    (a.out/'receipt.json').write_text(json.dumps(dict(status='RECONSTRUCTED_SCREEN_COMPLETE',states=len(allrows),pid=os.getpid(),finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),full_teacher='NOT_QUALIFIED',solves=0,history_commits=0,training=False),indent=2))


def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise FileExistsError(a.out)
    if a.out.resolve() in a.inputs.resolve().parents or a.inputs.resolve() in a.out.resolve().parents or a.out.resolve()==a.inputs.resolve():raise ValueError('Disjoint trees required')
    try:run(a)
    except Exception as e:
        if a.out.exists():(a.out/'failure.json').write_text(json.dumps({'status':'FAILED_NO_TREND','error':repr(e),'pid':os.getpid(),'full_teacher':'NOT_QUALIFIED'},indent=2))
        raise

if __name__=='__main__':main()
