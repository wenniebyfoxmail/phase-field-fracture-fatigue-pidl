#!/usr/bin/env python3
"""Posthoc descriptive path counts;no fitting,rescoring or new policy evaluation."""
import argparse,json,importlib.util,csv
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
spec=importlib.util.spec_from_file_location('qpath',Path(__file__).with_name('qualification_analysis.py'));q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q);m=q.m
p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--lock',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();cfg=m.read(a.config);summary,_,_,policies=q.validated(a.run,cfg,a.config,a.lock);data=m.read(a.run/'train_bank.json');ys=[y for row,y in zip(data['bank'][::2],data['labels'],strict=True) if row['reid'] in cfg['qualification_locations']];out=[];tables=[]
for row in policies:
 replay,table,_,_=q.analysis.replay(row,cfg)
 for item in table:tables.append(dict(harm_limit=row['harm_limit'],**item))
 threshold=row['baseline']['global_score_threshold'];candidate_threshold=row['candidate']['global_score_threshold'];accepted={r['parent_id'] for r in row['rows'] if r.get('chosen_correction')};pairs=row['pair_rows'][::2]
 out.append(dict(harm_limit=row['harm_limit'],descriptive_location_bootstrap_95_interval=replay['descriptive_location_bootstrap_95_interval'],baseline_threshold=threshold,geometry_gain_pairs=sum(y['gain'] for y in ys),gain_pairs_above_baseline_threshold=None if threshold is None else sum(y['gain'] and r['score']>=threshold for r,y in zip(pairs,ys,strict=True)),accepted_geometry_gain_pairs=sum(y['gain'] and r['parent_id'] in accepted for r,y in zip(pairs,ys,strict=True)),accepted_gain_above_baseline_threshold=None if threshold is None else sum(y['gain'] and r['parent_id'] in accepted and r['score']>=threshold for r,y in zip(pairs,ys,strict=True)),accepted_corrections_in_candidate_prefix=None if candidate_threshold is None else sum(bool(r.get('chosen_correction')) and r['score']>=candidate_threshold for r in row['rows'])))
result=dict(scope='posthoc descriptive count audit of frozen four training policies;not an extra comparator or rescued claim',run_id=a.run.name,policies=out);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if tables:
 with (a.output.parent/'qualification/location_metrics.csv').open('w',newline='') as file:
  writer=csv.DictWriter(file,fieldnames=list(tables[0]),lineterminator='\n');writer.writeheader();writer.writerows(tables)
 ts=[r for r in tables if r['harm_limit']==max(cfg['harm_score_limits'])];names=[r['location'] for r in ts];x=np.arange(len(ts));fig,axes=plt.subplots(1,2,figsize=(11,4.5))
 axes[0].bar(x-.18,[r['baseline_recall'] for r in ts],.36,color='#777777',label='E003');axes[0].bar(x+.18,[r['candidate_recall'] for r in ts],.36,color='#1976D2',label='Fixed .1 paired rule');axes[0].set_ylabel('Recall at1FP/image');axes[0].set_ylim(0,1);axes[0].legend(frameon=False)
 axes[1].bar(x,[r['retention'] if r['retention'] is not None else np.nan for r in ts],color='#009E73');axes[1].axhline(.95,color='black',ls='--',label='Frozen .95 retention');axes[1].set_ylabel('Old target retention');axes[1].set_ylim(0,1.03);axes[1].legend(frameon=False)
 for panel in axes:panel.set_xticks(x,names);panel.grid(axis='y',alpha=.2)
 fig.suptitle(a.run.name+' — four train qualification locations;conditional shared encoder\nFixed most permissive .1 rule,not a new arm or selected best result');fig.tight_layout();fig.savefig(a.output.parent/'qualification/F01_qualification_locations.png',dpi=180);plt.close(fig)
