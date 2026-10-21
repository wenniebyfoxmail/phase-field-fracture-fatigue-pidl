"""Verify saved Manav-setting FEM states without assembly, solving or refitting."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat


def scalar(s, k):
    return float(np.asarray(s[k]).item())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fem', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    assert not a.out.exists()
    expected = np.r_[np.arange(1, 8)*.03, np.arange(24, 41)*.01]
    m = loadmat(a.fem/'mesh.mat')
    x = m['nodes'][:, :2]
    n = len(x)
    schedule = m['schedule'].ravel()
    np.testing.assert_allclose(schedule, expected, atol=1e-14, rtol=0)
    top = m['top'].ravel().astype(int)-1
    bot = m['bot'].ravel().astype(int)-1
    crack = m['crack'].ravel().astype(int)-1
    assert np.isfinite(x).all()
    assert top.size and bot.size
    assert np.array_equal(np.sort(top), np.flatnonzero(abs(x[:, 1]-.5) < 1e-10))
    assert np.array_equal(np.sort(bot), np.flatnonzero(abs(x[:, 1]+.5) < 1e-10))
    geometry_crack = np.flatnonzero((abs(x[:, 1]) < 1e-10) & (x[:, 0] >= -.5-1e-10) & (x[:, 0] <= 1e-10))
    assert len(crack) == 251 and np.array_equal(crack, geometry_crack)
    free_xy = np.setdiff1d(np.arange(n), np.r_[top, bot])
    free_u = np.r_[free_xy, free_xy+n]
    free_pf = np.setdiff1d(np.arange(n), crack)
    zero = loadmat(a.fem/'state_000.mat')
    previous = zero['p_field'].ravel()
    assert np.array_equal(previous, m['alpha_initial'].ravel())
    assert np.array_equal(previous, zero['p_field_old'].ravel())
    assert np.all(zero['displ'] == 0) and scalar(zero, 'U') == 0
    assert np.isfinite(scalar(zero, 'res_pf')) and 0 <= scalar(zero, 'res_pf') <= 1e-6 and np.isfinite(previous).all()
    assert min(previous) >= -.005 and max(previous) <= 1.005 and np.all(previous[crack] == 1)
    with (a.fem/'trajectory.csv').open() as f:
        rows = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(f)]
    assert all(np.isfinite(r['step']) and r['step'].is_integer() and np.isfinite(r['U']) for r in rows)
    assert [int(r['step']) for r in rows] == list(range(1, len(rows)+1))
    verified = []
    for r in rows:
        step = int(r['step'])
        s = loadmat(a.fem/f'state_{step:03d}.mat')
        d, h, u, force, pf = [s[k].ravel() for k in ['p_field', 'p_field_old', 'displ', 'forces', 'pf_force']]
        assert all(np.isfinite(t).all() for t in [d, h, u, force, pf, s['driver']])
        assert len(d) == len(h) == len(pf) == n and len(u) == len(force) == 2*n
        assert scalar(s, 'step') == step and abs(scalar(s, 'U')-schedule[step-1]) < 1e-14
        assert abs(r['U']-schedule[step-1]) < 1e-14 and abs(r['U']-scalar(s, 'U')) < 1e-14
        assert ''.join(s['timing'].ravel().astype(str)) == 'post_solve_pre_history_update'
        assert np.array_equal(h, previous) and np.all(d[crack] == 1)
        np.testing.assert_allclose(u[top], schedule[step-1], rtol=0, atol=1e-12)
        np.testing.assert_allclose(u[np.r_[bot, bot+n, top+n]], 0, rtol=0, atol=1e-12)
        checks = dict(res_u=np.linalg.norm(force[free_u]), res_pf=np.linalg.norm(pf[free_pf]),
                      alpha_min=d.min(), alpha_max=d.max(), max_healing=(h-d).max(),
                      Rx_top=force[top].sum(), Rx_bottom=force[bot].sum())
        for k, v in checks.items():
            assert np.isclose(v, r[k], rtol=1e-10, atol=1e-12), (step, k, v, r[k])
        for k in ['E_el', 'E_d', 'res_u', 'res_pf']:
            assert np.isfinite(scalar(s, k)) and np.isclose(scalar(s, k), r[k], rtol=1e-10, atol=1e-12)
        assert checks['res_u']+checks['res_pf'] <= 1e-4
        assert checks['alpha_min'] >= -.005 and checks['alpha_max'] <= 1.005 and checks['max_healing'] <= .005
        verified.append(dict(r, verified=True))
        previous = d
    end = json.loads((a.fem.parent/'exit.json').read_text())
    complete = len(verified) == 24 and end['exit_code'] == 0 and (a.fem/'COMPLETED.txt').is_file()
    result = dict(complete_valid_reference=complete, accepted_prefix=len(verified), prescribed_states=24,
                  recovered_state0=True, loaded_force_norms_checked=len(verified), history_BC_and_damage_checked=True,
                  state0_PF_residual_reported_scalar_only=scalar(zero, 'res_pf'), state0_PF_force_not_exported=True,
                  native_assembly_replayed=False, exit=end, PIDL_status_not_checked=True)
    a.out.mkdir(parents=True)
    (a.out/'reference_verification.json').write_text(json.dumps(result, indent=2, allow_nan=False))
    if verified:
        with (a.out/'verified_states.csv').open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(verified[0])); w.writeheader(); w.writerows(verified)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
