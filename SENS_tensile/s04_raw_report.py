"""45b8d32 report: reads saved outputs; never fits/selects or opens confirmation."""
import argparse
import csv
import json
import os
from pathlib import Path

import numpy as np


def render(mesh, ids, arrays, destination, title):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    polygons = mesh['coordinates'][mesh['cells'].astype(int)[ids]-1]
    fields = [v[:, 2] for v in arrays]
    limit = max(float(v.max()) for v in fields)
    error = fields[2]-fields[0]; elimit = max(float(np.abs(error).max()), 1e-12)
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.6), constrained_layout=True)
    for j, values in enumerate([*fields, error]):
        ax = axes[j]
        bounds = (-elimit, elimit) if j == 3 else (0., max(limit, 1e-12))
        poly = PolyCollection(polygons, array=values, cmap='RdBu_r' if j == 3 else 'viridis',
                              clim=bounds, linewidth=0, rasterized=True)
        ax.add_collection(poly); ax.autoscale_view(); ax.set_aspect('equal')
        ax.set_title(('FEM', 'V0', 'V1', 'V1 - FEM')[j]); ax.set_xlabel('x'); ax.set_ylabel('y')
        fig.colorbar(poly, ax=ax, shrink=.7, label='raw archive units (linear)')
    fig.suptitle(title); fig.savefig(destination, dpi=150); plt.close(fig)


def report(out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from scipy.io import loadmat
    from s04_raw import ROOT, LOCK, authorization, require
    receipt = json.loads((out/'receipt.json').read_text())
    stage = json.loads((out.parent/(out.name+'_fit_guard_receipt.json')).read_text())
    require(receipt['status'] == stage['status'] == 'COMPLETED', 'stage completion')
    require(receipt['code_commit'] == stage['code_commit'] == os.environ['RAW_CODE_COMMIT'] and
            receipt['run_id'] == stage['run_id'] == os.environ['RAW_RUN_ID'] and
            stage['output'] == str(out.resolve()) and stage['children'][0]['pid'] == receipt['pid'] and
            stage['children'][0]['exit_code'] == 0, 'bound fit guard identity')
    synthetic = receipt['mode'] == 'synthetic_engineering'
    if synthetic:
        with np.load(out/'synthetic_mesh.npz') as m:
            mesh = {k: m[k] for k in ('coordinates', 'cells')}
    else:
        authorization(Path(os.environ['RAW_AUTHORIZATION']), out)
        lock = json.loads(LOCK.read_text())
        path = next(t['fem_path'] for t in lock['trajectories'] if t['id'] == 'u0115')
        mesh = loadmat(ROOT/path, variable_names=['coordinates', 'cells'])
    d = json.loads((out/'decision.json').read_text()); folds = d['folds']
    prefix = 'SYNTHETIC ENGINEERING — NOT METHOD EVIDENCE' if synthetic else 'synthetic archive / development s4 horizon0'
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.7), constrained_layout=True)
    for ax, metric in zip(axes, ('R', 'G')):
        ax.plot(range(4), [f[metric] for f in folds], 'o-', label='V1 / V0 RMSE')
        ax.axhline(1., color='gray', linestyle='--', label='V0=1')
        ax.set_xticks(range(4), [f['holdout']+('*' if f['fallback'] else '') for f in folds])
        ax.set_ylabel('physical raw RMSE ratio, lower better')
        ax.set_title('all-cycle balanced R' if metric == 'R' else 'C1–20 G'); ax.legend(fontsize=8)
    fig.suptitle(prefix+'\n'+receipt['run_id']+' | * = preselected fallback')
    fig.savefig(out/'V0_V1_holdouts.png', dpi=160); plt.close(fig)
    with np.load(out/'u0115_C20.npz') as p:
        render(mesh, p['ids'], [p[k] for k in ('fem', 'V0', 'V1')],
               out/'u0115_C20_raw.png', prefix+' | fixed U0.115 C20 raw, full native support')
    with (out/'folds.csv').open('x') as f:
        w = csv.DictWriter(f, fieldnames=list(folds[0])); w.writeheader(); w.writerows(folds)
    (out/'README_analysis.md').write_text(
        '# '+prefix+'\n\nQuestion: physical raw V1 versus identically admissible V0; horizon0.\n'
        'Source: percycle.csv, selection.json, models.json and fixed C20 snapshot.\n'
        'Read holdout R/G first, then fixed C20 FEM/V0/V1/error fields.\n'
        'Damage/history are identical between arms; only raw is learned.\n'
        'All four folds remain visible, including fallback.\n'
        'Numerical output status: '+d['status']+'.\n'
        'Engineering synthetic output is NOT a method result. Real-data output is\n'
        'development archive imitation only; not teacher/physics/confirmation proof.\n'
        'Next: independent review; no automatic refit, new arm or NN.\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    report(p.parse_args().out)
