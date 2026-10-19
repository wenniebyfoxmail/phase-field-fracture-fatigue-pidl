"""Future authorised worker. Preparation uses --check only; no scientific I/O before approval."""
from pathlib import Path
import argparse,csv,hashlib,json,os,platform,sys,time,tarfile,warnings
import contract

def rows_write(p,rows):
 with Path(p).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def preflight(code,cfg,r):
 import numpy as np
 import torch
 import r002_base as base
 frozen,files=contract.check(code,cfg)
 if cfg.get('clock')!='release_step':raise ValueError('unverified physical clock')
 if os.stat('/mnt/data2').st_dev!=os.stat(r).st_dev:raise ValueError('wrong producer mount')
 import shutil
 if shutil.disk_usage(r).free<8*2**30:raise RuntimeError('space below combined output/archive caps')
 mem={x.split(':')[0]:int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')}
 if mem.get('MemAvailable',0)<8*2**30:raise RuntimeError('insufficient available memory')
 data=Path(cfg['data_root']);source=Path(cfg['source_run_root'])
 for x in files:
  rel=Path(x['relative_path'])
  if rel.is_absolute() or '..' in rel.parts:raise ValueError('unsafe input')
  p=data/rel
  if p.stat().st_size!=x['bytes'] or contract.sha(p)!=x['sha256']:raise ValueError('input hash mismatch: '+str(rel))
 if hashlib.sha256((source/'code/runner.py').read_bytes()+(source/'code/config.producer.json').read_bytes()).hexdigest()!=cfg['source_package_sha256']:raise ValueError('R002 source package changed')
 m,frames,_=base.build_manifest(cfg)
 if m['cases']!=frozen['cases'] or m['exclusions']!=frozen['exclusions']:raise ValueError('cohort mismatch')
 feature_path=source/'outputs/origin_feature_evidence.npz'
 if contract.sha(feature_path)!=cfg['origin_feature_sha256']:raise ValueError('origin feature source changed')
 oldhash=contract.read(code/'r002_verification.json')['npz_sha256']
 for fold in range(19):
  for h in (10,40):
   for old in ('current_response','history_response','centered_history'):
    name=f'fold{fold}_{h}_{old}.npz'
    if contract.sha(source/'outputs'/name)!=oldhash[name]:raise ValueError('replay archive changed')
 with np.load(feature_path,allow_pickle=False) as z:
  states=z['states'].copy();origins=z['origin_stage'].copy()
 if states.shape!=(1144,3,138) or not np.isfinite(states).all() or list(origins)!=[c['origin_stage'] for c in m['cases']]:raise ValueError('saved input schema/identity')
 torch.set_num_threads(1)
 loader=base.Loader(data)
 for group in sorted({c['group'] for c in m['cases']}):
  c=next(c for c in m['cases'] if c['group']==group);x=loader.get(frames[(group,c['origin_stage'])])
  if x.shape!=(2,128,128) or x.dtype!=np.float32:raise ValueError('native schema')
 contract.write(r/'outputs/manifest.json',m)
 contract.write(r/'outputs/input_receipt.json',{'status':'VERIFIED_NO_FIT','files':180,'bytes':2309814734,'groups':19,'origins':1144,'clock':'release_step','physical_independence':'unknown','origin_features_sha256':cfg['origin_feature_sha256']})
 return m,frames,states,loader

def run(code,cfg,r):
 import numpy as np
 import r002_base as base
 import state
 from analysis import diagnostic,analyse,render
 m,frames,states,loader=preflight(code,cfg,r);cases=m['cases'];groups=sorted({c['group'] for c in cases});out=r/'outputs';records=[];selectors=[];fits=state.Fits();tol=cfg['tolerance'];replaymax=0.;pullmax=0.
 source=Path(cfg['source_run_root'])/'outputs'
 def get(c,offset):return loader.get(frames[(c['group'],c['origin_stage']+offset)])
 def native(c,arm,h,coarse=None):
  current=get(c,0)
  if arm=='P':return current
  if arm=='S':return current+(current-get(c,-10))*h/10.
  return current+np.repeat(np.repeat(coarse.reshape(2,16,16),8,1),8,2)
 def loss(preds,indexes,norm,arm,h):
  per={g:[] for g in groups}
  for k,i in enumerate(indexes):
   c=cases[i];p=native(c,arm,h,None if preds is None else preds[k]);per[c['group']].append(base.score(p,get(c,h),c['center_row'],norm,16)[0])
  return float(np.mean([np.mean(x) for x in per.values() if x]))
 for fold,held in enumerate(groups):
  dev=[g for g in groups if g!=held];valid=set(dev[::4]);train=[i for i,c in enumerate(cases) if c['group'] in set(dev)-valid];val=[i for i,c in enumerate(cases) if c['group'] in valid];development=[i for i,c in enumerate(cases) if c['group']!=held];test=[i for i,c in enumerate(cases) if c['group']==held]
  for h in (10,40):
   y=[];summaries=[]
   for c in cases:
    d=get(c,h)-get(c,0);y.append(base.pool(d,16).ravel());summaries.append(np.mean(np.abs(d),axis=(1,2)))
   y=np.asarray(y);summaries=np.asarray(summaries);ni=np.maximum(summaries[train].mean(0),1e-6);nf=np.maximum(summaries[development].mean(0),1e-6)
   x,hist=state.features(states,cases,h)
   inner,ie,iprefix=state.innovations(fits,x['C_RAW'],hist,train,val,cases)
   final,fe,fprefix=state.innovations(fits,x['C_RAW'],hist,development,test,cases)
   selected={};inner_losses={};outer={};models={}
   for arm in state.ARMS:
    xi,xv=inner[arm] if arm in inner else (x[arm][train],x[arm][val]);xd,xt=final[arm] if arm in final else (x[arm][development],x[arm][test])
    choices=[]
    for alpha in cfg['ridge_alphas']:
     model=fits.fit(xi,y[train],alpha,[cases[i]['group'] for i in train],locked_prefix=iprefix if arm in inner else None)
     p=state.predict(model,xv);choices.append((loss(p,val,ni,arm,h),alpha))
    best,alpha=min(choices);selected[arm]=alpha;inner_losses[arm]=best
    model=fits.fit(xd,y[development],alpha,[cases[i]['group'] for i in development],locked_prefix=fprefix if arm in final else None)
    p=state.predict(model,xt);outer[arm]=p;models[arm]=model
    if arm in ('C_RAW','H_RAW','H_REL'):
     old={'C_RAW':'current_response','H_RAW':'history_response','H_REL':'centered_history'}[arm]
     with np.load(source/f'fold{fold}_{h}_{old}.npz',allow_pickle=False) as z:
      if list(z['case_indices'])!=test or float(z['training_fixed_half_width'])<0:raise ValueError('replay case/metadata')
      discrepancy=max(float(np.max(np.abs(p-z['coarse_delta']))),float(np.max(np.abs(nf-z['normalizer']))))
      if discrepancy>=tol:raise ValueError('replay prediction/normalizer mismatch')
      for k,i in enumerate(test):
       c=cases[i];original=base.score(native(c,arm,h,z['coarse_delta'][k]),get(c,h),c['center_row'],z['normalizer'],16)[0];new=base.score(native(c,arm,h,p[k]),get(c,h),c['center_row'],nf,16)[0]
       if abs(new-original)>=tol:raise ValueError('replay score mismatch')
       discrepancy=max(discrepancy,abs(new-original))
      replaymax=max(replaymax,discrepancy)
    np.savez_compressed(out/f'fold{fold}_{h}_{arm}.npz',coarse_delta=p,case_indices=np.asarray(test),normalizer=nf,alpha=alpha,feature_mean=model[0],feature_scale=model[1],coef=model[2])
   baseline_losses={'P':loss(None,val,ni,'P',h),'S':loss(None,val,ni,'S',h),'C_RAW':inner_losses['C_RAW'],'C_REL':inner_losses['C_REL']};chosen=state.choose_baseline(baseline_losses)
   selectors.append({'fold':fold,'held_group':held,'horizon_stages':h,'chosen':chosen,'inner_losses':baseline_losses,'alphas':selected,'inner_train_indices':train,'inner_valid_indices':val,'outer_development_indices':development,'outer_test_indices':test})
   np.savez_compressed(out/f'fold{fold}_{h}_input_evidence.npz',**{'inner_'+k:v for k,v in ie.items()},**{'final_'+k:v for k,v in fe.items()})
   pp,pe=state.pullback(models['H_RAW'],x['H_RAW'][development],x['H_RAW'][test]);outer['H_RAW_PULLBACK']=pp
   if float(np.max(np.abs(pp-outer['H_RAW'])))>=tol:raise ValueError('pulled-back function mismatch')
   np.savez_compressed(out/f'fold{fold}_{h}_H_RAW_PULLBACK.npz',coarse_delta=pp,case_indices=np.asarray(test),normalizer=nf,alpha=selected['H_RAW'],**pe)
   for k,i in enumerate(test):
    c=cases[i];target=get(c,h);current=get(c,0);case_rows={}
    for arm in (*state.ARMS,'P','S','H_RAW_PULLBACK'):
     pred=native(c,arm,h,None if arm in ('P','S') else outer[arm][k]);balanced,mae,lmae,full,local=base.score(pred,target,c['center_row'],nf,16)
     row=dict(group=held,origin_stage=c['origin_stage'],horizon_stages=h,case_index=i,arm=arm,balanced_nmae=balanced,full_mae=mae,local_mae=lmae,full_nmae=full,local_nmae=local,alpha=selected.get('H_RAW' if arm=='H_RAW_PULLBACK' else arm))
     row.update(diagnostic(pred-current,target-current,nf,c['center_row']));records.append(row);case_rows[arm]=row
    d=abs(case_rows['H_RAW_PULLBACK']['balanced_nmae']-case_rows['H_RAW']['balanced_nmae']);pullmax=max(pullmax,d)
    if d>=tol:raise ValueError('pulled-back score mismatch')
    row=dict(case_rows[chosen]);row.update(arm='B_STAR',selector_chosen=chosen)
    # Keep score CSV schema uniform; method selection is frozen using inner data only.
    for rr in list(case_rows.values()):rr['selector_chosen']=''
    records.append(row)
   rows_write(out/'per_case_scores.csv',records);contract.write(out/'selectors.json',selectors)
   contract.write(out/'progress.json',{'completed_group_horizons':fold*2+(1 if h==10 else 2),'total':38,'predictor_fits':fits.predictor,'input_fits':fits.input})
 if fits.predictor!=912 or fits.input!=76 or len(records)!=22880:raise ValueError('work/row accounting mismatch')
 contract.write(out/'equivalence_receipt.json',{'replay_max_abs_discrepancy':replaymax,'pullback_max_abs_score_discrepancy':pullmax,'threshold':tol,'status':'VERIFIED'})
 analyse(out,records,groups,cfg)
 # All plots reconstruct saved coarse outputs; there is no post-analysis model forward.
 render(out,records,cases,groups,selectors,loader,frames,cfg)
 from verify import verify
 verify(out,cfg,m,loader,frames)
 contract.write(out/'receipt.json',{'status':'CANDIDATE_COMPLETE_REQUIRES_CONTROLLER','predictor_fits':fits.predictor,'input_fits':fits.input,'score_rows':20592,'selector_rows':2288,'clock':'release_step'})
 archive=r/'results.tar.gz.partial'
 with tarfile.open(archive,'w:gz') as t:
  t.add(out,arcname='outputs');t.add(code,arcname='code');t.add(r/'logs',arcname='logs');t.add(r/'provenance.json',arcname='provenance.json')
 if archive.stat().st_size>4*2**30:raise RuntimeError('archive cap')
 archive.rename(r/'results.tar.gz')
 contract.write(r/'archive_receipt.json',{'bytes':(r/'results.tar.gz').stat().st_size,'sha256':contract.sha(r/'results.tar.gz'),'status':'READY_FOR_RETRIEVAL'})

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,default=Path(__file__).with_name('config.producer.json'));p.add_argument('--check',action='store_true');p.add_argument('--run',action='store_true');p.add_argument('--approval-receipt',type=Path);args=p.parse_args(argv)
 code=Path(__file__).resolve().parent;cfg=contract.load_config(code,args.config);contract.check(code,cfg)
 if args.check:
  if args.run:raise ValueError('check is not run')
  print(json.dumps({'status':'METADATA_CONTRACT_CHECKED_NO_SCIENTIFIC_ARRAY_IO','groups':19,'origins':1144,'horizon_cases':2288,'production_authority':False}));return
 if not args.run:raise PermissionError('choose --check; production requires fresh explicit authority')
 digest,auth=contract.approval(code,cfg,args.approval_receipt)
 r=Path(cfg['run_root'])
 if not(r/'run_claim.json').exists():raise PermissionError('independent controller required')
 claim=contract.read(r/'run_claim.json')
 if claim['controller_pid']!=os.getppid() or claim['package_sha256']!=digest:raise PermissionError('controller identity mismatch')
 out=r/'outputs';out.mkdir(exist_ok=False)
 warnings.simplefilter('error')
 contract.write(r/'provenance.json',{'package_sha256':digest,'run_id':cfg['run_id'],'hostname':platform.node(),'python':sys.version,'pid':os.getpid(),'controller_pid':os.getppid(),'started_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'clock':'release_step','authority':auth,'code_path':str(code)})
 try:run(code,cfg,r)
 except BaseException as exc:
  contract.write(out/'receipt.json',{'status':'STOPPED_NO_RETRY','reason':type(exc).__name__+': '+str(exc)});raise
if __name__=='__main__':main()
