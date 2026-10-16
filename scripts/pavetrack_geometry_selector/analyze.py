"""Reuse frozen E013 plots; add own FIT membership without new comparisons."""
import importlib.util,json
from pathlib import Path
spec=importlib.util.spec_from_file_location('e014_old_analysis',Path(__file__).resolve().parent.parent/'pavetrack_protected_selector/analyze.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)

def render(run,result,models,support,evaluation,guard):
    old.render(run,result,models,support,evaluation,guard)
    audit=json.loads((run/'capacity_audit.json').read_text());folds=audit['folds'];plt=old.plt;xs=list(range(3))
    fig,axes=plt.subplots(1,3,figsize=(14,4.8));bars=axes[0].bar(xs,[s['positive_GT_count'] for s in support],color='#89939b');axes[0].bar_label(bars);axes[0].set_title('Available FIT positive GT');axes[0].set_ylabel('Distinct GT identities')
    for shift,values,color,label in [(-.19,[f['max_policy_positive_GT'] for f in folds],'#477da7','Maximum among fixed policies'),(.19,[f['chosen_policy']['selected_positive_GT'] for f in folds],'#397b55','Chosen policy')]:
        bars=axes[1].bar([x+shift for x in xs],values,width=.38,color=color,label=label);axes[1].bar_label(bars,padding=3)
    axes[1].set_title('FIT positive GT entering capacity');axes[1].set_ylim(0,max(1,max(s['positive_GT_count'] for s in support))+1);axes[1].legend(fontsize=8)
    for ax in axes[:2]:ax.set_xticks(xs,['FIT0','FIT1','FIT2'])
    axes[2].axis('off')
    for k,m in enumerate(models):axes[2].text(.02,.83-.25*k,f"fold{k}: tau={m['threshold']}\n{'no correction' if m['abstained'] else 'active'}",fontsize=11)
    fig.suptitle(f'{run.name} | geometry ordering; own FIT singleton membership\nMembership is descriptive; actual OOF net gain is shown in F01');fig.tight_layout();fig.savefig(run/'analysis/F00_learning.png',dpi=160);plt.close(fig);guard.check()
    p=run/'analysis/README_analysis.md';text=p.read_text().replace('E013','E014')
    text+='''\n## Single changed ranking and membership interpretation\n\nFixed d=1-IoU(original,correction) descending; unchanged classifier score s0 only breaks ties and remains the detection score. Large d is geometric change, not localisation quality. Disjoint boxes all tie at1. No geometry feature search or fitted geometry weight. Original eligibility, x thresholds, cap, abstention and protected FIT joint objective are unchanged.\n\nF00 replaces the reused support figure with available distinct positive GT, maximum selected positive GT among seven fixed policies, the final chosen policy membership, and learned thresholds. Maximum is a descriptive component, never a policy selector or an OOF claim. Counts join each own FIT's saved positive-singleton identities and already evaluated source_keys; no new U, policy replay or detection evaluation. Multiple candidate rows supporting the same GT are deduplicated. Capacity entry does not imply actual joint/new GT or protect old detections; F01 and saved result remain authoritative.\n'''
    for f in folds:text+=f"\nFIT{f['fold']}: support={f['available_positive_GT']}, maximum fixed-policy membership={f['max_policy_positive_GT']}, chosen membership={f['chosen_policy']['selected_positive_GT']}, chosen actual FIT netGT={f['chosen_policy']['joint_net_GT']}.\n"
    p.write_text(text)
