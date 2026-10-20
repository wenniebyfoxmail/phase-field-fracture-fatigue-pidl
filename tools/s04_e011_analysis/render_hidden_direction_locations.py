#!/usr/bin/env python3
"""Presentation-only native field maps from a completed audit's saved arrays."""
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import SymLogNorm


def main(folder):
    path=folder/'direction_net_locations.png'
    if path.exists():raise FileExistsError(path)
    with np.load(folder/'localization.npz') as z:a={k:z[k] for k in z.files}
    p,c,w=a['nodes'],a['cells'],a['weights']
    fig,axs=plt.subplots(2,3,figsize=(13,7.5),layout='constrained')
    for i,(prefix,title) in enumerate([('R2_','Free nodal force squared'),('active_error2_','Active error squared')]):
        raw=[a[prefix+'initial'],a[prefix+'head_8'],a[prefix+'head_8']-a[prefix+'initial']]
        display=[np.mean(v[c],axis=1) if i==0 else np.sum(w*v,axis=1)/w.sum(1) for v in raw]
        common=max(float(np.max(display[0])),float(np.max(display[1])))
        for j,v in enumerate(display):
            lim=common if j<2 else float(np.max(np.abs(v)));threshold=lim*1e-6
            norm=SymLogNorm(threshold,vmin=0 if j<2 else -lim,vmax=lim)
            pc=PolyCollection(p[c],array=v,cmap='magma' if j<2 else 'RdBu_r',norm=norm,edgecolors='none',antialiased=False,rasterized=True)
            ax=axs[i,j];ax.add_collection(pc);ax.autoscale_view();ax.set_aspect('equal')
            ax.set_title(['Initial','Final head8','Final minus initial'][j]+'\n'+title,fontsize=10)
            cb=fig.colorbar(pc,ax=ax,shrink=.74,pad=.025)
            ticks=[0,threshold,lim*1e-3,lim] if j<2 else [-lim,-lim*1e-3,0,lim*1e-3,lim]
            cb.set_ticks(ticks);cb.set_ticklabels(['0' if t==0 else f'{t:.1e}' for t in ticks]);cb.ax.tick_params(labelsize=8)
    fig.suptitle('Frozen c20s4 PIDL | initial vs final and signed total change | no new field evaluation',fontsize=12)
    fig.savefig(path,dpi=200);plt.close(fig)
    note='''# Frozen c20 PIDL spatial direction audit — presentation correction

Source: localization.npz from analysis_hidden_direction_20261020_r1, source Run pf_s04e011_tightcouple_137cb03_20261019T122720Z_production, c20s4/raw99/U=.11999988, fixed conditional FEM outer18 damage and original UV boundary.

Rows: free-nodal force squared (mean of four nodal squared forces in each Q4 cell, reactions already zeroed), and active g(d)psi+ squared error vs conditional FEM (Jacobian-weighted mean of four GPs in each cell). Columns: common initial, final closed head8, final minus initial. First two columns share each row's exact limit; signed column has its own symmetric limit. Symmetric-log linear threshold is 1e-6 of each displayed limit. Explicit four/five scientific ticks avoid overlapping automatic near-zero labels; no clipping/scoring change. Polygon antialiasing is disabled to remove subpixel mesh-edge display texture.

This replaces direction_locations.png for reporting: the old figure is retained with a documented near-zero colorbar overlap. The original displayed last-pair change; this figure deliberately displays TOTAL initial-to-final change, matching the main residual-increase question. No native replay, NN/Phi/model, history or solve is called. All numerical claims use original node/GP arrays, not cell display averages.

See: residual and active error occupy different spatial supports; active error remains concentrated near the left horizontal crack band.
Therefore: a small reduction in integrated energy does not demonstrate elimination of either residual or local active-field error. Centroids and signed positive/negative contributions are descriptive localization, not proof of a causal hidden-parameter spectrum.
'''
    path.with_suffix('.md').write_text(note)
    with (folder/'README_analysis.md').open('a') as f:f.write('\n## Presentation correction\n\nUse direction_net_locations.png for spatial reporting; original direction_locations.png is retained with near-zero colorbar tick overlap. The corrected total-change map uses the same saved localization.npz with no new operator evaluation. See its standalone sidecar for exact averaging/scales.\n')


if __name__=='__main__':
    from pathlib import Path
    ap=argparse.ArgumentParser();ap.add_argument('--folder',type=Path,required=True);main(ap.parse_args().folder)
