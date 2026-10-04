import sys
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
SENS = ROOT / "SENS_tensile"
sys.path.insert(0, str(SENS))

from run_native_q4_smooth_b0_picard import (  # noqa: E402
    AnchoredSmoothDamage,
    project_box_kkt_gradient,
    small_derivative_set,
    squared_residual_share,
)


def test_anchor_matches_hard_b0_with_frozen_float64_buffers():
    raw0 = torch.tensor([-4.0, -2.0, -1.0, 0.0, 1.0, 2.0, 4.0], dtype=torch.float32)
    mapping = AnchoredSmoothDamage(raw0, epsilon=1e-7)
    actual = mapping(raw0)
    hard = (raw0 / 4.0 + 0.5).clamp(0.0, 1.0)
    assert float((actual - hard).abs().max()) <= 2e-7
    assert torch.all((actual > 0.0) & (actual < 1.0))
    assert mapping.r0.dtype == torch.float64
    assert mapping.anchor_logit.dtype == torch.float64
    assert all(not buffer.requires_grad for buffer in mapping.buffers())


def test_initial_derivative_matches_legacy_and_boundary_is_central():
    raw0 = torch.tensor([-3.0, -2.0, -1.0, 2.0, 3.0], dtype=torch.float64)
    raw = raw0.clone().requires_grad_(True)
    mapping = AnchoredSmoothDamage(raw0, epsilon=1e-7)
    mapping(raw).sum().backward()
    expected = torch.tensor([1e-3, 0.25, 0.25, 0.25, 1e-3], dtype=torch.float64)
    torch.testing.assert_close(raw.grad, expected, rtol=2e-5, atol=1e-12)
    assert mapping.legacy_slope[1].item() == 0.25
    assert mapping.legacy_slope[3].item() == 0.25


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
