"""Decision plots for Stage A; coordinates only, no source pixels."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def render(run,guard):
    inv=load(run/'inventory.json');geo=load(run/'geometry.json');q=load(run/'qualification.json');cases=load(run/'cases.json')
    out=run/'analysis';out.mkdir(exist_ok=False);guard.check()
    fig,ax=plt.subplots(figsize=(10,4));ax.axis('off')
    ax.text(.02,.94,'S01-E012-R001 | training evidence only',fontsize=15,va='top')
    ax.text(.02,.76,f"{inv['images']} images / {inv['corrections']} existing OOF corrections / 12 training sites",fontsize=12)
    ax.text(.02,.56,'Corrected E003 scores: unavailable\nIncremental U / positive GT support: unavailable',fontsize=13,color='#ad5700')
    ax.text(.02,.26,'L2 distributed-support requirement: >=1 unique positive GT/site in each of 3 groups\nActual learned detection gain and old-hit retention: not measured',fontsize=11)
    ax.text(.02,.07,'Next: exact frozen-E003 rescore request; separate human approval required',fontsize=11)
    fig.tight_layout();fig.savefig(out/'F00_support.png',dpi=160);plt.close(fig);guard.check()
    groups=geo['by_source_group'];before=[g['original_GT'] for g in groups];after=[g['union_GT'] for g in groups]
    fig,ax=plt.subplots(figsize=(9,4));xs=list(range(len(groups)));ax.bar([i-.18 for i in xs],before,width=.36,label='original boxes',color='#88939c');ax.bar([i+.18 for i in xs],after,width=.36,label='original + OOF correction union',color='#477da8')
    ax.set_xticks(xs,[f"group {g['group']}\n+{g['new_GT']} GT / {g['new_sites']} sites" for g in groups]);ax.set_ylabel('Distinct covered GT (geometry only)');ax.set_title('S01-E012-R001 | existing training geometry coverage');ax.legend(fontsize=8)
    ax.set_ylim(0,max(after+[1])*1.3);fig.text(.5,.01,'Geometry union vs original boxes; not FP-budget detection or positive U',ha='center',fontsize=9);fig.tight_layout(rect=(0,.05,1,1));fig.savefig(out/'F01_geometry.png',dpi=160);plt.close(fig);guard.check()
    selected=cases['cases'];fig,axes=plt.subplots(1,3,figsize=(13,4))
    for ax,item in zip(axes,selected):
        for b in item['GT']: ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,edgecolor='#26834b',label='GT'))
        for name,color in [('original_box_xyxy','#477da8'),('corrected_box_xyxy','#b95238')]:
            b=item[name];ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,edgecolor=color,linewidth=2,label=name.split('_')[0]))
        all_boxes=item['GT']+[item['original_box_xyxy'],item['corrected_box_xyxy']];xmin=min(b[0] for b in all_boxes);xmax=max(b[2] for b in all_boxes);ymin=min(b[1] for b in all_boxes);ymax=max(b[3] for b in all_boxes);pad=max(xmax-xmin,ymax-ymin)*.1+1
        ax.set_xlim(xmin-pad,xmax+pad);ax.set_ylim(ymax+pad,ymin-pad);ax.set_aspect('equal');ax.set_title(f"site {item['location']}, source parent {item['source_parent_key']}\nU unavailable",fontsize=10)
        handles,labels=ax.get_legend_handles_labels();unique=dict(zip(labels,handles));ax.legend(unique.values(),unique.keys(),fontsize=7)
    for ax in axes[len(selected):]: ax.axis('off')
    axes[-1].text(.03,.6,'No qualified positive/negative U cases:\ncorrected scores unavailable',transform=axes[-1].transAxes,fontsize=10)
    fig.suptitle('S01-E012-R001 | fixed-rule coordinate cases (no pixels)');fig.tight_layout();fig.savefig(out/'F02_cases.png',dpi=160);plt.close(fig);guard.check()
    (out/'README_analysis.md').write_text('''# S01-E012 Stage A analysis

Question: do other twelve existing training sites provide qualified, distributed incremental-positive evidence? Sources are locked E007 OOF correction banks and allowlisted train metadata. No source images or classifier inference were used.

Read F00 for score/support missingness, F01 for unique GT geometry union vs original boxes, F02 for highest original-E003-score unavailable cases from at most two distinct sites. Useful/negative U roles are absent because corrected E003 scores are unavailable. Green GT, blue original, red correction; image coordinates, no pixels. Geometry coverage does not measure detection gain.

The frozen primary support standard is one positive-U unique GT/site in every source group plus positive/nonpositive examples in each FIT8 scope. It cannot be computed without verified corrected-crop scores. Missing values are not zeros. Original E003 rows remain fixed; no learned head, scored detector comparison, old-hit retention measurement or actual net benefit is claimed. The absence of scores is not evidence of the cause of E011 failure.

Next: use missing_scores_manifest.json to freeze a bounded E003 rescore source/forward-count/machine/budget approval version, then compute U under the unchanged budget before designing another head. Stage B requires independent code review and human approval. New confirmation and reserve sites remain sealed.
''',encoding='utf-8')
