import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm,SymLogNorm
p=argparse.ArgumentParser();p.add_argument('audit',type=Path);a=p.parse_args();s=json.loads((a.audit/'summary.json').read_text());z=np.load(a.audit/'fields.npz')
x=z['xy'];c=z['conn'];cent=x[c].mean(1);delta=np.linalg.norm(z['equilibrated_uv']-z['original_uv'],axis=1)/.11999988
w=z['gp_weights'];da=(w*(z['active_after']-z['active_before'])).sum(1)/w.sum(1)
fig,ax=plt.subplots(1,3,figsize=(14,4.3),layout='constrained')
q=ax[0].scatter(x[:,0],x[:,1],c=np.maximum(delta,1e-12),s=1,cmap='viridis',norm=LogNorm(vmin=1e-10,vmax=max(delta.max(),1e-9)),rasterized=True);fig.colorbar(q,ax=ax[0],label='|delta u| / Us (log color)' );ax[0].set_title('UV correction / fixed FEM damage')
v=max(abs(da).max(),1e-30);q=ax[1].scatter(cent[:,0],cent[:,1],c=da,s=1,cmap='RdBu_r',norm=SymLogNorm(linthresh=v*1e-4,vmin=-v,vmax=v),rasterized=True);fig.colorbar(q,ax=ax[1],label='delta active density (symlog color)' );ax[1].set_title('Active-driver change')
for q in ax[:2]:q.set_aspect('equal');q.set_xlabel('x');q.set_ylabel('y')
ax[2].plot(['Archived','UV equilibrated'],[s['before']['rho_u'],s['after']['rho_u']],'o-',label='UV');ax[2].plot(['Archived','UV equilibrated'],[s['before']['rho_d_common'],s['after']['rho_d_common']],'s-',label='Damage common free');ax[2].axhline(.001,color='black',ls='--',label='Frozen screen');ax[2].set_yscale('log');ax[2].set_ylabel('Mass-normalized residual');ax[2].legend(fontsize=8);ax[2].set_title('Frozen-state residuals')
o=a.audit/'figures';o.mkdir(exist_ok=True)
for ext in ['png','pdf']:fig.savefig(o/f'teacher_precision.{ext}',dpi=180)
(o/'README_analysis.md').write_text('Question: what correction restores UV equilibrium at fixed FEM c83 s4 damage? Source: S04-E006-R001 fields.npz and summary.json. Read UV correction, signed GP-weighted active-driver correction, then identical residual screens. UV color uses log scale (floor1e-10), signed active color uses symmetric log with linear width1e-4 of maximum amplitude; these are visualization scales, not scientific thresholds. Nodal/cell scatter maps use true Q4 locations, without triangulated interpolation. Damage and original-target fatigue stay fixed. Allowed: conditional UV correction and residual audit. Forbidden: physical-truth error, full coupled teacher qualification, trajectory or mesh-convergence claim. Storyline S04; destination censor.md.\n')
