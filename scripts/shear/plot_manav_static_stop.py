"""Plot only verified saved fields and recorded trial residuals; no solver calls."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np
from scipy.io import loadmat


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    a = p.parse_args()
    run = a.run
    fem = run/'retrieved/fem'
    analysis = run/'analysis'
    out = analysis/'figures'; out.mkdir(exist_ok=True)
    verification = json.loads((analysis/'reference_verification.json').read_text())
    metrics = json.loads((analysis/'decision_metrics.json').read_text())
    n = verification['accepted_prefix']
    with (fem/'newton_trace.csv').open() as f:
        trace = list(csv.DictReader(f))
    failed = metrics['failed']
    selected = [r for r in trace if int(r['step']) == failed['step'] and int(r['stagger']) == failed['stag'] and r['field'] == 'phase']
    origins = [r for r in selected if r['event'] == 'pre']
    last = max(int(r['iteration']) for r in origins)
    trials = [r for r in selected if r['event'] == 'trial' and int(r['iteration']) == last]
    ratio = [float(r['trial_residual'])/float(r['residual'])-1 for r in trials]
    assert min(ratio) > 0
    with (analysis/'failure_trials.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(trials[0])+['relative_residual_increase']); w.writeheader()
        for r, q in zip(trials, ratio): w.writerow(dict(r, relative_residual_increase=q))
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7), constrained_layout=True)
    axes[0].semilogy([int(r['iteration']) for r in origins], [float(r['residual']) for r in origins], color='#0072B2', lw=1.5)
    axes[0].axhline(1e-6, color='#D55E00', ls='--', label='Inner tolerance 1e-6')
    axes[0].set(xlabel='PF Newton iteration (current returned point)', ylabel='Free-DOF PF residual norm', title='(a) PF subproblem at U=0.24')
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].semilogy([int(r['trial']) for r in trials], ratio, 'o-', color='#D55E00', lw=1.5, ms=4)
    axes[1].set(xlabel='Backtracking index j (step = 2^-j)', ylabel='Trial residual / origin residual - 1', title=f'(b) All 13 trials increase residual (iteration {last})')
    for ax in axes: ax.grid(alpha=.17)
    fig.suptitle('R009: loaded PF line-search stop; no coupled certificate', fontsize=11)
    for ext in ['png', 'pdf']: fig.savefig(out/f'pf_line_search_stop.{ext}', dpi=180)
    plt.close(fig)
    origin = float(trials[0]['residual'])
    (out/'pf_line_search_stop.md').write_text(f'''# How to read PF line-search stop

## Data provenance

Question: why was the U=.24 candidate rejected? Source: {fem}/newton_trace.csv, step8/stagger1/phase; analysis/failure_trials.csv. Script: scripts/shear/plot_manav_static_stop.py. Only recorded residuals are used, no assembly or refit.
Panel(a): residual at each Newton origin, log y; dashed line is the unchanged1e-6 inner tolerance. Panel(b): relative residual increase of all13 trials in the final iteration, log y, step=2^-j. Every value is positive, hence none reduces the residual, a necessary condition for this residual Armijo rule. The exact Armijo sufficient-decrease curve is not reconstructed because the slope was not exported.
Final origin residual={origin:.17g}; smallest-step trial={float(trials[-1]['trial_residual']):.17g}, relative increase={ratio[-1]:.9g}. Limitations: no qualified coupled pair was reached. This shows the added acceptance-rule failure, not native Newton nonconvergence or a physical failure. Missing K/direction/active sets prevent a proven causal explanation.
Related: ../reference_verification.json, ../decision_metrics.json, ../failure_trials.csv.
''')
    mesh = loadmat(fem/'mesh.mat'); state = loadmat(fem/f'state_{n:03d}.mat')
    nodes = mesh['nodes'][:, :2]; quads = mesh['quads'].astype(int)-1
    damage = state['p_field'].ravel(); values = damage[quads].mean(1)
    fig, ax = plt.subplots(figsize=(4.9, 4.5), constrained_layout=True)
    art = PolyCollection(nodes[quads], array=values, cmap='viridis', edgecolors='none', linewidths=0, antialiased=False, rasterized=True)
    art.set_clim(-.005, 1.005); ax.add_collection(art)
    ax.set(xlim=(-.5, .5), ylim=(-.5, .5), aspect='equal', xlabel='x (normalized)', ylabel='y (normalized)', title=f'R009 FEM: last accepted U={metrics["last_U"]:.2f}\n{n}/24 loaded states; no PIDL result')
    fig.colorbar(art, ax=ax, label='Phase field alpha (Q4 nodal mean)', shrink=.85)
    for ext in ['png', 'pdf']: fig.savefig(out/f'last_accepted_damage.{ext}', dpi=200)
    plt.close(fig)
    (out/'last_accepted_damage.md').write_text(f'''# How to read last accepted damage field

## Data provenance

Question: what is the phase field at the highest accepted displacement? Source: {fem}/mesh.mat and state_{n:03d}.mat; verification: ../reference_verification.json; script: scripts/shear/plot_manav_static_stop.py.
One panel on the full normalized1x1 undeformed domain. Each Q4 face uses arithmetic mean of its4nodal values, a display reduction rather than a new pointwise solve or an exact general-quadrilateral area integral. Viridis range[-.005,1.005] contains the unmodified raw nodal range[{damage.min():.12g},{damage.max():.12g}]. No clipping, smoothing, mask or interpolation. The pre-existing crack remains present; this panel alone does not isolate new growth.
Selected by highest accepted U={metrics['last_U']}, independently of appearance. All7loaded states have saved-force norms and history/BC/damage checks verified. Limitations: the reference stops beforeU=.4 and no PIDL result exists; the image cannot support paired accuracy, full paper reproduction, or physical validation.
''')
    print(json.dumps(dict(figures=str(out), accepted=n, U=metrics['last_U'], final_PF_iteration=last)))


if __name__ == '__main__':
    main()
