#!/usr/bin/env python3
"""Exact additive-bank metrics and original-target retention;no fitting/search."""
import argparse,json,csv,math,importlib.util
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image
spec=importlib.util.spec_from_file_location('rescore_analysis_runner',Path(__file__).with_name('run.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
spec2=importlib.util.spec_from_file_location('fp_dependency',m.ROOT/'scripts/pavetrack_protected_cv/analyze.py');old=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(old)
def replay(e,cfg,qualification):
 rows,choice=m.added_bank(e['baseline_rows'],e['pair_rows'],e['corrected_probabilities'],cfg,e['score_ratio'])
 if rows!=e['rows'] or choice!=e['choice']:raise ValueError('admission replay')
 for key,rowkey in [('baseline','baseline_rows'),('candidate','rows')]:
  if e[key]!=m.metrics(e[rowkey],e['targets'],e['image_locations'],'score'):raise ValueError('metric replay')
 before=m.admitted_targets(e['baseline_rows'],e['targets'],e['baseline']);after=m.admitted_targets(e['rows'],e['targets'],e['candidate']);ret=None if not before else len(before&after)/len(before);delta=None if e['baseline']['macro_location_recall'] is None else e['candidate']['macro_location_recall']-e['baseline']['macro_location_recall'];net=len(after)-len(before);primary=None if ret is None or delta is None else ret>=cfg['minimum_retention'] and delta>=cfg['primary_delta'] and net>=cfg['minimum_net_targets'];qual=False if ret is None or delta is None else ret>=cfg['minimum_retention'] and delta>cfg['qualification_minimum_delta'] and net>=cfg['minimum_net_targets']
 if any(e[k]!=v for k,v in dict(retention=ret,delta=delta,net_targets=net,protected_primary_pass=primary,qualified=qual,retained_old_targets=len(before&after),lost_old_targets=len(before-after),new_detected_targets=len(after-before)).items()):raise ValueError('protected gain replay')
 if e['baseline_oracle']!=m.oracle_coverage(e['baseline_rows'],e['targets'],e['image_locations']) or e['oracle']!=m.oracle_coverage(e['rows'],e['targets'],e['image_locations']):raise ValueError('oracle replay')
 table=[]
 bm={r['location']:r for r in e['baseline']['locations']};cm={r['location']:r for r in e['candidate']['locations']}
 for loc in sorted(bm,key=int):
  b={h for h in before if e['image_locations'][h[0]]==loc};a={h for h in after if e['image_locations'][h[0]]==loc}
  table.append(dict(score_ratio=e['score_ratio'],location=loc,images=bm[loc]['images'],targets=bm[loc]['targets'],baseline_recall=bm[loc]['recall'],candidate_recall=cm[loc]['recall'],baseline_TP=bm[loc]['true_positives'],candidate_TP=cm[loc]['true_positives'],baseline_FP=bm[loc]['false_positives'],candidate_FP=cm[loc]['false_positives'],retained_old=len(b&a),lost_old=len(b-a),new_detected=len(a-b),retention=None if not b else len(b&a)/len(b)))
 ds=[r['candidate_recall']-r['baseline_recall'] for r in table if r['baseline_recall'] is not None];interval=None if not ds else np.quantile(np.random.default_rng(cfg['seed']).choice(ds,(10000,len(ds)),replace=True).mean(1),[.025,.975]).tolist()
 summary={k:e[k] for k in ['score_ratio','delta','retention','net_targets','new_detected_targets','lost_old_targets','retained_old_targets','protected_primary_pass','qualified','choice','diagnostic']};summary.update(baseline_macro_recall=e['baseline']['macro_location_recall'],candidate_macro_recall=e['candidate']['macro_location_recall'],baseline_fp_types=old.fp_types(e['baseline_rows'],e['targets'],e['baseline']),candidate_fp_types=old.fp_types(e['rows'],e['targets'],e['candidate']),descriptive_location_bootstrap_95_interval=interval,scope='reused training qualification;conditional encoder' if qualification else 'reused development;not fresh-location generalisation')
 return summary,table,before,after

def classified(rows,targets,metric):
 threshold=metric['global_score_threshold'];available={im:set(range(len(ts))) for im,ts in targets.items()};out=[]
 for row in sorted(rows,key=lambda r:(-r['score'],str(r['reid']),r['image_id'],tuple(r['box_xyxy']))):
  if threshold is None or row['score']<threshold:break
  im=row['image_id'];iou,index=max(((m.box_iou(row['box_xyxy'],targets[im][i]),i) for i in available[im]),default=(0.,-1))
  if iou>=.5:available[im].remove(index)
  out.append((row,None if iou<.5 else (im,index)))
 if len(out)!=metric['detections_used'] or sum(hit is None for _,hit in out)!=metric['false_positives']:raise ValueError('case prefix replay')
 return out

def cases(e,before,after):
 original={r['parent_id']:r for r in e['baseline_rows']};selected=[];candidate=classified(e['rows'],e['targets'],e['candidate']);baseline=classified(e['baseline_rows'],e['targets'],e['baseline'])
 groups=[('new_detected_target',[(r,h) for r,h in candidate if h in after-before]),('lost_old_target',[(r,h) for r,h in baseline if h in before-after]),('metric_false_positive',[(r,h) for r,h in candidate if h is None]),('corrected_only_false_positive',[(r,h) for r,h in candidate if h is None and r.get('rescored_correction')])]
 for kind,items in groups:
  seen=set();ordered=sorted(items,key=lambda z:(-z[0]['score'] if kind=='corrected_only_false_positive' else -original[z[0]['parent_id']]['score'],z[0]['image_id'],tuple(z[0]['box_xyxy']),z[0]['parent_id']))
  for row,hit in ordered:
   if row['reid'] in seen:continue
   selected.append(dict(kind=kind,image_id=row['image_id'],original=original[row['parent_id']],emitted=row,gt_identity=hit));seen.add(row['reid'])
   if len(seen)==2:break
 return selected

def verified_case_images(images,development,selected):
 canonical=m.ROOT/'docs/research/S01/S01-E006/run_config.json';files=m.read(m.ROOT/'docs/research/S01/S01-E008/source_manifest.json')['files'];m.m.check_hash(canonical,files['docs/research/S01/S01-E006/run_config.json']);m.m.check_hash(development,m.read(canonical)['source_development_sha256'])
 records={r['image_id']:r for r in m.read(development)['records']};result={}
 for case in selected:
  imid=case['image_id'];record=records[imid]
  if record['split'] not in ['train','validation']:raise ValueError('sealed image in montage')
  path=images/imid;m.m.check_hash(path,record['prepared_image_sha256'])
  with Image.open(path) as im:
   if im.size!=(record['width'],record['height']):raise ValueError('montage image dimensions')
   result[imid]=im.convert('RGB')
 return result

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--evaluation',type=Path,required=True);parser.add_argument('--decision',type=Path,required=True);parser.add_argument('--config',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--run-id',required=True);parser.add_argument('--images',type=Path);parser.add_argument('--development',type=Path);a=parser.parse_args();m.check_contract_paths(a.config);cfg=m.read(a.config);e=m.read(a.evaluation);d=m.read(a.decision)
 if e['protocol']!=cfg['protocol'] or d['protocol']!=cfg['protocol'] or e['config_sha256']!=m.sha256_file(a.config) or d['config_sha256']!=e['config_sha256']:raise ValueError('analysis lineage')
 qual='policies' in e;policies=e['policies'] if qual else [e];summaries=[];tables=[];hits=[]
 if qual and [r['score_ratio'] for r in policies]!=cfg['score_ratio_limits']:raise ValueError('fixed policy grid')
 for row in policies:
  summary,table,before,after=replay(row,cfg,qual);summaries.append(summary);tables+=table;hits.append((before,after))
 if qual:
  binding={k:v for k,v in e.items() if k not in ['scoring_receipt_sha256','policies']}
  if d!=m.decision_fields(binding,policies,cfg,m.sha256_file(a.evaluation)):raise ValueError('full qualification decision')
 else:
  status='inconclusive' if e['protected_primary_pass'] is None else ('protected_net_gain' if e['protected_primary_pass'] else 'stop_development_negative')
  binding={k:e[k] for k in ['protocol','source_manifest_sha256','config_sha256','lock_sha256','paired_feature_receipt_sha256','paired_run_id','inherited_lineage']}
  expected=dict(binding,status=status,validation_sha256=m.sha256_file(a.evaluation),delta=e['delta'],retention=e['retention'],net_targets=e['net_targets'],fresh_access=False)
  if d!=expected:raise ValueError('development decision')
 index=next((i for i,r in enumerate(policies) if qual and r['score_ratio']==d['selected_score_ratio']),0);selected=cases(policies[index],*hits[index]);a.output.mkdir(parents=True,exist_ok=True)
 (a.output/'summary.json').write_text(json.dumps(dict(run_id=a.run_id,status=d['status'],policies=summaries),indent=2)+'\n');(a.output/'montage_cases.json').write_text(json.dumps(dict(rule='selected ratio or fixed1 if none;highest original score for new/lost/FP,corrected score for corrected-onlyFP;two distinct locations/role',cases=selected),indent=2)+'\n')
 with (a.output/'location_metrics.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(tables[0]),lineterminator='\n');w.writeheader();w.writerows(tables)
 fig,axes=plt.subplots(1,3,figsize=(15,4.5));names=[str(r['score_ratio']) for r in summaries]
 for panel,key,threshold,label in [(axes[0],'delta',0 if qual else cfg['primary_delta'],'Macro recall change at1FP/image'),(axes[1],'retention',cfg['minimum_retention'],'Old detected target retention'),(axes[2],'net_targets',cfg['minimum_net_targets'],'Net detected target count')]:
  panel.bar(names,[r[key] if r[key] is not None else np.nan for r in summaries]);panel.axhline(threshold,color='black',ls='--');panel.set_ylabel(label);panel.set_xlabel('Fixed new/old score ratio');panel.grid(axis='y',alpha=.2)
  for i,r in enumerate(summaries):
   if r[key] is None:panel.text(i,.02,'NA',ha='center',transform=panel.get_xaxis_transform())
 axes[1].set_ylim(0,1.03);fig.suptitle(a.run_id+' — '+('train qualification' if qual else 'reused development')+';unchanged E003/additive corrections');fig.tight_layout();fig.savefig(a.output/'F00_decision.png',dpi=180);plt.close(fig)
 ts=[r for r in tables if r['score_ratio']==policies[index]['score_ratio']];x=np.arange(len(ts));fig,axes=plt.subplots(1,2,figsize=(11,4.5));axes[0].bar(x-.18,[r['baseline_recall'] if r['baseline_recall'] is not None else np.nan for r in ts],.36,label='E003',color='#777777');axes[0].bar(x+.18,[r['candidate_recall'] if r['candidate_recall'] is not None else np.nan for r in ts],.36,label='E003 + corrections',color='#1976D2');axes[0].set_ylabel('Recall at1FP/image');axes[0].set_ylim(0,1);axes[0].legend(frameon=False);axes[1].bar(x,[r['retention'] if r['retention'] is not None else np.nan for r in ts]);axes[1].axhline(.95,color='black',ls='--');axes[1].set_ylim(0,1.03);axes[1].set_ylabel('Old target retention')
 for panel in axes:panel.set_xticks(x,[r['location'] for r in ts]);panel.grid(axis='y',alpha=.2)
 fig.suptitle(a.run_id+' — '+('train qualification' if qual else 'reused development')+';ratio'+str(policies[index]['score_ratio']));fig.tight_layout();fig.savefig(a.output/'F01_locations.png',dpi=180);plt.close(fig)
 if a.images and selected:
  if a.development is None:raise ValueError('montage requires verified development manifest')
  case_images=verified_case_images(a.images,a.development,selected)
  fig,axes=plt.subplots(math.ceil(len(selected)/3),3,figsize=(16,4.4*math.ceil(len(selected)/3)),squeeze=False)
  for panel in axes.flat:panel.axis('off')
  for panel,case in zip(axes.flat,selected):
   panel.imshow(case_images[case['image_id']])
   for box in policies[index]['targets'][case['image_id']]:panel.add_patch(Rectangle((box[0],box[1]),box[2]-box[0],box[3]-box[1],fill=False,ec='#E41A1C',lw=2))
   for key,color in [('original','#F5A623'),('emitted','#00A6D6')]:
    box=case[key]['box_xyxy'];panel.add_patch(Rectangle((box[0],box[1]),box[2]-box[0],box[3]-box[1],fill=False,ec=color,lw=2))
   panel.set_title(case['kind']+':location'+case['original']['reid'])
  fig.suptitle(a.run_id+' — redGT,orange original,cyan emitted');fig.tight_layout();fig.savefig(a.output/'F02_montage.png',dpi=150);plt.close(fig)
 print(json.dumps(summaries,indent=2))
if __name__=='__main__':main()
