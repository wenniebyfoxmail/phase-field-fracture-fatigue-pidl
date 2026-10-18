"""Compact all-case view from E045 frozen outputs, no new computation of masks."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from md01_cached_stage_forecast import sha,save


def main(source,out):
    out.mkdir(parents=True,exist_ok=False)
    j=json.loads((source/'summary.json').read_text())
    fig,axes=plt.subplots(3,4,figsize=(18,7.7),layout='constrained')
    plt.rcParams['pdf.fonttype']=42
    for i,r in enumerate(j['rows']):
        s=r['stage']
        with np.load(source/f'step{s}/comparison_arrays.npz') as z:
            rgb=z['band_rgb'];sl=np.s_[800:1050,100:800]
            old,new,add,remove=(z[k][sl] for k in ('old_mask','new_mask','added','removed'))
        for ax in axes[i]:ax.imshow(rgb);ax.set_axis_off()
        for ax,mask,c in [(axes[i,1],old,(0,.55,.8)),(axes[i,2],new,(.35,.25,.65)),
                          (axes[i,3],add,(.9,.6,0)),(axes[i,3],remove,(0,.6,.5))]:
            o=np.zeros((*mask.shape,4));o[mask]=(*c,.8);ax.imshow(o)
        for ax,title in zip(axes[i],[f'Step{s}: source',f"Frozen: {r['old_area']} px²",f"Geometric: {r['new_area']} px²",f"Added {r['added']} / removed {r['removed']}"]):ax.set_title(title,fontsize=11)
    fig.suptitle('E045 | All 3 cases, one frozen image-only guide-transfer rule\nCyan: old; purple: new; orange/green: additions/removals (NOT truth labels)',fontsize=14)
    stem='F03_all_cases_compact'
    fig.savefig(out/f'{stem}.png',dpi=300);fig.savefig(out/f'{stem}.pdf');plt.close(fig)
    (out/f'{stem}.md').write_text('# How to read: compact all-case guide-transfer comparison\n\n## Figure question\nDoes the same rule recover the26omission without systematically changing everycase?\n'
      f'\n## Data provenance\nE045 R001 {source}; summary.json andstep24/25/26comparison_arrays.npz. '
      'Renderer scripts/plot_md01_guide_transfer_overview.py; fixedscoringband native[3900,1700,4600,1950], offset[100,800]withinROI. '
      'No new extraction, numericalcomparison, parametersearch orforecast.\n'
      '\n## Visual grammar and panel guide\nRows24,25,26 in order; columns original/frozen cyan/newpurple/orangeadded-greenremoved. '
      'Allsameextent/pixelscale. Delta coloursdonotindicateaccuracy; everycase shown.\n'
      '\n## Key numerical takeaway\n'+json.dumps(j['rows'],indent=2)+
      '\n\n## Limitations and claim boundary\nNo independent pixeltruth; sources alreadyviewed; shadows/pores stillcanfollowdarkridges. '
      'Imagepixels notphysicalwidth; counts are candidatearea, notTP/FP. Oldhalfdepth andscoresunchanged.\n'
      '\n## What this figure means\n看见：24带内不变，25轻微增删，26上部候选恢复且右侧暗块被删。\n'
      '因此：图像几何引导修复有针对性的观测收益，不是统一放宽阈值。\n'
      '不代表：所有候选都是真裂缝、全局阴影消失或物理宽度已准确。\n')
    save(out/'render_receipt.json',dict(execution='succeeded',source=str(source),
          summary_sha256=sha(source/'summary.json'),renderer_sha256=sha(Path(__file__)),numerical_rerun=False,
          output_hashes={p.name:sha(p) for p in out.iterdir() if p.is_file()}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args();main(a.source,a.output)
