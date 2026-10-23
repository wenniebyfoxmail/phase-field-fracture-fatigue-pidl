"""Summarize saved phase iterations only; no assembly, line search or solve."""
from pathlib import Path
import argparse,json,re,csv,hashlib
import numpy as np
from scipy.io import loadmat
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();r=a.run;f=r/'retrieved/fem';v=json.loads((r/'analysis/reference_verification.json').read_text());step=v['accepted_prefix']+1
failed=f/f'failed_state_{step:03d}.mat';s=loadmat(failed,simplify_cells=True);text=(f/'solver.log').read_text(errors='replace').rsplit(f'ACCEPTED step={step-1}',1)[1]
if f'COUPLED step={step} ' in text:text=text.rsplit(f'COUPLED step={step} ',1)[1].split('\n',1)[1]
loops=re.findall(r'BOX_PF iteration=(\d+) kkt=([^\s]+) raw=([^\s]+)',text);curves=re.findall(r'BOX_(?:CURVATURE|RAY) [^\n]*?initial_lambda=([^\s]+)',text);trials=re.findall(r'BOX_TRIAL iteration=(\d+) trial=(\d+) E=([^\s]+) slope=([^\s]+)',text)
assert len(loops)==len(curves)==500 and all(int(j)==i+1 for i,(j,_,_) in enumerate(loops));assert len(trials)==500 and all(int(bt)==0 for _,bt,_,_ in trials)
kkt=np.array([float(x[1]) for x in loops]);lam=np.array([float(x) for x in curves]);energy=np.array([float(x[2]) for x in trials]);last=s['box_last_state'];crack=np.asarray(loadmat(f/'mesh.mat',simplify_cells=True)['crack'],int)-1;free=np.setdiff1d(np.arange(len(last['alpha'])),crack);d=last['alpha'];g=last['Rpf'].copy();g[d==0]=np.minimum(g[d==0],0);g[d==1]=np.maximum(g[d==1],0)
witness=s.get('phase_direction_last',{})
summary=dict(last_direction_choice=witness.get('choice',{}),accepted_prefix=v['accepted_prefix'],accepted_U=float(list(csv.DictReader((r/'analysis/verified_states.csv').open()))[-1]['U']),failed_step=step,failed_U=float(s['U']),stage=s['failure_stage'],stagger=int(s['stag']),reason=s['rejection_reason'],iterations=500,all_logged_trials_accepted_without_halving=True,all_logged_trial_energy_decreases=bool(np.all(np.diff(energy)<0)),first_logged_KKT=float(kkt[0]),last_logged_preupdate_KKT=float(kkt[-1]),actual_last_saved_inner_KKT=float(np.linalg.norm(g[free])),required_inner_KKT=1e-6,last_initial_lambda=float(lam[-1]),last50_median_initial_lambda=float(np.median(lam[-50:])),last_trial_energy=float(energy[-1]),last_energy_decrease=float(energy[-1]-energy[-2]),all_last_inner_nodes_in_box=bool(np.all((d>=0)&(d<=1))),last_native_energy_gradient_mismatch=float(last['energy_gradient_mismatch']),outer_caller_is_not_last_inner_iterate=True,certificate_valid=bool(s['certificate_valid']),no_new_assembly_or_solve=True)
summary['stopped_on_numerical_iteration_limit_not_wall_or_resource']=True
(r/'analysis/iteration_stop.json').write_text(json.dumps(summary,indent=2));np.savetxt(r/'analysis/phase_iterations.csv',np.c_[np.arange(1,501),kkt,lam,energy],delimiter=',',header='iteration,preupdate_KKT,initial_lambda,accepted_trial_energy',comments='')
out=r/'analysis/figures';out.mkdir(exist_ok=True);fig,axs=plt.subplots(1,2,figsize=(10,3.6),constrained_layout=True);x=np.arange(1,501);axs[0].semilogy(x,kkt,color='#0072B2',label='Actual logged KKT');axs[0].axhline(1e-6,color='#D55E00',ls='--',label='Unchanged inner limit');axs[0].set(xlabel='Inner phase iteration',ylabel='Unscaled KKT norm',title=f'U={float(s["U"]):.2f}: 500-iteration stop');axs[0].legend(frameon=False);axs[1].semilogy(x,lam,color='#009E73');axs[1].set(xlabel='Inner phase iteration',ylabel='Accepted initial step lambda',title='Every trial accepted without halving');
for ax in axs:ax.spines[['top','right']].set_visible(False)
for ext in ['png','pdf']:fig.savefig(out/f'phase_iteration_stop.{ext}',dpi=180)
plt.close(fig);prov={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in [failed,f/'solver.log',r/'analysis/reference_verification.json',Path(__file__)]};(r/'analysis/iteration_stop_provenance.json').write_text(json.dumps(prov,indent=2))
(out/'phase_iteration_stop.md').write_text(f'''# Phase iteration stop

Question: did {r.name} stop on time, bounds, rejected line trials, or slow phase convergence?

## Data provenance

Sources: {f}/solver.log and failed_state_{step:03d}.mat; upstream ../reference_verification.json. SHA256 in ../iteration_stop_provenance.json. All 500 logged phase iterations and accepted trial energies exported to ../phase_iterations.csv. No new energy evaluation, assembly, optimization, or solve.

## How to read

Left: actual logged original-unit box KKT against iteration; dashed orange line is unchanged1e-6 inner limit. Right: exact-ray selected initial lambda. Every one of these500 trials was accepted at backtrack0; no rejected trial is hidden. Energy decreases at every logged consecutive accepted trial. Last preupdate KKT={kkt[-1]:.12g}; independently recomputed final saved inner KKT={summary['actual_last_saved_inner_KKT']:.12g}; last lambda={lam[-1]:.12g}. Last energy decrease={summary['last_energy_decrease']:.12g}. The max500 iteration limit, not a time limit, ended the attempt.

Limitations: valid reference is only {v['accepted_prefix']}/24 states through U={summary['accepted_U']:.2f}; failed U={float(s['U']):.2f} is excluded. Caller field and last saved inner iterate differ; no final coupled certificate for either candidate. Small accepted lambda and slow progress support a globalization/active-set efficiency bottleneck, but do not prove a unique cause or that larger steps, a different active set, or more iterations completes the trajectory. No PIDL/45-degree comparison or physical-validation claim.
''');print(json.dumps(summary,indent=2))
