"""Plot only endpoint read-only diagnostics; no fitting or solve."""
from pathlib import Path
import sys,csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path(sys.argv[1]);d=r/'diagnosis_20261018_v2';rows=list(csv.DictReader((d/'parity_supports.csv').open()));z=np.load(d/'profiles.npz')
colors=['#777777','#0072B2','#D55E00'];names=['original','control','physical_uv'];labels=['Original','Control 200','Candidate 200']
fig,ax=plt.subplots(1,2,figsize=(10,3.8),layout='constrained')
for j,sup in enumerate(['train_mixture','display']):
 for i,(name,color) in enumerate(zip(names,colors)):
  row=next(q for q in rows if q['arm']==name and q['representation']=='direct_network' and q['support']==sup)
  val=float(row['uv_mse'])*1e7;ax[j].bar(i,val,color=color,width=.6);ax[j].text(i,val,f'{val:.2f}',ha='center',va='bottom',fontsize=9)
 ax[j].set(xticks=range(3),xticklabels=labels,ylabel='Normalized mirror MSE (x 1e-7)',ylim=(0,8 if j==0 else 43),title=['Exact training support','Displayed local window'][j])
 ax[j].spines[['top','right']].set_visible(False)
fig.suptitle('Direct network u/v mirror loss | same endpoints, different supports | frozen c1s2')
fig.savefig(d/'symmetry_support_diagnosis.png',dpi=180);plt.close(fig)
y=z['y'];fig,ax=plt.subplots(1,2,figsize=(10,3.8),layout='constrained')
for xp,a in zip(['-0.25','0'],ax):
 for key,label,color,ls in [('PIDL_analytic_initial_history','Initial PIDL history','#777777','--'),('FEM_recovered_initial','FEM after U=0 recovery','#009E73',':'),('FEM_s2','FEM c1s2','#0072B2','-'),('original_native_Q4','PIDL original c1s2','#D55E00','-')]:
  a.plot(y,z[key+'_cross_'+xp],label=label,color=color,ls=ls,lw=1.5)
 a.set(xlabel='y',ylabel='damage d',title='Transverse profile at x='+xp,xlim=(-.025,.025),ylim=(-.015,1.04));a.spines[['top','right']].set_visible(False)
ax[0].legend(fontsize=7,loc='upper right');fig.suptitle('Preset crack history does not fix the evolving damage band | native Q4 readout')
fig.savefig(d/'precrack_damage_diagnosis.png',dpi=180);plt.close(fig)
print('Two diagnostic figures saved')
