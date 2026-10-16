"""Saved-only positive retention, capacity entry and actual detection plots."""
import importlib.util,json
from pathlib import Path
spec=importlib.util.spec_from_file_location('e015_old_analysis',Path(__file__).resolve().parent.parent/'pavetrack_geometry_selector/analyze.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)

def render(run,result,models,support,evaluation,guard):
    old.render(run,result,models,support,evaluation,guard)
    audit=json.loads((run/'locality_audit.json').read_text());cap=json.loads((run/'capacity_audit.json').read_text());plt=old.old.plt;xs=list(range(3));fig,axes=plt.subplots(1,3,figsize=(15,5))
    for shift,key,color,label in [(-.19,'positive_GT_before','#89939b','Original support'),(.19,'positive_GT_after','#bc8b45','Retained by fixed gate')]:
        bars=axes[0].bar([x+shift for x in xs],[f[key] for f in audit['folds']],width=.38,color=color,label=label);axes[0].bar_label(bars,padding=3)
    axes[0].set_title('FIT positive GT before / after gate');axes[0].set_ylabel('Distinct original-support GT');axes[0].legend(fontsize=8)
    for shift,values,color,label in [(-.19,[f['max_policy_positive_GT'] for f in cap['folds']],'#477da7','Maximum fixed policy'),(.19,[f['chosen_policy']['selected_positive_GT'] for f in cap['folds']],'#397b55','Chosen policy')]:
        bars=axes[1].bar([x+shift for x in xs],values,width=.38,color=color,label=label);axes[1].bar_label(bars,padding=3)
    axes[1].set_title('Positive GT entering capacity');axes[1].legend(fontsize=8)
    top=max(1,max(f['positive_GT_before'] for f in audit['folds']))+1
    for ax in axes[:2]:ax.set_xticks(xs,['FIT0','FIT1','FIT2']);ax.set_ylim(0,top)
    axes[2].axis('off')
    for k,(m,f) in enumerate(zip(models,audit['folds'],strict=True)):axes[2].text(.02,.85-.28*k,f"fold{k}: tau={m['threshold']}\nremoved {f['removed']}/{f['base_eligible']} candidates",fontsize=10)
    fig.suptitle(f'{run.name} | fixed positive-area intersection only\nRetention and capacity membership are descriptive; actual OOF benefit is F01');fig.tight_layout();fig.savefig(run/'analysis/F00_learning.png',dpi=160);plt.close(fig);guard.check()
    p=run/'analysis/README_analysis.md';text=p.read_text().replace('E014','E015').replace('## Single changed ranking and membership interpretation','## Inherited E014 geometry ranking and membership interpretation')
    text+='''\n## Only new decision: strict positive intersection\n\nOriginal and corrected boxes must overlap with positive width on both axes. Edge/corner contact fails; any representable positive overlap passes. No epsilon, area threshold, IoU scan, ranking reversal or new weights. Base eligibility19384 and source identities stay unchanged; a separate positive_intersection field filters policy input before NMS/caps. Candidate-removal counts expose the locality prior's potential coverage cost.\n\nF00 shows original own-FIT singleton-positive support retained by the gate, maximum/chosen policy membership and removed-pool counts. Retained GT need not equal original support and do not force abstention or success. Counts are descriptive original-U support, not new U or a recomputed joint outcome. A remaining GT can be supported by another retained candidate even if one candidate is removed. Prediction files are frozen before these audits. Only actual saved FIT joint optimisation chooses thresholds; only saved OOF result determines the primary verdict.\n\n|Scope|Base eligible|Retained|Removed|Positive candidates before/after|Positive GT before/after|\n|---|---:|---:|---:|---|---|\n'''
    total=audit['all12_pool'];text+=f"|all12 GT-free|{total['base_eligible']}|{total['retained']}|{total['removed']}|not used|not used|\n"
    for f in audit['folds']:text+=f"|FIT{f['fold']}|{f['base_eligible']}|{f['retained']}|{f['removed']}|{f['positive_candidates_before']}/{f['positive_candidates_after']}|{f['positive_GT_before']}/{f['positive_GT_after']}|\n"
    p.write_text(text)
