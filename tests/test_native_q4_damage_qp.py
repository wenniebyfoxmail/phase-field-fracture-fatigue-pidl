import numpy as np
import pytest

from damage_conditioned_equilibrium import build_q4_kinematics
from native_q4_damage_qp import (
    assemble_at1_damage_qp,
    gauss_interpolation_matrix,
    osqp_certificate,
    solve_with_osqp,
    validate_qp_contract,
)


def one_element():
    points = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)
    cells = np.array([[0, 1, 2, 3]], dtype=np.int32)
    return build_q4_kinematics(points, cells)


def test_gp_interpolation_preserves_constant_field():
    kin = one_element()
    assert np.allclose(gauss_interpolation_matrix(kin) @ np.full(4, 0.37), 0.37)


def test_at1_qp_is_symmetric_and_accepts_previous_state_witness():
    kin = one_element()
    previous_nodal = np.array([0.1, 0.2, 0.3, 0.4])
    previous_gp = (gauss_interpolation_matrix(kin) @ previous_nodal).reshape(1, 4)
    problem = assemble_at1_damage_qp(
        kin, np.full((1, 4), 0.8), np.full((1, 4), 0.7), previous_gp
    )
    report = validate_qp_contract(problem, previous_nodal)
    assert report["feasible_witness"]
    assert report["sampled_psd"]
    assert np.allclose(problem.hessian.toarray(), problem.hessian.toarray().T)


def test_negative_fatigue_is_rejected():
    kin = one_element()
    with pytest.raises(ValueError, match="non-negative"):
        assemble_at1_damage_qp(
            kin, np.ones((1, 4)), -np.ones((1, 4)), np.zeros((1, 4))
        )


def test_osqp_solution_has_independent_kkt_certificate():
    pytest.importorskip("osqp")
    kin = one_element()
    previous = np.full((1, 4), 0.15)
    problem = assemble_at1_damage_qp(
        kin, np.full((1, 4), 0.4), np.ones((1, 4)), previous
    )
    x, y, diagnostics = solve_with_osqp(problem, np.full(4, 0.15))
    certificate = osqp_certificate(problem, x, y)
    assert "solved" in diagnostics["status"].lower()
    assert np.min(problem.gp_constraint @ x - problem.gp_lower) >= -1.0e-7
    assert certificate.rho_damage <= 1.0e-5
