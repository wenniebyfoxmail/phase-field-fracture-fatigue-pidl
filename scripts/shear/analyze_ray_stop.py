"""Read saved ray-stop vectors/logs; no new derivative assembly or solve."""
from pathlib import Path
import argparse,json,re,hashlib
import numpy as np
from scipy.io import loadmat
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);args=p.parse_args();r=args.run;f=r/'retrieved/fem';v=json.loads((r/'analysis/reference_verification.json').read_text());step=v['accepted_prefix']+1;s=loadmat(f/f'failed_state_{step:03d}.mat',simplify_cells=True);m=loadmat(f/'mesh.mat',simplify_cells=True);text=(f/'solver.log').read_text(errors='replace')
segment=text.rsplit(f'COUPLED step={step} ',1)[1].split('\n',1)[1]
loops=[(int(i),float(k)) for i,k in re.findall(r'BOX_PF iteration=(\d+) kkt=([^\s]+)',segment)]
rays=[dict(zip(['Qbase','slope0','slope1','lambda','bisections','lo','hi','analytic_slope0','mismatch'],map(float,z))) for z in re.findall(r'BOX_RAY Qbase=(\S+) slope0=(\S+) slope1=(\S+) initial_lambda=(\S+) bisections=(\S+) lo=(\S+) hi=(\S+) analytic_slope0=(\S+) slope_mismatch=(\S+)',segment)]
last_it=loops[-1][0];trials=[(int(bt),float(e),float(sl)) for it,bt,e,sl in re.findall(r'BOX_TRIAL iteration=(\d+) trial=(\d+) E=(\S+) slope=(\S+)',segment) if int(it)==last_it];assert len(trials)==13 and [z[0] for z in trials]==list(range(13));assert all(z[2]>=0 for z in trials)
b=s['box_last_state'];d=b['alpha'].ravel();g=b['Rpf'].ravel().copy();crack=np.asarray(m['crack'],int)-1;free=np.setdiff1d(np.arange(len(d)),crack);g[d==0]=np.minimum(g[d==0],0);g[d==1]=np.maximum(g[d==1],0)
out=dict(accepted_prefix=v['accepted_prefix'],last_valid_U=float(m['schedule'][v['accepted_prefix']-1]),failed_step=step,failed_U=float(s['U']),stagger=int(s['stag']),iteration=last_it,failure_stage=s['failure_stage'],reason=s['rejection_reason'],certificate_valid=bool(s['certificate_valid']),last_logged_pretrial_KKT=loops[-1][1],last_saved_trial_KKT=float(np.linalg.norm(g[free])),required_inner_KKT=1e-6,last_logged_ray=rays[-1],all13_actual_slopes_nonnegative=True,zero_actual_slope_count=sum(x[2]==0 for x in trials),all13_logged_energies_equal=len({x[1] for x in trials})==1,last_trial_energy=float(b['energy']),last_energy_gradient_mismatch=float(b['energy_gradient_mismatch']),all_last_trial_nodes_in_box=bool(np.all((d>=0)&(d<=1))),last_trial_max_healing=float(np.max(b['previous']-d)),caller_and_last_inner_trial_must_be_distinguished=True,inner_origin_and_full_direction_not_exported=True,no_unique_float_root_cause_claim=True,no_new_assembly_or_solve=True)
(r/'analysis/ray_stop.json').write_text(json.dumps(out,indent=2));np.savetxt(r/'analysis/last_ray_trials.csv',np.array(trials),delimiter=',',header='backtrack,energy,actual_origin_gradient_dot_step',comments='');np.savetxt(r/'analysis/last_phase_iterations.csv',np.array(loops),delimiter=',',header='iteration,pretrial_KKT',comments='')
fig,axs=plt.subplots(1,2,figsize=(10,3.6),constrained_layout=True);axs[0].semilogy(*np.array(loops).T,'o-',color='#0072B2',ms=3);axs[0].axhline(1e-6,ls='--',color='#D55E00',label='Unchanged inner limit');axs[0].set(xlabel='Inner phase iteration',ylabel='Original-unit box KKT norm',title=f'U={float(s["U"]):.2f}, stagger {int(s["stag"])}');axs[0].legend(frameon=False);axs[1].plot([x[0] for x in trials],[x[2] for x in trials],'o-',color='#0072B2',ms=3);axs[1].axhline(0,ls='--',color='#D55E00',label='Strict descent requires below zero');axs[1].set(xlabel='Backtrack index (0..12)',ylabel='Actual gradient dot represented step',title='All 13 final trials non-descent');axs[1].legend(frameon=False,fontsize=8)
for ax in axs:ax.spines[['top','right']].set_visible(False)
figdir=r/'analysis/figures';figdir.mkdir(exist_ok=True)
for ext in ['png','pdf']:fig.savefig(figdir/f'ray_stop.{ext}',dpi=180)
plt.close(fig);paths=[f/f'failed_state_{step:03d}.mat',f/'solver.log',f/'mesh.mat',r/'analysis/reference_verification.json',Path(__file__)];(r/'analysis/ray_stop_provenance.json').write_text(json.dumps({str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in paths},indent=2))
(figdir/'ray_stop.md').write_text(f'''# How to read the ray stop

## Question and data provenance

Why did R020 stop before a full24-state reference? Saved inputs {f}/failed_state_{step:03d}.mat, mesh.mat, solver.log and ../reference_verification.json. Exact SHA256 ../ray_stop_provenance.json; values ../ray_stop.json, ../last_ray_trials.csv and ../last_phase_iterations.csv. No new residual, Hessian, energy assembly or solve.

## How to read

Left: all logged original-unit KKT norms in the final failed phase call; orange unchanged1e-6 inner criterion. Right: all13 actual backtracked steps' current native gradient dotted with the represented nodal step; strict descent requires a negative value. Nonnegative values cannot be accepted even when floating energy is unchanged. Iteration and backtrack counters are numerical, not physical load states.

## Numerical takeaway

Accepted prefix{v['accepted_prefix']}/24 throughU={out['last_valid_U']:.2f}; failedU={float(s['U']):.2f},stagger{int(s['stag'])},iteration{last_it}. Last KKT={out['last_saved_trial_KKT']:.12g}; original target1e-6 remains unmet. Proposed ray slope={rays[-1]['slope0']:.12g},Qbase={rays[-1]['Qbase']:.12g},root bracket=[{rays[-1]['lo']:.12g},{rays[-1]['hi']:.12g}],initiallambda={rays[-1]['lambda']:.12g}. Final13 energies equal, all actual slopes>=0, {out['zero_actual_slope_count']} exactlyzero. Last native/analytic energy-gradient mismatch={out['last_energy_gradient_mismatch']:.12g}; all last nodes in[0,1].

## Limitations and next discriminator

The full original inner direction and pretrial vector were not exported; do not reconstruct them from the failed outer caller. A nearly cancelling negative model slope with a nonzero Qbase supports a weak projected-Newton descent/representability problem, but this alone does not uniquely identify floating arithmetic vs active-set conditioning. More bisections, more halvings or accepting zero steps do not supply the missing KKT certificate. A prospective direction safeguard may compare the feasible Newton target with an exact-diagonal projected-gradient direction using the same native tangent; this is not executed or a claim that it will reachU=.4. No PIDL/45-degree result exists.
''');print(json.dumps(out,indent=2))
