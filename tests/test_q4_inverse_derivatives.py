"""Small-array derivative checks only: no primal FEM or inverse optimization."""
from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"source"))
from hybrid_history import AcceptedState, fatigue_factor
from hybrid_kinematics import build_portable_native_q4_kinematics
from q4_inverse_derivatives import (
    ImplicitStep, Material, NonregularBranch, Q4Residual, Variation,
    observation_tangent, dense_regularity_evidence,
)


def fixture(compression=False, accumulating=True):
    points = np.array([[0., 0.], [1., 0.], [1., 1.], [0., 1.]])
    kin = build_portable_native_q4_kinematics(points, np.array([[0, 1, 2, 3]]))
    m = Material(gc=.08, alpha_t=.2)
    old_a = np.array([[.33, .37, .41, .46]])
    old_q = np.full((1, 4), .0001 if accumulating else .2)
    old = AcceptedState(np.zeros(8), np.array([.08, .09, .10, .11]),
            old_a, old_q, fatigue_factor(old_a, m.alpha_t, m.power),
            np.zeros((1, 4)), 0, 0, "unit-mesh", "unit-physics", "unit-load")
    u = np.array([.001, .002, .12, .015, .13, .11, .02, .12])
    if compression:
        u = -u
    d = np.array([.22, .26, .24, .25])
    return kin, m, old, u, d


def perturbed(kin, m, old, u, d, du, dd, ov, pm, h):
    mt = replace(m, youngs_modulus=m.youngs_modulus+h*pm[0],
                 gc=m.gc+h*pm[1], alpha_t=m.alpha_t+h*pm[2])
    a = old.accumulated+h*ov.accumulated
    prev = replace(old, displacement=old.displacement+h*ov.displacement,
                   damage=old.damage+h*ov.damage, accumulated=a,
                   driver=old.driver+h*ov.driver,
                   fatigue=fatigue_factor(a, mt.alpha_t, mt.power))
    return Q4Residual(kin, mt, prev).evaluate(u+h*du, d+h*dd)


@pytest.mark.parametrize("compression", [False, True])
@pytest.mark.parametrize("accumulating", [False, True])
def test_full_jvp_matches_original_kernel_central_difference(compression, accumulating):
    kin, m, old, u, d = fixture(compression, accumulating)
    r = Q4Residual(kin, m, old)
    du = np.linspace(-.03, .02, 8)
    dd = np.array([.02, -.01, .03, -.02])
    ov = Variation(np.zeros(8), np.array([.001, .002, -.001, -.002]),
                   np.array([[.03, -.02, .01, .04]]), np.full((1, 4), .0002))
    pm = np.array([.17, -.012, .025])
    analytic = r.directional(u, d, du, dd, old_variation=ov, parameters=pm)
    h = 1.e-5
    plus = perturbed(kin, m, old, u, d, du, dd, ov, pm, h)
    minus = perturbed(kin, m, old, u, d, du, dd, ov, pm, -h)
    for name in vars(analytic):
        fd = (getattr(plus, name)-getattr(minus, name))/(2*h)
        np.testing.assert_allclose(getattr(analytic, name), fd, rtol=3.e-7, atol=2.e-10)


@pytest.mark.parametrize("parameter", range(3))
def test_each_material_path_including_explicit_reaction(parameter):
    kin, m, old, u, d = fixture()
    r = Q4Residual(kin, m, old)
    pm = np.eye(3)[parameter]
    z = r.zero_variation()
    derivative = r.directional(u, d, z.displacement, z.damage, parameters=pm)
    plus = perturbed(kin, m, old, u, d, z.displacement, z.damage, z, pm, 1.e-6)
    minus = perturbed(kin, m, old, u, d, z.displacement, z.damage, z, pm, -1.e-6)
    for name in vars(derivative):
        np.testing.assert_allclose(getattr(derivative, name),
            (getattr(plus, name)-getattr(minus, name))/2.e-6, rtol=2.e-6, atol=3.e-10)
    reaction, observed_u = observation_tangent(derivative, z,
                        reaction_dofs=np.array([3, 5]), displacement_dofs=np.array([2, 6]))
    if parameter == 0:
        assert abs(reaction) > 1.e-4
    np.testing.assert_array_equal(observed_u, 0.)


def test_no_fatigue_parameter_information_before_threshold():
    kin, m, old, u, d = fixture()
    a = old.accumulated*.001
    old = replace(old, accumulated=a, fatigue=fatigue_factor(a, m.alpha_t, m.power))
    r = Q4Residual(kin, m, old)
    z = r.zero_variation()
    out = r.directional(u, d, z.displacement, z.damage, parameters=(0., 0., 1.))
    np.testing.assert_array_equal(out.fatigue, 0.)
    np.testing.assert_array_equal(out.damage_residual, 0.)


def test_scale_symmetry_direction_is_invisible_in_u_d_but_not_force():
    kin, m, old, u, d = fixture()
    r = Q4Residual(kin, m, old)
    ov = Variation(np.zeros(8), np.zeros(4), old.accumulated, old.driver)
    out = r.directional(u, d, np.zeros(8), np.zeros(4), old_variation=ov,
                        parameters=(m.youngs_modulus, m.gc, m.alpha_t))
    p = r.evaluate(u, d)
    np.testing.assert_allclose(out.fatigue, 0., atol=2.e-16)
    np.testing.assert_allclose(out.force, p.force, atol=2.e-16)
    np.testing.assert_allclose(out.damage_residual, p.damage_residual, atol=2.e-15)


def test_lower_bound_tangent_inherits_old_damage_without_primal_solve():
    kin, m, old, u, _ = fixture(accumulating=False)
    u = u*.05
    r = Q4Residual(kin, m, old)
    step = ImplicitStep(r, u, old.damage, np.arange(8),
                        force_tolerance=1.e-10, damage_tolerance=1.e-10)
    assert step.size == 0
    ov = Variation(np.zeros(8), np.array([.001, .002, .003, .004]),
                   np.ones((1, 4))*.03, np.ones((1, 4))*.002)
    def forbidden(*args):
        raise AssertionError("no linear or primal solve needed")
    out, derivative = step.propagate(ov, solve=forbidden, linear_tolerance=1.e-10)
    np.testing.assert_array_equal(out.damage, ov.damage)
    np.testing.assert_array_equal(out.accumulated, ov.accumulated)
    assert np.linalg.norm(derivative.force) > 0


def test_switches_rejected_for_linear_implicit_use():
    kin, m, old, u, d = fixture()
    r = Q4Residual(kin, m, old)
    z = r.zero_variation()
    with pytest.raises(NonregularBranch):
        r.directional(np.zeros(8), d, z.displacement, z.damage)
    same_q = r.evaluate(u, d).driver
    changed = replace(old, driver=same_q)
    with pytest.raises(NonregularBranch):
        Q4Residual(kin, m, changed).directional(u, d, z.displacement, z.damage)


def test_history_switch_one_sided_is_not_silently_a_linear_jacobian():
    kin, m, old, u, d = fixture()
    r = Q4Residual(kin, m, old)
    old = replace(old, driver=r.evaluate(u, d).driver)
    r = Q4Residual(kin, m, old)
    du = u*.1
    z = r.zero_variation()
    j = r.directional(u, d, du, z.damage, strict=False)
    plus = perturbed(kin, m, old, u, d, du, z.damage, z, np.zeros(3), 1.e-6)
    p = r.evaluate(u, d)
    np.testing.assert_allclose(j.accumulated, (plus.accumulated-p.accumulated)/1.e-6,
                               rtol=2.e-5, atol=1.e-10)


def test_fatigue_threshold_has_correct_one_sided_direction():
    kin, m, old, u, d = fixture(accumulating=False)
    old = replace(old, accumulated=np.full((1, 4), m.alpha_t), fatigue=np.ones((1, 4)))
    r = Q4Residual(kin, m, old)
    z = r.zero_variation()
    with pytest.raises(NonregularBranch):
        r.directional(u, d, z.displacement, z.damage)
    out = r.directional(u, d, z.displacement, z.damage, parameters=(0., 0., -1.), strict=False)
    np.testing.assert_allclose(out.fatigue, -m.power/(2*m.alpha_t))
    plus = perturbed(kin, m, old, u, d, z.displacement, z.damage, z, np.array([0., 0., -1.]), 1.e-7)
    np.testing.assert_allclose(out.fatigue, (plus.fatigue-1)/1.e-7, rtol=1.e-6)


@pytest.mark.parametrize("sign", [-1., 1.])
def test_amor_trace_switch_right_direction_matches_original_residual(sign):
    kin, m, old, _, d = fixture()
    u = np.column_stack((.05*kin.points[:, 0], -.05*kin.points[:, 1])).ravel()
    du = sign*np.column_stack((.01*kin.points[:, 0], .02*kin.points[:, 1])).ravel()
    r = Q4Residual(kin, m, old)
    z = r.zero_variation()
    out = r.directional(u, d, du, z.damage, strict=False)
    plus = perturbed(kin, m, old, u, d, du, z.damage, z, np.zeros(3), 1.e-7)
    p = r.evaluate(u, d)
    for name in vars(out):
        np.testing.assert_allclose(getattr(out, name),
            (getattr(plus, name)-getattr(p, name))/1.e-7, rtol=1.e-5, atol=3.e-9)


def test_rejects_bad_material_history_geometry_and_sensors():
    kin, m, old, u, d = fixture()
    with pytest.raises(ValueError):
        Material(gc=-1.)
    with pytest.raises(ValueError):
        Q4Residual(kin, replace(m, alpha_t=.4), old)
    wrong = replace(kin, shape_values=kin.shape_values[::-1])
    with pytest.raises(ValueError):
        Q4Residual(wrong, m, old)
    r = Q4Residual(kin, m, old)
    with pytest.raises(ValueError):
        r.evaluate(u, old.damage-.01)
    with pytest.raises(ValueError):
        observation_tangent(r.evaluate(u, d), r.zero_variation(),
                    reaction_dofs=np.array([1, 1]), displacement_dofs=np.array([0]))


def test_geometry_cannot_change_after_adapter_creation():
    kin, m, old, u, d = fixture()
    r = Q4Residual(kin, m, old)
    before = r.evaluate(u, d).force
    kin.b_matrices[:] *= 4
    np.testing.assert_array_equal(r.evaluate(u, d).force, before)


def test_coupled_implicit_algebra_and_boundary_lift_on_analytic_patch():
    # Analytically prescribed stationary 4-cell patch. No primal solver or
    # parameter optimizer is called. Only its 11x11 sensitivity equation is
    # solved as unit-test linear algebra.
    points = np.array([[x, y] for y in (0., .5, 1.) for x in (0., .5, 1.)])
    cells = np.array([[0, 1, 4, 3], [1, 2, 5, 4], [3, 4, 7, 6], [4, 5, 8, 7]])
    kin = build_portable_native_q4_kinematics(points, cells)
    m = Material(gc=.08, alpha_t=.2)
    u = (.3*points).ravel()
    a = np.full((4, 4), 2.)
    f = fatigue_factor(a, m.alpha_t, m.power)
    from damage_conditioned_equilibrium import tensile_energy
    psi = tensile_energy(kin, u, youngs_modulus=m.youngs_modulus,
                         poisson_ratio=m.poisson_ratio)[0]
    damage = 1.-m.gc*f[0, 0]/((8/3)*m.length_scale*2*psi[0, 0])
    old = AcceptedState(np.zeros(18), np.full(9, .1), a, np.full((4, 4), 10.),
                        f, np.zeros((4, 4)), 0, 0, "patch", "unit", "unit")
    r = Q4Residual(kin, m, old)
    bc = np.array([i for i in range(18) if i not in (8, 9)])
    step = ImplicitStep(r, u, np.full(9, damage), bc,
                        force_tolerance=1.e-12, damage_tolerance=1.e-12)
    assert step.size == 11
    matrix = np.column_stack([step.operator @ col for col in np.eye(step.size)])
    regularity = dense_regularity_evidence(step.operator)
    assert np.linalg.norm(matrix[:2, 2:]) > .001  # Kud retained
    assert np.linalg.norm(matrix[2:, :2]) > .001  # Kdu retained
    ov = Variation(np.zeros(18), np.zeros(9), np.full((4, 4), .02), np.zeros((4, 4)))
    pm = np.array([.1, .01, .03]); scale = .04
    solve = lambda op, rhs: np.linalg.solve(matrix, rhs)
    v, fields = step.propagate(ov, parameters=pm, boundary_variation=scale*u[bc],
                              solve=solve, linear_tolerance=1.e-11, regularity=regularity)
    expected_df = m.power*(pm[2]/m.alpha_t-(.02+pm[2])/(2.+m.alpha_t))
    expected_dd = -(1.-damage)*(pm[1]/m.gc+expected_df-pm[0]/m.youngs_modulus-2*scale)
    np.testing.assert_allclose(v.displacement, scale*u, atol=3.e-15)
    np.testing.assert_allclose(v.damage, expected_dd, atol=3.e-14)
    np.testing.assert_allclose(v.accumulated, .02, atol=1.e-16)
    top = np.array([13, 15, 17])
    reaction, _ = observation_tangent(fields, v, reaction_dofs=top,
                                      displacement_dofs=np.array([8]))
    base = r.evaluate(u, np.full(9, damage)).force[top].sum()
    expected_force = base*(pm[0]/m.youngs_modulus-2*expected_dd/(1.-damage)+scale)
    np.testing.assert_allclose(reaction, expected_force, atol=3.e-14)
    with pytest.raises(RuntimeError, match="linear solve failed"):
        step.propagate(ov, parameters=pm, solve=lambda op, rhs: np.ones(step.size)*123,
                       linear_tolerance=1.e-12, regularity=regularity)
    with pytest.raises(NonregularBranch, match="missing or wrong-operator"):
        step.propagate(ov, parameters=pm, solve=solve, linear_tolerance=1.e-12)
    malformed = replace(regularity, sigma_min=np.nan)
    with pytest.raises(NonregularBranch, match="malformed"):
        step.propagate(ov, parameters=pm, solve=solve, linear_tolerance=1.e-12, regularity=malformed)
    wrong_op = replace(regularity, operator=np.eye(step.size))
    with pytest.raises(NonregularBranch, match="wrong-operator"):
        step.propagate(ov, parameters=pm, solve=solve, linear_tolerance=1.e-12, regularity=wrong_op)


def test_null_modes_rejected_before_any_tangent_solve():
    kin, m, old, u, _ = fixture(accumulating=False)
    old = replace(old, damage=np.ones(4))
    r = Q4Residual(kin, m, old)
    step = ImplicitStep(r, u, np.ones(4), np.array([], dtype=int),
                        force_tolerance=1.e-10, damage_tolerance=1.e-10)
    evidence = dense_regularity_evidence(step.operator)
    def forbidden(*args):
        raise AssertionError("must reject singular operator before solver callback")
    with pytest.raises(NonregularBranch, match="singular or inadequately conditioned"):
        step.propagate(r.zero_variation(), solve=forbidden, linear_tolerance=1.e-12,
                       regularity=evidence)
