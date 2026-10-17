#!/usr/bin/env python3
"""Audit actual native joint blocks, derive stop policies, compare unchanged PIDL."""
import argparse,json,csv,subprocess,hashlib,sys,datetime as dt
from pathlib import Path
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import SymLogNorm
from analyze_c1_commit import a,v,scalar,state,same,text
from analyze_s2_isolation import struct_columns
from audit_raw_response_bound import admission as raw_admission,stencil as raw_stencil
from analyze_s2_sum_outer import first_stop,selftest
from run_multicycle_cross_replay import q4_geometry,amor_raw,interp,corr
from audit_phase_tangent import assemble
from localize_endpoint_tight import mechanics_force
from audit_fem_final_residuals import projected_gradient
PROTOCOL='S04-E011-MCSA-r1'
PRODUCER='0a0691ec9b480aa4069258dbf8bb4c15b277f8fd'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def js(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def table(p,rows):
 if not rows:return
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with p.open('w',newline='') as f:q=csv.DictWriter(f,keys);q.writeheader();q.writerows(rows)
def rel(x,y):return float(np.max(abs(x-y)/np.maximum(1,abs(y))))
def snapshot(p):
 with h5py.File(p) as h:
  z=h['request28_snapshot'];uu=a(z,'u_node').T
  assert uu.shape==(86756,2)
  return dict(u=np.r_[uu[:,0],uu[:,1]],d=v(z,'d_node'),raw=a(z,'psi_raw_gp').T,
     history=a(z,'history_vars_old').transpose(2,1,0),cycle=int(scalar(z,'cycle')),substep=int(scalar(z,'substep')),
     load=scalar(z,'load_factor'),committed=bool(scalar(z,'history_committed')) and bool(scalar(z,'damage_committed')),
     nodes=a(z,'node_coords').T,cells=a(z,'connectivity').T.astype(int)-1)
def verify(run):
 r=js(run/'retrieval_verification.json');assert r['all_hashes_and_sizes_match']
 root=run/'retrieved';assert len(r['manifest'])==r['files'] and sum(x['bytes'] for x in r['manifest'])==r['bytes']
 for x in r['manifest']:
  p=root/x['relative'].replace('\\','/');assert p.stat().st_size==x['bytes'] and sha(p)==x['sha256']
 return root,r

def main(z):
 assert not z.out.exists();z.out.mkdir(parents=True)
 repo=Path(__file__).resolve().parents[2];commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip()
 review=js(z.review);assert review['status']=='passed' and review['commit']==commit and review['analysis_sha256']==sha(Path(__file__))
 root,retrieval=verify(z.run);m=js(root/'input_manifest.json');assert m['source_commit']==PRODUCER
 package=js(z.package);oldready=js(z.package.parent/'local_independent_review.json')
 assert oldready['status']=='passed' and oldready['commit']==PRODUCER and oldready['package_manifest_sha256']==sha(z.package)
 assert package['source_commit']==PRODUCER and len(package['files'])==29 and len(package['staging'])==23
 for x in package['files']:
  p=root/x['name'];assert p.stat().st_size==x['bytes'] and sha(p)==x['sha256']
 launch=js(root/'launch_receipt.json');assert launch['commit']==PRODUCER and launch['root']==package['remote_root'] and launch['dirty'] is False and launch['threads']==1
 assert launch['account'].lower()==r'ad\xw436' and launch['run_id']==z.run.name
 assert m['staging']==package['staging'] and m['protocol_revision']=='S04-E011-MCS-r1'
 expected_cases={'c1_common_anchor'}|{f'c{c}_s{s}' for c in [1,20,60,80,83] for s in [2,4]}
 assert {p.name for p in (root/'output/mcs').iterdir() if p.is_dir()}==expected_cases
 tests=js(root/'selftest.json');assert sum(x.get('cases',0) for x in tests.values() if isinstance(x,dict))==64
 io=js(root/'io_preflight.json');assert io['status']=='passed' and io['unique_inputs']==23
 assert (root/'sequence_finished.json').exists() and not (root/'sequence_failure.json').exists()
 inputs={x['role']:root/'inputs'/Path(x['target'].replace('\\','/')).name for x in m['staging']}
 for x in m['staging']:assert sha(inputs[x['role']])==x['sha256']
 texts={p.name:p.read_text() for p in root.glob('*.m')}
 coupled=texts['e011_s2ra_coupled.m'];stop=texts['e011_s2ra_stop.m']
 assert coupled.count('next.policy_pass')==1 and 'if next.policy_pass,stop="policy_tolerance";break;end' in coupled
 assert 'if du==0 && dd==0,stop="exact_stagnation";break;end' in coupled
 assert 'ur/limits.outer_u_tol' in stop and '(ur+dr)/limits.joint_tol' in stop and 'eligible=outer>=1 && value<=1' in stop
 for name in ['e011_s2ra_coupled.m','e011_s2ra_mechanical.m','e011_damage_solve.m','e011_mcs_case.m']:
  assert 'joint_tol' not in texts[name] and 'outer_u_tol' not in texts[name]
 dump(z.out/'dataflow_certificate.json',dict(protocol=PROTOCOL,producer=PRODUCER,modules={k:sha(root/k) for k in texts},selftest=selftest()))
 with h5py.File(inputs['common']) as h:
  nodes=a(h,'node_coords').T;c=a(h,'connectivity').T.astype(int)-1;fu=v(h,'free_dof_u').astype(int)-1;fd=v(h,'free_dof_d').astype(int)-1
 N,B,w,xy=q4_geometry(nodes,c);n=len(nodes);fixedu=np.setdiff1d(np.arange(2*n),fu);fixedd=np.setdiff1d(np.arange(n),fd)
 mass=np.zeros(n)
 for j in range(4):np.add.at(mass,c[:,j],np.einsum('eg,g->e',w,N[:,j]))
 rawB=raw_stencil(nodes,c)
 cross=[];policies=[];cases=[];metrics=[];maps={};ncp=[]
 if z.pidl:
  ncproot,ncpretrieval=verify(z.pidl);ncpcontract=js(ncproot/'root/code/contract.json');ncpready=js(z.ncp_review)
  assert ncpready['status']=='passed' and sha(ncproot/'root/code/contract.json')==ncpready['contract_sha256']
  assert sha(ncproot/'root/code/read_pidl_plateau.py')==ncpready['worker_sha256']
  assert ncpcontract['analysis_commit']==ncpready['commit'] and ncpcontract['source_commit']=='ad749c8bbba8120b3961add989b11427fab86254'
  nlaunch=js(ncproot/'root/launch_receipt.json');assert nlaunch['commit']==ncpready['commit'] and nlaunch['run_id']==z.pidl.name and nlaunch['dirty'] is False and nlaunch['device']=='cpu' and nlaunch['threads']==1
  z.pidl=ncproot/'archive/readout'
  complete=js(z.pidl/'complete.json');receipt=js(z.pidl/'receipt.json')
  assert complete['status']=='completed' and complete['states']==10 and complete['history_commits']==complete['optimizer_steps']==0
  assert receipt['analysis_commit']==ncpready['commit'] and receipt['source_commit']==ncpcontract['source_commit'] and receipt['history_commits']==receipt['optimizer_steps']==0
  assert receipt['original_archive']==ncpcontract['archive'] and receipt['device']=='cpu' and receipt['threads']==1
  ncp=js(z.pidl/'rows.json');assert len(ncp)==10 and {(r['cycle'],r['substep'],r['step']) for r in ncp}=={(c,s,5*(c-1)+s) for c in [1,20,60,80,83] for s in [2,4]}
  trials=js(z.pidl/'trials.json')
  for r in ncp:
   qq=[t for t in trials if t['step']==r['step']]
   assert r['source_objective_readout_pass']==(max(r['original_poststep_component_relative_errors'])<=1e-4)
   assert len(qq)==(8 if r['source_objective_readout_pass'] and r['parameter_gradient_l2']>0 else 0)
   r['direction_evaluations']=len(qq)
   if not qq:r['best_tested_loss_drop']=None;r['lower_fixed_objective_found']=None
  mesh=np.load(z.pidl/'mesh.npz');assert np.max(abs(mesh['node_coords']-nodes))<2e-8 and np.array_equal(mesh['connectivity'],c)
 def fields(u,d):
  raw=amor_raw(u[:n],u[n:],c,B);g=(1-interp(d,c,N))**2
  return dict(u=u,d=d,raw=raw,g=g,active=raw*g)
 def compare(label,F,P,cycle,step):
  r=dict(cycle=cycle,substep=step,fem_state=label)
  for name in ['raw','g','active']:
   f,p=F[name],P[name];sq=float(np.sum(w*(f-p)**2));fn=float(np.sum(w*f*f));pn=float(np.sum(w*p*p))
   r.update({name+'_abs_L2':float(np.sqrt(sq)),name+'_relative_to_FEM':float(np.sqrt(sq/fn)) if fn>1e-30 else None,
      name+'_relative_to_fixed_PIDL':float(np.sqrt(sq/pn)) if pn>1e-30 else None,name+'_correlation':corr(f,p,w),
      name+'_FEM_integral':float(np.sum(w*f)),name+'_PIDL_integral':float(np.sum(w*p))})
  for name,ww in [('u',np.r_[mass,mass]),('d',mass)]:
   r[name+'_abs_L2']=float(np.sqrt(np.sum(ww*(F[name]-P[name])**2)))
  metrics.append(r)
 for folder in sorted((root/'output/mcs').iterdir()):
  if not folder.is_dir():continue
  result=js(folder/'result.json');label=folder.name;anchor=label=='c1_common_anchor';cycle=result['physical_cycle'];sub=result['substep']
  assert result['history_commits']==0 and not result['fatal'] and result['u_calls']<=250 and result['phase_calls']<=250
  with h5py.File(folder/'case.mat') as h:
   pre=state(h['pre']);start={k:v(h['start'],k) for k in ['u','d']};predictor={k:v(h['predictor'],k) for k in ['u','d']}
   if isinstance(h['out'],h5py.Group):
    assert scalar(h['out'],'history_commits')==0 and bool(scalar(h['out'],'policy_pass'))==result['accepted']
    # Native string is opaque MATLAB object; JSON reason is checked against actual stop invariants below.
    assert scalar(h['counts'],'u')==result['u_calls'] and scalar(h['counts'],'d')==result['phase_calls']
    assert scalar(h['out/counts'],'u')+1==result['u_calls'] and scalar(h['out/counts'],'d')==result['phase_calls']
   else:assert not result['accepted']
  if not anchor:
   before=snapshot(inputs[f'c{cycle}_s{sub-1}']);original=snapshot(inputs[f'c{cycle}_s{sub}'])
   for s,ss in [(before,sub-1),(original,sub)]:
    assert s['cycle']==cycle and s['substep']==ss and s['committed'] and np.array_equal(s['nodes'],nodes) and np.array_equal(s['cells'],c)
   for key in ['u','d','raw','history']:assert np.array_equal(pre[key],before[key])
   assert np.isfinite(pre['history']).all() and np.isfinite(pre['lower']).all()
   assert np.array_equal(pre['lower'],before['d']) and pre['version']==5*(cycle-1)+sub-1
   assert np.array_equal(start['u'],pre['u']) and np.array_equal(start['d'],pre['d'])
  else:
   assert result['reference']['pass'] and result['outer']==19
   with h5py.File(inputs['anchor']) as ref,h5py.File(folder/'case.mat') as now:
    same(state(ref['pre']),pre)
    for name,value in [('start',start),('predictor',predictor)]:
     for k,x in value.items():assert np.array_equal(v(ref[name],k),x)
    for key in ['u','d']:assert np.max(abs(v(ref['current'],key)-v(now['current'],key)))<=1e-10
    assert rel(a(ref['current'],'history234'),a(now['current'],'history234'))<=1e-10
    rr,_=raw_admission(v(now['current'],'u'),a(now['current'],'raw').T,v(ref['current'],'u'),a(ref['current'],'raw').T,c,rawB,n);assert rr['pass_new']
  top=np.flatnonzero(abs(nodes[:,1]-nodes[:,1].max())<1e-12)
  assert max(abs(predictor['u'][n+top]-result['target_u']))<1e-12
  q=[];F={};prev=None;native_errors=[]
  paths=sorted(folder.glob('outer_*.mat'))
  if not paths:
   assert not result['accepted'];cases.append(dict(case=label,cycle=cycle,substep=sub,anchor=anchor,strict_accepted=False,strict_stop=result['reason'],first_stops={k:None for k in ['S0V0','S1V0','S0V1','S1V1']},last_vs_first_active_rel_L2=None,complete_blocks=0));continue
  assert [int(p.stem.split('_')[-1]) for p in paths]==list(range(result['outer']+1))
  for k,p in enumerate(paths):
   with h5py.File(p) as h:
    g=h['point'];assert scalar(g,'outer')==k
    u=v(g,'u');d=v(g,'d');raw=a(g,'raw').T
    assert np.isfinite(u).all() and np.isfinite(d).all() and np.all(d>=pre['lower']-1e-12) and np.all(d<=1+1e-12)
    assert np.array_equal(u[fixedu],predictor['u'][fixedu]) and np.array_equal(d[fixedd],start['d'][fixedd])
    ff=fields(u,d);rd,t=assemble(d,ff['raw'],pre['lower'],pre['history'],c,N,B,w,n);ru=mechanics_force(u,d,c,N,B,w,n)
    err=max(rel(ff['raw'],raw),rel(rd,v(g,'rd')),rel(ru,v(g,'ru')),rel(np.stack([t['alpha'],t['active'],t['f']],axis=2),a(g,'history234').transpose(2,1,0)))
    assert err<=1e-10;native_errors.append(err)
    ur=float(np.linalg.norm(ru[fu]));dr=float(np.linalg.norm(projected_gradient(d[fd],rd[fd],pre['lower'][fd])))
    assert abs(ur-scalar(g,'u_l2'))<1e-12 and abs(dr-scalar(g,'d_feasible_l2'))<1e-12
    limits=g['controls/limits']
    for key,val in dict(u_tol=1e-8,d_tol=4e-6,joint_tol=4e-6,outer_u_tol=1e-8,max_outer=20).items():assert scalar(limits,key)==val
    assert scalar(g['controls'],'physical_cycle')==cycle and scalar(g['controls'],'substep')==sub
    u_before=None;reintroduced=None
    if k:
     pp=g['phase_input'];assert np.array_equal(v(pp,'d_before'),prev[1]) and np.array_equal(v(pp,'u_returned'),u) and np.array_equal(v(pp,'u_evaluated'),u)
     u_before=float(np.linalg.norm(mechanics_force(u,prev[1],c,N,B,w,n)[fu]));assert u_before<1e-8
     reintroduced=float(np.linalg.norm((ru-mechanics_force(u,prev[1],c,N,B,w,n))[fu]))
     du=float(np.max(abs(u-prev[0])));dd=float(np.max(abs(d-prev[1])))
    else:
     assert np.array_equal(u,predictor['u']) and np.array_equal(d,start['d']);du=dd=None
    trace=struct_columns(h['trace']) if isinstance(h['trace'],h5py.Group) else {}
    if k:
     for name,value in [('outer',k),('u_l2',ur),('d_fresh_l2',dr),('u_delta_max',du),('d_delta_max',dd)]:
      assert len(trace[name])==k and abs(trace[name][-1]-value)<=1e-12
    assert abs(scalar(g,'criterion')-max((ur+dr)/4e-6,ur/1e-8))<1e-8
    if k==result['outer'] and isinstance(h['trace'],h5py.Group):
     with h5py.File(folder/'case.mat') as endpoint:
      for key in ['u','d','raw','ru','rd','history234']:assert np.array_equal(a(g,key),a(endpoint['current'],key))
      assert scalar(endpoint['out'],'completed_outer')==k
      cu=int(scalar(h['calls'],'u'));cd=int(scalar(h['calls'],'d'));tu=int(scalar(endpoint['out/counts'],'u'));td=int(scalar(endpoint['out/counts'],'d'))
      if result['reason'] in ['displacement_inner_miss','damage_inner_miss']:
       assert cu<=tu and cd<=td and 'last_attempt' in endpoint['out']
       assert ('u_out' if result['reason']=='displacement_inner_miss' else 'd_out') in endpoint['out/last_attempt']
      else:assert cu==tu and cd==td
     assert abs(result['fresh_C']-scalar(g,'criterion'))<1e-8
     assert result['accepted']==bool(k>=1 and max((ur+dr)/4e-6,ur/1e-8)<=1 and result['reason']=='policy_tolerance')
    free_force=np.zeros(2*n);free_force[fu]=ru[fu];force_nodes=free_force[:n]**2+free_force[n:]**2
    fs=float(force_nodes.sum());imax=int(np.argmax(force_nodes))
    r=dict(case=label,cycle=cycle,substep=sub,outer=k,u_l2=ur,d_l2=dr,u_delta_max=du,d_delta_max=dd,u_before_damage=u_before,
       reintroduced_u_force_l2=reintroduced,u_force_wake_squared_share=float(force_nodes[nodes[:,0]<=0].sum()/fs) if fs else None,
       u_force_max_x=float(nodes[imax,0]),u_force_max_y=float(nodes[imax,1]),active_integral=float(np.sum(w*ff['active'])),f_min=float(t['f'].min()),
       u_calls=int(scalar(h['calls'],'u'))+1,phase_calls=int(scalar(h['calls'],'d')),native_error=err)
    assert r['u_calls']<=250 and r['phase_calls']<=250
    q.append(r);F[k]=ff;prev=u,d
   print('AUDIT',label,k,ur,dr,flush=True)
  cross.extend(q);chosen={}
  if result['accepted']:assert first_stop(q,1,1)[0]==result['outer']
  elif result['reason']=='outer_budget':assert result['outer']==20 and first_stop(q,1,1)[0] is None
  elif result['reason']=='exact_stagnation':assert q[-1]['u_delta_max']==q[-1]['d_delta_max']==0
  for s,vv in [(0,0),(1,0),(0,1),(1,1)]:
   key=f'S{s}V{vv}';k,why=first_stop(q,s,vv);chosen[key]=k
   policies.append(dict(case=label,cycle=cycle,substep=sub,policy=key,first_outer=k,reason=why,source_strict_accepted=result['accepted']))
  eligible=[r for r in q if r['outer']>=1]
  bottleneck=[r for r in eligible if r['u_l2']+r['d_l2']>4e-6 or r['u_l2']>1e-8]
  row=dict(case=label,cycle=cycle,substep=sub,anchor=anchor,strict_accepted=result['accepted'],strict_stop=result['reason'],last_complete=result['outer'],
      first_stops=chosen,preaccept_blocks=len(bottleneck),damage_pass_preaccept=sum(r['d_l2']<=4e-6 for r in bottleneck),
      u_fails_preaccept=sum(r['u_l2']>1e-8 for r in bottleneck),max_native_error=max(native_errors),
      final_u=q[-1]['u_l2'],final_d=q[-1]['d_l2'],inner_failure=bool(result['reason'] not in ['policy_tolerance','outer_budget','exact_stagnation']))
  row['last_vs_first_active_rel_L2']=None
  if 1 in F:
   A0=F[1]['active'];end=F[result['outer']]['active'];den=float(np.sum(w*A0*A0));sq=float(np.sum(w*(end-A0)**2))
   row['last_vs_first_active_rel_L2']=float(np.sqrt(sq/den)) if den>1e-30 else None
   row['change_wake_squared_share']=float(np.sum((w*(end-A0)**2)[xy[:,:,0]<=0])/sq) if sq else None
  row['stopping_gate_pattern']='same_observed_first_crossing' if chosen['S1V0'] is not None and chosen['S1V0']==chosen['S0V1']==chosen['S1V1'] else ('both_strict_crossings_missing' if chosen['S1V0'] is None and chosen['S0V1'] is None else 'different_first_crossings')
  row['source_reference_pass_required']=anchor
  cases.append(row)
  if anchor:continue
  O=fields(original['u'],original['d']);rd,tt=assemble(original['d'],O['raw'],pre['lower'],pre['history'],c,N,B,w,n)
  row['original_u']=float(np.linalg.norm(mechanics_force(original['u'],original['d'],c,N,B,w,n)[fu]))
  row['original_d']=float(np.linalg.norm(projected_gradient(original['d'][fd],rd[fd],pre['lower'][fd])))
  row['archived_post_history234_scaled_mapping_gap']=rel(np.stack([tt['alpha'],tt['active'],tt['f']],axis=2),original['history'][:,:,1:4])
  if z.pidl:
   pp=np.load(z.pidl/'fields'/f'c{cycle}_s{sub}.npz');P=fields(np.r_[pp['u'].reshape(-1),pp['v'].reshape(-1)],pp['d'].reshape(-1))
   comparisons=[('original',O),('strict_accepted' if result['accepted'] else 'strict_last_MISS',F[result['outer']])]
   if 1 in F:comparisons.append(('first_complete',F[1]))
   for name,ff in comparisons:compare(name,ff,P,cycle,sub)
   nr=next(r for r in ncp if r['cycle']==cycle and r['substep']==sub)
   nr['own_free_u_energy_gradient_l2']=float(np.linalg.norm(np.r_[pp['own_energy_gradient_u'].reshape(-1),pp['own_energy_gradient_v'].reshape(-1)][fu]))
   nr['own_free_d_energy_gradient_l2']=None
   nr['own_nodal_damage_gradient_valid']=False
   nr['own_nodal_damage_gradient_issue']='Producer348be4b retain_grad accumulated component autograd.grad contributions before backward; raw array preserved, excluded from scoring.'
   nr['common_operator_PIDL_free_u_l2']=float(np.linalg.norm(mechanics_force(P['u'],P['d'],c,N,B,w,n)[fu]))
   if sub==4:maps[cycle]=(O,F[result['outer']],P,result['accepted'])
 table(z.out/'crossings.csv',cross);table(z.out/'policies.csv',policies);table(z.out/'fem_pidl_fields.csv',metrics)
 dump(z.out/'cases.json',cases);dump(z.out/'pidl_plateau.json',ncp)
 dump(z.out/'summary.json',dict(protocol=PROTOCOL,analysis_commit=commit,producer=PRODUCER,cases=cases,retrieval_files=retrieval['files'],retrieval_bytes=retrieval['bytes'],
  new_native_solve=False,history_commits=0,trajectory='conditional original-history restarts; no propagated repaired trajectory',pidl=str(z.pidl) if z.pidl else None))
 draw(z.out,cases,cross,policies,metrics,ncp,maps,nodes,c,w)
 (z.out/'README_analysis.md').write_text('''# Cross-cycle fixed-history solver control and unchanged PIDL

Question: do damage updates reintroduce mechanics imbalance, and do two outer stopping gates remain redundant across stages? Native evidence: MCS producer0a0691e; every retrieved byte verified; source stop-only dataflow and Q4/GP residuals independently recomputed. Actual complete native blocks only; missing policy crossing stays missing; strict budget misses are not accepted FEM solutions. c1 common anchor is separate from natural c1 restarts. No history commits or continuous repaired trajectory.

Read mcs_control.png first: stage-specific observed residuals and four first-policy crossings. Then fem_pidl_comparison.png: original/strict FEM vs unchanged same-state PIDL under common operators; hollow markers mean strict last MISS, not improved teacher. fem_pidl_maps.png shows aligned reference/prediction/signed error maps on common axes. pidl_plateau.png shows original-loss stopping traces and original-objective directional readout. Tables and cases.json authoritative.

Allowed: conditional solver-control sensitivities, common-operator field gaps and own-objective descent availability. Blocked: selecting FEM by agreement with PIDL; stitched repaired evolution, unique physical teacher, causal percentage allocation, or certifying convergence from loss plateau. Original baseline evolution and local repaired endpoints are distinct. Spatial/commit-state alignment does not remove fixed committed-f vs trial-f or joint NN Deep-Ritz vs staggered/Picard differences. No accepted PIDL update or optimizer continuation occurred. Producer348be4b nodal damage gradient export is INVALID because retain_grad accumulates three component autograd.grad contributions before backward; preserve raw arrays but exclude this metric. Network parameter gradients/directions and independent common-operator force are unaffected; u/v agreement independently checked.
''')
 for png in z.out.glob('*.png'):
  png.with_suffix('.md').write_text((z.out/'README_analysis.md').read_text()+'\nFigure: '+png.name+'; exact tables/summary in this directory. Map colour ranges differ across cycle rows; within each row reference and PIDL share a scale, signed gaps share a separate symmetric scale. Source-readout mismatches have no directional-loss bar, not zero gain.\n')
 print('ANALYSIS_COMPLETE',z.out,flush=True)

def draw(out,cases,rows,policies,metrics,ncp,maps,nodes,c,w):
 natural=[r for r in cases if not r['anchor']];natural.sort(key=lambda r:(r['cycle'],r['substep']));labels=[r['case'] for r in natural]
 fig,axs=plt.subplots(2,2,figsize=(13,8))
 for sub,ax in [(2,axs[0,0]),(4,axs[0,1])]:
  for r in natural:
   if r['substep']!=sub:continue
   q=[v for v in rows if v['case']==r['case'] and v['outer']>=1]
   line=ax.semilogy([v['outer'] for v in q],[max(v['u_l2'],1e-18) for v in q],'.-',label=f"c{r['cycle']} Ru"+(' MISS' if not r['strict_accepted'] else ''))[0]
   ax.semilogy([v['outer'] for v in q],[max(v['d_l2'],1e-18) for v in q],':',color=line.get_color(),alpha=.6)
  ax.axhline(1e-8,color='k',ls='--',lw=.7);ax.axhline(4e-6,color='grey',ls='--',lw=.7);ax.set_title(f's{sub}: after-damage Ru solid / feasible Rd dotted');ax.set_xlabel('Complete outer (not time)');ax.set_ylabel('free residual L2');ax.legend(fontsize=7)
 for j,key in enumerate(['S0V0','S1V0','S0V1','S1V1']):
  vals=[r['first_stops'][key] for r in natural];axs[1,0].plot(np.arange(len(natural))+.07*j,[np.nan if v is None else v for v in vals],'.-',label=key)
 axs[1,0].set_xticks(range(len(labels)),labels,rotation=45,ha='right');axs[1,0].set_ylabel('First eligible outer; missing is not extrapolated');axs[1,0].legend(fontsize=7)
 axs[1,1].bar(range(len(natural)),[100*r['last_vs_first_active_rel_L2'] if r.get('last_vs_first_active_rel_L2') is not None else np.nan for r in natural],color=['#0072B2' if r['strict_accepted'] else '#D55E00' for r in natural]);axs[1,1].set_xticks(range(len(labels)),labels,rotation=45,ha='right');axs[1,1].set_ylabel('FEM last vs first active weighted L2 / first (%)');axs[1,1].set_title('Orange = last complete MISS; FEM self-change')
 fig.suptitle('S04-E011 MCS | original predecessor frozen; no propagated trajectory');fig.tight_layout();fig.savefig(out/'mcs_control.png',dpi=170);plt.close(fig)
 if not metrics:return
 fig,axs=plt.subplots(2,2,figsize=(12,8))
 for sub,col in [(2,0),(4,1)]:
  for key,mark in [('original','o'),('strict_accepted','s'),('strict_last_MISS','x')]:
   q=sorted([r for r in metrics if r['substep']==sub and r['fem_state']==key],key=lambda r:r['cycle'])
   axs[0,col].plot([r['cycle'] for r in q],[r['active_relative_to_fixed_PIDL'] for r in q],mark,ls='none',label=key)
   axs[1,col].plot([r['cycle'] for r in q],[r['active_FEM_integral'] for r in q],mark,ls='none',label=key)
  q=sorted([r for r in metrics if r['substep']==sub and r['fem_state']=='original'],key=lambda r:r['cycle'])
  axs[1,col].plot([r['cycle'] for r in q],[r['active_PIDL_integral'] for r in q],'D:',label='unchanged PIDL')
  axs[0,col].set_title(f's{sub}: common Q4/GP active field');axs[0,col].set_ylabel('weighted gap / fixed PIDL norm');axs[1,col].set_ylabel('Active integral');axs[1,col].set_xlabel('Cycle (independent conditional states)')
  for ax in axs[:,col]:ax.legend(fontsize=8);ax.grid(alpha=.2)
 fig.tight_layout();fig.savefig(out/'fem_pidl_comparison.png',dpi=170);plt.close(fig)
 if maps:
  chosen=[k for k in [1,60,83] if k in maps];fig,axs=plt.subplots(len(chosen),4,figsize=(15,4*len(chosen)),squeeze=False)
  for i,k in enumerate(chosen):
   O,T,P,accepted=maps[k];ref=T if accepted else O
   vals=[np.sum(w*f['active'],axis=1)/w.sum(1) for f in [ref,P]];vm=max(float(x.max()) for x in vals)
   errs=[P['active']-ref['active'],T['active']-O['active']];ec=[np.sum(w*x,axis=1)/w.sum(1) for x in errs];ev=max(max(float(abs(x).max()) for x in ec),1e-15);vm=max(vm,1e-15)
   for j,(val,title) in enumerate(zip(vals+ec,[('strict accepted FEM' if accepted else 'original FEM (strict MISS)'), 'unchanged PIDL','PIDL - reference','strict last - original'+(' (MISS)' if not accepted else '')])):
    norm=SymLogNorm(max((vm if j<2 else ev)*1e-5,1e-15),vmin=0 if j<2 else -ev,vmax=vm if j<2 else ev)
    pc=PolyCollection(nodes[c],array=val,norm=norm,cmap='viridis' if j<2 else 'RdBu_r',edgecolors='none');ax=axs[i,j];ax.add_collection(pc);ax.autoscale();ax.set_aspect('equal');ax.set_title(f'c{k}s4 {title}',fontsize=9);ax.set_xlabel('native x');ax.set_ylabel('native y');cb=fig.colorbar(pc,ax=ax,shrink=.65)
    if j>=2:
     ticks=[-ev,-ev*.01,0,ev*.01,ev];cb.set_ticks(ticks);cb.set_ticklabels(['0' if x==0 else f'{x:.1e}' for x in ticks])
  fig.suptitle('Active cell means / signed gaps; colour limits common within each row, differ across cycles',fontsize=9);fig.tight_layout();fig.savefig(out/'fem_pidl_maps.png',dpi=150);plt.close(fig)
 if ncp:
  ncp.sort(key=lambda r:(r['cycle'],r['substep']));labs=[f"c{r['cycle']}s{r['substep']}" for r in ncp];x=np.arange(len(ncp));fig,axs=plt.subplots(2,2,figsize=(13,8))
  axs[0,0].bar(x,[r['epochs'] for r in ncp]);axs[0,0].set_ylabel('Original RPROP iterations')
  for key in ['parameter_gradient_l2','physical_log_parameter_gradient_l2','reg_parameter_gradient_l2']:axs[0,1].semilogy(x,[r[key] if r['source_objective_readout_pass'] else np.nan for r in ncp],'o-',label=key.replace('_parameter_gradient_l2',''))
  axs[0,1].legend(fontsize=7);axs[0,1].set_ylabel('Source-qualified objective gradient norm')
  for i,r in enumerate(ncp):
   if not r['source_objective_readout_pass']:axs[0,1].annotate('source mismatch',(i,.5),xycoords=('data','axes fraction'),rotation=90,fontsize=7,ha='center')
  axs[1,0].bar(x,[r['best_tested_loss_drop'] if r['source_objective_readout_pass'] and r['best_tested_loss_drop'] is not None else np.nan for r in ncp]);axs[1,0].plot(x,[r['direction_loss_roundoff_floor'] for r in ncp],'k--',label='declared roundoff screen');axs[1,0].legend(fontsize=7);axs[1,0].set_ylabel('Independent normalized -gradient loss drop')
  axs[1,1].semilogy(x,[max(r['common_operator_PIDL_free_u_l2'],1e-18) for r in ncp],'o-',label='common Q4 free-u force (all fields)');axs[1,1].plot(x,[np.nan for r in ncp],'s-',label='nodal d gradient INVALID (excluded)');axs[1,1].axhline(1e-8,color='k',ls='--',lw=.7);axs[1,1].legend(fontsize=7);axs[1,1].set_ylabel('Nodal L2; force is independent of objective replay')
  for ax in axs.ravel():ax.set_xticks(x,labs,rotation=45,ha='right');ax.grid(alpha=.2)
  fig.suptitle('Unchanged PIDL checkpoint readout | no optimizer steps/history commits');fig.tight_layout();fig.savefig(out/'pidl_plateau.png',dpi=170);plt.close(fig)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--package',type=Path,required=True);ap.add_argument('--ncp-review',type=Path);ap.add_argument('--run',type=Path,required=True);ap.add_argument('--pidl',type=Path);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--review',type=Path,required=True);main(ap.parse_args())
