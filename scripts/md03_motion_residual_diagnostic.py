"""D3: raw vs saved-motion-compensated residuals; no fitting/segmentation."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from md03_fixed_triplet import BASE, WORK, read, guard
from md01_cached_stage_forecast import sha, save

RUNROOT=BASE/'D3_20261019'
PAIRS=((89,132,'historical design pair'),(132,175,'exposed development diagnostic'))


def now():return datetime.now(timezone.utc).isoformat()


def warp_valid(a,matrix):
    """Forward source->destination matrix; full bilinear neighbourhood required."""
    h,w=a.shape
    warped=cv2.warpAffine(a.astype(np.float32),matrix,(w,h),flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT,borderValue=0)
    inv=cv2.invertAffineTransform(matrix)
    yy,xx=np.indices((h,w),dtype=np.float64)
    sx=inv[0,0]*xx+inv[0,1]*yy+inv[0,2]
    sy=inv[1,0]*xx+inv[1,1]*yy+inv[1,2]
    valid=(np.floor(sx)>=0)&(np.floor(sx)+1<w)&(np.floor(sy)>=0)&(np.floor(sy)+1<h)
    return warped,valid


def tests():
    a=np.arange(80,dtype=np.float32).reshape(8,10)
    ident=np.array([[1.,0,0],[0,1.,0]])
    w,v=warp_valid(a,ident);assert np.array_equal(w,a)
    assert v.sum()==7*9 and not v[-1].any() and not v[:,-1].any()
    trans=np.array([[1.,0,2],[0,1.,1]])
    w,v=warp_valid(a,trans)
    assert np.array_equal(w[1:,2:],a[:-1,:-2])
    assert np.all((w[1:,2:]-a[:-1,:-2])==0)
    assert not v[:1].any() and not v[:,:2].any()
    # A genuine darkening remains a positive residual after exact translation.
    b=w.copy();b[3,5]-=7
    assert (w-b)[3,5]==7
    fractional=np.array([[1.,0,.5],[0,1.,.5]])
    w,v=warp_valid(a,fractional)
    assert np.isclose(w[4,4],np.mean(a[3:5,3:5]))
    print('Identity, forward integer/fractional warp, strict support, signed-darkening tests passed.')


def stats(d,valid):
    values=d[valid].astype(np.float64)
    return dict(mean_abs=float(np.mean(abs(values))),rmse=float(np.sqrt(np.mean(values**2))),
                mean_signed=float(np.mean(values)),p90_abs=float(np.percentile(abs(values),90)),
                units='fixed uint8 grayscale code levels; not geometry or accuracy')


def run(out):
    start=time.monotonic();cpu=time.process_time()
    oldlock=json.loads((BASE/'R000_selection/selection_lock.json').read_text());guard(oldlock)
    protected=dict(oldlock['protected'])
    for p in BASE.rglob('*'):
        if p.is_file() and RUNROOT not in p.parents:protected[str(p)]=sha(p)
    cfg=json.loads((BASE/'history_support.json').read_text())
    h=json.loads((BASE/'R002_history/predictions_before_target.json').read_text())
    t=json.loads((BASE/'R003_target/summary.json').read_text())
    matrices=[np.array(h['history_view_diagnostic']['affine_roi_pixels'],dtype=float),
              np.array(t['target_view_diagnostic']['affine_roi_pixels'],dtype=float)]
    sources={f['index']:f for f in oldlock['frames']}
    assert set(sources)=={89,132,175}
    out.mkdir(parents=True,exist_ok=False)
    receipt=dict(execution='running',started_utc=now(),host=socket.gethostname(),pid=os.getpid(),
        command=sys.argv,runtime=sys.executable,code_sha256=sha(__file__),
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip(),
        dirty=subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True).splitlines(),
        fit_calls=0,source_downloads=0,segmentation_calls=0,new_forecast_comparisons=0)
    save(out/'start_receipt.json',receipt);save(out/'protected_inputs.json',protected)
    save(out/'input_specification.json',dict(pairs=PAIRS,roi=cfg['roi'],band=cfg['band'],
        source_records=list(sources.values()),matrices=[m.tolist() for m in matrices],
        matrix_role='previously saved forward similarity sourceROI->destinationROI, no re-estimation',
        interpolation='OpenCV INTER_LINEAR once on float32; no extra smoothing or photometric normalisation',
        common_support='inverse source floor(x/y) and +1 both in-bounds; used for both residuals',
        d0='A-B same native image grid',d1='warp(A)-B on destination grid',
        color_limits=[-255,255],raw_scope='controlled experiment development diagnostics, not crack truth'))
    def check():
        if any(sha(p)!=digest for p,digest in protected.items()):raise ValueError('Old evidence changed')
        if max(time.monotonic()-start,time.process_time()-cpu)>120:raise TimeoutError('120s analysis cap')
    try:
        roi=cfg['roi'];band=cfg['band'];x0,y0,x1,y1=roi
        bx0,by0,bx1,by1=np.array(band)-np.array([x0,y0,x0,y0]);sl=np.s_[by0:by1,bx0:bx1]
        gray={}
        for index,f in sources.items():
            rgb,info=read(f);assert info['oriented_size']==cfg['oriented_size']
            gray[index]=rgb[y0:y1,x0:x1,0].astype(np.float32)
        rows=[]
        for (a,b,role),matrix in zip(PAIRS,matrices):
            case=out/f'{a}_{b}';case.mkdir()
            aw,valid_full=warp_valid(gray[a],matrix)
            aa,bb,warped=gray[a][sl],gray[b][sl],aw[sl]
            valid=valid_full[sl];d0=aa-bb;d1=warped-bb
            assert valid.any() and np.array_equal(d0,aa.astype(float)-bb.astype(float))
            old=BASE/'R002_history'/str(b) if b!=175 else BASE/'R003_target'
            with np.load(old/'arrays.npz') as z:oldmask=z['band_mask']
            assert oldmask.shape==valid.shape
            np.savez_compressed(case/'residual_arrays.npz',a=aa,b=bb,warped_a=warped,
                   d0=d0,d1=d1,common_valid=valid,old_mask_b=oldmask)
            raw,comp=stats(d0,valid),stats(d1,valid)
            row=dict(pair=[a,b],role=role,matrix=matrix.tolist(),raw=raw,compensated=comp,
                 mean_abs_reduction_fraction=1-comp['mean_abs']/raw['mean_abs'] if raw['mean_abs'] else None,
                 support_valid_pixels=int(valid.sum()),band_pixels=int(valid.size),
                 support_fraction=float(valid.mean()),crack_measurement=False)
            save(case/'statistics.json',row);rows.append(row)
        check()
        summary=dict(rows=rows,old_files_verified=len(protected),frozen_observer_and_scores_unchanged=True,
              no_new_masks_or_widths=True,no_source_outside_89_132_175=True,
              conclusion_requires_visual_inspection=True,175_role='exposed development, not blind validation')
        save(out/'summary.json',summary)
        receipt.update(execution='succeeded',retrieval='verified_local',protected_files_verified=len(protected))
        print(json.dumps(summary,indent=2))
    except Exception as error:
        receipt.update(execution='failed',error=repr(error));raise
    finally:
        receipt.update(ended_utc=now(),wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        save(out/'receipt.json',receipt)


def render(source,out):
    out.mkdir(parents=True,exist_ok=False)
    spec=json.loads((source/'input_specification.json').read_text())
    summary=json.loads((source/'summary.json').read_text());band=spec['band']
    extent=(band[0],band[2],band[3],band[1])
    plt.rcParams.update({'font.size':9})
    fig,axs=plt.subplots(2,4,figsize=(16,7.4),layout='constrained')
    cmap=plt.get_cmap('RdBu_r').copy();cmap.set_bad('#B0B0B0')
    for axes,row in zip(axs,summary['rows']):
        a,b=row['pair']
        with np.load(source/f'{a}_{b}/residual_arrays.npz') as z:
            data={k:z[k] for k in z.files}
        aa,bb,valid=data['a'],data['b'],data['common_valid']
        overlay=np.stack([aa,bb,bb],axis=-1)/255
        overlay[~valid]=.69
        axes[0].imshow(overlay,extent=extent,interpolation='nearest')
        axes[0].set_title(f'{a} → {b}: original overlay\nred=A, cyan=B; '+('design' if a==89 else 'exposed development'))
        for ax,key,label in zip(axes[1:3],['d0','d1'],['Raw A-B','Saved-motion warp(A)-B']):
            im=ax.imshow(np.ma.array(data[key],mask=~valid),cmap=cmap,vmin=-255,vmax=255,
                         extent=extent,interpolation='nearest')
            metric=row['raw' if key=='d0' else 'compensated']['mean_abs']
            ax.set_title(f'{label}\nmean |difference|={metric:.3f} gray levels')
        axes[3].imshow(bb,cmap='gray',vmin=0,vmax=255,extent=extent,interpolation='nearest')
        # Contours from the immutable old mask; NOT a newly extracted object.
        axes[3].contour(np.arange(band[0],band[2])+.5,np.arange(band[1],band[3])+.5,
                        data['old_mask_b'].astype(float),levels=[.5],colors=['#56B4E9'],linewidths=.6)
        axes[3].axvline(2750,color='#E69F00',ls='--',lw=.8)
        axes[3].set_title(f'{b}: original + OLD cyan candidates\norange fixed x2750, NOT crack label')
        for ax in axes:ax.set_xlabel('native image x (px)');ax.set_ylabel('native image y (px)')
    cb=fig.colorbar(im,ax=axs[:,1:3].ravel().tolist(),orientation='vertical',shrink=.7,pad=.015)
    cb.set_label('signed difference (8-bit gray levels)\npositive = later image darker')
    fig.suptitle('MD03 D3 | Same fixed band, shared support, saved transforms only\n'
        'Residual reduction is not crack identification; no new segmentation / forecasts',fontsize=13)
    stem='F01_raw_vs_motion_residuals';fig.savefig(out/(stem+'.png'),dpi=220);plt.close(fig)
    note=('# How to read: MD03 raw vs motion-compensated residuals\n\n## Figure question\n'
        'Does cancelling existing measured image motion make crack-like changes distinguishable from sprayed speckles?\n'
        f'\n## Data provenance\nExact arrays/statistics{source}; D3 input_specification.json specifies sources and transforms. '
        'Only old89/132/175TIFFs, E049 fixed band[2500,1720,3000,2080], old16bit//257 conversion. '
        f'Renderer{Path(__file__)} render. No new fits, masks, forecasts or physical widths.\n'
        '\n## Panels and visual grammar\nRows89→132 historical design and132→175 exposed development. '
        'Columns original redA/cyanB overlay; rawA-B; saved-similarity warp(A)-B; B original with OLDcyan candidate contours/orange fixedx2750. '
        'Residuals shareRdBu_r zero-centered[-255,255], positive means later darkening. Originalgray0..255. '
        'All columns same native image band; gray invalid support excluded from both statistics. '
        'Bilinear sampling once, not nonrigid material registration.\n\n## Key numerical takeaway\n'+
        json.dumps(summary['rows'],indent=2)+
        '\n## Limitations and claim boundary\nPixel intensity continuity, not crack accuracy or real width. '
        'Sprayed speckle edges, lighting, distributed deformation and interpolation can all create residuals. '
        'Smaller residual is not evidence of preserved cracks; a retained line is only a candidate without reference. '
        '175 already exposed, no capture-clock/load qualification, no new prediction gains scored. '
        'No area/length/width remeasurement, no threshold sweep or four-anchor repair.\n')
    (out/(stem+'.md')).write_text(note)
    save(out/'receipt.json',dict(execution='succeeded',utc=now(),render_source=str(source),
           source_summary_sha256=sha(source/'summary.json'),renderer_sha256=sha(__file__),
           figure_sha256=sha(out/(stem+'.png')),sidecar_sha256=sha(out/(stem+'.md'))))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['self-test','run','render'])
    parser.add_argument('--output',type=Path);parser.add_argument('--source',type=Path)
    args=parser.parse_args()
    if args.phase=='self-test':tests()
    elif args.phase=='run':run(args.output)
    else:render(args.source,args.output)
