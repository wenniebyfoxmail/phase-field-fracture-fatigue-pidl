from dataclasses import replace
import hashlib
import json

import numpy as np
import pytest
import torch

from compute_energy import compute_energy_per_elem
from material_properties import MaterialProperties
from pff_model import PFFModel
from q4_quadrature import q4_interpolate, q4_shape_data
from native_q4_damage_qp import (
    assemble_at1_damage_qp,
    build_native_q4_kinematics,
    gauss_interpolation_matrix,
    osqp_certificate,
    solve_with_osqp,
    validate_a1_admission_receipt,
    validate_qp_contract,
)


def one_element():
    points = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)
    cells = np.array([[0, 1, 2, 3]], dtype=np.int32)
    return build_native_q4_kinematics(points, cells)


def test_gp_interpolation_preserves_constant_field():
    kin = one_element()
    assert np.allclose(gauss_interpolation_matrix(kin) @ np.full(4, 0.37), 0.37)


def test_native_gp_interpolation_order_matches_q4_operator_for_two_nonconstant_elements():
    points = np.array([[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]], dtype=float)
    cells = np.array([[0, 1, 4, 3], [1, 2, 5, 4]], dtype=np.int32)
    nodal = np.array([0.02, 0.13, 0.41, 0.29, 0.73, 0.97])
    kin = build_native_q4_kinematics(points, cells)
    actual = (gauss_interpolation_matrix(kin) @ nodal).reshape(2, 4)
    inp = torch.tensor(points, dtype=torch.float64)
    conn = torch.tensor(cells, dtype=torch.long)
    shape, _, _ = q4_shape_data(inp, conn)
    expected = q4_interpolate(torch.tensor(nodal), conn, shape).numpy()
    assert np.allclose(actual, expected, atol=1.0e-14, rtol=0.0)


def test_at1_qp_is_symmetric_and_accepts_previous_state_witness():
    kin = one_element()
    previous_nodal = np.array([0.1, 0.2, 0.3, 0.4])
    previous_gp = (gauss_interpolation_matrix(kin) @ previous_nodal).reshape(1, 4)
    problem = assemble_at1_damage_qp(
        kin, np.full((1, 4), 0.8), np.full((1, 4), 0.7), previous_gp
    )
    report = validate_qp_contract(problem, previous_nodal)
    assert report["feasible_witness"]
    assert report["assembly_psd"]
    assert np.allclose(problem.hessian.toarray(), problem.hessian.toarray().T)


def test_negative_fatigue_is_rejected():
    kin = one_element()
    with pytest.raises(ValueError, match="non-negative"):
        assemble_at1_damage_qp(
            kin, np.ones((1, 4)), -np.ones((1, 4)), np.zeros((1, 4))
        )


def test_local_psd_certificate_rejects_a_declared_indefinite_assembly():
    kin = one_element()
    problem = assemble_at1_damage_qp(
        kin, np.ones((1, 4)), np.ones((1, 4)), np.zeros((1, 4))
    )
    bad = replace(problem, minimum_local_eigenvalue=-1.0)
    with pytest.raises(RuntimeError, match="PSD"):
        validate_qp_contract(bad, np.zeros(4))


def test_qp_gradient_and_hessian_match_compute_energy_native_q4():
    points = np.array([[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]], dtype=float)
    cells = np.array([[0, 1, 4, 3], [1, 2, 5, 4]], dtype=np.int32)
    kin = build_native_q4_kinematics(points, cells)
    inp = torch.tensor(points, dtype=torch.float64)
    conn = torch.tensor(cells, dtype=torch.long)
    u = torch.tensor([0.00, 0.03, 0.08, 0.01, 0.05, 0.11], dtype=torch.float64)
    v = torch.tensor([0.00, -0.01, -0.02, 0.04, 0.07, 0.12], dtype=torch.float64)
    damage = torch.tensor([0.31, 0.37, 0.42, 0.35, 0.48, 0.53], dtype=torch.float64,
                          requires_grad=True)
    history = torch.full((6,), -1.0, dtype=torch.float64)
    fatigue = torch.tensor([[0.91, 0.84, 0.79, 0.88], [0.73, 0.69, 0.64, 0.71]],
                           dtype=torch.float64)
    mat = MaterialProperties(1.0, 0.3, 1.0, 0.01)
    model = PFFModel("AT1", "volumetric", residual_stiffness=0.0)
    _, psi = __import__("compute_energy").strain_energy_with_split(
        *(
            lambda dshape: (
                __import__("q4_quadrature").q4_gradient(u, conn, dshape)[:, :, 0],
                __import__("q4_quadrature").q4_gradient(v, conn, dshape)[:, :, 1],
                0.5 * (
                    __import__("q4_quadrature").q4_gradient(u, conn, dshape)[:, :, 1]
                    + __import__("q4_quadrature").q4_gradient(v, conn, dshape)[:, :, 0]
                ),
            )
        )(q4_shape_data(inp, conn)[1]),
        q4_interpolate(damage.detach(), conn, q4_shape_data(inp, conn)[0]), mat, model,
    )
    previous_gp = np.zeros((2, 4))
    problem = assemble_at1_damage_qp(kin, psi.detach().numpy(), fatigue.numpy(), previous_gp)

    def energy(alpha):
        parts = compute_energy_per_elem(
            inp, u, v, alpha, history, mat, model, torch.ones(2), conn,
            f_fatigue=fatigue,
            irreversibility_penalty_cfg={"enable": True, "mode": "fem_gp_q4"},
        )
        return sum(part.sum() for part in parts)

    gradient = torch.autograd.grad(energy(damage), damage, create_graph=True)[0]
    hessian = torch.autograd.functional.hessian(energy, damage.detach())
    qp_gradient = problem.hessian @ damage.detach().numpy() + problem.linear
    assert np.allclose(qp_gradient, gradient.detach().numpy(), atol=2.0e-12, rtol=2.0e-12)
    assert np.allclose(problem.hessian.toarray(), hessian.detach().numpy(),
                       atol=2.0e-12, rtol=2.0e-12)


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


def test_certificate_rejects_wrong_positive_dual_on_active_gp_lower_bound():
    kin = one_element()
    problem = assemble_at1_damage_qp(
        kin, np.zeros((1, 4)), np.zeros((1, 4)), np.zeros((1, 4))
    )
    # q=-1 and a wrong positive GP dual cancel stationarity at x=0.  The
    # lower-only sign check must still reject the certificate.
    problem = replace(problem, linear=-np.ones(4))
    x = np.zeros(4)
    dual = np.concatenate((np.zeros(4), np.ones(4)))
    certificate = osqp_certificate(problem, x, dual)
    assert certificate.stationarity_scaled == pytest.approx(0.0)
    assert certificate.dual_sign_inf == pytest.approx(1.0)
    assert certificate.rho_damage == pytest.approx(1.0)


def test_a1_receipt_is_hash_bound_and_fail_closed(tmp_path):
    payload = {
        "schema": "s04-e003-native-cross-stationarity-admission-v1",
        "label": "A1_TRIAL_F_ADMITTED",
        "native_capture_sha256": "capture",
        "mesh_signature": "mesh",
        "source_state": "lineage-qualified FEM c83 s4 pre-phase accepted state",
        "target_state": "lineage-qualified FEM c83 s4 converged peak",
        "native_gp_order": "(+,+),(-,+),(+,-),(-,-)",
        "trial_f_semantics": "rebuilt from immutable accepted history",
        "directional_derivative_pass": True,
        "mechanics_residual_equivalence_pass": True,
        "damage_residual_equivalence_pass": True,
        "trial_cross_stationarity_pass": True,
        "admit_s04_e004": True,
        "primary_threshold": 1.0e-3,
        "rho_u_trial": 1.0e-4,
        "rho_d_trial": 2.0e-4,
        "directional_derivative_error": 3.0e-7,
    }
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(payload, sort_keys=True))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    accepted = validate_a1_admission_receipt(
        path, digest, native_capture_sha256="capture", mesh_signature="mesh"
    )
    assert accepted["admit_s04_e004"]
    payload["trial_cross_stationarity_pass"] = False
    path.write_text(json.dumps(payload, sort_keys=True))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(RuntimeError, match="does not admit"):
        validate_a1_admission_receipt(
            path, digest, native_capture_sha256="capture", mesh_signature="mesh"
        )
