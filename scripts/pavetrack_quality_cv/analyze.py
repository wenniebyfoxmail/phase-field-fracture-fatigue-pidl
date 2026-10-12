#!/usr/bin/env python3
"""Exact scored-output evidence renderer; no model fitting or score search."""
import argparse,csv,json,math
from pathlib import Path
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image
from run import box_iou,metrics,oracle_coverage,sha256_file

def exact_outcomes(e,field,metric):
 threshold=metric['global_score_threshold']
 if threshold is None:return [],{}
 unmatched={im:set(range(len(ts))) for im,ts in e['targets'].items()}
 outcomes=[];hits=defaultdict(set)
 for r in sorted(e['rows'],key=lambda r:(-r[field],r['reid'],r['image_id'],tuple(r['box_xyxy']))):
  if r[field]<threshold:break
  im=r['image_id'];available=unmatched[im]
  overlap,index=max(((box_iou(r['box_xyxy'],e['targets'][im][i]),i) for i in available),default=(0.,-1))
  hit=overlap>=.5
  if hit:available.remove(index);hits[im].add(index)
  outcomes.append((r,hit,index))
 if sum(int(hit) for _,hit,_ in outcomes)!=sum(r['true_positives'] for r in metric['locations']):raise ValueError('matching replay mismatch')
 return outcomes,hits

def cases(e):
 by=defaultdict(list)
 for r in e['rows']:by[r['image_id']].append(r)
 oldout,oldhits=exact_outcomes(e,'old_score',e['baseline']);newout,newhits=exact_outcomes(e,'score',e['candidate'])
 threshold=e['candidate']['global_score_threshold'];groups={'recovered_target':[],'covering_candidate_below_budget':[],'metric_false_positive':[]}
 for r,hit,index in newout:
  im=r['image_id']
  if hit and len(newhits[im])>len(oldhits.get(im,set())) and index not in oldhits.get(im,set()):groups['recovered_target'].append(r)
  if not hit:groups['metric_false_positive'].append(r)
 for im,targets in e['targets'].items():
  missed=set(range(len(targets)))-newhits.get(im,set())
  for r in by[im]:
   if threshold is not None and r['score']<threshold and any(box_iou(r['box_xyxy'],targets[i])>=.5 for i in missed):groups['covering_candidate_below_budget'].append(r)
 selected=[]
 for kind,rows in groups.items():
  used=set()
  for row in sorted(rows,key=lambda r:(-r['score'],r['image_id'],tuple(r['box_xyxy']))):
   loc=row['reid']
   if loc in used:continue
   used.add(loc);selected.append({'kind':kind,'image_id':row['image_id'],'row':row})
   if len(used)==2:break
 return selected

def main():
 p=argparse.ArgumentParser();p.add_argument('--evaluation',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--images',type=Path);p.add_argument('--expected-split',choices=['validation','test'],required=True);p.add_argument('--run-id',required=True);p.add_argument('--config',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);e=json.loads(a.evaluation.read_text(encoding='utf-8-sig'));cfg=json.loads(a.config.read_text());gate=cfg['primary_delta']
 if e['split']!=a.expected_split:raise ValueError('unexpected evaluation split')
 if e['config_sha256']!=sha256_file(a.config):raise ValueError('config identity mismatch')
 for metric,field in [('baseline','old_score'),('candidate','score')]:
  if e[metric]!=metrics(e['rows'],e['targets'],e['image_locations'],field):raise ValueError('metric mismatch')
 oracle=oracle_coverage(e['rows'],e['targets'],e['image_locations']);bm={r['location']:r for r in e['baseline']['locations']};cm={r['location']:r for r in e['candidate']['locations']};locations=[k for k in sorted(bm,key=int) if bm[k]['recall'] is not None];deltas=np.array([cm[k]['recall']-bm[k]['recall'] for k in locations]);rng=np.random.default_rng(cfg['seed']);boot=rng.choice(deltas,(10000,len(deltas)),replace=True).mean(1);interval=np.quantile(boot,[.025,.975]).tolist();delta=float(deltas.mean());
 if abs(delta-e['delta'])>1e-12:raise ValueError('authoritative delta mismatch')
 if a.expected_split=='test' and (e['primary_pass']!=(e['delta']>=gate) or e['oracle']!=oracle):raise ValueError('authoritative verdict/oracle mismatch')
 delta=e['delta'];macro_a=e['baseline']['macro_location_recall'];macro_b=e['candidate']['macro_location_recall']
 rows=[{'location':k,'images':bm[k]['images'],'targets':bm[k]['targets'],'baseline_recall':bm[k]['recall'],'candidate_recall':cm[k]['recall'],'delta':None if bm[k]['recall'] is None else cm[k]['recall']-bm[k]['recall'],'baseline_TP':bm[k]['true_positives'],'candidate_TP':cm[k]['true_positives'],'baseline_FP':bm[k]['false_positives'],'candidate_FP':cm[k]['false_positives']} for k in sorted(bm,key=int)]
 with (a.output/'location_metrics.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 selected=cases(e);(a.output/'montage_cases.json').write_text(json.dumps({'selection_rule':'Exact admitted-prefix greedy matching; strongest recovered target from images with TP gain, highest covering proposal below budget for unmatched targets, highest metric FP (including duplicates); two distinct locations per role; ties lexicographic image/box','cases':selected},indent=2)+'\n')
 summary={'protocol':e['protocol'],'run_id':a.run_id,'evaluation_sha256':sha256_file(a.evaluation),'split':e['split'],'baseline_macro_recall':macro_a,'candidate_macro_recall':macro_b,'delta':delta,'gate':gate,'primary_pass':e.get('primary_pass'),'development_gate_pass':delta>=cfg['development_delta_to_access_test'],'descriptive_location_bootstrap_95_interval':interval,'oracle_macro_recall':oracle['macro_location_recall'],'baseline_capture_ratio':macro_a/oracle['macro_location_recall'],'candidate_capture_ratio':macro_b/oracle['macro_location_recall'],'target_bearing_locations':len(locations),'uncertainty_scope':'small fixed selected holdout; not population confidence'};(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 fig,axes=plt.subplots(1,2,figsize=(12,4.8));x=np.arange(len(locations)+1);labels=locations+['macro'];old=[bm[k]['recall'] for k in locations]+[macro_a];new=[cm[k]['recall'] for k in locations]+[macro_b]
 axes[0].bar(x-.18,old,.36,color='#777777',label='Frozen E003 ranker');axes[0].bar(x+.18,new,.36,color='#1976D2',label='Valid-detection quality head');axes[0].set_xticks(x,labels);axes[0].set_ylim(0,1);axes[0].set_ylabel('Recall at 1 FP/image');axes[0].legend(frameon=False);axes[0].grid(axis='y',alpha=.2)
 axes[1].scatter(np.arange(len(deltas)),deltas,color='#1976D2');axes[1].axhline(gate,color='black',ls='--',label=f'Frozen +{gate:.2f} gate');axes[1].axhline(0,color='#777777',lw=.8);axes[1].scatter([len(deltas)],[delta],color='#009E73' if delta>=gate else '#D55E00',s=65);axes[1].vlines(len(deltas),interval[0],interval[1],color='#777777');axes[1].set_xticks(x,labels);axes[1].set_ylabel('Paired absolute recall improvement');axes[1].legend(frameon=False);axes[1].set_title(f'Macro delta {delta:+.4f}; descriptive location bootstrap');axes[1].grid(axis='y',alpha=.2)
 fig.suptitle(f"{a.run_id} — real-road, {e['split']}, current-image detection\nSame frozen tiled candidates; only ranking changes",fontweight='bold');fig.tight_layout();fig.savefig(a.output/'F01_decision.png',dpi=180);plt.close(fig)
 if a.images and selected:
  n=len(selected);fig,axes=plt.subplots(math.ceil(n/3),3,figsize=(16,math.ceil(n/3)*4.4),squeeze=False)
  for ax in axes.flat:ax.axis('off')
  for ax,case in zip(axes.flat,selected):
   im=Image.open(a.images/case['image_id']).convert('RGB');ax.imshow(im);r=case['row'];box=r['box_xyxy']
   for t in e['targets'][case['image_id']]:ax.add_patch(Rectangle((t[0],t[1]),t[2]-t[0],t[3]-t[1],fill=False,ec='#E41A1C',lw=2))
   color='#F5A623' if case['kind']=='covering_candidate_below_budget' else '#00A6D6';ax.add_patch(Rectangle((box[0],box[1]),box[2]-box[0],box[3]-box[1],fill=False,ec=color,lw=2));ax.set_title(f"{case['kind']} — location {r['reid']}\nnew={r['score']:.3f}; old={r['old_score']:.3f}",fontsize=10)
  fig.suptitle('Exact-score deterministic cases; red target, cyan admitted, orange below budget');fig.tight_layout();fig.savefig(a.output/'F02_error_montage.png',dpi=150);plt.close(fig)
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
