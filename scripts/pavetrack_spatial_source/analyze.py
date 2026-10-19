"""Saved-output only plots; source boundary pixels and target envelopes stay separate."""
import csv
import json
from pathlib import Path
import numpy as np


def render(run):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    read=lambda n:json.loads((run/n).read_text(encoding='utf-8-sig'))
    result=read('result.json');meta=read('cfd_identities.json');domain='SYNTHETIC ENGINEERING ONLY | ' if meta.get('synthetic') else ''
    with np.load(run/'references.npz',allow_pickle=False) as z:refs={n:z[n] for n in z.files}
    rgb={n:np.load(run/f'{n}_rgb.npy',mmap_mode='r') for n in ['cfd','pavetrack']}
    maps={n:np.load(run/f'{n}_pass0.npy',mmap_mode='r') for n in rgb}
    rows=[]
    for r in result['cfd']['rows']:
        rows.append(dict(id=meta['rows'][r['index']]['id'],Dice=r['correct']['Dice'],Brier=r['correct']['Brier'],Dice_gain=r['Dice_gain'],Brier_gain=r['Brier_gain'],pair_Dice_gain=r['pair_Dice_gain'],passed=r['passed']))
    with (run/'decision_table.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    fig,ax=plt.subplots(figsize=(11,4));ax.bar(range(12),[r['Dice_gain'] for r in rows],color=['#3178a6' if r['passed'] else '#ce704c' for r in rows]);ax.axhline(0,color='black',linewidth=.8);ax.set_xticks(range(12),[r['id'] for r in rows]);ax.set_ylabel('Dice advantage over strongest fixed comparator')
    ax.set_title(domain+f'E027 released-boundary development probe: {result["cfd"]["passed_images"]}/12 positive, primary requires7\nNo independent-site/physical-width/OOF claim',fontsize=10);fig.tight_layout();fig.savefig(run/'F00_boundary_decision.png',dpi=140);plt.close(fig)
    total=refs['cfd'].sum(0,dtype=np.float64)
    for group in range(3):
        fig,axes=plt.subplots(4,5,figsize=(13,9))
        for row,j in enumerate(range(group*4,group*4+4)):
            panels=[rgb['cfd'][j].transpose(1,2,0),refs['cfd'][j],(total-refs['cfd'][j])/11,maps['cfd'][j],maps['cfd'][(j+1)%12]]
            for col,x in enumerate(panels):axes[row,col].imshow(x,**({} if col==0 else dict(cmap='magma',vmin=0,vmax=1)));axes[row,col].set_xticks([]);axes[row,col].set_yticks([])
            axes[row,0].set_ylabel(meta['rows'][j]['id']);axes[row,3].set_xlabel(f'Dice={rows[j]["Dice"]:.4f}; gain={rows[j]["Dice_gain"]:+.4f}',fontsize=8)
        for ax,t in zip(axes[0],['Native RGB','Released Boundaries','LOO GT position prior','Frozen final prediction','Fixed next-image map'],strict=True):ax.set_title(t,fontsize=9)
        fig.suptitle(domain+'CFD fixed exposed development images; common0..1, no tolerance or postprocessing\nReference can trace sides; it is not filled area, exact centerline or physical width',fontsize=10);fig.tight_layout(rect=[0,0,1,.92]);fig.savefig(run/f'F01_cfd_fixed{group}.png',dpi=140);plt.close(fig)
    for group in range(2):
        fig,axes=plt.subplots(8,3,figsize=(8,17))
        for row,j in enumerate(range(group*8,group*8+8)):
            panels=[rgb['pavetrack'][j].transpose(1,2,0),refs['pavetrack'][j],maps['pavetrack'][j]]
            for col,x in enumerate(panels):axes[row,col].imshow(x,**({} if col==0 else dict(cmap='magma',vmin=0,vmax=1)));axes[row,col].set_xticks([]);axes[row,col].set_yticks([])
            axes[row,0].set_ylabel(f'fixed control{j}',fontsize=8)
        for ax,t in zip(axes[0],['Saved RGB128','Partial region envelope32','Frozen probability128'],strict=True):ax.set_title(t,fontsize=9)
        fig.suptitle(domain+'PaveTrack16 existing controls: descriptive only, not target qualification\nEnvelope outside is not verified negative; common0..1',fontsize=10);fig.tight_layout(rect=[0,0,1,.94]);fig.savefig(run/f'F02_pavetrack_fixed{group}.png',dpi=140);plt.close(fig)
    (run/'README_analysis.md').write_text(domain+'''# E027 frozen-source interpretation

F00: fixed.5 Dice on the12 predetermined exposed CFD development images must exceed the strongest of all0/all1, oracle per-image prevalence, other11reference-position mean, and cyclic next-image probability on at least7images. This is a minimal-majority benchmark-reference claim, not reliable deployment, exact crack area/width or independent generalisation. Every image is retained, no threshold/side/checkpoint/seed selection.

F01 fixed0..2: ALL12 predefined CFD images, native RGB/released Boundaries/GT-informed leave-one-out position map/frozen final probability/fixed identity mismatch; common0..1. Boundaries may trace sides of cracks and cannot be called filled area or exact physical centerline. Brier/soft and pairing differences are component evidence and do not vote on the primary. Published checkpoint training history is author-reported, not independently reconstructed.

F02 fixed0..1: ALL16 original PaveTrack control contexts, cached RGB128/partial envelope32/frozen probability128. These are a separate descriptive domain check, not exact pixel truth or natural-site qualification. Outside-envelope activation is not automatically a false crack. A source pass cannot connect a selector. E003/capacity/abstention/sealed sites remain untouched; OOF/net/retention null.

Only pass0 is scored. Pass1 repeats identical inputs in reverse order to check numerical output/weight stability, not learning or independent seed stability. Saved56maps, references and prediction freeze support recomputation. Source acquisition/safety or numerical repetition failure means inconclusive/invalid evidence, not model failure. Checkpoint is a separate locked input, not copied into100MiB outputs. No training or source images were used by this plotter.
''',encoding='utf8')
