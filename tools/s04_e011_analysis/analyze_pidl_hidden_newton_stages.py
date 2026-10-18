"""Secondary descriptive replay of ALL saved stages; primary verdict unchanged."""
from pathlib import Path
import sys,json,csv
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s04_e011_analysis'))
import analyze_pidl_hidden_newton as a
B=a.BASE
run=B/'runs/pf_s04e011_hiddennewton_ccc011f_20261018T121350Z_production';out=run/'analysis_hidden_newton'
item=next(x for x in a.read_json(a.INPUTS)['cases'] if x['cycle']==20)
with np.load(item['path']) as z:inp={k:z[k] for k in z.files}
op,_=a.independent_operator(ROOT);geo=op.q4_geometry(inp['nodes'],inp['cells']);N,_,w,_=geo;mass=np.zeros(len(inp['nodes']))
for j in range(4):np.add.at(mass,inp['cells'][:,j],np.sum(w*N[:,j],axis=1))
fem={k:inp[k+'_fem'] for k in ['u','v','d']};ref=a.q4_fields(fem,inp,op,geo);rows=[]
for label in ['initial']+[f'{kind}_{i}' for i in range(1,5) for kind in ['hidden','head']]:
 p=run/'retrieved/archive/output/c20_s4/checkpoints'/label
 with np.load(p/'fields.npz') as z:f={k:z[k] for k in ['u','v','d']}
 assert np.array_equal(f['d'],fem['d']);a.boundary_check(f,fem,inp)
 metrics,_=a.score(f,fem,inp,op,geo,ref,mass);raw=a.read_json(p/'result.json');a.verify_four(raw,metrics)
 rows.append(dict(stage=label,**metrics))
with (out/'stage_metrics.csv').open('w') as f:
 c=csv.DictWriter(f,fieldnames=list(rows[0]));c.writeheader();c.writerows(rows)
(out/'stage_metrics.json').write_text(json.dumps(dict(kind='posthoc secondary descriptive check of all nine saved accepted checkpoints; not a new criterion',rows=rows),indent=2)+'\n')
print(json.dumps([{k:r[k] for k in ['stage','E_el','free_u_l2','uv_mass_rel_L2','active_vs_FEM_relative_L2']} for r in rows],indent=2))

# Descriptive only: every accepted exported checkpoint, no selected subsets.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axs=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
x=np.arange(len(rows));names=['initial']+[f'{kind}{i}' for i in range(1,5) for kind in ['hidden','Newton']]
main=a.read_json(out/'summary.json')['state']['metrics']
for ax,key,title in zip(axs,['E_el','active_vs_FEM_relative_L2'],['Elastic energy','Active weighted relative L2 / FEM']):
 values=[r[key] for r in rows];ax.plot(x,values,color='#0072B2',zorder=1)
 for j,value in enumerate(values):
  ax.scatter(j,value,color='#D55E00' if j>0 and j%2==0 else '#0072B2',marker='s' if j>0 and j%2==0 else 'o',zorder=2)
 ax.axhline(main['fixed_feature_Newton'][key],ls=':',color='#555555',label='fixed-feature Newton start')
 ax.axhline(main['PBD_full_network'][key],ls='--',color='#009E73',label='earlier full-network L-BFGS')
 ax.set_xticks(x,names,rotation=35,ha='right',fontsize=8);ax.set_title(title);ax.grid(alpha=.2);ax.legend(fontsize=7)
fig.suptitle('PIDL c20s4 | all 9 saved accepted stages | fixed FEM damage and boundary',fontsize=11)
path=out/'c20_hidden_newton_stage_tradeoff.png';fig.savefig(path,dpi=160);plt.close(fig)
path.with_suffix('.md').write_text('# c20 hidden/Newton stage tradeoff\n\n## Data provenance\n\n'+str(run)+'; sourceccc011f0. All nine saved accepted checkpoints independently rescored by native Q4/2x2 GP NumPy operator; stage_metrics.csv/json. Baselines from summary.json.\n\n## How to read\n\nBoth axes are linear. Blue circles are initial/hidden-block endpoints; orange squares are Newton head corrections. Every exported accepted checkpoint is shown in execution order, no cherry-picking or trajectory stitching. Dotted grey is fixed-feature Newton start; dashed green is earlier full-network L-BFGS, which has a different starting point/work count.\n\n## Limitation\n\nPosthoc descriptive check, not an added primary criterion or causal percentage allocation. c20 peak only, same exact FEM damage/UV boundary, no history commit/rollout. Lower energy is not active-field agreement, whole-network convergence or physical truth. Full exact stage values are authoritative.\n')
with (out/'README_analysis.md').open('a') as f:f.write('\nSecondary posthoc supplement: c20_hidden_newton_stage_tradeoff.png shows every one of the nine saved accepted checkpoints; stage_metrics.csv/json are independent field replays. This does not change the primary energy-improvement observable, does not allocate causal shares, and is not a fatigue evolution curve.\n')
