"""Reduce saved R015 line trials; no assembly, optimization, or new trial evaluation."""
import argparse,json,re,hashlib
from pathlib import Path
import numpy as np
from scipy.io import loadmat
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);a=p.parse_args();r=a.run;f=r/'retrieved/fem'
 s=loadmat(f/'failed_state_008.mat',simplify_cells=True);m=loadmat(f/'mesh.mat',simplify_cells=True)
 assert s['failure_stage']=='phase' and s['step']==8 and s['stag']==1 and not s['certificate_valid']
 origin=s['p_field'].ravel();old=s['p_field_old'].ravel();last=s['box_last_state'];trial=last['alpha'].ravel();g=last['Rpf'].ravel();d=trial-origin
 assert np.array_equal(origin,old) and np.array_equal(old,loadmat(f/'state_007.mat',simplify_cells=True)['p_field'].ravel())
 assert np.array_equal(last['previous'].ravel(),old) and np.array_equal(last['driver'],s['driver'])
 assert np.all((origin>=0)&(origin<=1)) and np.all((trial>=0)&(trial<=1))
 crack=np.asarray(m['crack'],int)-1;assert np.all(d[crack]==0) and np.all(trial[crack]==1)
 text=(f/'solver.log').read_text(errors='replace').rsplit('ACCEPTED step=7',1)[1]
 rows=[(int(j),float(e),float(sl)) for j,e,sl in re.findall(r'BOX_TRIAL iteration=1 trial=(\d+) E=([^\s]+) slope=([^\s]+)',text)]
 assert [z[0] for z in rows]==list(range(13));j,e,sl=rows[-1];assert np.isclose(e,last['energy'],rtol=0,atol=1e-16)
 # Origin equals old. Along the feasible positive ray, lower penalty is zero,
 # history branch sign is fixed, and every remaining term is quadratic.
 q=float(g@d-sl);assert q>0 and sl<0
 t=.5**j;S=sl/t;Q=q/t**2;E0=e-sl-.5*q
 reconstructed=[E0+S*.5**k+.5*Q*.5**(2*k) for k,_,_ in rows]
 max_error=max(abs(v-z[1]) for v,z in zip(reconstructed,rows));assert max_error<1e-9
 c1=1e-4;threshold=2*(1-c1)*(-S)/Q
 first_predicted=int(np.ceil(-np.log2(threshold)))
 out=dict(failure='bounded_energy_line_search_exhausted',accepted_prefix=7,max_accepted_U=.21,rejected_U=float(s['U']),step=8,stagger=1,certificate_valid=False,
  caller_alpha_equals_accepted_history=True,all_last_trial_values_in_box=True,raw_last_trial_gradient_norm=float(np.linalg.norm(g[np.setdiff1d(np.arange(len(g)),crack)])),
  max_native_energy_gradient_mismatch_last_trial=float(last['energy_gradient_mismatch']),last_trial_index=j,last_lambda=t,last_energy=e,last_reported_origin_gradient_dot_displacement=sl,
  directional_curvature_at_last_displacement=q,inferred_origin_energy=E0,full_target_slope=S,full_target_ray_curvature=Q,max_reconstruction_error_over13_logged_energies=max_error,
  energy_change_last=e-E0,Armijo_required_change_last=c1*sl,quadratic_ray_max_Armijo_lambda=threshold,first_predicted_dyadic_index=first_predicted,
  prediction_not_evaluated=True,no_new_energy_or_residual_assembly=True,no_new_solve=True,no_retry=True)
 dest=r/'analysis';(dest/'line_search_mechanism.json').write_text(json.dumps(out,indent=2)+'\n')
 np.savetxt(dest/'line_search_trials.csv',np.array([[k,.5**k,v,v-E0,c1*slope] for k,v,slope in rows]),delimiter=',',header='trial,lambda,energy,change_from_inferred_origin,Armijo_required_change',comments='')
 figdir=dest/'figures';figdir.mkdir(exist_ok=True)
 fig,ax=plt.subplots(figsize=(6.5,4),constrained_layout=True)
 steps=np.array([z[0] for z in rows]);energies=np.array([z[1]-E0 for z in rows]);req=np.array([c1*z[2] for z in rows]);ax.plot(steps,energies,'o-',color='#0072B2',label='Actual logged energy change');ax.plot(steps,req,'--',color='#D55E00',label='Required Armijo decrease');ax.axhline(0,color='#444444',lw=.8)
 ax.set_yscale('symlog',linthresh=1e-10);ax.set(xlabel='Actual backtrack index (lambda=2^-index)',ylabel='Energy change from origin',title='R015 U=0.24: all 13 evaluated trials rejected');ax.legend(frameon=False,fontsize=8);ax.spines[['right','top']].set_visible(False)
 for ext in ['png','pdf']:fig.savefig(figdir/f'bounded_energy_trials.{ext}',dpi=180)
 plt.close(fig)
 provenance={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in [f/'failed_state_008.mat',f/'state_007.mat',f/'mesh.mat',f/'solver.log',Path(__file__)]};(dest/'line_search_provenance.json').write_text(json.dumps(provenance,indent=2))
 (figdir/'bounded_energy_trials.md').write_text(f'''# How to read bounded energy trials

## Question and data provenance

Why did the common-box FEM stop? Saved inputs: {f}/failed_state_008.mat, state_007.mat, mesh.mat and solver.log. Exact hashes ../line_search_provenance.json; reductions ../line_search_mechanism.json and ../line_search_trials.csv. Script scripts/shear/analyze_common_box_stop.py. No solve, new energy evaluation, residual/tangent assembly, clipping or retry.

## Panels and axes

One panel: horizontal axis the13actuallyevaluatedindices0..12, lambda=2^-index. Blue dots actual logged energy minus inferred same-origin energy; orange dashed required Armijo change1e-4*g_origin dot displacement. Symmetriclogverticalaxis withlinear core1e-10 preserves both signs. Zero line marks unchangedenergy. Allbluepoints remain above theorange acceptance threshold.

## Numerical interpretation

At lastlambda={t:.12g}, energyincrease={e-E0:.12g}, requireddecrease={c1*sl:.12g}. Origin equals acceptedhistory, so feasible ray has fixed one-sided healing branch, no negative-alpha branch and quadratic native energy. Lastsavedgradientdotactualdisplacement and logged originslope give q={q:.12g}; reconstructed13energies differ fromlogged byatmost{max_error:.3g}. This supports bounded globalization exhaustion on this direction, not damageboundfailure. Ray analysis predicts Armijolambda≤{threshold:.12g}, firstdyadicindex{first_predicted}; those smallersteps WERE NOT evaluated and are not an acceptedstate or a claim of overall recovery.

## Limitations and claim boundary

No acceptedU=.24 or fullU=.4 reference, noPIDL/45°. Sevenacceptedstates require upstreamverification. Lasttrialrawgradient is not a coupledcertificate; failedcallerstate differs fromsavedlasttrial. The reconstruction relies on savedstateidentity/constantdriver and the implemented piecewisequadratic energy whose gradient agrees with nativeR at evaluatedpoints. This is not a unique-model/mesh diagnosis, proof a different solver completes24loads, or physicalvalidation. Do not simply enlarge backtrackcount; a prospective curvature-controlled globalization must be separately reviewed and authorized after this consumedfirstfailure.
''')
 print(json.dumps(out,indent=2))


if __name__=='__main__':main()
