"""Read-only R007 stopped-step diagnostics, explicitly unaccepted iterates."""
from pathlib import Path
import argparse,re,csv,json
import numpy as np
from scipy.io import loadmat
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--fem',type=Path,required=True);a=p.parse_args()
s=loadmat(a.fem/'failed_state_013.mat');assert int(s['step'].item())==13
text=(a.fem.parent/'stdout.log').read_text(errors='replace').split('ACCEPTED step=12')[-1]
rows=[]
for match in re.finditer(r'STAG ITER Nr\.:\s*(\d+)\s+tot_en=([\deE.+-]+)\s+res_sum=([\deE.+-]+)',text):
 i=int(match[1]);context=a.fem/f'mechanics/step_013/stag_{i+1:04d}/phase_context.mat'
 alpha=loadmat(context)['alpha'].ravel()
 rows.append(dict(stagger=i,printed_total_energy=float(match[2]),printed_post_phase_residual_sum=float(match[3]),post_phase_alpha_max=float(alpha.max()),nodes_above_1_005=int((alpha>1.005).sum())))
assert [x['stagger'] for x in rows]==list(range(1,79))
np.testing.assert_array_equal(loadmat(a.fem/'mechanics/step_013/stag_0079/phase_context.mat')['alpha'],s['p_field'])
out=a.run/'analysis';table=out/'tables/stopped_step_stagger.csv'
with table.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
fig,axs=plt.subplots(1,2,figsize=(9.1,3.5),constrained_layout=True)
x=[z['stagger'] for z in rows]
axs[0].semilogy(x,[z['printed_post_phase_residual_sum'] for z in rows],color='#0072B2')
axs[0].axhline(1e-4,color='#D55E00',ls='--',label='Required final limit')
axs[0].set(xlabel='Completed outer stagger',ylabel='Printed post-phase residual sum',title='Coupled residual remains above limit');axs[0].legend(frameon=False,fontsize=8)
axs[1].plot(x,[z['post_phase_alpha_max'] for z in rows],color='#0072B2')
axs[1].axhline(1.005,color='#D55E00',ls='--',label='Original damage upper limit')
axs[1].set(xlabel='Completed outer stagger',ylabel='Maximum nodal alpha (zoomed scale)',title='Unaccepted damage overshoot');axs[1].legend(frameon=False,fontsize=8)
for ax in axs:ax.grid(alpha=.15)
fig.suptitle('U=0.29: unaccepted iterates before the 600 s stop',fontsize=11)
for ext in ['png','pdf']:fig.savefig(out/f'figures/stopped_step_stagger.{ext}',dpi=180)
plt.close(fig)
(out/'figures/stopped_step_stagger.md').write_text('''# Stopped U=.29 stagger diagnostics

Question: did extra inner-mechanics globalization finish the coupled step with acceptable damage?
Source: evidence/stdout.log after ACCEPTED step=12, and evidence/fem/mechanics/step_013/stag_0002 through stag_0079/phase_context.mat; failed_state_013.mat. Table ../tables/stopped_step_stagger.csv contains every completed outer iteration1–78. Printed residual/energy have log precision only, not fresh final acceptance diagnostics.
Timing alignment: context at start of stagger i+1 is alpha after native PF update i, matching printed post-phase residual i. Lastcontext exactly equals failed-state alpha. Iteration79 terminates on budget; it is not another completed PF update. Neither panel is an accepted physical-state curve.
Left: printed combined residual remains above original1e-4; it is not a replacement for final fresh Ru/PF checks (final PF diagnostic is missing). Right: maximum nodal alpha with a clearly zoomed vertical scale and unchanged upper bound1.005. Three nodes in last saved candidate exceed this bound; candidate is unaccepted, so this does not establish the eventual converged damage maximum.
Therefore: a larger iteration/time ceiling alone cannot yet be justified as a complete repair. Preserve coupled-iteration/damage behavior and investigate it in a separately designed next decision. Does not establish physical shear crack propagation, model validity, or PIDL agreement.
''')
print(json.dumps({'completed_staggers':len(rows),'last_printed_residual_sum':rows[-1]['printed_post_phase_residual_sum'],'first_stagger_with_overshoot':next((z['stagger'] for z in rows if z['nodes_above_1_005']),None),'last_nodes_above_damage_limit':rows[-1]['nodes_above_1_005']}))
