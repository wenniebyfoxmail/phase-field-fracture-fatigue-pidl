"""Saved-value role-probe figures; no fitting or policy replay."""
import importlib.util,json
from pathlib import Path
s=importlib.util.spec_from_file_location('e018_saved_base',Path(__file__).resolve().parent.parent/'pavetrack_protected_selector/analyze.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)

def render(run,result,models,support,evaluation,guard):
    old.render(run,result,models,support,evaluation,guard)
    cap=json.loads((run/'capacity_audit.json').read_text());loc=json.loads((run/'locality_audit.json').read_text());plt=old.plt;fig,axes=plt.subplots(1,3,figsize=(15,5));xs=list(range(3))
    for dx,vals,color,label in [(-.2,[s['positive_GT_count'] for s in support],'#89939b','Available'),(0,[f['positive_GT_after'] for f in loc['folds']],'#bc8b45','Positive intersection'),(.2,[f['max_policy_positive_GT'] for f in cap['folds']],'#477da7','Max learned-score gate')]:
        bars=axes[0].bar([x+dx for x in xs],vals,width=.2,color=color,label=label);axes[0].bar_label(bars,padding=3)
    axes[0].set_title('Own FIT positive GT: pool to capacity');axes[0].set_xticks(xs,['FIT0','FIT1','FIT2']);axes[0].set_ylim(0,max(1,max(s['positive_GT_count'] for s in support))+1);axes[0].legend(fontsize=7)
    bars=axes[1].bar(xs,[f['chosen_policy']['selected_positive_GT'] for f in cap['folds']],color='#397b55');axes[1].bar_label(bars,padding=3);axes[1].set_xticks(xs,['FIT0','FIT1','FIT2']);axes[1].set_ylim(0,max(1,max(s['positive_GT_count'] for s in support))+1);axes[1].set_title('Chosen gate positive GT in capacity')
    axes[2].axis('off')
    for k,m in enumerate(models):axes[2].text(.02,.85-.28*k,f"fold{k}: gate={m['threshold']}\n7 coefficients; {'abstain' if m['abstained'] else 'active'}",fontsize=10)
    fig.suptitle(f'{run.name} | GT-free Q*N*A role probe\nCapacity membership is a component; actual protected OOF gain is F01');fig.tight_layout();fig.savefig(run/'analysis/F00_learning.png',dpi=160);plt.close(fig);guard.check()
    p=run/'analysis/README_analysis.md';fp=p.read_text().split('## Budget-admitted FP decomposition',1)[1]
    p.write_text('''# E018 low-capacity GT-free role probe

Question: can seven fixed ridge coefficients turn E017 GT-informed opportunity into actual protected OOF gain? Source: exact saved main models, FIT/OOF predictions, capacity/locality audits, freeze receipt and evaluation. Read F00 (own FIT support, strict positive intersection, maximum/chosen gate capacity), F01 (E003 vs actual pooled12 OOF old retention/new/lost/net/macro), F02 (at most six appended cases ordered by original score then image/box/key, green GT/blue original/red correction; explicit abstention if empty). No pixels or new computations of policies, metrics or U occur in analysis.

Q learns continuous localisation IoU, N valid novel reference, A cached safe budget admission; input is only corrected probability, original-corrected IoU, inverse nonparent overlap count and inverse original score pressure. Q*N*A is a ranking score, not a probability. Frozen original detection scores and prefix, cap1/image3/group, strict positive intersection and fixed x>=0 are unchanged; no intersection-threshold scan. Learned gate is one of0,1/16,1/8,1/4 or abstain, selected by own FIT actual joint protected net gain. All nine main heads numerically verified before predictions; model/OOF freeze precedes diagnostics and held evaluation.

Primary: same1FP/image and IoU=.5, pooled old retention>=.95, netGT>=1 and macrodelta>0. Saved numerical result determines verdict. FIT positiveGT3/5/6 remain sparse; dense labels and correlated candidates do not prove sample adequacy. Ten deletion diagnostics hold original FIT8 labels/context/bank and main gate fixed, remove a whole positive-support location from head-training rows only; not rebased FIT7 U, independent CV or confidence intervals. They never feed back into selection.

Allowed conclusion is conditional OOF selection on twelve consumed/reused upstream training sites. Blocked: fresh-site generalisation, full-pipeline independence, calibrated probability, sample sufficiency or GT-informed deployment. FIT8-to-held4 pressure shift is a limitation. E017+3/+4/+5 is overlapping GT-informed opportunity only and cannot be added or treated as a learned target. Preserve pool/capacity/safe-abstention progress even if primary fails. If all FIT models abstain, complete fixed OOF then stop this family; no L2/feature/gate/cap/intersection rescue. Fresh confirmation sites remain sealed. Storyline advance depends on actual OOF gain, not design or synthetic success.

## Budget-admitted FP decomposition'''+fp,encoding='utf8')
