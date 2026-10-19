"""Source close-ups and unchanged texture matches; not an independent label."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from datetime import datetime,timezone
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

from md03_fixed_triplet import BASE,WORK
from md03_grouped_observability import GROUP,XS,YS,OFF,match,intercept
from md01_cached_stage_forecast import sha,save

LOCAL=BASE/'D3_local_correspondence_20261019'
PROTOCOL=WORK/'docs/research/S03/S03-E049-MD03/local_correspondence_protocol.md'


def now():return datetime.now(timezone.utc).isoformat()


def run(out):
    start=time.monotonic();cpu=time.process_time();protected={}
    prior=json.loads((GROUP/'R001/protected_inputs.json').read_text())
    assert all(sha(p)==h for p,h in prior.items());protected.update(prior)
    for p in BASE.rglob('*'):
        if p.is_file() and LOCAL not in p.parents:protected[str(p)]=sha(p)
    for p in (Path(__file__),PROTOCOL):protected[str(p)]=sha(p)
    with np.load(GROUP/'R001/real_132_175/evidence.npz') as z:
        median=np.median(z['jump_x'],axis=0)
    peak=float(median.max());ties=XS[median==peak].tolist()
    candidate=min(ties,key=lambda x:(abs(x-2750),x))
    centers=sorted(set([2598,2750,candidate,2902]));assert candidate==2782
    cfg=json.loads((BASE/'history_support.json').read_text());roi,band=cfg['roi'],cfg['band']
    out.mkdir(parents=True,exist_ok=False)
    receipt=dict(execution='running',started_utc=now(),command=sys.argv,host=socket.gethostname(),pid=os.getpid(),
       runtime=sys.executable,commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip(),
       dirty=subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True).splitlines(),
       source_downloads=0,independent_reference_acquired=False,new_masks=0,new_forecast_scores=0)
    save(out/'start_receipt.json',receipt);save(out/'protected_inputs.json',protected)
    selection=dict(candidate_x=candidate,centers=centers,y=1900,source_y_range=[1800,2000],crop_halfwidth=92,
       selection='maximum prior175 medianJ column, fixed before source closeups; ties nearest2750/lowerx',
       prior_algorithm_selected=True,not_blind=True,no_reference_truth=True,all_column_medians=median.tolist(),xs=XS.tolist())
    save(out/'selection.json',selection)
    prov=f'\n## Data provenance\nE049 old three-source ROI arrays and grouped fields{GROUP}/R001; input hashes/selection/matches saved{out}. Renderer{Path(__file__)}. '
    limits=('\n## Limitations and claim boundary\nAlgorithm-selected development candidate, not an independent or blind annotation. '
        'Same three already-exposed images; no reference acquired, crack truth or physical-width measurement. '
        'NCC fits reproduce earlier algorithm, not physical material identity. Global reference image resampled once. '
        'No parameter/threshold/position replacement, no new mask/forecast score; old half-depth unchanged.\n')
    def export(fig,stem,text):
        fig.savefig(out/(stem+'.png'),dpi=200);plt.close(fig)
        (out/(stem+'.md')).write_text(text+prov+limits)
    try:
        raw={}
        for s in (89,132,175):
            p=BASE/'R002_history'/str(s) if s!=175 else BASE/'R003_target'
            with np.load(p/'arrays.npz') as z:raw[s]=z['roi_rgb'][:,:,0]
        fig,ax=plt.subplots(figsize=(9,3.8),layout='constrained')
        ax.plot(XS,median,'-o',lw=1.3,ms=3,color='#0072B2')
        for c in centers:ax.axvline(c,color='#D55E00' if c==candidate else '#777777',ls='--',lw=.9)
        ax.set(xlabel='native x (px), all39 columns',ylabel='prior median J across21rows (image px)',
               title=f'All prior column summaries | selected x{candidate}, NOT a validated crack')
        ax.grid(alpha=.2)
        export(fig,'F00_transparent_selection','# How to read: transparent prior-field selection\n\n## Figure question\n'
          'Which existing algorithm response selected the local check?\n'
          '\n## Panels and visual grammar\nOne panel, all39pre-existing175paircolumnmedianJ; orange selectedmax, grayfixedcontrols. '
          'No local source-image selection, predictor error or width score involved.\n'
          f'\n## Key numerical takeaway\nSelectedx{candidate}; priorcolumnmedianJ{peak:.6f}imagepx, not realaperture.\n')
        fig,axs=plt.subplots(len(centers),3,figsize=(10.5,3.1*len(centers)),layout='constrained')
        for row,c in enumerate(centers):
            for col,s in enumerate((89,132,175)):
                x0,y0=c-92,1800;x1,y1=c+92,2000
                crop=raw[s][y0-roi[1]:y1-roi[1],x0-roi[0]:x1-roi[0]]
                axs[row,col].imshow(crop,cmap='gray',vmin=0,vmax=255,
                    interpolation='nearest',extent=(x0,x1,y1,y0))
                axs[row,col].set_title(f'IMG_{s:04d} | x{c} '+('prior candidate' if c==candidate else 'fixed comparison'))
                axs[row,col].set_xlabel('native x (px)');axs[row,col].set_ylabel('native y (px)')
        fig.suptitle('Source-only close-ups | same native coordinates, NO algorithm contours / NO enhancement\n'
                     'Selected location is already algorithm-informed; this is NOT blind annotation',fontsize=12)
        export(fig,'F01_source_only_local_checks','# How to read: all source-only local checks\n\n## Figure question\n'
          'Can a coherent gap be confidently located on original image structure, independently of a drawn algorithm contour?\n'
          '\n## Panels and visual grammar\nRows four frozenxcolumns2598/2750/2782/2902; columns source89/132/175. '
          'Identical xcentre±92,y1800..2000crop perrow, native0..255gray, nearest-display only, no enhancement/overlays. '
          'Same image coordinates are not material coordinates.\n'
          '\n## Key numerical takeaway\nTwelve crops retained, no post-view favourable replacement.\n')
        records=[]
        for c in centers:
            fig,axs=plt.subplots(2,3,figsize=(13,7.7),layout='constrained')
            for row,(a,b) in enumerate([(89,132),(132,175)]):
                with np.load(GROUP/f'R001/real_{a}_{b}/evidence.npz') as z:d={k:z[k] for k in z.files}
                x,y=c-band[0],1900-band[1]
                left=[match(d['reference'],d['b_image'],x-int(o),y) for o in OFF]
                right=[match(d['reference'],d['b_image'],x+int(o),y) for o in OFF]
                l,lr=intercept([p['dx'] for p in left]);r,rr=intercept([p['dx'] for p in right])
                iy=int(np.flatnonzero(YS==1900)[0]);ix=int(np.flatnonzero(XS==c)[0])
                assert abs((r-l)-d['jump_x'][iy,ix])<1e-10
                record=dict(pair=[a,b],x=c,y=1900,left=left,right=right,jump=r-l,
                    gap_contrast=float(d['gap_contrast'][iy,ix]),left_intercept=l,right_intercept=r,
                    left_fit_rms=lr,right_fit_rms=rr,ncc_min=float(d['ncc_min'][iy,ix]),
                    same_algorithm_reconstruction=True,not_independent_reference=True)
                records.append(record)
                ext=(c-92,c+92,1960,1840)
                for ax,key,title in zip(axs[row,:2],['reference','b_image'],['Globally resampled A reference','Original B']):
                    crop=d[key][120:240,x-92:x+92]
                    ax.imshow(crop,cmap='gray',vmin=0,vmax=255,extent=ext,interpolation='nearest')
                    ax.axvline(c,color='#777777',ls=':',lw=.8)
                    ax.set_title(f'{a}→{b} | {title}')
                    ax.set_xlabel('native x (px)');ax.set_ylabel('native y (px)')
                for sign,side,color in [(-1,left,'#0072B2'),(1,right,'#D55E00')]:
                    for o,m in zip(OFF,side):
                        xx=c+sign*o
                        axs[row,0].add_patch(Rectangle((xx-15,1885),31,31,fill=False,edgecolor=color,lw=1))
                        axs[row,1].add_patch(Rectangle((xx-15+m['dx'],1885+m['dy']),31,31,fill=False,edgecolor=color,lw=1))
                    values=[m['dx'] for m in side];slope=(values[2]-values[0])/48
                    at0=l if sign==-1 else r
                    offsets=sign*OFF
                    axs[row,2].plot(offsets,values,'o',color=color,label='left patches' if sign==-1 else 'right patches')
                    sx=np.linspace(min(0,offsets.min()),max(0,offsets.max()),50)
                    axs[row,2].plot(sx,at0+(slope/sign)*sx,color=color,lw=1.2)
                axs[row,2].axvline(0,color='#777777',ls=':',lw=.8)
                axs[row,2].set_title(f'J={r-l:+.3f} image px; Q={record["gap_contrast"]:+.3f} gray\n'
                       f'min NCC={record["ncc_min"]:.3f}; not physical crack width')
                axs[row,2].set_xlabel('patch centre offset from candidate (px)')
                axs[row,2].set_ylabel('horizontal displacement (image px)');axs[row,2].grid(alpha=.2)
                axs[row,2].legend(fontsize=8)
            fig.suptitle(f'Fixed x{c}, y1900 | six unchanged texture matches and side extrapolations\n'
                         'Boxes show source and matched windows; high NCC is NOT independent material truth',fontsize=12)
            export(fig,f'F02_correspondence_x{c}',f'# How to read: local texture correspondence atx{c}\n\n## Figure question\n'
                'Which six texture matches produce the saved opening proxy, and can source structure substantiate it?\n'
                '\n## Panels and visual grammar\nRows89→132/132→175; columns compensatedreference, untouchedlaterB, '
                'sixhorizontal displacements and separately extrapolatedsidefits. Blueleft/orangeright31x31patches, '
                'fixedcentralgrayguide. Shiftedboxes use the actual fitted displacement, no arrow exaggeration. '
                'Patchcoordinates x±24/48/72,y1900; reference resampling explicitly labelled. '
                'Displacement units imagepixels; Qrelativegraycode, no mask or physical-width output.\n'
                '\n## Key numerical takeaway\n'+json.dumps(records[-2:],indent=2))
        save(out/'matches.json',records)
        assert all(sha(p)==h for p,h in protected.items())
        assert max(time.monotonic()-start,time.process_time()-cpu)<90
        receipt.update(execution='succeeded',retrieval='verified_local',protected_files_verified=len(protected),
              crops=12,local_match_sets=8,old_J_reconstructed_exact=True)
        print(json.dumps([dict(pair=r['pair'],x=r['x'],J=r['jump'],Q=r['gap_contrast'],ncc=r['ncc_min']) for r in records],indent=2))
    except Exception as error:receipt.update(execution='failed',error=repr(error));raise
    finally:
        receipt.update(ended_utc=now(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        save(out/'receipt.json',receipt)


if __name__=='__main__':run(LOCAL/'R001')
