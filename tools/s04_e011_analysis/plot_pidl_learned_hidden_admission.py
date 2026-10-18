#!/usr/bin/env python3
"""Presentation-only failed-initial-admission figure; no field solve/training."""
from pathlib import Path
import argparse,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--probe',type=Path,required=True);ap.add_argument('--initial',type=Path,required=True);a=ap.parse_args()
    load=lambda p:json.loads(p.read_text())
    folder=a.run/'retrieved/archive/output';probe=load(a.probe/'retrieved/archive/output/probe_pass.json')
    initial=load(a.initial/'retrieved/archive/output/c20_s4/result.json');trace=load(folder/'c20_s4/trace.json')
    failure=load(folder/'failure.json');log=(a.run/'retrieved/run/worker.log').read_text()
    assert len(trace)==1 and trace[0]['completed'] and trace[0]['role']=='raw_network_gradient_initial_learned_head'
    assert failure['type']=='AssertionError' and 'obs[\'reduced_gradient_inf\']<=GTOL' in log
    assert trace[0]['E_el']==initial['E_el']==probe['source_reproduction']['actual_energy']
    assert not (folder/'c20_s4/checkpoints').exists()
    out=a.run/'analysis_initial_admission_failure';out.mkdir(exist_ok=False)
    sourceg=initial['actual_network']['conditioned_head_gradient_inf'];probeg=probe['source_reproduction']['actual_current_head_gradient_inf'];target=1e-10
    data=dict(status='initial_admission_failed_before_optimizer',E_el=[initial['E_el'],probe['source_reproduction']['actual_energy'],trace[0]['E_el']],
        projected_head_gradient_inf=[sourceg,probeg,None],production_gradient_bound='strictly >1e-10 inferred from exact E reproduction, finite readout and failed conjunction; exact value not saved',
        target=target,optimizer_updates=0,hidden_updates=0,Newton_updates=0,history_commits=0,production_evaluations=1,probe_evaluations=probe['evaluations'],
        interpretation='No hidden-optimization outcome, no new accepted terminal. Source/probe head gradients use their own current numerical bases; no causal attribution or norm-ratio claim.',
        sources=dict(production=str(a.run),probe=str(a.probe),unique_initial=str(a.initial),trace=str(folder/'c20_s4/trace.json'),log=str(a.run/'retrieved/run/worker.log')))
    (out/'scored_admission.json').write_text(json.dumps(data,indent=2)+'\n')
    fig,axs=plt.subplots(1,2,figsize=(12,4.7),layout='constrained');x=[0,1,2];labels=['accepted source','zero-update probe','production initial']
    axs[0].plot(x,data['E_el'],'o-',color='#0072B2');axs[0].set_xticks(x,labels,rotation=15);axs[0].ticklabel_format(axis='y',useOffset=False,style='plain');axs[0].set_ylim(initial['E_el']-1e-5,initial['E_el']+1e-5);axs[0].set_title('Same actual elastic energy, no optimisation');axs[0].set_ylabel('Eel');axs[0].text(.5,.8,'All three = 0.005268400005223913',ha='center',transform=axs[0].transAxes,fontsize=9)
    axs[1].plot([0,1],[sourceg,probeg],'o',color='#009E73');axs[1].axhline(target,color='#D55E00',ls='--',label='unchanged admission target 1e-10');axs[1].set_yscale('log');axs[1].set_ylim(1e-11,4e-10);axs[1].set_xlim(-.4,2.6);axs[1].set_xticks(x,labels,rotation=15);axs[1].set_title('Actual current-basis projected head gradient');axs[1].set_ylabel('Infinity norm (run-specific numerical basis)')
    axs[1].text(2,2.1e-10,'Rejected: > 1e-10\nExact value not saved',ha='center',va='center',fontsize=9,bbox=dict(facecolor='.95',edgecolor='.6'));axs[1].legend(loc='lower left',fontsize=8)
    fig.suptitle('PIDL c20s4: initial admission failure | 0 hidden / Newton / history updates',fontsize=12)
    fig.savefig(out/'initial_admission_failure.png',dpi=170);plt.close(fig)
    text=('# Initial admission, not a hidden-optimisation outcome\n\n## Data provenance\n\n'+json.dumps(data['sources'],indent=2)+'\n\n## How to read\n\nLeft: exact saved Eel for the accepted source, zero-update probe and production initial readout; all equal. Right: only two numeric head-gradient points are available. The production label records the inferred inequality >1e-10, not an invented exact point/bar. The dashed1e-10 line is unchanged. No actual hidden/head update or new accepted checkpoint exists.\n\n## Limitation\n\nThe production exact gradient and current basis were not persisted before the assertion. Rebuilt bases, force-accumulation rounding and other numerical readout effects cannot be distinguished here. The source/probe infinity norms use their respective numerical coordinates; do not assign physical contributions by their ratio. This does not show that hidden optimisation succeeds/fails or that network capacity is insufficient.\n')
    (out/'initial_admission_failure.md').write_text(text);(out/'README_analysis.md').write_text(text+'\nPrimary figure:initial_admission_failure.png. Generic stage figures in the sibling analysis directory contain no accepted new stages; their empty axes are missing data, never zero error.\n')
    print(out)

if __name__=='__main__':main()
