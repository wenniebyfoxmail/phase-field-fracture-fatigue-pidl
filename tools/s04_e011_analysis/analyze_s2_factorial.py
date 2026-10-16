#!/usr/bin/env python3
"""Read-only c1s2 Q4 replay and controlled solver/predecessor attribution."""
import argparse,csv,hashlib,json
from pathlib import Path
import h5py,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize,SymLogNorm
from analyze_c1_commit import state,a,v,scalar,same
from run_multicycle_cross_replay import q4_geometry,amor_raw,interp
from audit_phase_tangent import assemble
from localize_endpoint_tight import mechanics_force
from audit_fem_final_residuals import projected_gradient
from audit_raw_response_bound import admission as raw_admission,stencil as raw_stencil

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def dump(path,data):path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def table(path,rows):
 if not rows:return
 with path.open('w',newline='') as f:
  wr=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');wr.writeheader();wr.writerows(rows)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-run',required=True,type=Path);ap.add_argument('--run',required=True,type=Path);ap.add_argument('--package',type=Path);z=ap.parse_args();out=z.run/'analysis';out.mkdir(parents=True,exist_ok=True)
 src=z.source_run/'retrieved/output/c1_commit';receipt=json.loads((z.source_run/'retrieval_verification.json').read_text());assert receipt['all_hashes_and_sizes_match']
 for item in receipt['manifest']:
  p=z.source_run/'retrieved'/item['relative'].replace('\\','/');assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
 with h5py.File(src/'common_initial.mat') as h:
  points=a(h,'node_coords').T;c=a(h,'connectivity').T.astype(int)-1;fu=v(h,'free_dof_u').astype(int)-1;fd=v(h,'free_dof_d').astype(int)-1
 N,B,w,xy=q4_geometry(points,c);n=len(points);inputs=[src/'common_initial.mat'];pres={};ends={};fields={}
 for label,arm in [('O','original'),('R','repaired')]:
  with h5py.File(src/arm/'s1/accepted_commit.mat') as h:pres[label]=state(h['proposed'])
  p=src/arm/'s2/accepted_commit.mat';inputs.extend([p,src/arm/'s1/accepted_commit.mat'])
  with h5py.File(p) as h:
   same(state(h['pre']),pres[label]);ends[label]=dict(u=v(h['candidate'],'u'),d=v(h['candidate'],'d'),raw=a(h['candidate'],'raw').T)
   assert np.max(np.abs(ends[label]['raw']-amor_raw(ends[label]['u'][:n],ends[label]['u'][n:],c,B))/np.maximum(1,np.abs(ends[label]['raw'])))<=1e-10
 for U in ['O','R']:
  for D in ['O','R']:fields[U+D]=amor_raw(ends[U]['u'][:n],ends[U]['u'][n:],c,B)*(1-interp(ends[D]['d'],c,N))**2
 delta=fields['RR']-fields['OO'];den=float(np.sum(w*delta**2));assert den>0
 def stats(name,f):
  return dict(name=name,integral=float(np.sum(w*f)),weighted_L2=float(np.sqrt(np.sum(w*f*f))),relative_L2_to_archived_OO=float(np.sqrt(np.sum(w*(f-fields['OO'])**2)/np.sum(w*fields['OO']**2))))
 def effect(name,f):
  return dict(component=name,projection_onto_observed_delta=float(np.sum(w*f*delta)/den),L2_over_observed_delta=float(np.sqrt(np.sum(w*f*f)/den)),signed_integral=float(np.sum(w*f)))
 ucomp=((fields['RO']-fields['OO'])+(fields['RR']-fields['OR']))/2
 dcomp=((fields['OR']-fields['OO'])+(fields['RR']-fields['RO']))/2
 assert np.max(np.abs(delta-ucomp-dcomp))<1e-12
 replay=[stats(k,f) for k,f in fields.items()];effects=[effect('displacement_response',ucomp),effect('damage_degradation',dcomp)]
 regions=[]
 for name,mask in [('wake_x_le_0',xy[:,:,0]<=0),('ligament_x_gt_0',xy[:,:,0]>0),('wake_lower',(xy[:,:,0]<=0)&(xy[:,:,1]<=0)),('wake_upper',(xy[:,:,0]<=0)&(xy[:,:,1]>0)),('ligament_lower',(xy[:,:,0]>0)&(xy[:,:,1]<=0)),('ligament_upper',(xy[:,:,0]>0)&(xy[:,:,1]>0))]:
  regions.append(dict(region=name,area=float(w[mask].sum()),weighted_squared_gap_share=float((w*delta**2)[mask].sum()/den)))
 sq=w*delta**2;ij=np.unravel_index(np.argmax(np.abs(delta)),delta.shape)
 localization=dict(max_absolute_gap=float(abs(delta[ij])),signed_gap_at_max=float(delta[ij]),zero_based_cell=int(ij[0]),zero_based_gp=int(ij[1]),max_gap_xy=xy[ij].tolist(),squared_gap_centroid=(np.sum(sq[...,None]*xy,axis=(0,1))/den).tolist(),regions=regions)
 history=[]
 for label,endpoint in ends.items():
  for L,low in pres.items():
   for H,hist in pres.items():
    rd,t=assemble(endpoint['d'],endpoint['raw'],low['lower'],hist['history'],c,N,B,w,n)
    history.append(dict(endpoint=label,lower=L,history=H,bound_filtered_phase_l2=float(np.linalg.norm(projected_gradient(endpoint['d'][fd],rd[fd],low['lower'][fd]))),infeasible_nodes=int(np.count_nonzero((endpoint['d']<low['lower']-1e-12)|(endpoint['d']>1+1e-12))),f_min=float(t['f'].min()),f_max=float(t['f'].max()),alpha_max=float(t['alpha'].max()),penalized_gp=int(np.count_nonzero(t['pen'])),active_integral=float(np.sum(w*t['active']))))
 dump(out/'offline_replay.json',dict(cross_ud=replay,effects=effects,localization=localization,history_lower_cross=history,definition='Exact GP/Jacobian weighting. U/D letters identify archived endpoint displacement/damage. Effects are symmetric algebraic allocations, not physical causal fractions.',inputs=[dict(path=str(p),sha256=sha(p)) for p in inputs]))
 table(out/'cross_ud.csv',replay);table(out/'cross_ud_effects.csv',effects);table(out/'fixed_regions.csv',regions);table(out/'history_lower_cross.csv',history)
 draw_offline(out,points,c,w,fields,effects,regions,z.run.name)
 native=z.run/'retrieved';base=native/'output/s2x';native_rows=[];controlled={};case_fields={};case_inputs=[]
 retrieval_verified=False
 if (z.run/'retrieval_verification.json').exists():
  rc=json.loads((z.run/'retrieval_verification.json').read_text());assert rc['all_hashes_and_sizes_match']
  assert rc['files']==len(rc['manifest']) and rc['bytes']==sum(t['bytes'] for t in rc['manifest'])
  for item in rc['manifest']:
   p=native/item['relative'].replace('\\','/');assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
  assert z.package is not None,'Exact reviewed package required for native evidence'
  package=json.loads(z.package.read_text());review=json.loads((z.package.parent/'local_independent_review.json').read_text())
  assert review['status']=='passed' and review['package_manifest_sha256']==sha(z.package) and review['commit']==package['source_commit']
  for item in package['files']:
   p=native/item['name'];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
  launch=json.loads((native/'launch_receipt.json').read_text(encoding='utf-8-sig'));nm=json.loads((native/'input_manifest.json').read_text())
  assert launch['commit']==nm['source_commit']==package['source_commit'] and launch['dirty'] is False and launch['threads']==1
  assert launch['root']==package['remote_root'] and launch['account'].lower()==r'ad\xw436'
  assert nm['protocol_revision']=='S04-E011-S2X-r1' and nm['staging']==package['staging']
  original_inputs={'common':src/'common_initial.mat','mesh':z.source_run/'retrieved/inputs/0e6db55abde58802_0e6db55abde58802_native_q4_original.inp'}
  for letter,arm in [('O','original'),('R','repaired')]:
   for step in [1,2]:original_inputs[letter+str(step)]=src/arm/f's{step}/accepted_commit.mat'
  assert len(nm['staging'])==len(original_inputs)==6
  for item in nm['staging']:
   p=original_inputs[item['role']];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
   p=native/'inputs'/item['target'].replace('\\','/').split('/')[-1];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
  tests=json.loads((native/'selftest.json').read_text(encoding='utf-8-sig'))
  for name,cases in [('damage',6),('coupled',6),('commit',10),('raw',12)]:assert tests[name]['status']=='passed' and tests[name]['cases']==cases
  io=json.loads((native/'io_preflight.json').read_text(encoding='utf-8-sig'));assert io['status']=='passed' and io['unique_inputs']==6
  retrieval_verified=True
 for name in ['anchor_OO','anchor_RR','C_OO','C_RO','C_OR','C_RR']:
  p=base/name/'completed.mat'
  if not p.exists():continue
  case_inputs.append(p);P=name[-1];mode='original' if name[-2]=='O' else 'repaired'
  with h5py.File(p) as h:
   pre=state(h['pre']);same(pre,pres[P]);u=v(h['candidate'],'u');d=v(h['candidate'],'d');raw=a(h['candidate'],'raw').T
   start=dict(u=v(h['start'],'u'),d=v(h['start'],'d'));pr=dict(u=v(h['predictor'],'u'),d=v(h['predictor'],'d'),r=v(h['predictor'],'r'))
   if name.startswith('C_'):
    assert np.array_equal(start['u'],pres['O']['u']) and np.array_equal(start['d'],np.maximum(pres['O']['d'],pres['R']['d']))
    if controlled:same(pr,next(iter(controlled.values())))
    controlled[name]=pr
   else:
    assert np.array_equal(start['u'],pres[P]['u']) and np.array_equal(start['d'],pres[P]['d'])
    assert max(np.max(np.abs(u-ends[P]['u'])),np.max(np.abs(d-ends[P]['d'])))<=1e-10
    assert bool(scalar(h['reference'],'pass'))
   expected=amor_raw(u[:n],u[n:],c,B);assert np.max(np.abs(raw-expected)/np.maximum(1,np.abs(expected)))<=1e-10
   rd,t=assemble(d,raw,pre['lower'],pre['history'],c,N,B,w,n);ru=mechanics_force(u,d,c,N,B,w,n)
   if name.startswith('anchor_'):
    with h5py.File(src/('original' if P=='O' else 'repaired')/'s2/accepted_commit.mat') as ref:
     reference_history=a(ref['proof'],'history234').transpose(2,1,0)
     assert np.max(np.abs(np.stack([t['alpha'],t['active'],t['f']],axis=2)-reference_history)/np.maximum(1,np.abs(reference_history)))<=1e-10
     assert scalar(h['out'],'completed_outer')==scalar(ref['out'],'completed_outer')
    rc_anchor,_=raw_admission(u,raw,ends[P]['u'],ends[P]['raw'],c,raw_stencil(points,c),n);assert rc_anchor['pass_new']
   err=max(float(np.max(np.abs(ru-v(h['proof'],'ru')))),float(np.max(np.abs(rd-v(h['proof'],'rd')))))
   assert err<=1e-10 and np.max(np.abs(a(h['proof'],'history234').transpose(2,1,0)-np.stack([t['alpha'],t['active'],t['f']],axis=2)))<=1e-10
   assert np.all(d>=pre['lower']-1e-12) and np.all(d<=1+1e-12)
   fixed_u=np.setdiff1d(np.arange(2*n),fu);fixed_d=np.setdiff1d(np.arange(n),fd)
   assert np.array_equal(u[fixed_u],pr['u'][fixed_u]) and np.array_equal(d[fixed_d],start['d'][fixed_d])
   ur=float(np.linalg.norm(ru[fu]));dr=float(np.linalg.norm(projected_gradient(d[fd],rd[fd],pre['lower'][fd])));C=max((ur+dr)/4e-6,ur/1e-8)
   summary=h['summary'];uc=int(scalar(h['counts'],'u'));dc=int(scalar(h['counts'],'d'));blocks=int(scalar(h['out'],'completed_outer'))
   assert scalar(summary,'history_commits')==0 and abs(C-scalar(summary,'C'))<1e-8*max(1,C)
   native_accepted=bool(scalar(summary,'native_accepted'));passed=(base/name/'result.json').exists() and native_accepted and bool(scalar(summary,'reference_pass')) and (mode=='original' or C<=1) and not(base/name/'failure.json').exists()
   if mode=='repaired':assert uc<=250 and dc<=250 and blocks<=20
   if passed and mode=='repaired':assert C<=1
   row=dict(case=name,solver=mode,predecessor=P,passed=passed,C=C,u_l2=ur,d_feasible_l2=dr,blocks=blocks,u_calls=uc,phase_calls=dc,history_commits=0,native_residual_maxerr=err,trial_f_min=float(scalar(summary,'trial_f_min')),trial_alpha_max=float(scalar(summary,'trial_alpha_max')),phase_calls_with_f_below_one=int(scalar(summary,'phase_calls_with_f_below_one')),final_f_min=float(t['f'].min()),active_integral=float(np.sum(w*t['active'])),active_relative_L2_to_archived_OO=float(np.sqrt(np.sum(w*(t['active']-fields['OO'])**2)/np.sum(w*fields['OO']**2))))
   native_rows.append(row);case_fields[name]=t['active']
 table(out/'native_cases.csv',native_rows)
 success=(native/'sequence_finished.json').exists();allocation=[];components={}
 if success:
  assert retrieval_verified,'Terminal marker alone is not verified native evidence'
  assert len(native_rows)==6 and all(r['passed'] for r in native_rows)
  terminal=json.loads((native/'sequence_finished.json').read_text(encoding='utf-8-sig'));assert terminal['history_commits']==0
  OO,RO,OR,RR=[case_fields['C_'+k] for k in ['OO','RO','OR','RR']]
  components=dict(local_solver=((RO-OO)+(RR-OR))/2,incoming_lower_history=((OR-OO)+(RR-RO))/2,warm_start_bridge=(OO-fields['OO'])+(fields['RR']-RR))
  interaction=RR-RO-OR+OO;error=float(np.max(np.abs(delta-sum(components.values()))));assert error<=1e-12
  allocation=[effect(k,f) for k,f in components.items()];assert abs(sum(r['projection_onto_observed_delta'] for r in allocation)-1)<1e-10
  contrasts=[effect(k,f) for k,f in [('solver_at_O',RO-OO),('solver_at_R',RR-OR),('predecessor_at_O',OR-OO),('predecessor_at_R',RR-RO),('interaction',interaction)]]
  for row,ref in zip(contrasts,[OO,OR,OO,RO]):
   row['relative_difference_to_pair_reference']=float(row['L2_over_observed_delta']*np.sqrt(den/np.sum(w*ref**2)))
  contrasts[-1]['relative_difference_to_pair_reference']=None
  table(out/'controlled_allocation.csv',allocation);table(out/'conditional_contrasts.csv',contrasts)
  dump(out/'controlled_attribution.json',dict(components=allocation,conditional_contrasts=contrasts,exact_reconstruction_maxerr=error,primary='Diagnostic field decomposition; projection coefficients can be negative or >1 and do not imply physical causal percentages. Incoming lower/history is a grouped effect. Warm-start bridge depends on chosen common trial start.'))
  draw(out,points,c,w,fields,case_fields,components,native_rows,allocation,z.run.name)
 status='six_case_complete_offline_checked' if success else 'offline_replay_complete_native_pending_or_partial'
 code=[Path(__file__).resolve(),Path(assemble.__code__.co_filename),Path(amor_raw.__code__.co_filename),Path(mechanics_force.__code__.co_filename),Path(raw_admission.__code__.co_filename)]
 dump(out/'s2x_analysis.json',dict(status=status,run=z.run.name,source_run=str(z.source_run),raw_admission='r4 retained for anchors; no criterion relaxation',native_cases=native_rows,allocation=allocation,history_commits=0,source_inputs=[dict(path=str(p),sha256=sha(p)) for p in inputs+case_inputs],analysis_code=[dict(path=str(p),sha256=sha(p)) for p in dict.fromkeys(code)],scope='One synthetic c1s2. No physical/teacher/unique-equilibrium or multi-cycle growth claim.'))
 print(json.dumps(dict(status=status,offline_effects=effects,localization=localization,native_cases=native_rows,allocation=allocation),indent=2))

def draw_offline(out,points,c,w,fields,effects,regions,runid):
 fig,axs=plt.subplots(2,3,figsize=(13,8));axes=axs.reshape(-1)
 norm=Normalize(-12,np.log10(max(float(f.max()) for f in fields.values())))
 for ax,k in zip(axes[:4],['OO','RO','OR','RR']):
  cell=(w*fields[k]).sum(1)/w.sum(1)
  pc=PolyCollection(points[c],array=np.log10(np.maximum(cell,1e-12)),cmap='viridis',norm=norm,edgecolors='none',antialiased=False,rasterized=True)
  ax.add_collection(pc);ax.autoscale();ax.set_aspect('equal');ax.set_title(k+' (first displacement, second damage)');ax.set_xlabel('native x');ax.set_ylabel('native y');fig.colorbar(pc,ax=ax,label='log10 active cell mean',shrink=.7)
 axes[4].bar([0,1],[r['projection_onto_observed_delta'] for r in effects]);axes[4].axhline(0,c='black',lw=.5);axes[4].set_xticks([0,1],['displacement','damage']);axes[4].set_ylabel('Signed projection onto archived active difference')
 rr=regions[2:];axes[5].bar(range(4),[r['weighted_squared_gap_share'] for r in rr]);axes[5].set_xticks(range(4),[r['region'] for r in rr],rotation=30,ha='right');axes[5].set_ylabel('Share of weighted squared archived gap')
 fig.suptitle('Saved synthetic c1s2 Q4 cross replay | no new solve | '+runid,fontsize=10);fig.tight_layout();fig.savefig(out/'s2x_cross_replay.png',dpi=160);plt.close(fig)
 (out/'s2x_cross_replay.md').write_text('# Saved c1s2 u/d cross replay\n\nQuestion: locate archived active-field differences and distinguish algebraic displacement/damage response.\n\nData provenance: Run '+runid+'; source archive c1v4_r1 producer6794251, exact input/code identities in offline_replay.json and s2x_analysis.json. All four endpoint cross combinations are shown. First letter identifies archived displacement O/R, second archived damage O/R; crossed fields are artificial operator evaluations, not solved equilibria.\n\nHow to read: Four spatial panels use native Q4 polygons coloured by GP/Jacobian-weighted cell active means, shared log10 scale with1e-12 floor. Tables retain unaveraged native GP. Fifth panel gives symmetric signed projection onto full archived RR−OO difference: '+json.dumps(effects)+'. Negative or >1 values expose cancellation, not causal percentages. Sixth panel shows the four predeclared x/y quadrants and weighted squared-gap shares; all quadrants shown, no adaptive windows.\n\nMain takeaway: raw displacement response and damage degradation changes strongly cancel; the left initial crack wake accounts for '+str(sum(r['weighted_squared_gap_share'] for r in rr[:2]))+' of squared gap.\n\nLimitations: This is one synthetic c1s2, not a forecast/holdout or physical reference. No solves/commits performed in this replay; crossed states can be mechanically unbalanced/infeasible relative to another lower. Native controlled cases, if available, answer a different solver/predecessor diagnostic. No unique equilibrium/teacher/fatigue-life claim.\n')

def draw(out,points,c,w,fields,case_fields,components,rows,alloc,runid):
 fig,axs=plt.subplots(2,4,figsize=(16,8));polygons=points[c];axes=axs.reshape(-1)
 panels=[('Archived OO',fields['OO']),('Archived RR',fields['RR'])]+[(k,case_fields['C_'+k]) for k in ['OO','RO','OR','RR']]
 top=max(float(f.max()) for _,f in panels);norm=Normalize(-12,np.log10(max(top,1e-12)))
 for ax,(title,f) in zip(axes,panels):
  fcell=(w*f).sum(1)/w.sum(1);pc=PolyCollection(polygons,array=np.log10(np.maximum(fcell,1e-12)),cmap='viridis',norm=norm,edgecolors='none',antialiased=False,rasterized=True);ax.add_collection(pc);ax.autoscale();ax.set_aspect('equal');ax.set_title(title);fig.colorbar(pc,ax=ax,label='log10 active cell mean',shrink=.7)
 vm=max(float(np.max(np.abs(components[k]))) for k in ['local_solver','incoming_lower_history']);sn=SymLogNorm(linthresh=max(vm*1e-3,1e-15),vmin=-vm,vmax=vm)
 for ax,k in zip(axes[6:],['local_solver','incoming_lower_history']):
  fcell=(w*components[k]).sum(1)/w.sum(1);pc=PolyCollection(polygons,array=fcell,cmap='RdBu_r',norm=sn,edgecolors='none',antialiased=False,rasterized=True);ax.add_collection(pc);ax.autoscale();ax.set_aspect('equal');ax.set_title(k);fig.colorbar(pc,ax=ax,label='signed active component',shrink=.7)
 for ax in axes:ax.set_xlabel('native x');ax.set_ylabel('native y')
 fig.suptitle('Synthetic c1s2 | first letter solver, second incoming lower/history | '+runid,fontsize=11);fig.tight_layout();fig.savefig(out/'s2x_fields.png',dpi=160);plt.close(fig)
 fig,axs=plt.subplots(1,2,figsize=(12,4.5));x=np.arange(len(rows));axs[0].bar(x,[r['C'] for r in rows]);axs[0].set_yscale('log');axs[0].axhline(1,ls='--',c='black');axs[0].set_xticks(x,[r['case'] for r in rows],rotation=20);axs[0].set_ylabel('Fresh joint C; dashed threshold1 for repaired')
 axs[1].bar(np.arange(3),[r['projection_onto_observed_delta'] for r in alloc]);axs[1].axhline(0,c='black',lw=.5);axs[1].set_xticks(range(3),['local solver','lower+history','warm-start bridge'],rotation=12);axs[1].set_ylabel('Signed projection onto archived active difference');fig.suptitle('c1s2 controlled diagnostic | '+runid,fontsize=10);fig.tight_layout();fig.savefig(out/'s2x_decision.png',dpi=180);plt.close(fig)
 for leaf,desc in [('s2x_fields','Top/first six panels: archived OO/RR and all four common-start controlled native-Q4 active fields. First letter solver O/R; second lower/history O/R. Identical log10 scale for these six panels, floor1e-12. Last two panels: signed symmetric local-solver and incoming-lower/history components, shared symlog scale. Native Q4 polygon colours are physical-GP-weighted cell means for display only; tables use all native GP directly. All cases shown, no selected windows.'),('s2x_decision','Left: all six native fresh PRE-COMMIT C values under each OLD lower/history; threshold1 applies to repaired, while original keeps native cached acceptance. Right: signed projections of local solver, grouped incoming lower/history, and common-start bridge onto the archived active difference. Contributions sum to1; they are bookkeeping allocations with possible cancellation, not causal percentages. No winner threshold.')]:
  (out/(leaf+'.md')).write_text('# c1s2 controlled attribution\n\nQuestion: local solver versus incoming irreversible state and warm start. Synthetic, diagnostic, onec1s2, no holdout/forecast.\n\nData provenance: Run '+runid+'. Exact inputs/code hashes in s2x_analysis.json; native_cases.csv and controlled_allocation.csv are authoritative.\n\nHow to read: '+desc+'\n\nNumerical takeaway: '+json.dumps(alloc)+'\n\nLimitations: common feasible d=max(s1O,s1R) is artificial trial initialization; two diagonal anchors admit restart fidelity only. P groups lower/history, L/P split the interaction symmetrically; bridge is chosen-start dependent. Repeated trials do not commit history; history commits0. Smaller residual does not prove unique/global equilibrium, spatial truth, qualified teacher, fatigue life or multi-cycle growth. New trial/final f values in native_cases.csv must be consulted before saying fatigue feedback is inactive.\n')
if __name__=='__main__':main()
