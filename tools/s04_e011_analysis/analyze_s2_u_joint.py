#!/usr/bin/env python3
"""Offline S2UJ native-state audit; no solves or interpolation of absent arms."""
import argparse,json
from pathlib import Path
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize,SymLogNorm
from analyze_s2_isolation import sha,dump,table,jsonfile,struct_columns
from analyze_c1_commit import a,v,scalar,state,same
from run_multicycle_cross_replay import q4_geometry,amor_raw
from audit_phase_tangent import assemble
from localize_endpoint_tight import mechanics_force
from audit_fem_final_residuals import projected_gradient
from audit_raw_response_bound import admission as raw_admission,stencil as raw_stencil

def relative(x,y):return float(np.max(abs(x-y)/np.maximum(1,abs(y))))
def norm(g,key):return float(np.linalg.norm(g[key]))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',required=True,type=Path);ap.add_argument('--package',required=True,type=Path);args=ap.parse_args()
 run=args.run;root=run/'retrieved';base=root/'output/s2uj';out=run/'analysis';out.mkdir(exist_ok=True)
 receipt=jsonfile(run/'retrieval_verification.json');assert receipt['all_hashes_and_sizes_match'] and receipt['files']==len(receipt['manifest']) and receipt['bytes']==sum(t['bytes'] for t in receipt['manifest'])
 for t in receipt['manifest']:
  p=root/t['relative'].replace('\\','/');assert p.stat().st_size==t['bytes'] and sha(p)==t['sha256']
 package=jsonfile(args.package);review=jsonfile(args.package.parent/'local_independent_review.json')
 assert review['status']=='passed' and review['commit']==package['source_commit'] and review['package_manifest_sha256']==sha(args.package)
 for t in package['files']:
  p=root/t['name'];assert p.stat().st_size==t['bytes'] and sha(p)==t['sha256']
 launch=jsonfile(root/'launch_receipt.json');manifest=jsonfile(root/'input_manifest.json')
 assert launch['commit']==manifest['source_commit']==package['source_commit'] and launch['dirty'] is False and launch['threads']==1
 assert launch['root']==package['remote_root'] and launch['account'].lower()==r'ad\xw436'
 assert manifest['protocol_revision']=='S04-E011-S2UJ-r1' and manifest['staging']==package['staging']
 inputs={t['role']:root/'inputs'/Path(t['target'].replace('\\','/')).name for t in manifest['staging']}
 for t in manifest['staging']:
  p=inputs[t['role']];assert p.stat().st_size==t['bytes'] and sha(p)==t['sha256']
 if not all((root/t).exists() for t in ['selftest.json','io_preflight.json']):
  dump(out/'s2uj_analysis.json',dict(status='prerequisites_not_reached',planned=[dict(case=k,status='NOT RUN') for k in ['00','10','01','11']],contrasts=[],symmetric_algebraic_allocation=[],failure=jsonfile(root/'sequence_failure.json') if (root/'sequence_failure.json').exists() else None));return
 tests=jsonfile(root/'selftest.json')
 for name,number in [('damage',6),('coupled',6),('commit',10),('raw',12),('refresh_accuracy',14),('damage_joint',8),('u_joint',8)]:assert tests[name]['status']=='passed' and tests[name]['cases']==number
 assert jsonfile(root/'io_preflight.json')['unique_inputs']==7
 with h5py.File(inputs['common']) as h:
  nodes=a(h,'node_coords').T;c=a(h,'connectivity').T.astype(int)-1;fu=v(h,'free_dof_u').astype(int)-1;fd=v(h,'free_dof_d').astype(int)-1
 n=len(nodes);N,B,w,xy=q4_geometry(nodes,c);stencil=raw_stencil(nodes,c)
 with h5py.File(inputs['O1']) as h:pre=state(h['proposed'])
 with h5py.File(inputs['R1']) as h:other=state(h['proposed'])
 start={'u':pre['u'],'d':np.maximum(pre['d'],other['d'])};predictor=None
 with h5py.File(inputs['scale_reference']) as h:
  same(state(h['pre']),pre);same({k:v(h['start'],k) for k in ['u','d']},start)
  parent_predictor={k:v(h['predictor'],k) for k in ['u','d','r']};g=h['current'];uu=v(g,'u');dd=v(g,'d');raw=a(g,'raw').T
  assert relative(raw,amor_raw(uu[:n],uu[n:],c,B))<=1e-10
  rd,t=assemble(dd,raw,pre['lower'],pre['history'],c,N,B,w,n);ru=mechanics_force(uu,dd,c,N,B,w,n)
  h234=np.stack([t['alpha'],t['active'],t['f']],axis=2)
  parent_error=max(relative(rd,v(g,'rd')),relative(ru,v(g,'ru')),relative(h234,a(g,'history234').transpose(2,1,0)))
  assert parent_error<=1e-10 and int(scalar(g,'outer'))==1
  parent_field=t['active'];parent_norm=float(np.sum(w*parent_field**2))
 parent_normalization=dict(role='scale_reference',source_case='S2DJ_P0J0',input_sha256=next(t['sha256'] for t in manifest['staging'] if t['role']=='scale_reference'),weighted_squared_norm=parent_norm,native_replay_scaled_maxerr=parent_error)

 fields={};firstfields={};blockfields={};rows=[];outers=[];timing=[];ledgers=[];anchors=[];planned=[]
 fixedu=np.setdiff1d(np.arange(2*n),fu);fixedd=np.setdiff1d(np.arange(n),fd)
 def feasible(d,rd):return float(np.linalg.norm(projected_gradient(d[fd],rd[fd],pre['lower'][fd])))
 def replay(d,raw):
  rd,t=assemble(d,raw,pre['lower'],pre['history'],c,N,B,w,n)
  return rd,np.stack([t['alpha'],t['active'],t['f']],axis=2),t
 def point(g,U,J):
  R=1;A=J;controls=g['controls'];limits=controls['limits']
  assert scalar(controls,'U')==U and scalar(controls,'J')==J and scalar(controls,'refresh')==1
  expected_limits={'max_u':248,'max_d':248,'max_outer':20,'u_tol':1e-8 if U else 1e-6,'d_tol':4e-6,'joint_tol':4e-6 if J else 4e-4,'outer_u_tol':1e-8 if J else 4e-4}
  for key,value in expected_limits.items():assert scalar(limits,key)==value
  u=v(g,'u');d=v(g,'d');raw=a(g,'raw').T;k=int(scalar(g,'outer'));assert np.isfinite(u).all() and np.isfinite(d).all()
  assert np.all(d>=pre['lower']-1e-12) and np.all(d<=1+1e-12)
  assert np.array_equal(u[fixedu],predictor['u'][fixedu]) and np.array_equal(d[fixedd],start['d'][fixedd])
  expected=amor_raw(u[:n],u[n:],c,B);rawerr=relative(raw,expected);assert rawerr<=1e-10
  rd,hh,t=replay(d,raw);ru=mechanics_force(u,d,c,N,B,w,n)
  err=max(relative(rd,v(g,'rd')),relative(ru,v(g,'ru')));herr=relative(hh,a(g,'history234').transpose(2,1,0));assert err<=1e-10 and herr<=1e-10
  ur=float(np.linalg.norm(ru[fu]));dr=feasible(d,rd);cached=float(scalar(g,'d_cached_l2'))
  if k:
   p=g['phase_input'];ue=v(p,'u_evaluated');ut=v(p,'u_returned');db=v(p,'d_before');ri=a(p,'raw').T;rb=a(p,'fresh_before_raw').T
   assert np.array_equal(ut,u) and (R==0 or np.array_equal(ue,ut))
   raw_input_err=relative(ri,amor_raw(ue[:n],ue[n:],c,B));raw_before_err=relative(rb,expected)
   rue=mechanics_force(ue,db,c,N,B,w,n);rub=mechanics_force(ut,db,c,N,B,w,n)
   rd0,hh0,_=replay(d,ri);ce=max(relative(rd0,v(p,'cached_rd')),relative(hh0,a(p,'cached_history234').transpose(2,1,0)))
   rbe=relative(rub,v(p,'fresh_before_ru'));crnorm=float(np.linalg.norm(rue[fu]));saved=float(scalar(p,'cached_u_residual_l2'))
   assert max(raw_input_err,raw_before_err,ce,rbe,abs(crnorm-saved))<=1e-10
   assert abs(feasible(d,rd0)-cached)<=1e-10
   rt=relative(ri,rb);dm=relative(raw,rb)
   assert abs(rt-scalar(g,'raw_timing_scaled_maxerr'))<=1e-10 and abs(dm-scalar(g,'raw_damage_scaled_maxerr'))<=1e-10
   assert saved<expected_limits['u_tol'] and feasible(d,rd0)<=4e-6+1e-15
   timing.append(dict(case=f'{U}{J}',outer=k,u_return_minus_evaluated_max=float(np.max(abs(ut-ue))),cached_u_l2=crnorm,fresh_before_u_l2=float(np.linalg.norm(rub[fu])),raw_timing_scaled_maxerr=rt,raw_damage_scaled_maxerr=dm,d_cached_l2=cached,d_fresh_l2=dr,phase_norm_difference=abs(cached-dr),crossing_old=(cached<=4e-4)!=(dr<=4e-4),crossing_tight=(cached<=4e-6)!=(dr<=4e-6),native_replay_maxerr=max(raw_input_err,raw_before_err,ce,rbe)))
  chosen=dr if R else cached;jtol=4e-6 if A else 4e-4;utol=1e-8 if A else 4e-4
  PC=max((ur+chosen)/jtol,ur/utol);C=max((ur+dr)/4e-6,ur/1e-8)
  assert abs(C-scalar(g,'criterion'))<=1e-8*max(1,C) and abs(PC-scalar(g,'policy_C'))<=1e-8*max(1,PC)
  assert bool(scalar(g,'policy_pass'))==(k>=1 and PC<=1)
  return t['active'],dict(outer=k,fresh_C=C,policy_C=PC,joint_component=(ur+dr)/jtol,outer_u_component=ur/utol,inner_u_returned_l2=float(scalar(g['phase_input'],'cached_u_residual_l2')) if k else None,u_l2=ur,d_fresh_l2=dr,d_cached_l2=cached,active_integral=float(np.sum(w*t['active'])),f_min=float(t['f'].min()),native_residual_scaled_maxerr=err,history_scaled_maxerr=herr,raw_scaled_maxerr=rawerr)
 for name in ['00','11','10','01']:
  folder=base/('U'+name[0]+'J'+name[1])
  if not all((folder/t).exists() for t in ['case.mat','result.json']):planned.append(dict(case=name,status='NOT RUN'));continue
  result=jsonfile(folder/'result.json');U,J=map(int,name);assert result['U']==U and result['J']==J and result['refresh']==1 and result['history_commits']==0
  assert result['u_calls']<=249 and result['phase_calls']<=248
  planned.append(dict(case=name,status='FATAL' if result['fatal'] else ('accepted' if result['accepted'] else 'MISS'),reason=result['reason']))
  if result['fatal']:continue
  with h5py.File(folder/'case.mat') as h:
   same(state(h['pre']),pre);same({k:v(h['start'],k) for k in ['u','d']},start)
   if not isinstance(h['current'],h5py.Group) or not isinstance(h['out'],h5py.Group):
    planned[-1]['status']='NO AUDITABLE POINT';continue
   pr={k:v(h['predictor'],k) for k in ['u','d','r']}
   if predictor is not None:same(pr,predictor)
   predictor=pr;same(predictor,parent_predictor)
   assert int(scalar(h['counts'],'u'))==result['u_calls']==int(scalar(h['out']['counts'],'u'))+1
   assert int(scalar(h['counts'],'d'))==result['phase_calls']==int(scalar(h['out']['counts'],'d'))
   final,q=point(h['current'],U,J);fields[name]=final
   assert q['outer']==result['outer']==scalar(h['out'],'completed_outer')
   assert abs(q['fresh_C']-result['fresh_C'])<=1e-8*max(1,q['fresh_C']) and abs(q['policy_C']-result['policy_C'])<=1e-8
   assert scalar(h['out'],'history_commits')==0
   assert bool(scalar(h['out'],'policy_pass'))==result['accepted'] and (not result['accepted'] or (q['outer']>=1 and q['policy_C']<=1))
   if name in ['00','11']:
    assert result['reference']['pass']
    with h5py.File(inputs['anchor'+name]) as ref:
     g=ref['current'];errors=[float(np.max(abs(v(h['current'],k)-v(g,k)))) for k in ['u','d']]
     errors.append(relative(a(h['current'],'history234'),a(g,'history234')))
     rawcheck,_=raw_admission(v(h['current'],'u'),a(h['current'],'raw').T,v(g,'u'),a(g,'raw').T,c,stencil,n)
     assert max(errors)<=1e-10 and rawcheck['pass_new'] and scalar(g,'outer')==q['outer']
     anchors.append(dict(case=name,maxerr=max(errors),raw_r4_pass=True,outer=q['outer']))
   previous_d=None
   for p in sorted(folder.glob('outer_*.mat')):
    with h5py.File(p) as z:
     active,oq=point(z['point'],U,J);outers.append(dict(case=name,**oq));blockfields[(name,oq['outer'])]=active
     if oq['outer']==0:
      assert np.array_equal(v(z['point'],'u'),predictor['u']) and np.array_equal(v(z['point'],'d'),start['d'])
     else:assert np.array_equal(v(z['point']['phase_input'],'d_before'),previous_d)
     previous_d=v(z['point'],'d')
     if oq['outer']==1:firstfields[name]=active
   own=[t for t in outers if t['case']==name];assert [t['outer'] for t in own]==list(range(q['outer']+1))
   with h5py.File(folder/f"outer_{q['outer']:02d}.mat") as last:
    for k in ['u','d','raw','ru','rd','history234']:assert np.array_equal(a(last['point'],k),a(h['current'],k))
   led=struct_columns(h['ledger']);assert np.array_equal(led['call'],np.arange(1,result['phase_calls']+1))
   assert all(np.isfinite(t).all() for t in led.values())
   assert max(led['lower_violations'])==max(led['upper_violations'])==0
   for j in range(len(led['call'])):ledgers.append(dict(case=name,**{k:float(t[j]) for k,t in led.items()}))
   rows.append(dict(case=name,U=U,J=J,accepted=result['accepted'],reason=result['reason'],u_calls=result['u_calls'],phase_calls=result['phase_calls'],**q,trial_alpha_max=float(max(led['alpha_max'])),trial_f_min=float(min(led['f_min']))))
   print('AUDITED',name,result['accepted'],q['fresh_C'],flush=True)
 # Each terminal point was replayed twice for final/trajectory consistency; timing rows deduplicated.
 timing=list({(t['case'],t['outer']):t for t in timing}.values())
 by={r['case']:r for r in rows};contrasts=[];allocation=[]
 reference=fields.get('00');norm0=float(np.sum(w*reference**2)) if reference is not None else None
 total=fields['11']-reference if reference is not None and '11' in fields else None;gapnorm=float(np.sum(w*total**2)) if total is not None else None
 def contrast(label,left,right,kind,baseline):
  d=right-left;norm=float(np.sum(w*d*d));ij=np.unravel_index(np.argmax(abs(d)),w.shape)
  return dict(contrast=label,kind=kind,weighted_relL2_to_left=float(np.sqrt(norm/np.sum(w*left*left))),weighted_relL2_to_common00=float(np.sqrt(norm/np.sum(w*baseline**2))),weighted_relL2_to_parent00=float(np.sqrt(norm/parent_norm)),signed_integral=float(np.sum(w*d)),projection_on_diagonal_endpoint_total=float(np.sum(w*d*total)/gapnorm) if gapnorm else None,wake_squared_share=float(np.sum((w*d*d)[xy[:,:,0]<=0])/norm) if norm else 0.,max_absolute_gap=float(abs(d[ij])),x=float(xy[ij][0]) if norm else None,y=float(xy[ij][1]) if norm else None)
 pairs=[('U_at_J0','00','10'),('U_at_J1','01','11'),('J_at_U0','00','01'),('J_at_U1','10','11'),('total','00','11')]
 for label,lo,hi in pairs:
  if norm0 and lo in fields and hi in fields:
   kind='accepted_policy_endpoint' if by[lo]['accepted'] and by[hi]['accepted'] else 'last_complete_not_both_accepted'
   contrasts.append(contrast(label,fields[lo],fields[hi],kind,reference))
  if '00' in firstfields and lo in firstfields and hi in firstfields:
   contrasts.append(contrast(label,firstfields[lo],firstfields[hi],'first_completed_outer',firstfields['00']))
 for label,lo,hi in pairs:
  common=sorted({k for name,k in blockfields if name==lo} & {k for name,k in blockfields if name==hi})
  for k in common:
   if k<1 or reference is None:continue
   row=contrast(label,blockfields[(lo,k)],blockfields[(hi,k)],'same_completed_outer',reference);row['outer']=k
   # Keep CSV schema stable: every contrast has outer, null for endpoint-class rows.
   contrasts.append(row)
 for row in contrasts:row.setdefault('outer',None)
 interaction=None
 if gapnorm and all(k in by and by[k]['accepted'] for k in ['00','10','01','11']):
  PP=.5*((fields['10']-fields['00'])+(fields['11']-fields['01']));JJ=.5*((fields['01']-fields['00'])+(fields['11']-fields['10']))
  assert relative(PP+JJ,total)<=1e-12
  for label,effect in [('U',PP),('J',JJ)]:allocation.append(dict(factor=label,signed_projection_on_total=float(np.sum(w*effect*total)/gapnorm),weighted_L2_relative_to_total=float(np.sqrt(np.sum(w*effect**2)/gapnorm))))
  it=fields['11']-fields['10']-fields['01']+fields['00'];interaction=dict(weighted_L2_to_00=float(np.sqrt(np.sum(w*it**2)/norm0)))
 for r in rows:r['active_relL2_to_00']=float(np.sqrt(np.sum(w*(fields[r['case']]-reference)**2)/norm0)) if norm0 else None
 table(out/'cases.csv',rows);table(out/'completed_outers.csv',outers);table(out/'timing.csv',timing);table(out/'phase_calls.csv',ledgers);table(out/'contrasts.csv',contrasts)
 done=(root/'sequence_finished.json').exists();assert not done or len(planned)==4
 summary=dict(parent_normalization=parent_normalization,status='four_case_complete' if done and len(rows)==4 else 'partial_terminal',producer_commit=package['source_commit'],cases=rows,planned=planned,anchors=anchors,contrasts=contrasts,symmetric_algebraic_allocation=allocation,interaction=interaction,history_commits=0,unique_complete_points=len(outers),complete_blocks=len(timing),timing_max={k:max((t[k] for t in timing),default=None) for k in ['raw_timing_scaled_maxerr','raw_damage_scaled_maxerr','phase_norm_difference','native_replay_maxerr','u_return_minus_evaluated_max']},phase_threshold_crossings=sum(t['crossing_old'] or t['crossing_tight'] for t in timing),definition='Fixed freshR1/constrainedD1/nativep2. U=inneru tolerance; J=jointsum/outeru thresholds; phase4e-6fixed. All arms require a complete block. Firstblock common00first norm distinct from endpoint norm. Miss states are last complete, never accepted. No fullallocation if any miss. No physical/teacher/multicycle claim.',analysis_code=dict(path=str(Path(__file__).resolve()),sha256=sha(Path(__file__).resolve())))
 dump(out/'s2uj_analysis.json',summary)
 draw(out,nodes,c,w,fields,rows,outers,timing,contrasts,run.name)
 (out/'README_analysis.md').write_text('# c1s2 inner u versus joint/outer-u stopping\n\nScientific question: strictphase4e-6/fresh/constrained/nativep2 fixed, separate Uinneru1e-6/1e-8 fromJjointsum/outeru(4e-4,4e-4)/(4e-6,1e-8). SameO1/commonstart/predictor.\n\nData provenance: '+run.name+'; producer '+package['source_commit']+'; exactinput/package/retrieval and nativeoperator/controls/timing replays in s2uj_analysis.json. Seventhscale_reference=oldS2DJ00 independentlyreplayed, neverevolved. New00=S2DJ10; newdiagonal75.72% andparent55.90% shareadifferencevector butdifferentnorms. CSV exactnativeGP/Jacobian, nointerpolation.\n\nReadingorder: s2uj_decision.png own/strictC,firstblockandacceptedendpoint conditionaldifferences usingnew00FIRST/ENDPOINT respectively. s2uj_fields.png nativefirst/end/lastcompletefields+conditionalmaps, explicitmisslabels. s2uj_trajectory.png allcompleteRu/Rd/C/active. s2uj_inner_outer.png returnedinneru and normalizedjoint/outerucomponents. Exacttables alsoinclude actualsavedcommon-outer contrasts; fixednew00ENDPOINTnormisreferencenormalization, notanextended00trajectory.\n\nInterpretation: firstblock/acceptedendpoint/commonouter aredistinctclasses. Uonlychangesinneru; Jstillgroupstwooutergates. Evaluateconditionaldifferences, notjustdiagonal. Missesnotimputed; nofullallocationunlessall4accepted. No fittedwinnerthreshold; priorqualified75.72/55.90%scale.\n\nAllowedconclusion: localnumericalcontrol sensitivity atonesyntheticc1s2, nohistory/recovery/nextstep. Blocked: physicalteacher/unique/global equilibrium,fatiguedf<1certificate ormulticyclegrowth. Storyline: locate subsequent55.90% whilekeepingstrictphase. Spatial/Carraraalignmentdoesnoterasecommitted-f/trial-f orjointDeep-Ritz/staggereddifferences.\n')
 print(json.dumps(summary,indent=2))

def draw(out,nodes,c,w,fields,rows,outers,timing,contrasts,runid):
 names=['00','10','01','11'];by={r['case']:r for r in rows};present=[k for k in names if k in by];x=np.arange(len(present))
 fig,axs=plt.subplots(1,3,figsize=(17,4.8))
 axs[0].bar(x-.18,[max(by[k]['policy_C'],1e-18) for k in present],.35,label='own policy C');axs[0].bar(x+.18,[max(by[k]['fresh_C'],1e-18) for k in present],.35,label='strict fresh C');axs[0].set_yscale('log');axs[0].axhline(1,c='black',ls='--');axs[0].set_xticks(x,['U'+k[0]+' J'+k[1]+('' if by[k]['accepted'] else '\nMISS') for k in present]);axs[0].legend(fontsize=8);axs[0].set_ylabel('C, dashed1 (log displayfloor1e-18)')
 for ax,kind,title in [(axs[1],'first_completed_outer','First complete block (not convergence)'),(axs[2],'accepted_policy_endpoint','Accepted-policy endpoints only')]:
  q=[t for t in contrasts if t['kind']==kind];ax.bar(np.arange(len(q)),[100*t['weighted_relL2_to_common00'] for t in q]);ax.set_xticks(np.arange(len(q)),[t['contrast'].replace('_at_','\nat ') for t in q],fontsize=8);ax.set_ylabel('Weighted active gap / NEW00 norm (%)');ax.set_title(title,fontsize=11)
 axs[2].text(.03,.97,'Pairs involving MISS excluded\nDifferent endpoints can have different outers',transform=axs[2].transAxes,va='top',fontsize=8)
 fig.suptitle('Fixed fresh / constrained / native p2 | U inneru, J joint/outer-u | '+runid,fontsize=10);fig.tight_layout();fig.savefig(out/'s2uj_decision.png',dpi=170);plt.close(fig)
 # Retrieve first-block fields from the already audited native outer files, not interpolation.
 first={}
 for k in present:
  p=out.parent/'retrieved/output/s2uj'/('U'+k[0]+'J'+k[1])/'outer_01.mat'
  if p.exists():
   with h5py.File(p) as h:first[k]=a(h['point'],'history234').transpose(2,1,0)[:,:,1]
 allfields=list(fields.values())+list(first.values());nf=Normalize(-12,np.log10(max([float(t.max()) for t in allfields]+[1e-11])))
 pairs=[('U at J0','10','00'),('U at J1','11','01'),('J at U0','01','00'),('J at U1','11','10')]
 diffs=[fields[hi]-fields[lo] for _,hi,lo in pairs if hi in fields and lo in fields];vm=max([float(abs(t).max()) for t in diffs]+[1e-15]);nd=SymLogNorm(max(vm*.001,1e-15),vmin=-vm,vmax=vm)
 fig,axs=plt.subplots(3,4,figsize=(16,12));pc=dc=None
 def cloud(ax,f,norm,cmap):
  cell=(w*f).sum(1)/w.sum(1);pc=PolyCollection(nodes[c],array=cell,norm=norm,cmap=cmap,edgecolors='none',antialiased=False);ax.add_collection(pc);ax.autoscale();ax.set_aspect('equal');return pc
 for row,data in [(0,first),(1,fields)]:
  for ax,k in zip(axs[row],names):
   if k not in data:ax.text(.5,.5,k+' unavailable',ha='center');continue
   # Weighted mean then log for display; no averaging used in scalar metrics.
   f=data[k];cell=np.log10(np.maximum((w*f).sum(1)/w.sum(1),1e-12));pc=PolyCollection(nodes[c],array=cell,norm=nf,cmap='viridis',edgecolors='none',antialiased=False);ax.add_collection(pc);ax.autoscale();ax.set_aspect('equal')
   title=k+' first complete outer1' if row==0 else k+' outer'+str(by[k]['outer'])+(' / own-policy accepted' if by[k]['accepted'] else ' / MISS: last complete')
   ax.set_title(title,fontsize=9)
 for ax,(label,hi,lo) in zip(axs[2],pairs):
  if hi not in fields or lo not in fields:continue
  dc=cloud(ax,fields[hi]-fields[lo],nd,'RdBu_r');ax.set_title(label+' ('+hi+' - '+lo+')'+(' / accepted endpoints' if by[hi]['accepted'] and by[lo]['accepted'] else '\nlast complete; pair not both accepted'),fontsize=9)
 for ax in axs.flat:ax.set_xlabel('native x');ax.set_ylabel('native y')
 if pc is not None:fig.colorbar(pc,ax=axs[:2].ravel().tolist(),label='log10 active cell mean (floor1e-12)',shrink=.7)
 if dc is not None:fig.colorbar(dc,ax=list(axs[2]),label='Signed active gap (shared symlog)',shrink=.7)
 fig.suptitle('First block versus endpoint/last complete | native Q4, GP-weighted cell means for display');fig.savefig(out/'s2uj_fields.png',dpi=165,bbox_inches='tight');plt.close(fig)
 fig,axs=plt.subplots(2,2,figsize=(13,8))
 for k in present:
  q=[t for t in outers if t['case']==k];xx=[t['outer'] for t in q];label=k+('' if by[k]['accepted'] else ' MISS:last complete')
  for ax,key in [(axs[0,0],'fresh_C'),(axs[0,1],'u_l2'),(axs[1,0],'d_fresh_l2')]:ax.plot(xx,[max(t[key],1e-18) for t in q],marker='.',label=label)
  axs[1,1].plot(xx,[t['active_integral'] for t in q],marker='.',label=label)
 axs[0,0].axhline(1,c='black',ls='--');axs[0,0].set_title('Strict fresh C (dashed1)')
 axs[0,1].axhline(1e-8,c='black',ls=':');axs[0,1].axhline(4e-4,c='black',ls='--');axs[0,1].set_title('Post-damage fresh ||Ru||; outer u thresholds')
 axs[1,0].axhline(4e-6,c='black',ls=':');axs[1,0].set_title('Fresh feasible ||Rd||; fixed phase threshold4e-6')
 axs[1,1].set_title('Native GP/Jacobian active integral')
 for ax in axs.flat:ax.set_xlabel('Completed outer (0 observation only)');ax.legend(fontsize=7)
 for ax in [axs[0,0],axs[0,1],axs[1,0]]:ax.set_yscale('log')
 fig.suptitle('All4 declared U/J cells | failed inner trials excluded; values<=1e-18 floored only for display',fontsize=10);fig.tight_layout();fig.savefig(out/'s2uj_trajectory.png',dpi=170);plt.close(fig)
 fig,axs=plt.subplots(1,2,figsize=(13,4.8))
 for k in present:
  q=[t for t in outers if t['case']==k and t['outer']>=1];xx=[t['outer'] for t in q]
  axs[0].plot(xx,[max(t['inner_u_returned_l2'],1e-18) for t in q],marker='.',label=k)
  axs[1].plot(xx,[max(t['joint_component'],1e-18) for t in q],marker='.',label=k+' jointsum')
  axs[1].plot(xx,[max(t['outer_u_component'],1e-18) for t in q],ls=':',marker='x',label=k+' outeru')
 axs[0].axhline(1e-6,c='black',ls='--');axs[0].axhline(1e-8,c='black',ls=':');axs[0].set_title('Fresh inner-u returned norm; two inner thresholds')
 axs[1].axhline(1,c='black',ls='--');axs[1].set_title('Own-policy normalized stopping components')
 for ax in axs:ax.set_yscale('log');ax.set_xlabel('Actually completed outer');ax.legend(fontsize=7,ncol=2)
 fig.suptitle('Fixedstrictphase | values<=1e-18 flooredonlyfordisplay | '+runid,fontsize=9);fig.tight_layout();fig.savefig(out/'s2uj_inner_outer.png',dpi=170);plt.close(fig)
 captions={
 's2uj_decision':'Own policy C and common strict C (dashed1), initialpointineligible. Firstcompleteblock contrast uses common00 FIRST norm; accepted endpoints use common00 ENDPOINT norm. Miss-involving endpoint pairs omitted from accepted bars. Log C display floor1e-18; exactCSV retained.',
 's2uj_fields':'Top: all firstcompleteouter1 fields, observational/notconvergence. Middle: accepted endpoint or explicitly MISS lastcomplete. Bottom: conditional endpoint differences; misspairs explicitly notbothaccepted. Shared log active scale, floor1e-12; shared signed symlog difference scale, linearthreshold0.001maxGPgap. Exact scalar metrics use all GP/Jacobian weights; weightedcellmean is displayonly.',
 's2uj_trajectory':'Allcompleteouter strictC, postdamage Ru, fresh feasibleRd and activeintegral.0observationonly. Thresholds shown; a single phase/u threshold alone is not jointclosure. Failedinnerstates excluded; missesretain lastcomplete. Values<=1e-18 flooredonlyfordisplay, CSV exact.'}
 captions['s2uj_inner_outer']='Everycompleteblock returnedinneru norm versus displacement inner thresholds; own-policy normalizedjointsum andouteru components separately, dashed1. Exactzero/smallvalues<=1e-18 displayflooronly. J is still a pair of stoppingthresholds, notseparatelyintervened gates.'
 for stem,caption in captions.items():(out/(stem+'.md')).write_text('# '+stem+'\n\nData provenance: '+runid+'; s2uj_analysis.json and cases/completed_outers/contrasts/timing.csv; exact nativeQ4 package/retrieval/operator replay.\n\nQuestion: fixedfresh/constrained/nativep2, isolate Uinneru fromJjointsum/outeru thresholdpair withstrictphase4e-6 at same origin.\n\nHow to read: '+caption+'\n\nInterpretation and limitations: README_analysis.md. Diagnostic local policy effect only, no physical/teacher/global/multicyclegrowth conclusion.\n')
if __name__=='__main__':main()
