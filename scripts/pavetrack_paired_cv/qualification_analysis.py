#!/usr/bin/env python3
"""Read-only exact tables and all-policy replay before qualification figures."""
import argparse,csv,json,importlib.util,math
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from matplotlib.patches import Rectangle
spec=importlib.util.spec_from_file_location('paired_runner',Path(__file__).with_name('run.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
z=importlib.util.spec_from_file_location('paired_cases',Path(__file__).with_name('analyze.py'));analysis=importlib.util.module_from_spec(z);z.loader.exec_module(analysis)
def table(path,rows):
 with path.open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
def validated(run,cfg,config,lock):
 d=m.read(run/'qualification_decision.json');receipt=m.read(run/'feature_receipt.json');data=m.read(run/'train_bank.json');audit=m.read(run/'label_audit.json')
 for payload in [d,receipt,data,audit]:
  if payload['protocol']!=cfg['protocol'] or payload['config_sha256']!=m.sha256_file(config) or payload['lock_sha256']!=m.sha256_file(lock):raise ValueError('analysis identity')
 for name in ['train_bank.json','label_audit.json']:m.m.check_hash(run/name,receipt['files'][name])
 for old,new,y in zip(data['bank'][::2],data['bank'][1::2],data['labels'],strict=True):
  if m.labels(old['box_xyxy'],new['box_xyxy'],data['targets'][old['image_id']])!=y:raise ValueError('label identity replay')
 binding={k:audit[k] for k in ['protocol','source_manifest_sha256','config_sha256','lock_sha256','parent_feature_receipt_sha256','parent_run_id','inherited_lineage']}
 if audit!=dict(binding,**m.label_audit(data,m.read(lock),cfg)):raise ValueError('label counts/cases replay')
 summary={'run_id':run.name,'status':d['status'],'selected_harm_limit':d.get('selected_harm_limit'),'scope':'four held train locations;conditional shared encoder;not fresh/development','label_counts':audit['counts'],'policies':[]};policies=[];selected=None
 if d['status']=='inconclusive_qualification_classes':
  if d!=dict(binding,status='inconclusive_qualification_classes',fresh_access=False):raise ValueError('class stop decision replay')
  fit=audit['counts'][0]
  if all(fit[k+'_'+str(v)]>0 for k in ['harm','gain'] for v in [0,1]) or (run/'qualification_head_started.json').exists() or (run/'qualification_evaluation.json').exists():raise ValueError('false class stop')
  return summary,audit['cases'],data['targets'],policies
 e=m.read(run/'qualification_evaluation.json')
 if e['protocol']!=cfg['protocol'] or m.sha256_file(run/'qualification_evaluation.json')!=d['qualification_evaluation_sha256'] or len(e['policies'])!=4:raise ValueError('qualification receipt')
 qd,_=m.subset(data,np.empty((len(data['labels']),0)),cfg['qualification_locations'])
 for limit,row in zip(cfg['harm_score_limits'],e['policies'],strict=True):
  analysis.replay(row,cfg)
  if row['harm_limit']!=limit or row['pair_probabilities']['harm_limit']!=limit:raise ValueError('policy grid')
  accepted={r['parent_id'] for r in row['rows'] if r.get('chosen_correction')};ls=[y for r,y in zip(qd['bank'][::2],qd['labels'],strict=True) if r['parent_id'] in accepted and y['protected']];n=len(ls);harms=sum(y['harm'] for y in ls);rate=None if not n else harms/n
  ok=row['retention'] is not None and row['retention']>=cfg['minimum_retention'] and row['delta'] is not None and row['delta']>cfg['qualification_minimum_delta'] and n>=cfg['qualification_minimum_protected_exposures'] and rate<=cfg['qualification_harm_rate_maximum']
  if any(row[k]!=v for k,v in dict(protected_exposures=n,harm_count=harms,harm_rate=rate,qualified=ok).items()):raise ValueError('qualification harm/criteria replay')
  policies.append(row);summary['policies'].append(dict(harm_limit=limit,baseline_macro_recall=row['baseline']['macro_location_recall'],candidate_macro_recall=row['candidate']['macro_location_recall'],baseline_TP=sum(r['true_positives'] for r in row['baseline']['locations']),candidate_TP=sum(r['true_positives'] for r in row['candidate']['locations']),baseline_FP=row['baseline']['false_positives'],candidate_FP=row['candidate']['false_positives'],**{k:row[k] for k in ['delta','retention','protected_exposures','harm_count','harm_rate','new_detected_targets','lost_old_targets','qualified']},**row['choice']))
 if d!=m.decision_fields(binding,policies,cfg,m.sha256_file(run/'qualification_evaluation.json')):raise ValueError('qualification selection replay')
 chosen=next((r for r in policies if r['harm_limit']==d['selected_harm_limit']),None)
 selected=chosen or policies[-1];oldhits=m.admitted_targets(selected['baseline_rows'],selected['targets'],selected['baseline']);newhits=m.admitted_targets(selected['rows'],selected['targets'],selected['candidate']);cases=analysis.cases(selected,oldhits,newhits)
 return summary,cases,selected['targets'],policies

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--lock',type=Path,required=True);p.add_argument('--images',type=Path);a=p.parse_args();cfg=m.read(a.config);summary,cases,targets,policies=validated(a.run,cfg,a.config,a.lock);a.output.mkdir(parents=True,exist_ok=True)
 table(a.output/'label_counts.csv',summary['label_counts'])
 if summary['policies']:table(a.output/'qualification_metrics.csv',summary['policies'])
 (a.output/'montage_cases.json').write_text(json.dumps({'scope':'train labels' if not policies else 'train qualification','rule':'class stop:fixed split/label cases;else selected qualified policy or fixed .1','cases':cases},indent=2)+'\n')
 fig,ax=plt.subplots(1,4,figsize=(19,4.5))
 if policies:
  limits=[str(x['harm_limit']) for x in policies]
  for panel,key,threshold,label in [(ax[0],'delta',0,'Macro recall change at1FP/image'),(ax[1],'retention',.95,'Old detected target retention'),(ax[2],'protected_exposures',cfg['qualification_minimum_protected_exposures'],'Accepted original-valid pair exposures'),(ax[3],'harm_rate',cfg['qualification_harm_rate_maximum'],'Empirical original-target harm rate')]:
   panel.bar(limits,[x[key] if x[key] is not None else float('nan') for x in policies]);panel.axhline(threshold,color='black',ls='--');panel.set_xlabel('Fixed harm-score limit');panel.set_ylabel(label);panel.grid(axis='y',alpha=.2)
   for i,row in enumerate(policies):
    if row[key] is None:panel.text(i,.02,'NA',ha='center',transform=panel.get_xaxis_transform())
  ax[1].set_ylim(0,1.03);ax[3].set_ylim(0,max(.1,max((x['harm_rate'] or 0 for x in policies))) *1.1)
 else:
  fit,qual=summary['label_counts'];names=['harm0','harm1','gain0','gain1'];keys=['harm_0','harm_1','gain_0','gain_1']
  for panel,c,label in [(ax[0],fit,'12 decision-fit locations'),(ax[1],qual,'4 qualification locations')]:panel.bar(names,[c[k] for k in keys]);panel.set_title(label);panel.set_ylabel('Exact paired label counts')
  ax[2].bar(['fit','qualification'],[fit['protected'],qual['protected']]);ax[2].set_ylabel('Original-valid pairs');ax[3].axis('off');ax[3].text(.5,.5,'Required paired class absent\nNo paired head fitted\nNo development comparison',ha='center',va='center',transform=ax[3].transAxes)
 fig.suptitle(a.run.name+' — train qualification\n'+summary['status']+';empirical rates are not population risk guarantees');fig.tight_layout();fig.savefig(a.output/'F00_training_qualification.png',dpi=180);plt.close(fig)
 if a.images and cases:
  montage,axes=plt.subplots((len(cases)+2)//3,3,figsize=(16,4.4*((len(cases)+2)//3)),squeeze=False)
  for panel in axes.flat:panel.axis('off')
  for panel,case in zip(axes.flat,cases):
   panel.imshow(Image.open(a.images/case['image_id']).convert('RGB'))
   for box in targets[case['image_id']]:panel.add_patch(Rectangle((box[0],box[1]),box[2]-box[0],box[3]-box[1],fill=False,ec='#E41A1C',lw=2))
   for key,color in [('original','#F5A623'),('emitted','#00A6D6')]:
    box=case[key]['box_xyxy'];panel.add_patch(Rectangle((box[0],box[1]),box[2]-box[0],box[3]-box[1],fill=False,ec=color,lw=2))
   panel.set_title(case['kind']+': location '+case['original']['reid'])
  montage.suptitle(a.run.name+' — train geometry cases;redGT,orange original,cyan correction');montage.tight_layout();montage.savefig(a.output/'F02_qualification_montage.png',dpi=150);plt.close(montage)
 (a.output/'qualification_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
