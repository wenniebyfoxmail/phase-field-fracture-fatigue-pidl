"""Posthoc E044 geometry-only guide overlay; no extraction or scoring changes."""
import argparse
import json
from pathlib import Path

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import distance_transform_edt

from md01_cached_stage_forecast import sha,save


def main(source,lockpath,out):
    out.mkdir(parents=True,exist_ok=False)
    summary=json.loads((source/'summary.json').read_text());lock=json.loads(lockpath.read_text())
    # Fixed interpretation rule: largest absolute frozen separated-predictor error.
    row=max((r for r in summary['comparisons'] if r['support_hold_ae'] is not None),
            key=lambda r:(r['support_hold_ae'],-r['target']))
    target=row['target'];arraypath=source/f'W{target}/observation_arrays.npz'
    inputs={str(p):sha(p) for p in (source/'summary.json',lockpath,arraypath,Path(__file__))}
    roi,band=lock['roi'],lock['band'];seed=np.zeros((roi[3]-roi[1],roi[2]-roi[0]),np.uint8)
    pts=np.rint(np.array(lock['new_stage_support']['coarse_guide_xy'])-np.array(roi[:2])).astype(np.int32)
    cv2.polylines(seed,[pts],False,1,thickness=1)
    distance=distance_transform_edt(~seed.astype(bool))
    x0,y0,x1,y1=np.array(band)-np.array([roi[0],roi[1],roi[0],roi[1]])
    d=distance[y0:y1,x0:x1]
    with np.load(arraypath) as z:rgb=z['band_rgb'];mask=z['band_mask']
    assert not np.any(mask&(d>60)), 'Saved mask outside frozen corridor'
    plt.rcParams.update({'font.size':10,'pdf.fonttype':42})
    fig,axes=plt.subplots(2,1,figsize=(10,7.3),layout='constrained')
    for ax in axes:
        ax.imshow(rgb,extent=[band[0],band[2],band[3],band[1]])
        ax.contour(np.arange(band[0],band[2]),np.arange(band[1],band[3]),d,levels=[60],colors=['#E69F00'],linewidths=1.4)
        xy=np.array(lock['new_stage_support']['coarse_guide_xy']);ax.plot(xy[:,0],xy[:,1],color='#E69F00',ls='--',lw=1)
        ax.set(xlim=(band[0],band[2]),ylim=(band[3],band[1]),xlabel='Native image x (px)',ylabel='Native image y (px)')
    axes[0].set_title(f'A  Step{target} source + frozen stage23 guide (dashed) and60px corridor edges')
    overlay=np.zeros((*mask.shape,4));overlay[mask]=(0,.55,.8,.8)
    axes[1].imshow(overlay,extent=[band[0],band[2],band[3],band[1]])
    axes[1].set_title('B  Same saved candidate mask (cyan); nothing extracted or repaired')
    fig.suptitle('E044 posthoc guide-transfer diagnosis | worst fixed-query error\nOutside-corridor surface is ineligible; no crack-truth labels or physical-turnover claim',fontsize=12)
    stem='F03_worst_case_frozen_guide'
    fig.savefig(out/f'{stem}.png',dpi=300);fig.savefig(out/f'{stem}.pdf');plt.close(fig)
    (out/f'{stem}.md').write_text('# How to read: frozen-guide transfer on the worst fixed query\n\n## Figure question\nCan frozen guide geometry explain part of the visible omission, without editing identification?\n'
        f'\n## Data provenance\nE044 numeric R001: {source}; R000 selection: {lockpath}. Renderer scripts/plot_md01_guide_transfer_audit.py. '
        f'Only saved target{target} band RGB/mask used; fullROI guide distance raster recomputed from unchanged source23 points, not from target pixels. '
        'Posthoc diagnosis, not a new mask run, performance arm or parameter selection. Example rule=largest saved separated-predictor AE, smallest target on tie.\n'
        '\n## Visual grammar and panel guide\nA native sourceband with orange dashed guide and orange60pxdistance contours. B identicalsource with savedcyanmask, samecontours. '
        'Coordinates native imagepx; fullROI EDT matches extractor geometry before bandcrop. Contour lines show onlycorridor gate, not allgray/contrast/contactconditions.\n'
        f'\n## Key numerical takeaway\nSelected target{target}, frozen AE={row["support_hold_ae"]:.2f}px². All saved candidate pixels satisfy≤60pxcorridor. '
        'Upper-left visible dark trace falls outside much of the transferred corridor; current candidatearea can lose it while retaining nearby otherdarkpixels. '
        'No labelled truecrack pixelcount, recall or identifiedmissingarea.\n'
        '\n## Limitations and claim boundary\nVisual sourceinterpretation only, not independent pixelannotation. Shadows/texture remain. '
        'Demonstrates geometriceligibility restriction, not cause ofevery omittedpixel, fullarea decrease, physicalshrinkage or correctedprediction. '
        'Old scores, masks andhalfdepth unchanged. This limits fixed-guide transfer, not the entire per-frame recognition/prediction route.\n')
    assert all(sha(p)==h for p,h in inputs.items())
    save(out/'render_receipt.json',dict(execution='succeeded',posthoc=True,target=target,
         selection_rule='largest stored separated AE; smallest target tie-break',inputs=inputs,
         old_saved_mask_unchanged=True,new_extraction=False,new_forecast=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path);p.add_argument('--lock',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args();main(a.source,a.lock,a.output)
