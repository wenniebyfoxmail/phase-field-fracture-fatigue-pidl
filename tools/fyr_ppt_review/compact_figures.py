"""Replot retained fields for the shorter talk. No new results or model calls."""
from pathlib import Path
import csv,json,h5py
import numpy as np
from scipy.io import loadmat
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize,LogNorm,TwoSlopeNorm

R=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
W=R/'local_archive/fyr_ppt_15slide_revision_20261017';F=W/'figures'
OLD=R/'local_archive/experiments/S04-E011/runs/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z'
F.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':12,'axes.titlesize':13,'axes.labelsize':11,'xtick.labelsize':10,'ytick.labelsize':10,'savefig.dpi':200})
m=loadmat(OLD/'analysis/trajectory_error/raw/mesh_for_fem_trajectory.mat')
xy=m['points'];q4=m['q4cells'].astype(int)-1;t3=m['t3cells'].astype(int)-1
tri=mtri.Triangulation(xy[:,0],xy[:,1],t3)
def save(fig,name):
 fig.savefig(F/(name+'.png'));fig.savefig(F/(name+'.pdf'));plt.close(fig)

fig,ax=plt.subplots(2,3,figsize=(12,3.5),constrained_layout=True)
for i,arm in enumerate(['q4','t3']):
 with h5py.File(OLD/f'analysis/multicycle_cross_replay/fem_nodal/fem_{arm}_nodal_trajectory.mat') as f:
  c=f['cycles'][()].ravel().astype(int);a=f['d_node'][()][np.flatnonzero(c==83)[0]]
 p=np.load(OLD/f'analysis/multicycle_cross_replay/pidl_nodal/pidl_{arm}_nodal_trajectory.npz')
 b=p['d_node'][np.flatnonzero(p['cycles']==83)[0]]
 for j,(name,d) in enumerate([('FEM',a),('PIDL',b),('PIDL − FEM',b-a)]):
  opts=dict(cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-1,vcenter=0,vmax=1)) if j==2 else dict(cmap='viridis',vmin=0,vmax=1)
  pp=ax[i,j].tripcolor(tri,d,shading='gouraud',rasterized=True,**opts)
  ax[i,j].set(xlim=(.35,.5),ylim=(-.035,.035),xlabel='x',ylabel='y',title=arm.upper()+' '+name);ax[i,j].set_aspect('equal')
  if j==0:pa=pp
  if j==2:pd=pp
fig.colorbar(pa,ax=ax[:,:2],label='Damage d',shrink=.85);fig.colorbar(pd,ax=ax[:,2],label='Δd',shrink=.85)
save(fig,'damage_front_pair')

rows=list(csv.DictReader((R/'local_archive/report_ch4_fatigue_fields_20261015/analysis/same_state_GP_differences.csv').open()))
fig,ax=plt.subplots(1,2,figsize=(12,3.35),constrained_layout=True)
for arm,col in [('q4','#0072B2'),('t3','#CC79A7')]:
 for domain,ls in [('full','-'),('corridor_abs_y_le_0.03','--')]:
  for a,field,key in [(ax[0],'H','relative_L2'),(ax[1],'F','MAE')]:
   rr=[next(r for r in rows if r['topology']==arm and r['domain']==domain and r['field']==field and int(r['cycle'])==c) for c in [20,60,83]]
   a.plot([20,60,83],[float(r[key]) for r in rr],ls+'o',color=col,lw=1.8,label=arm.upper()+(' full' if domain=='full' else ' central strip'))
for a,title in zip(ax,['Fatigue-history relative L2 difference','Fatigue-factor mean absolute difference']):
 a.set(title=title,xlabel='Physical cycle',xticks=[20,60,83]);a.grid(alpha=.18);a.legend(fontsize=10)
save(fig,'history_evolution_gaps')

z=np.load(OLD/'analysis/c83_q4_mechanism/fields.npz');verts=xy[q4]
mask=(verts[...,0].max(1)>=-.1)&(verts[...,0].min(1)<=.5)&(verts[...,1].max(1)>=-.04)&(verts[...,1].min(1)<=.04)
fig,ax=plt.subplots(3,2,figsize=(8.7,4.8),constrained_layout=True)
for i,(field,label,floor) in enumerate([('raw','Raw driving energy',1e-7),('g','Damage factor g',None),('active','Active driver',1e-12)]):
 a=z[f'fem_{field}_elem'];b=z[f'pidl_{field}_elem']
 norm=Normalize(0,1) if field=='g' else LogNorm(floor,max(a.max(),b.max()))
 for j,(solver,d) in enumerate([('FEM',a),('PIDL',b)]):
  coll=PolyCollection(verts[mask],array=d[mask] if floor is None else np.maximum(d[mask],floor),norm=norm,cmap='viridis' if field=='g' else 'magma',edgecolors='none',antialiaseds=False,rasterized=True)
  ax[i,j].add_collection(coll);ax[i,j].set(xlim=(-.1,.5),ylim=(-.04,.04),xlabel='x',ylabel='y',title=solver+' '+label);ax[i,j].set_aspect('equal')
 fig.colorbar(coll,ax=ax[i,:],label='g' if field=='g' else 'Log scale',shrink=.85)
save(fig,'q4_energy_overlap')

(F/'README_analysis.md').write_text('''# Figures for the 15-page main talk

All panels replot existing S04-E011 paired Hard-5 outputs. No training, inference,
solver run, new metric threshold or experimental verdict occurs here.

Reading order: damage_front_pair compares both topologies at c83; history_evolution_gaps
shows the already-tabulated c20/c60/c83 fatigue differences; q4_energy_overlap
shows raw energy, damage factor and their native-GP product reduced independently
to cell means. The active driver is not obtained by multiplying the two cell means.

Damage uses the common fixed T3 display split of saved nodal values. Both topology
zooms show x=[.35,.50], y=[-.035,.035], shared d=[0,1] and Δd=[-1,1].
Numeric widths/extents remain those in the previous descriptive review. They
describe diffuse damage, not physical crack opening. History metrics use the
original native GP weights and post-update peaks. Dashed curves use |y_GP|<=.03.
Lines connect only three saved states. Energy uses the previously retained c83
diagnostic before PIDL history refresh, with the FEM raw energy from the final
pre-phase input and accepted damage. Raw/active displays use log floors 1e-7/1e-12,
with each row sharing limits across solvers. g has [0,1]. Floors affect display only.

The figures support local shape/history/overlap descriptions. They do not assign
causal contributions to initialisation, update timing, constraints or optimisation,
and do not establish pavement prediction. Numerical sources are the exact local
paths embedded in compact_figures.py. Original full maps and profiles remain in
the backup slides. Visual review checks orientation, common crops, labels/scales
and consistency with the unchanged earlier summaries.
''')
print('Replotted 3 figure sets from retained outputs.')
