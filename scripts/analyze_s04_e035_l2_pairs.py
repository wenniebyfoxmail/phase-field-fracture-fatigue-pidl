"""Analyze exact S04-E035 local matched solve outputs; no optimization."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation


def main():
    p = argparse.ArgumentParser()
    p.add_argument('raw', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--baseline', type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    results = json.loads((a.raw / 'results.json').read_text())
    rows = []
    param_rows = []
    fields = []
    for step in sorted({r['step'] for r in results}):
        group = {r['arm']: r for r in results if r['step'] == step}
        if len(group) != 2:
            continue
        control, zero = group['L2_1e-5'], group['L2_zero']
        folders = [a.raw / f'step_{step:03d}_{name}' for name in ('L2_1e-5', 'L2_zero')]
        finals = [np.load(f / 'final.npz') for f in folders]
        initials = [np.load(f / 'initial.npz') for f in folders]
        assert all(np.array_equal(initials[0][key], initials[1][key])
                   for key in initials[0].files), 'Initial pair mismatch'
        assert np.array_equal(finals[0]['hist_alpha'], finals[1]['hist_alpha'])
        row = dict(step=step, cycle=control['cycle'], substep=control['substep'],
                   load=control['load'], control_updates=control['updates'],
                   zero_updates=zero['updates'], control_stop=control['stop_reason'],
                   zero_stop=zero['stop_reason'],
                   control_seconds=control['optimization_seconds'],
                   zero_seconds=zero['optimization_seconds'])
        for key in ('u', 'v', 'd', 'psi_active', 'trial_histfat', 'trial_f'):
            x, y = (f[key].astype(np.float64) for f in finals)
            delta = y-x
            row.update({f'{key}_diff_rms': float(np.sqrt(np.mean(delta**2))),
                        f'{key}_diff_maxabs': float(np.max(np.abs(delta))),
                        f'{key}_diff_relL2': float(np.linalg.norm(delta)/max(np.linalg.norm(x),1e-30))})
        # Deterministic standard damage-history commit, derived offline only.
        committed=[np.maximum(f['hist_alpha'].astype(np.float64),f['d'].astype(np.float64)) for f in finals]
        hist_delta=committed[1]-committed[0]
        row['trial_histalpha_diff_rms']=float(np.sqrt(np.mean(hist_delta**2)))
        row['trial_histalpha_diff_maxabs']=float(np.max(np.abs(hist_delta)))
        row['zero_only_history_gt0p5_node_fraction']=float(np.mean((committed[1]>.5)&(committed[0]<=.5)))
        for label, r in (('control', control), ('zero', zero)):
            for key, val in r['final'].items():
                row[f'{label}_{key}'] = val
        row['energy_change_percent'] = 100*(
            sum(zero['final'][k] for k in ('E_el','E_d','E_irr')) /
            sum(control['final'][k] for k in ('E_el','E_d','E_irr'))-1)
        checkpoints=[torch.load(f/'final.pt',map_location='cpu',weights_only=False) for f in folders]
        for prefix,checkpoint in zip(('control','zero'),checkpoints):
            square_sum=sum(float(v.double().square().sum()) for k,v in checkpoint.items() if 'weight' in k)
            row[f'{prefix}_weight_norm']=float(np.sqrt(square_sum))
            row[f'{prefix}_weight_maxabs']=max(float(v.abs().max()) for k,v in checkpoint.items() if 'weight' in k)
            for name,v in checkpoint.items():
                param_rows.append(dict(step=step,arm=prefix,parameter=name,
                                       norm=float(v.double().norm()),maxabs=float(v.abs().max())))
        row['weight_norm_ratio']=row['zero_weight_norm']/row['control_weight_norm']
        if a.baseline:
            best=a.baseline/'best_models'
            archived=np.load(best/'energy_gradient_terms_vs_cycle.npy')
            reference=archived[archived[:,0]==step][0,1:4]
            replay=np.array([control['final'][k] for k in ('E_el','E_d','E_irr')])
            row['control_replay_energy_max_relerr']=float(np.max(
                np.abs(replay-reference)/np.maximum(np.abs(reference),1e-30)))
            old=torch.load(best/f'trained_1NN_{step}.pt',map_location='cpu',weights_only=False)
            new=checkpoints[0]
            row['control_replay_weights_maxabs']=max(
                float((new[k]-old[k]).abs().max()) for k in old)
            row['control_replay_update_diff']=control['updates']-len(
                np.load(best/f'trainLoss_1NN_{step}.npy'))
        rows.append(row)
        fields.append((row, [f['d'].copy() for f in finals], folders))
    assert rows, 'No complete matched pair'
    with (a.output / 'paired_metrics.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    with (a.output / 'parameter_scales.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(param_rows[0]))
        writer.writeheader();writer.writerows(param_rows)
    (a.output / 'summary.json').write_text(json.dumps(rows, indent=2)+'\n')
    mesh = np.load(a.raw / 'mesh.npz')
    tri = Triangulation(mesh['xy'][:,0], mesh['xy'][:,1], mesh['triangles'])
    dmin = min(float(d.min()) for _,ds,_ in fields for d in ds)
    dmax = max(float(d.max()) for _,ds,_ in fields for d in ds)
    errmax = max(float(np.abs(ds[1]-ds[0]).max()) for _,ds,_ in fields)
    fig, axes = plt.subplots(len(rows), 3, figsize=(10,3.1*len(rows)), squeeze=False,
                             layout='constrained')
    for axs,(row,ds,_) in zip(axes,fields):
        for j,d in enumerate([ds[0], ds[1], ds[1]-ds[0]]):
            im=axs[j].tripcolor(tri,d,shading='gouraud',cmap='viridis' if j<2 else 'RdBu_r',
                               vmin=dmin if j<2 else -errmax, vmax=dmax if j<2 else errmax,
                               rasterized=True)
            axs[j].set_aspect('equal');axs[j].set_xlabel('x (normalized)')
            axs[j].set_ylabel('y (normalized)')
            axs[j].set_title(f"c{row['cycle']} {'peak' if row['substep']==4 else 'unload'} · "+
                             ['L2 = 1e-5','L2 = 0','zero − control'][j],fontsize=10)
            fig.colorbar(im,ax=axs[j],shrink=.8,label='damage d' if j<2 else 'damage difference')
    fig.suptitle('S04-E035 · synthetic · one seed · frozen-history local solves\n'
                 f'All {len(rows)} retrieved matched states; common scales; endpoints are finite solves',fontsize=13)
    fig.savefig(a.output / 'damage_pairs.png',dpi=170);plt.close(fig)
    # Fixed example rule: lowest preselected raw step (c1 peak), irrespective
    # of observed differences. Full six-state maps above remain authoritative.
    row,ds,_=fields[0]
    fig,axes=plt.subplots(1,3,figsize=(10.5,3.6),layout='constrained')
    limits=(min(float(d.min()) for d in ds),max(float(d.max()) for d in ds))
    de=float(np.abs(ds[1]-ds[0]).max())
    for j,d in enumerate((ds[0],ds[1],ds[1]-ds[0])):
        im=axes[j].tripcolor(tri,d,shading='gouraud',cmap='viridis' if j<2 else 'RdBu_r',
                            vmin=limits[0] if j<2 else -de,vmax=limits[1] if j<2 else de)
        axes[j].set_aspect('equal');axes[j].set_xlabel('x (normalized)');axes[j].set_ylabel('y (normalized)')
        axes[j].set_title(['L2 = 1e-5','L2 = 0','zero − control'][j])
        fig.colorbar(im,ax=axes[j],shrink=.85,label='damage d' if j<2 else 'damage difference')
    fig.suptitle(f"S04-E035 · fixed first state: c{row['cycle']} peak, step {row['step']}\n"
                 'Same preceding network and history · finite local solves',fontsize=12)
    fig.savefig(a.output/'damage_first_state.png',dpi=180);plt.close(fig)
    unloaded=[entry for entry in fields if entry[0]['substep']==5]
    if unloaded:
        fig,axes=plt.subplots(len(unloaded),3,figsize=(10.5,3.2*len(unloaded)),
                              layout='constrained',squeeze=False)
        lo=min(float(d.min()) for _,ds,_ in unloaded for d in ds)
        hi=max(float(d.max()) for _,ds,_ in unloaded for d in ds)
        de=max(float(np.abs(ds[1]-ds[0]).max()) for _,ds,_ in unloaded)
        for axs,(row,ds,_) in zip(axes,unloaded):
            stop='240s cap' if row['zero_stop']=='wall_cap' else 'early stop'
            titles=[f"c{row['cycle']} unloaded · L2 = 1e-5\n{row['control_updates']} updates",
                    f"L2 = 0 · {row['zero_updates']} updates\n{stop}", 'zero − control']
            for j,d in enumerate((ds[0],ds[1],ds[1]-ds[0])):
                im=axs[j].tripcolor(tri,d,shading='gouraud',cmap='viridis' if j<2 else 'RdBu_r',
                                   vmin=lo if j<2 else -de,vmax=hi if j<2 else de)
                axs[j].set_aspect('equal');axs[j].set_xlabel('x');axs[j].set_ylabel('y')
                axs[j].set_title(titles[j],fontsize=10)
                fig.colorbar(im,ax=axs[j],shrink=.8,label='damage d' if j<2 else 'damage difference')
        fig.suptitle('S04-E035 · all retrieved preselected unloaded states · synthetic, one seed\n'
                     'Same preceding network/history · finite endpoints; convergence not established',fontsize=12)
        fig.savefig(a.output/'damage_unloading_pairs.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(len(rows),2,figsize=(11,2.7*len(rows)),layout='constrained',squeeze=False)
    for axs,(row,_,folders) in zip(axes,fields):
        for folder,label,color in zip(folders,['L2 = 1e-5','L2 = 0'],['#0072B2','#D55E00']):
            loss=json.loads((folder/'loss_trace.json').read_text())
            grad=json.loads((folder/'gradient_trace.json').read_text())
            axs[0].plot([r['epoch'] for r in loss],[r['logE'] for r in loss],label=label,c=color,lw=1)
            axs[1].semilogy([r['update'] for r in grad],[r['grad_logE_l2'] for r in grad],
                            label=label,c=color,lw=1)
        for ax in axs:
            ax.set_xlabel('RPROP updates (preupdate sample)');ax.grid(alpha=.2);ax.legend(fontsize=8)
        axs[0].set_ylabel('common log10 energy')
        axs[1].set_ylabel('physical network gradient norm')
        axs[0].set_title(f"c{row['cycle']} {'peak' if row['substep']==4 else 'unload'} · step {row['step']}")
    fig.suptitle('S04-E035 · objective-independent comparison · fixed input histories\n'
                 'Stopping uses each original objective; physical gradients differentiated directly',fontsize=12)
    fig.savefig(a.output/'optimization_pairs.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    x=np.arange(len(rows));labels=[f"c{r['cycle']}\n{'peak' if r['substep']==4 else 'unload'}" for r in rows]
    axes[0].bar(x,[r['d_diff_rms'] for r in rows],color='#D55E00');axes[0].set_ylabel('damage difference RMS')
    for offset,prefix,label,color in [(-.17,'control','L2 = 1e-5','#0072B2'),(.17,'zero','L2 = 0','#D55E00')]:
        axes[1].bar(x+offset,[100*r[f'{prefix}_nonzero_opposite_fraction'] for r in rows],width=.32,label=label,color=color)
        axes[2].bar(x+offset,[r[f'{prefix}_gp_retreat_max'] for r in rows],width=.32,label=label,color=color)
    axes[1].set_ylabel('opposite nonzero signs (% of all coordinates)')
    axes[2].set_ylabel('maximum tri3 damage retreat')
    for ax in axes:
        ax.set_xticks(x,labels);ax.grid(axis='y',alpha=.2)
    axes[1].legend(fontsize=9);axes[2].legend(fontsize=9)
    fig.suptitle(f'S04-E035 · final local states · {len(rows)} correlated states, one trajectory',fontsize=12)
    fig.savefig(a.output/'decision_overview.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for offset,prefix,label,color in [(-.17,'control','L2 = 1e-5','#0072B2'),(.17,'zero','L2 = 0','#D55E00')]:
        axes[0].bar(x+offset,[r[f'{prefix}_weight_norm'] for r in rows],width=.32,label=label,color=color)
        axes[1].bar(x+offset,[r[f'{prefix}_weight_maxabs'] for r in rows],width=.32,label=label,color=color)
    axes[0].set_ylabel('Euclidean norm of regularized weights')
    axes[1].set_ylabel('maximum absolute weight')
    for ax in axes:
        ax.set_yscale('log');ax.set_xticks(x,labels);ax.grid(axis='y',alpha=.2);ax.legend(fontsize=9)
    fig.suptitle('S04-E035 · weight-scale response to L2 removal\n'
                 'Final parameter scales; not physical residuals or an added loss in the zero arm',fontsize=12)
    fig.savefig(a.output/'parameter_scales.png',dpi=180);plt.close(fig)
    print(json.dumps(rows,indent=2))


if __name__=='__main__':
    main()
