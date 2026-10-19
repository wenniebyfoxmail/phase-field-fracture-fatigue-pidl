"""Future saved-output verification: no fit, coefficient forward, or alpha selection."""
from pathlib import Path
import csv
import contract

def verify(out,cfg,manifest,loader,frames):
 import numpy as np
 from state import ARMS,choose_baseline
 out=Path(out);cases=manifest['cases'];groups=sorted({c['group'] for c in cases});rows=list(csv.DictReader((out/'per_case_scores.csv').open()))
 lookup={(r['group'],int(r['horizon_stages']),int(r['case_index']),r['arm']):r for r in rows}
 if len(rows)!=22880 or len(lookup)!=22880:raise ValueError('case-method or selector count')
 selectors=contract.read(out/'selectors.json')
 if len(selectors)!=38:raise ValueError('selector count')
 sl={(s['held_group'],s['horizon_stages']):s for s in selectors};maxdiff=0.;count=0;hashes={}
 def get(i,k):
  c=cases[i];return loader.get(frames[(c['group'],c['origin_stage']+k)])
 summaries={h:np.asarray([np.abs(get(i,h)-get(i,0)).mean((1,2)) for i in range(len(cases))]) for h in (10,40)}
 for fold,g in enumerate(groups):
  ids=[i for i,c in enumerate(cases) if c['group']==g];dev=[i for i,c in enumerate(cases) if c['group']!=g]
  for h in (10,40):
   norm=np.maximum(summaries[h][dev].mean(0),1e-6);selector=sl[(g,h)];chosen=choose_baseline(selector['inner_losses'])
   if chosen!=selector['chosen'] or selector['outer_test_indices']!=ids or selector['outer_development_indices']!=dev:raise ValueError('selection identity')
   train=selector['inner_train_indices'];valid=selector['inner_valid_indices'];tg={cases[i]['group'] for i in train};vg={cases[i]['group'] for i in valid}
   if tg&vg or g in tg|vg or set(train)|set(valid)!=set(dev):raise ValueError('fold leakage')
   with np.load(out/f'fold{fold}_{h}_input_evidence.npz',allow_pickle=False) as z:
    for prefix,fit,q in [('inner',train,valid),('final',dev,ids)]:
     if list(z[prefix+'_train_indices'])!=fit or list(z[prefix+'_query_indices'])!=q:raise ValueError('input estimator fold')
     for recipients,key in [(fit,'train_donor_indices'),(q,'query_donor_indices')]:
      donors=list(map(int,z[prefix+'_'+key]));pool=set(fit)
      if len(donors)!=len(recipients) or any(d not in pool or cases[d]['group']==cases[i]['group'] for i,d in zip(recipients,donors)):raise ValueError('donor leakage')
   predictions={}
   for arm in (*ARMS,'H_RAW_PULLBACK'):
    p=out/f'fold{fold}_{h}_{arm}.npz';hashes[p.name]=contract.sha(p)
    with np.load(p,allow_pickle=False) as z:
     if list(z['case_indices'])!=ids or np.max(np.abs(norm-z['normalizer']))>=1e-11:raise ValueError('normalizer/case mismatch')
     predictions[arm]=z['coarse_delta'].copy()
   for k,i in enumerate(ids):
    cur=get(i,0);target=get(i,h);source_scores={}
    for arm in (*ARMS,'P','S','H_RAW_PULLBACK'):
     if arm=='P':pred=cur
     elif arm=='S':pred=cur+(cur-get(i,-10))*h/10.
     else:pred=cur+np.repeat(np.repeat(predictions[arm][k].reshape(2,16,16),8,1),8,2)
     err=np.abs(pred-target)/norm[:,None,None];c=cases[i]['center_row'];lo=max(0,c-16);hi=min(128,c+17)
     actual=.5*float(err.mean())+.5*float(err[:,lo:hi].mean());stored=float(lookup[(g,h,i,arm)]['balanced_nmae']);d=abs(actual-stored)
     if not np.isfinite(actual) or d>=1e-11:raise ValueError('saved score discrepancy')
     maxdiff=max(maxdiff,d);count+=1;source_scores[arm]=actual
    row=lookup[(g,h,i,'B_STAR')]
    if row['selector_chosen']!=chosen or abs(float(row['balanced_nmae'])-source_scores[chosen])>=1e-11:raise ValueError('Bstar copied score mismatch')
    count+=1
 if count!=22880 or len(hashes)!=266:raise ValueError('archive count mismatch')
 contract.write(out/'verification.json',{'status':'VERIFIED','main_method_scores':20592,'selector_scores':2288,'scores_checked':count,'prediction_and_equivalence_archives':266,'maximum_absolute_score_discrepancy':maxdiff,'archive_sha256':hashes,'fit_or_forward_calls':0})
