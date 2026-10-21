"""Show an independently verified shear prefix/reference; never solve or refit."""
from pathlib import Path
import argparse,csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from scipy.io import loadmat

p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--fem',type=Path,required=True);a=p.parse_args()
r=a.run;v=json.loads((r/'verification/reference_verification.json').read_text())
with (r/'verification/verified_states.csv').open() as f:
 rows=[{k:float(value) for k,value in x.items() if k!='verified'} for x in csv.DictReader(f)]
assert rows
out=r/'analysis/figures';out.mkdir(parents=True,exist_ok=True)
u=np.array([x['U'] for x in rows]);n=len(rows);complete=v['complete_valid_reference']
status=f'{n}/{v["prescribed_states"]} accepted; '+('full reference' if complete else 'incomplete reference')
fig,axs=plt.subplots(1,3,figsize=(11.7,3.6),constrained_layout=True)
axs[0].plot(u,[x['Rx_top'] for x in rows],'o-',ms=3,color='#0072B2')
axs[0].set(xlabel='Prescribed shear displacement U',ylabel='Top horizontal reaction',title='Native assembled reaction')
axs[1].semilogy(u,[x['res_u']+x['res_pf'] for x in rows],'o-',ms=3,color='#0072B2')
axs[1].axhline(1e-4,color='#D55E00',ls='--',label='Unchanged limit 1e-4')
axs[1].set(xlabel='Prescribed U',ylabel='Final ||Ru|| + ||Rpf||',title='Fresh final-state residuals');axs[1].legend(frameon=False,fontsize=8)
axs[2].bar(np.arange(1,n+1),[x['step_seconds'] for x in rows],color='#0072B2',label='Accepted step')
for failure in v['failures']:
 if failure['step_seconds'] is not None:
  axs[2].bar(failure['step'],failure['step_seconds'],color='#D55E00',label='Rejected step')
if not complete:
 reason=v['exit']['reason']
 axs[2].text(.98,.97,f'Stopped before accepting step {n+1}\nSupervisor: {reason}',transform=axs[2].transAxes,ha='right',va='top',fontsize=8,bbox=dict(facecolor='white',alpha=.85,edgecolor='none'))
 axs[2].set_xlim(.2,n+1.8)
axs[2].set(xlabel='Load step',ylabel='Elapsed seconds',title='Step cost (same 600 s cap)')
axs[2].axhline(600,color='#777777',ls=':',lw=1);axs[2].legend(frameon=False,fontsize=8)
for ax in axs:ax.grid(alpha=.15)
fig.suptitle(f'{r.name}: {status}',fontsize=11)
for ext in ['png','pdf']:fig.savefig(out/f'shear_reference_progress.{ext}',dpi=180)
plt.close(fig)

m=loadmat(a.fem/'mesh.mat');s=loadmat(a.fem/f'state_{n:03d}.mat')
x=m['nodes'][:,:2];q=m['quads'].astype(int)-1;nn=len(x);uv=s['displ'].ravel()
fields=[uv[:nn][q].mean(1),uv[nn:][q].mean(1),s['p_field'].ravel()[q].mean(1)]
fig,axs=plt.subplots(1,3,figsize=(10.8,3.5),constrained_layout=True)
for ax,values,label in zip(axs,fields,['u_x','u_y','Damage alpha']):
 damage=label=='Damage alpha';bound=max(float(abs(values).max()),1e-8)
 art=PolyCollection(x[q],array=values,cmap='viridis' if damage else 'RdBu_r',edgecolors='none',linewidths=0,antialiased=False,rasterized=True)
 art.set_clim(*((0,1) if damage else (-bound,bound)));ax.add_collection(art)
 ax.set(xlim=(-.5,.5),ylim=(-.5,.5),aspect='equal',xlabel='x',ylabel='y',title=label)
 fig.colorbar(art,ax=ax,shrink=.8,extend='both')
fig.suptitle(f'Highest accepted shear state: U={u[-1]:.2f}; {status}',fontsize=11)
for ext in ['png','pdf']:fig.savefig(out/f'last_valid_shear_fields.{ext}',dpi=180)
plt.close(fig)
common=f'''Sources: {r.name}/verification/reference_verification.json and verified_states.csv; {a.fem}/mesh.mat and state_001 through state_{n:03d}.mat. No PIDL output exists in this plot. All quantities use normalized model units; time is wall seconds.
Selection: every verified loaded state for curves/costs; highest accepted U={u[-1]:.17g} for fields, irrespective of appearance. Status: {status}. Failed states are excluded from response/field panels and separately marked in cost only when a failed-state file supplies elapsed time. A supervisor-only kill may lack such a vector/time; absence of an orange bar is not success.
Evidence: final residual sum maximum {max(z['res_u']+z['res_pf'] for z in rows):.12g}; maximum nodal damage decrease {max(z['max_healing'] for z in rows):.12g}. Original checks and precrack retained. Force-vector verification does not rerun native assembly. No physical validation or FEM/PIDL agreement follows.
'''
(out/'shear_reference_progress.md').write_text('# Shear reference progress\n\nQuestion: how far did the bounded solver produce valid states, and at what cost?\n'+common+'Panels: top assembled reaction, freshly assembled final residual sum, per-step cost with original600s cap. Curves stop at the last accepted state; no interpolation through failures.\n')
(out/'last_valid_shear_fields.md').write_text('# Highest accepted shear fields\n\nQuestion: what are the actual fields at the largest accepted prescribed displacement?\n'+common+'Panels are Q4 nodal means of ux,uy,alpha on the undeformed mesh; symmetric signed displacement scales per component and fixed damage color limits[0,1], with colorbar extensions for out-of-range means. Original arrays are not clipped or smoothed. The initial crack is present; this figure alone does not isolate new crack growth.\n')
print(json.dumps({'accepted_states':n,'last_U':float(u[-1]),'complete_valid_reference':complete}))
