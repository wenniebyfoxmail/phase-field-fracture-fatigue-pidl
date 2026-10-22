"""Saved-output three-arm E038 comparison. Never performs model forward/optimization."""
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

KEYS = ('E_el', 'E_d', 'E_irr')
LABELS = ('L2=1e-5, cap50', 'L2=0, cap50', 'L2=0, cap0.001')
COLORS = ('#0072B2', '#D55E00', '#009E73')

def read(p):
    return json.loads(p.read_text())

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('old', type=Path); p.add_argument('new', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
    mesh = np.load(a.new/'mesh.npz')
    oldmesh = np.load(a.old/'mesh.npz')
    assert all(np.array_equal(mesh[k], oldmesh[k]) for k in mesh.files)
    tri = Triangulation(*mesh['xy'].T, mesh['triangles'])
    rows, data = [], []
    for step in (5, 200):
        folders = [a.old/f'step_{step:03d}_{arm}' for arm in ('L2_1e-5', 'L2_zero')]
        folders += [a.new/f'step_{step:03d}_L2_zero_cap1e-3']
        receipts = [read(f/'receipt.json') for f in folders]
        initial = [np.load(f/'initial.npz') for f in folders]
        finals = [np.load(f/'final.npz') for f in folders]
        for f in initial[1:]:
            assert all(np.array_equal(initial[0][k], f[k]) for k in initial[0].files)
        for f in finals:
            assert all(np.isfinite(f[k]).all() for k in f.files)
            assert np.array_equal(f['hist_alpha'], initial[0]['hist_alpha'])
        traces = [read(f/'loss_trace.json') for f in folders]
        opt = read(a.new/f'optimizer_trace_step_{step:03d}.json')
        assert opt['updates'] == receipts[2]['updates']
        common_n = min(r['updates'] for r in receipts)
        equal_prefix = 0
        for old_row, new_row in zip(traces[1], traces[2]):
            if old_row != new_row:
                break
            equal_prefix += 1
        control_e = sum(receipts[0]['final'][k] for k in KEYS)
        hc = np.maximum(finals[0]['d'], finals[0]['hist_alpha'])
        for idx, (folder, r, f, trace) in enumerate(zip(folders, receipts, finals, traces)):
            assert len(trace) == r['updates']
            ck = torch.load(folder/'final.pt', map_location='cpu', weights_only=False)
            ws = [v.double() for k,v in ck.items() if 'weight' in k]
            norm = float(np.sqrt(sum(float(v.square().sum()) for v in ws)))
            maxabs = max(float(v.abs().max()) for v in ws)
            energy = sum(r['final'][k] for k in KEYS)
            common_e = energy if common_n == r['updates'] else 10**trace[common_n]['logE']
            diff = f['d'].astype(float) - finals[0]['d'].astype(float)
            history = np.maximum(f['d'], f['hist_alpha'])
            row = dict(step=step,cycle=r['cycle'],arm=LABELS[idx],updates=r['updates'],
                seconds=r['optimization_seconds'],stop=r['stop_reason'],
                weight_norm=norm,weight_maxabs=maxabs,energy=energy,
                initial_weight_norm=float(np.sqrt(r['initial']['canonical_L2']/1e-5)),
                weight_growth_percent=100*(norm/np.sqrt(r['initial']['canonical_L2']/1e-5)-1),
                max_logged_energy_vs_initial=max(10**q['logE'] for q in trace)/sum(r['initial'][k] for k in KEYS),
                energy_vs_control_percent=100*(energy/control_e-1),
                energy_vs_initial=energy/sum(r['initial'][k] for k in KEYS),
                d_diff_control_rms=float(np.sqrt(np.mean(diff**2))),
                d_diff_control_maxabs=float(np.abs(diff).max()),
                new_history_gt0p5_node_fraction=float(((history>.5)&(hc<=.5)).mean()),
                common_updates=common_n,energy_at_common_updates=common_e,
                **{k:r['final'][k] for k in ('d_min','d_max','gp_retreat_max','grad_logE_l2')})
            rows.append(row)
            if idx == 2:
                assert np.isclose(norm,opt['final']['weight_norm'],rtol=1e-5)
                assert maxabs == opt['final']['weight_abs_max']
                assert opt['final']['step_max'] <= .001000001
                row.update(identical_zeroL2_initial_trace_rows=equal_prefix,actual_step_max=opt['final']['step_max'],
                           actual_cap_fraction=opt['final']['step_at_cap_fraction'])
        data.append((step,receipts,finals,traces,opt))
    (a.output/'metrics.json').write_text(json.dumps(rows,indent=2)+'\n')
    with (a.output/'metrics.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        writer.writeheader();writer.writerows(rows)
    fig,axes=plt.subplots(2,4,figsize=(14,7),layout='constrained')
    lo=min(float(f['d'].min()) for _,_,fs,_,_ in data for f in fs)
    hi=max(float(f['d'].max()) for _,_,fs,_,_ in data for f in fs)
    err=max(float(np.abs(fs[2]['d']-fs[0]['d']).max()) for _,_,fs,_,_ in data)
    for axs,(step,rs,fs,_,_) in zip(axes,data):
        ds=[f['d'].reshape(-1) for f in fs]; ds += [ds[2]-ds[0]]
        for i,(ax,d) in enumerate(zip(axs,ds)):
            im=ax.tripcolor(tri,d,shading='gouraud',cmap='viridis' if i<3 else 'RdBu_r',
                vmin=lo if i<3 else -err,vmax=hi if i<3 else err,rasterized=True)
            ax.set_aspect('equal');ax.set_xlabel('x');ax.set_ylabel('y')
            ax.set_title(f"c{rs[0]['cycle']} unload: "+(LABELS[i] if i<3 else 'small cap - control'),fontsize=10)
            fig.colorbar(im,ax=ax,shrink=.75,label='damage d' if i<3 else 'damage difference')
    fig.suptitle('S04-E038: all two preselected unloading states, shared initial fields/history\n'
                 'Synthetic, one seed; finite local solves, no trajectory rollout',fontsize=12)
    fig.savefig(a.output/'damage_cap_comparison.png',dpi=170);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(14,7),layout='constrained')
    for axs,(step,rs,fs,traces,opt) in zip(axes,data):
        einit=sum(rs[0]['initial'][k] for k in KEYS)
        for r,t,label,color in zip(rs,traces,LABELS,COLORS):
            n=r['updates']; x=np.arange(n+1)
            y=[10**q['logE']/einit for q in t]+[sum(r['final'][k] for k in KEYS)/einit]
            axs[0].plot(x,y,label=label,c=color,lw=.8)
        axs[0].axhline(1,c='gray',ls=':',lw=.8)
        axs[0].set_yscale('log')
        axs[0].set_ylabel('common physical energy / initial (log scale)');axs[0].legend(fontsize=8)
        rr=opt['rows']+[opt['final']]
        axs[1].plot([q['update'] for q in rr],[q['weight_norm'] for q in rr],c=COLORS[2])
        axs[1].set_ylabel('weight norm (small cap only)')
        axs[2].plot([q['update'] for q in rr],[q['step_max'] for q in rr],c=COLORS[2])
        axs[2].set_ylabel('actual maximum coordinate step size')
        axs[2].set_ylim(0,.0011)
        for ax in axs:
            ax.set_xlabel('completed RPROP updates');ax.grid(alpha=.2)
        axs[0].set_title(f"c{rs[0]['cycle']} unload, U=0")
    fig.suptitle('E038 measured optimization paths; old max50 arms from E035\n'
                 'Different stopping times retained; physical energy excludes network L2',fontsize=12)
    fig.savefig(a.output/'optimization_cap_comparison.png',dpi=170);plt.close(fig)
    for name in ('damage_cap_comparison','optimization_cap_comparison'):
        (a.output/f'{name}.md').write_text(f'# {name}\n\nSource: E035 original raw outputs and E038 new raw outputs.\n'
            'All preselected c1/c40 unloaded local solves, one seed, shared mesh/history.\n'
            'No rollout, physical validation or convergence claim. Reproduce with analyze_s04_e038_rprop_cap.py.\n')
    print(json.dumps(rows,indent=2))

if __name__=='__main__':
    main()
