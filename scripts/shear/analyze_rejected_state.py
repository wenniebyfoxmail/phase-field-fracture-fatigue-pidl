"""Diagnose the preserved, unaccepted R004 state without rerunning FEM."""
from pathlib import Path
import json,csv
import numpy as np
from scipy.io import loadmat
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

R=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E035/runs/S04-E035-R004')
OUT=R/'analysis';(OUT/'figures').mkdir(parents=True,exist_ok=True);(OUT/'tables').mkdir(exist_ok=True)
m=loadmat(R/'retrieved/fem/mesh.mat');s=loadmat(R/'retrieved/fem/failed_state_001.mat')
nodes=m['nodes'][:,:2];quad=m['quads'].astype(int)-1
a=s['p_field'].ravel();h=s['p_field_old'].ravel();delta=h-a
assert float(s['U'].item())==.03 and int(s['step'].item())==1
assert ''.join(s['timing'].ravel().astype(str))=='unaccepted_post_solve_pre_history_update'
for key,value in [('alpha_min',a.min()),('alpha_max',a.max()),('max_healing',delta.max())]:
    assert np.isclose(float(s[key].item()),value,rtol=0,atol=1e-14)
line=(abs(nodes[:,1])<1e-12)&(nodes[:,0]<=1e-12)&(h>=1-1e-12)
bad=delta>.005;idx=int(delta.argmax())
metrics=json.loads((R/'initial_diagnostic_metrics.json').read_text())
metrics.update(crackline_nodes=int(line.sum()),bad_off_crackline=int((bad&~line).sum()),max_healing_off_crackline=float(delta[~line].max()),healing_limit_ratio=float(delta.max()/.005),all_violations_on_initial_fully_damaged_line=bool(np.all(line[bad])),alpha_lower_violation=bool(a.min()<-.005),alpha_upper_violation=bool(a.max()>1.005))
rows=[]
for i in np.flatnonzero(bad):rows.append(dict(node0=int(i),x=nodes[i,0],y=nodes[i,1],alpha_previous=h[i],alpha_candidate=a[i],healing=delta[i]))
with (OUT/'tables/violating_nodes.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
order=np.flatnonzero(line);order=order[np.argsort(nodes[order,0])]
with (OUT/'tables/crackline_profile.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['node0','x','alpha_previous','alpha_candidate','healing','limit'])
    for i in order:w.writerow([int(i),nodes[i,0],h[i],a[i],delta[i],.005])
# Figure source is exactly the exported rejected vector; no clipping or repair.
fig,axs=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
field=delta[quad].mean(1);vmax=float(abs(delta).max())
artist=PolyCollection(nodes[quad],array=field,cmap='RdBu_r',edgecolors='none',rasterized=True)
artist.set_clim(-vmax,vmax);axs[0].add_collection(artist)
axs[0].scatter(nodes[bad,0],nodes[bad,1],s=4,c='#E69F00',label='Decrease > 0.005',zorder=4)
axs[0].plot(nodes[idx,0],nodes[idx,1],'kx',ms=7,label='Largest decrease')
axs[0].set(xlim=(-.5,.5),ylim=(-.5,.5),xlabel='x',ylabel='y',title='Spatial damage decrease',aspect='equal')
axs[0].legend(frameon=False,fontsize=8,loc='upper right')
fig.colorbar(artist,ax=axs[0],label=r'$\alpha_{previous}-\alpha_{candidate}$',shrink=.85)
axs[1].plot(nodes[order,0],delta[order],lw=1.5,color='#0072B2',label='Initial crack line, y=0')
axs[1].axhline(.005,color='#D55E00',ls='--',lw=1.3,label='Original limit 0.005')
axs[1].fill_between(nodes[order,0],.005,delta[order],where=delta[order]>.005,color='#D55E00',alpha=.15)
axs[1].set(xlim=(-.5,0),ylim=(0,.0105),xlabel='x on prescribed initial crack',ylabel='Damage decrease',title='250 nodes exceed the original limit')
axs[1].grid(alpha=.15);axs[1].legend(frameon=False,fontsize=8)
fig.suptitle('First shear state U=0.03: unaccepted candidate',fontsize=12)
for ext in ['png','pdf']:fig.savefig(OUT/f'figures/first_state_healing.{ext}',dpi=180)
plt.close(fig)
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2))
text=f'''# First-state damage decrease diagnostic

Source: S04-E035-R004, failed_state_001.mat, U=.03, unaccepted post-solve/pre-history-update state.
Initial FEM mesh/profile are array-identical to R001. Native candidate
alpha_min={a.min():.12g}, alpha_max={a.max():.12g}; both satisfy the original
[-.005,1.005] checks. Maximum damage decrease={delta.max():.12g} > .005;
all {int(bad.sum())} violating nodes lie on the initial fully damaged y=0 line.
Worst coordinate={nodes[idx].tolist()}, previous alpha={h[idx]:.12g},
candidate alpha={a[idx]:.12g}; no violating node is off that line.
Off-line maximum decrease={delta[~line].max():.12g}.
Native displacement residual={float(s['res_u'].item()):.12g};
phase-field residual={float(s['res_pf'].item()):.12g}.

Read spatial map first, then the crack-line profile. Left colors are cell means
of raw nodal damage decrease, common symmetric range +/-{vmax:.12g}; orange
points are the exact violating nodes. Right uses every prescribed initial
crack-line node ordered by x; dashed line is the unchanged .005 limit.
No node/state was clipped, projected or removed to improve validity.

See: the decrease exceeding tolerance is confined to the already broken line,
including its interior, rather than a new crack path.
Therefore: the binding discrepancy is preservation of the imposed initial
fracture under finite penalty; numerical residual convergence alone did not
preserve it. The data do not show a qualified shear trajectory or PIDL agreement.

Mechanism repair proposal: in a fresh prospectively amended pair, hold the
prescribed initial crack alpha=1 as an essential condition in both FEM and
PIDL. Existing native non_hom_pf BC supports this. Preserve the off-line soft
profile, material, loading, residual and decrease thresholds. This changes the
initial-crack constraint prospectively; it does not rescue either rejected state.
Whether off-line bounds and whole-path behavior then remain valid is untested.
Do not project this candidate or launch another calculation under R004.
'''
(OUT/'README_analysis.md').write_text(text)
(OUT/'figures/first_state_healing.md').write_text(text+'\nFigure: first_state_healing.png/pdf. Tables: ../tables/*.csv.\n')
print(json.dumps({k:metrics[k] for k in ['crackline_nodes','bad_off_crackline','max_healing_off_crackline','healing_limit_ratio','all_violations_on_initial_fully_damaged_line']},indent=2))
