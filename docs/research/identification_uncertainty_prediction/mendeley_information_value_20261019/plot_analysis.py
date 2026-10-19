"""Post-run descriptive analysis only: saved scored outputs; no fit or new data."""
from pathlib import Path
from collections import defaultdict
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).parent
analysis=json.loads((root/'analysis.json').read_text())
rows=list(csv.DictReader((root/'retrieved/outputs/per_case_scores.csv').open()))
arms=['scalar','compact','rich','rich_fixed','rich_set','persistence','secant']
labels=['Span scalar','Compact response','Rich field','Rich + fixed width','Rich + threshold set','Persistence','Secant']
colors=['#888888','#0072B2','#009E73','#56B4E9','#CC79A7','#333333','#D55E00']
groups=sorted({r['group'] for r in rows});cells=defaultdict(list)
for r in rows: cells[(r['arm'],r['group'],int(r['horizon_stages']))].append(float(r['balanced_nmae']))
m={k:np.mean(v) for k,v in cells.items()}
fig,ax=plt.subplots(2,2,figsize=(14,9),constrained_layout=True)
score=analysis['primary_equal_group_horizon_scores'];v=[score[a] for a in arms]
ax[0,0].barh(labels,v,color=colors,height=.65)
ax[0,0].invert_yaxis();ax[0,0].set_xlim(0,1.63)
for i,x in enumerate(v):ax[0,0].text(x+.015,i,f'{x:.4f}',va='center',fontsize=9)
ax[0,0].set_xlabel('Balanced normalized MAE (lower is better)');ax[0,0].set_title('(a) Primary: equal release-group / horizon weights',loc='left')
for base,col,marker in [('scalar','#888888','o'),('persistence','#333333','s')]:
 d=np.array([np.mean([m[('compact',g,h)]-m[(base,g,h)] for h in (10,40)]) for g in groups])
 ax[0,1].scatter(np.arange(1,20),d,c=col,marker=marker,label='Compact minus '+base,s=32)
ax[0,1].axhline(0,color='#777777',lw=.9);ax[0,1].set_xticks(range(1,20,2));ax[0,1].set_xlabel('Released group (alphabetical index, 1-19)');ax[0,1].set_ylabel('Paired score difference; below 0 favors compact');ax[0,1].legend(fontsize=9);ax[0,1].set_title('(b) Group variation; physical independence unverified',loc='left')
for a,label,c in zip(arms,labels,colors):
 ax[1,0].plot([10,40],[analysis['by_horizon_stages'][str(h)][a] for h in (10,40)],color=c,marker='o',lw=1.5,label=label)
ax[1,0].set_xticks([10,40]);ax[1,0].set_xlabel('Forecast horizon in release stages');ax[1,0].set_ylabel('Balanced normalized MAE');ax[1,0].set_title('(c) Rich wins at H10; compact wins at H40',loc='left');ax[1,0].legend(fontsize=8,ncol=2)
for a,label,c in zip(arms,labels,colors):
 ax[1,1].plot([0,1,2],[analysis['by_early_mid_late_release_position_not_lifetime'][a][str(p)] for p in (0,1,2)],color=c,marker='o',lw=1.5)
ax[1,1].set_xticks([0,1,2],['Early','Middle','Late']);ax[1,1].set_xlabel('Thirds of retained release origins (not physical lifetime)');ax[1,1].set_ylabel('Balanced normalized MAE');ax[1,1].set_title('(d) Persistence leads early / middle; gains occur late',loc='left')
for a in ax.flat:a.spines[['top','right']].set_visible(False);a.grid(axis='x' if a is ax[0,0] else 'y',alpha=.15);a.set_axisbelow(True)
fig.suptitle('Mendeley published-DIC exploration | 19 exposed groups | common current-field anchor',fontsize=13)
fig.savefig(root/'IU_R001_information_value.png',dpi=180);fig.savefig(root/'IU_R001_information_value.pdf');plt.close(fig)
summary={}
for arm in arms:
 summary[arm]={}
 for metric in ('full_nmae','local_nmae'):
  cells2=defaultdict(list)
  for r in rows:
   if r['arm']==arm:cells2[(r['group'],r['horizon_stages'])].append(float(r[metric]))
  summary[arm][metric]=float(np.mean([np.mean(x) for x in cells2.values()]))
(root/'full_local_breakdown.json').write_text(json.dumps(summary,indent=2))
(root/'group_index.json').write_text(json.dumps({i+1:g for i,g in enumerate(groups)},indent=2))
print(json.dumps(summary,indent=2))
