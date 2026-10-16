"""Presentation from exact saved predictions/evaluation; no calibration/inference."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

def render(run,result,models,support,evaluation,guard):
    out=run/'analysis';out.mkdir(exist_ok=False);xs=range(3)
    fig,axes=plt.subplots(1,2,figsize=(10,4));bars=axes[0].bar(xs,[s['positive_GT_count'] for s in support],color='#477da7');axes[0].bar_label(bars);axes[0].set_xticks(list(xs),['FIT0','FIT1','FIT2']);axes[0].set_ylabel('Distinct FIT positive GT');axes[0].set_title('Sparse FIT support (not sample adequacy)')
    axes[1].axis('off')
    for k,m in enumerate(models):axes[1].text(.05,.8-.25*k,f"fold{k}: tau={m['threshold']}; {'no correction' if m['abstained'] else 'active'}",fontsize=12)
    fig.suptitle(f'{run.name} | one learned threshold per FIT8');fig.tight_layout();fig.savefig(out/'F00_learning.png',dpi=160);plt.close(fig);guard.check()
    comp=result['comparison'];old=comp['retained_old']+comp['lost_old'];new=old+comp['net_GT'];fig,axes=plt.subplots(1,3,figsize=(12,4.5))
    bars=axes[0].bar(['E003','OOF learned'],[old,new],color=['#89939b','#477da7']);axes[0].bar_label(bars,padding=3);axes[0].set_ylim(0,max(old,new,1)*1.15);axes[0].set_ylabel('Budget-admitted GT')
    ret=comp['retention'];bars=axes[1].bar(['Old retention'],[ret or 0],color='#397b55');axes[1].axhline(.95,color='#555',linestyle='--');axes[1].set_ylim(0,1.12);axes[1].set_title('Unknown' if ret is None else f"{comp['retained_old']}/{old} retained")
    bars=axes[2].bar(['new','lost','net'],[comp['new_GT'],comp['lost_old'],comp['net_GT']],color=['#477da7','#af5949','#397b55']);axes[2].bar_label(bars,padding=3);d=comp['macro_delta'];axes[2].set_title('macro delta unknown' if d is None else f'macro recall {100*d:+.4f} pp')
    fig.suptitle(f'{run.name} | {result["status"]}\n12 reused sites; 1FP/image, IoU=.5; B12 not old four-site282');fig.tight_layout();fig.savefig(out/'F01_detection.png',dpi=160);plt.close(fig);guard.check()
    # Up to six score-ordered actually appended cases; all absences explicit.
    originals={r['parent_id']:r for r in evaluation['baseline_rows']};added=evaluation['rows'][len(originals):];chosen=sorted(added,key=lambda r:(-originals[r['parent_id']]['score'],r['image_id'],tuple(r['box_xyxy']),r['parent_id']))[:6]
    fig,axes=plt.subplots(2,3,figsize=(13,7));axes=axes.flatten()
    for ax,row in zip(axes,chosen):
        oldrow=originals[row['parent_id']];boxes=evaluation['targets'][row['image_id']]+[oldrow['box_xyxy'],row['box_xyxy']]
        for box in evaluation['targets'][row['image_id']]:ax.add_patch(Rectangle((box[0],box[1]),box[2]-box[0],box[3]-box[1],fill=False,edgecolor='#397b55'))
        for value,color in [(oldrow,'#477da7'),(row,'#af5949')]:
            b=value['box_xyxy'];ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,edgecolor=color,linewidth=2))
        lo=min(b[0] for b in boxes);hi=max(b[2] for b in boxes);top=min(b[1] for b in boxes);bottom=max(b[3] for b in boxes);pad=max(hi-lo,bottom-top)*.1+1;ax.set_xlim(lo-pad,hi+pad);ax.set_ylim(bottom+pad,top-pad);ax.set_aspect('equal');ax.set_title(f"site{row['reid']} source{row['parent_id']}",fontsize=9)
    for ax in axes[len(chosen):]:ax.axis('off')
    if not chosen:axes[0].text(.05,.5,'No corrections selected (explicit abstention)',transform=axes[0].transAxes)
    fig.suptitle(f'{run.name} | appended cases: green GT / blue original / red correction');fig.tight_layout(h_pad=2.2);fig.savefig(out/'F02_cases.png',dpi=160);plt.close(fig);guard.check()
    fp_lines=['## Budget-admitted FP decomposition','', '|Scope|Detector|partial|duplicate|no_small_overlap|','|---|---|---:|---:|---:|']
    for scope,comparison in [('pooled12',result['comparison'])]+[(f'held{k}',item['comparison']) for k,item in enumerate(result['held_groups'])]:
        for key in ['baseline','candidate']:
            counts=comparison[key+'_FP_types'];fp_lines.append('|'+scope+'|'+key+'|'+ '|'.join(str(counts[name]) for name in ['partial','duplicate','no_small_overlap'])+'|')
    (out/'README_analysis.md').write_text('''# E013 conditional learned selector

Question: can a seven-choice single-threshold policy trained on FIT8 improve exact budget-admitted detections while protecting E003? Source is saved models, OOF_predictions and evaluation from this Run; F00 shows FIT3/5/6 support and learned thresholds/abstention, F01 shows unchanged E003 versus pooled learned OOF at1FP/image,IoU=.5 and frozen retention/net/macro criterion. F02 shows at most six appended cases sorted by highest original score then lexical image/box/key; greenGT/blueoriginal/redcorrection, no source pixels. Empty selection is explicit. Exact numerical verdict is authoritative; no plot votes.

Primary requires old retention>=.95,netGT>=1,macrodelta>0. Learned selection is GT-free at prediction, but sites/outcomes and upstream models are reused/consumed. Not fresh-site generalisation, probability calibration, independent statistical confidence or oldfour-site282 verification. Positive FIT support3/5/6 constrains capacity; correlated location-deletion sensitivity is diagnostic only and never chooses the main threshold. Original-row preservation is separately verified and does not guarantee budget retention.

No further policy selection, U/joint computation or inference occurs in analysis. Preserve component support, safe abstention and old protection if primary misses. Follow the preregistered failure-to-repair map; no grid/L2 rescue or automatic training/retry. Fresh locations remain sealed.
'''+ '\n'.join(fp_lines)+'\n',encoding='utf8')
