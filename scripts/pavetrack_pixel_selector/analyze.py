"""Saved detection values plus bounded, hash-verified actual-image case overlays."""
import importlib.util,json,hashlib
from pathlib import Path
import numpy as np
s=importlib.util.spec_from_file_location('e023_base_plot',Path(__file__).resolve().parent.parent/'pavetrack_protected_selector/analyze.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
s=importlib.util.spec_from_file_location('e023_case_pixels',Path(__file__).with_name('spatial.py'));spatial=importlib.util.module_from_spec(s);s.loader.exec_module(spatial)

def render(run,result,models,support,evaluation,guard,cases,buffers):
    old.render(run,result,models,support,evaluation,guard)
    domain='SYNTHETIC ENGINEERING TEST — NOT A REAL-ROAD RESULT' if 'synthetic' in run.name.lower() else 'current-image real-road detection'
    cap=json.loads((run/'capacity_audit.json').read_text());features=json.loads((run/'spatial_features.json').read_text())['rows'];plt=old.plt;fig,axes=plt.subplots(1,3,figsize=(15,5));xs=list(range(3));top=max(1,max(v['positive_GT_count'] for v in support))+1
    for dx,values,color,label in [(-.2,[v['positive_GT_count'] for v in support],'#89939b','Original support'),(0,[f['max_policy_positive_GT'] for f in cap['folds']],'#477da7','Max fixed gate'),(.2,[f['chosen_policy']['selected_positive_GT'] for f in cap['folds']],'#397b55','Chosen gate')]:
        bars=axes[0].bar([x+dx for x in xs],values,width=.2,color=color,label=label);axes[0].bar_label(bars,padding=3)
    axes[0].set_ylim(0,top);axes[0].set_xticks(xs,['FIT0','FIT1','FIT2']);axes[0].set_title('Known positive GT entering top-three capacity');axes[0].legend(fontsize=7)
    counts=[sum(r['degenerate'] is None for r in features),sum(r['degenerate']=='zero_mass' for r in features),sum(r['degenerate']=='empty_context' for r in features)]
    bars=axes[1].bar(['nonzero','zero mass','empty'],counts,color=['#477da7','#89939b','#af5949']);axes[1].bar_label(bars,padding=3);axes[1].set_title('OOF region map (not width GT)');axes[2].axis('off')
    for k,m in enumerate(models):axes[2].text(.02,.85-.28*k,f"fold{k}: gate={m['threshold']}\n41 pixel + 11 role coefficients",fontsize=9)
    fig.suptitle(f'{run.name} | Polygon-supervised spatial readout | {domain}\nOwn FIT components; actual protected conditional OOF is F01');fig.tight_layout();fig.savefig(run/'analysis/F00_learning.png',dpi=160);plt.close(fig);guard.check()
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
        for ax in pair:
            for poly in row.get('GT_polygons',[]):ax.add_patch(__import__('matplotlib').patches.Polygon(poly,closed=True,facecolor='#51c878',alpha=.12,edgecolor='#51c878'))
        pair[1].imshow(heat,extent=(x1,x2,y2,y1),interpolation='nearest',cmap='magma',vmin=0,vmax=vmax,alpha=.6)
        for ax in pair:ax.set_aspect('auto')
        for x in np.linspace(x1,x2,15):pair[1].axvline(x,color='white',linewidth=.4,alpha=.5)
        for y in np.linspace(y1,y2,15):pair[1].axhline(y,color='white',linewidth=.4,alpha=.5)
        C,D=row['descriptor']['values'];pair[0].set_title(f"site{row['location']} source{row['parent_id']} | C_sem={C:.3f}, D_sem={D:.3f}",fontsize=8)
        pair[1].set_title('Learned region map | fold'+str(row['pixel_model_fold'])+' | '+row['map_scope']+' | max='+f'{vmax:.3g}',fontsize=8)
    for pair in axes[len(buffers):]:
        for ax in pair:ax.axis('off')
    if not buffers:axes[0,0].text(.02,.5,'No appended cases or known FIT opportunities',transform=axes[0,0].transAxes)
    kind='OOF APPENDED' if cases['kind']=='OOF_appended' else 'FIT OPPORTUNITIES — NOT SELECTED; NO OOF ADDITIONS'
    fig.suptitle(f'{run.name} | {domain} | {kind}\nGreen dashed GT / blue original / red dotted correction; fixed score-ordered examples; context-cropped, aspect stretched for readability',fontsize=10)
    fig.tight_layout(rect=(0,0,1,.965));fig.savefig(run/'analysis/F02_cases.png',dpi=120);plt.close(fig);guard.check()
    p=run/'analysis/README_analysis.md';fp=p.read_text().split('## Budget-admitted FP decomposition',1)[1]
    component=json.loads((run/'pixel_evaluation.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(12,4));sites=component['locations'];xs=range(len(sites))
    axes[0].plot(xs,[r['Brier'] for r in sites],label='supervised region head');axes[0].plot(xs,[r['constant_Brier'] for r in sites],label='FIT foreground-rate constant');axes[0].set_title('Frozen held pixel Brier, lower is better');axes[0].legend(fontsize=7)
    axes[1].plot(xs,[r['Dice'] for r in sites],label='all contexts');axes[1].plot(xs,[np.nan if r['foreground_context_Dice'] is None else r['foreground_context_Dice'] for r in sites],label='reference-foreground contexts');axes[1].set_title('Fixed .5 Dice; empty/empty=1');axes[1].legend(fontsize=7)
    for ax in axes:ax.set_xticks(list(xs),[r['location'] for r in sites],rotation=45)
    fig.suptitle(run.name+' | '+domain+'\nDescriptive region supervision, not primary detection gain');fig.tight_layout();fig.savefig(run/'analysis/F03_pixel_component.png',dpi=140);plt.close(fig);guard.check()
    p.write_text("""# E023 polygon-region supervised spatial readout

F00 shows own-FIT useful support and original top-three admission plus OOF map degeneracy. F01 is the authoritative same-budget E003/OOF retained/new/lost/net/macro and all12locations. F02 is the same frozen score-ordered cases with actual pixels, original/GT/corrected boxes and saved14x14 learned region maps. F03 shows only post-freeze held region Brier vs own-FIT prevalence constant and Dice under the frozen averaging/empty rules. All values are saved outputs; no new inference, gradients, fitting, matching, policy or detection metric in analysis.

New supervision is the original human crack-region polygons, NOT exact crack width. Frozen E003 features[:6]40x14x14,41pixel coefficients plus11role coefficients per fold,own-FIT polygons only. Coarse labels may include background or omit unlabelled cracks.1million sampled cells are not independent GT or additional useful-positive targets;FIT useful3/5/6support remains. Pixel and role heads adapt on same FIT,optimistic FIT calibration remains;held excludes current labels from both fits. Reused upstream/train sites mean conditional selector OOF only,not complete-pipeline independence/new-location validation.

Same original rows/boxes/scores,positive-area intersection,1/image3/source-group,accepted-only conflict,four active fixed gates plus abstain. Primary is once pooled12,1FP/image,IoU=.5,baseline684,old>=95%,netGT>=1,macro>0. Pixel loss/maps/component Dice or partial rank movement never rescue the primary. If no capacity/all-abstain,stop the fixed intermediate-layer41coefficient pixel-ridge family without layer/sample/threshold/L2/intersection/cap search orR002. Fresh confirmation/validation/reserve and four old excluded locations stay sealed.

All3pixel and9role heads verify before role predictions;models/OOF/maps freeze precedes held pixel references or final evaluation. No deletion refit is presented as independent pipeline sensitivity. Pixel evaluation uses>=.5,empty/emptyDice1,FIT foreground-rate from unweighted16sample counts,Brier per context then equal contexts/image,images/location,12locations. Foreground-context subset is separately shown,empty groups null. No component chooses models/gates.

F02 is actual OOF additions else unique known FIT opportunities sorted original score,image/box/key,max6 after freeze/evaluation. FIT examples are explicitly NOT SELECTED/NO OOF ADDITIONS. FIT opportunity maps state their own-FIT model fold;OOF additions use held-fold model. No GT polygon enters map prediction. Both panels display SAME context with stretched aspect after all imshow;display max only,not model normalisation. No extra forward;case<=6source decodes. GT outside fixed context is clipped. Original fixed numerical verdict remains authoritative.

## Budget-admitted FP decomposition"""+fp,encoding='utf8')
