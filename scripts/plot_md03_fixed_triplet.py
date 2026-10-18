"""Exact-output visualisation of E049; never selects windows or changes masks."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
from PIL import Image

from md03_fixed_triplet import BASE, read, sha


def export(fig,out,stem,description):
    fig.savefig(out/(stem+'.png'),dpi=180)
    plt.close(fig)
    description=description.replace('# ','# How to read: ',1).replace('## Provenance','## Data provenance')
    (out/(stem+'.md')).write_text(description)


def inspect():
    out=BASE/'R001c_native_inspection';out.mkdir(exist_ok=False)
    frames=json.loads((BASE/'R000_selection/selection_lock.json').read_text())['frames'][:2]
    fig,axs=plt.subplots(2,1,figsize=(14,9),layout='constrained')
    for ax,f in zip(axs,frames):
        rgb,info=read(f)
        ax.imshow(rgb[1550:2200,1950:3500],extent=(1950,3500,2200,1550))
        ax.set_title(f'{f["filename"]} | history only | native pixels, uint16 / 257')
        ax.set_xlabel('native image x (px)');ax.set_ylabel('native image y (px)')
    fig.suptitle('E049 history inspection | same beam interior, no enhancement / no target')
    export(fig,out,'history_beam_interior',
        '# Historical beam-interior inspection\n\nQuestion: can a crack guide be defined from histories?\n'
        'Both fixed historical TIFFs0089/0132, official hashes in R000selection.\n'
        'Two panels same native crop[1950,1550,3500,2200], code-value division257 only, no enhancement.\n'
        'Axes native image pixels, dark means original low grayscale, no algorithm overlays.\n'
        'Display does not establish crack truth, time ordering or physical aperture.\n')


def detail():
    out=BASE/'R001d_native_detail';out.mkdir(exist_ok=False)
    frames=json.loads((BASE/'R000_selection/selection_lock.json').read_text())['frames'][:2]
    for f in frames:
        rgb,_=read(f);stem=f['filename'][:-4]+'_native_detail'
        Image.fromarray(rgb[1750:2200,2450:3150]).save(out/(stem+'.png'))
        (out/(stem+'.md')).write_text('# Native history detail\n\n'
            f'Source{f["source"]}, hash{f["sha256"]}. Same crop[2450,1750,3150,2200] on both histories.\n'
            'Single native-resolution view, fixed uint16//257 decoding, no enhancement, no algorithm labels.\n'
            'Purpose: identify a source-only coarse guide before measuring or opening target.\n'
            'Dark dots are DIC speckles, not crack labels; no accuracy/width/time claims.\n')


def final():
    out=BASE/'R004_figures';out.mkdir(exist_ok=False)
    lock=json.loads((BASE/'R000_selection/selection_lock.json').read_text())
    cfg=json.loads((BASE/'history_support.json').read_text())
    summary=json.loads((BASE/'R003_target/summary.json').read_text())
    saved=json.loads((BASE/'R002_history/predictions_before_target.json').read_text())
    frames=lock['frames'];sources=[BASE/'R002_history'/str(f['index']) for f in frames[:2]]+[BASE/'R003_target']
    observations=saved['history_observations']+[summary['target_observation']]
    band=cfg['band'];roi=cfg['roi'];x0,y0,x1,y1=band
    arrays=[]
    for p in sources:
        with np.load(p/'arrays.npz') as z:arrays.append({k:z[k] for k in z.files})
    provenance=('\n## Provenance\nE049 R000 fixed ranks87/130/173, indices89/132/175; '
        f'official SHA256 metadata and raw files in{BASE}. '
        'Measurements from R002_history and R003_target, prediction saved before target download. '
        f'Frozen history-only configuration{BASE}/history_support.json. Renderer{Path(__file__)}.\n')
    limits=('\n## Limitations and claim boundary\nOne beam/one file-order query. TIFFs contain no capture timestamps; '
        'absolute time/load order not established. Intensity mapped by uint16//257, no image-adaptive scaling. '
        'Dense sprayed DIC speckles may dominate frozen dark candidates. Central seed is a geometry probe, '
        'not an independently traced crack. No truth mask, no physical width, no old half-depth redefinition. '
        'Numerical forecast errors concern observer output only, not validated crack prediction.\n')
    fig,axs=plt.subplots(1,3,figsize=(14,4.8),layout='constrained')
    for i,(ax,f) in enumerate(zip(axs,frames)):
        rgb,_=read(f);ax.imshow(rgb)
        ax.add_patch(Rectangle((roi[0],roi[1]),roi[2]-roi[0],roi[3]-roi[1],fill=False,color='#E69F00',lw=1))
        ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,color='#56B4E9',lw=1))
        ax.set_title(f'{f["filename"]}\n'+('History' if i<2 else 'Target, opened after prediction'))
        ax.axis('off')
    fig.suptitle('E049 | All three fixed MD03 source images\nOrange: processing ROI; cyan: fixed scoring band. Same native image frame.')
    export(fig,out,'F00_source_context','# Source context\n\n## Figure question\nWhere does the frozen probe sit on the beam?\n'+provenance+
        '\n## Panels and visual grammar\nAll3 fixed whole-source frames left to right, same scale. Orange processing ROI, cyan scoringband. '
        'No favourable frame substitution. Whole view thumbnails display-only.\n\n## Takeaway\nThe small interior band is not whole-beam crack coverage.\n'+limits)
    fig,axs=plt.subplots(3,3,figsize=(13,10),layout='constrained')
    colors=['#0072B2','#009E73','#CC79A7']
    for i,(z,f,obs) in enumerate(zip(arrays,frames,observations)):
        a,b,c=axs[i];rgb=z['band_rgb'];mask=z['band_mask']
        a.imshow(rgb,extent=(x0,x1,y1,y0));b.imshow(rgb,extent=(x0,x1,y1,y0))
        overlay=np.zeros((*mask.shape,4));overlay[mask]=(0,.65,.85,.6)
        b.imshow(overlay,extent=(x0,x1,y1,y0),interpolation='nearest')
        paths=json.loads((sources[i]/'paths.json').read_text())
        for path in paths:
            xy=np.asarray(path['xy_native']);b.plot(xy[:,0],xy[:,1],color='#E69F00',lw=.7)
        guide=z['guide_path'];valid=(guide[:,1]>=y0)&(guide[:,1]<y1)
        b.plot(guide[valid,0],guide[valid,1],ls='--',color='#CC79A7',lw=.9)
        a.set_title(f'{f["filename"]}: original scoring band')
        b.set_title(f'Cyan mask: {obs["observation"]["area"]:,} px² | orange paths')
        c.plot(z['row_mass'],np.arange(y0,y1),color=colors[i],lw=1.1)
        c.set_ylim(y1,y0);c.set_xlim(0,max(float(z['row_mass'].max()) for z in arrays)*1.08)
        c.set_title(f'Row mass | {obs["observation"]["support"]}/360 occupied rows')
        c.set_xlabel('candidate pixels / image row');c.set_ylabel('native y (px)')
        c.grid(alpha=.18)
        for ax in (a,b):ax.set_xlabel('native x (px)');ax.set_ylabel('native y (px)')
    fig.suptitle('E049 | Frozen recognition on dense DIC speckles\nSame band and thresholds; geometric seed is NOT a crack annotation',fontsize=13)
    export(fig,out,'F01_observer_overlays','# All fixed-frame recognition results\n\n## Figure question\nDoes the transferred observer isolate a coherent crack?\n'+provenance+
        '\n## Panels and visual grammar\nRows89/132/175. Columns original scoringband, cyan frozen mask/orange fragment paths/purple dashed transferredseed, '
        'and row candidate mass vs native imagey. Same band extent, massxlimits and original grayscale. '
        'Orange segments are skeleton-derived graph paths, not independently confirmed crack traces.\n\n## Key numerical takeaway\n'+
        json.dumps([r['observation'] for r in observations],indent=2)+limits)
    fig,axs=plt.subplots(1,3,figsize=(13,4.9),layout='constrained')
    indices=[f['index'] for f in frames];aa=[o['observation']['area'] for o in observations]
    ll=[o['observation']['support'] for o in observations];mm=[o['observation']['mass'] for o in observations]
    for ax,values,label in zip(axs,[aa,ll,mm],['Candidate area (px²; zoomed)','Occupied image rows / 360','Pixels / occupied row (not crack width)']):
        ax.plot(indices[:2],values[:2],'-o',color='#222222',lw=1.4,label='History observation')
        ax.scatter(indices[2],values[2],color='#222222',marker='s',s=45,label='Target observation',zorder=5)
        ax.axvline(indices[1],color='#777777',ls=':',lw=1)
        ax.set_xticks(indices);ax.set_xlabel('Filename index (NOT time / load)');ax.set_ylabel(label);ax.grid(alpha=.18)
    p=summary['predictions'];err=summary['absolute_area_errors']
    for key,color,ls,label in [('persistence','#E69F00','--','Hold'),('secant','#0072B2','-.','Area extrapolation')]:
        axs[0].plot(indices[1:],[aa[1],p[key]],ls=ls,color=color,lw=1.5,label=f'{label}: {p[key]:,.0f}; AE {err[key]:,.0f}')
        axs[0].scatter(indices[2],p[key],color=color,marker='x',s=70,zorder=6)
    if p['support_hold'] is not None:
        axs[0].scatter(indices[2],p['support_hold'],marker='o',facecolors='none',edgecolors='#009E73',s=120,
                       label=f'Separated: {p["support_hold"]:,.0f}; AE {err["support_hold"]:,.0f}',zorder=7)
    for ax in axs:ax.legend(fontsize=7,loc='best')
    axs[0].set_title('Origin-only forecasts, then target');axs[1].set_title('L: coverage support, not path length')
    axs[2].set_title('M: conditional row mass, not half-depth')
    gain=summary['gains_vs_hold']['secant']
    fig.suptitle(f'E049 | One fixed candidate-output comparison | gain vs hold {gain:+,.0f} px²\n'
                 'Numeric continuity is not validated crack forecasting; no verified capture times',fontsize=12)
    export(fig,out,'F02_forecast_comparison','# Candidate-output forecasts\n\n## Figure question\nDoes two-history extrapolation beat holding the observer output?\n'+provenance+
        '\n## Panels and visual grammar\nLeftA: observed area histories solidblack/targetblack square, holdorange dashed, '
        'area extrapolationblue dashdot, separatedgreen open circle. Forecasts start at origin132. '
        'Candidate-area axis zoomed, no zero baseline inference. MiddleL occupiedrows (not cracklength). '
        'RightM mean candidate rowmass (not halfdepth or physicalwidth). Dottedorigin. '
        'Only one target, no confidence interval or independent replicates.\n\n## Key numerical takeaway\n'+
        json.dumps(dict(observations=[o['observation'] for o in observations],predictions=p,
                        errors=err,gains=summary['gains_vs_hold']),indent=2)+limits)
    manifest={str(p):sha(p) for p in out.glob('*') if p.is_file()}
    (out/'render_manifest.json').write_text(json.dumps(manifest,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('inspect','detail','final'))
    args=parser.parse_args()
    if args.phase=='inspect':inspect()
    elif args.phase=='detail':detail()
    else:final()
