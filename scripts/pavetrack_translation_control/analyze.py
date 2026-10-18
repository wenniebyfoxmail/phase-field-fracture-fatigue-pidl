"""Decision plots and CSVs exclusively from saved E026 arrays/metrics."""
import csv
import importlib.util
import json
from pathlib import Path
import numpy as np

spec=importlib.util.spec_from_file_location('e026_plot_probe',Path(__file__).with_name('probe.py'))
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


def render(run):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    read=lambda n:json.loads((run/n).read_text(encoding='utf-8-sig'))
    with np.load(run/'controls.npz',allow_pickle=False) as z:
        rgb,ys,folds=(z[k] for k in ['rgb','masks','fold_indices'])
    meta=read('identities.json');rows=[];metrics=[]
    domain='SYNTHETIC ENGINEERING ONLY | ' if meta.get('synthetic') else ''
    for k in range(3):
        for j in range(2):
            m=read(f'metrics_{k}_{j}.json');metrics.append(m)
            row=dict(fold=k,seed=m['seed'],level=m['level'],passed=m['passed'],**m['gains'])
            for name,values in m['averages'].items():
                for key in ['Brier','Dice']:row[f'{name}_{key}']=values[key]
            rows.append(row)
    with (run/'decision_table.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    fig,axes=plt.subplots(1,3,figsize=(13,4))
    labels=[f'f{r["fold"]}/s{r["seed"]}' for r in rows]
    for ax,key,title in zip(axes,['Brier_gain','Dice_gain','phase_pairing_gain'],['Brier gain over best simple baseline','Dice gain over best simple baseline','Brier advantage of correct phase'],strict=True):
        ax.bar(np.arange(6),[r[key] for r in rows],color=['#3178a6' if r[key]>1e-6 else '#ce704c' for r in rows])
        ax.axhline(0,color='black',linewidth=.8);ax.axhline(1e-6,color='gray',linestyle='--',linewidth=.5)
        ax.set_xticks(np.arange(6),labels,rotation=60,fontsize=7);ax.set_title(title,fontsize=10)
    fig.suptitle(domain+'E026 fixed translated training-content controls | positive gains required | folds0/2 repeat contents',fontsize=10)
    fig.tight_layout();fig.savefig(run/'F00_components.png',dpi=140);plt.close(fig)
    # Per fold: all4 frozen evaluation phases of the first fixed control context.
    for k in range(3):
        ids=folds[k];p0=np.load(run/f'maps_{k}_0.npy',mmap_mode='r');p1=np.load(run/f'maps_{k}_1.npy',mmap_mode='r')
        with np.load(run/f'plan_{k}_0.npz',allow_pickle=False) as z:prior0=z['position_prior'];keep=z['shared_seam_masks']
        with np.load(run/f'plan_{k}_1.npz',allow_pickle=False) as z:prior1=z['position_prior']
        fig,axes=plt.subplots(4,11,figsize=(21,8))
        for phase,s in enumerate(probe.TEST_SHIFTS):
            x=probe.shift_rgb(rgb[ids[0]],s).transpose(1,2,0);y=probe.shift_mask(ys[ids[0]],s)
            panels=[x,y,prior0,prior1,p0[0,phase,0],p1[0,phase,0],p0[1,phase,0],p1[1,phase,0],p0[2,phase,0],p1[2,phase,0],keep[phase]]
            for col,panel in enumerate(panels):
                ax=axes[phase,col];ax.imshow(panel,interpolation='nearest',**({} if col==0 else dict(cmap='magma',vmin=0,vmax=1)));ax.set_xticks([]);ax.set_yticks([])
                if col==0:
                    if s[0]:ax.axhline(4*s[0]-.5,color='cyan',linewidth=.7)
                    if s[1]:ax.axvline(4*s[1]-.5,color='cyan',linewidth=.7)
            axes[phase,0].set_ylabel(f'shift{tuple(s.tolist())}\nsite{meta["rows"][ids[0]]["location"]}\nindex{meta["rows"][ids[0]]["source_index"]}',fontsize=7)
        for ax,title in zip(axes[0],['Correct RGB (cyan seam)','Target envelope','Position prior seed0','Position prior seed1','Correct seed0','Correct seed1','Wrong phase seed0','Wrong phase seed1','Wrong identity seed0','Wrong identity seed1','Shared seam keep mask'],strict=True):ax.set_title(title,fontsize=8)
        fig.suptitle(domain+f'E026 fold{k}: all4 fixed test shifts, first frozen context; probabilities/reference0..1\nWrong-phase RGB is same image shifted additional(16,16) grid cells; no natural-site/semantic claim',fontsize=11)
        fig.tight_layout(rect=[0,0,1,.92]);fig.savefig(run/f'F01_cases_fold{k}.png',dpi=140);plt.close(fig)
    (run/'README_analysis.md').write_text(domain+'''# E026 saved-output interpretation

Question: does paired spatial translation produce input-dependent regions on the same fixed training contents? All arrays are saved E026-R001 output, not new inference. RGB128 and mask32 come exclusively from16 prior control identities. No source-image, qualification/holdout label or E003 access.

Read F00: each seed must improve Brier and fixed.5 Dice over the strongest of training prevalence/all0/all1/actual-training-position mean map, and Brier over same-image phase-mismatched RGB. All three positive differences>1e-6 are necessary; two fixed seeds per fold give that fold's bounded repeatability. Positive component gains remain recorded even when another condition misses. Fold0/2 reuse the exact8contents; phases and pixels are not independent images. No statistical significance claim.

Read F01 fold0..2: each displays all4 fixed withheld shifts of its first prospectively fixed context, both fixed seeds and both mismatch types. Cyan lines show correct-input wrap seams; the final mask excludes borders and the union of correct/phase-mismatched seams for every auxiliary comparison. Wrong phase retains image identity/histogram, wrong identity cyclically uses the next of8images. Both use identical transforms to the extent specified; wrap/padding cues remain possible. Priors differ by training seed because they use that seed's actual128 shifts/context. Common0..1maps; region envelope reference does not identify exact visible crack width. Every other context remains saved in full arrays, not visually selected.

See the actual maps and F00 together; a Brier or pairing gain alone does not establish useful foreground regions. A two-seed regional pass supports only spatial input dependence on artificial transforms of these trained contents. It cannot establish crack semantics, natural-site qualification, selector top3 admission, E003 retention or OOF net benefit. No selector was connected. Preserve E025 negative and all E003/cap/abstention/sealed boundaries. result.json and decision_table.csv are the fixed criteria, auxiliary displays never rescue a miss.
''',encoding='utf8')
