"""Descriptive replot of existing outputs, never a solver or model evaluation."""
from pathlib import Path
import json,csv,h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.colors import TwoSlopeNorm

ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
OUT=ROOT/'local_archive/fyr_ppt_evidence_revision_20261017'
FIG=OUT/'figures';ANA=OUT/'analysis'
for p in (FIG,ANA):p.mkdir(parents=True,exist_ok=True)
# Reuse the already checked PACK decoder and native GP geometry, without its
# plotting/output block. The source path and timing assertions remain intact.
parser=ROOT/'.codex/worktrees/fyr-ch4-local-revision-20261015/tools/fyr_ch4_review/plot_fatigue_fields.py'
env={};exec(compile(parser.read_text().split('fields={};checks={}')[0],str(parser),'exec'),env)
points,cells,geo=env['points'],env['cells'],env['geo']
payload,pidl=env['payload'],env['pidl']
OLD=env['OLD'];CYCLES=[20,60,83]
tri=mtri.Triangulation(points[:,0],points[:,1],cells['t3'])
mass=np.zeros(len(points))
for k in range(4):np.add.at(mass,cells['q4'][:,k],geo['q4']['area']/4)
plt.rcParams.update({'font.size':11,'axes.titlesize':12,'axes.labelsize':11,'xtick.labelsize':10,'ytick.labelsize':10,'savefig.dpi':200})
def save(fig,name):
 fig.savefig(FIG/(name+'.png'));fig.savefig(FIG/(name+'.pdf'));plt.close(fig)
def write(name,rows):
 with (ANA/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def interp(d,x,y):return np.asarray(mtri.LinearTriInterpolator(tri,d)(x,y))
def l2(a,b,w):return float(np.sqrt(np.sum(w*(a-b)**2)/np.sum(w*a*a)))
nodal={};damage_rows=[];sections=[]
yy=np.linspace(-.04,.04,2001);xx=np.linspace(0,.5,5001)
for arm in ['q4','t3']:
 with h5py.File(OLD/f'analysis/multicycle_cross_replay/fem_nodal/fem_{arm}_nodal_trajectory.mat') as f:
  fc=f['cycles'][()].ravel().astype(int);fd=f['d_node'][()]
 pp=np.load(OLD/f'analysis/multicycle_cross_replay/pidl_nodal/pidl_{arm}_nodal_trajectory.npz')
 for c in [1,20,60,83]:
  a=fd[np.flatnonzero(fc==c)[0]];b=pp['d_node'][np.flatnonzero(pp['cycles']==c)[0]]
  nodal[(arm,c)]=(a,b)
  for solver,d in [('FEM',a),('PIDL',b)]:
   outside=np.abs(points[:,1])>.03
   center=interp(d,xx,np.zeros_like(xx));front=float(xx[np.flatnonzero(center>=.5)[-1]])
   damage_rows.append(dict(topology=arm,cycle=c,solver=solver,mean=float(np.sum(mass*d)),relative_L2_to_FEM=l2(a,d,mass),centerline_forward_extent_d_ge_0_5=front,background_mean_abs_y_gt_0_03=float(np.sum(mass[outside]*d[outside])/mass[outside].sum()),background_area_d_gt_0_1=float(np.sum(mass[outside]*(d[outside]>.1))),damage_min=float(d.min()),damage_max=float(d.max())))
   if c==83:
    for x in [.25,.4,.46]:
     z=interp(d,np.full_like(yy,x),yy);above=z>=.5
     # Total thresholded transverse measure within a fixed section, not an
     # opening displacement or physical crack-width measurement.
     width=float(np.trapezoid(above.astype(float),yy));den=np.trapezoid(np.maximum(z,0),yy);cent=float(np.trapezoid(yy*np.maximum(z,0),yy)/den) if den>0 else None
     sections.append(dict(topology=arm,solver=solver,cycle=c,x=x,section_ymin=-.04,section_ymax=.04,threshold=.5,thresholded_damage_band_width=width,positive_damage_centroid_y=cent))
 a,b=nodal[(arm,83)]
 fig,ax=plt.subplots(2,3,figsize=(12,4.9),constrained_layout=True)
 for j,(label,d) in enumerate([('FEM',a),('PIDL',b),('PIDL minus FEM',b-a)]):
  opts=dict(cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-1,vcenter=0,vmax=1)) if j==2 else dict(cmap='viridis',vmin=0,vmax=1)
  p=ax[0,j].tripcolor(tri,d,shading='gouraud',rasterized=True,**opts)
  ax[0,j].set(xlim=(.35,.5),ylim=(-.035,.035),xlabel='x',ylabel='y',title=arm.upper()+' '+label)
  ax[0,j].set_aspect('equal');fig.colorbar(p,ax=ax[0,j],shrink=.8,label='Δd' if j==2 else 'd')
 for j,x in enumerate([.25,.4,.46]):
  for label,d,color,style in [('FEM',a,'#0072B2','-'),('PIDL',b,'#D55E00','--')]:ax[1,j].plot(yy,interp(d,np.full_like(yy,x),yy),style,color=color,label=label,lw=1.6)
  ax[1,j].axhline(.5,color='.5',lw=.7);ax[1,j].set(xlabel='y',ylabel='Damage d',title=f'Transverse section x = {x:.2f}',ylim=(-.03,1.13));ax[1,j].legend(fontsize=9);ax[1,j].grid(alpha=.15)
 save(fig,arm+'_damage_zoom_profiles')
write('damage_descriptive_metrics.csv',damage_rows);write('damage_sections_c83.csv',sections)

history_rows=[]
fig,ax=plt.subplots(2,2,figsize=(12,4.7),constrained_layout=True)
for i,arm in enumerate(['q4','t3']):
 xy=geo[arm]['gp_xy'];w=geo[arm]['weights']
 edges=np.linspace(-.5,.5,101);centers=(edges[:-1]+edges[1:])/2
 for solver,src,color,style in [('FEM',payload,'#0072B2','-'),('PIDL',pidl,'#D55E00','--')]:
  for c in CYCLES:
   H=src[f'{arm}_c{c}_s4_H'];peak=np.unravel_index(np.argmax(H),H.shape)
   history_rows.append(dict(topology=arm,solver=solver,cycle=c,history_max=float(H[peak]),peak_x=float(xy[peak][0]),peak_y=float(xy[peak][1]),mean=float(np.sum(H*w)),native_gauss_points=H.size))
  for j,name in enumerate(['H','F']):
   v=src[f'{arm}_c83_s4_{name}'];mask=np.abs(xy[...,1])<=.01
   sw=np.histogram(xy[...,0][mask],edges,weights=w[mask])[0]
   sv=np.histogram(xy[...,0][mask],edges,weights=(w*v)[mask])[0]
   line=np.divide(sv,sw,out=np.full(100,np.nan),where=sw>0)
   ax[i,j].plot(centers,line,style,color=color,lw=1.6,label=solver)
   ax[i,j].set(title=arm.upper()+(' fatigue history' if j==0 else ' fatigue factor'),xlabel='x',ylabel='Raw history ᾱ' if j==0 else 'f');ax[i,j].grid(alpha=.15);ax[i,j].legend(fontsize=10)
save(fig,'c83_history_factor_profiles');write('history_peaks_and_means.csv',history_rows)

active=[]
for arm in ['q4','t3']:
 with h5py.File(OLD/f'analysis/trajectory_error/raw/fem_{arm}_trajectory_compact.mat') as f:
  cs=f['cycles'][()].ravel().astype(int);a=f['active_gp'][()].transpose(2,1,0);w=f['weights'][()].T
 p=np.load(OLD/f'analysis/trajectory_error/raw/pidl_{arm}_trajectory_compact.npz')
 for c in sorted(set(cs)&set(p['cycles'])):
  v=a[np.flatnonzero(cs==c)[0]];u=p['active_gp'][np.flatnonzero(p['cycles']==c)[0]]
  active.append(dict(topology=arm,cycle=int(c),active_relative_L2=l2(v,u,w)))
write('existing_active_trajectory.csv',active)
receipt={'scope':'Existing S04-E011 paired Hard-5 outputs; descriptive diagnostics only','new_experiment':False,'network_inference':False,'damage_display':'Nodal d on fixed T3 display split; absolute [0,1], signed [-1,1]; metrics use raw values','damage_sections':'Linear interpolation on common display triangulation, y=[-.04,.04], fixed x=.25,.40,.46; d>=.5 thresholded band width is not crack opening','damage_background':'Common Q4 row-sum nodal weights, |y|>.03, area threshold d>.1','history_profiles':'Native GP weighted averages in x bins of width .01 and |y_GP|<=.01, post-update c83 peak; no history normalization or clipping','history_maps':'Reuse existing shared LogNorm plots with display floor 1e-4; numerical metrics unchanged','onset':'Different initial damage already at c0; sampled active states start c1. These samples cannot identify the first within-step onset.','sources':[str(parser),str(OLD/'analysis/multicycle_cross_replay'),str(OLD/'analysis/trajectory_error/raw'),str(env['RAW'])]}
(ANA/'descriptive_replot_receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps({'c83_damage':[r for r in damage_rows if r['cycle']==83],'sections':sections,'history':history_rows,'first_active':[r for r in active if r['cycle']==1]},indent=2))
