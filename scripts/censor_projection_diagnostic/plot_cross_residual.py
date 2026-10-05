"""Spatial localization of frozen-field residual audit; visualization only."""
import argparse,json,textwrap
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np

p=argparse.ArgumentParser();p.add_argument('audit',type=Path);a=p.parse_args()
s=json.loads((a.audit/'summary.json').read_text());z=np.load(a.audit/'residual_fields.npz')
xy,c=z['xy'],z['conn'];mass=z['nodal_mass_fraction'];free=z['free_uv_mask']
g=z['total_grad_uv']*s['nominal_displacement']/s['energy_scale']
local=np.linalg.norm(g/mass[:,None],axis=1);local[~free]=np.nan
# Mean of only free nodal values for boundary cells; Dirichlet forces excluded.
vals=local[c];count=np.isfinite(vals).sum(axis=1);u=np.divide(np.nansum(vals,axis=1),count,out=np.zeros(len(c)),where=count>0)
data=[z['target_damage'][c].mean(1),z['healing_gp'].max(1),np.log10(np.maximum(u,1e-12)),z['projected_damage_residual'][c].mean(1)]
titles=['FEM c83 damage: nodal mean','Previous minus FEM damage: GP positive maximum','Free UV residual density: log10(cell mean)','Total projected damage residual: nodal mean']
cmaps=['viridis','magma','magma','RdBu_r']
fig,axes=plt.subplots(1,4,figsize=(14,3.8),layout='constrained')
for i,(ax,values,title,cmap) in enumerate(zip(axes,data,titles,cmaps)):
    pc=PolyCollection(xy[c],array=values,cmap=cmap,edgecolors='none',antialiaseds=False,rasterized=True)
    if i==0:pc.set_clim(0,1)
    if i==1:pc.set_clim(0,max(float(values.max()),1e-12))
    if i==3:pc.set_clim(-1,1)
    ax.add_collection(pc);ax.set_xlim(-.5,.5);ax.set_ylim(-.5,.5);ax.set_aspect('equal');ax.set_title(textwrap.fill(title,30),fontsize=9);ax.set_xlabel('x');ax.set_ylabel('y');fig.colorbar(pc,ax=ax,shrink=.78)
fig.suptitle('Frozen FEM target / projected PIDL413 history — read-only audit',fontsize=12)
out=a.audit/'figures';out.mkdir(exist_ok=True)
fig.savefig(out/'cross_residual_localization.png',dpi=180);fig.savefig(out/'cross_residual_localization.pdf');plt.close(fig)
(out/'README_analysis.md').write_text('''# Cross-residual spatial audit\n\nQuestion: where do the fixed FEM c83 field and frozen projected PIDL413 objective disagree? Source: S04-E002-R003 residual_fields.npz and summary.json; no optimization. Destination: censor research note / diagnostic archive.\n\nRead left to right: FEM damage; GP positive healing-gap maximum in each native Q4; free-UV residual density norm |M^-1*g_u| shown as log10 of the free-node cell mean (floor1e-12); total box-projected damage residual nodal mean. Exact quadrilateral polygons are used, no interpolation to a raster mesh or triangulation. Cell means are visualization reductions, not the norms used for gates. Boundary UV forces are excluded from the residual-density plot. All fields are dimensionless. Signed damage scale is fixed[-1,1].\n\nAllowed interpretation: spatial localization in this one-state frozen-history counterfactual. No FEM predecessor history control was available. The figure cannot isolate history as the sole cause, prove network incapacity, or qualify a trajectory. Numeric gate uses the unreduced nodal/GP arrays and the frozen mass-weighted definitions, not the plotted reductions.\n''')
