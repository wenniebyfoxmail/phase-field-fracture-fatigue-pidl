"""Exact saved outputs only: content/PCA diagnostics never select a model."""
import importlib.util,json
from pathlib import Path
s=importlib.util.spec_from_file_location('e019_saved_base',Path(__file__).resolve().parent.parent/'pavetrack_protected_selector/analyze.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)


def render(run,result,models,support,evaluation,guard):
    old.render(run,result,models,support,evaluation,guard)
    cap=json.loads((run/'capacity_audit.json').read_text());plt=old.plt;fig,axes=plt.subplots(1,3,figsize=(15,5));xs=list(range(3));top=max(1,max(s['positive_GT_count'] for s in support))+1
    for dx,vals,color,label in [(-.2,[s['positive_GT_count'] for s in support],'#89939b','Original support'),(0,[f['max_policy_positive_GT'] for f in cap['folds']],'#477da7','Maximum fixed gate'),(.2,[f['chosen_policy']['selected_positive_GT'] for f in cap['folds']],'#397b55','Chosen gate')]:
        bars=axes[0].bar([x+dx for x in xs],vals,width=.2,color=color,label=label);axes[0].bar_label(bars,padding=3)
    axes[0].set_title('Own FIT positive GT entering top-three capacity');axes[0].set_xticks(xs,['FIT0','FIT1','FIT2']);axes[0].set_ylim(0,top);axes[0].legend(fontsize=7)
    bars=axes[1].bar(xs,[m['content_model']['top2_variance_fraction'] for m in models],color='#bc8b45');axes[1].bar_label(bars,fmt='%.3f',padding=3);axes[1].set_xticks(xs,['FIT0','FIT1','FIT2']);axes[1].set_ylim(0,1.12);axes[1].set_title('FIT-only PCA2 variance (not detection gain)');axes[2].axis('off')
    for k,m in enumerate(models):axes[2].text(.02,.85-.28*k,f"fold{k}: gate={m['threshold']}\nPCA2 +11 supervised coefficients",fontsize=10)
    fig.suptitle(f'{run.name} | FIT-only content plus low-capacity role heads\nCapacity/variance are components; actual protected OOF gain is F01');fig.tight_layout();fig.savefig(run/'analysis/F00_learning.png',dpi=160);plt.close(fig);guard.check()
    p=run/'analysis/README_analysis.md';fp=p.read_text().split('## Budget-admitted FP decomposition',1)[1]
    p.write_text('''# E019 FIT-only compressed content selection

Question: can existing corrected-crop content move beneficial corrections into unchanged top-three source-group capacity and actual protected OOF gain? Evidence: exact saved main PCA/head models, six-column FIT/OOF predictions, capacity/locality audits, freeze receipt and evaluation. Read F00 for own FIT support to capacity and PCA variance; F01 for E003 vs actual pooled12 OOF retention/new/lost/net/macro; F02 for at most six actual appended cases ordered by original E003 score then image/box/key, green GT/blue original/red correction, no pixels. No appended cases is explicit abstention.

New information relative to E018 is existing E012-R004 corrected-crop576-dimensional content, compressed to two coordinates using only own FIT eligible rows and GT-free equal-location/image/row weights. Own FIT-only mean/std/covariance/eigenbasis/projection scales are frozen; held content never fits any statistic. Rank is fixed2; low-variance/degenerate components are recorded or zeroed rather than searched. Bounded PCA coordinates join pcorrected/parent-correctionIoU in Q, and nonparent-overlap context in N. A uses original-score pressure unchanged. Q continuous localisation, N valid novel reference and A cached safe admission targets remain decomposed. Eleven supervised coefficients excludes PCA's fitted means/scales/loadings; unsupervised fitting does not guarantee predictive content or remove upstream reuse. Not the E009589-parameter binary score attenuation or E011 scalar-U regression. No old-four qualification data is reopened.

Q*N*A ranks additions, not probability or detector rescoring. Original prefix/coordinates/probabilities/scores/order, strict positive intersection,x>=0,cap1/image3/source-group and accepted-only conflicts stay fixed. Four gates0,1/16,1/8,1/4 plus abstain are selected by own FIT actual joint protected net gain, not singleton sums. All main PCAs and nine heads verify before role prediction;3models including PCA and OOF freeze before diagnostics/evaluation. Ten deletion diagnostics retain original FIT8 PCA/context/labels/bank and main gate, removing ridge training rows only: label influence conditional on a fixed representation, not complete leave-site-out PCA, independent CV or confidence intervals. No diagnostic feedback.

Primary is one same1FP/image,IoU=.5 pooled12 OOF comparison: old retention>=.95,netGT>=1,macrodelta>0. Sparse actual positiveGT3/5/6 remain the limit; dense feature rows/PCA variance/lower training loss are not actual new detections, calibration or sample adequacy. E017 GT-informed+3/+4/+5 overlap and are not additive or learner effects. E018 historical comparisons do not isolate a single-factor causal content effect. Allowed conclusion is conditional selection on twelve consumed/reused upstream training sites; blocked fresh-site generalisation/full-pipeline independence. FIT8-to-held4 pressure shift remains. Fresh confirmation locations stay sealed.

Preserve pool/capacity/safe-abstention progress, then use actual OOF numerical verdict. If all FITs abstain, complete fixed OOF and stop this PCA2 head family; no rank/whitening/L2/gate/intersection/cap rescue. PCA may emphasise background and discard useful cues; a failure does not prove all content is useless. If capacity entry without gain, inspect saved budget roles; if FIT gain fails to transfer, use fixed-representation label influence and group results. No new PCA/fits/policy replay/U/metrics are performed by analysis. Exact cached source snapshots and receipts are authoritative.

## Budget-admitted FP decomposition'''+fp,encoding='utf8')
