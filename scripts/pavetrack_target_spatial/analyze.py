"""Render only saved outputs; common-scale evidence, no additional inference."""
import json,csv
from pathlib import Path
import numpy as np


def render(run):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    read=lambda n:json.loads((run/n).read_text(encoding='utf-8-sig'))
    scope,result=read('scope.json'),read('result.json')
    prefix='SYNTHETIC ENGINEERING ONLY | ' if scope.get('synthetic') else ''
    primary=result['combinations']['native_max_any']['sites'];sites=[r['location'] for r in primary]
    fig,ax=plt.subplots(1,2,figsize=(11,4));ax[0].bar(sites,[r['gain'] if r['gain'] is not None else np.nan for r in primary],color='#3178a6');ax[0].axhline(0,color='black',lw=.8);ax[0].set_ylabel('Envelope Dice gain vs strongest6 comparators')
    ax[1].bar(sites,[r['Dice'] if r['Dice'] is not None else np.nan for r in primary],color='#ce704c');ax[1].set_ylim(0,1);ax[1].set_ylabel('Absolute envelope Dice on shared R_any-FG')
    
    for j,row in enumerate(primary):
        if row['gain'] is None:
            for a in ax:a.text(j,.5,'inconclusive',ha='center',va='center',fontsize=8,rotation=90,transform=a.get_xaxis_transform())
    for a in ax:a.set_xlim(-.5,len(sites)-.5)
    if all(row['gain'] is None for row in primary):ax[0].set_ylim(-.05,.05)
    fig.suptitle(prefix+f'E028 primary native/max/any: {sum(p["qualified"] for p in result["pairs"])}/3 original pairs qualified\nPartial envelopes; no independent holdout, selector or OOF claim',fontsize=10);fig.tight_layout();fig.savefig(run/'F00_site_qualification.png',dpi=140);plt.close(fig)
    names=list(result['combinations']);fig,(ax,table_ax)=plt.subplots(2,1,figsize=(13,8),gridspec_kw={'height_ratios':[3,2]});x=np.arange(len(names))
    for j,site in enumerate(sites):
        values=[next(r for r in result['combinations'][n]['sites'] if r['location']==site)['gain'] for n in names]
        ax.bar(x+(j-1)*.24,[np.nan if v is None else v for v in values],width=.24,label=site)
    ax.axhline(0,color='black',lw=.8);ax.set_xticks(x,names,rotation=25,ha='right');ax.set_ylabel('Own-map/reference comparator Dice gain');ax.legend(title='Reused qualification site')
    support=read('support_summary.json')['rows'];fields=list(dict.fromkeys(r['field'] for r in support));table_ax.axis('off')
    values=[[next(f"{r['nonempty_contexts']}/{r['total_contexts']}" for r in support if r['field']==field and r['site']==site) for site in sites] for field in fields]
    tab=table_ax.table(cellText=values,rowLabels=fields,colLabels=sites,loc='center',cellLoc='center');tab.auto_set_font_size(False);tab.set_fontsize(9);tab.scale(.7,1.4);table_ax.set_title('Fixed.5 nonempty-context counts (reference rows are envelope presence)',fontsize=10)
    fig.suptitle(prefix+'Fixed8 combinations, SAME R_any-FG contexts and image/site weights\nNative changes resolution AND context; component comparisons do not replace the main candidate',fontsize=10);fig.tight_layout();fig.savefig(run/'F01_operator_comparison.png',dpi=140);plt.close(fig)
    with np.load(run/'projections.npz') as z:maps={k:z[k] for k in z.files}
    with np.load(run/'references.npz') as z:refs={k:z[k] for k in z.files}
    lookup={r['index']:j for j,r in enumerate(scope['rows'])}
    for site in sites:
        cases=[i for i in scope['cases'] if scope['rows'][lookup[i]]['location']==site]
        fig,axes=plt.subplots(len(cases),6,figsize=(15,4*len(cases)),squeeze=False)
        for row,i in enumerate(cases):
            j=lookup[i];rgb=np.load(run/f'cases/{i}_rgb.npy').transpose(1,2,0)
            panels=[rgb,refs['center'][j],refs['any'][j],maps['cached_max'][j],maps['native_max'][j],rgb]
            for col,a in enumerate(panels):
                axes[row,col].imshow(a,**({} if col in [0,5] else dict(cmap='magma',vmin=0,vmax=1)));axes[row,col].set_xticks([]);axes[row,col].set_yticks([])
                if col==5:
                    # Overlay binned support, not exact native crack-width contours.
                    axes[row,col].imshow(np.ma.masked_where(refs['any'][j]==0,refs['any'][j]),cmap='Greens',alpha=.25,vmin=0,vmax=1,extent=(-.5,rgb.shape[1]-.5,rgb.shape[0]-.5,-.5),interpolation='nearest')
                    field=maps['native_max'][j]
                    if field.min()<.5<=field.max():axes[row,col].contour(np.linspace(0,rgb.shape[1]-1,32),np.linspace(0,rgb.shape[0]-1,32),field,levels=[.5],colors=['#d55e00'],linewidths=.8)
            axes[row,0].set_ylabel(f'fixed row{i}',fontsize=8)
        for a,title in zip(axes[0],['Saved native RGB crop','Center envelope32','Any envelope32','Cached128 max32','Native max32','Green envelope / orange .5 support'],strict=True):a.set_title(title,fontsize=8)
        fig.suptitle(prefix+f'Site{site}: lexicographic first/last image, first context; fixed common0..1\nOverlay uses32 presence bins, not pixel width; outside envelope is unknown',fontsize=10);fig.tight_layout(rect=[0,0,1,.92]);fig.savefig(run/f'F02_cases_{site}.png',dpi=140);plt.close(fig)
    table=[]
    for name,c in result['combinations'].items():
        for row in c['sites']:table.append(dict(combination=name,**row))
    with (run/'site_decisions.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]),lineterminator='\n');w.writeheader();w.writerows(table)
    (run/'README_analysis.md').write_text(prefix+'''# E028 saved-output interpretation

Question: can a frozen external pixel-supervised representation yield image-specific partial-envelope spatial correspondence on the complete3 reused target qualification sites? Source: this Run's prediction freeze,338 native maps, cached context maps, saved projections/references and result. All predictions precede reference decoding; no fitting/selector/OOF here.

Read F00 first: per-site primary Dice advantage against each context's strongest of6 fixed comparators and absolute Dice; at least one ORIGINAL qualification pair must have both sites positive >1e-6. Missing support is inconclusive, not zero. F01 shows all8 predetermined input/pool/reference combinations on the SAME R_any-FG contexts, then equal context/image/site weights, with EACH combination's own reference and own-map mismatch/shift baselines. Changes in reference cannot change the evaluation sample composition. A non-primary component cannot rescue the frozen main candidate.

F02 shows all6 fixed cases (lexicographic first and last image of each site, first candidate context). RGB/native-max are saved model outputs. Common0..1 scale, green partial envelope and orange fixed.5 support contour. Native input changes both sampling resolution and visible context. Contours are32 support bins, not physical pixel width; outside-envelope activation is not a verified false crack. A good looking case is not site qualification or detection utility. All0 foreground counts, center/any support and full per-context/site scores remain in saved arrays/result, not inferred from screenshots.

Allowed: bounded development-site envelope presence correspondence, measured component gains and a decision on target qualification. Blocked: exhaustive crack pixel truth, physical width, generalisation to sealed/new sites, training stability, old-detection retention or OOF net benefit. Qualification pass only permits a separate frozen selector/utility design; no selector is connected here. E003/capacity/abstention/intersection rules and sealed locations are unchanged. Figures and synthetic engineering samples never constitute real performance evidence.
''')
