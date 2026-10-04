from __future__ import annotations

import json
import sys
from pathlib import Path

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
    direct_gradient,
    kkt_metrics,
    projected_kkt_map,
    solve_damage_block,
    validate_arm_b_trigger,
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
    receipt = tmp_path / "arm_a.json"
    receipt.write_text(json.dumps({
        "arm": ARM_A,
        "used_K0": 9e-4,
        "candidate_K0": 8e-4,
        "irreversibility_gp_max": 2e-6,
        "implementation_or_state_error": False,
    }))
    assert validate_arm_b_trigger(receipt)["arm"] == ARM_A
    data = json.loads(receipt.read_text())
    data["candidate_K0"] = 2e-3
    receipt.write_text(json.dumps(data))
    with pytest.raises(RuntimeError, match="trigger is not satisfied"):
        validate_arm_b_trigger(receipt)


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
    assert result["evaluations"] == len(result["evaluation_trace"])
