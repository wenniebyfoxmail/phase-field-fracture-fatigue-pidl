"""Plot the exact verified R006 prefix and rejected attempt, no solving."""
from pathlib import Path
import json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

R=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E035/runs/S04-E035-R006')
V=json.loads((R/'verification/reference_verification.json').read_text())
with (R/'verification/verified_states.csv').open() as f:rows=[{k:float(v) for k,v in r.items() if k!='verified'} for r in csv.DictReader(f)]
before=json.loads((R.parent/'S04-E035-R004/analysis/metrics.json').read_text())
# Read the scalar from the original saved field to avoid ambiguous JSON aliases.
from scipy.io import loadmat
s=loadmat(R.parent/'S04-E035-R004/retrieved/fem/failed_state_001.mat');old_healing=float(s['max_healing'].item())
failed=V['failures'][0];assert failed['step']==7 and V['accepted_prefix']==6
out=R/'analysis';fig,axs=plt.subplots(1,2,figsize=(10,3.9),constrained_layout=True)
axs[0].plot([r['U'] for r in rows],[r['max_healing'] for r in rows],'o-',color='#0072B2',lw=1.5,label='R006: accepted prefix')
axs[0].plot(.03,old_healing,'X',color='#D55E00',ms=8,label='R004: rejected, soft initial crack')
axs[0].plot(failed['U'],failed['max_healing'],'^',mfc='none',color='#777777',ms=7,label='R006: rejected mechanical iterate')
axs[0].axhline(.005,color='#D55E00',ls='--',lw=1.2,label='Unchanged limit 0.005')
axs[0].set(xlabel='Prescribed shear displacement U',ylabel='Maximum nodal damage decrease',ylim=(-.0003,.0105),title='Initial-crack preservation improved')
axs[0].legend(frameon=False,fontsize=7.7);axs[0].grid(alpha=.15)
u=[r['U'] for r in rows]+[failed['U']];seconds=[r['step_seconds'] for r in rows]+[failed['step_seconds']]
axs[1].bar(np.arange(7),seconds,color=['#0072B2']*6+['#D55E00'],width=.65)
for i,t in enumerate(seconds):axs[1].text(i,t+7,f'{t:.1f}',ha='center',fontsize=8)
axs[1].set(xticks=np.arange(7),xticklabels=[f'{v:.2f}' for v in u],xlabel='Prescribed U',ylabel='Per-step elapsed seconds',ylim=(0,650),title='New bottleneck: displacement Newton')
axs[1].text(2.4,445,'U=0.21: rejected\n500-iteration limit\nNo PIDL training',fontsize=9,ha='center')
axs[1].grid(axis='y',alpha=.15)
for ext in ['png','pdf']:fig.savefig(out/f'figures/shear_validity_and_cost.{ext}',dpi=180)
plt.close(fig)
with (out/'tables/step_cost_and_validity.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['step','U','step_seconds','max_healing','accepted'])
 for r in rows:w.writerow([int(r['step']),r['U'],r['step_seconds'],r['max_healing'],True])
 w.writerow([failed['step'],failed['U'],failed['step_seconds'],failed['max_healing'],False])
caption=f'''# Shear reference validity and cost

Question: did the paired hard-initial-crack amendment remove the observed binding failure, and did it yield a complete reference?
Exact sources: R004/retrieved/fem/failed_state_001.mat (unaccepted); R006/verification/verified_states.csv and reference_verification.json (raw-array checks); R006/retrieved/fem/failed_state_007.mat. Table ../tables/step_cost_and_validity.csv. Units are normalized model units; time is wall seconds.
Left: original maximum healing {old_healing:.12g} at U=.03, rejected; revised first-state maximum {rows[0]['max_healing']:.12g}, accepted. Original .005 limit unchanged. All six accepted R006 states have maximum decrease≤{max(r['max_healing'] for r in rows):.12g}. Hollow grey marker is a rejected mechanical iterate, not an accepted reference despite damage checks within limits.
Right: exact per-state runner elapsed time. First six accepted states U=.03–.18; rejected seventh U=.21 used{failed['step_seconds']:.6f}s and hit displacement Newton limit500. The complete30-state reference was not obtained. No PIDL state or comparison exists.

See: imposing the known initial crack removes its excessive relaxation over the observed valid prefix; most runtime was spent on a later failed mechanics solve.
Therefore: preserve six qualified numerical states but stop this package; next design should target bounded nonlinear mechanics globalization with the same physical contract, not relax damage/residual checks.
Does not show: that initial-crack preservation guarantees the full trajectory, that R004/R006 have identical boundary contracts, or any physical/road validation. The changed essential initial-crack condition is precisely the intervention; the rejected R004 field is never projected or retrospectively accepted.
'''
(out/'figures/shear_validity_and_cost.md').write_text(caption)
with (out/'README_analysis.md').open('a') as f:f.write('\n## Reference verification and decision\n\nRead shear_validity_and_cost first, then reaction/energy curves, then displacement/damage snapshots.\n'+caption+'\n')
for stem in ['shear_response','shear_energies','shear_damage','shear_displacement']:
 with (out/f'figures/{stem}.md').open('a') as f:f.write(f'\nMeasured result: raw-array verification confirms6/30accepted states throughU=.18; U=.21 rejected at native displacement Newton limit500. AtU=.18 topRx={rows[-1]["Rx_top"]:.12g}, E_el={rows[-1]["E_el"]:.12g}, E_d={rows[-1]["E_d"]:.12g}. All shown accepted states have unchanged residual/bounds/healing checks satisfied and alpha1 on the251-node initial crack. No PIDL state exists; these fields/curves cannot show cross-solver agreement or full-path crack evolution.\n')
print(json.dumps({'first_state_healing':rows[0]['max_healing'],'accepted_prefix':len(rows),'failed_step_seconds':failed['step_seconds']},indent=2))
