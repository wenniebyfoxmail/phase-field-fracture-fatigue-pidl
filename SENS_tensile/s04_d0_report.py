"""Read scored D0 outputs only; no refit or selection."""
import argparse
import csv
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np
from scipy.io import loadmat


def report(root, out):
    run = json.loads((out/'receipt.json').read_text())
    guard = json.loads((out.parent/(out.name+'_fit_guard_receipt.json')).read_text())
    assert run['status'] == guard['status'] == 'COMPLETED'
    assert run['run_id'] == guard['run_id'] == 'S04-E016-D0-R002'
    assert run['code_commit'] == guard['code_commit'] == os.environ['D0_COMMIT']
    assert guard['output'] == str(out.resolve()) and guard['children'][0]['exit_code'] == 0
    assert guard['children'][0]['pid'] == run['pid']
    # Stage-fit admission only; final pipeline guard is written after plotting.
    rows = list(csv.DictReader((out/'percycle.csv').open()))
    assert len(rows) == 357*3 and all(np.isfinite(float(r[k])) for r in rows for k in
        ('B0_transformed_mse', 'B1_transformed_mse', 'B0_physical_mse', 'B1_physical_mse'))
    summary = []
    keys = sorted({r['holdout'] for r in rows})
    fields = ('damage', 'alpha_bar', 'psi_raw_direct')
    for key in keys:
        for field in fields:
            subset = [r for r in rows if r['holdout'] == key and r['field'] == field]
            for stratum in ('all', '0', '1', '2'):
                group = [r for r in subset if stratum == 'all' or r['stratum'] == stratum]
                w = np.array([float(r['cycle_weight']) for r in group]); w /= w.sum()
                record = dict(holdout=key, field=field, stratum=stratum)
                for scale in ('transformed', 'physical'):
                    for arm in ('B0', 'B1'):
                        record[arm+'_'+scale+'_rmse'] = float(np.sqrt(sum(
                            wi*float(r[arm+'_'+scale+'_mse']) for wi, r in zip(w, group))))
                    record[scale+'_ratio'] = record['B1_'+scale+'_rmse']/record['B0_'+scale+'_rmse']
                record['mean_bound_area'] = float(sum(wi*float(r['bound_violation_area']) for wi, r in zip(w, group)))
                record['maximum_bound_area'] = max(float(r['bound_violation_area']) for r in group)
                summary.append(record)
    with (out/'summary.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0])); writer.writeheader(); writer.writerows(summary)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    colors = ['#0072B2', '#D55E00', '#009E73']
    for ax, scale in zip(axes, ('transformed', 'physical')):
        for field, color in zip(fields, colors):
            values = [next(r[scale+'_ratio'] for r in summary if r['holdout'] == k and
                           r['field'] == field and r['stratum'] == 'all') for k in keys]
            ax.plot(range(4), values, '-o', label=field, color=color, linewidth=1.4)
        ax.axhline(1, color='gray', linestyle='--', label='B0 = 1')
        ax.set_xticks(range(4), keys); ax.set_ylabel('B1 / B0 balanced RMSE (lower better)')
        ax.set_title(scale+' scale'); ax.set_yscale('log'); ax.legend(fontsize=8)
    fig.suptitle('S04-E016-D0-R002 | whole-Umax development holdouts | synthetic s4 horizon 0')
    fig.savefig(out/'B0_B1_holdouts.png', dpi=180); plt.close(fig)
    model = json.loads((out/'models.json').read_text())['outer_u0115']
    with np.load(out/'u0115_C20.npz') as p:
        ids = p['ids']; data = [p[k] for k in ('fem', 'pin', 'B1')]
    lock = json.loads((root/'docs/research/S04/S04-E016/paired_s4_lock_candidate_20261013.json').read_text())
    fempath = next(t['fem_path'] for t in lock['trajectories'] if t['id'] == 'u0115')
    mesh = loadmat(root/fempath, variable_names=['coordinates', 'cells'])
    render_fields(mesh, ids, data, model['scales'], out/'u0115_C20_fields.png',
                  'Fixed heldout U0.115 C20 / s4 | native Q4 P0 | display asinh only; no clipping')
    assert sum(f.stat().st_size for f in out.rglob('*') if f.is_file()) < 100*1024**2
    print(json.dumps([r for r in summary if r['stratum'] == 'all'], indent=2))


def render_fields(mesh, ids, data, scales, destination, title):
    """Same twelve native-Q4 panels for production and synthetic-only memory QA."""
    fields = ('damage', 'alpha_bar', 'psi_raw_direct')
    polygons = mesh['coordinates'][mesh['cells'].astype(int)[ids]-1]
    fig, axes = plt.subplots(3, 4, figsize=(13, 9), constrained_layout=True)
    for j, field in enumerate(fields):
        scale = 1. if j == 0 else scales[j-1]
        visible = [np.arcsinh(v[:, j]/scale) for v in data]
        limit = max(float(np.abs(v).max()) for v in visible)
        residual = np.arcsinh((data[2][:, j]-data[0][:, j])/scale)
        rlimit = max(float(np.abs(residual).max()), 1e-12)
        for i, v in enumerate([*visible, residual]):
            ax = axes[j, i]; lim = rlimit if i == 3 else limit
            poly = PolyCollection(polygons, array=v, cmap='RdBu_r', clim=(-lim, lim), linewidth=0, rasterized=True)
            ax.add_collection(poly)
            ax.set_xlim(float(mesh['coordinates'][:, 0].min()), float(mesh['coordinates'][:, 0].max()))
            ax.set_ylim(float(mesh['coordinates'][:, 1].min()), float(mesh['coordinates'][:, 1].max()))
            ax.set_aspect('equal'); ax.set_xlabel('x (native frame)'); ax.set_ylabel('y (native frame)')
            ax.set_title((['FEM', 'PIN / B0', 'B1', 'B1 - FEM'][i])+' | '+field, fontsize=9)
            fig.colorbar(poly, ax=ax, shrink=.75, label='asinh(value / training PIN scale)' if j else 'asinh(d)')
    fig.suptitle(title)
    fig.savefig(destination, dpi=160); plt.close(fig)

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', required=True); a = p.parse_args()
    report(Path(__file__).resolve().parents[1], Path(a.out))
