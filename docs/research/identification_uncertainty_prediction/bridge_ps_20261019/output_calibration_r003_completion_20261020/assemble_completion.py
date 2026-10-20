"""Saved-output-only full19 assembly. No original input access, fitting or model forwards.
Arrays stay in two hash-bound component stores; complete tables/figures reference them.
"""
from pathlib import Path
import argparse,csv,itertools,json,collections
import numpy as np
import package,engine,evidence,prefix_binding

def check_local_storage(cfg,reserve=32*2**20):
 roots=[Path(p).resolve() for p in cfg['local_storage_roots']]
 if any(a==b or a in b.parents or b in a.parents for i,a in enumerate(roots) for b in roots[i+1:]):raise ValueError('overlapping storage accounting roots')
 counts={str(r):sum(p.stat().st_size for p in r.rglob('*') if p.is_file()) for r in roots if r.exists()}
 if sum(counts.values())+reserve>cfg['approved_budget']['total_generated_bytes']:raise ValueError('combined local storage budget/reserve')
 return {'roots':counts,'total_bytes':sum(counts.values()),'assembly_reserve_bytes':reserve}

def verify_retrieval(root):
 root=Path(root);inventory=root.parent/'retrieval_inventory.json';proof=root.parent.parent/'retrieval_verification.json'
 p=package.read(proof);inv=package.read(inventory)
 if p['status']!='COMPLETE_SNAPSHOT_ALL_HASHES_VERIFIED' or p['inventory_sha256']!=package.sha(inventory):raise ValueError('verified retrieval proof absent or changed')
 archive=Path(p['snapshot_path'])
 if archive.stat().st_size!=p['snapshot_bytes'] or package.sha(archive)!=p['snapshot_sha256']:raise ValueError('retrieved snapshot changed')
 actual={str(f.relative_to(root)) for f in root.rglob('*') if f.is_file()}
 if actual!=set(inv['files']):raise ValueError('retrieved file set changed')
 for name,item in inv['files'].items():
  rel=Path(name)
  if rel.is_absolute() or '..' in rel.parts:raise ValueError('unsafe retrieved file')
  f=root/rel
  if f.is_symlink() or f.stat().st_size!=item['bytes'] or package.sha(f)!=item['sha256']:raise ValueError('retrieval hash mismatch '+name)
 return {'files_verified':len(actual),'snapshot_sha256':p['snapshot_sha256']}

def rows(path,n=None):
 with Path(path).open() as f:return [json.loads(x) for x in (f if n is None else itertools.islice(f,n))]

def verify_component(root,groups,counts,cohort,horizons=(10,40),half_height=16):
 root=Path(root);o=root/'outputs';s=package.read(o/'array_schema.json');labels=[x['group'] for x in cohort];hs=horizons
 fields=rows(o/'outer_fields.jsonl',counts['outer_rows']);inner=rows(o/'inner_index.jsonl',counts['inner_rows']);prov=rows(o/'model_provenance.jsonl',counts['residualizer']);sels=rows(o/'selections.jsonl',len(groups)*2)
 if [x['row'] for x in fields]!=list(range(counts['outer_rows'])) or [x['row'] for x in inner]!=list(range(counts['inner_rows'])):raise ValueError('stream row identities')
 expected={(i,h) for i,g in enumerate(labels) if g in groups for h in hs}
 if len(fields)!=len(expected) or {(z['case'],z['H']) for z in fields}!=expected:raise ValueError('outer case/H coverage')
 want_inner={(g,h,d,i) for g in groups for h in hs for d in sorted(set(labels)-{g}) for i,l in enumerate(labels) if l==d}
 got_inner={(z['outer'],z['H'],z['inner'],z['case']) for z in inner}
 if len(inner)!=len(want_inner) or got_inner!=want_inner:raise ValueError('inner case/fold coverage')
 expected_models={(g,h,d) for g in groups for h in hs for d in [None]+sorted(set(labels)-{g})}
 if len(prov)!=len(expected_models) or {(z['outer'],z['H'],z['inner']) for z in prov}!=expected_models:raise ValueError('model fold coverage')
 final_norm={}
 for z in prov:
  train=[i for i,g in enumerate(labels) if g not in {z['outer'],z['inner']}];query=[i for i,g in enumerate(labels) if g==(z['inner'] or z['outer'])]
  if z['train']!=train or z['normalizer_train_ids']!=train or z['query']!=query or z['alpha']!=10.:raise ValueError('provenance leakage')
  engine.finite(z['normalizer'],'saved model normalizer')
  if z['final']!=(z['inner'] is None):raise ValueError('model role')
  if z['inner'] is None:final_norm[z['outer'],z['H']]=z['normalizer']
 loss=np.memmap(o/'inner_losses.f64',dtype='<f8',mode='r',shape=tuple(s['loss_shape']))
 if not np.isfinite(loss[:counts['inner_rows']]).all():raise ValueError('inner nonfinite')
 bycell=collections.defaultdict(lambda:collections.defaultdict(list))
 for k,z in enumerate(inner):bycell[z['outer'],z['H']][z['inner']].append(k)
 choices={};selerr=0.
 if len(sels)!=len(groups)*2 or len({(z['outer'],z['H']) for z in sels})!=len(sels):raise ValueError('selection coverage')
 for z in sels:
  k=z['outer'],z['H'];ix=bycell[k]
  means=np.mean([loss[ix[g],:,0].mean(axis=0) for g in sorted(ix)],axis=0)
  saved_mean=np.asarray(z['candidate_group_mean_balanced'],dtype=float)
  if saved_mean.shape!=(len(engine.PAIRS),) or not np.isfinite(saved_mean).all():raise ValueError('saved selector mean nonfinite/schema')
  selerr=max(selerr,float(abs(means-saved_mean).max()))
  chosen=[engine.select(dict(zip(engine.PAIRS,means)),family) for family in (engine.U,engine.C,engine.A)]
  if [list(x) for x in chosen]!=z['chosen_U_C_A']:raise ValueError('selector mismatch')
  choices[k]=list(engine.FIXED)+chosen
 if selerr>1e-11:raise ValueError('selection mean mismatch')
 loss._mmap.close()
 with (o/'outer_scores.csv').open() as f:score_rows=list(itertools.islice(csv.DictReader(f),counts['outer_scores']))
 scores={(int(z['case']),int(z['H']),z['arm']):z for z in score_rows}
 for z in score_rows:
  engine.finite([float(v) for k,v in z.items() if k not in ('group','arm') and v not in ('',None)],'saved score numeric')
 if len(score_rows)!=counts['outer_scores'] or len(scores)!=len(score_rows):raise ValueError('outer scores count/duplicate')
 # Stream saved arrays directly once; decoder used separately for figure access.
 arrays=[np.memmap(o/name,dtype=dtype,mode='r',shape=tuple(s[key])) for name,dtype,key in [('outer_bases.f64','<f8','outer_base_shape'),('current_anchors.f32','<f4','anchor_shape'),('outer_targets.f32','<f4','target_shape')]]
 bases,anchors,targets=arrays;anchor_cases=s.get('anchor_cases',list(range(len(anchors))));anchor_ix={case:row for row,case in enumerate(anchor_cases)};delta=0.
 for z in fields:
  i,h,r=z['case'],z['H'],z['row'];g=labels[i]
  if z['group']!=g or z['normalizer']!=final_norm[g,h] or [tuple(x) for x in z['weights']]!=[tuple(x) for x in choices[g,h]]:raise ValueError('field identity/weights/normalizer')
  field=engine.decoded_fields(anchors[anchor_ix[i]],bases[r,0],bases[r,1],z['weights'],s['coarse_side']);target=targets[r];norm=np.asarray(z['normalizer']);center=cohort[i]['center_row']
  value=engine.native_losses(field,target,norm,center,half_height)
  for j,arm in enumerate(engine.ARMS):
   saved=scores[i,h,arm]
   if saved['group']!=g or (float(saved['lambda_g']),float(saved['lambda_s']))!=tuple(z['weights'][j]):raise ValueError('score identity/weight')
   delta=max(delta,float(abs(value[j]-[float(saved[k]) for k in ('balanced','full','band')]).max()))
   for ch in (0,1):
    error=abs(field[j,ch]-target[ch])/norm[ch];lo=max(0,center-half_height);hi=min(target.shape[-2],center+half_height+1)
    delta=max(delta,abs(float(error.mean())-float(saved[f'native_full_{ch}'])),abs(float(error[lo:hi].mean())-float(saved[f'native_band_{ch}'])))
 if delta>1e-11:raise ValueError('native metric mismatch')
 for x in arrays:x._mmap.close()
 return score_rows,{'groups':groups,'counts':counts,'native_scores_recomputed':len(scores),'max_native_difference':delta,'model_provenance_checked':len(prov),'selector_cells_reaggregated':len(sels),'max_selector_mean_difference':selerr},fields

def assemble(code,oldroot,newroot,out,render=True):
 code=Path(code);oldroot=Path(oldroot);newroot=Path(newroot);out=Path(out)
 if out.exists():raise FileExistsError('fresh assembly path required')
 cfg=package.read(code/'config.json');storage=check_local_storage(cfg);retrieval=verify_retrieval(newroot)
 binding=prefix_binding.verify_root(code,oldroot);cfg=package.read(code/'config.json');digest=package.check(code)
 if package.check(newroot/'code')!=digest:raise ValueError('new component source mismatch')
 receipt=package.read(newroot/'watchdog_receipt.json')
 if receipt['status']!='COMPLETE_CONTROLLER_EXIT_VERIFIED' or receipt['package_sha256']!=digest:raise ValueError('new scientific run not complete')
 from watchdog import verify_controller_exit
 controller=verify_controller_exit(newroot,receipt['controller_pid'])
 for n,pid in [('logs/runtime_exit.json',controller['worker_pid']),('logs/controller_exit.json',receipt['controller_pid']),('logs/watchdog_exit.json',receipt['watchdog_pid'])]:
  seal=package.read(newroot/n)
  if seal['status']!='RETURNED_AND_EXIT_CALLBACKS_COMPLETE' or seal['pid']!=pid:raise ValueError('missing clean actual exit/PID identity')
 for n in ['launch.stderr','logs/controller.stderr','logs/worker.stderr']:
  if (newroot/n).stat().st_size:raise ValueError('stderr not empty')
 wr=package.read(newroot/'outputs/receipt.json')
 if wr['counts']!={k:v for k,v in cfg['expected_work'].items() if k!='training_sets'} or wr['scope']!='FOUR_OUTER_GROUPS_ONLY_NOT_FULL19':raise ValueError('new work count/scope')
 for item in wr['files_before_receipt']:
  p=newroot/'outputs'/item['path']
  if p.stat().st_size!=item['bytes'] or package.sha(p)!=item['sha256']:raise ValueError('new outputs changed')
 cohort=package.read(code/'frozen_cohort.json')['cases'];data=[];checks=[];sources={}
 for root,groups,counts in [(oldroot,binding['complete_groups'],binding['counts']),(newroot,cfg['outer_groups'],wr['counts'])]:
  values,check,fields=verify_component(root,groups,counts,cohort);data.extend(values);checks.append(check)
  for z in fields:
   key=str(z['case'])+':'+str(z['H'])
   if key in sources:raise ValueError('component overlap')
   sources[key]=str((root/'outputs').resolve())
 fullplan=engine.work_plan(len(set(c['group'] for c in cohort)),len(cohort),len(cfg['H']))
 if len(sources)!=fullplan['outer_rows'] or len(data)!=fullplan['outer_scores']:raise ValueError('full19 coverage')
 grouped=collections.defaultdict(list)
 for z in data:grouped[z['group'],int(z['H']),z['arm']].append(z)
 summaries=[];pairs=[]
 for g in sorted({c['group'] for c in cohort}):
  for h in (10,40):
   pair={'group':g,'H':h}
   for arm in engine.ARMS:
    rr=grouped[g,h,arm];entry={'group':g,'H':h,'arm':arm,'n':len(rr)}
    for k in rr[0]:
     if k not in ('case','group','H','arm'):
      vs=[float(r[k]) for r in rr if r[k] not in ('',None)];entry[k]=float(np.mean(vs)) if vs else None
    summaries.append(entry);pair[arm]=entry['balanced']
   pair['primary_C_minus_A']=pair['SELECT_C']-pair['SELECT_A']
   pair['worst_selected_A_case']=int(max(grouped[g,h,'SELECT_A'],key=lambda r:(float(r['balanced']),-int(r['case'])))['case']);pairs.append(pair)
 out.mkdir(parents=True)
 with (out/'outer_scores.csv').open('x',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
 evidence.write(out/'component_sources.json',{'case_horizon_source':sources,'old_prefix_binding_sha256':package.sha(code/'prefix_binding.json'),'new_package_sha256':digest,'zero_new_fits_or_original_input_reads':True},True)
 counts={k:sum(x['counts'][k] for x in checks) for k in binding['counts']}
 info={'group_scores':summaries,'paired':pairs,'primary_mean':float(np.mean([x['primary_C_minus_A'] for x in pairs])),'counts':counts,'scope':'FULL19_COMPLETED_FROM_IMMUTABLE15_PLUS_NEW4','components':checks,'retrieval_verification':retrieval,'local_storage_accounting':storage,'cumulative_cost':'R002 full1200s including uncheckpointed tail plus separate R003;2166 completed solves not total attempts','limits':'exposed development groups; unknown specimen independence; release steps/current anchor; not fresh confirmation, causal memory or road validation'}
 evidence.write(out/'group_horizon_results.json',info,True)
 check_local_storage(cfg)
 if render:
  import figures
  figures.render(out)
 check_local_storage(cfg,reserve=0)
 return info

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--old-root',required=True);p.add_argument('--new-root',required=True);p.add_argument('--out',required=True);args=p.parse_args();result=assemble(Path(__file__).parent,args.old_root,args.new_root,args.out);print(json.dumps(result,indent=2))
