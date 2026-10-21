"""Saved-array diagnosis of native PF return timing; no assembly or fitting."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.io import loadmat


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    a = p.parse_args()
    r = a.run
    fem = r/'retrieved/fem'
    verification = json.loads((r/'analysis/reference_verification.json').read_text())
    assert not verification['complete_valid_reference']
    mesh = loadmat(fem/'mesh.mat', simplify_cells=True)
    s = loadmat(fem/'failed_state_007.mat', simplify_cells=True)
    last = s['native_last_completed']
    entered = s['native_last_entered']
    n = len(mesh['nodes'])
    crack = np.asarray(mesh['crack'], dtype=int)-1
    free = np.setdiff1d(np.arange(n), crack)
    assert s['step'] == 7 and s['stag'] == 2 and s['U'] == .21
    assert s['failure_stage'] == 'phase' and not s['certificate_valid']
    assert last['assembled'] and last['call'] == entered['call'] == 102
    assert np.array_equal(last['alpha'], entered['alpha'])
    point_file = loadmat(fem/'native_phase_last_points.mat', simplify_cells=True)
    assert np.array_equal(last['alpha'], point_file['native_last_completed']['alpha'])
    assert np.array_equal(last['Rpf'], point_file['native_last_completed']['Rpf'])
    returned = np.asarray(s['p_field']).ravel()
    pre = np.asarray(last['alpha']).ravel()
    pre_norm = float(np.linalg.norm(last['Rpf'][free]))
    fresh = float(s['native_return_pf_residual'])
    assert pre_norm < 1e-6 < fresh
    previous = loadmat(fem/'state_006.mat', simplify_cells=True)['p_field']
    assert np.array_equal(s['p_field_old'], previous)
    source = json.loads((r/'actual_helpers.json').read_text())
    native = next(x['content'] for x in source['sources'] if x['path'].endswith('/newton_raphson.m'))
    assert native.index('field_vars(active_dof, 1) = field_vars(active_dof, 1) + Dfield_vars;') < native.index('res = norm(res_field_vars(active_dof,1));') < native.index('res < args.res_tol')
    result = dict(accepted_loaded_states=verification['accepted_prefix'], last_accepted_U=.18,
        failed_U=.21, step=7, stagger=2, native_assembly_call=102,
        preupdate_Rpf_vector_norm=pre_norm, returned_fresh_Rpf_reported_scalar=fresh,
        original_tolerance=1e-6, returned_minus_preupdate_Linf=float(abs(returned-pre).max()),
        returned_minus_preupdate_L2=float(np.linalg.norm(returned-pre)),
        failed_alpha_min=float(returned.min()), failed_alpha_max=float(returned.max()),
        failed_max_healing=float((previous-returned).max()),
        solver_seconds=float(s['elapsed_seconds']), failed_step_seconds=float(s['step_seconds']),
        native_return_replayed=False, returned_Rpf_vector_exported=False,
        coupled_certificate_valid=False,
        conclusion='Native stopping residual belongs to the preupdate point; the returned postupdate point fails the unchanged fresh residual check. Full trajectory after repair is untested.')
    out = r/'analysis'
    (out/'native_return_timing.json').write_text(json.dumps(result, indent=2)+'\n')
    with (out/'native_return_timing.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['point', 'residual', 'evidence'])
        w.writerow(['last_native_preupdate', pre_norm, 'norm of exported Rpf vector'])
        w.writerow(['returned_postupdate', fresh, 'exported fresh scalar; no replay'])
    figs = out/'figures'
    figs.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.2, 4.2), constrained_layout=True)
    vals = [pre_norm, fresh]
    ax.bar([0, 1], vals, color=['#0072B2', '#D55E00'], width=.55)
    ax.axhline(1e-6, color='#444444', ls='--', lw=1.3, label='Unchanged tolerance 1e-6')
    for i, v in enumerate(vals):
        ax.text(i, v+3e-8, f'{v:.6g}', ha='center', fontsize=10)
    ax.set_xticks([0, 1], ['Last native assembly\nbefore update', 'Returned field\nfresh assembly'])
    ax.set_ylim(0, 1.48e-6)
    ax.set_ylabel('Free-DOF PF residual norm (normalized)')
    ax.ticklabel_format(axis='y', style='sci', scilimits=(0, 0))
    ax.set_title('R011: U=0.21, stagger 2\nStopping residual and returned field use different points', fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc='upper left')
    ax.spines[['right', 'top']].set_visible(False)
    for ext in ['png', 'pdf']:
        fig.savefig(figs/f'native_pf_return_timing.{ext}', dpi=180)
    plt.close(fig)
    (figs/'native_pf_return_timing.md').write_text(f'''# How to read native PF return timing

## Question and data provenance

Why did the fresh PF residual check reject the returned field? Exact source: {fem}/failed_state_007.mat, native_phase_last_points.mat, mesh.mat; source semantics: {r}/actual_helpers.json (locked native newton_raphson.m). Script: scripts/shear/analyze_manav_native_return.py. See ../native_return_timing.csv and ../native_return_timing.json. No assembly, fit or solver replay.

## How to read

One panel, same fixed PF input driver/history at U=.21, outer stagger2. Blue is the independent norm of the exported native preupdate Rpf vector, {pre_norm:.17g}; orange is the exported freshly assembled returned-point scalar, {fresh:.17g}. The dashed line is the original1e-6 inner tolerance. The native source updates the field before testing the preupdate residual; these are distinct fields (max nodal difference {result['returned_minus_preupdate_Linf']:.12g}). Axes use normalized residual units, zero baseline; no smoothing/clipping.

## Interpretation and limitations

The last assembled point is below tolerance, but after one further update the reported fresh returned residual is above it. This identifies the stopping/return-point mismatch for this call. The returned PF vector was not exported; its scalar is not independently reassembled here. No coupled certificate exists for either candidate at U=.21. Six accepted loaded states throughU=.18 were independently checked from saved arrays. No PIDL result exists. This does not prove a corrected full trajectory would converge, does not upgrade a rejected field to an accepted state, and does not establish physical or road validation.
''')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
