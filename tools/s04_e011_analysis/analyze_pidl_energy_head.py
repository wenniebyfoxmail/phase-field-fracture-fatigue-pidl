#!/usr/bin/env python3
"""Offline independent Q4 replay of same-energy fixed-feature UV-head diagnostics."""
import argparse,json,csv,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize,SymLogNorm
from matplotlib.ticker import FormatStrFormatter
from analyze_pidl_block_diagnosis import independent_operator,q4_fields,dump
ROOT=Path(__file__).resolve().parents[2]
BASE=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011')
OLD=BASE/'runs/pf_s04e011_pbd_2c7c5dc_20261017T2110Z_production/retrieved/archive/output'

def complete_sidecars(out, run):
 for image in out.glob('*.png'):
  sidecar=image.with_suffix('.md');caption=sidecar.read_text()
  if '## Data provenance' in caption:continue
  caption+=f"\n## Data provenance\n\nRun {run.name}; producer c3e42282; actual installed-network fields in retrieved/archive/output, original/PBD comparison from the closed2c7c5dc run. c1s4 step4 and c20s4 step99, native86756nodes/86408Q4 elements/2x2GP, eta0. Exact metric values and input identities are in summary.json and the run contract.\n\n## How to read\n\nUse the panel titles and existing caption above for the plotted quantity, axes and method. FEM is the numerical reference; all PIDL U candidates use the same fixed FEM damage. Fields use GP-weighted cell means, mass-L2 uses assembled nodal mass, H1 uses full Q4 displacement gradients. Colour limits are shared per field row; signed errors are candidate minus FEM. Curve plots use every accepted point and count trials in the evaluation axis.\n\n## Main numerical takeaway and limitation\n\nHead Eel c1/c20 is .006342778465/.006024091519, above PBD .005672469584/.005401565679; the actual conditioned-gradient L2 remains .0316614/.00791124 at400calls. Smaller late energy differences do not certify stationarity. These are independent conditional peak mechanical blocks, not a new joint PIDL trajectory, physical teacher, or a full-head/network capacity bound. No missing/partial candidate is scored as a verified head result.\n"
  sidecar.write_text(caption)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--output-name',default='analysis');a=ap.parse_args();assert Path(a.output_name).name==a.output_name;out=a.run/a.output_name;out.mkdir(exist_ok=False)
 worker=a.run/'retrieved/archive/output';op,_=independent_operator(ROOT);rows=[];states=[]
 for cycle in [1,20]:
  rp=worker/f'c{cycle}_s4/result.json'
  if not rp.exists():
   states.append(dict(cycle=cycle,status='missing',primary_directional_screen=None));continue
  gate=json.loads(rp.read_text())
  if gate['status']!='completed' or gate.get('actual_network') is None:
   states.append(dict(cycle=cycle,status=gate['status'],primary_directional_screen=None,worker=gate));continue
  inp=dict(np.load(BASE/f'pidl_block_preparation_20261017_v1/inputs/c{cycle}_peak.npz'));geo=op.q4_geometry(inp['nodes'],inp['cells']);N,B,w,_=geo;c=inp['cells'];mass=np.zeros(len(inp['nodes']))
  for j in range(4):np.add.at(mass,c[:,j],np.sum(w*N[:,j],axis=1))
  fem={k:inp[k+'_fem'] for k in ['u','v','d']};head=dict(np.load(worker/f'c{cycle}_s4/fields.npz'))
  fields={'FEM':fem,'PIDL original UV':dict(np.load(OLD/f'c{cycle}_s4/fields.npz')),'PIDL PBD U-energy':dict(np.load(OLD/f'c{cycle}_s4/U_energy/fields.npz')),'PIDL frozen head':head}
  ref=q4_fields(fem,inp,op,geo);den=np.sum(mass*(fem['u']**2+fem['v']**2));hden=np.sum(w*(ref['gu']**2+ref['gv']**2).sum(2));scored={}
  for name,f in fields.items():
   assert all(np.isfinite(f[k]).all() for k in ['u','v','d']);assert np.array_equal(f['d'],fem['d']),(cycle,name,'fixed damage changed')
   q=q4_fields(f,inp,op,geo);scored[name]=q
   r=dict(cycle=cycle,substep=4,method=name,E_el=q['E_el'],elastic_excess=q['E_el']/ref['E_el']-1,free_u_l2=q['independent_free_u_l2'],uv_mass_rel_L2=float(np.sqrt(np.sum(mass*((f['u']-fem['u'])**2+(f['v']-fem['v'])**2))/den)),uv_H1_rel=float(np.sqrt(np.sum(w*((q['gu']-ref['gu'])**2+(q['gv']-ref['gv'])**2).sum(2))/hden)))
   rows.append(r)
  hr=rows[-1];pbd=rows[-2];info=json.loads((worker/f'c{cycle}_s4/result.json').read_text());energy_check=abs(hr['E_el']-info['actual_network']['E_el'])/max(abs(hr['E_el']),1e-30);assert energy_check<1e-9,(cycle,energy_check)
  checks={k:abs(hr[k]-info['actual_network'][k])/max(abs(hr[k]),1e-30) for k in ['free_u_l2','uv_mass_rel_L2','uv_H1_rel']};assert max(checks.values())<1e-9,(cycle,checks)
  delta=1-hr['E_el']/pbd['E_el'];states.append(dict(cycle=cycle,pbd_relative_energy_reduction=delta,primary_directional_screen=bool(delta>=1e-4),independent_energy_relative_discrepancy=energy_check,independent_metric_relative_discrepancies=checks,worker=info))
  # Every prescribed state and every scored mechanical candidate, no example selection.
  fig,axs=plt.subplots(3,4,figsize=(15,10),layout='constrained');polygons=inp['nodes'][c]
  for ir,(quantity,label) in enumerate([('u','horizontal u'),('v','vertical v'),('active','active energy')]):
   vals=[]
   for name,f in fields.items():
    gp=scored[name]['active'] if quantity=='active' else op.interp(f[quantity],c,N);vals.append(np.sum(w*gp,axis=1)/w.sum(1))
   lo=min(float(v.min()) for v in vals);hi=max(float(v.max()) for v in vals);norm=Normalize(lo,hi) if quantity!='active' else SymLogNorm(max(abs(lo),abs(hi),1e-30)*1e-5,vmin=lo,vmax=hi)
   for j,((name,_),v) in enumerate(zip(fields.items(),vals)):
    ax=axs[ir,j];pc=PolyCollection(polygons,array=v,cmap='viridis',norm=norm,edgecolors='none');ax.add_collection(pc);ax.autoscale();ax.set_aspect('equal');ax.set_title(label+' | '+name,fontsize=8);fig.colorbar(pc,ax=ax,shrink=.75)
  fig.suptitle(f'c{cycle}s4 | all PIDL U candidates use fixed FEM damage; native Q4 cell means | synthetic diagnostic')
  path=out/f'c{cycle}_mechanical_fields.png';fig.savefig(path,dpi=135);plt.close(fig)
  path.with_suffix('.md').write_text(f'Question: same-energy UV-head recovery. c{cycle}s4, all four scored exports, nativeQ4 2x2GP cell means, same row limits. FEM first, original PIDL UV + FEM d, PBD full-network U + FEM d, new frozen-feature UV head + FEM d. These are conditional hybrids, not jointly solved trajectories. Sources: {worker}, {OLD}; metrics: summary.json. No physical/whole-network capacity certificate.\n')
  fig,axs=plt.subplots(2,3,figsize=(12,7),layout='constrained')
  for ir,key in enumerate(['u','v']):
   gp0=op.interp(fem[key],c,N);errors=[np.sum(w*op.interp(fields[name][key]-fem[key],c,N),axis=1)/w.sum(1) for name in list(fields)[1:]];lim=max(max(float(abs(v).max()) for v in errors),1e-30)
   for j,(name,val) in enumerate(zip(list(fields)[1:],errors)):
    ax=axs[ir,j];pc=PolyCollection(polygons,array=val,cmap='RdBu_r',norm=SymLogNorm(lim*1e-4,vmin=-lim,vmax=lim),edgecolors='none');ax.add_collection(pc);ax.autoscale();ax.set_aspect('equal');ax.set_title(key+': '+name+' minus FEM',fontsize=9);cb=fig.colorbar(pc,ax=ax,shrink=.75);cb.set_ticks([-lim,-lim/100,0,lim/100,lim]);cb.ax.yaxis.set_major_formatter(FormatStrFormatter('%.2g'))
  fig.suptitle(f'c{cycle}s4 | signed UV errors; fixed FEM d; shared signed scale per row');path=out/f'c{cycle}_uv_errors.png';fig.savefig(path,dpi=135);plt.close(fig);path.with_suffix('.md').write_text('Exact scored fields, signed displacement errors on nativeQ4 GP-weighted cell means. All three PIDL mechanical candidates versus the same conditional FEM peak, shared signed symlog row scale; full domain without clipping. See summary.json and mechanical-fields sidecar for provenance and limitations.\n')
 dump(out/'summary.json',dict(protocol='S04-E011-UVHEAD-r1',run=str(a.run),rows=rows,states=states,claim_boundary='retained frozen-feature head, fixed FEM d; no trajectory/whole-network capacity/physical claim'))
 if not rows:
  (out/'README_analysis.md').write_text('No actually verified head endpoints; see summary.json. Missing/partial states excluded from gain comparisons.');return
 with (out/'metrics.csv').open('w') as f:
  cw=csv.DictWriter(f,fieldnames=list(rows[0]));cw.writeheader();cw.writerows(rows)
 fig,axs=plt.subplots(1,3,figsize=(12,4),layout='constrained')
 for cycle in [1,20]:
  rr=[r for r in rows if r['cycle']==cycle]
  if not rr:continue
  for ax,key in zip(axs,['elastic_excess','free_u_l2','uv_mass_rel_L2']):ax.plot(range(4),[r[key] for r in rr],'o-',label=f'c{cycle}s4');ax.set_xticks(range(4),['FEM','Original UV','PBD U','Frozen head'],rotation=25);ax.set_title(key);ax.grid(alpha=.2);ax.legend()
 axs[1].set_title('free_u_l2 (FEM ~4e-15)');fig.suptitle('Fixed FEM damage | original hidden head energy solve | synthetic exploration');path=out/'head_decision.png';fig.savefig(path,dpi=150);plt.close(fig);path.with_suffix('.md').write_text('Both prescribed states, exact independent replay metrics in metrics.csv, same FEM damage across all mechanical candidates. Elastic excess relative to conditional FEM; force is absolute free-u L2; UV error mass weighted. Head versus PBD gain threshold1e-4 is diagnostic, not physical accuracy. No whole-network capacity claim.\n')
 fig,axs=plt.subplots(1,2,figsize=(12,4),layout='constrained')
 for state in states:
  if 'worker' not in state or state['worker'].get('status')!='completed':continue
  cy=state['cycle'];accepted=json.loads((worker/f'c{cy}_s4/accepted.json').read_text());ref_energy=state['worker']['FEM']['E_el'];x=[q['evaluations'] for q in accepted]
  axs[0].plot(x,[q['E_el']/ref_energy-1 for q in accepted],label=f'c{cy}s4')
  axs[1].semilogy(x,[q['reduced_gradient_l2'] for q in accepted],label=f'c{cy}s4')
 for ax,title in zip(axs,['Accepted elastic excess relative to FEM','Conditioned head gradient L2 (accepted only)']):ax.set_title(title);ax.set_xlabel('Objective / gradient evaluations, trials included');ax.grid(alpha=.2);ax.legend()
 fig.suptitle('Small energy changes do not certify head stationarity | 400-call cap, no retry');path=out/'head_stationarity.png';fig.savefig(path,dpi=150);plt.close(fig)
 path.with_suffix('.md').write_text('Exact accepted.json curves, all accepted points for c1s4/c20s4. Abscissa includes trial and contract calls; final actual installed-head observation is call400 and in summary.json. Left: elastic excess over the independent conditional FEM reference. Right: conditioned-gradient L2, not the global nodal force. Library gtol uses infinity norm and is not drawn as an L2 threshold. Both runs stopped at evaluation cap, so finite candidate gradients cannot establish a feature-space optimum. Source: worker directories in summary.json. No new optimization evaluations.\n')
 (out/'README_analysis.md').write_text('S04-E011 UVHEAD r1. Offline NumPy nativeQ4 replay, no training/history update. Both c1s4/c20s4 included. Read summary.json/metrics.csv; head_decision shows scalar tradeoffs; mechanical_fields shows FEM/original/PBD/head on row-shared scales; uv_errors shows signed errors. All PIDL U fields paired with fixed FEM damage. Original paired joint PIDL baseline and B0 Smooth Boundary/constrained-Q4 damage routes unchanged. No stitched trajectory or physical certificate.\n')
 complete_sidecars(out,a.run)
 print(json.dumps(states,indent=2))
if __name__=='__main__':main()
