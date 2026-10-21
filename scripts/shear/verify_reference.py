"""Recompute a retrieved shear reference's declared checks; never solve/refit."""
from pathlib import Path
import argparse,json,csv
import numpy as np
from scipy.io import loadmat


def scalar(s,k):return float(s[k].item())
def text(s,k):return ''.join(s[k].ravel().astype(str))
def finite_number(x):return float(x) if np.isfinite(x) else None

def main():
 p=argparse.ArgumentParser();p.add_argument('--fem',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--previous-mesh',type=Path,required=True);a=p.parse_args()
 assert not a.out.exists();a.out.mkdir(parents=True)
 m=loadmat(a.fem/'mesh.mat');old=loadmat(a.previous_mesh)
 for k in ['nodes','quads','alpha_initial','schedule']:assert np.array_equal(m[k],old[k]),k
 x=m['nodes'][:,:2];n=len(x);schedule=m['schedule'].ravel();crack=m['crack'].ravel().astype(int)-1
 expected=np.flatnonzero((abs(x[:,1])<1e-10)&(x[:,0]>=-.5-1e-10)&(x[:,0]<=1e-10))
 assert np.array_equal(crack,expected) and len(crack)==251
 top=m['top'].ravel().astype(int)-1;bot=m['bot'].ravel().astype(int)-1
 free=np.setdiff1d(np.arange(n),np.r_[top,bot]);free_dof=np.r_[free,free+n]
 previous=m['alpha_initial'].ravel()
 with (a.fem/'trajectory.csv').open() as f:rows=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
 assert [int(r['step']) for r in rows]==list(range(1,len(rows)+1))
 verified=[];pf_force_verified=0
 free_pf=np.setdiff1d(np.arange(n),crack)
 for r in rows:
  step=int(r['step']);s=loadmat(a.fem/f'state_{step:03d}.mat');alpha=s['p_field'].ravel();hist=s['p_field_old'].ravel();uv=s['displ'].ravel();force=s['forces'].ravel()
  assert len(uv)==2*n and len(force)==2*n and len(alpha)==n
  for v in [alpha,hist,uv,force,s['driver']]:assert np.isfinite(v).all()
  assert text(s,'timing')=='post_solve_pre_history_update' and scalar(s,'step')==step
  assert scalar(s,'U')==schedule[step-1] and abs(r['U']-schedule[step-1])<1e-14
  assert np.array_equal(hist,previous)
  assert np.all(alpha[crack]==1)
  np.testing.assert_allclose(uv[top],r['U'],rtol=0,atol=1e-12)
  np.testing.assert_allclose(uv[np.r_[bot,bot+n,top+n]],0,rtol=0,atol=1e-12)
  checks={'alpha_min':alpha.min(),'alpha_max':alpha.max(),'max_healing':(hist-alpha).max(),'res_u':np.linalg.norm(force[free_dof]),'Rx_top':force[top].sum(),'Rx_bottom':force[bot].sum()}
  for k,v in checks.items():assert np.isclose(v,r[k],rtol=1e-10,atol=1e-12),(step,k,v,r[k])
  for k in ['res_u','res_pf','E_el','E_d']:assert np.isclose(scalar(s,k),r[k],rtol=1e-10,atol=1e-12)
  assert all(np.isfinite(scalar(s,k)) for k in ['res_u','res_pf','E_el','E_d'])
  if 'pf_force' in s:
   pf_force=s['pf_force'].ravel();assert len(pf_force)==n and np.isfinite(pf_force).all()
   assert np.isclose(np.linalg.norm(pf_force[free_pf]),r['res_pf'],rtol=1e-10,atol=1e-12)
   pf_force_verified+=1
  assert checks['alpha_min']>=-.005 and checks['alpha_max']<=1.005 and checks['max_healing']<=.005
  assert scalar(s,'res_u')+scalar(s,'res_pf')<=1e-4
  verified.append(dict(r,verified=True));previous=alpha
 failures=[]
 for path in sorted(a.fem.glob('failed_state_*.mat')):
  s=loadmat(path);alpha=s['p_field'].ravel();hist=s['p_field_old'].ravel();uv=s['displ'].ravel()
  failures.append(dict(file=path.name,step=int(scalar(s,'step')),U=scalar(s,'U'),timing=text(s,'timing'),reason=text(s,'rejection_reason'),seconds=scalar(s,'elapsed_seconds'),step_seconds=scalar(s,'step_seconds'),alpha_min=float(alpha.min()),alpha_max=float(alpha.max()),max_healing=float((hist-alpha).max()),displacement_finite=bool(np.isfinite(uv).all()),max_abs_displacement=float(abs(uv).max()),history_matches_last_accepted=bool(np.array_equal(hist,previous)),res_u=finite_number(scalar(s,'res_u')),res_pf=finite_number(scalar(s,'res_pf')),forces_present=bool(s['forces'].size),initial_crack_held=bool(np.all(alpha[crack]==1))))
 end=json.loads((a.fem.parent/'exit.json').read_text())
 complete=len(verified)==len(schedule) and end['exit_code']==0 and (a.fem/'COMPLETED.txt').exists()
 result=dict(accepted_prefix=len(verified),prescribed_states=len(schedule),complete_valid_reference=complete,native_mesh_and_initial_arrays_equal_prior=True,PF_force_norm_verified_states=pf_force_verified,failures=failures,exit=end,PIDL_ran=False,scope='synthetic numerical reference' if complete else 'synthetic numerical prefix; no full-path reference',evidence_boundary='No physical validation or paired score inferred; saved force vectors are checked, native assembly is not replayed.')
 (a.out/'reference_verification.json').write_text(json.dumps(result,indent=2,allow_nan=False))
 if verified:
  with (a.out/'verified_states.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(verified[0]));w.writeheader();w.writerows(verified)
 print(json.dumps(result,indent=2,allow_nan=False))

if __name__=='__main__':main()
