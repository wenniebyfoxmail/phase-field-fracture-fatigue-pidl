import sys
import json
from pathlib import Path

import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
SENS = ROOT / "SENS_tensile"
sys.path.insert(0, str(SENS))

from run_native_q4_smooth_b0_picard import (  # noqa: E402
    AnchoredSmoothDamage,
    FROZEN_SOLVER_CONTRACT,
    fail_closed_step,
    project_box_kkt_gradient,
    small_derivative_set,
    squared_residual_share,
    validate_frozen_solver_contract,
    validate_smoke_pass_receipt,
    weighted_rel_change,
)
from compute_energy import compute_energy_per_elem, get_psi_plus_per_elem  # noqa: E402
from fatigue_history import compute_fatigue_degrad  # noqa: E402
from material_properties import MaterialProperties  # noqa: E402
from pff_model import PFFModel  # noqa: E402


def smoke_identity():
    return {
        "runner_sha256": "runner", "mesh_sha256": "mesh",
        "checkpoint_sha256": "checkpoint", "network_sha256": "network",
        "anchor_epsilon": 1e-7, "b0_match_atol": 2e-7,
        "solver_contract_sha256": "contract", "b0_audit_sha256": "audit",
        "anchor_identity_sha256": "anchor",
    }


def valid_smoke_receipt(expected):
    return {
        "schema": "hard5-native-q4-smooth-b0-smoke-v1",
        "status": "SMOKE_PASS", "uv_updates": 100, "damage_updates": 100,
        "b0_identity_status": "PASS", "accepted_state_unchanged": True,
        "anchor_read_only": True, "fresh_b0_required_for_production": True,
        "finite_contract_status": "PASS", "bounds_contract_status": "PASS",
        "positive_energy_contract_status": "PASS",
        "frozen_fields_contract_status": "PASS",
        "b0_nodal_max_abs": 1e-8, "b0_gp_max_abs": 1e-8,
        "b0_initial_derivative_max_relative_error": 1e-6,
        "b0_independent_physical_gradient_normalized_max": 1e-4,
        "b0_max_energy_component_abs_difference_over_E0": 1e-4,
        "b0_runtime_raw_increment_max_abs": 0.0,
        "used_rho_uv": 1.0, "candidate_rho_uv": 1.0,
        "used_rho_damage": 1.0, "candidate_rho_damage": 1.0,
        "used_chi_small": 0.1, "candidate_chi_small": 0.1,
        **expected,
    }


def test_anchor_matches_hard_b0_with_frozen_float64_buffers():
    raw0 = torch.tensor([-4.0, -2.0, -1.0, 0.0, 1.0, 2.0, 4.0], dtype=torch.float32)
    mapping = AnchoredSmoothDamage(raw0, epsilon=1e-7)
    actual = mapping(raw0)
    hard = (raw0 / 4.0 + 0.5).clamp(0.0, 1.0)
    assert float((actual - hard).abs().max()) <= 2e-7
    assert torch.all((actual > 0.0) & (actual < 1.0))
    assert actual.dtype == raw0.dtype
    assert mapping.r0.dtype == torch.float64
    assert mapping.anchor_logit.dtype == torch.float64
    assert all(not buffer.requires_grad for buffer in mapping.buffers())


def test_frozen_solver_contract_rejects_changed_load_budget_threshold_or_small_gate():
    from types import SimpleNamespace
    args = SimpleNamespace(**FROZEN_SOLVER_CONTRACT)
    validate_frozen_solver_contract(args)
    for key, changed in (
        ("peak_displacement", 0.05), ("max_outer", 13),
        ("outer_rho_tol", 1.0), ("small_residual_fraction", 0.9),
    ):
        candidate = SimpleNamespace(**FROZEN_SOLVER_CONTRACT)
        setattr(candidate, key, changed)
        with pytest.raises(ValueError, match="frozen solver contract mismatch"):
            validate_frozen_solver_contract(candidate)


def test_initial_derivative_matches_legacy_and_boundary_is_central():
    raw0 = torch.tensor([-3.0, -2.0, -1.0, 2.0, 3.0], dtype=torch.float64)
    raw = raw0.clone().requires_grad_(True)
    mapping = AnchoredSmoothDamage(raw0, epsilon=1e-7)
    mapping(raw).sum().backward()
    expected = torch.tensor([1e-3, 0.25, 0.25, 0.25, 1e-3], dtype=torch.float64)
    torch.testing.assert_close(raw.grad, expected, rtol=2e-5, atol=1e-12)
    assert mapping.legacy_slope[1].item() == 0.25
    assert mapping.legacy_slope[3].item() == 0.25


def test_runtime_float32_output_derivative_matches_frozen_float64_slope():
    raw0 = torch.tensor([-3.0, -2.0, -1.0, 2.0, 3.0], dtype=torch.float32)
    raw = raw0.clone().requires_grad_(True)
    mapping = AnchoredSmoothDamage(raw0, epsilon=1e-7)
    output = mapping(raw)
    output.sum().backward()
    expected = mapping.legacy_slope.to(torch.float32)
    relmax = float(((raw.grad - expected).abs() / expected.abs()).max())
    assert output.dtype == raw.dtype
    assert relmax <= 2e-5


def test_anchor_is_mesh_and_order_locked():
    mapping = AnchoredSmoothDamage(torch.tensor([-3.0, 0.0, 3.0]))
    try:
        mapping(torch.zeros(2))
    except RuntimeError as error:
        assert "mesh/order locked" in str(error)
    else:
        raise AssertionError("shape mismatch must fail")


def test_serialization_preserves_anchor_exactly():
    raw0 = torch.tensor([-3.0, -2.0, 0.0, 2.0, 3.0])
    first = AnchoredSmoothDamage(raw0)
    second = AnchoredSmoothDamage(torch.zeros_like(raw0))
    second.load_state_dict(first.state_dict())
    for name in ("r0", "hard_b0", "p", "legacy_slope", "anchor_logit", "anchor_scale"):
        assert torch.equal(getattr(first, name), getattr(second, name))
    assert torch.equal(first(raw0), second(raw0))


def test_independent_box_kkt_projection_contract_is_unchanged():
    damage = torch.tensor([0.0, 0.0, 0.5, 1.0, 1.0])
    gradient = torch.tensor([2.0, -3.0, 4.0, 5.0, -6.0])
    projected = project_box_kkt_gradient(damage, gradient, 1e-7)
    torch.testing.assert_close(projected, torch.tensor([0.0, -3.0, 4.0, 5.0, 0.0]))


def test_reblock_gate_uses_strict_relative_derivative_and_squared_residual_share():
    slope = torch.tensor([0.25, 0.25, 1e-3, 1e-3], dtype=torch.float64)
    derivative = torch.tensor([2.49e-4, 2.50e-4, 0.99e-6, 1.00e-6], dtype=torch.float64)
    mask = small_derivative_set(derivative, slope)
    assert torch.equal(mask, torch.tensor([True, False, True, False]))
    feasible = torch.tensor([3.0, 4.0, 0.0, 0.0])
    assert squared_residual_share(feasible, mask) == 9.0 / 25.0


def test_smooth_map_runs_complete_float32_q4_energy_and_history_path():
    points = torch.tensor(
        [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        dtype=torch.float32,
    )
    cells = torch.tensor([[0, 1, 2, 3]], dtype=torch.long)
    raw = torch.tensor([-3.0, -1.0, 1.0, 3.0], dtype=torch.float32,
                       requires_grad=True)
    damage = AnchoredSmoothDamage(raw.detach())(raw)
    u, v = 0.01 * points[:, 0], 0.02 * points[:, 1]
    accepted = torch.zeros(4, dtype=torch.float32)
    area = torch.ones(1, dtype=torch.float32)
    fatigue = torch.ones((1, 4), dtype=torch.float32)
    mat = MaterialProperties(1.0, 0.3, 1.0, 0.01)
    model = PFFModel("AT1", "volumetric", 5e-3, residual_stiffness=0.0)
    parts = compute_energy_per_elem(
        points, u, v, damage, accepted, mat, model, area, cells,
        f_fatigue=fatigue,
        irreversibility_penalty_cfg={"enable": True, "mode": "fem_gp_q4"},
    )
    total = sum(x.sum() for x in parts)
    total.backward()
    assert torch.isfinite(total) and raw.grad is not None and torch.isfinite(raw.grad).all()
    active = get_psi_plus_per_elem(
        points, u, v, damage.detach(), mat, model, area, cells,
        history_driver_reduction_dict={"enable": True, "mode": "native_q4_gp4"},
    )
    history = torch.relu(active)
    f = compute_fatigue_degrad(history, {
        "fatigue_on": True, "loading_type": "cyclic", "accum_type": "carrara",
        "degrad_type": "asymptotic", "alpha_T": 0.5,
        "spatial_alpha_T": {"enable": False},
    })
    assert active.shape == f.shape == (1, 4)
    assert active.dtype == f.dtype == torch.float32
    assert torch.isfinite(active).all() and torch.isfinite(f).all()


def test_weighted_fatigue_gap_uses_q4_weights():
    old = torch.tensor([[1.0, 2.0]], dtype=torch.float64)
    new = torch.tensor([[2.0, 2.0]], dtype=torch.float64)
    weights = torch.tensor([[4.0, 1.0]], dtype=torch.float64)
    assert weighted_rel_change(new, old, weights) == pytest.approx(2.0 / (8.0 ** 0.5))


def test_final_optimizer_step_that_poisons_parameter_fails_closed():
    parameter = torch.nn.Parameter(torch.tensor([1.0]))

    class PoisonFinalStep:
        param_groups = [{"params": [parameter]}]

        @staticmethod
        def zero_grad(set_to_none=True):
            parameter.grad = None

        @staticmethod
        def step():
            with torch.no_grad():
                parameter.fill_(float("nan"))

    with pytest.raises(RuntimeError, match="non-finite optimizer parameter"):
        fail_closed_step(PoisonFinalStep(), lambda: parameter.square().sum(), 1, [])


def test_production_receipt_is_exactly_bound_to_smoke_identity(tmp_path):
    expected = smoke_identity()
    receipt = tmp_path / "smoke.json"
    receipt.write_text(json.dumps(valid_smoke_receipt(expected)))
    assert validate_smoke_pass_receipt(receipt, expected)["status"] == "SMOKE_PASS"
    bad = json.loads(receipt.read_text())
    bad["runner_sha256"] = "stale"
    receipt.write_text(json.dumps(bad))
    with pytest.raises(RuntimeError, match="stale smooth-B0 smoke receipt"):
        validate_smoke_pass_receipt(receipt, expected)


def test_production_receipt_rejects_nonfinite_diagnostic(tmp_path):
    expected = smoke_identity()
    receipt = tmp_path / "smoke.json"
    payload = valid_smoke_receipt(expected)
    payload["used_rho_damage"] = float("nan")
    receipt.write_text(json.dumps(payload))
    with pytest.raises(RuntimeError, match="non-finite smoke receipt.used_rho_damage"):
        validate_smoke_pass_receipt(receipt, expected)


def test_production_receipt_requires_diagnostics_and_consistent_pass(tmp_path):
    expected = smoke_identity()
    receipt = tmp_path / "smoke.json"
    payload = valid_smoke_receipt(expected)
    del payload["candidate_chi_small"]
    receipt.write_text(json.dumps(payload))
    with pytest.raises(RuntimeError, match="missing diagnostics"):
        validate_smoke_pass_receipt(receipt, expected)
    payload = valid_smoke_receipt(expected)
    payload["used_chi_small"] = 0.5
    receipt.write_text(json.dumps(payload))
    with pytest.raises(RuntimeError, match="contradicts the reblock gate"):
        validate_smoke_pass_receipt(receipt, expected)
    payload = valid_smoke_receipt(expected)
    payload["b0_nodal_max_abs"] = 3e-7
    receipt.write_text(json.dumps(payload))
    with pytest.raises(RuntimeError, match="contradicts B0 PASS"):
        validate_smoke_pass_receipt(receipt, expected)
