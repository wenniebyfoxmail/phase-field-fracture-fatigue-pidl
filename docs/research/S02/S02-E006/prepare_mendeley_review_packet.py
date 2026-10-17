"""Prepare an unsent, locally blinded repeat-measurement packet; no labels filled."""
from pathlib import Path
import argparse, csv, html, json, random
from functools import lru_cache
import numpy as np
import pandas as pd
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(base):
    out=base/'measurement_review_packet';out.mkdir(exist_ok=True)
    inv=pd.read_csv(base/'pt_frame_inventory.csv')
    raw=json.loads((base.parent/'mendeley_four_specimen_audit_20261013/archive_header_manifest.json').read_text())
    rawmap={(r['name'].split('/')[1],int(r['name'].rsplit('_',1)[1][:-4])):r['name'] for r in raw}
    items=[]
    for group in ['E_0Deg_20%_#1','E_0Deg_20%_#2','E_0Deg_20%_#3']:
        stages=sorted(inv[inv.group==group].stage.tolist())
        for i in np.linspace(0,len(stages)-1,5).round().astype(int):
            items.append(dict(group=group,stage=int(stages[i]),role='new_candidate'))
    labels=json.loads((base/'published_labels.json').read_text())
    for sheet,group in [('E_0_175_1(Section 5.1)','E_0Deg_17.5%_#1'),('C_15_20_1(Section 5.2)','C_15Deg_20%_#1')]:
        values=labels[sheet]
        for i in np.linspace(0,len(values)-1,5).round().astype(int):
            stage,cycle,label,_=values[i]
            items.append(dict(group=group,stage=int(stage),role='published_label_anchor',
                              reference_sheet=sheet,published_label=label))
    assert len({(r['group'],r['stage']) for r in items})==25
    originals=list(items)
    for group in sorted({r['group'] for r in originals}):
        r=sorted([r for r in originals if r['group']==group],key=lambda r:r['stage'])[2]
        items.append(dict(r,hidden_repeat=True))
    random.Random(20261017).shuffle(items)

    @lru_cache(maxsize=3)
    def load_pt(member):
        return torch.load(base/'pt_extracted'/member,map_location='cpu',weights_only=True)

    keys=[]
    for number,item in enumerate(items,1):
        ident=f'R{number:03d}'
        group,stage=item['group'],item['stage']
        row=inv[(inv.group==group)&(inv.stage==stage)].iloc[0]
        rawpath=base/'csv_extracted'/rawmap[(group,stage)]
        a=np.loadtxt(rawpath,skiprows=4)
        pt=load_pt(row.pt_member)[int(row.list_index)].numpy()[0,1]
        lo,hi=np.nanpercentile(np.r_[a[:,5],pt.ravel()],[1,99])
        fig,axes=plt.subplots(1,3,figsize=(12,4.2),layout='constrained')
        for ax in axes[:2]:
            ax.scatter(a[:,1],a[:,2],c=a[:,5],s=3,cmap='viridis',vmin=lo,vmax=hi,rasterized=True)
            ax.set(xlim=(-2,102),xlabel='Published CSV x / mm',ylabel='Published CSV y / mm')
        axes[0].set(ylim=(-6,108),title='Raw uy: full field')
        axes[1].set(ylim=(35,65),title='Raw uy: fixed central zoom')
        im=axes[2].imshow(pt,origin='lower',cmap='viridis',vmin=lo,vmax=hi)
        axes[2].set(title='Published PT channel 1',xlabel='Column / px',ylabel='Row / px')
        fig.colorbar(im,ax=axes[2],shrink=.7)
        fig.suptitle(ident+' | Current published fields; no automatic tip markers')
        fig.savefig(out/(ident+'.png'),dpi=125);plt.close(fig)
        keys.append(dict(item,item_id=ident,raw_file=str(rawpath),pt_member=row.pt_member,
                         pt_list_index=int(row.list_index)))
    (out/'INTERNAL_source_key.json').write_text(json.dumps(keys,indent=2))
    columns=['item_id','left_endpoint_x_mm','left_endpoint_y_mm','right_endpoint_x_mm',
             'right_endpoint_y_mm','unmeasurable_reason','confidence_note']
    with (out/'blank_measurements.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader()
        w.writerows(dict(item_id=k['item_id']) for k in keys)
    intro='''<h1>Mendeley: current-field measurement review</h1>
<p>25 unique source frames plus 5 hidden repeat presentations. No measurements have been filled.</p>
<p>Mark the visible displacement-discontinuity endpoints in published CSV coordinates.
Use the same projected-span convention throughout; mark an item unmeasurable when an endpoint is unclear.
Do not infer an invisible physical crack from a smooth field. The PT physical grid mapping is unknown.</p>
<p>Do not consult automatic candidates, author lengths or INTERNAL_source_key.json during the review.
Agreement/repeats assess this DIC-derived definition, not independent physical tip accuracy.</p>'''
    body=''.join(f'<h2>{k["item_id"]}</h2><img loading="lazy" src="{k["item_id"]}.png" style="max-width:100%">' for k in keys)
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Local measurement review</title>'+intro+body)
    print('Prepared local packet:25 unique frames +5 repeats; blank template; nothing sent')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base',type=Path);main(p.parse_args().base)
