#!/usr/bin/env python3
"""Exact paired-coordinate analysis, without fitting or threshold selection."""
import argparse,json,csv,math
from pathlib import Path
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image
import importlib.util
_spec=importlib.util.spec_from_file_location('e005_analysis_runner',Path(__file__).with_name('run.py'));_run=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_run)
metrics,box_iou,oracle_coverage,sha256_file=_run.metrics,_run.box_iou,_run.oracle_coverage,_run.sha256_file

def outcomes(rows,targets,metric):
 threshold=metric['global_score_threshold'];available={im:set(range(len(ts))) for im,ts in targets.items()};result=[]
 if threshold is not None:
  for row in sorted(rows,key=lambda r:(-r['score'],r['reid'],r['image_id'],tuple(r['box_xyxy']))):
   if row['score']<threshold:break
   im=row['image_id'];overlap,index=max(((box_iou(row['box_xyxy'],targets[im][i]),i) for i in available[im]),default=(0.,-1));hit=overlap>=.5
   if hit:available[im].remove(index)
   result.append((row,hit,index))
 if len(result)!=metric['detections_used'] or sum(not h for _,h,_ in result)!=metric['false_positives'] or sum(h for _,h,_ in result)!=sum(v['true_positives'] for v in metric['locations']):raise ValueError('admitted-prefix replay mismatch')
 return result

def fp_counts(items,targets):
 counts={'partial':0,'duplicate':0,'no_small_overlap':0}
 for row,hit,index in items:
  if hit:continue
  value=max((box_iou(row['box_xyxy'],t) for t in targets[row['image_id']]),default=0.)
  counts['duplicate' if value>=.5 else 'partial' if value>=.05 else 'no_small_overlap']+=1
 return counts

def cases(e,oldout,newout):
 oldhits={(r['image_id'],i) for r,h,i in oldout if h};newhits={(r['image_id'],i) for r,h,i in newout if h};groups={'recovered_target':[],'lost_target':[],'metric_false_positive':[]}
 for row,hit,index in newout:
  if hit and (row['image_id'],index) not in oldhits:groups['recovered_target'].append(row)
  if not hit:groups['metric_false_positive'].append(row)
 for row,hit,index in oldout:
  if hit and (row['image_id'],index) not in newhits:groups['lost_target'].append(row)
 corrected={r['candidate_id']:r for r in e['all_corrected_rows']};old={r['candidate_id']:r for r in e['baseline_rows']};selected=[]
 for kind,rows in groups.items():
  used=set()
  for row in sorted(rows,key=lambda r:(-r['score'],r['image_id'],tuple(r['box_xyxy']),r['candidate_id'])):
   if row['reid'] in used:continue
   used.add(row['reid']);selected.append({'kind':kind,'image_id':row['image_id'],'candidate_id':row['candidate_id'],'original':old[row['candidate_id']],'corrected':corrected[row['candidate_id']]})
   if len(used)==2:break
 return selected

def summarize(e,cfg):
 for key,rows in [('baseline','baseline_rows'),('candidate','rows')]:
  if metrics(e[rows],e['targets'],e['image_locations'],'score')!=e[key]:raise ValueError('metric mismatch '+key)
 old={r['candidate_id']:r for r in e['baseline_rows']};corrected={r['candidate_id']:r for r in e['all_corrected_rows']}
 if len(old)!=len(e['baseline_rows']) or set(old)!=set(corrected):raise ValueError('candidate ID mismatch')
 for i,r in corrected.items():
  if r['score']!=old[i]['score'] or r['original_box_xyxy']!=old[i]['box_xyxy'] or r['image_id']!=old[i]['image_id']:raise ValueError('score/identity changed')
 if _run.suppress(e['baseline_rows'],cfg['refinement_nms_iou'])!=e['baseline_rows'] or _run.suppress(e['all_corrected_rows'],cfg['refinement_nms_iou'])!=e['rows'] or e['suppressed_count']!=len(corrected)-len(e['rows']):raise ValueError('NMS replay mismatch')
 if len({r['candidate_id'] for r in e['rows']})!=len(e['rows']) or any(r!=corrected[r['candidate_id']] for r in e['rows']):raise ValueError('post-NMS identity')
 bm={r['location']:r for r in e['baseline']['locations']};cm={r['location']:r for r in e['candidate']['locations']};locs=[k for k in sorted(bm,key=int) if bm[k]['recall'] is not None];delta=None;interval=None
 if locs:
  d=np.array([cm[k]['recall']-bm[k]['recall'] for k in locs]);delta=float(d.mean());rng=np.random.default_rng(cfg['seed']);interval=np.quantile(rng.choice(d,(10000,len(d)),replace=True).mean(1),[.025,.975]).tolist()
 if (delta is None)!=(e['delta'] is None) or (delta is not None and abs(delta-e['delta'])>1e-12):raise ValueError('delta replay')
 bo=oracle_coverage(e['baseline_rows'],e['targets'],e['image_locations']);co=oracle_coverage(e['rows'],e['targets'],e['image_locations'])
 if bo!=e['baseline_oracle'] or co!=e['oracle']:raise ValueError('oracle replay')
 oldout=outcomes(e['baseline_rows'],e['targets'],e['baseline']);newout=outcomes(e['rows'],e['targets'],e['candidate']);iou=[]
 for i,r in corrected.items():
  ts=e['targets'][r['image_id']];a=max((box_iou(old[i]['box_xyxy'],t) for t in ts),default=0.);b=max((box_iou(r['box_xyxy'],t) for t in ts),default=0.);iou.append(b-a)
 return {'baseline_macro_recall':e['baseline']['macro_location_recall'],'candidate_macro_recall':e['candidate']['macro_location_recall'],'delta':e['delta'],'gate':cfg['primary_delta'],'development_gate_pass':None if delta is None else delta>=cfg['development_delta_to_access_test'],'primary_pass':e['primary_pass'],'descriptive_location_bootstrap_95_interval':interval,'baseline_oracle':bo['macro_location_recall'],'candidate_oracle':co['macro_location_recall'],'baseline_fp_types':fp_counts(oldout,e['targets']),'candidate_fp_types':fp_counts(newout,e['targets']),'suppressed_count':e['suppressed_count'],'correction_flags':{key:sum(r['correction_flags'][key] for r in corrected.values()) for key in ['bounded','image_clipped','fallback']},'paired_max_iou_delta_mean':float(np.mean(iou)) if iou else None,'paired_max_iou_delta_median':float(np.median(iou)) if iou else None,'uncertainty_scope':'reused validation is descriptive; fixed selected fresh locations only if test'},bm,cm,locs,cases(e,oldout,newout)

def main():
 p=argparse.ArgumentParser();p.add_argument('--evaluation',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--run-id',required=True);p.add_argument('--expected-split',choices=['validation','test'],required=True);p.add_argument('--images',type=Path);a=p.parse_args();e=json.loads(a.evaluation.read_text());cfg=json.loads(a.config.read_text())
 if e['protocol']!=cfg['protocol'] or e['config_sha256']!=sha256_file(a.config) or e['split']!=a.expected_split:raise ValueError('analysis binding')
 summary,bm,cm,locs,selected=summarize(e,cfg);expected=None if e['delta'] is None else e['delta']>=cfg['primary_delta']
 if a.expected_split=='test' and e['primary_pass']!=expected:raise ValueError('test verdict mismatch')
 a.output.mkdir(parents=True,exist_ok=True);summary.update(protocol=e['protocol'],split=e['split'],run_id=a.run_id,evaluation_sha256=sha256_file(a.evaluation));(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(a.output/'montage_cases.json').write_text(json.dumps({'selection_rule':'highest frozen-score recovered TP, lost TP and candidate FP; two distinct locations per role; lexical image/box/candidate-ID ties','cases':selected},indent=2)+'\n')
 rows=[{'location':k,'images':bm[k]['images'],'targets':bm[k]['targets'],'baseline_recall':bm[k]['recall'],'candidate_recall':cm[k]['recall'],'baseline_TP':bm[k]['true_positives'],'candidate_TP':cm[k]['true_positives'],'baseline_FP':bm[k]['false_positives'],'candidate_FP':cm[k]['false_positives']} for k in sorted(bm,key=int)]
 with (a.output/'location_metrics.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 fig,axes=plt.subplots(1,2,figsize=(12,4.8));x=np.arange(len(locs)+1);labels=locs+['macro']
 if not locs:
  for ax in axes:ax.axis('off');ax.text(.5,.5,'INCONCLUSIVE: no target-bearing locations',ha='center',transform=ax.transAxes)
 else:
  old=[bm[k]['recall'] for k in locs]+[summary['baseline_macro_recall']];new=[cm[k]['recall'] for k in locs]+[summary['candidate_macro_recall']];axes[0].bar(x-.18,old,.36,color='#777777',label='Frozen E003');axes[0].bar(x+.18,new,.36,color='#1976D2',label='Box refinement');axes[0].set_ylim(0,1);axes[0].set_ylabel('Recall at 1 FP/image');axes[0].legend(frameon=False);axes[1].scatter(x,np.array(new)-np.array(old));axes[1].axhline(cfg['primary_delta'],ls='--',color='black',label='Frozen +0.05 gate');axes[1].axhline(0,color='#777777');axes[1].vlines(len(locs),*summary['descriptive_location_bootstrap_95_interval'],color='#777777');axes[1].set_ylabel('Paired absolute recall change');axes[1].legend(frameon=False)
  for ax in axes:ax.set_xticks(x,labels);ax.grid(axis='y',alpha=.2)
 fig.suptitle(f'{a.run_id}: real-road {e["split"]}, current-image detection\nFrozen E003 scores; coordinates corrected and fixed NMS replayed');fig.tight_layout();fig.savefig(a.output/'F01_decision.png',dpi=180);plt.close(fig)
 if a.images and selected:
  fig,axes=plt.subplots(math.ceil(len(selected)/3),3,figsize=(16,4.4*math.ceil(len(selected)/3)),squeeze=False)
  for ax in axes.flat:ax.axis('off')
  for ax,case in zip(axes.flat,selected):
   ax.imshow(Image.open(a.images/case['image_id']).convert('RGB'))
   for t in e['targets'][case['image_id']]:ax.add_patch(Rectangle((t[0],t[1]),t[2]-t[0],t[3]-t[1],fill=False,ec='#E41A1C',lw=2))
   for key,color in [('original','#F5A623'),('corrected','#00A6D6')]:
    b=case[key]['box_xyxy'];ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,ec=color,lw=2))
   ax.set_title(f'{case["kind"]}: location {case["original"]["reid"]}\nfrozen score {case["original"]["score"]:.3f}',fontsize=10)
  fig.suptitle('Deterministic exact-budget cases: red GT, orange original, cyan corrected');fig.tight_layout();fig.savefig(a.output/'F02_box_montage.png',dpi=150);plt.close(fig)
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
