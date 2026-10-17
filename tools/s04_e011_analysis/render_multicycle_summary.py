#!/usr/bin/env python3
"""Render existing audited MCSA tables only; no new solution or scientific gate."""
import argparse,json,csv,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

def main(z):
 out=z.analysis;cases=json.loads((out/'cases.json').read_text());cases=sorted([r for r in cases if not r['anchor']],key=lambda r:(r['cycle'],r['substep']))
 rows=list(csv.DictReader((out/'crossings.csv').open()));ncp=json.loads((out/'pidl_plateau.json').read_text());trials=json.loads(z.trials.read_text())
 inputs=[out/'cases.json',out/'crossings.csv',out/'pidl_plateau.json',z.trials]
 hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs};labels=[r['case'] for r in cases]
 fig,axs=plt.subplots(2,2,figsize=(13,8.7))
 for sub,ax in [(2,axs[0,0]),(4,axs[0,1])]:
  for r in cases:
   if r['substep']!=sub:continue
   q=[v for v in rows if v['case']==r['case'] and int(v['outer'])>=1]
   line=ax.semilogy([int(v['outer']) for v in q],[float(v['u_l2']) for v in q],'.-',label=f"c{r['cycle']}"+(' budget miss' if not r['strict_accepted'] else ''))[0]
   ax.semilogy([int(v['outer']) for v in q],[float(v['d_l2']) for v in q],':',color=line.get_color(),alpha=.65)
  ax.axhline(1e-8,color='k',ls='--',lw=.8);ax.axhline(4e-6,color='grey',ls='--',lw=.8);ax.set_xlabel('Complete outer (not physical time)');ax.set_ylabel('Free residual L2');ax.set_title(f's{sub}: after-damage Ru solid / feasible Rd dotted');ax.legend(fontsize=7)
 keys=['S0V0','S1V0','S0V1','S1V1'];matrix=np.array([[np.nan if r['first_stops'][k] is None else r['first_stops'][k] for k in keys] for r in cases])
 cmap=plt.colormaps['Blues'].copy();cmap.set_bad('#dddddd');axs[1,0].imshow(matrix,cmap=cmap,norm=Normalize(1,20),aspect='auto')
 for i,r in enumerate(cases):
  for j,k in enumerate(keys):
   value=r['first_stops'][k];axs[1,0].text(j,i,'not seen <=20' if value is None else str(value),ha='center',va='center',fontsize=8,color='white' if value and value>10 else 'black')
 axs[1,0].set_yticks(range(10),labels,fontsize=8);axs[1,0].set_xticks(range(4),keys);axs[1,0].set_title('FIRST complete stop; gray = missing, no extrapolation')
 axs[1,1].bar(range(10),[100*r['last_vs_first_active_rel_L2'] for r in cases],color=['#0072B2' if r['strict_accepted'] else '#D55E00' for r in cases]);axs[1,1].set_xticks(range(10),labels,rotation=45,ha='right');axs[1,1].set_ylabel('Active weighted L2 gap / first block (%)');axs[1,1].set_title('FEM self-change; orange = last complete MISS')
 fig.suptitle('S04-E011 MCS | original predecessor frozen | no propagated repaired trajectory',fontsize=11);fig.tight_layout();fig.savefig(out/'mcs_control_reviewed.png',dpi=170);plt.close(fig)
 ncp.sort(key=lambda r:(r['cycle'],r['substep']));x=np.arange(10);labs=[f"c{r['cycle']}s{r['substep']}" for r in ncp];fig,axs=plt.subplots(2,2,figsize=(13,8))
 axs[0,0].bar(x,[r['epochs'] for r in ncp],color='#0072B2');axs[0,0].set_ylabel('Original RPROP iterations');axs[0,0].set_title('All 10 stopped on relative-loss plateau; cap 10000')
 axs[0,1].semilogy(x,[r['common_operator_PIDL_free_u_l2'] for r in ncp],'o-',label='Common Q4 free-u force');axs[0,1].axhline(1e-8,color='k',ls='--',label='FEM strict u tolerance');axs[0,1].set_ylabel('Free nodal force L2');axs[0,1].legend(fontsize=8);axs[0,1].set_title('Independent of source-objective reproduction')
 for key,label,marker in [('parameter_gradient_l2','total','o'),('physical_log_parameter_gradient_l2','physical logE','x'),('reg_parameter_gradient_l2','weight penalty','s')]:
  axs[1,0].semilogy(x,[r[key] if r['source_objective_readout_pass'] else np.nan for r in ncp],marker,ls='none',label=label)
 axs[1,0].set_ylabel('Parameter gradient L2');axs[1,0].legend(fontsize=8);axs[1,0].set_title('3 source-qualified states; other 7 omitted')
 for i,r in enumerate(ncp):
  if not r['source_objective_readout_pass']:continue
  q=[t for t in trials if t['step']==r['step'] and t['valid']];assert len(q)==8
  rise=min(t['loss']-r['loss'] for t in q);assert rise>0
  axs[1,1].bar(i,rise,color='#D55E00');axs[1,1].plot(i,r['direction_loss_roundoff_floor'],'k_',ms=15)
 axs[1,1].set_yscale('log');axs[1,1].set_ylabel('Smallest tested loss RISE (positive = worse)');axs[1,1].set_title('8 independent -gradient fractions / qualified state\nblack mark = declared roundoff screen',fontsize=9)
 for ax in axs.ravel():ax.set_xticks(x,labs,rotation=45,ha='right');ax.grid(axis='y',alpha=.2)
 fig.suptitle('Unchanged PIDL readout | no optimizer steps/history commits | no convergence certificate',fontsize=10);fig.tight_layout();fig.savefig(out/'pidl_plateau_reviewed.png',dpi=170);plt.close(fig)
 assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
 receipt=dict(kind='render_only_existing_audited_tables',inputs=hashes,new_solve=False,new_scientific_gate=False)
 (out/'render_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 for name,caption in [('mcs_control_reviewed','Four first-stop policies on actual complete blocks; gray explicitly means no strict crossing observed within20; not future redundancy. Active self-change uses each state first-block norm; orange strict MISS.'),('pidl_plateau_reviewed','Original stop iterations, common free-u force, three source-qualified gradient readouts and actual smallest tested loss RISE among eight independent trials. Seven source-component mismatches omitted from original-objective attribution. No lower loss at this grid is not a stationarity proof.')]:
  (out/(name+'.md')).write_text('# '+name+'\n\n'+caption+'\n\nSource MCSA analysis903b2ae, MCS0a0691e and NCP348be4b; exact input table hashes in render_receipt.json. See README_analysis.md, cases.json, policies.csv, crossings.csv, pidl_plateau.json and original NCP trials.json. No training/solve/history update.\n')
 print('RENDER_COMPLETE')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);p.add_argument('--trials',type=Path,required=True);main(p.parse_args())
