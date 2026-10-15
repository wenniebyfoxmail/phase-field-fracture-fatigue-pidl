#!/usr/bin/env python3
"""Read-only E016 training asset figures; never solve or parse stage15."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from aa2024_geometry_prior import completed, PREP, load, bindings, sha


def assets(root, out):
    receipt=completed(root,'prepare',PREP)
    a=load(root/'prepared.npz');training=load(root/'training_geometry.npz')
    audit=json.loads((root/'geometry_audit.json').read_text())
    meta=json.loads((root/'preparation.json').read_text())
    lineage=dict(source_prepare=bindings(root,PREP),plotter_sha256=sha(__file__),
        preparation_run_id=receipt['run_id'],cycle=meta['cycle'],stages=[13,14],
        reference_coordinates='stage13',no_held_response=True)
    provenance='E016 | controlled experimental training assets | cycle'+meta['cycle']+' | stages13/14 only | '+receipt['run_id']
    fig,axes=plt.subplots(3,2,figsize=(11,9),constrained_layout=True)
    for row,band in enumerate(('3.6','1.8','2.7')):
        p=audit['profiles'][band];x=np.array(p['x_mm']);left,right=axes[row]
        left.plot(x,np.asarray(p['opening_mm'],float),label='raw opening',color='#0072B2')
        if p['outer_trend_mm'] is not None:
            left.plot(x,p['outer_trend_mm'],'--',label='outer linear trend',color='#D55E00')
        outer=p['outer_indices'];left.scatter(x[outer],np.asarray(p['opening_mm'],float)[outer],s=14,color='black',label='outer supported points')
        right.plot(x,np.asarray(p['corrected_mm'],float),color='#0072B2',label='detrended; missing stays blank')
        cross=p['crossings']
        if cross is not None:
            right.axhline(cross['halfheight_mm'],ls=':',color='grey',label='half peak')
            right.axvline(cross['left_mm'],color='#D55E00',ls='--');right.axvline(cross['right_mm'],color='#D55E00',ls='--')
        else:right.text(.03,.95,'Undefined: '+str(p['issue']),transform=right.transAxes,va='top',fontsize=8,wrap=True)
        left.set_title('b='+band+' mm | raw and fixed outer trend')
        right.set_title('b='+band+' mm | '+('PRIMARY' if row==0 else 'sensitivity on existing support'))
        for ax in (left,right):
            ax.set_xlabel('stage13 reference x [mm]');ax.set_ylabel('opening proxy [mm]')
            ax.legend(loc='upper center',bbox_to_anchor=(.5,-.22),fontsize=7)
    fig.suptitle(provenance+'\nOpening-localisation proxy, NOT measured crack tips',fontsize=10)
    save(fig,out,'training_profiles')

    fig,axes=plt.subplots(2,2,figsize=(11,8),constrained_layout=True)
    for ax,k in zip(axes[0],('old','proxy')):
        c=ax.scatter(*a['mesh'].T,c=a[k],s=7,cmap='viridis',vmin=0,vmax=1)
        fig.colorbar(c,ax=ax,label='d0 prior [dimensionless]')
        endpoints=(-9,6) if k=='old' else (meta['proxy_geometry']['left_mm'],meta['proxy_geometry']['right_mm'])
        ax.plot(endpoints,[0,0],color='#D55E00',lw=2)
        ax.set_title(k+' geometric prior; not measured damage')
    ax=axes[1,0]
    ax.scatter(*training['xy'].T,s=1,color='#bbbbbb',label='joint finite training support')
    c=ax.scatter(*a['xy'].T,c=a['weights'],s=7,cmap='viridis')
    fig.colorbar(c,ax=ax,label='frozen source lumped area [mm²]')
    for b in (1.8,2.7,3.6):
        for sign in (-1,1):ax.axhline(sign*b,color='#0072B2',lw=.6,ls=':')
    ax.set_title('Support, prescribed gauges and scoring weights')
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.22),fontsize=7)
    ax=axes[1,1];mesh=a['mesh'];bd=a['boundary'];bc=a['bc']
    ax.scatter(*mesh[bd].T,s=6,color='#D55E00')
    ax.quiver(*mesh[bd].T,*bc.T,angles='xy',scale_units='xy',scale=1/333,color='#0072B2')
    ax.set_title('Common training Dirichlet increment; arrows ×333')
    # Include arrowheads and all training support in shared spatial bounds.
    all_xy=np.vstack((mesh,training['xy'],mesh[bd]+333*bc))
    lo=all_xy.min(0)-1;hi=all_xy.max(0)+1
    for ax in axes.ravel():
        ax.set_aspect('equal');ax.set_xlim(lo[0],hi[0]);ax.set_ylim(lo[1],hi[1])
        ax.set_xlabel('stage13 reference x [mm]');ax.set_ylabel('stage13 reference y [mm]')
    fig.suptitle(provenance+'\nSame artificial mesh/BC; line position AND length may change',fontsize=10)
    save(fig,out,'training_spatial_assets')
    guide=('# E016 training-only spatial asset review\n\n'
        'Purpose: inspect a training-opening-defined prior procedure before any real solve.\n'
        'Read training_profiles then training_spatial_assets, then the exact JSON/NPZ numerical records.\n'
        'All three fixed gauges, all53 x locations and full joint training support are shown; no selection, smoothing or clipping.\n'
        'Halfheight endpoints describe localisation under fixed direction/mark spacing; auxiliary maxima are on existing support only.\n'
        'Spatial priors share0..1; BC arrows magnify saved mm increments333x for display, not a deformed-mesh claim.\n'
        'Source geometry, finite support and positive lumped weights are authoritative, not inferred from blank image space.\n'
        'Review geometry_audit.json for all106 primary queries, neighbour IDs/distances/conditions/coefficients and amplification,\n'
        'and preparation.json for coverage integrals and boundary interpolation diagnostics.\n'
        'Priors are not true damage, integrals are not crack area/effective stiffness; no material or future-cycle inference.\n'
        'This renderer only reads source-bound completed preparation; no held response, FEM solve or scoring.\n\n'
        'Source: '+str(root.resolve())+'\n\nLineage: '+json.dumps(lineage,ensure_ascii=False)+'\n\n'
        'Discrete prior/local-multiplier reports: '+json.dumps(meta['prior_coverage'],ensure_ascii=False)+'\n')
    (out/'README_analysis.md').write_text(guide)
    for name in ('training_profiles','training_spatial_assets'):
        (out/(name+'.md')).write_text('# '+name+'\n\n'+guide)
    (out/'render_receipt.json').write_text(json.dumps(dict(lineage,artifacts_sha256={p.name:sha(p) for p in out.iterdir() if p.is_file()}),indent=2))


def save(fig,out,name):
    fig.savefig(out/(name+'.png'),dpi=160);fig.savefig(out/(name+'.pdf'));plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False);assets(args.input,args.output)


if __name__=='__main__':main()
