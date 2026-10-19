import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'SENS_tensile'))
from s04_e024_joint_head import quadratic_terms, solve_joint


def test_exact_mass_quadratic_and_gradient():
    rng = np.random.default_rng(7)
    e, v, w = rng.normal(size=(9, 2)), rng.normal(size=(3, 9, 2)), rng.uniform(size=(9, 2))
    c, g, h = quadratic_terms(e, v, w)
    z = np.array([.1, -.3, .05])
    actual = np.sum(w*(e+np.einsum('i,ind->nd', z, v))**2)/c
    assert actual == pytest.approx(1+2*np.dot(g, z)+np.einsum('i,ij,j', z, h, z), abs=1e-14)
    assert np.linalg.eigvalsh(h).min() > 0


def test_error_unit_and_weight_scale_invariance():
    rng = np.random.default_rng(2)
    e, v, w = rng.normal(size=(6, 4)), rng.normal(size=(3, 6, 4)), np.ones((6, 4))
    a = quadratic_terms(e, v, w)
    b = quadratic_terms(100*e, 100*v, 3*w)
    assert b[0] == pytest.approx(a[0]*30000)
    np.testing.assert_allclose(a[1], b[1], atol=1e-14)
    np.testing.assert_allclose(a[2], b[2], atol=1e-14)


def test_whitened_solve_preserves_original_ball_and_known_optimum():
    h = np.tile(np.diag([1., 4., 9.]), (7, 1, 1))
    g = np.tile([-.1, -.2, -.3], (7, 1))
    z, report = solve_joint(g, h)
    assert report['success'] and report['feasible']
    np.testing.assert_allclose(z, [.1, .05, 1/30], atol=1e-9)
    assert report['numerical_rank_relative_1e12'] == 3
    assert np.dot(z, z) <= 1


def test_shared_budget_active_and_rotated_coordinates():
    h = np.tile(np.diag([.2, 2., 5.]), (7, 1, 1))
    g = np.tile([-2., -.4, -.7], (7, 1))
    z, report = solve_joint(g, h)
    assert report['success'] and report['feasible']
    assert np.linalg.norm(z) == pytest.approx(1, abs=1e-9)
    rotation, _ = np.linalg.qr(np.random.default_rng(4).normal(size=(3, 3)))
    rg = np.einsum('ki,ij->kj', g, rotation)
    rh = np.einsum('ia,kij,jb->kab', rotation, h, rotation)
    rz, rr = solve_joint(rg, rh)
    assert rr['success'] and rr['feasible']
    np.testing.assert_allclose(rotation@rz, z, atol=2e-6)


def test_physics_proxy_constraints_can_bind_without_replacing_actual_checks():
    h = np.tile(np.eye(3), (7, 1, 1))
    g = np.tile([-1., -1., -.1], (7, 1))
    g[4] = [.5, -.5, 0.]
    z, report = solve_joint(g, h)
    assert report['success'] and report['feasible']
    assert max(report['proxy_squared_relative_changes']) <= 1e-9
    assert report['objective_half_relative_change'] < -.1


@pytest.mark.parametrize('bad', ['nonfinite', 'shape', 'negative_weight', 'zero_error'])
def test_bad_quadratic_inputs_refused(bad):
    e, v, w = np.ones((4, 2)), np.ones((3, 4, 2)), np.ones((4, 2))
    if bad == 'nonfinite': v[0, 0, 0] = np.inf
    if bad == 'shape': v = v[:2]
    if bad == 'negative_weight': w[0, 0] = -1
    if bad == 'zero_error': e *= 0
    with pytest.raises(ValueError): quadratic_terms(e, v, w)


def test_nonconvex_and_singular_full_uv_refused():
    h = np.tile(np.eye(3), (7, 1, 1)); g = np.tile([-1., -.5, -.1], (7, 1))
    h[5, 0, 0] = -.2
    with pytest.raises(ValueError): solve_joint(g, h)
    h[5] = np.eye(3); h[0, 0, 0] = 0
    with pytest.raises(ValueError): solve_joint(g, h)


def test_floor_changes_coordinates_not_the_original_objective():
    h = np.tile(np.diag([1e-14, 1., 2.]), (7, 1, 1))
    g = np.zeros((7, 3)); g[:, 1] = -.2
    z, report = solve_joint(g, h)
    assert report['success'] and report['feasible']
    assert report['numerical_rank_relative_1e12'] == 2
    assert report['objective_half_relative_change'] == pytest.approx(-.02, abs=1e-10)
