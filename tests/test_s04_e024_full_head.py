import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'SENS_tensile'))
from s04_e024_full_head import build_proxies, dual_value_gradient, solve_full
from s04_e024_weak_guard import Mechanics
from s04_e024_head_cone import elastic_driver


def test_dual_value_gradient_with_original_ellipsoid():
    rng = np.random.default_rng(7); n = 8
    columns = rng.normal(size=(7, n, n))
    h = np.einsum('kji,kjl->kil', columns, columns)+np.eye(n)[None]
    g = rng.normal(size=(7, n)); ball = np.diag(np.linspace(.5, 2, n))
    x = np.r_[np.full(6, .3), .7]
    _, gradient = dual_value_gradient(x, g, h, ball=ball)
    for i in range(7):
        delta = np.eye(7)[i]*1e-5
        finite = (dual_value_gradient(x+delta, g, h, ball=ball)[0]-dual_value_gradient(x-delta, g, h, ball=ball)[0])/2e-5
        assert gradient[i] == pytest.approx(finite, rel=1e-7, abs=1e-8)


def test_known_full_head_ball_solution_and_duality():
    g = np.tile(np.array([-2., 0., 0., 0.]), (7, 1))
    h = np.tile(np.eye(4), (7, 1, 1))
    z, raw, info, trace = solve_full(g, h)
    assert info['numerically_resolved'] and info['feasible']
    np.testing.assert_allclose(z, [1, 0, 0, 0], atol=1e-6)
    assert info['primal_half_relative_change'] == pytest.approx(-1.5, abs=1e-7)
    assert -1e-9 <= info['primal_dual_gap'] <= 1e-6
    assert np.linalg.norm(z) <= 1 and len(trace) > 0


def test_rank_deficiency_retains_all_coordinates_and_inactive_ball():
    g = np.tile(np.array([-.1, -.2, 0., 0.]), (7, 1))
    h = np.tile(np.diag([1., 2., 0., 0.]), (7, 1, 1))
    z, _, info, _ = solve_full(g, h)
    assert info['all_coordinates_retained'] and info['full_uv_rank_relative_1e12'] == 2
    assert info['numerically_resolved']
    np.testing.assert_allclose(z, [.1, .1, 0, 0], atol=1e-6)


def test_sparse_full_proxies_match_all_direct_native_columns():
    xy = np.array([[x, y] for y in [0., .5, 1.] for x in [0., .5, 1.]])
    conn = np.array([[0, 1, 4, 3], [1, 2, 5, 4], [3, 4, 7, 6], [4, 5, 8, 7]])
    damage = np.linspace(.1, .7, 9)
    origin = np.stack([xy[:, 0]**2*.01, -.003*xy[:, 1]], axis=1)
    mech = Mechanics(xy, conn, damage, origin)
    rng = np.random.default_rng(2); phi = np.zeros((9, 3)); phi[4] = rng.normal(size=3)
    error = rng.normal(size=(9, 2)); mass = mech.mass
    masks = dict(full=np.ones(9, bool), damage=np.arange(9)<5,
                 background=np.arange(9)>=5, inside_background=np.arange(9)>=6)
    weights = {k:mass*m/np.sum(mass*m) for k, m in masks.items()}
    gp_damage = np.full((4, 4), .4)
    p0, stress = elastic_driver(mech, origin, gp_damage)
    det = np.stack([a[1] for a in mech.geo], axis=1)
    gp_masks = [np.ones((4, 4), bool), np.indices((4, 4))[0]<2]
    ref = dict(US=.2, origin_force=mech.force(origin), basis_flat=np.eye(6)[:3],
               weights=det, driver_reference=p0*.7+1e-5, driver_masks=gp_masks)
    c, g, h, audit = build_proxies(phi, error, weights, mech, ref, .03, p0, stress)
    columns = np.zeros((6, 9, 2))
    for j in range(6):columns[j, :, j%2] = .03*phi[:, j//2]
    assert audit['sparse_tangent_3D_max_abs'] < 1e-13
    errors, derivatives, ws = [], [], []
    for weight in weights.values():
        errors.append(error); derivatives.append(columns/.2); ws.append(np.broadcast_to(weight[:, None], error.shape))
    errors.append(mech.dual(ref['origin_force']))
    derivatives.append(np.stack([mech.dual(mech.force(v, tangent=True)) for v in columns]))
    ws.append(np.ones_like(errors[-1]))
    ddriver = np.stack([np.sum(stress*mech.strains(v), axis=-1) for v in columns])
    for mask in gp_masks:
        errors.append(p0-ref['driver_reference']); derivatives.append(ddriver); ws.append(det*mask)
    for i, (e, v, w) in enumerate(zip(errors, derivatives, ws)):
        cc = np.sum(w*e**2); gg = np.einsum('n,n,in->i', w.ravel(), e.ravel(), v.reshape(6, -1))/cc
        hh = np.einsum('n,in,jn->ij', w.ravel(), v.reshape(6, -1), v.reshape(6, -1))/cc
        assert c[i] == pytest.approx(cc, rel=1e-12)
        np.testing.assert_allclose(g[i], gg, rtol=1e-11, atol=1e-12)
        np.testing.assert_allclose(h[i], hh, rtol=1e-11, atol=1e-12)


def test_invalid_or_indefinite_proxies_stop():
    g = np.ones((7, 4)); h = np.tile(np.eye(4), (7, 1, 1))
    h[3, 0, 0] = -1
    with pytest.raises(ValueError):solve_full(g, h)
    with pytest.raises(ValueError):solve_full(g[:6], h[:6])


def test_saved_solution_recovery_never_calls_an_optimizer(monkeypatch):
    import s04_e024_full_head
    from s04_e024_full_head_recovery import restore_solution
    monkeypatch.setattr(s04_e024_full_head, 'minimize', lambda *a, **k: pytest.fail('unexpected new solve'))
    cache = dict(full_z=np.array([1., 0.]), raw_z=np.array([1., 0.]),
                 quadratic_gradients=np.tile([-2., 0.], (7, 1)),
                 quadratic_hessians=np.tile(np.eye(2), (7, 1, 1)))
    record = dict(function_evaluations=1, multipliers=[0.]*6+[1.], dual_lower_bound=-1.5)
    candidate, raw, _, trace = restore_solution(cache, record)
    np.testing.assert_array_equal(candidate, cache['full_z'])
    assert trace[0]['dual_lower_bound'] == pytest.approx(-1.5)
    cache['raw_z'][0] = .9
    with pytest.raises(AssertionError):restore_solution(cache, record)


def test_cached_guard_failure_stops_after_one_saved_forward():
    from s04_e024_full_head_recovery import revalidate_once
    from s04_e024_three_head import GUARDS
    calls = []
    cache = dict(head_coefficients=np.ones((1, 2)), uv=np.zeros((3, 2)))
    def forward(coeff):
        calls.append(coeff.copy())
        return cache['uv'].copy()
    baseline = dict.fromkeys(GUARDS, 1.)
    failed = baseline.copy(); failed['weak_squared'] = 2.
    with pytest.raises(ValueError, match='cached c20 failed actual'):
        revalidate_once(cache, forward, lambda uv:failed, baseline, .02)
    assert len(calls) == 1
    np.testing.assert_array_equal(calls[0], cache['head_coefficients'])


def test_recovery_budget_includes_preserved_failed_attempt():
    from s04_e024_full_head_recovery import remaining_seconds
    assert remaining_seconds(100., 12.6264)==pytest.approx(787.3736)
    with pytest.raises(TimeoutError):remaining_seconds(888., 12.6264)
