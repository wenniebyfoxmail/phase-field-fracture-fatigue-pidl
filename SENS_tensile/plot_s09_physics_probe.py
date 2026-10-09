#!/usr/bin/env python3
"""Decision figures from scored S09-E003 output; no training or inference."""
import argparse,json,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree

p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=True)
h=np.genfromtxt(a.run/'history.csv',delimiter=',',names=True);m=json.loads((a.run/'metrics.json').read_text())
f=np.load(a.run/'final_fields.npz');xy=f['xy'];u=f['u'];ref=f['u_native'];free=f['free'];force=f['force']
fig,ax=plt.subplots(figsize=(7,4.5),layout='constrained')
ax.plot(h['step'],h['force_rms_ratio_to_affine'],color='#0072B2',label='Equilibrium-only PINN')
ax.axhline(1,color='0.4',ls='--',label='Affine BC baseline')
ax.axhline(.8,color='#D55E00',ls=':',label='Frozen diagnostic gate (final <= 0.8)')
ax.set(xlabel='Adam updates',ylabel='Free-force RMS / initial affine RMS',title='S09-E003-R001 | fixed FEM damage, U012 c76 s4\nOne synthetic state, one seed; no holdout')
ax.set_yscale('log');ax.legend(fontsize=9);ax.grid(alpha=.15)
for ext in ['png','pdf']:fig.savefig(a.out/f'physics_decision.{ext}',dpi=180)
plt.close(fig)
# All native-domain nodes; nearest-node display only, no scored metric regridding.
gx=np.linspace(xy[:,0].min(),xy[:,0].max(),450);gy=np.linspace(xy[:,1].min(),xy[:,1].max(),450)
xx,yy=np.meshgrid(gx,gy);idx=cKDTree(xy).query(np.c_[xx.ravel(),yy.ravel()])[1].reshape(xx.shape)
fig,axs=plt.subplots(2,3,figsize=(11,7.3),layout='constrained')
extent=[gx.min(),gx.max(),gy.min(),gy.max()]
for j,name in enumerate(['u_x','u_y']):
 lo=min(u[:,j].min(),ref[:,j].min());hi=max(u[:,j].max(),ref[:,j].max())
 for k,(v,title) in enumerate([(ref[:,j],f'Native {name} (diagnostic reference)'),(u[:,j],f'PINN {name} at update 500')]):
  im=axs[j,k].imshow(v[idx],origin='lower',extent=extent,cmap='viridis',vmin=lo,vmax=hi)
  axs[j,k].set_title(title,fontsize=10)
 fig.colorbar(im,ax=axs[j,:2],shrink=.8,label='Displacement (normalized units)')
 err=u[:,j]-ref[:,j];lim=max(abs(err).max(),1e-15)
 im=axs[j,2].imshow(err[idx],origin='lower',extent=extent,cmap='RdBu_r',vmin=-lim,vmax=lim)
 axs[j,2].set_title('PINN minus native',fontsize=10);fig.colorbar(im,ax=axs[j,2],shrink=.8)
for ax in axs.ravel():ax.set(xlabel='x',ylabel='y')
fig.suptitle('S09-E003-R001 | full domain, fixed native d, final checkpoint\n450x450 nearest-node display; native reference is not an exact equilibrium certificate',fontsize=11)
for ext in ['png','pdf']:fig.savefig(a.out/f'physics_fields.{ext}',dpi=180)
plt.close(fig)
# Spatial failure view, no assertion of independent units.
r=np.sqrt((force**2).sum(1));mask=free.any(1)
fig,ax=plt.subplots(figsize=(6,4),layout='constrained');v=np.log10(np.maximum(r,1e-18));v[~mask]=np.nan
im=ax.imshow(v[idx],origin='lower',extent=extent,cmap='magma');fig.colorbar(im,ax=ax,label='log10 free-node force norm')
ax.set(title='Final spatial residual | boundary reactions excluded',xlabel='x',ylabel='y')
fig.savefig(a.out/'physics_residual.png',dpi=180);plt.close(fig)
print(json.dumps({'final_force_rms_recomputed':float(np.sqrt(np.mean(force[free]**2))),
 'reported_final_force_rms':m['final']['force_rms'],'final_step':int(f['step'])},indent=2))
