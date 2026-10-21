"""Plot saved coupled candidates with unchanged thresholds; no solver calls."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    a = p.parse_args()
    r = a.run
    verification = json.loads((r/'analysis/reference_verification.json').read_text())
    with (r/'retrieved/fem/coupling.csv').open() as f:
        rows = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(f)]
    assert rows
    step = 24 if verification['complete_valid_reference'] else verification['accepted_prefix']+1
    selected = [v for v in rows if int(v['step']) == step]
    assert selected
    assert all(np.isfinite(list(v.values())).all() for v in selected)
    with (r/'analysis/selected_coupling.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(selected[0])); w.writeheader(); w.writerows(selected)
    x = [int(v['stagger']) for v in selected]
    ru, pf = [[v[key] for v in selected] for key in ['res_u', 'res_pf']]
    fig, axes = plt.subplots(1, 2, figsize=(9.7, 3.7), constrained_layout=True)
    axes[0].semilogy(x, ru, color='#0072B2', lw=1.4, label='Fresh mechanics norm')
    axes[0].semilogy(x, pf, color='#009E73', lw=1.4, label='Fresh PF norm')
    axes[0].axhline(1e-4, ls='--', color='#444444', lw=1.2, label='Coupled sum limit 1e-4')
    axes[0].set(xlabel='Outer stagger iteration', ylabel='Residual norm (normalized)', title='Same candidate, refreshed driver/history fixed')
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].plot(x, [v['alpha_max'] for v in selected], color='#D55E00', lw=1.4)
    axes[1].axhline(1.005, ls='--', color='#444444', lw=1.2, label='Final-state nodal upper limit')
    axes[1].set(xlabel='Outer stagger iteration', ylabel='Maximum nodal phase field alpha', title='Candidate range; no clipping')
    axes[1].legend(frameon=False, fontsize=8)
    for ax in axes: ax.grid(alpha=.15)
    U = selected[0]['U']
    status = 'accepted final load' if verification['complete_valid_reference'] else 'unaccepted next load'
    fig.suptitle(f'{r.name}: U={U:.2f}, {status}; valid prefix {verification["accepted_prefix"]}/24', fontsize=11)
    out = r/'analysis/figures'; out.mkdir(exist_ok=True)
    for ext in ['png', 'pdf']: fig.savefig(out/f'coupling_candidates.{ext}', dpi=180)
    plt.close(fig)
    (out/'coupling_candidates.md').write_text(f'''# How to read coupled candidates

## Question and data provenance

How do coupled stationarity and candidate range evolve at the last attempted load? Source: {r}/retrieved/fem/coupling.csv; upstream ../reference_verification.json; exact selected rows ../selected_coupling.csv. Script scripts/shear/plot_manav_coupling.py. No assembly, solver, interpolation, clipping or fitting.

## How to read

The selected load is deterministically step{step}/U={U:.17g}, the first unaccepted load after the accepted prefix, or the final24th load if the full reference succeeds. Every completely exported same-candidate row is shown, outer iteration1..{x[-1]}. Left: mechanics (blue) and phase-field (green) free-DOF norms from fresh assembly on the same(u,alpha), refreshed driver and fixed old history. The dashed1e-4 line is the limit on their SUM; being individually below it is not enough. A curve above it is sufficient to reject the sum. Right: maximum unmodified nodal alpha, original final-state limit1.005. Interim candidate overshoot is not itself an accepted-state failure; final acceptance still needs every declared check.

## Interpretation and limitations

Valid prefix={verification['accepted_prefix']}/24; full reference={verification['complete_valid_reference']}; last completely exported coupled sum={ru[-1]+pf[-1]:.12g}, last candidate alpha_max={selected[-1]['alpha_max']:.12g}. Missing/partly buffered final iterations are not reconstructed. These are scalar diagnostics, not per-iteration field certificates. A slow/nonconverged coupled sequence does not identify whether inner tolerance, coupling instability or finite-penalty/discretization is causal. A budget stop does not prove a physical model failure. No PIDL agreement or45degree result follows from this figure.
''')
    print(json.dumps(dict(selected_step=step, U=U, complete_rows=len(selected), last_coupled_sum=ru[-1]+pf[-1], last_alpha_max=selected[-1]['alpha_max'])))


if __name__ == '__main__':
    main()
