#!/usr/bin/env python3
"""Exact frozen-score detection and retained-target evidence; no fitting or sweep."""
import argparse,json,csv,math,importlib.util
from pathlib import Path
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image
spec=importlib.util.spec_from_file_location('protected_analysis_runner',Path(__file__).with_name('run.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def fp_types(rows,targets,metric):
 threshold=metric['global_score_threshold'];available={im:set(range(len(ts))) for im,ts in targets.items()};counts={'partial':0,'duplicate':0,'no_small_overlap':0};tp=0;used=0
 if threshold is not None:
  for row in sorted(rows,key=lambda r:(-r['score'],str(r['reid']),r['image_id'],tuple(r['box_xyxy']))):
   if row['score']<threshold:break
   im=row['image_id'];iou,index=max(((m.box_iou(row['box_xyxy'],targets[im][i]),i) for i in available[im]),default=(0.,-1));used+=1
   if iou>=.5:available[im].remove(index);tp+=1
   else:
    value=max((m.box_iou(row['box_xyxy'],t) for t in targets[im]),default=0.);counts['duplicate' if value>=.5 else 'partial' if value>=.05 else 'no_small_overlap']+=1
 if used!=metric['detections_used'] or sum(counts.values())!=metric['false_positives'] or tp!=sum(r['true_positives'] for r in metric['locations']) or used!=tp+sum(counts.values()):raise ValueError('FP type replay count')
 return counts

def replay(e,cfg):
 original=e['baseline_rows'];rows=e['rows'];by={r['parent_id']:r for r in original}
 if len(rows)!=len(original) or len(by)!=len(original):raise ValueError('protected count/ID')
 for old,new in zip(original,rows,strict=True):
  if old['parent_id']!=new['parent_id'] or old['score']!=new['score'] or old['E003_score']!=new['E003_score']:raise ValueError('protected score/order')
 expected,choice=m.coordinate_choice(original,e['pair_rows'],e['pair_probabilities'],cfg)
 if expected!=rows or choice!=e['choice']:raise ValueError('coordinate policy replay')
 for metric,key in [('baseline','baseline_rows'),('candidate','rows')]:
  if e[metric]!=m.metrics(e[key],e['targets'],e['image_locations'],'score'):raise ValueError('metric replay')
 oldhits=m.admitted_targets(original,e['targets'],e['baseline']);newhits=m.admitted_targets(rows,e['targets'],e['candidate']);ret=None if not oldhits else len(oldhits&newhits)/len(oldhits);delta=None if e['baseline']['macro_location_recall'] is None else e['candidate']['macro_location_recall']-e['baseline']['macro_location_recall'];passed=None if ret is None or delta is None else ret>=cfg['minimum_retention'] and delta>=cfg['primary_delta']
 if ret!=e['retention'] or delta!=e['delta'] or passed!=e['protected_primary_pass'] or len(oldhits&newhits)!=e['retained_old_targets'] or len(oldhits-newhits)!=e['lost_old_targets'] or len(newhits-oldhits)!=e['new_detected_targets']:raise ValueError('protected criterion replay')
 if m.oracle_coverage(original,e['targets'],e['image_locations'])!=e['baseline_oracle'] or m.oracle_coverage(rows,e['targets'],e['image_locations'])!=e['oracle']:raise ValueError('oracle replay')
 bm={r['location']:r for r in e['baseline']['locations']};cm={r['location']:r for r in e['candidate']['locations']};locs=[k for k in sorted(bm,key=int) if bm[k]['recall'] is not None];interval=None
 if locs:
  ds=np.asarray([cm[k]['recall']-bm[k]['recall'] for k in locs]);rng=np.random.default_rng(cfg['seed']);interval=np.quantile(rng.choice(ds,(10000,len(ds)),replace=True).mean(1),[.025,.975]).tolist()
 table=[]
 for k in sorted(bm,key=int):
  oh={h for h in oldhits if e['image_locations'][h[0]]==k};nh={h for h in newhits if e['image_locations'][h[0]]==k}
  table.append({'location':k,'images':bm[k]['images'],'targets':bm[k]['targets'],'baseline_recall':bm[k]['recall'],'candidate_recall':cm[k]['recall'],'baseline_TP':bm[k]['true_positives'],'candidate_TP':cm[k]['true_positives'],'baseline_FP':bm[k]['false_positives'],'candidate_FP':cm[k]['false_positives'],'retained_old':len(oh&nh),'lost_old':len(oh-nh),'new_detected':len(nh-oh),'retention':None if not oh else len(oh&nh)/len(oh)})
 summary={k:e[k] for k in ['delta','retention','retained_old_targets','lost_old_targets','new_detected_targets','protected_primary_pass','choice']};summary.update(baseline_fp_types=fp_types(original,e['targets'],e['baseline']),candidate_fp_types=fp_types(rows,e['targets'],e['candidate']),baseline_macro_recall=e['baseline']['macro_location_recall'],candidate_macro_recall=e['candidate']['macro_location_recall'],gain_gate=cfg['primary_delta'],retention_gate=cfg['minimum_retention'],descriptive_location_bootstrap_95_interval=interval,baseline_oracle=e['baseline_oracle']['macro_location_recall'],candidate_oracle=e['oracle']['macro_location_recall'],uncertainty_scope='reused development descriptive; fixed selected locations only if fresh test')
 return summary,table,oldhits,newhits

def cases(e,oldhits,newhits):
 groups={'new_detected_target':[],'lost_old_target':[],'metric_false_positive':[]}
 for key,metric,desired,role in [('rows','candidate',newhits-oldhits,'new_detected_target'),('baseline_rows','baseline',oldhits-newhits,'lost_old_target')]:
  available={im:set(range(len(ts))) for im,ts in e['targets'].items()};threshold=e[metric]['global_score_threshold']
  if threshold is None:continue
  for row in sorted(e[key],key=lambda r:(-r['score'],str(r['reid']),r['image_id'],tuple(r['box_xyxy']))):
   if row['score']<threshold:break
   im=row['image_id'];iou,i=max(((m.box_iou(row['box_xyxy'],e['targets'][im][j]),j) for j in available[im]),default=(0.,-1));hit=iou>=.5
   if hit:
    available[im].remove(i)
    if (im,i) in desired:groups[role].append(row)
   elif key=='rows':groups['metric_false_positive'].append(row)
 selected=[];original={r['parent_id']:r for r in e['baseline_rows']};emitted={r['parent_id']:r for r in e['rows']}
 for role,rows in groups.items():
  used=set()
  for row in sorted(rows,key=lambda r:(-r['score'],r['image_id'],tuple(r['box_xyxy']),r['parent_id'])):
   if row['reid'] in used:continue
   used.add(row['reid']);selected.append({'kind':role,'image_id':row['image_id'],'parent_id':row['parent_id'],'original':original[row['parent_id']],'emitted':emitted[row['parent_id']]})
   if len(used)==2:break
 return selected

def main():
 p=argparse.ArgumentParser();p.add_argument('--evaluation',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--run-id',required=True);p.add_argument('--expected-split',choices=['validation','test'],required=True);p.add_argument('--images',type=Path);a=p.parse_args();e=m.read(a.evaluation);cfg=m.read(a.config)
 if e['protocol']!=cfg['protocol'] or e['config_sha256']!=m.sha256_file(a.config) or e['split']!=a.expected_split:raise ValueError('analysis lineage')
 summary,table,oldhits,newhits=replay(e,cfg);selected=cases(e,oldhits,newhits);a.output.mkdir(parents=True,exist_ok=True);summary.update(protocol=e['protocol'],run_id=a.run_id,split=e['split'],evaluation_sha256=m.sha256_file(a.evaluation));(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(a.output/'montage_cases.json').write_text(json.dumps({'selection_rule':'exact-budget new/lost GT and candidate FP, highest frozen E3score and lexical image/box/parent;two distinct locations per role','cases':selected},indent=2)+'\n')
 with (a.output/'location_metrics.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(table[0]),lineterminator='\n');w.writeheader();w.writerows(table)
 fig,axes=plt.subplots(1,3,figsize=(16,4.8));locs=[r['location'] for r in table if r['baseline_recall'] is not None];ts=[r for r in table if r['baseline_recall'] is not None];x=np.arange(len(ts)+1);names=locs+['macro']
 if e['delta'] is None:
  for ax in axes:ax.axis('off');ax.text(.5,.5,'INCONCLUSIVE\nNo target-bearing locations',ha='center',transform=ax.transAxes)
 else:
  old=[r['baseline_recall'] for r in ts]+[summary['baseline_macro_recall']];new=[r['candidate_recall'] for r in ts]+[summary['candidate_macro_recall']];axes[0].bar(x-.18,old,.36,color='#777777',label='Frozen E003');axes[0].bar(x+.18,new,.36,color='#1976D2',label='Paired coordinate choice');axes[0].set_ylim(0,1);axes[0].set_ylabel('Recall at 1 FP/image');axes[0].legend(frameon=False);axes[1].scatter(x,np.asarray(new)-np.asarray(old));axes[1].axhline(cfg['primary_delta'],color='black',ls='--',label='Frozen +.05 gain');axes[1].axhline(0,color='#777777');axes[1].vlines(len(ts),*summary['descriptive_location_bootstrap_95_interval'],color='#777777');axes[1].set_ylabel('Paired recall change');axes[1].legend(frameon=False)
  for ax in axes[:2]:ax.set_xticks(x,names);ax.grid(axis='y',alpha=.2)
  ret=[r['retention'] if r['retention'] is not None else np.nan for r in table]+[e['retention'] if e['retention'] is not None else np.nan];axes[2].bar(np.arange(len(ret)),ret,color='#009E73');axes[2].axhline(cfg['minimum_retention'],color='black',ls='--',label='Frozen .95 retention');axes[2].set_xticks(np.arange(len(ret)),[r['location'] for r in table]+['micro']);axes[2].set_ylim(0,1.02);axes[2].set_ylabel('Old detected target retention');axes[2].legend(frameon=False);axes[2].grid(axis='y',alpha=.2)
 fig.suptitle(f'{a.run_id} — real-road {e["split"]}, current-image detection\nFrozen scores and parent count; protected claim requires gain AND retention');fig.tight_layout();fig.savefig(a.output/'F01_protected_decision.png',dpi=180);plt.close(fig)
 if a.images and selected:
  fig,axes=plt.subplots(math.ceil(len(selected)/3),3,figsize=(16,4.4*math.ceil(len(selected)/3)),squeeze=False)
  for ax in axes.flat:ax.axis('off')
  for ax,case in zip(axes.flat,selected):
   ax.imshow(Image.open(a.images/case['image_id']).convert('RGB'))
   for t in e['targets'][case['image_id']]:ax.add_patch(Rectangle((t[0],t[1]),t[2]-t[0],t[3]-t[1],fill=False,ec='#E41A1C',lw=2))
   for key,color in [('original','#F5A623'),('emitted','#00A6D6')]:
    b=case[key]['box_xyxy'];ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,ec=color,lw=2))
   ax.set_title(f'{case["kind"]}: location {case["original"]["reid"]}\nE003 score {case["original"]["score"]:.3f}',fontsize=10)
  fig.suptitle('Deterministic exact-budget cases: red GT, orange original, cyan emitted');fig.tight_layout();fig.savefig(a.output/'F02_choice_montage.png',dpi=150);plt.close(fig)
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
