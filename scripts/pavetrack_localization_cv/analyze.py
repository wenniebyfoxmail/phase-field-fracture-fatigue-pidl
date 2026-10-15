#!/usr/bin/env python3
"""E009 exact-cache analysis; box-coordinate schematics, never image pixels."""
import argparse
import csv
import hashlib
import importlib.util
import math
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

spec = importlib.util.spec_from_file_location('e009_runner_for_analysis',Path(__file__).with_name('run.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
spec = importlib.util.spec_from_file_location('e008_case_helpers',r.ROOT/'scripts/pavetrack_rescore_cv/analyze.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


def summarise(e, cfg):
    before=r.e8.admitted_targets(e['baseline_rows'],e['targets'],e['baseline'])
    after=r.e8.admitted_targets(e['rows'],e['targets'],e['candidate'])
    bm={v['location']:v for v in e['baseline']['locations']}
    cm={v['location']:v for v in e['candidate']['locations']}
    table=[]
    for loc in cfg['locations']:
        b={h for h in before if e['image_locations'][h[0]]==loc}
        a={h for h in after if e['image_locations'][h[0]]==loc}
        table.append(dict(location=loc,images=bm[loc]['images'],targets=bm[loc]['targets'],
            baseline_recall=bm[loc]['recall'],candidate_recall=cm[loc]['recall'],
            baseline_TP=bm[loc]['true_positives'],candidate_TP=cm[loc]['true_positives'],
            baseline_FP=bm[loc]['false_positives'],candidate_FP=cm[loc]['false_positives'],
            retained_old=len(a&b),lost_old=len(b-a),new_targets=len(a-b),retention=None if not b else len(a&b)/len(b)))
    cases=[c for c in prior.cases(e,before,after) if c['kind']!='corrected_only_false_positive']
    ds=[v['candidate_recall']-v['baseline_recall'] for v in table if v['baseline_recall'] is not None]
    interval=None if not ds else np.quantile(np.random.default_rng(cfg['seed']).choice(ds,(10000,len(ds)),replace=True).mean(1),[.025,.975]).tolist()
    summary={k:e[k] for k in ['delta','retention','net_targets','retained_old_targets','new_detected_targets','lost_old_targets','protected_primary_pass','choice','added_corrections_in_candidate_prefix']}
    summary.update(scope=cfg['scope'],baseline_macro_recall=e['baseline']['macro_location_recall'],
        candidate_macro_recall=e['candidate']['macro_location_recall'],
        baseline_fp_types=prior.old.fp_types(e['baseline_rows'],e['targets'],e['baseline']),
        candidate_fp_types=prior.old.fp_types(e['rows'],e['targets'],e['candidate']),
        descriptive_location_bootstrap_95_interval=interval,
        missing_case_roles=[k for k in ['new_detected_target','lost_old_target','metric_false_positive'] if not any(c['kind']==k for c in cases)])
    return summary,table,cases


def render(run, e, data, cfg):
    out=run/'analysis'
    out.mkdir(exist_ok=True)
    if e is None:
        (out/'README_analysis.md').write_text('# E009 stopped before fitting\n\nThe fixed annotation-informed feasibility policy failed. No learned prediction, learned comparison or detection figure exists. See input_audit.json and status.json. No fresh access.\n',encoding='utf-8')
        return
    summary,table,cases=summarise(e,cfg)
    r.write(out/'summary.json',summary)
    r.write(out/'schematic_cases.json',dict(rule='highest original E003 score per role; up to two distinct locations; fixed OOF policy only',cases=cases))
    with (out/'location_metrics.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    fig,axes=plt.subplots(1,3,figsize=(13,4))
    for ax,key,label,threshold in zip(axes,['delta','retention','net_targets'],['Macro recall change','Old target retention','Net detected targets'],[0.,cfg['minimum_retention'],cfg['minimum_net_targets']],strict=True):
        value=summary[key]
        ax.bar(['One fixed OOF policy'],[np.nan if value is None else value],color='#1976D2')
        ax.axhline(threshold,color='black',ls='--')
        ax.set_ylabel(label)
        ax.grid(axis='y',alpha=.2)
        if value is None:
            ax.text(0,.5,'Undefined',ha='center')
    axes[1].set_ylim(0,1.03)
    fig.suptitle(run.name+' | conditional reused-training crossfit')
    fig.tight_layout()
    fig.savefig(out/'F00_decision.png',dpi=170)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    x=np.arange(len(table))
    axes[0].bar(x-.18,[v['baseline_recall'] for v in table],.36,label='Frozen E003',color='#777777')
    axes[0].bar(x+.18,[v['candidate_recall'] for v in table],.36,label='E003 + quality-gated corrections',color='#1976D2')
    axes[0].set_ylabel('Recall at 1 FP/image')
    axes[0].legend(frameon=False,fontsize=8)
    axes[1].bar(x,[np.nan if v['retention'] is None else v['retention'] for v in table])
    axes[1].set_ylabel('Old target retention by location')
    for ax in axes:
        ax.set_ylim(0,1.03)
        ax.set_xticks(x,[v['location'] for v in table])
    fig.suptitle('Four held locations; primary retention is pooled, not per-location')
    fig.tight_layout()
    fig.savefig(out/'F01_locations.png',dpi=170)
    plt.close(fig)
    records={v['image_id']:v for v in data['records']}
    fig,axes=plt.subplots(max(1,math.ceil(len(cases)/3)),3,figsize=(14,max(1,math.ceil(len(cases)/3))*3.5),squeeze=False)
    for ax in axes.flat:
        ax.axis('off')
    for ax,case in zip(axes.flat,cases):
        rec=records[case['image_id']]
        ax.axis('on')
        ax.set_xlim(0,rec['width'])
        ax.set_ylim(rec['height'],0)
        ax.set_aspect('equal')
        for box in e['targets'][case['image_id']]:
            ax.add_patch(Rectangle((box[0],box[1]),box[2]-box[0],box[3]-box[1],fill=False,ec='#E41A1C',lw=2))
        for key,color in [('original','#F5A623'),('emitted','#00A6D6')]:
            box=case[key]['box_xyxy']
            ax.add_patch(Rectangle((box[0],box[1]),box[2]-box[0],box[3]-box[1],fill=False,ec=color,lw=1.5))
        emitted=case['emitted']['box_xyxy']
        iou=max((r.e8.box_iou(emitted,t) for t in e['targets'][case['image_id']]),default=0.)
        ax.set_title(case['kind']+' | '+case['original']['reid']+' | maxIoU '+format(iou,'.3f'),fontsize=9)
        ax.set_xlabel(case['image_id'],fontsize=6)
    fig.suptitle('Box-coordinate schematics ONLY: red GT / orange original / cyan emitted; no image pixels')
    fig.text(.01,.01,'Absent roles: '+(', '.join(summary['missing_case_roles']) or 'none'),fontsize=9)
    fig.tight_layout(rect=(0,.035,1,.96))
    fig.savefig(out/'F02_schematics.png',dpi=170)
    plt.close(fig)
    text='''# E009 cached localisation quality analysis

Question: does one fixed quality-gated correction policy add net detections at the E003 false-positive budget while retaining old detected targets?
Source: exact evaluation.json/OOF scores and four train-location heads in this Run, source/metadata/cache identities in their receipts. The original E003 rows are unchanged. The fixed label-oracle diagnostic is annotation-informed, never a learned result.
Read F00 primary margins, F01 all four held locations, F02 fixed-role coordinate schematics and exact case JSON. F02 uses pinned GT boxes and image dimensions only, not pixel evidence; no prior E008 images are relabelled. Missing roles are explicitly reported. Location bootstrap is descriptive.
This is conditional reused-training crossfit. The shared E003 encoder saw all training locations; these locations/outcomes were previously viewed. It does not establish independent-location, development, forecasting or mechanics performance. Valid duplicates remain positive training labels, so no learned duplicate-removal claim.
'''
    text+='\nExact primary outcome: '+str(summary['protected_primary_pass'])+'; macro change '+str(summary['delta'])+'; old retention '+str(summary['retention'])+'; netTP '+str(summary['net_targets'])+'.\n'
    text+='If positive, only prepare the next independent study. If negative, retain E003 and follow the frozen partial/duplicate FP repair map; no within-run changes or fresh access.\n'
    (out/'README_analysis.md').write_text(text,encoding='utf-8')
    names=sorted(p.name for p in out.iterdir() if p.is_file() and p.name!='analysis_receipt.json')
    r.write(out/'analysis_receipt.json',dict(evaluation_sha256=r.sha(run/'evaluation.json'),
            files={n:r.sha(out/n) for n in names},pixel_reads=0))


def main():
    parser=argparse.ArgumentParser()
    for name in ['config','lock','cache','metadata','run']:
        parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    cfg,lock=r.verify_source(a.config,a.lock)
    e,data=r.verify(a,cfg,lock)
    sys.addaudithook(r.pixel_guard)
    render(a.run,e,data,cfg)


if __name__=='__main__':
    main()
