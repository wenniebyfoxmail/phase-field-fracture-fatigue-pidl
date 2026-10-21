"""Read saved R007 Armijo scalars/available vectors; no native replay."""
from pathlib import Path
import argparse,csv,json
import numpy as np
from scipy.io import loadmat
p=argparse.ArgumentParser();p.add_argument('--fem',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
a.out.mkdir(exist_ok=False)
m=loadmat(a.fem/'mesh.mat');n=len(m['nodes']);edge=np.r_[m['top'].ravel(),m['bot'].ravel()].astype(int)-1
free=np.setdiff1d(np.arange(n),edge);active=np.r_[free,free+n]
summary=[];mapping=[];vectors=0;backtracked=0;accepted_updates=0;max_halvings=0
for file in sorted((a.fem/'mechanics').glob('step_*/stag_*/trace.csv')):
 with file.open() as f:rows=list(csv.DictReader(f))
 if not rows:continue
 base_values={float(r['global_evaluation_id']) for r in rows if np.isfinite(float(r['global_evaluation_id']))}
 assert len(base_values)==1,'Review a new global-ID behavior rather than relabel silently'
 base=int(next(iter(base_values)));trials={};accepted=0;maxev=0
 for rownum,r in enumerate(rows,1):
  kind=r['event'];it=int(r['iteration']);j=int(r['trial']);ev=int(r['evaluations']);maxev=max(maxev,ev)
  if kind=='trial':
   lam=float(r['lambda']);phi=float(r['trial_merit']);ru=float(r['trial_Ru'])
   assert 0<=j<=12 and lam==.5**j
   assert np.isfinite(phi) and np.isclose(phi,.5*ru*ru,rtol=2e-12,atol=1e-25)
   trials[(it,j)]=r
  if kind=='accepted':
   trial=trials[(it,j)];phi=float(trial['trial_merit']);phi0=float(trial['pre_merit']);slope=float(trial['slope']);lam=float(trial['lambda'])
   assert np.isfinite(slope) and slope<0 and phi<=phi0+1e-4*lam*slope
   accepted+=1;accepted_updates+=1;backtracked+=j>0;max_halvings=max(max_halvings,j)
   origin=file.parent/f'iter_{it:04d}_origin.mat';end=file.parent/f'iter_{it:04d}_accepted.mat'
   if origin.exists() and end.exists():
    o=loadmat(origin);e=loadmat(end);u=o['u'].ravel().copy();u[active]+=lam*o['direction'].ravel()
    np.testing.assert_allclose(e['u'].ravel(),u,rtol=0,atol=2e-13)
    np.testing.assert_allclose(np.linalg.norm(e['R'].ravel()[active]),float(r['trial_Ru']),rtol=1e-10,atol=1e-12)
    vectors+=1
  # This is an entered-call ID only for normal events. Failure rows can refer
  # to distinct origin/attempt caches and are deliberately left unresolved.
  derived=base+ev if kind!='failure' else None
  mapping.append(dict(trace=str(file.relative_to(a.fem)),row=rownum,event=kind,raw_captured_base=base,local_attempt_ordinal=ev,derived_normal_current_call_id=derived,limitation='failure origin/attempt ID unresolved' if kind=='failure' else 'normal-event count reconstruction; no native replay'))
 report=file.parent/'report.mat';ok=None
 if report.exists():
  rep=loadmat(report,simplify_cells=True)['report'];ok=bool(rep['ok'])
  assert int(rep['updates'])==accepted
 summary.append(dict(step=int(file.parent.parent.name.split('_')[1]),stag=int(file.parent.name.split('_')[1]),captured_base=base,local_attempts=maxev,accepted_updates=accepted,report_ok=ok,last_event=rows[-1]['event']))
# Compare reconstructed normally completed mechanical ranges with independently
# exported outer native counters at every accepted physical state.
checks=[]
for path in sorted(a.fem.glob('state_*.mat')):
 s=loadmat(path);step=int(s['step'].item())
 if not step:continue
 count=int(s['equilibrium_evaluations'].item());calls=[x for x in summary if x['step']==step]
 assert calls and all(x['report_ok'] is True for x in calls)
 assert all(x['captured_base']+x['local_attempts']<=count for x in calls)
 checks.append(dict(step=step,outer_native_count=count,last_mechanical_call_end=calls[-1]['captured_base']+calls[-1]['local_attempts'],outside_mechanics_tail=count-calls[-1]['captured_base']-calls[-1]['local_attempts']))
result=dict(mechanics_calls=len(summary),accepted_newton_updates=accepted_updates,backtracked_accepted_updates=backtracked,max_accepted_halvings=max_halvings,available_vector_pairs_verified=vectors,outer_count_checks=checks,calls=summary,diagnostic_defect='raw global_evaluation_id is a captured call base, not a live ID; raw records unchanged',evidence_boundary='Normal-event scalar IDs reconstructed as base plus local attempts. Failure origin/attempt IDs remain unresolved. Counters bound calls; this does not replay native assembly or establish rejected-state equilibrium.')
(a.out/'trace_verification.json').write_text(json.dumps(result,indent=2,allow_nan=False))
with (a.out/'derived_normal_call_ids.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(mapping[0]));w.writeheader();w.writerows(mapping)
print(json.dumps({k:v for k,v in result.items() if k not in ['calls','outer_count_checks']},indent=2))
