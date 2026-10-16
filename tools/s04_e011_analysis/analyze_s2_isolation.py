#!/usr/bin/env python3
"""Offline native-Q4 audit and same-origin D/S/F control contrasts."""
import argparse,csv,hashlib,itertools,json,math
from pathlib import Path
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize,SymLogNorm
from analyze_c1_commit import a,v,scalar,state,same
from run_multicycle_cross_replay import q4_geometry,amor_raw,interp
from audit_phase_tangent import assemble
from localize_endpoint_tight import mechanics_force
from audit_fem_final_residuals import projected_gradient
from audit_raw_response_bound import admission as raw_admission,stencil as raw_stencil

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def table(p,rows):
 if not rows:return
 with p.open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def jsonfile(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def struct_columns(g):
 out={}
 for k in g:
  data=np.asarray(g[k]).reshape(-1)
  out[k]=np.array([np.asarray(g.file[t]).item() for t in data]) if h5py.check_dtype(ref=data.dtype) else data
 return out

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--package',type=Path,required=True);args=ap.parse_args()
 run=args.run;root=run/'retrieved';base=root/'output/s2i';out=run/'analysis';out.mkdir(exist_ok=True)
 receipt=jsonfile(run/'retrieval_verification.json');assert receipt['all_hashes_and_sizes_match']
 assert receipt['files']==len(receipt['manifest']) and receipt['bytes']==sum(x['bytes'] for x in receipt['manifest'])
 for item in receipt['manifest']:
  p=root/item['relative'].replace('\\','/');assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
 package=jsonfile(args.package);review=jsonfile(args.package.parent/'local_independent_review.json')
 assert review['status']=='passed' and review['commit']==package['source_commit'] and review['package_manifest_sha256']==sha(args.package)
 for item in package['files']:
  p=root/item['name'];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
 launch=jsonfile(root/'launch_receipt.json');manifest=jsonfile(root/'input_manifest.json')
 assert launch['commit']==manifest['source_commit']==package['source_commit'] and launch['dirty'] is False and launch['threads']==1
 assert launch['root']==package['remote_root'] and launch['account'].lower()==r'ad\xw436'
 assert manifest['protocol_revision']=='S04-E011-S2I-r1' and manifest['staging']==package['staging']
 inputs={x['role']:root/'inputs'/Path(x['target'].replace('\\','/')).name for x in manifest['staging']}
 for item in manifest['staging']:
  p=inputs[item['role']];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
 if not(root/'selftest.json').exists() or not(base/'admission.mat').exists():
  dump(out/'execution_failure.json',dict(status='no_admitted_field_evidence',failure=jsonfile(root/'sequence_failure.json') if (root/'sequence_failure.json').exists() else None,planned_cases=10,scientific_verdict='inconclusive; prerequisites not reached'))
  print('NO_ADMITTED_FIELD_EVIDENCE');return
 tests=jsonfile(root/'selftest.json')
 for name,number in [('damage',6),('coupled',6),('commit',10),('raw',12),('isolation',16)]:assert tests[name]['status']=='passed' and tests[name]['cases']==number
 assert jsonfile(root/'io_preflight.json')['unique_inputs']==6
 with h5py.File(inputs['common']) as h:
  nodes=a(h,'node_coords').T;c=a(h,'connectivity').T.astype(int)-1;fu=v(h,'free_dof_u').astype(int)-1;fd=v(h,'free_dof_d').astype(int)-1
 n=len(nodes);N,B,w,xy=q4_geometry(nodes,c)
 with h5py.File(inputs['O1']) as h:pre=state(h['proposed'])
 with h5py.File(inputs['R1']) as h:other=state(h['proposed'])
 expected_start=dict(u=pre['u'],d=np.maximum(pre['d'],other['d']))
 field={};firstfield={};rows=[];outerrows=[];ledgers=[];worstrows=[];predictor=None;residual_errors=[]
 def check_point(g,F):
  u=v(g,'u');d=v(g,'d');raw=a(g,'raw').T
  assert np.all(np.isfinite(u)) and np.all(d>=pre['lower']-1e-12) and np.all(d<=1+1e-12)
  assert np.array_equal(u[np.setdiff1d(np.arange(2*n),fu)],predictor['u'][np.setdiff1d(np.arange(2*n),fu)])
  assert np.array_equal(d[np.setdiff1d(np.arange(n),fd)],expected_start['d'][np.setdiff1d(np.arange(n),fd)])
  expected=amor_raw(u[:n],u[n:],c,B);assert np.max(abs(raw-expected)/np.maximum(1,abs(expected)))<=1e-10
  rd,t=assemble(d,raw,pre['lower'],pre['history'],c,N,B,w,n,coefficient=np.ones_like(w) if F else None)
  ru=mechanics_force(u,d,c,N,B,w,n)
  err=max(float(np.max(abs(rd-v(g,'rd')))),float(np.max(abs(ru-v(g,'ru')))))
  hh=np.stack([t['alpha'],t['active'],t['f']],axis=2);herr=float(np.max(abs(hh-a(g,'history234').transpose(2,1,0))/np.maximum(1,abs(hh))))
  assert err<=1e-10 and herr<=1e-10,(err,herr)
  ur=float(np.linalg.norm(ru[fu]));dr=float(np.linalg.norm(projected_gradient(d[fd],rd[fd],pre['lower'][fd])))
  C=max((ur+dr)/4e-6,ur/1e-8);assert abs(C-scalar(g,'criterion'))<=1e-8*max(1,C)
  return t['active'],dict(outer=int(scalar(g,'outer')),C=C,u_l2=ur,d_feasible_l2=dr,d_raw_l2=float(np.linalg.norm(rd[fd])),residual_maxerr=err,history_scaled_maxerr=herr,active_integral=float(np.sum(w*t['active'])),final_f_min=float(t['f'].min()))
 # Native preflight fixtures, independently replayed; no solves on Mac.
 admission=[]
 with h5py.File(base/'admission.mat') as h:
  assert np.array_equal(a(h,'node_coords').T,nodes) and np.array_equal(a(h,'connectivity').T.astype(int)-1,c)
  for i,ref in enumerate(a(h,'admission').reshape(-1)):
   g=h[ref];d=v(g,'d');raw=a(g,'raw').T
   for F in [0,1]:
    rd,t=assemble(d,raw,pre['lower'],pre['history'],c,N,B,w,n,coefficient=np.ones_like(w) if F else None)
    saved=v(g,'r0' if F else 'r2');hh=a(g,'h0' if F else 'h2').transpose(2,1,0)
    re=float(np.max(abs(rd-saved)/np.maximum(1,abs(saved))));he=float(np.max(abs(np.stack([t['alpha'],t['active'],t['f']],axis=2)-hh)/np.maximum(1,abs(hh))))
    # Extreme cancellation fixture independently recomputes f using same stable expression.
    assert re<=1e-10 and he<=1e-10,(i,F,re,he)
    admission.append(dict(fixture=i,F=F,residual_scaled_maxerr=re,history_scaled_maxerr=he,f_min=float(t['f'].min())))
 names=['000','110','001','100','101','111','T1','T0','011','010'];planned=[];stencil=raw_stencil(nodes,c)
 for name in names:
  folder=base/name
  if not(folder/'case.mat').exists():
   planned.append(dict(case=name,status='NOT RUN',reason='No saved native case',audited_point=False));continue
  result=jsonfile(folder/'result.json');D,S,F=result['bits'];expected_bits=[int(t) for t in name] if name[0]!='T' else [int(name[1]),2,0]
  assert result['bits']==expected_bits and result['history_commits']==0 and result['u_calls']<=250 and result['phase_calls']<=250
  assert not result['accepted'] or (result['fatal'] is False and result['status']=='accepted')
  planned.append(dict(case=name,status='accepted' if result['accepted'] else 'MISS',reason=result['reason'],audited_point=False))
  with h5py.File(folder/'case.mat') as h:
   same(state(h['pre']),pre);same(dict(u=v(h['start'],'u'),d=v(h['start'],'d')),expected_start)
   assert int(scalar(h['counts'],'u'))==result['u_calls'] and int(scalar(h['counts'],'d'))==result['phase_calls']
   if not isinstance(h['current'],h5py.Group) or not isinstance(h['native'],h5py.Group):
    planned[-1]['status']='NO FINAL AUDIT';continue
   pr={k:v(h['predictor'],k) for k in ['u','d','r']}
   if predictor is not None:same(pr,predictor)
   predictor=pr
   final,point=check_point(h['current'],F);field[name]=final
   native,point_native=check_point(h['native'],0);assert np.max(abs(native-final))<=1e-12
   if name in ['000','110']:
    assert result['reference']['pass']
    with h5py.File(inputs['anchor'+name]) as ref:
     assert max(np.max(abs(v(h['current'],'u')-v(ref['candidate'],'u'))),np.max(abs(v(h['current'],'d')-v(ref['candidate'],'d'))))<=1e-10
     hh=a(ref['proof'],'history234').transpose(2,1,0);assert np.max(abs(a(h['current'],'history234').transpose(2,1,0)-hh)/np.maximum(1,abs(hh)))<=1e-10
     assert point['outer']==scalar(ref['out'],'completed_outer')
     rawcheck,_=raw_admission(v(h['current'],'u'),a(h['current'],'raw').T,v(ref['candidate'],'u'),a(ref['proof'],'raw').T,c,stencil,n);assert rawcheck['pass_new']
   if result['accepted']:
    if S==0:
     assert bool(scalar(h['out'],'native_accepted'))
     tr=struct_columns(h['out']['trace']);assert len(tr['outer'])==point['outer']
     # Frozen native post_iter_update uses absolute fresh Ru + cached phase norm.
     assert point['u_l2']+tr['cached_d'][-1]<=4e-4
    else:
     assert bool(scalar(h['out'],'joint_pass')) and scalar(h['current'],'stop_criterion')<=1
     expected_stop=max((point['u_l2']+point['d_feasible_l2'])/4e-6,point['u_l2']/1e-8) if S==1 else (point['u_l2']+(point['d_raw_l2'] if D==0 else point['d_feasible_l2']))/4e-4
     assert abs(expected_stop-scalar(h['current'],'stop_criterion'))<=1e-8*max(1,expected_stop)
   if result['accepted'] and S==1:assert point['C']<=1
   assert abs(point['C']-result['C_effective'])<=1e-8*max(1,point['C'])
   assert abs(point_native['C']-result['C_native_p2'])<=1e-8*max(1,point_native['C'])
   for p in sorted(folder.glob('outer_*.mat')):
    with h5py.File(p) as z:
     active,q=check_point(z['point'],F);outerrows.append(dict(case=name,**q))
     if q['outer']==1:firstfield[name]=active
   own_outers=[q for q in outerrows if q['case']==name]
   assert [q['outer'] for q in own_outers]==list(range(point['outer']+1)) and point['outer']==result['outer']
   with h5py.File(folder/f"outer_{point['outer']:02d}.mat") as last:
    for key in ['u','d','raw','ru','rd','history234']:assert np.array_equal(a(last['point'],key),a(h['current'],key))
   led=struct_columns(h['ledger']);length=len(led['call'])
   assert np.array_equal(led['call'],np.arange(1,length+1)) and result['phase_calls']==length+2*F
   for j in range(length):ledgers.append(dict(case=name,**{k:float(vv[j]) for k,vv in led.items()}))
   g=h['worst'];d=v(g,'d');raw=a(g,'raw').T
   rd,t=assemble(d,raw,pre['lower'],pre['history'],c,N,B,w,n,coefficient=np.ones_like(w) if F else None)
   hh=a(g,'history234').transpose(2,1,0);he=float(np.max(abs(hh-np.stack([t['alpha'],t['active'],t['f']],axis=2))/np.maximum(1,abs(hh))))
   assert he<=1e-10
   p2rd,p2=assemble(d,raw,pre['lower'],pre['history'],c,N,B,w,n)
   if F:
    assert np.max(abs(p2rd-v(g,'native_p2_rd'))/np.maximum(1,abs(p2rd)))<=1e-10
    assert np.max(abs(a(g,'native_p2_history234').transpose(2,1,0)-np.stack([p2['alpha'],p2['active'],p2['f']],axis=2))/np.maximum(1,abs(hh)))<=1e-10
   gp=interp(d,c,N);idx=np.unravel_index(np.argmax(t['alpha']),w.shape)
   worstrows.append(dict(case=name,call=int(scalar(g,'call')),alpha_max=float(t['alpha'].max()),effective_f_min=float(t['f'].min()),native_p2_f_min=float(p2['f'].min()),d_min=float(d.min()),d_max=float(d.max()),lower_violations=int(np.count_nonzero(d<pre['lower']-1e-12)),upper_violations=int(np.count_nonzero(d>1+1e-12)),cell=int(idx[0]),gp=int(idx[1]),x=float(xy[idx][0]),y=float(xy[idx][1]),d_gp_at_alpha_max=float(gp[idx]),raw_at_alpha_max=float(raw[idx]),history_scaled_maxerr=he))
   rows.append(dict(case=name,D=D,S=S,F=F,accepted=result['accepted'],reason=result['reason'],C_effective=point['C'],C_native_p2=point_native['C'],outer=point['outer'],u_calls=result['u_calls'],phase_calls=result['phase_calls'],u_l2=point['u_l2'],d_feasible_l2=point['d_feasible_l2'],active_integral=point['active_integral'],final_effective_f_min=point['final_f_min'],final_native_f_min=point_native['final_f_min'],trial_effective_f_min=float(np.min(led['effective_f_min'])),trial_native_f_min=float(np.min(led['native_p2_f_pred_min'])),trial_alpha_max=float(np.max(led['alpha_max'])),max_lower_violations=int(np.max(led['lower_violations'])),max_upper_violations=int(np.max(led['upper_violations'])),native_residual_maxerr=max(point['residual_maxerr'],point_native['residual_maxerr'])))
   planned[-1]['audited_point']=True
   print('AUDITED',name,result['accepted'],point['C'],flush=True)
 table(out/'planned_case_status.csv',planned)
 if not all(k in field for k in ['000','110']):
  dump(out/'s2i_analysis.json',dict(status='partial_anchor_unavailable',cases=rows,planned=planned,contrasts=[],cube_allocation=[],admission=admission));draw(out,nodes,c,w,field,rows,outerrows,ledgers,run.name,planned);return
 rowby={r['case']:r for r in rows};reference=field['000'];norm=float(np.sum(w*reference**2));delta=field['110']-reference;gapnorm=float(np.sum(w*delta**2))
 def contrast(label,left,right,kind):
  diff=right-left;ij=np.unravel_index(np.argmax(abs(diff)),w.shape)
  return dict(contrast=label,kind=kind,weighted_relL2_to_left=float(np.sqrt(np.sum(w*diff**2)/np.sum(w*left**2))),weighted_relL2_to_000=float(np.sqrt(np.sum(w*diff**2)/norm)),signed_integral=float(np.sum(w*diff)),projection_onto_110_minus_000=float(np.sum(w*diff*delta)/gapnorm),wake_squared_share=float(np.sum((w*diff**2)[xy[:,:,0]<=0])/np.sum(w*diff**2)) if np.any(diff) else 0.,max_absolute_gap=float(abs(diff[ij])),x=float(xy[ij][0]),y=float(xy[ij][1]))
 contrasts=[]
 for factor in range(3):
  for rest in itertools.product('01',repeat=2):
   bits=list(rest);bits.insert(factor,'0');left=''.join(bits);bits[factor]='1';right=''.join(bits)
   if left in rowby and right in rowby and rowby[left]['accepted'] and rowby[right]['accepted']:
    contrasts.append(contrast('DSF'[factor]+':'+left+'->'+right,field[left],field[right],'accepted_declared_policy'))
   if left in firstfield and right in firstfield:contrasts.append(contrast('DSF'[factor]+':'+left+'->'+right,firstfield[left],firstfield[right],'first_completed_outer_not_converged'))
 for left,right in [('000','T0'),('100','T1'),('T0','010'),('T1','110')]:
  if left in rowby and right in rowby and rowby[left]['accepted'] and rowby[right]['accepted']:contrasts.append(contrast(left+'->'+right,field[left],field[right],'timing_or_accuracy_bridge_accepted'))
  if left in firstfield and right in firstfield:contrasts.append(contrast(left+'->'+right,firstfield[left],firstfield[right],'timing_or_accuracy_bridge_first_outer'))
 allocation=[]
 if all(k in rowby and rowby[k]['accepted'] for k in map(''.join,itertools.product('01',repeat=3))):
  for j in range(3):
   comp=np.zeros_like(reference)
   for rest in itertools.product('01',repeat=2):
    b=list(rest);b.insert(j,'0');lo=''.join(b);b[j]='1';hi=''.join(b);m=sum(int(t) for t in rest)
    comp+=(math.factorial(m)*math.factorial(2-m)/6)*(field[hi]-field[lo])
   allocation.append(dict(factor='DSF'[j],projection_onto_111_minus_000=float(np.sum(w*comp*(field['111']-reference))/np.sum(w*(field['111']-reference)**2))))
 for row in rows:
  row['active_relL2_to_000']=float(np.sqrt(np.sum(w*(field[row['case']]-reference)**2)/norm))
 table(out/'cases.csv',rows);table(out/'completed_outers.csv',outerrows);table(out/'phase_calls.csv',ledgers);table(out/'worst_trials.csv',worstrows);table(out/'contrasts.csv',contrasts)
 completed=(root/'sequence_finished.json').exists();assert not completed or len(rows)==10
 summary=dict(status='ten_case_complete' if completed else 'partial_fatal',producer_commit=package['source_commit'],planned=planned,cases=rows,contrasts=contrasts,cube_allocation=allocation,admission=admission,worst_trials=worstrows,history_commits=0,recovery_calls=0,definition='Exact native Q4 GP/Jacobian weights. D=strategy including norm/direction/line search; S=fresh plus stricter accuracy; F=phase-only p0 ablation. Accepted means each declared effective policy, not strict native equilibrium. No imputation of missing arms.',analysis_code=dict(path=str(Path(__file__).resolve()),sha256=sha(Path(__file__).resolve())))
 dump(out/'s2i_analysis.json',summary)
 draw(out,nodes,c,w,field,rows,outerrows,ledgers,run.name,planned)
 (out/'README_analysis.md').write_text('# c1s2 D/S/F local-control diagnosis\n\nQuestion: isolate constrained damage strategy, fresh/strict stopping and trial-f at one identical predecessor/start/predictor.\n\nSource: '+run.name+'; producer '+package['source_commit']+'; exact retrieval/package checks and independent native residual/history replay in s2i_analysis.json. Tables cases.csv, completed_outers.csv, phase_calls.csv, worst_trials.csv and contrasts.csv are authoritative.\n\nRead: s2i_decision.png all-arm strict residual screen and active integrals, then s2i_fields.png native-Q4 fields with shared scales, then s2i_trials.png all trial trajectories. All10 cells retained, misses labelled; first-outer and accepted-endpoint comparisons are distinct. GP/Jacobian-weighted cell means are display-only; every scalar uses unaveraged nativeGP.\n\nInterpretation: consult conditional contrasts rather than a single percentage. The fresh timing bridges retain old absolute/raw or feasible outer norms as specified. S includes accuracy policy, D includes constrained direction/line search/norm, F1 fixes only phase coefficient to1. Failed inner trials are never endpoints. Fullcube allocation omitted unless all8 accepted.\n\nAllowed: bounded same-origin numerical mechanism at synthetic c1s2. Blocked: physical/teacher validity, unique/global equilibrium, fatigue life or multicycle error law. No history was committed, and no training/solve ran on Mac. Spatial and Carrara state alignment do not erase committed-f versus trial-f or joint Deep-Ritz versus staggered differences.\n')
 print(json.dumps(dict(status=summary['status'],cases=rows,contrasts=contrasts,cube_allocation=allocation),indent=2))

def draw(out,nodes,c,w,fields,rows,outers,ledgers,runid,planned):
 names=[r['case'] for r in rows];x=np.arange(len(rows));colors=['#237a57' if r['accepted'] else '#bd6734' for r in rows]
 fig,axs=plt.subplots(1,3,figsize=(16,4.8));axs[0].bar(x,[max(r['C_effective'],1e-12) for r in rows],color=colors);axs[0].scatter(x,[max(r['C_native_p2'],1e-12) for r in rows],marker='x',c='black',label='native p2 audit');axs[0].set_yscale('log');axs[0].axhline(1,c='black',ls='--');axs[0].set_ylabel('Strict fresh joint C (descriptive for S0/T)');axs[0].legend(fontsize=8)
 axs[1].bar(x,[r['active_integral'] for r in rows],color=colors);axs[1].set_ylabel('Native active integral at last completed outer')
 for r in rows:
  q=[t for t in outers if t['case']==r['case']];axs[2].plot([t['outer'] for t in q],[max(t['C'],1e-12) for t in q],label=r['case'])
 axs[2].set_yscale('log');axs[2].axhline(1,c='black',ls='--');axs[2].set_xlabel('Completed outer (not failed inner trial)');axs[2].set_ylabel('Strict fresh C');axs[2].legend(fontsize=7,ncol=2)
 for ax in axs[:2]:ax.set_xticks(x,[r['case']+('' if r['accepted'] else '\nMISS') for r in rows],fontsize=8)
 fig.suptitle('Same-origin synthetic c1s2 | D/S/F cube + timing bridges | '+runid,fontsize=10);fig.tight_layout();fig.savefig(out/'s2i_decision.png',dpi=170);plt.close(fig)
 fig,axs=plt.subplots(2,5,figsize=(18,8));norm=Normalize(-12,np.log10(max([float(t.max()) for t in fields.values()]+[1e-11])));pc=None
 for ax,r in zip(axs.flat,planned):
  if r['case'] not in fields:
   ax.text(.5,.5,r['case']+'\n'+r['status'],ha='center',va='center');ax.set_xticks([]);ax.set_yticks([]);continue
  r=next(q for q in rows if q['case']==r['case'])
  name=r['case'];f=fields[name];cell=(w*f).sum(1)/w.sum(1);pc=PolyCollection(nodes[c],array=np.log10(np.maximum(cell,1e-12)),cmap='viridis',norm=norm,edgecolors='none',rasterized=True);ax.add_collection(pc);ax.autoscale();ax.set_aspect('equal');ax.set_title(name+(' accepted' if r['accepted'] else ' MISS / last completed'));ax.set_xlabel('native x');ax.set_ylabel('native y')
 if pc is not None:fig.colorbar(pc,ax=axs.ravel().tolist(),label='log10 GP-weighted active cell mean',shrink=.65)
 fig.suptitle('Native Q4 fields; all10 planned cases; shared scale; accepted uses declared effective policy',fontsize=12);fig.savefig(out/'s2i_fields.png',dpi=160,bbox_inches='tight');plt.close(fig)
 fig,axs=plt.subplots(2,5,figsize=(18,7),sharey=True)
 positive=[t[k] for t in ledgers for k in ['effective_f_min','native_p2_f_pred_min'] if t[k]>0];floor=min(positive+[1e-16])
 dump(out/'trial_display.json',dict(log_display_floor=floor,zero_values=sum(t[k]==0 for t in ledgers for k in ['effective_f_min','native_p2_f_pred_min']),rule='Zero coefficients plotted at the display floor only; CSV retains exact zeros.'))
 for ax,r in zip(axs.flat,planned):
  q=[t for t in ledgers if t['case']==r['case']];calls=[t['call'] for t in q]
  if not q:ax.text(.5,.5,r['case']+'\n'+r['status'],ha='center',va='center');continue
  zeros=sum(t[k]==0 for t in q for k in ['effective_f_min','native_p2_f_pred_min'])
  ax.plot(calls,[max(t['effective_f_min'],floor) for t in q],label='effective f');ax.plot(calls,[max(t['native_p2_f_pred_min'],floor) for t in q],ls=':',label='native p2 f');ax.set_yscale('log');ax.set_ylim(floor/2,1.5);ax.set_title(r['case']+(' zeros='+str(zeros) if zeros else ''));ax.set_xlabel('phase assembly call');ax.set_ylabel('minimum fatigue coefficient');ax.legend(fontsize=6)
  twin=ax.twinx();twin.plot(calls,[t['upper_violations']+t['lower_violations'] for t in q],c='#b74230',alpha=.5,lw=.7);twin.set_ylabel('out-of-bounds nodes',fontsize=7)
 fig.suptitle('All phase calls, including rejected trials | red = bounds violations | native p2 is predicted in F1');fig.tight_layout();fig.savefig(out/'s2i_trials.png',dpi=160);plt.close(fig)
 for stem in ['s2i_decision','s2i_fields','s2i_trials']:
  (out/(stem+'.md')).write_text('# '+stem+'\n\nQuestion and scope: one identical synthetic c1s2 predecessor/start; local controls only.\n\nSource: '+runid+'; cases.csv/completed_outers.csv/phase_calls.csv; exact code/inputs in s2i_analysis.json and retrieval verification.\n\nReading order, definitions and limitations: see README_analysis.md. All arms and misses retained. No physical, unique-equilibrium, teacher or multicycle claim.\n')
if __name__=='__main__':main()
