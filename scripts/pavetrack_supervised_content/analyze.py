"""Presentation of saved E020 outputs only; no fitting or policy replay."""
import importlib.util,json
from pathlib import Path
s=importlib.util.spec_from_file_location('e020_saved_base',Path(__file__).resolve().parent.parent/'pavetrack_protected_selector/analyze.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)

def render(run,result,models,support,evaluation,guard):
    old.render(run,result,models,support,evaluation,guard)
    cap=json.loads((run/'capacity_audit.json').read_text());plt=old.plt;fig,axes=plt.subplots(1,3,figsize=(15,5));xs=list(range(3));top=max(1,max(s['positive_GT_count'] for s in support))+1
    for dx,vals,color,label in [(-.2,[s['positive_GT_count'] for s in support],'#89939b','Original support'),(0,[f['max_policy_positive_GT'] for f in cap['folds']],'#477da7','Maximum fixed gate'),(.2,[f['chosen_policy']['selected_positive_GT'] for f in cap['folds']],'#397b55','Chosen gate')]:
        bars=axes[0].bar([x+dx for x in xs],vals,width=.2,color=color,label=label);axes[0].bar_label(bars,padding=3)
    axes[0].set_title('Own FIT positive GT entering top-three capacity');axes[0].set_xticks(xs,['FIT0','FIT1','FIT2']);axes[0].set_ylim(0,top);axes[0].legend(fontsize=7)
    for dx,name,color in [(-.15,'Q','#477da7'),(.15,'N','#bc8b45')]:
        values=[m['content_model']['directions'][name]['constant_baseline_objective']-m['content_model']['directions'][name]['objective'] for m in models]
        bars=axes[1].bar([x+dx for x in xs],values,width=.3,color=color,label=name);axes[1].bar_label(bars,fmt='%.3f',padding=3)
    axes[1].set_xticks(xs,['FIT0','FIT1','FIT2']);axes[1].set_title('Direction training improvement vs constant');axes[1].set_ylabel('Weighted objective decrease (not OOF gain)');axes[1].legend();axes[2].axis('off')
    for k,m in enumerate(models):axes[2].text(.02,.85-.28*k,f"fold{k}: gate={m['threshold']}\n29 supervised coefficients (18 +11)",fontsize=10)
    fig.suptitle(f'{run.name} | Target-supervised directions in fixed sketch8\nFIT components only; actual protected OOF gain is F01');fig.tight_layout();fig.savefig(run/'analysis/F00_learning.png',dpi=160);plt.close(fig);guard.check()
    # Per-site variation uses saved pooled operating-prefix metrics, not rescoring.
    comp=result['comparison'];baseline={r['location']:r for r in result['baseline']['locations']};candidate={r['location']:r for r in comp['candidate']['locations']};sites=sorted(baseline,key=int)
    fig,axes=plt.subplots(2,2,figsize=(13,8));oldhits=comp['retained_old']+comp['lost_old']
    bars=axes[0,0].bar(['E003','OOF'],[oldhits,oldhits+comp['net_GT']],color=['#89939b','#477da7']);axes[0,0].bar_label(bars,padding=3);axes[0,0].set_title('Budget-admitted GT');axes[0,0].set_ylim(0,max(1,oldhits+max(0,comp['net_GT']))*1.15)
    bars=axes[0,1].bar(['Old retention'],[comp['retention'] or 0],color='#397b55');axes[0,1].axhline(.95,color='#555',linestyle='--');axes[0,1].set_ylim(0,1.15);axes[0,1].set_title(f"{comp['retained_old']}/{oldhits} retained")
    bars=axes[1,0].bar(['new','lost','net'],[comp['new_GT'],comp['lost_old'],comp['net_GT']],color=['#477da7','#af5949','#397b55']);axes[1,0].bar_label(bars,padding=3);axes[1,0].set_title(f"macro recall delta={comp['macro_delta']}")
    deltas=[candidate[site]['true_positives']-baseline[site]['true_positives'] for site in sites];bars=axes[1,1].bar(range(len(sites)),deltas,color='#477da7');axes[1,1].bar_label(bars,padding=3);axes[1,1].axhline(0,color='#555');axes[1,1].set_xticks(range(len(sites)),sites,rotation=45);axes[1,1].set_title('All sites: pooled-prefix TP difference vs E003')
    fig.suptitle(f'{run.name} | {result["status"]} | current-image real-road detection\n12 consumed/reused sites; conditional OOF; same 1FP/image, IoU=.5');fig.tight_layout();fig.savefig(run/'analysis/F01_detection.png',dpi=160);plt.close(fig);guard.check()
    originals={r['parent_id']:r for r in evaluation['baseline_rows']};added=evaluation['rows'][len(originals):];chosen=sorted(added,key=lambda r:(-originals[r['parent_id']]['score'],r['image_id'],tuple(r['box_xyxy']),r['parent_id']))[:6]
    fig,axes=plt.subplots(2,3,figsize=(13,7));axes=axes.flatten()
    for ax,row in zip(axes,chosen):
        original=originals[row['parent_id']];targets=evaluation['targets'][row['image_id']];boxes=targets+[original['box_xyxy'],row['box_xyxy']]
        for b,color in [(v,'#397b55') for v in targets]+[(original['box_xyxy'],'#477da7'),(row['box_xyxy'],'#af5949')]:ax.add_patch(old.Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,edgecolor=color,linewidth=2))
        lo=min(b[0] for b in boxes);hi=max(b[2] for b in boxes);top=min(b[1] for b in boxes);bottom=max(b[3] for b in boxes);pad=max(hi-lo,bottom-top)*.1+1;ax.set_xlim(lo-pad,hi+pad);ax.set_ylim(bottom+pad,top-pad);ax.set_aspect('equal');ax.set_title(f"site{row['reid']} source{row['parent_id']}",fontsize=9)
    for ax in axes[len(chosen):]:ax.axis('off')
    if not chosen:axes[0].text(.05,.5,'No corrections selected (explicit abstention)',transform=axes[0].transAxes)
    fig.suptitle(f'{run.name} | Coordinate schematics, no source pixels\nActually appended cases: green GT / blue original / red correction');fig.tight_layout(h_pad=2.2);fig.savefig(run/'analysis/F02_cases.png',dpi=160);plt.close(fig);guard.check()
    p=run/'analysis/README_analysis.md';fp=p.read_text().split('## Budget-admitted FP decomposition',1)[1]
    p.write_text("""# E020 target-supervised low-capacity content selection

Question: can Q/N-supervised content directions move beneficial corrections into unchanged top-three capacity and actual E003-protected OOF net gain? Sources: this Run's saved models, FIT/OOF predictions, capacity audit, freeze and evaluation. Read F00 for sparse support, capacity and direction training improvement versus intercept-only; the latter is a training component, never detection evidence. F01 shows actual E003 versus pooled12 OOF retention/new/lost/net/macro. F02 is at most six appended coordinate schematics (not source-image overlays), green GT/blue original/red correction, highest original-score then image/box/key; missing cases explicitly mean abstention. Exact tables and frozen criterion are authoritative.

Existing576-dimensional corrected-crop cache is mapped by fixed signed sketch8, with own-FIT-only GT-free mean/std. Q continuous localisation and N valid-new-reference labels each fit nine coefficients to choose a direction. Two bounded coordinates join unchanged four scalars in eleven-coefficient Q/N/A heads. Total29 supervised coefficients, plus16 GT-free statistics, not eleven total. Same-FIT two-stage label adaptation remains;3/5/6 actual useful GT are not replaced by dense rows. Projection orientation follows targets rather than E019 unsupervised total variance, but fixed sketch can discard information. This is neither E009589-parameter binary score attenuation nor E011 scalar-U regression; representation and supervised capacity change together, no single-factor causal conclusion.

Same original rows/boxes/probabilities/scores/order, positive-area intersection,x>=0,original duplicate IoU<=.7,accepted-only correction conflict>.5,cap1/image3/source-group,score and four fixed gates plus abstain. FIT active requires100% old retention,netGT>=1,macrodelta>0. Rank Q*N*A is not a calibrated probability or detector score. All three representations and nine main role heads verify before role prediction; full model and OOF freeze precede held evaluation and ten deletion diagnostics. Diagnostics refit BOTH supervised directions and role heads without the omitted site's training rows, fixing main GT-free sketch statistics/context/original FIT8 label semantics/bank/gate. Not complete leave-site-out CV or confidence intervals; never used to choose the main policy.

Primary: once pooled12 at1FP/image,IoU=.5,old retention>=95%,netGT>=1,macrodelta>0; baseline684 must verify. Allowed: conditional selector evidence on twelve consumed/upstream-reused sites. Blocked: fresh-site generalisation, full-pipeline independence, statistical sufficiency/calibration, or all-content impossibility. New confirmation/validation/reserve remain sealed. Components cannot rescue a negative verdict. All-abstain or no top-three entry stops this fixed sketch8/two-direction family, without dimension/seed/sign/L2/weight/gate/intersection/cap rescue. Capacity-without-gain redirects to saved budget roles; FIT-only gain without OOF transfer motivates separately qualified support expansion. No new fit/prediction/policy/U/metric in analysis.

## Budget-admitted FP decomposition"""+fp,encoding='utf8')
