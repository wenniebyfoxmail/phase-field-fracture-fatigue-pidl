from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "SENS_tensile"), str(ROOT / "source")]

from compute_energy import compute_energy_per_elem  # noqa: E402
from material_properties import MaterialProperties  # noqa: E402
from pff_model import PFFModel  # noqa: E402
from q4_quadrature import q4_interpolate, q4_shape_data  # noqa: E402
from run_native_q4_direct_q4_damage import (  # noqa: E402
    ARM_A,
    FixedDamageProblem,
    analytic_damage_gradient,
    audit_arm_b_feasibility,
    build_proximity_identity,
    direct_gradient,
    evaluate_fem_proximity,
    kkt_metrics,
    load_proximity_assets,
    projected_kkt_map,
    solve_damage_block,
    smoke_progress_ok,
    stagnation_reached,
    validate_arm_b_trigger,
    validate_frozen_solver_contract,
    validate_smoke_pass_receipt,
    weighted_relative_gap,
)


def patch(nx=1, ny=1):
    points = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            points.append([float(i), float(j)])
    cells = []
    stride = nx + 1
    for j in range(ny):
        for i in range(nx):
            n0 = j * stride + i
            cells.append([n0, n0 + 1, n0 + stride + 1, n0 + stride])
    points = torch.tensor(points, dtype=torch.float64)
    cells = torch.tensor(cells, dtype=torch.long)
    area = torch.ones(len(cells), dtype=torch.float64)
    u = 0.013 * points[:, 0] - 0.002 * points[:, 1]
    v = -0.004 * points[:, 0] + 0.021 * points[:, 1]
    accepted = torch.linspace(0.08, 0.18, len(points), dtype=torch.float64)
    damage = torch.linspace(0.12, 0.32, len(points), dtype=torch.float64)
    fatigue = torch.linspace(0.65, 0.95, len(cells) * 4,
                             dtype=torch.float64).reshape(len(cells), 4)
    mat = MaterialProperties(1.0, 0.3, 1.0, 0.01)
    model = PFFModel("AT1", "volumetric", 5e-3, residual_stiffness=0.0)
    return points, cells, area, u, v, accepted, damage, fatigue, mat, model


def proximity_receipt(label="UNCLOSED_DESCRIPTIVE_ONLY"):
    return {
        "proximity_label": label,
        "proximity_qualification_pass": False,
        "proximity_e_q_new": 1.0,
        "proximity_e_q_comparator": 1.0,
        "proximity_e_I_new": 1.0,
        "proximity_e_I_comparator": 1.0,
        "proximity_e_d_new": 1.0,
        "proximity_e_d_comparator": 1.0,
    }


def proximity_identity(comparator_sha="comparator", fem_sha="fem"):
    return {
        "comparator_label": "adaptive_final_C9600",
        "comparator_sha256": comparator_sha,
        "fem_reference_label": "fem_c83_peak",
        "fem_reference_sha256": fem_sha,
        "metric_schema": "native_q4_det_weighted_relL2_q_d_abs_log_integral_v1",
        "operator_schema": "native_q4_gp4_same_support_and_det_j_v1",
        "proximity_identity_sha256": "identity",
    }


def test_frozen_solver_contract_rejects_relaxed_production_gate():
    from run_native_q4_direct_q4_damage import FROZEN_SOLVER_CONTRACT
    args = SimpleNamespace(**FROZEN_SOLVER_CONTRACT)
    validate_frozen_solver_contract(args)
    args.outer_k_tol = 1.0
    with pytest.raises(ValueError, match="frozen solver contract mismatch"):
        validate_frozen_solver_contract(args)


@pytest.mark.parametrize("nx,ny", [(1, 1), (2, 2)])
def test_analytic_damage_gradient_matches_independent_autograd(nx, ny):
    inp, cells, area, u, v, accepted, damage, fatigue, mat, model = patch(nx, ny)
    analytic = analytic_damage_gradient(
        inp, cells, u, v, damage, accepted, fatigue, mat, model
    )
    independent, _, _ = direct_gradient(
        inp, cells, area, u, v, damage, accepted, fatigue, mat, model
    )
    relmax = float((analytic - independent).abs().max()) / max(
        float(independent.abs().max()), 1e-30
    )
    assert relmax <= 1e-8


def test_irreversibility_penalty_formula_and_derivative():
    inp, cells, area, u, v, accepted, damage, fatigue, mat, model = patch()
    u = torch.zeros_like(u)
    v = torch.zeros_like(v)
    damage = torch.full_like(damage, 0.1).requires_grad_(True)
    accepted = torch.full_like(accepted, 0.3)
    _, _, e_hist = compute_energy_per_elem(
        inp, u, v, damage, accepted, mat, model, area, cells,
        f_fatigue=fatigue,
        irreversibility_penalty_cfg={"enable": True, "mode": "fem_gp_q4"},
    )
    shape, _, det = q4_shape_data(inp, cells)
    dgp = q4_interpolate(damage, cells, shape)
    d0gp = q4_interpolate(accepted, cells, shape)
    manual = 0.5 * mat.w1 * model.irrPenalty() * (
        torch.relu(d0gp - dgp).square() * det
    ).sum()
    torch.testing.assert_close(e_hist.sum(), manual, rtol=0.0, atol=1e-12)
    (grad_ad,) = torch.autograd.grad(e_hist.sum(), damage)
    grad_manual = torch.zeros_like(damage).scatter_add(
        0, cells.reshape(-1),
        torch.einsum(
            "eg,gn->en",
            -mat.w1 * model.irrPenalty() * det * torch.relu(d0gp - dgp),
            shape,
        ).reshape(-1),
    )
    torch.testing.assert_close(grad_ad, grad_manual, rtol=1e-12, atol=1e-12)


def test_scaled_box_kkt_map_has_correct_bound_signs_and_known_solution():
    damage = torch.tensor([0.0, 0.0, 0.4, 1.0, 1.0], dtype=torch.float64)
    gradient = torch.tensor([2.0, -3.0, 0.0, -4.0, 5.0], dtype=torch.float64)
    kmap = projected_kkt_map(damage, gradient, 1.0)
    torch.testing.assert_close(kmap, torch.tensor([0.0, -1.0, 0.0, 0.0, 1.0],
                                                  dtype=torch.float64))
    known = torch.tensor([0.0, 0.3, 1.0], dtype=torch.float64)
    known_gradient = torch.tensor([0.2, 0.0, -0.4], dtype=torch.float64)
    assert kkt_metrics(known, known_gradient, 1.0)["k_inf"] <= 1e-8
    fixed = torch.tensor([1.0], dtype=torch.float64)
    assert kkt_metrics(fixed, torch.tensor([123.0], dtype=torch.float64), 1.0,
                       lower=fixed)["k_inf"] == 0.0


def test_weighted_relative_gap_uses_q4_integration_weights():
    old = torch.tensor([[1.0, 2.0]], dtype=torch.float64)
    new = torch.tensor([[2.0, 2.0]], dtype=torch.float64)
    weights = torch.tensor([[4.0, 1.0]], dtype=torch.float64)
    expected = 2.0 / np.sqrt(8.0)
    assert weighted_relative_gap(new, old, weights) == pytest.approx(expected)


def test_arm_b_feasibility_audits_nodal_and_gp_lower_bounds():
    inp, cells, _, _, _, accepted, damage, _, _, _ = patch()
    lower = torch.minimum(accepted, damage)
    shape, _, _ = q4_shape_data(inp, cells)
    history_gp = q4_interpolate(lower, cells, shape)
    report = audit_arm_b_feasibility(inp, cells, damage, lower, history_gp)
    assert report["initial_feasible"] and report["gp_lower_feasible"]
    with pytest.raises(RuntimeError, match="Arm B NO-GO"):
        audit_arm_b_feasibility(inp, cells, damage, lower, history_gp + 1e-3)


def test_arm_b_trigger_requires_both_K0_passes_and_gp_violation(tmp_path):
    identity = {"runner_sha256": "runner", "b0_identity_sha256": "b0"}
    prox_identity = proximity_identity()
    smoke_sha256 = "smoke"
    receipt = tmp_path / "arm_a.json"
    receipt.write_text(json.dumps({
        "schema": "hard5-native-q4-direct-damage-terminal-v1",
        "arm": ARM_A,
        "endpoint_role": "ARM_A_PREDECLARED_TERMINAL_ENDPOINT",
        "final_label": "FIELD_BUDGET_NOT_CLOSED",
        "terminal_outer": 6,
        "fem_proximity": proximity_receipt(),
        "proximity_identity": prox_identity,
        "provenance": identity,
        "smoke_pass_receipt_sha256": smoke_sha256,
        "fresh_b0_start": True,
        "used_K0": 9e-4,
        "candidate_K0": 8e-4,
        "irreversibility_gp_max": 2e-6,
        "implementation_or_state_error": False,
    }))
    receipt_sha256 = hashlib.sha256(receipt.read_bytes()).hexdigest()
    assert validate_arm_b_trigger(
        receipt, receipt_sha256, identity, smoke_sha256, prox_identity
    )["arm"] == ARM_A
    data = json.loads(receipt.read_text())
    data["candidate_K0"] = 2e-3
    receipt.write_text(json.dumps(data))
    with pytest.raises(RuntimeError, match="trigger is not satisfied"):
        validate_arm_b_trigger(
            receipt, hashlib.sha256(receipt.read_bytes()).hexdigest(), identity,
            smoke_sha256, prox_identity
        )


def test_arm_b_trigger_rejects_stale_provenance_and_wrong_receipt_hash(tmp_path):
    identity = {"runner_sha256": "runner", "b0_identity_sha256": "b0"}
    prox_identity = proximity_identity()
    payload = {
        "schema": "hard5-native-q4-direct-damage-terminal-v1",
        "arm": ARM_A,
        "endpoint_role": "ARM_A_PREDECLARED_TERMINAL_ENDPOINT",
        "final_label": "FIELD_BUDGET_NOT_CLOSED",
        "terminal_outer": 6,
        "fem_proximity": proximity_receipt(),
        "proximity_identity": prox_identity,
        "provenance": {**identity, "b0_identity_sha256": "stale"},
        "smoke_pass_receipt_sha256": "smoke",
        "fresh_b0_start": True,
        "used_K0": 9e-4,
        "candidate_K0": 8e-4,
        "irreversibility_gp_max": 2e-6,
        "implementation_or_state_error": False,
    }
    receipt = tmp_path / "arm_a.json"
    receipt.write_text(json.dumps(payload))
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        validate_arm_b_trigger(receipt, "0" * 64, identity, "smoke", prox_identity)
    with pytest.raises(RuntimeError, match="identity mismatch"):
        validate_arm_b_trigger(receipt, _sha256(receipt), identity, "smoke", prox_identity)


def test_arm_b_trigger_rejects_stale_proximity_identity(tmp_path):
    identity = {"runner_sha256": "runner", "b0_identity_sha256": "b0"}
    expected_proximity = proximity_identity()
    payload = {
        "schema": "hard5-native-q4-direct-damage-terminal-v1", "arm": ARM_A,
        "endpoint_role": "ARM_A_PREDECLARED_TERMINAL_ENDPOINT",
        "final_label": "FIELD_BUDGET_NOT_CLOSED", "terminal_outer": 6,
        "fem_proximity": proximity_receipt(),
        "proximity_identity": proximity_identity(fem_sha="stale-fem"),
        "provenance": identity, "smoke_pass_receipt_sha256": "smoke",
        "fresh_b0_start": True, "used_K0": 9e-4, "candidate_K0": 8e-4,
        "irreversibility_gp_max": 2e-6, "implementation_or_state_error": False,
    }
    receipt = tmp_path / "arm_a.json"
    receipt.write_text(json.dumps(payload))
    with pytest.raises(RuntimeError, match="identity mismatch"):
        validate_arm_b_trigger(
            receipt, _sha256(receipt), identity, "smoke", expected_proximity
        )


@pytest.mark.parametrize(
    "final_label,proximity,match",
    [
        ("PHYSICAL_FIXED_POINT_CLOSED", proximity_receipt(), "closed endpoint"),
        ("PHYSICAL_FIXED_POINT_CLOSED",
         {**proximity_receipt("CLOSED_FEM_PROXIMITY_PASS"),
          "proximity_qualification_pass": False}, "closed endpoint"),
        ("FIELD_BUDGET_NOT_CLOSED",
         {**proximity_receipt("UNCLOSED_DESCRIPTIVE_ONLY"),
          "proximity_qualification_pass": True}, "unclosed endpoint"),
    ],
)
def test_arm_b_trigger_rejects_endpoint_proximity_label_mismatch(
        tmp_path, final_label, proximity, match):
    identity = {"runner_sha256": "runner", "b0_identity_sha256": "b0"}
    prox_identity = proximity_identity()
    payload = {
        "schema": "hard5-native-q4-direct-damage-terminal-v1", "arm": ARM_A,
        "endpoint_role": "ARM_A_PREDECLARED_TERMINAL_ENDPOINT",
        "final_label": final_label, "terminal_outer": 3,
        "fem_proximity": proximity, "proximity_identity": prox_identity,
        "provenance": identity, "smoke_pass_receipt_sha256": "smoke",
        "fresh_b0_start": True, "used_K0": 9e-4, "candidate_K0": 8e-4,
        "irreversibility_gp_max": 2e-6, "implementation_or_state_error": False,
    }
    receipt = tmp_path / "arm_a.json"
    receipt.write_text(json.dumps(payload))
    with pytest.raises(RuntimeError, match=match):
        validate_arm_b_trigger(
            receipt, _sha256(receipt), identity, "smoke", prox_identity
        )


@pytest.mark.parametrize(
    "label,qualification",
    [("CLOSED_FEM_PROXIMITY_PASS", True), ("CLOSED_FEM_PROXIMITY_FAIL", False)],
)
def test_arm_b_trigger_accepts_consistent_closed_proximity_decision(
        tmp_path, label, qualification):
    identity = {"runner_sha256": "runner", "b0_identity_sha256": "b0"}
    prox_identity = proximity_identity()
    proximity = {**proximity_receipt(label),
                 "proximity_qualification_pass": qualification}
    payload = {
        "schema": "hard5-native-q4-direct-damage-terminal-v1", "arm": ARM_A,
        "endpoint_role": "ARM_A_PREDECLARED_TERMINAL_ENDPOINT",
        "final_label": "PHYSICAL_FIXED_POINT_CLOSED", "terminal_outer": 3,
        "fem_proximity": proximity, "proximity_identity": prox_identity,
        "provenance": identity, "smoke_pass_receipt_sha256": "smoke",
        "fresh_b0_start": True, "used_K0": 9e-4, "candidate_K0": 8e-4,
        "irreversibility_gp_max": 2e-6, "implementation_or_state_error": False,
    }
    receipt = tmp_path / "arm_a.json"
    receipt.write_text(json.dumps(payload))
    assert validate_arm_b_trigger(
        receipt, _sha256(receipt), identity, "smoke", prox_identity
    )["fem_proximity"]["proximity_label"] == label


def test_fixed_problem_counts_every_objective_gradient_evaluation():
    inp, cells, area, u, v, accepted, damage, fatigue, mat, model = patch()
    scale = 1.0
    problem = FixedDamageProblem(
        inp, cells, area, u, v, accepted, fatigue, mat, model, scale,
        torch.zeros_like(damage), 3,
    )
    x = damage.numpy()
    problem.value_gradient(x)
    problem.value_gradient(x + 1e-4)
    assert problem.evaluations == 2
    assert [row["evaluation"] for row in problem.records] == [1, 2]
    assert all(not row["accepted"] for row in problem.records)


def test_lbfgsb_known_zero_damage_solution_has_strict_KKT():
    pytest.importorskip("scipy")
    inp, cells, area, u, v, accepted, damage, fatigue, mat, model = patch()
    # Zero strain, zero accepted damage: AT1 fracture energy is minimized at d=0.
    u = 1e-5 * inp[:, 0]
    v = 1e-5 * inp[:, 1]
    accepted = torch.zeros_like(accepted)
    initial = torch.full_like(damage, 0.2)
    scale = 1.0
    problem = FixedDamageProblem(
        inp, cells, area, u, v, accepted, fatigue, mat, model, scale,
        torch.zeros_like(initial), 200,
    )
    result = solve_damage_block(
        problem, initial.numpy(), check_iterations=1, k_floor=1e-10,
        entry_ratio=0.0, required_consecutive=2,
    )
    assert result["final_K_lb"] <= 1e-8
    assert np.max(np.abs(result["damage"])) <= 1e-8
    assert result["accepted_nonzero_iterations"] >= 1
    assert result["evaluations"] == len(result["evaluation_trace"])


def test_evaluation_cap_returns_complete_last_accepted_tuple(monkeypatch):
    pytest.importorskip("scipy")

    class BudgetProblem:
        def __init__(self):
            self.lower = torch.zeros(2, dtype=torch.float64)
            self.scale = 1.0
            self.max_evaluations = 2
            self.evaluations = 0
            self.records = []
            self._last_x = self._last_value = self._last_gradient = None

        def value_gradient(self, x):
            from run_native_q4_direct_q4_damage import EvaluationBudgetExceeded
            if self.evaluations >= self.max_evaluations:
                raise EvaluationBudgetExceeded
            x = np.asarray(x, dtype=np.float64)
            value, gradient = float(x @ x), 2.0 * x
            self.evaluations += 1
            self.records.append({"evaluation": self.evaluations, "accepted": False})
            self._last_x = x.copy()
            self._last_value = value
            self._last_gradient = gradient.copy()
            return value, gradient

        def cached_or_evaluate(self, x):
            x = np.asarray(x, dtype=np.float64)
            if self._last_x is not None and np.array_equal(x, self._last_x):
                return self._last_value, self._last_gradient
            return self.value_gradient(x)

    def fake_minimize(fun, _initial, **_kwargs):
        fun(np.array([0.4, 0.4]))  # consumes the final allowed evaluation
        return SimpleNamespace(x=np.array([0.3, 0.3]), success=False, message="cap")

    monkeypatch.setattr("scipy.optimize.minimize", fake_minimize)
    result = solve_damage_block(BudgetProblem(), np.array([0.5, 0.5]), check_iterations=1)
    np.testing.assert_array_equal(result["damage"], np.array([0.5, 0.5]))
    assert result["objective"] == pytest.approx(0.5)
    np.testing.assert_array_equal(result["gradient"], np.array([1.0, 1.0]))
    assert result["termination"] == "EVALUATION_CAP_NOT_PHYSICAL_CLOSE"


def test_smoke_progress_allows_zero_steps_only_when_initial_kkt_is_closed():
    assert smoke_progress_ok(9e-4, 0)
    assert not smoke_progress_ok(2e-3, 0)
    assert smoke_progress_ok(2e-3, 1)


def test_smoke_pass_receipt_locks_identity_caps_and_nonzero_progress(tmp_path):
    identity = {"runner_sha256": "runner", "b0_identity_sha256": "b0"}
    receipt = tmp_path / "smoke.json"
    payload = {
        "schema": "hard5-native-q4-direct-damage-smoke-v1",
        "label": "FULL_MESH_FIXED_UV_F_SMOKE_PASS",
        "evaluation_cap": 200,
        "accepted_iteration_cap": 50,
        "accepted_state_unchanged": True,
        "fresh_b0_required_for_production": True,
        "energy_nonincrease": True,
        "bounds_ok": True,
        "gradient_ok": True,
        "progress_ok": True,
        "abnormal_line_search": False,
        "initial_kkt_closed": False,
        "accepted_nonzero_iterations": 1,
        "accepted_iterations": 1,
        "evaluations": 3,
        "initial_objective": 2.0,
        "final_objective": 1.0,
        "entry_K0": 2e-3,
        "final_K0": 9e-4,
        **identity,
    }
    receipt.write_text(json.dumps(payload))
    assert validate_smoke_pass_receipt(receipt, identity)["label"].endswith("PASS")
    payload["accepted_nonzero_iterations"] = 0
    receipt.write_text(json.dumps(payload))
    with pytest.raises(RuntimeError, match="no valid nonzero accepted step"):
        validate_smoke_pass_receipt(receipt, identity)
    payload["initial_kkt_closed"] = True
    payload["evaluation_cap"] = 20
    receipt.write_text(json.dumps(payload))
    with pytest.raises(RuntimeError, match="stale or invalid"):
        validate_smoke_pass_receipt(receipt, identity)


def test_stagnation_uses_best_value_in_five_round_window():
    assert not stagnation_reached([100.0, 80.0, 70.0, 95.0, 110.0])
    assert stagnation_reached([100.0, 99.8, 99.6, 99.4, 99.2])
    assert not stagnation_reached([0.9, 0.9, 0.9, 0.9, 0.9])


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_locked_fem_proximity_gate_and_unclosed_semantics(tmp_path):
    weights = np.ones((1, 4), dtype=np.float64)
    fem_path = tmp_path / "fem.npz"
    comparator_path = tmp_path / "comparator.npz"
    np.savez_compressed(
        fem_path,
        psi_active_gp=np.ones((1, 4)), damage_gp=np.full((1, 4), 0.5), det_j=weights,
    )
    np.savez_compressed(
        comparator_path,
        psi_active_gp=np.full((1, 4), 2.0), damage_gp=np.full((1, 4), 0.6),
        det_j=weights,
    )
    assets = load_proximity_assets(
        comparator_path=comparator_path,
        comparator_label="adaptive_final_C9600",
        comparator_sha256=_sha256(comparator_path),
        fem_path=fem_path,
        fem_label="fem_c83_peak",
        fem_sha256=_sha256(fem_path),
    )
    locked_identity = build_proximity_identity(assets)
    assert locked_identity["comparator_label"] == "adaptive_final_C9600"
    assert locked_identity["comparator_sha256"] == _sha256(comparator_path)
    assert locked_identity["fem_reference_sha256"] == _sha256(fem_path)
    assert len(locked_identity["proximity_identity_sha256"]) == 64
    new = {
        "psi_active_gp": np.full((1, 4), 1.5),
        "damage_gp": np.full((1, 4), 0.6),
        "det_j": weights,
    }
    closed = evaluate_fem_proximity(new, assets, closed_endpoint=True)
    assert closed["proximity_label"] == "CLOSED_FEM_PROXIMITY_PASS"
    assert closed["proximity_qualification_pass"]
    unclosed = evaluate_fem_proximity(new, assets, closed_endpoint=False)
    assert unclosed["proximity_label"] == "UNCLOSED_DESCRIPTIVE_ONLY"
    assert not unclosed["proximity_qualification_pass"]


def test_production_asset_lock_fails_on_wrong_hash_or_comparator_label(tmp_path):
    path = tmp_path / "asset.npz"
    np.savez_compressed(
        path, psi_active_gp=np.ones((1, 4)), damage_gp=np.ones((1, 4)),
        det_j=np.ones((1, 4)),
    )
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        load_proximity_assets(
            comparator_path=path, comparator_label="adaptive_final_C9600",
            comparator_sha256="0" * 64, fem_path=path, fem_label="fem",
            fem_sha256=_sha256(path),
        )
    with pytest.raises(ValueError, match="comparator label"):
        load_proximity_assets(
            comparator_path=path, comparator_label="wrong",
            comparator_sha256=_sha256(path), fem_path=path, fem_label="fem",
            fem_sha256=_sha256(path),
        )
