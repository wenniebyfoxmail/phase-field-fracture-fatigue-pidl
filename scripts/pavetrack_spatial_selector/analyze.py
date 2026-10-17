"""Saved detection values plus bounded, hash-verified actual-image case overlays."""
import importlib.util,json,hashlib
from pathlib import Path
import numpy as np
s=importlib.util.spec_from_file_location('e021_base_plot',Path(__file__).resolve().parent.parent/'pavetrack_protected_selector/analyze.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
s=importlib.util.spec_from_file_location('e021_case_pixels',Path(__file__).with_name('spatial.py'));spatial=importlib.util.module_from_spec(s);s.loader.exec_module(spatial)

def render(run,result,models,support,evaluation,guard,cases,buffers):
    old.render(run,result,models,support,evaluation,guard)
    cap=json.loads((run/'capacity_audit.json').read_text());features=json.loads((run/'spatial_features.json').read_text())['rows'];plt=old.plt;fig,axes=plt.subplots(1,3,figsize=(15,5));xs=list(range(3));top=max(1,max(v['positive_GT_count'] for v in support))+1
    for dx,values,color,label in [(-.2,[v['positive_GT_count'] for v in support],'#89939b','Original support'),(0,[f['max_policy_positive_GT'] for f in cap['folds']],'#477da7','Max fixed gate'),(.2,[f['chosen_policy']['selected_positive_GT'] for f in cap['folds']],'#397b55','Chosen gate')]:
        bars=axes[0].bar([x+dx for x in xs],values,width=.2,color=color,label=label);axes[0].bar_label(bars,padding=3)
    axes[0].set_ylim(0,top);axes[0].set_xticks(xs,['FIT0','FIT1','FIT2']);axes[0].set_title('Known positive GT entering top-three capacity');axes[0].legend(fontsize=7)
    counts=[sum(r['degenerate'] is None for r in features),sum(r['degenerate']=='zero_mass' for r in features),sum(r['degenerate']=='empty_context' for r in features)]
    bars=axes[1].bar(['nonzero','zero mass','empty'],counts,color=['#477da7','#89939b','#af5949']);axes[1].bar_label(bars,padding=3);axes[1].set_title('Fixed spatial measurement (not semantic validity)');axes[2].axis('off')
    for k,m in enumerate(models):axes[2].text(.02,.85-.28*k,f"fold{k}: gate={m['threshold']}\n11 supervised coefficients; no fitted representation",fontsize=9)
    fig.suptitle(f'{run.name} | New box-relative pixel information\nOwn FIT components; actual protected conditional OOF is F01');fig.tight_layout();fig.savefig(run/'analysis/F00_learning.png',dpi=160);plt.close(fig);guard.check()
    # Per-site variation uses saved pooled operating-prefix metrics, not rescoring.
    comp=result['comparison'];baseline={r['location']:r for r in result['baseline']['locations']};candidate={r['location']:r for r in comp['candidate']['locations']};sites=sorted(baseline,key=int)
    fig,axes=plt.subplots(2,2,figsize=(13,8));oldhits=comp['retained_old']+comp['lost_old']
    bars=axes[0,0].bar(['E003','OOF'],[oldhits,oldhits+comp['net_GT']],color=['#89939b','#477da7']);axes[0,0].bar_label(bars,padding=3);axes[0,0].set_title('Budget-admitted GT');axes[0,0].set_ylim(0,max(1,oldhits+max(0,comp['net_GT']))*1.15)
    bars=axes[0,1].bar(['Old retention'],[comp['retention'] or 0],color='#397b55');axes[0,1].axhline(.95,color='#555',linestyle='--');axes[0,1].set_ylim(0,1.15);axes[0,1].set_title(f"{comp['retained_old']}/{oldhits} retained")
    bars=axes[1,0].bar(['new','lost','net'],[comp['new_GT'],comp['lost_old'],comp['net_GT']],color=['#477da7','#af5949','#397b55']);axes[1,0].bar_label(bars,padding=3);axes[1,0].set_title(f"macro recall delta={comp['macro_delta']}")
    deltas=[candidate[site]['true_positives']-baseline[site]['true_positives'] for site in sites];bars=axes[1,1].bar(range(len(sites)),deltas,color='#477da7');axes[1,1].bar_label(bars,padding=3);axes[1,1].axhline(0,color='#555');axes[1,1].set_xticks(range(len(sites)),sites,rotation=45);axes[1,1].set_title('All sites: pooled-prefix TP difference vs E003')
    fig.suptitle(f'{run.name} | {result["status"]} | current-image real-road detection\n12 consumed/reused sites; conditional OOF; same 1FP/image, IoU=.5');fig.tight_layout();fig.savefig(run/'analysis/F01_detection.png',dpi=160);plt.close(fig);guard.check()

    if len(cases['cases'])!=len(buffers):raise ValueError('case buffer identity')
    fig,axes=plt.subplots(2,3,figsize=(15,9));axes=axes.flatten()
    for ax,row,raw in zip(axes,cases['cases'],buffers):
        if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('case source hash')
        image=spatial.decode(raw,row,guard,'case_image_decodes')
        try:ax.imshow(np.array(image))
        finally:image.close()
        boxes=row['GT']+[row['original']['box_xyxy'],row['corrected']['box_xyxy']];ctx=spatial.context_box(boxes,row['width'],row['height'])
        for b,color,style in [(v,'#51c878','--') for v in row['GT']]+[(row['original']['box_xyxy'],'#438de3','-'),(row['corrected']['box_xyxy'],'#ed6757',':')]:ax.add_patch(old.Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,edgecolor=color,linestyle=style,linewidth=2))
        ax.set_xlim(ctx[0],ctx[2]);ax.set_ylim(ctx[3],ctx[1]);C,D=row['descriptor']['values'];ax.set_title(f"site{row['location']} source{row['parent_id']} | C={C:.3f}, D={D:.3f}",fontsize=9)
    for ax in axes[len(buffers):]:ax.axis('off')
    if not buffers:axes[0].text(.02,.5,'No appended cases or known FIT opportunities',transform=axes[0].transAxes)
    kind='OOF APPENDED' if cases['kind']=='OOF_appended' else 'FIT OPPORTUNITIES — NOT SELECTED; NO OOF ADDITIONS'
    fig.suptitle(f'{run.name} | Actual source-image overlays | {kind}\nGreen dashed GT / blue original / red dotted correction; fixed score-ordered examples');fig.tight_layout();fig.savefig(run/'analysis/F02_cases.png',dpi=160);plt.close(fig);guard.check()
    p=run/'analysis/README_analysis.md';fp=p.read_text().split('## Budget-admitted FP decomposition',1)[1]
    p.write_text("""# E021 new box-relative spatial localisation information

Question: can explicit original/corrected-box spatial pixel evidence put useful corrections into unchanged top-three capacity and actual E003-protected OOF net gain? Read F00 for known FIT support/capacity and spatial degeneracy, F01 for actual E003 vs same-budget OOF retention/new/lost/net/macro and every site, F02 for actual image overlays. Evidence is exact saved spatial_features/capacity/models/OOF/evaluation/cases and the hash-matched source snapshots. No extra fitting, matching, policy replay or detection metric in analysis.

New information is fixed pixel-to-box geometry, not another576-pooled/PCA/sketch compressor. Every original/corrected pair uses one shared union plus25% context,128-square bilinear L grayscale,four one-pixel opposite-neighbour dark-line responses. C is corrected response mass fraction minus area fraction,D half the original-to-corrected change. No learned photometric statistics or representation;11 supervised Q/N/A coefficients. Dark response is a localisation hypothesis,not a crack mask or GT: shadows,seams,texture,light cracks,scale and short-box bias may mislead. Nonzero response/finite features/fit loss/partial rank progress cannot prove detection gain. Dense roles do not remove3/5/6 actual useful-GT scarcity.

Only835 exact pinned original-train image identities are read,bytes hashed before decode;held extraction fits nothing. Own-FIT heads and gate exclude current held GT. Same originals/scores,strict positive intersection,x>=0,cap1/image3/source-group,accepted-only conflicts and four fixed gates plus abstain. Q*N*A ranks additions,not probability or detector rescoring. All main heads verify before role prediction;model/OOF freeze precedes held evaluation,ten row-deletion diagnostics and case choice. Diagnostics fix deterministic descriptors/context/bank/labels/main gate;not independent CV or confidence intervals.

Primary remains once pooled12 at1FP/image,IoU=.5:old retention>=95%,netGT>=1,macrodelta>0,baseline684 verified. Conditional selector evidence only on12consumed/upstream-reused sites;no full-pipeline independence,fresh-site validation,calibration or statistical sufficiency. New confirmation/validation/reserve sites sealed. Stop this fixed grayscale C/D family if no top-three entry/all-abstain;no kernel/resolution/threshold/colour/L2/gate/intersection/cap search or R002. Capacity-without-gain redirects to saved budget roles;FIT-only gain requires separate support/validation study. Failure does not imply all localisation information is useless.

F02 selection: actual OOF appended rows first,else known positive-singleton FIT opportunities;unique source key,descending original E003 score then image/box/key,at most6. FIT opportunities are labelled NOT SELECTED,not OOF detections. GT comes from same pinned metadata only for post-freeze display. Window is all displayed boxes' union plus25%,clipped to source image. Each overlay uses the same verified source bytes,at most6 additional source reads/decodes;retained snapshots are hash-bound. Cases never choose a model or policy. Empty cases are explicit. Exact numerical verdict remains authoritative.

## Budget-admitted FP decomposition"""+fp,encoding='utf8')
