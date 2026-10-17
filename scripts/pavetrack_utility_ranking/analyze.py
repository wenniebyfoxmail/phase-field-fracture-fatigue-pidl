"""Figures from saved outputs only; no policy or utility computation."""
import copy,importlib.util,json
from pathlib import Path
s=importlib.util.spec_from_file_location('e016_saved_plots',Path(__file__).resolve().parent.parent/'pavetrack_protected_selector/analyze.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)


def render(run,result,models,support,evaluation,guard):
    # Reuse unchanged exact-result/box plotting; no inherited threshold semantics survive.
    display=copy.deepcopy(models)
    for m in display:m['threshold']=m['mixture']
    old.render(run,result,display,support,evaluation,guard)
    locality=json.loads((run/'locality_audit.json').read_text());capacity=json.loads((run/'capacity_audit.json').read_text());plt=old.plt;xs=list(range(3));fig,axes=plt.subplots(1,3,figsize=(15,5))
    for shift,key,color,label in [(-.25,'positive_GT_before','#89939b','Original support'),(0,'positive_GT_after','#bc8b45','Positive intersection'),(.25,'fixed_admission_positive_GT','#477da7','Also x>=0')]:
        bars=axes[0].bar([x+shift for x in xs],[f[key] for f in locality['folds']],width=.25,color=color,label=label);axes[0].bar_label(bars,padding=3)
    axes[0].set_title('Own FIT positive GT retained');axes[0].set_ylabel('Distinct original-support GT');axes[0].legend(fontsize=8)
    for shift,values,color,label in [(-.19,[f['max_policy_positive_GT'] for f in capacity['folds']],'#477da7','Maximum fixed policy'),(.19,[f['chosen_policy']['selected_positive_GT'] for f in capacity['folds']],'#397b55','Learned policy')]:
        bars=axes[1].bar([x+shift for x in xs],values,width=.38,color=color,label=label);axes[1].bar_label(bars,padding=3)
    axes[1].set_title('Positive GT entering capacity');axes[1].legend(fontsize=8)
    top=max(1,max(f['positive_GT_before'] for f in locality['folds']))+1
    for ax in axes[:2]:ax.set_xticks(xs,['FIT0','FIT1','FIT2']);ax.set_ylim(0,top)
    axes[2].axis('off')
    for k,m in enumerate(models):axes[2].text(.02,.85-.28*k,f"fold{k}: alpha={m['mixture']}\n{'no correction' if m['abstained'] else 'active joint-utility choice'}",fontsize=10)
    fig.suptitle(f'{run.name} | six-choice utility-optimized capacity ranking\nRetention / membership are components; actual OOF benefit is F01');fig.tight_layout();fig.savefig(run/'analysis/F00_learning.png',dpi=160);plt.close(fig);guard.check()
    p=run/'analysis/README_analysis.md';fp=p.read_text().split('## Budget-admitted FP decomposition',1)[1]
    text="""# E016 conditional utility-optimized finite ranking

Question: can a FIT-only six-choice capacity ordering produce protected joint net gain? Evidence: exact saved models, policies, locality/capacity audits, frozen OOF predictions and evaluation from this Run. Read F00 (original / positive-intersection / fixed x>=0 support, maximum and learned capacity membership, learned alpha or abstention), F01 (E003 vs actual pooled12 OOF at1FP/image,IoU=.5, old retention,new/lost/net and macro delta), F02 (at most six actually appended cases, highest original score then lexical image/box/key; greenGT/blueoriginal/redcorrection, no pixels). No selected correction is explicitly shown as abstention. Figures do not choose a model or rescue a verdict.

q=(1-alpha)*tanh(x/2)+alpha*original-corrected IoU, alpha in0,.25,.5,.75,1 plus abstain. Fixed x>=0 replaces E015 threshold learning; no threshold-by-alpha grid. Strict positive axis intersection unchanged, no epsilon/area/IoU threshold scan. Rank does not replace original or corrected detection scores. Learn only one policy index by actual FIT joint netGT, retaining100% old FIT detections and positive macro delta; no singleton U sum or per-candidate U regression.

Primary: one pooled12 OOF comparison, old retention>=.95, netGT>=1, macrodelta>0. All12 sites and upstream models reused/consumed; not fresh-site generalisation, whole-pipeline independent validation, probability calibration, sample adequacy or oldfour-site282 verification. FIT support3/5/6 and correlated whole-location deletion sensitivity limit interpretation; diagnostics do not feed main selection. Support dropping to zero does not replace actual joint optimisation. Original-row preservation and detection-budget retention are separate.

Cross-figure interpretation: retain valid support/pool and safe-abstention progress, then distinguish capacity entry from actual budget-admitted benefit. Only saved OOF numerical result determines primary. If all FIT policies lack protected gain, stop this mixture family; no alpha refinement, sign reversal, cap expansion or intersection threshold scan. If capacity entry occurs without joint benefit, investigate budget/conflict information under a new frozen design. Fresh sites remain sealed. No new model, policy replay, U or metrics occur in plotting.

## Budget-admitted FP decomposition"""+fp
    text+='\n## Own FIT support and capacity (descriptive only)\n\n|FIT|Original|Positive intersection|Also x>=0|max policy entry|learned entry|learned actual joint netGT|\n|---|---:|---:|---:|---:|---:|---:|\n'
    for f,cap in zip(locality['folds'],capacity['folds'],strict=True):text+=f"|{f['fold']}|{f['positive_GT_before']}|{f['positive_GT_after']}|{f['fixed_admission_positive_GT']}|{cap['max_policy_positive_GT']}|{cap['chosen_policy']['selected_positive_GT']}|{cap['chosen_policy']['joint_net_GT']}|\n"
    p.write_text(text,encoding='utf8')
