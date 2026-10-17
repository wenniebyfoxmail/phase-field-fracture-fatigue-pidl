"""Saved detection values plus bounded, hash-verified actual-image case overlays."""
import importlib.util,json,hashlib
from pathlib import Path
import numpy as np
s=importlib.util.spec_from_file_location('e022_base_plot',Path(__file__).resolve().parent.parent/'pavetrack_protected_selector/analyze.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
s=importlib.util.spec_from_file_location('e022_case_pixels',Path(__file__).with_name('spatial.py'));spatial=importlib.util.module_from_spec(s);s.loader.exec_module(spatial)

def render(run,result,models,support,evaluation,guard,cases,buffers):
    old.render(run,result,models,support,evaluation,guard)
    domain='SYNTHETIC ENGINEERING TEST — NOT A REAL-ROAD RESULT' if 'synthetic' in run.name.lower() else 'current-image real-road detection'
    cap=json.loads((run/'capacity_audit.json').read_text());features=json.loads((run/'spatial_features.json').read_text())['rows'];plt=old.plt;fig,axes=plt.subplots(1,3,figsize=(15,5));xs=list(range(3));top=max(1,max(v['positive_GT_count'] for v in support))+1
    for dx,values,color,label in [(-.2,[v['positive_GT_count'] for v in support],'#89939b','Original support'),(0,[f['max_policy_positive_GT'] for f in cap['folds']],'#477da7','Max fixed gate'),(.2,[f['chosen_policy']['selected_positive_GT'] for f in cap['folds']],'#397b55','Chosen gate')]:
        bars=axes[0].bar([x+dx for x in xs],values,width=.2,color=color,label=label);axes[0].bar_label(bars,padding=3)
    axes[0].set_ylim(0,top);axes[0].set_xticks(xs,['FIT0','FIT1','FIT2']);axes[0].set_title('Known positive GT entering top-three capacity');axes[0].legend(fontsize=7)
    counts=[sum(r['degenerate'] is None for r in features),sum(r['degenerate']=='zero_mass' for r in features),sum(r['degenerate']=='empty_context' for r in features)]
    bars=axes[1].bar(['nonzero','zero mass','empty'],counts,color=['#477da7','#89939b','#af5949']);axes[1].bar_label(bars,padding=3);axes[1].set_title('Frozen class attribution (not segmentation GT)');axes[2].axis('off')
    for k,m in enumerate(models):axes[2].text(.02,.85-.28*k,f"fold{k}: gate={m['threshold']}\n11 supervised coefficients; no fitted representation",fontsize=9)
    fig.suptitle(f'{run.name} | Frozen E003 class-margin spatial information | {domain}\nOwn FIT components; actual protected conditional OOF is F01');fig.tight_layout();fig.savefig(run/'analysis/F00_learning.png',dpi=160);plt.close(fig);guard.check()
    # Per-site variation uses saved pooled operating-prefix metrics, not rescoring.
    comp=result['comparison'];baseline={r['location']:r for r in result['baseline']['locations']};candidate={r['location']:r for r in comp['candidate']['locations']};sites=sorted(baseline,key=int)
    fig,axes=plt.subplots(2,2,figsize=(13,8));oldhits=comp['retained_old']+comp['lost_old']
    bars=axes[0,0].bar(['E003','OOF'],[oldhits,oldhits+comp['net_GT']],color=['#89939b','#477da7']);axes[0,0].bar_label(bars,padding=3);axes[0,0].set_title('Budget-admitted GT');axes[0,0].set_ylim(0,max(1,oldhits+max(0,comp['net_GT']))*1.15)
    bars=axes[0,1].bar(['Old retention'],[comp['retention'] or 0],color='#397b55');axes[0,1].axhline(.95,color='#555',linestyle='--');axes[0,1].set_ylim(0,1.15);axes[0,1].set_title(f"{comp['retained_old']}/{oldhits} retained")
    bars=axes[1,0].bar(['new','lost','net'],[comp['new_GT'],comp['lost_old'],comp['net_GT']],color=['#477da7','#af5949','#397b55']);axes[1,0].bar_label(bars,padding=3);axes[1,0].set_title(f"macro recall delta={comp['macro_delta']}")
    deltas=[candidate[site]['true_positives']-baseline[site]['true_positives'] for site in sites];bars=axes[1,1].bar(range(len(sites)),deltas,color='#477da7');axes[1,1].bar_label(bars,padding=3);axes[1,1].axhline(0,color='#555');axes[1,1].set_xticks(range(len(sites)),sites,rotation=45);axes[1,1].set_title('All sites: pooled-prefix TP difference vs E003')
    fig.suptitle(f'{run.name} | {result["status"]} | {domain}\n12 consumed/reused sites; conditional OOF; same 1FP/image, IoU=.5');fig.tight_layout();fig.savefig(run/'analysis/F01_detection.png',dpi=160);plt.close(fig);guard.check()

    if len(cases['cases'])!=len(buffers):raise ValueError('case buffer identity')
    fig,axes=plt.subplots(6,2,figsize=(11,24),squeeze=False)
    for pair,row,raw in zip(axes,cases['cases'],buffers):
        if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('case source hash')
        image=spatial.decode(raw,row,guard,'case_image_decodes')
        try:pixels=np.array(image)
        finally:image.close()
        ctx=row['descriptor']['context'];x1,y1,x2,y2=ctx
        heat=np.asarray(row['descriptor']['heatmap']);vmax=max(1e-12,float(heat.max()))
        for ax in pair:
            ax.imshow(pixels)
            for b,color,style in [(v,'#51c878','--') for v in row['GT']]+[(row['original']['box_xyxy'],'#438de3','-'),(row['corrected']['box_xyxy'],'#ed6757',':')]:ax.add_patch(old.Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,edgecolor=color,linestyle=style,linewidth=1.5))
            ax.set_xlim(x1,x2);ax.set_ylim(y2,y1);ax.set_aspect('auto')
        pair[1].imshow(heat,extent=(x1,x2,y2,y1),interpolation='nearest',cmap='magma',vmin=0,vmax=vmax,alpha=.6)
        for x in np.linspace(x1,x2,8):pair[1].axvline(x,color='white',linewidth=.4,alpha=.5)
        for y in np.linspace(y1,y2,8):pair[1].axhline(y,color='white',linewidth=.4,alpha=.5)
        C,D=row['descriptor']['values'];pair[0].set_title(f"site{row['location']} source{row['parent_id']} | C_sem={C:.3f}, D_sem={D:.3f}",fontsize=8)
        pair[1].set_title('Same context | 7x7 attribution, NOT GT | display max='+f'{vmax:.3g}',fontsize=8)
    for pair in axes[len(buffers):]:
        for ax in pair:ax.axis('off')
    if not buffers:axes[0,0].text(.02,.5,'No appended cases or known FIT opportunities',transform=axes[0,0].transAxes)
    kind='OOF APPENDED' if cases['kind']=='OOF_appended' else 'FIT OPPORTUNITIES — NOT SELECTED; NO OOF ADDITIONS'
    fig.suptitle(f'{run.name} | {domain} | {kind}\nGreen dashed GT / blue original / red dotted correction; fixed score-ordered examples; context-cropped, aspect stretched for readability',fontsize=10)
    fig.tight_layout(rect=(0,0,1,.965));fig.savefig(run/'analysis/F02_cases.png',dpi=120);plt.close(fig);guard.check()
    p=run/'analysis/README_analysis.md';fp=p.read_text().split('## Budget-admitted FP decomposition',1)[1]
    p.write_text("""# E022 frozen E003 class-margin spatial attribution

Question: can frozen crack-vs-background class evidence put useful corrections into unchanged top-three capacity and actual E003-protected OOF net gain? F00 shows own-FIT support/capacity and zero/finite attribution, F01 actual baseline/OOF retention/new/lost/net/macro plus every site, F02 actual image overlays paired with SAME candidate's saved coarse7x7 map. Evidence is saved spatial_features/capacity/models/OOF/evaluation/cases and source snapshots. Analysis does no new model forward/gradient/fitting/matching/policy/metric.

New axis: frozen E003 pre-pooling spatial features, class-margin pooled-input derivative, positive weighted activation. This is a class-conditioned attribution hypothesis, NOT a crack segmentation mask or teacher. Global576cache cannot recover this spatial distribution; no pooled cache compressor or grayscale C/D tuning. Shadows/seams/background, upstream reuse, context shift, coarse7x7detail and3/5/6useful-GT scarcity remain. Nonzero heat/fit loss/partial rank gains cannot establish semantic validity or detection gain. All parameters frozen; true head-input derivative work recorded, no backbone backward or parameter gradient/update. CPU1/GPU1 extraction uses31156forward/derivative rows,835source+<=6case reads/decodes,39role solves,once frozenOOF;all runtime/memory budgets apply.

Exact box-cell area coverage integrates class evidence without changing geometry/eligibility. The two mass/area descriptors replace only the last two columns of the same11coefficient Q/N/A heads. Same old rows/boxes/probabilities/scores/order,strict positive intersection,1/image3/source-group,accepted-only conflict and four fixed gates plus abstain. Own-FIT active requires100%old retention,positive net and macro. All9main heads verify before role prediction;model and OOF freeze precede evaluation,10deletion diagnostics and case selection. Diagnostics fix semantic descriptors/context/original labels/bank/main gate;not independent CV or confidence intervals.

Primary: once pooled12,1FP/image,IoU=.5,baseline684,retention>=95%,netGT>=1,macrodelta>0. Conditional selector evidence on consumed/upstream-reused train sites,not pipeline independence/fresh-location or statistical confirmation. No confirmation/validation/reserve access/intersection scan. If no top-three/all-abstain,stop this fixed final-layer margin-Grad-CAM descriptor family without layer/target/gradient/smoothing/resolution/normalisation/L2/gate/cap rescue orR002. A future proposal needs qualified localisation evidence/support under a separate contract.

F02 cases: actual OOF appended first,else known singleton-positive FIT opportunities;unique source keys,descending original score,image/box/key,at most6. Selection is after freeze/evaluation,not heatmap-based. FIT examples explicitly NOT SELECTED and not OOF additions. Source bytes hashed before the sole case decode;all rendering uses saved7x7maps with no new forward. Both panels use the same shared union+25% context;GT outside context is clipped,not rematched. Aspect is stretched for visibility,not physical aspect ratio. Right map is nearest-cell overlay with visible7x7grid and a per-case display maximum (display only,not learner normalisation). Attribution is NOT GT. Exact numerical verdict remains authoritative.

## Budget-admitted FP decomposition"""+fp,encoding='utf8')
