#!/usr/bin/env python3
"""Offline S2RA native-state audit; no solves or interpolation of absent arms."""
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
 run=args.run;root=run/'retrieved';base=root/'output/s2ra';out=run/'analysis';out.mkdir(exist_ok=True)
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
 assert manifest['protocol_revision']=='S04-E011-S2RA-r1' and manifest['staging']==package['staging']
 inputs={t['role']:root/'inputs'/Path(t['target'].replace('\\','/')).name for t in manifest['staging']}
 for t in manifest['staging']:
  p=inputs[t['role']];assert p.stat().st_size==t['bytes'] and sha(p)==t['sha256']
 if not all((root/t).exists() for t in ['selftest.json','io_preflight.json']):
  dump(out/'s2ra_analysis.json',dict(status='prerequisites_not_reached',planned=[dict(case=k,status='NOT RUN') for k in ['00','10','01','11']],contrasts=[],symmetric_algebraic_allocation=[],failure=jsonfile(root/'sequence_failure.json') if (root/'sequence_failure.json').exists() else None));return
 tests=jsonfile(root/'selftest.json')
 for name,number in [('damage',6),('coupled',6),('commit',10),('raw',12),('refresh_accuracy',14)]:assert tests[name]['status']=='passed' and tests[name]['cases']==number
 assert jsonfile(root/'io_preflight.json')['unique_inputs']==6
 with h5py.File(inputs['common']) as h:
  nodes=a(h,'node_coords').T;c=a(h,'connectivity').T.astype(int)-1;fu=v(h,'free_dof_u').astype(int)-1;fd=v(h,'free_dof_d').astype(int)-1
 n=len(nodes);N,B,w,xy=q4_geometry(nodes,c);stencil=raw_stencil(nodes,c)
 with h5py.File(inputs['O1']) as h:pre=state(h['proposed'])
 with h5py.File(inputs['R1']) as h:other=state(h['proposed'])
 start={'u':pre['u'],'d':np.maximum(pre['d'],other['d'])};predictor=None
 fields={};firstfields={};rows=[];outers=[];timing=[];ledgers=[];anchors=[];planned=[]
 fixedu=np.setdiff1d(np.arange(2*n),fu);fixedd=np.setdiff1d(np.arange(n),fd)
 def feasible(d,rd):return float(np.linalg.norm(projected_gradient(d[fd],rd[fd],pre['lower'][fd])))
 def replay(d,raw):
  rd,t=assemble(d,raw,pre['lower'],pre['history'],c,N,B,w,n)
  return rd,np.stack([t['alpha'],t['active'],t['f']],axis=2),t
 def point(g,R,A):
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
   timing.append(dict(case=f'{R}{A}',outer=k,u_return_minus_evaluated_max=float(np.max(abs(ut-ue))),cached_u_l2=crnorm,fresh_before_u_l2=float(np.linalg.norm(rub[fu])),raw_timing_scaled_maxerr=rt,raw_damage_scaled_maxerr=dm,d_cached_l2=cached,d_fresh_l2=dr,phase_norm_difference=abs(cached-dr),crossing_old=(cached<=4e-4)!=(dr<=4e-4),crossing_tight=(cached<=4e-6)!=(dr<=4e-6),native_replay_maxerr=max(raw_input_err,raw_before_err,ce,rbe)))
  chosen=dr if R else cached;jtol=4e-6 if A else 4e-4;utol=1e-8 if A else 4e-4
  PC=max((ur+chosen)/jtol,ur/utol);C=max((ur+dr)/4e-6,ur/1e-8)
  assert abs(C-scalar(g,'criterion'))<=1e-8*max(1,C) and abs(PC-scalar(g,'policy_C'))<=1e-8*max(1,PC)
  assert bool(scalar(g,'policy_pass'))==(k>=1 and PC<=1)
  return t['active'],dict(outer=k,fresh_C=C,policy_C=PC,u_l2=ur,d_fresh_l2=dr,d_cached_l2=cached,active_integral=float(np.sum(w*t['active'])),f_min=float(t['f'].min()),native_residual_scaled_maxerr=err,history_scaled_maxerr=herr,raw_scaled_maxerr=rawerr)
 for name in ['00','11','10','01']:
  folder=base/('R'+name[0]+'A'+name[1])
  if not all((folder/t).exists() for t in ['case.mat','result.json']):planned.append(dict(case=name,status='NOT RUN'));continue
  result=jsonfile(folder/'result.json');R,A=map(int,name);assert result['R']==R and result['A']==A and result['history_commits']==0
  assert result['u_calls']<=249 and result['phase_calls']<=248
  planned.append(dict(case=name,status='FATAL' if result['fatal'] else ('accepted' if result['accepted'] else 'MISS'),reason=result['reason']))
  if result['fatal']:continue
  with h5py.File(folder/'case.mat') as h:
   same(state(h['pre']),pre);same({k:v(h['start'],k) for k in ['u','d']},start)
   if not isinstance(h['current'],h5py.Group) or not isinstance(h['out'],h5py.Group):
    planned[-1]['status']='NO AUDITABLE POINT';continue
   pr={k:v(h['predictor'],k) for k in ['u','d','r']}
   if predictor is not None:same(pr,predictor)
   predictor=pr
   assert int(scalar(h['counts'],'u'))==result['u_calls']==int(scalar(h['out']['counts'],'u'))+1
   assert int(scalar(h['counts'],'d'))==result['phase_calls']==int(scalar(h['out']['counts'],'d'))
   final,q=point(h['current'],R,A);fields[name]=final
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
     active,oq=point(z['point'],R,A);outers.append(dict(case=name,**oq))
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
   rows.append(dict(case=name,R=R,A=A,accepted=result['accepted'],reason=result['reason'],u_calls=result['u_calls'],phase_calls=result['phase_calls'],**q,trial_alpha_max=float(max(led['alpha_max'])),trial_f_min=float(min(led['f_min']))))
   print('AUDITED',name,result['accepted'],q['fresh_C'],flush=True)
 # Each terminal point was replayed twice for final/trajectory consistency; timing rows deduplicated.
 timing=list({(t['case'],t['outer']):t for t in timing}.values())
 by={r['case']:r for r in rows};contrasts=[];allocation=[]
 reference=fields.get('00');norm0=float(np.sum(w*reference**2)) if reference is not None else None;total=fields['11']-reference if reference is not None and '11' in fields else None;gapnorm=float(np.sum(w*total**2)) if total is not None else None
 def contrast(label,left,right,kind):
  d=right-left;norm=float(np.sum(w*d*d));ij=np.unravel_index(np.argmax(abs(d)),w.shape)
  return dict(contrast=label,kind=kind,weighted_relL2_to_left=float(np.sqrt(norm/np.sum(w*left*left))),weighted_relL2_to_00=float(np.sqrt(norm/norm0)),signed_integral=float(np.sum(w*d)),projection_on_total=float(np.sum(w*d*total)/gapnorm) if gapnorm else None,wake_squared_share=float(np.sum((w*d*d)[xy[:,:,0]<=0])/norm) if norm else 0.,max_absolute_gap=float(abs(d[ij])),x=float(xy[ij][0]) if norm else None,y=float(xy[ij][1]) if norm else None)
 pairs=[('R_at_A0','00','10'),('R_at_A1','01','11'),('A_at_R0','00','01'),('A_at_R1','10','11'),('total','00','11')]
 for label,lo,hi in pairs if norm0 else []:
  if all(k in by and by[k]['accepted'] for k in [lo,hi]):contrasts.append(contrast(label,fields[lo],fields[hi],'declared_policy_endpoint'))
  if lo in firstfields and hi in firstfields:contrasts.append(contrast(label,firstfields[lo],firstfields[hi],'first_completed_outer'))
 interaction=None
 if gapnorm and all(k in by and by[k]['accepted'] for k in ['00','10','01','11']):
  R=.5*((fields['10']-fields['00'])+(fields['11']-fields['01']));A=.5*((fields['01']-fields['00'])+(fields['11']-fields['10']))
  assert relative(R+A,total)<=1e-12
  for label,effect in [('R',R),('A',A)]:allocation.append(dict(factor=label,signed_projection_on_total=float(np.sum(w*effect*total)/gapnorm),weighted_L2_relative_to_total=float(np.sqrt(np.sum(w*effect**2)/gapnorm))))
  it=fields['11']-fields['10']-fields['01']+fields['00'];interaction=dict(weighted_L2_to_00=float(np.sqrt(np.sum(w*it**2)/norm0)),weighted_L2_to_total=float(np.sqrt(np.sum(w*it**2)/gapnorm)))
 for r in rows:r['active_relL2_to_00']=float(np.sqrt(np.sum(w*(fields[r['case']]-reference)**2)/norm0)) if norm0 else None
 table(out/'cases.csv',rows);table(out/'completed_outers.csv',outers);table(out/'timing.csv',timing);table(out/'phase_calls.csv',ledgers);table(out/'contrasts.csv',contrasts)
 done=(root/'sequence_finished.json').exists();assert not done or len(planned)==4
 summary=dict(status='four_case_complete' if done and len(rows)==4 else 'partial_terminal',producer_commit=package['source_commit'],cases=rows,planned=planned,anchors=anchors,contrasts=contrasts,symmetric_algebraic_allocation=allocation,interaction=interaction,history_commits=0,unique_complete_points=len(outers),complete_blocks=len(timing),timing_max={k:max((t[k] for t in timing),default=None) for k in ['raw_timing_scaled_maxerr','raw_damage_scaled_maxerr','phase_norm_difference','native_replay_maxerr','u_return_minus_evaluated_max']},phase_threshold_crossings=sum(t['crossing_old'] or t['crossing_tight'] for t in timing),definition='D1 native p2 fixed. R=mechanical return/raw timing plus outer phase feedback; all constrained phase residuals already fresh. A=numeric inner/joint/outer tolerance values. All arms require a complete block. No physical/teacher/multicycle claim.',analysis_code=dict(path=str(Path(__file__).resolve()),sha256=sha(Path(__file__).resolve())))
 dump(out/'s2ra_analysis.json',summary)
 draw(out,nodes,c,w,fields,rows,outers,timing,contrasts,run.name)
 (out/'README_analysis.md').write_text('# c1s2 refresh versus accuracy\n\nScientific question: separate refresh R from numerical tolerances A at identical predecessor/start/predictor with constrained damage and native trial-f.\n\nData provenance: '+run.name+'; producer '+package['source_commit']+'; exact inputs/package/retrieval and native residual/history/timing replays in s2ra_analysis.json. CSV files retain all cases/complete points, including misses.\n\nReading order: s2ra_decision.png shows declared policy and strict fresh C, four conditional contrasts with common00 denominator, completed-outer trajectory. s2ra_fields.png shows all four native-Q4 active fields and conditional differences using shared scales. s2ra_timing.png shows mechanical evaluated/returned state differences and cached/fresh phase norms at every completed block. Fields at each declared-policy endpoint may have different outer counts; incomplete trials excluded.\n\nCross-figure interpretation: read the computed conditional effects, not just the diagonal80.67% gap. R includes mechanical return/raw timing and outer phase feedback. All phase inner solves already use fresh constrained residual. A changes grouped numerical threshold values, not a solver direction. Same mandatory first block eliminates prior initial-acceptance ambiguity. Algebraic allocation, when all four accepted, is not a physical causal percentage.\n\nAllowed conclusion: bounded local numerical sensitivity at synthetic c1s2; no committed history, recovery or next substep. Blocked: teacher/physical validity, global/unique equilibrium, multicycle error accumulation, or individual tolerance attribution. Storyline impact: determines the next local-control diagnostic without changing frozen E003/E011 verdicts. Mesh/Carrara alignment does not erase committed-f/trial-f or joint Deep-Ritz/staggered differences.\n')
 print(json.dumps(summary,indent=2))

def draw(out,nodes,c,w,fields,rows,outers,timing,contrasts,runid):
 names=['00','10','01','11'];by={r['case']:r for r in rows};names=[k for k in names if k in by];x=np.arange(len(names))
 fig,axs=plt.subplots(1,3,figsize=(16,4.7))
 axs[0].bar(x-.18,[max(by[k]['policy_C'],1e-18) for k in names],.35,label='own policy C');axs[0].bar(x+.18,[max(by[k]['fresh_C'],1e-18) for k in names],.35,label='strict fresh C');axs[0].set_yscale('log');axs[0].axhline(1,c='black',ls='--');axs[0].set_xticks(x,['R'+k[0]+' A'+k[1]+('' if by[k]['accepted'] else '\nMISS') for k in names]);axs[0].legend(fontsize=8);axs[0].set_ylabel('C (dashed1)')
 q=[t for t in contrasts if t['kind']=='declared_policy_endpoint'];axs[1].bar(np.arange(len(q)),[100*t['weighted_relL2_to_00'] for t in q]);axs[1].set_xticks(np.arange(len(q)),[t['contrast'].replace('_at_','\nat ') for t in q],fontsize=8);axs[1].set_ylabel('GP-weighted active gap / ||active00|| (%)')
 for k in names:
  t=[r for r in outers if r['case']==k];axs[2].plot([r['outer'] for r in t],[max(r['fresh_C'],1e-18) for r in t],marker='.',label=k)
 axs[2].set_yscale('log');axs[2].axhline(1,c='black',ls='--');axs[2].set_xlabel('Completed outer (0 observation only)');axs[2].set_ylabel('Strict fresh C');axs[2].legend(fontsize=8)
 fig.suptitle('Same-origin c1s2 | R refresh / A accuracy | '+runid,fontsize=10);fig.tight_layout();fig.savefig(out/'s2ra_decision.png',dpi=170);plt.close(fig)
 panels=[('R at A0','10','00'),('R at A1','11','01'),('A at R0','01','00'),('A at R1','11','10')]
 fig,axs=plt.subplots(2,4,figsize=(16,8));norm=Normalize(-12,np.log10(max([float(t.max()) for t in fields.values()]+[1e-11])))
 diffs=[fields[hi]-fields[lo] for _,hi,lo in panels if hi in fields and lo in fields];vm=max([float(abs(t).max()) for t in diffs]+[1e-15]);nd=SymLogNorm(max(vm*.001,1e-15),vmin=-vm,vmax=vm)
 pc=dc=None
 for ax,k in zip(axs[0],['00','10','01','11']):
  if k not in fields:ax.text(.5,.5,k+' missing',ha='center');continue
  f=fields[k];cell=(w*f).sum(1)/w.sum(1);pc=PolyCollection(nodes[c],array=np.log10(np.maximum(cell,1e-12)),norm=norm,cmap='viridis',edgecolors='none',antialiased=False);ax.add_collection(pc);ax.autoscale();ax.set_aspect('equal');ax.set_title(k+' / outer'+str(by[k]['outer'])+(' accepted' if by[k]['accepted'] else ' MISS'),fontsize=10)
 for ax,(label,hi,lo) in zip(axs[1],panels):
  if hi not in fields or lo not in fields:continue
  f=fields[hi]-fields[lo];cell=(w*f).sum(1)/w.sum(1);dc=PolyCollection(nodes[c],array=cell,norm=nd,cmap='RdBu_r',edgecolors='none',antialiased=False);ax.add_collection(dc);ax.autoscale();ax.set_aspect('equal');ax.set_title(label+' ('+hi+' - '+lo+')'+('' if by[hi]['accepted'] and by[lo]['accepted'] else '\nlast complete / not accepted'),fontsize=10)
 for ax in axs.flat:ax.set_xlabel('native x');ax.set_ylabel('native y')
 if pc is not None:fig.colorbar(pc,ax=list(axs[0]),label='log10 active (floor1e-12)',shrink=.7)
 if dc is not None:fig.colorbar(dc,ax=list(axs[1]),label='signed active difference (shared symlog)',shrink=.7)
 fig.suptitle('Native Q4; display GP/Jacobian-weighted cell means; scalar metrics use all GP');fig.savefig(out/'s2ra_fields.png',dpi=170,bbox_inches='tight');plt.close(fig)
 fig,axs=plt.subplots(2,2,figsize=(13,8));floor=1e-18
 for k in names:
  q=[t for t in timing if t['case']==k];x=[t['outer'] for t in q]
  axs[0,0].plot(x,[max(t['u_return_minus_evaluated_max'],floor) for t in q],marker='.',label=k)
  axs[0,1].plot(x,[max(t['raw_timing_scaled_maxerr'],floor) for t in q],marker='.',label=k)
  axs[1,0].plot(x,[max(t['d_cached_l2'],floor) for t in q],marker='.',label=k+' cached');axs[1,0].plot(x,[max(t['d_fresh_l2'],floor) for t in q],ls=':',marker='x',label=k+' fresh')
  axs[1,1].plot(x,[max(t['phase_norm_difference'],floor) for t in q],marker='.',label=k)
 titles=['max |u returned - u evaluated|','max scaled raw timing difference','Phase feasible norms: cached / fresh','Absolute cached/fresh phase norm difference']
 axs[1,0].axhline(4e-4,c='black',ls='--');axs[1,0].axhline(4e-6,c='black',ls=':')
 for ax,title in zip(axs.flat,titles):ax.set_yscale('log');ax.set_title(title);ax.set_xlabel('Completed outer');ax.legend(fontsize=7,ncol=2)
 fig.suptitle('Returned-state timing audit | values <=1e-18 displayed at1e-18; CSV retains zeros');fig.tight_layout();fig.savefig(out/'s2ra_timing.png',dpi=170);plt.close(fig)
 captions={'s2ra_decision':'Own policy C and common strict fresh C with threshold1 (values <=1e-18 display at1e-18 only); four conditional contrasts and diagonal total use common00 active norm; completed outer trajectory. Accepted under own policy need not pass strict C.', 's2ra_fields':'All four endpoints and conditional difference maps. Shared active log scale and shared signed symlog difference scale (linear threshold0.001 of max GP gap). Display weighted cell mean only, scalar metrics use native GP. Exact zero differences remain blank at centre of signed scale.', 's2ra_timing':'Every completed block: return/evaluation u difference, raw timing difference, cached/fresh feasible phase norms with both tolerances, and their difference. Values <=1e-18 display at1e-18 only; timing.csv retains exact values. Failed trials excluded.'}
 for stem,caption in captions.items():(out/(stem+'.md')).write_text('# '+stem+'\n\nData provenance: '+runid+'; s2ra_analysis.json and cases.csv/completed_outers.csv/timing.csv/contrasts.csv; exact package and retrieval verified.\n\nQuestion: separate grouped tolerance values A from refresh R at fixed D1/native p2 and identical origin.\n\nHow to read: '+caption+'\n\nInterpretation and limitations: README_analysis.md. Local numerical sensitivity only; no physical/teacher/multicycle certificate.\n')
if __name__=='__main__':main()
