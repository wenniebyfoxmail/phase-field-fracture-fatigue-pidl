"""Existing-output/source analysis only; no forward, backward or optimization."""
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('raw',type=Path)
    p.add_argument('baseline',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    original=json.loads((a.raw/'results.json').read_text())
    paired=json.loads((a.raw.parents[1]/'analysis/summary.json').read_text())
    rows=[]
    for target in [4,5,199,200,414,415]:
        r=next(x for x in original if x['step']==target and x['arm']=='L2_zero')
        folder=a.raw/f'step_{target:03d}_L2_zero'
        z=torch.load(folder/'final.pt',map_location='cpu',weights_only=False)
        init=torch.load(a.baseline/'best_models'/f'trained_1NN_{target-1}.pt',map_location='cpu',weights_only=False)
        w=torch.cat([v.flatten().double() for k,v in z.items() if 'weight' in k])
        delta=torch.cat([(v.double()-init[k].double()).flatten() for k,v in z.items() if 'weight' in k])
        large=w.abs()>100 # Descriptive cutoff, not a scientific acceptance gate.
        trace=json.loads((folder/'loss_trace.json').read_text())
        loge=np.array([t['logE'] for t in trace]);ratio=10**(loge-loge[0])
        d=next(x for x in paired if x['step']==target)
        row=dict(step=target,cycle=r['cycle'],substep=r['substep'],updates=r['updates'],stop=r['stop_reason'],
                 weight_coordinate_count=len(w),large_weight_count=int(large.sum()),
                 large_weight_negative_fraction=float((w[large]<0).double().mean()),
                 large_weight_share_squares=float(w[large].square().sum()/w.square().sum()),
                 weight_norm=float(w.norm()),max_abs_net_weight_drift=float(delta.abs().max()),
                 max_coordinate_net_drift_per_update=float(delta.abs().max()/r['updates']),
                 uv_output_weight_max_drift=float((z['output_layer.weight'][:2].double()-init['output_layer.weight'][:2].double()).abs().max()),
                 damage_output_weight_max_drift=float((z['output_layer.weight'][2].double()-init['output_layer.weight'][2].double()).abs().max()),
                 initial_nonzero_opposite_fraction=r['initial']['nonzero_opposite_fraction'],
                 initial_zero_fraction=r['initial']['physical_zero_fraction'],
                 initial_total_sign_change_fraction=r['initial']['sign_change_fraction'],
                 final_vs_initial_energy_ratio=float(10**(r['final']['logE']-r['initial']['logE'])),
                 max_vs_initial_energy_ratio=float(max(ratio.max(),10**(r['final']['logE']-r['initial']['logE']))),
                 damage_diff_rms=d['d_diff_rms'])
        for n in [361,658,1292]:
            if len(ratio)>n:
                row[f'energy_ratio_after_{n}_updates']=float(ratio[n])
            elif len(ratio)==n:
                row[f'energy_ratio_after_{n}_updates']=row['final_vs_initial_energy_ratio']
        rows.append(row)
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (a.output/'mechanism_metrics.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');writer.writeheader();writer.writerows(rows)
    (a.output/'mechanism_metrics.json').write_text(json.dumps(rows,indent=2)+'\n')
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained',sharey=True)
    for ax,step in zip(axes,[5,200,415]):
        for arm,label,color in [('L2_1e-5','L2 = 1e-5','#0072B2'),('L2_zero','L2 = 0','#D55E00')]:
            trace=json.loads((a.raw/f'step_{step:03d}_{arm}'/'loss_trace.json').read_text())
            receipt=next(r for r in original if r['step']==step and r['arm']==arm)
            y=np.array([t['logE'] for t in trace]);y-=y[0]
            final=receipt['final']['logE']-receipt['initial']['logE']
            ax.plot(np.arange(len(y)+1),np.r_[y,final],label=label,c=color,lw=.9,alpha=.9)
            ax.plot(len(y),final,'o',color=color,ms=4)
        ax.axhline(0,c='grey',lw=.7);ax.grid(alpha=.2)
        ax.set_title(f'c{(step-1)//5+1} unloaded');ax.set_xlabel('completed RPROP updates')
        ax.legend(fontsize=8)
    axes[0].set_ylabel('log10(common energy / initial common energy)')
    fig.suptitle('S04-E035 · all preselected unloaded states · existing traces\n'
                 'Endpoints marked; c1/c40 zero-L2 arms capped at 240s, c83 early stopped',fontsize=11)
    fig.savefig(a.output/'unloading_energy_paths.png',dpi=180);plt.close(fig)
    toy=dict(scope='analytic constant-sign bound only; NOT a PIDL execution',
             initial_step=1e-5,eta_plus=1.2,max_step=50,
             first_update_reaching_max=1+math.ceil(math.log(50/1e-5)/math.log(1.2)),
             conditions='nonzero same-sign gradients; no product underflow or parameter rounding effects')
    (a.output/'rprop_scale_arithmetic.json').write_text(json.dumps(toy,indent=2)+'\n')
    print(json.dumps(rows,indent=2))


if __name__=='__main__':
    main()
