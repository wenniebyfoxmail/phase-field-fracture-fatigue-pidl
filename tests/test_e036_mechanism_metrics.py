"""Artificial vectors/algebra only; no project network or optimization loop."""
import sys
from pathlib import Path
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/s04_e036"))
from mechanism_metrics import gradient_balance, direct_box_projection, projection_receipt, clipped_descent_receipt


def test_regularizer_can_cancel_or_reverse_physical_gradient():
    a = [torch.tensor([2., -1., 0.], dtype=torch.float64)]
    b = [torch.tensor([-2., 2., 3.], dtype=torch.float64)]
    report = gradient_balance(a, b, [a[0] + b[0]])
    assert report["rprop_sign_changed_coordinates"] == 2
    assert report["physical_gradient_l1_mass_with_changed_sign"] == 1.
    assert report["analytic_sum_to_actual_total_l2"] == 0.
    assert report["physical_regularizer_cosine"] < 0


def test_zero_gradient_is_undefined_not_perfect_alignment():
    report = gradient_balance([torch.zeros(3)], [torch.zeros(3)], [torch.zeros(3)])
    assert report["physical_regularizer_cosine"] is None
    assert report["cancellation_ratio"] is None
    assert report["rprop_sign_changed_fraction"] is None


def test_projection_preserves_feasible_values_and_records_changes():
    raw = torch.tensor([-.1, .3, 1.1, .7], dtype=torch.float64, requires_grad=True)
    lower = torch.tensor([0., .2, 0., 1.], dtype=torch.float64)
    projected = direct_box_projection(raw, lower)
    assert torch.equal(projected, torch.tensor([0., .3, 1., 1.], dtype=torch.float64))
    projected.sum().backward()
    assert torch.equal(raw.grad, torch.tensor([0., 1., 0., 0.], dtype=torch.float64))
    report = projection_receipt(raw, projected, lower)
    assert report["raw_below_lower_nodes"] == 2
    assert report["raw_above_upper_nodes"] == 1
    assert report["changed_function_family"] is True


def test_projection_does_not_accept_a_differentiable_or_infeasible_old_state():
    raw = torch.zeros(2)
    with pytest.raises(ValueError, match="immutable"):
        direct_box_projection(raw, torch.zeros(2, requires_grad=True))
    with pytest.raises(ValueError, match="immutable"):
        direct_box_projection(raw, torch.tensor([0., 1.01]))


def test_collapsed_damage_interval_has_zero_derivative_even_at_equality():
    raw = torch.tensor([1.], requires_grad=True)
    direct_box_projection(raw, torch.ones(1)).sum().backward()
    assert torch.equal(raw.grad, torch.zeros(1))


def test_trainable_activation_scaling_is_a_field_preserving_gauge():
    # Verify the algebra m*(W*x+b), without constructing any project network.
    w = torch.tensor([[1., 2.], [-3., 4.]], dtype=torch.float64)
    x = torch.tensor([.25, -.5], dtype=torch.float64)
    b = torch.tensor([.1, -.3], dtype=torch.float64)
    m, scale = 2., .125
    pre = m * (w @ x + b)
    rescaled = (m / scale) * ((scale * w) @ x + scale * b)
    assert torch.equal(pre, rescaled)
    assert torch.sum((scale * w) ** 2) == scale ** 2 * torch.sum(w ** 2)


def test_clamp_does_not_hide_feasible_descent_in_parameter_stationarity_report():
    report = clipped_descent_receipt(torch.tensor([-.1, -.1, 1.1, 1.2]),
                                    torch.tensor([0., 0., 0., 1.]),
                                    torch.tensor([-3., 2., 4., 99.]))
    assert report["lower_tail_blocked_feasible_descent_nodes"] == 1
    assert report["upper_tail_blocked_feasible_descent_nodes"] == 1
    assert report["blocked_feasible_descent_force_l2"] == 5.
