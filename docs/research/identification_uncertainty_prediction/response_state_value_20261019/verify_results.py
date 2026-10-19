"""Recompute all archived predictions' scores; no fitting, no new predictions."""
from pathlib import Path
import csv,hashlib,json,sys,time
import numpy as np
root=Path('/mnt/data2/drtao/wennie/IU-RESPONSE-STATE-20261019-R002');sys.path.insert(0,str(root/'code'));import runner
out=root/'outputs';assert json.loads((out/'receipt.json').read_text())['status']=='COMPLETE'
start=time.monotonic();cfg=json.loads((root/'code/config.producer.json').read_text());m,frames,candidates=runner.build_manifest(cfg);cases=m['cases'];groups=sorted({c['group'] for c in cases});loader=runner.Loader(cfg['data_root'])
rows=list(csv.DictReader((out/'per_case_scores.csv').open()));lookup={(r['group'],int(r['origin_stage']),int(r['horizon_stages']),r['arm']):r for r in rows};assert len(rows)==len(lookup)==len(cases)*2*(len(cfg['arms'])+3)
errors=[];count=0;archive_hashes={}
for fold,g in enumerate(groups):
 for h in cfg['horizon_stage_steps']:
  norm=None
  for arm in cfg['arms']:
   path=out/f'fold{fold}_{h}_{arm}.npz';archive_hashes[path.name]=runner.digest(path)
   with np.load(path) as z:
    norm=z['normalizer'].copy()
    for k,i in enumerate(z['case_indices']):
     c=cases[i];assert c['group']==g;n=c['origin_stage'];current=loader.get(frames[(g,n)]);future=loader.get(frames[(g,n+h)])
     delta=np.repeat(np.repeat(z['coarse_delta'][k].reshape(2,16,16),8,1),8,2)
     prediction=current+delta
     err=np.abs(prediction-future)/norm[:,None,None];lo=max(0,c['center_row']-16);hi=min(128,c['center_row']+17)
     actual=.5*float(err.mean())+.5*float(err[:,lo:hi].mean())
     expected=float(lookup[(g,n,h,arm)]['balanced_nmae']);errors.append(abs(actual-expected));count+=1
  for c in [c for c in cases if c['group']==g]:
   n=c['origin_stage'];current=loader.get(frames[(g,n)]);future=loader.get(frames[(g,n+h)]);past=loader.get(frames[(g,n-10)])
   oracle=np.repeat(np.repeat(runner.pool(future-current,16),8,1),8,2)
   for arm,pred in [('persistence',current),('secant',current+(current-past)*h/10.),('oracle_output_projection',current+oracle)]:
    err=np.abs(pred-future)/norm[:,None,None];lo=max(0,c['center_row']-16);hi=min(128,c['center_row']+17);actual=.5*float(err.mean())+.5*float(err[:,lo:hi].mean());expected=float(lookup[(g,n,h,arm)]['balanced_nmae']);errors.append(abs(actual-expected));count+=1
report={'predictions_rescored':count,'expected':len(rows),'maximum_absolute_score_discrepancy':max(errors),'saved_predictions_preserve_float64':True,'PT_inputs_match_prior_staging':'producer_preflight.json','npz_sha256':archive_hashes,'elapsed_seconds':time.monotonic()-start,'status':'VERIFIED' if count==len(rows) and max(errors)<1e-11 else 'DISCREPANCY'}
(root/'result_verification.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='npz_sha256'}),flush=True)
assert report['status']=='VERIFIED'

prior_rows=list(csv.DictReader(Path('/mnt/data2/drtao/wennie/IU-PUBLISHED-DIC-20261019-R001/outputs/per_case_scores.csv').open()))
prior_lookup={(r['group'],r['origin_stage'],r['horizon_stages'],r['arm']):float(r['balanced_nmae']) for r in prior_rows}
replay={'span_only':'scalar','compact_noclock':'compact','rich_noclock':'rich'}
replay_errors={a:[] for a in replay}
for row in rows:
 a=row['arm']
 if a in replay:
  replay_errors[a].append(abs(float(row['balanced_nmae'])-prior_lookup[(row['group'],row['origin_stage'],row['horizon_stages'],replay[a])]))
replay_report={a:{'count':len(e),'max_abs_discrepancy':max(e)} for a,e in replay_errors.items()}
assert all(x['count']==len(cases)*2 and x['max_abs_discrepancy']<1e-11 for x in replay_report.values()),replay_report
(root/'replay_verification.json').write_text(json.dumps(replay_report,indent=2));print('REPLAY_VERIFIED',json.dumps(replay_report),flush=True)
