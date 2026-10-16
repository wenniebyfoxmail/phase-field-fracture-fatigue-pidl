"""Plots from scored outputs only: no model, pixels or singleton calls."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

def render(run,result,reports,cases,guard):
    out=run/'analysis';out.mkdir(exist_ok=False)
    held=result['held_support'];xs=list(range(len(held)))
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for name,color in [('positive_pairs','#397b55'),('zero_pairs','#88939a'),('negative_pairs','#af5949')]:axes[0].plot(xs,[t[name] for t in held],marker='o',label=name,color=color)
    axes[0].set_xticks(xs,['group0','group1','group2']);axes[0].set_ylabel('Eligible candidate pairs');axes[0].legend(fontsize=8)
    axes[1].bar(xs,[t['positive_GT_count'] for t in held],color='#477da7');axes[1].axhline(1,color='#555',linestyle='--',label='>=1 unique GT/site per group')
    axes[1].set_xticks(xs,[f"g{i}: {len(t['positive_sites'])} sites" for i,t in enumerate(held)]);axes[1].set_ylabel('Distinct positive-U GT (full12 scope)');axes[1].legend(fontsize=8)
    fig.suptitle(f"{run.name} | frozen E003 training-evidence qualification\n{result['status']} — not learned detection");fig.tight_layout();fig.savefig(out/'F00_support.png',dpi=160);plt.close(fig);guard.check()
    j=result['joint'];fig,axes=plt.subplots(1,3,figsize=(12,4));axes[0].bar(['original','GT-informed'],[sum(x['true_positives'] for x in m['locations']) for m in [j['baseline'],j['candidate']]],color=['#89939b','#477da7']);axes[0].set_ylabel('Budget-admitted GT; 1 FP/image, IoU=.5')
    axes[1].bar(['retention B12'],[j['retention_B12'] or 0],color='#397b55');axes[1].axhline(.95,color='#555',linestyle='--');axes[1].set_ylim(0,1.05);axes[1].set_title('Unknown' if j['retention_B12'] is None else f"retained {j['retained_old']}, lost {j['lost_old']}")
    axes[2].bar(['new','lost','net'],[j['new_targets'],j['lost_old'],j['net_targets']],color=['#477da7','#af5949','#397b55']);axes[2].set_title(f"macro recall delta={j['delta']}")
    fig.suptitle(f'{run.name} | one GT-informed joint diagnostic (not model or upper bound)');fig.tight_layout();fig.savefig(out/'F01_budget.png',dpi=160);plt.close(fig);guard.check()
    chosen=cases['cases'];fig,axes=plt.subplots(2,3,figsize=(13,7));axes=axes.flatten()
    for ax,item in zip(axes,chosen):
        boxes=item['GT']+[item['original']['box_xyxy'],item['corrected']['box_xyxy']]
        for b in item['GT']:ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,edgecolor='#397b55'))
        for row,color in [(item['original'],'#477da7'),(item['corrected'],'#af5949')]:
            b=row['box_xyxy'];ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,edgecolor=color,linewidth=2))
        lo=min(b[0] for b in boxes);hi=max(b[2] for b in boxes);top=min(b[1] for b in boxes);bot=max(b[3] for b in boxes);pad=max(hi-lo,bot-top)*.1+1
        ax.set_xlim(lo-pad,hi+pad);ax.set_ylim(bot+pad,top-pad);ax.set_aspect('equal');ax.set_title(f"{item['role']} site {item['label']['location']}\nsource {item['label']['parent_id']} U={item['label']['U']}",fontsize=9)
    for ax in axes[len(chosen):]:ax.axis('off')
    if len(chosen)<6:axes[-1].text(.05,.5,'Missing roles: '+', '.join(cases['missing_roles']),transform=axes[-1].transAxes)
    fig.suptitle(f'{run.name} | fixed-rule coordinate cases; green GT / blue original / red correction');fig.tight_layout();fig.savefig(out/'F02_cases.png',dpi=160);plt.close(fig);guard.check()
    (out/'README_analysis.md').write_text('''# Stage B scored evidence

Read F00 for exact full12 positive/zero/negative candidate counts and deduplicated GT/site support; FIT8 contrast is in qualification.json. Primary L2 requires each group at least one positive-U GT/site and each FIT positive/nonpositive support. F01 compares E003 and one GT-informed joint selection on B12 at1FP/image,IoU=.5. It is potential,not learned performance or an upper bound; it does not verify the consumed four-site282 old hits. F02 uses highest original E003 score then lexical image/box/source-key,up to two sites per positive/harm/FP role. Missing roles explicit;green GT,blue original,red correction,no source pixels.

The encoder and head are unchanged; all original rows preserved. Positive utility is singleton newGT-lostGT-added-correctionFP,not geometric coverage or a sum of joint gains. Three source groups are support diagnostics,not end-to-end held generalisation. Pool/scoring/source identity and two head passes are fixed in receipts. No classifier/feature forward or U calculation is performed by analysis. Fresh confirmation/validation/reserve remain sealed.

Only a separately reviewed learning/selection experiment can establish actual protected net benefit. Preserve partial support; if joint budget harms old hits,repair set selection before fitting. No threshold rescue or automatic extra run is authorised.
''',encoding='utf8')
