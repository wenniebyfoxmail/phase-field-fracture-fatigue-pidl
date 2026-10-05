"""S04-E007 c83 archive-only audit. Inputs fixed to E003 immutable identities."""
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path
import h5py
import numpy as np
from hard_kkt import assess

LATE_LOCKS={76:'11a1abe4f48e15c5247fc961080e1801247a8113e96763252c4c4ae9cd721f74',82:'488c4dff334d8afa7c9c207202283699b89c19e0602b93f3e8eb10f472593e52'}
LOCKS={'native':'e4270ebd45bf35703dffa8375c2d9b474bdceb303448ddfa6d5fc453956309d4',
       'qualified':'ecee498054293f66c881a7bcf08a51b1b0315b4e2d11fa20a50c7bbe204f16c5'}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--native',type=Path,required=True);p.add_argument('--qualified',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--additional-native-dir',type=Path)
    a=p.parse_args()
    for inp in (a.native,a.qualified):
        if a.out.resolve()==inp.resolve() or a.out.resolve() in inp.resolve().parents:
            raise ValueError('Output may not contain an input')
    a.out.mkdir(parents=True,exist_ok=False)
    receipt={'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'pid':os.getpid(),'training':False,'assembly':False,'solve':False,'history_commits':0}
    try:
        receipt['commit']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        for k,expected in LOCKS.items():
            path=getattr(a,k);actual=hashlib.sha256(path.read_bytes()).hexdigest()
            receipt[k]={'path':str(path.resolve()),'sha256':actual}
            if actual!=expected:raise ValueError(k+' identity mismatch')
        with h5py.File(a.native) as f:
            c=f['converged_peak_solution'];prev=f['pre_phase_input'];o=f['matlab_residual']
            for g in (c,prev):
                assert int(g['cycle'][0,0])==83 and int(g['step'][0,0])==4
            assert int(c['staggered_iteration'][0,0])==int(prev['staggered_iteration'][0,0])
            d=c['d'][()].ravel();lo=prev['p_field_old'][()].ravel();r=o['R_d_full'][()].ravel()
            free=o['free_dof_d'][()].ravel().astype(int)-1
            fixed=o['prescribed_dof_d'][()].ravel().astype(int)-1
            assert len(d)==86756 and len(free)==86505 and len(fixed)==251
            assert np.array_equal(np.sort(fixed),np.setdiff1d(np.arange(len(d)),free))
            assert np.array_equal(lo,o['p_field_old'][()].ravel())
            assert np.array_equal(prev['history_vars_old'][()],o['history_vars_old'][()])
            assert np.array_equal(r[free],o['R_d_free'][()].ravel())
        with np.load(a.qualified) as z:
            assert np.array_equal(lo,z['fem_previous_damage']) and np.array_equal(r,z['matlab_rd']) and np.array_equal(free,z['free_damage'])
            mass=z['mass'].copy();gd=z['F_d_Ftrial_f_gd'].copy();xy=z['xy'].copy()
        # E003 locked H=1, total area=1, E=1, t=1 and Us=0.11999988.
        assert abs(np.ptp(xy[:,1])-1.)<1e-12
        es=.11999988**2
        rows={};arrays={}
        for name,vec in [('matlab',r),('pidl_frozen_trial',gd)]:
            rows[name],arrays[name+'_filtered'],arrays[name+'_legacy']=assess(vec,d,lo,free,mass,es)
            idx=rows[name]['max_kkt_node_zero_based'];rows[name]['max_kkt_xy']=xy[idx].tolist()
            for v in rows[name]['feasibility'].values():v['xy']=xy[v['node_zero_based']].tolist()
        diff=float(np.sqrt(np.sum((r[free]-gd[free])**2/mass[free]))/max(es,float(np.sqrt(np.sum(r[free]**2/mass[free])))))
        summary={'state':'U0.12 c83 s4 original FEM','coefficient':'original target frozen ftrial','rows':rows,
                 'vector_scaled_difference':diff,'vector_gate':1e-9,'vector_pass':diff<=1e-9,
                 'energy_scale':es,'normalized_hard_threshold':None,'full_teacher':'NOT_QUALIFIED'}
        if abs(rows['pidl_frozen_trial']['box_mass_rms_free']-.058073024942739936)>1e-10:raise ValueError('E003 baseline box mismatch')
        (a.out/'summary.json').write_text(json.dumps(summary,indent=2))
        np.savez_compressed(a.out/'fields.npz',d=d,previous=lo,free=free,xy=xy,**arrays)
        if diff>1e-9:raise ValueError('Vector consistency gate failed; evidence retained')
        if a.additional_native_dir is not None:
            late={}
            for cycle,sha in LATE_LOCKS.items():
                path=a.additional_native_dir/f'cycle_{cycle:04d}_peak_native_q4.mat'
                if a.out.resolve() in path.resolve().parents:raise ValueError('Output contains input')
                actual=hashlib.sha256(path.read_bytes()).hexdigest()
                receipt[f'native_c{cycle}']={'path':str(path.resolve()),'sha256':actual}
                if actual!=sha:raise ValueError('Late native identity mismatch')
                with h5py.File(path) as f:
                    c=f['converged_peak_solution'];pr=f['pre_phase_input'];o=f['matlab_residual']
                    for g in (c,pr):assert int(g['cycle'][0,0])==cycle and int(g['step'][0,0])==4
                    assert int(c['staggered_iteration'][0,0])==int(pr['staggered_iteration'][0,0])
                    dc=c['d'][()].ravel();lc=pr['p_field_old'][()].ravel();rc=o['R_d_full'][()].ravel()
                    fc=o['free_dof_d'][()].ravel().astype(int)-1
                    assert np.array_equal(fc,free) and len(dc)==len(d)
                    assert np.array_equal(lc,o['p_field_old'][()].ravel())
                    assert np.array_equal(pr['history_vars_old'][()],o['history_vars_old'][()])
                    assert np.array_equal(rc[fc],o['R_d_free'][()].ravel())
                    assert np.array_equal(np.sort(o['prescribed_dof_d'][()].ravel().astype(int)-1),np.sort(fixed))
                    assert abs(float(c['load_factor'][0,0])-.999999)<1e-12
                    ru=o['R_u_full'][()].ravel();fu=o['free_dof_u'][()].ravel().astype(int)-1
                    assert np.array_equal(fu,np.load(a.qualified)['free_uv'])
                    assert np.array_equal(ru[fu],o['R_u_free'][()].ravel()) and np.isfinite(ru).all()
                metrics,k,legacy=assess(rc,dc,lc,fc,mass,es)
                metrics['rho_u']=float(np.sqrt(np.sum((ru[fu]*.11999988/es)**2/np.tile(mass,2)[fu])))
                metrics['oracle']='native MATLAB only; no new AD comparison in this run'
                late[str(cycle)]=metrics
                np.savez_compressed(a.out/f'c{cycle}_fields.npz',d=dc,previous=lc,filtered=k,legacy=legacy)
                (a.out/'late_native_summary.json').write_text(json.dumps(late,indent=2))
        receipt['status']='COMPLETED_DIAGNOSTIC'
        print(json.dumps(summary,indent=2))
    except Exception as e:
        receipt['status']='FAILED';receipt['error']=repr(e)
        raise
    finally:
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
