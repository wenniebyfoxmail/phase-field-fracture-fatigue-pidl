"""Render only saved, frozen outcomes and six preselected saved RGB arrays."""
import json
from pathlib import Path
import numpy as np

def render(run,out,plan):
    import os
    os.environ['MPLCONFIGDIR']=str(out/'.mplconfig')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    read=lambda p:json.loads(p.read_text())
    result=read(run/'evaluate/result.json');evaluation=read(run/'evaluate/evaluation.json');bank=read(run/'bank/bank.json')
    arms=plan['arms'];fig,ax=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    ax[0].bar(arms,[result['U'][a] for a in arms]);ax[0].axhline(0,color='black',lw=.7);ax[0].set_ylabel('Net GT at 1 FP/image, nine consumed sites');ax[0].set_title('Primary D='+str(result['D']))
    for j,a in enumerate(arms):
        v=result['comparisons']['pooled12'][a];ax[1].bar(j,v['new_GT'],color='seagreen');ax[1].bar(j,-v['lost_old'],color='firebrick')
    ax[1].set_xticks(range(4),arms);ax[1].set_ylabel('New (+) / lost old (-), pooled12');ax[1].axhline(0,color='black',lw=.7)
    fig.suptitle('S01-E029 saved OOF comparison; old development sites, no fresh-site claim');fig.savefig(out/'F00_utility.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    for j,arm in enumerate(['aligned','half_shift']):
        vals=[]
        for k in range(3):
            fit=read(run/f'fit_{k}/{arm}_FIT.json');chosen=next(p for p in fit['policies'] if p['threshold']==fit['model']['threshold']);vals.append(chosen['positive_GT'])
        ax[j].bar(range(3),vals,label='chosen policy positives in capacity');ax[j].plot(range(3),[3,5,6],'ko--',label='available FIT GT (overlapping)');ax[j].set_xticks(range(3),['FIT0','FIT1','FIT2']);ax[j].set_title(arm+'; FIT evidence only');ax[j].legend(fontsize=8)
    fig.savefig(out/'F01_capacity.png',dpi=160);plt.close(fig)
    maps=np.load(run/'spatial/native_max.npy',mmap_mode='r');cases=read(run/'spatial/cases.json')['cases'];fig,axs=plt.subplots(6,2,figsize=(12,13),layout='constrained')
    selected={r['parent_id'] for r in evaluation['added']['aligned']}
    for row,cs in zip(axs,cases,strict=True):
        i=cs['index'];candidate=bank['candidates'][i];ctx=cs['context'];x1,y1,x2,y2=ctx;rgb=np.load(run/f'spatial/case_{i}_rgb.npy').transpose(1,2,0)
        row[0].imshow(rgb,extent=(x1,x2,y2,y1),aspect='auto');row[1].imshow(maps[i],vmin=0,vmax=1,cmap='magma',extent=(x1,x2,y2,y1),aspect='auto')
        for axis in row:
            for b,color in [(candidate['row']['original_box_xyxy'],'cyan'),(candidate['row']['box_xyxy'],'lime'),*[(b,'yellow') for b in evaluation['targets'][cs['image_id']]]]:
                axis.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,edgecolor=color,lw=.8))
            axis.set_xlim(x1,x2);axis.set_ylim(y2,y1);axis.tick_params(labelsize=6)
        row[0].set_title(cs['image_id']+' / parent '+str(candidate['parent_id']),fontsize=7)
        row[1].set_title('aligned OOF selected='+str(candidate['parent_id'] in selected)+'; probability 0..1',fontsize=8)
    fig.suptitle('Six GT-free fixed cases; display stretched. Cyan original, green correction, yellow box reference. Not pixel truth.',fontsize=10);fig.savefig(out/'F02_cases.png',dpi=160);plt.close(fig)
    (out/'README_analysis.md').write_text('''# S01-E029 saved evidence

Read F00 for the single nine-site net-GT contrast and pooled12 old protection; F01 for overlapping own-FIT capacity support (not independent gains); F02 for the six preselected first/last new-image cases in original groups, first candidate context. Cases were fixed before GT and saved during the permitted source decode, never picked by success. RGB/map geometry is the same crop; display stretched, common map scale0..1. Yellow is box reference, not exact pixel truth. Empty maps, abstention, failures and negative sites stay visible.

All quantities originate in frozen held predictions and evaluate/result.json; FIT policies are development calibration only. Full twelve/three qualification sites, including24, remain in the machine-readable comparisons. The primary nine sites exclude E028 qualification GT but were previously consumed. No full-pipeline geographic generalisation or confirmatory significance follows. Compare each operating point with its own E003 old-hit identities; do not combine scopes. A prior qualified localisation component does not establish utility here.
''',encoding='utf8')
