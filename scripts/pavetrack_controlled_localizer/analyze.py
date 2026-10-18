"""Exact saved qualification, conditional detection, and actual-image overlays."""
import io,json,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Polygon

def render(run,result,qualifications,admitted,cases,buffers,g,c,spatial):
    out=run/'analysis';out.mkdir(exist_ok=False);domain='SYNTHETIC ENGINEERING TEST — NOT REAL ROAD' if 'synthetic' in run.name.lower() else 'current-image real-road; region-envelope reference'
    fig,grid=plt.subplots(2,2,figsize=(12,9));axes=grid[1];xs=np.arange(3)
    for j,color in [(0,'#477da7'),(1,'#397b55')]:
        results=[q['training_controls']['results'][j] for q in qualifications]
        grid[0,0].bar(xs+(j-.5)*.3,[v['Brier_gain'] for v in results],width=.28,color=color,label=f'control seed {j}')
        grid[0,1].bar(xs+(j-.5)*.3,[v['foreground_Dice_gain'] for v in results],width=.28,color=color,label=f'control seed {j}')
    for ax,title in zip(grid[0],['Training-only control Brier improvement','Training-only control foreground Dice improvement']):
        ax.axhline(1e-6,color='#555555',linestyle='--');ax.set_xticks(xs,[f'fold{k}' for k in range(3)]);ax.set_title(title);ax.legend(fontsize=8)
    grid[0,0].set_ylabel('best simple baseline minus model');grid[0,1].set_ylabel('model minus best trivial binary')
    for dx,values,color,label in [(-.16,[q['macro']['Brier'] for q in qualifications],'#477da7','CNN'),(.16,[min(q['macro'][k] for k in ['constant_Brier','zero_Brier','one_Brier']) for q in qualifications],'#89939b','best fixed constant')]:axes[0].bar(xs+dx,values,width=.3,label=label,color=color)
    for dx,values,color,label in [(-.16,[q['foreground_macro']['Dice'] if q['foreground_macro']['Dice'] is not None else np.nan for q in qualifications],'#477da7','CNN'),(.16,[np.nan if q['foreground_macro']['Dice'] is None else max(q['foreground_macro'][k] for k in ['constant_Dice','all_background_Dice','all_foreground_Dice']) for q in qualifications],'#89939b','best trivial binary')]:axes[1].bar(xs+dx,values,width=.3,label=label,color=color)
    # Individual qualification locations are reused units, not just fold averages.
    for k,q in enumerate(qualifications):
        if q['foreground_macro']['Dice'] is None:axes[1].text(k,.02,'NA: no foreground',ha='center',fontsize=7,rotation=90)
        for j,site in enumerate(q['sites']):
            offset=(j-.5)*.07
            axes[0].scatter(k-.16+offset,site['Brier'],s=20,color='#173f60',marker='x',zorder=4)
            axes[0].scatter(k+.16+offset,min(site[key] for key in ['constant_Brier','zero_Brier','one_Brier']),s=20,color='#444444',marker='x',zorder=4)
            if site['foreground']['Dice'] is not None:
                axes[1].scatter(k-.16+offset,site['foreground']['Dice'],s=20,color='#173f60',marker='x',zorder=4)
                axes[1].scatter(k+.16+offset,max(site['foreground'][key] for key in ['constant_Dice','all_background_Dice','all_foreground_Dice']),s=20,color='#444444',marker='x',zorder=4)
    for ax in axes:ax.set_xticks(xs,[f"fold{k}\n"+q['status'].replace('negative_control','control miss') for k,q in enumerate(qualifications)]);ax.legend(fontsize=8)
    axes[0].set_title('Own qualification2 regional Brier — lower better');axes[1].set_title('Reference-foreground context Dice — higher better')
    fig.suptitle(f'{run.name}\n{domain}\nTop: two fixed-seed train-only controls (no generalisation claim)\nBottom: train6 / qualification2; admitted={admitted}; 3 reused sites; x = individual site diagnostics',fontsize=9);fig.subplots_adjust(top=.78,bottom=.10,left=.11,right=.98,hspace=.48,wspace=.27);fig.savefig(out/'F00_qualification.png',dpi=140);plt.close(fig);g.check()
    if admitted:
        comp=result['comparison'];base={v['location']:v for v in result['baseline']['locations']};after={v['location']:v for v in comp['candidate']['locations']};sites=sorted(base,key=int);fig,axes=plt.subplots(1,4,figsize=(16,4));bars=axes[0].bar(['E003','conditional OOF'],[comp['retained_old']+comp['lost_old'],comp['retained_old']+comp['new_GT']],color=['#89939b','#477da7']);axes[0].bar_label(bars);axes[0].set_title(f"old {comp['retained_old']}/"+str(comp['retained_old']+comp['lost_old'])+f"; retention={comp['retention']}")
        bars=axes[2].bar(['new','lost','net'],[comp[k] for k in ['new_GT','lost_old','net_GT']],color=['#477da7','#af5949','#397b55']);axes[2].bar_label(bars);axes[2].set_title(f"macro change={comp['macro_delta']}");bars=axes[3].bar(range(len(sites)),[after[s]['true_positives']-base[s]['true_positives'] for s in sites]);axes[3].bar_label(bars);axes[3].set_xticks(range(len(sites)),sites,rotation=45);axes[3].set_title('Full12 sites, including rejectedfold E003')
        axes[1].bar(['old retention'],[comp['retention'] or 0],color='#397b55');axes[1].axhline(.95,color='#555555',linestyle='--');axes[1].set_ylim(0,1.1);axes[1].set_title('Frozen old retention >=.95')
        fig.suptitle(f'{run.name} | {domain}\nSame1FP/image IoU=.5; once pooled12 conditional OOF; primary={result["primary_pass"]}');fig.tight_layout();fig.savefig(out/'F01_detection.png',dpi=140);plt.close(fig);g.check()
    fig,axes=plt.subplots(6,2,figsize=(11,24),squeeze=False)
    for pair,row,raw in zip(axes,cases,buffers):
        if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('case buffer identity')
        image=spatial.decode(raw,row,g,'case_image_decodes')
        try:pixels=np.array(image)
        finally:image.close()
        x1,y1,x2,y2=row['context'];heat=np.asarray(row['heatmap'])
        for ax in pair:
            ax.imshow(pixels)
            for b,color,style in [(v,'#51c878','--') for v in row['GT']]+[(row['original'],'#438de3','-'),(row['corrected'],'#ed6757',':')]:ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,edgecolor=color,linestyle=style,linewidth=1.3))
            for polygon in row['GT_polygons']:ax.add_patch(Polygon(polygon,facecolor='#51c878',edgecolor='none',alpha=.18))
        pair[1].imshow(heat,extent=(x1,x2,y2,y1),alpha=.55,cmap='magma',vmin=0,vmax=1)
        for ax in pair:ax.set_xlim(x1,x2);ax.set_ylim(y2,y1);ax.set_aspect('auto');ax.tick_params(labelsize=7)
        pair[0].set_title(f"site{row['location']} key{row['parent_id']} fold{row['fold']}",fontsize=8);pair[1].set_title(row['scope']+' | saved32grid map',fontsize=8)
    for pair in axes[len(cases):]:
        for ax in pair:ax.axis('off')
    fig.suptitle(f'{run.name} | {domain}\nBlue original / red correction / green reference; fixed score-ordered cases; shared context, aspect stretched for display',fontsize=10);fig.tight_layout(rect=(0,0,1,.96));fig.savefig(out/'F02_cases.png',dpi=120);plt.close(fig);g.check()
    (out/'README_analysis.md').write_text(f'''# S01-E025 exact saved outputs

Domain: {domain}. Question: does an independently trained regional RGB model first beat simple baselines, then let useful corrections enter unchanged capacity and yield protected detection gain? F00 first shows both fixed-seed training-only control improvements, then ownFIT qualification2; control sample/seed success is not generalisation. Both controls and qualification must pass before connection. Qualification uses all models trained solely on fixed train6 and frozen before qualification. Three distinct reused qualification sites, not six independent sites. Brier lower and foreground-context Dice higher than fixed best trivial baselines must both improve >1e-6. Missing foreground support is inconclusive. Per-site/context/image metrics are in qualification_fold_*.json; qualification is a minimal capability condition, not reliable teacher or exact-width measurement.

Admitted folds: {admitted}. F01 exists only when at least one fold qualifies; it is the frozen full12-site conditional OOF including E003/abstain on rejectedfolds. No admitted folds means no detection metric, netGT null, no false zero-gain claim. Passing qualification never rescues the downstream primary. E003 scores/boxes/order,cap1/image3/group,positive intersection,abstention remain unchanged. All model/decision/OOF/map hashes freeze before outer references. No fresh-site independence; original upstream/sites have been reused.

F02 uses one global max6case branch, no extra model forward. All admission branches use the same highest original-score context per fold/qualification-site and saved qualification maps, maximum6; duplicate source images under distinct models are not independent examples. They are qualification-only, never selected OOF detection examples. F01 separately displays full12 detection outcomes when connected. GT polygons are region envelopes,not visible width. Shared context and display-only stretched aspect,common heat range0..1; no display changes alter metrics. See cases.json for exact rule/identities/fold/scope. Three simple baselines prevent all-background/no-localisation tricks; overall foreground/background imbalance and overlapping contexts remain.

Decision: {result['status']}. Primary: {result.get('primary_pass')}. Keep valid component gains separate; stop current fixed family on frozen failure,do not tune layer/loss/seed/threshold/cap/intersection or retry. Inputs, private labels, arrays and source images remain private archived artifacts, not public source. Analysis uses saved maps/metrics and already-approved case reads, no fitting or rescoring.
''')
