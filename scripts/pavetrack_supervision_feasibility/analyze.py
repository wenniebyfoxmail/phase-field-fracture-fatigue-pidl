"""Read saved scope tables only. No new target, policy, U or metric calculations."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def render(run,result,cases,guard):
    out=run/'analysis';out.mkdir(exist_ok=False);xs=list(range(3));folds=result['folds'];fig,axes=plt.subplots(1,2,figsize=(12,4.8))
    for shift,key,color,label in [(-.27,'valid_localisation','#89939b','Valid reference'),(-.09,'positive_same_reference_gain','#bc8b45','Positive same-reference gain'),(.09,'novel_valid_reference','#477da7','Novel valid reference'),(.27,'cached_positive_utility','#397b55','Cached singleton new GT')]:
        field='distinct_cached_new_GT' if key=='cached_positive_utility' else 'distinct_reference_GT'
        bars=axes[0].bar([x+shift for x in xs],[f['supervision']['components'][key][field] for f in folds],width=.18,color=color,label=label);axes[0].bar_label(bars,padding=2)
    axes[0].set_ylabel('Distinct GT per own FIT (do not sum across FIT)');axes[0].set_xticks(xs,['FIT0','FIT1','FIT2']);axes[0].legend(fontsize=7);axes[0].set_title('Dense reference labels are not new independent positives')
    axes[1].axis('off')
    for k,f in enumerate(folds):
        cs=f['supervision']['components'];axes[1].text(.02,.88-.28*k,f"FIT{k}: records={f['supervision']['records']}\nvalid but FP={cs['valid_but_cached_FP']['candidates']}; valid below budget={cs['valid_but_not_budget_admitted']['candidates']}",fontsize=9)
    fig.suptitle(f'{run.name} | GT-informed supervision feasibility, no learned model');fig.tight_layout();fig.savefig(out/'F00_learning.png',dpi=160);plt.close(fig);guard.check()
    fig,axes=plt.subplots(1,3,figsize=(13,4.7))
    for shift,name,color,label in [(-.18,'validity_only','#89939b','A validity only'),(.18,'decomposed_novel_budget','#477da7','B decomposed oracle')]:
        policies=[next(p for p in f['oracles'] if p['name']==name) for f in folds]
        for ax,key in zip(axes,['net_GT','retention']):
            vals=[p['comparison'][key] or 0 for p in policies];bars=ax.bar([x+shift for x in xs],vals,width=.36,color=color,label=label);ax.bar_label(bars,padding=3)
        bars=axes[2].bar([x+shift for x in xs],[p['selected_positive_GT'] for p in policies],width=.36,color=color,label=label);axes[2].bar_label(bars,padding=3)
    for ax in axes:ax.set_xticks(xs,['FIT0','FIT1','FIT2'])
    axes[0].set_title('Actual joint net GT vs E003');axes[0].axhline(1,ls='--',color='#555');axes[1].set_title('Old-hit retention (undefined shown as0)');axes[1].axhline(1,ls='--',color='#555');axes[1].set_ylim(0,1.15);axes[2].set_title('Cached positive GT entering fixed cap');axes[2].legend(fontsize=7)
    fig.suptitle(f'{run.name} | FIT-only GT-informed A/B, not OOF or an upper bound\nB protected-opportunity scopes={result["passing_FITs"]}; feasibility only');fig.tight_layout();fig.savefig(out/'F01_detection.png',dpi=160);plt.close(fig);guard.check()
    fig,axs=plt.subplots(2,3,figsize=(13,7));axs=axs.flatten();chosen=cases['cases']
    for ax,case in zip(axs,chosen):
        boxes=case['targets']+[case['original_box'],case['corrected_box']]
        for b in case['targets']:ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,ec='#397b55'))
        for b,color in [(case['original_box'],'#477da7'),(case['corrected_box'],'#af5949')]:ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,ec=color,lw=2))
        low=min(b[0] for b in boxes);high=max(b[2] for b in boxes);top=min(b[1] for b in boxes);bottom=max(b[3] for b in boxes);pad=max(high-low,bottom-top)*.1+1;ax.set_xlim(low-pad,high+pad);ax.set_ylim(bottom+pad,top-pad);ax.set_aspect('equal');ax.set_title(f"FIT{case['fold']} site{case['location']} source{case['parent_id']}",fontsize=9)
    for ax in axs[len(chosen):]:ax.axis('off')
    if not chosen:axs[0].text(.05,.5,'No B corrections selected; keep E003',transform=axs[0].transAxes)
    fig.suptitle(f'{run.name} | fixed B-appended FIT cases; green GT, blue original, red correction\nCoordinate schematic; no source pixels or learned predictions');fig.tight_layout(h_pad=2.);fig.savefig(out/'F02_cases.png',dpi=160);plt.close(fig);guard.check()
    text='''# E017 decomposed-supervision feasibility

Question: can a fixed decomposition oracle identify a protected incremental opportunity inside the unchanged capacity? Read F00 for original-U support vs dense reference geometry and label-role contradictions, F01 for all three own-FIT A/B budget outcomes and positive membership, F02 for at most six actually B-appended coordinate cases. Exact source is saved result.json/FIT_audit_fold files, scope supervision/context tables and cases.json; no target, U, policy, model or detector metric is recomputed here.

A uses valid localisation and unchanged s0 ranking. B adds corrected-reference novelty relative to own E003 budget hits plus cached admitted/lost0/FP0 roles, then same-reference IoU gain ordering. Both use the same strict positive-coordinate intersection, fixed x>=0,1/image3/sourcegroup caps and unchanged original prefix/detection scores. Both are GT-informed diagnostics, not learned heads, new predictions, E009 reruns or mathematical upper bounds. B can fail because singleton admission and joint budget differ.

Primary is at least one own FIT B retaining100% old hits, netGT>=1 and macrodelta>0. Passing establishes only this fixed oracle opportunity; not predictor quality, adequate3/5/6 positive support, OOF effect or independent generalisation. F00 dense labels and cross-FIT repeated GT do not create independent new examples. Scope grouping is overlapping FIT, not independent folds; no held/full12 comparison occurs. Cases are highest original score then fold/image/box/key; repetitions across FIT are correlated. Empty selection is explicit; no source pixels.

Retain original-E003 detection as current policy. If B lacks protected gain stop this decomposition family without threshold/alpha/cap rescue; preserve support/role findings. If B has opportunity, only a separately frozen low-capacity GT-free learning test could establish learnability and actual OOF net benefit. Feature context is bank-relative score pressure, atomic tie mass and higher-score overlapping-original competition, never observed cutoff, H0, GT or cached role. Future held-bank shift remains a limitation. No fits, new singleton U, fresh sites or external access are authorized by these figures.

## Exact diagnostic outcomes

|FIT|Oracle|Old retained|New|Lost|Net|Macro delta|Correction prefix|Positive GT in cap|
|---|---|---:|---:|---:|---:|---:|---:|---:|
'''
    for f in folds:
        for o in f['oracles']:
            q=o['comparison'];text+=f"|{f['fold']}|{o['name']}|{q['retained_old']}|{q['new_GT']}|{q['lost_old']}|{q['net_GT']}|{q['macro_delta']}|{len(o['correction_prefix_roles'])}|{o['selected_positive_GT']}|\n"
    (out/'README_analysis.md').write_text(text,encoding='utf8')
