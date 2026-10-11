import sys
from pathlib import Path

import torch
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_multiobjective import (
    data_anchored_projected_direction, gradient_statistics,
    linearized_changes, normalized_sum_direction,
    strict_balanced_projected_direction, weighted_sum_direction,
)


def test_gradient_statistics_reports_scale_and_conflict():
    named = [
        ("encoder.weight", torch.nn.Parameter(torch.zeros(2))),
        ("blocks.0.weight", torch.nn.Parameter(torch.zeros(1))),
        ("coarse.weight", torch.nn.Parameter(torch.zeros(1))),
        ("decoder.bias", torch.nn.Parameter(torch.zeros(1))),
    ]
    gd = (torch.tensor([1.0, 0.0]), torch.ones(1), torch.ones(1), torch.ones(1))
    gp = (torch.tensor([-2.0, 0.0]), torch.full((1,), .1),
          torch.full((1,), .1), torch.full((1,), .1))
    stats = gradient_statistics(named, gd, gp)
    assert stats["global"]["cosine"] < 0
    assert stats["encoder"]["physics_to_data_norm"] == 2.0


def test_normalized_sum_equalizes_objective_gradient_norms():
    gd = (torch.tensor([3.0, 4.0]),)
    gp = (torch.tensor([0.0, 2.0]),)
    direction = normalized_sum_direction(gd, gp)
    torch.testing.assert_close(direction[0], torch.tensor([0.6, 1.8]))


def test_projected_direction_never_increases_data_to_first_order():
    cases = [
        ((torch.tensor([1.0, 0.0]),), (torch.tensor([-2.0, 1.0]),)),
        ((torch.tensor([1.0, 1.0]),), (torch.tensor([2.0, 0.0]),)),
    ]
    for gd, gp in cases:
        direction, metadata = data_anchored_projected_direction(gd, gp)
        change = linearized_changes(gd, gp, direction)
        assert change["delta_data_per_unit_lr"] <= 0
        assert metadata["fallback_to_data_only"] is False


def test_weighted_direction_and_linearized_signs():
    gd = (torch.tensor([1.0, 0.0]),)
    gp = (torch.tensor([-10.0, 1.0]),)
    direction = weighted_sum_direction(gd, gp, 0.2)
    changes = linearized_changes(gd, gp, direction)
    assert changes["delta_data_per_unit_lr"] > 0
    assert changes["delta_physics_per_unit_lr"] < 0


def test_degenerate_gradients_fail_closed_and_antiparallel_falls_back():
    with pytest.raises(ValueError, match="data gradient norm"):
        normalized_sum_direction((torch.zeros(2),), (torch.ones(2),))
    with pytest.raises(ValueError, match="physics gradient norm"):
        normalized_sum_direction((torch.ones(2),), (torch.zeros(2),))
    direction, metadata = data_anchored_projected_direction(
        (torch.tensor([1.0, 0.0]),), (torch.tensor([-2.0, 0.0]),)
    )
    torch.testing.assert_close(direction[0], torch.tensor([1.0, 0.0]))
    assert metadata == {"conflict": True, "fallback_to_data_only": True,
                        "projected_physics_norm": 0.0}


def test_statistics_reject_missing_groups_length_shape_and_nonfinite():
    named = [("encoder.weight", torch.nn.Parameter(torch.zeros(2)))]
    with pytest.raises(ValueError, match="lengths differ"):
        gradient_statistics(named, (torch.ones(2),), ())
    with pytest.raises(ValueError, match="shape mismatch"):
        gradient_statistics(named, (torch.ones(3),), (torch.ones(2),))
    with pytest.raises(ValueError, match="non-finite"):
        gradient_statistics(named, (torch.tensor([float("nan"), 1.0]),), (torch.ones(2),))
    with pytest.raises(ValueError, match="missing declared parameter groups"):
        gradient_statistics(named, (torch.ones(2),), (torch.ones(2),))


def test_statistics_reject_unexpected_parameter_group():
    named = [("mystery.weight", torch.nn.Parameter(torch.zeros(1)))]
    with pytest.raises(ValueError, match="unexpected parameter group"):
        gradient_statistics(named, (torch.ones(1),), (torch.ones(1),))


def test_strict_balanced_projection_uses_global_norm_and_beta():
    gd = (torch.tensor([3.0, 4.0]), torch.tensor([0.0]))
    gp = (torch.tensor([0.0, 2.0]), torch.tensor([0.0]))
    direction, metadata = strict_balanced_projected_direction(gd, gp, 0.25)
    expected = torch.tensor([3.0, 5.25])
    torch.testing.assert_close(direction[0], expected)
    torch.testing.assert_close(direction[1], torch.tensor([0.0]))
    assert metadata["beta"] == 0.25
    assert metadata["conflict"] is False
    assert metadata["physics_norm"] == 2.0
    assert metadata["data_norm"] == 5.0


def test_strict_balanced_projection_removes_only_global_opposition():
    gd = (torch.tensor([1.0]), torch.tensor([1.0]))
    gp = (torch.tensor([-2.0]), torch.tensor([1.0]))
    direction, metadata = strict_balanced_projected_direction(gd, gp, 1.0)
    projected = torch.cat([direction[0] - gd[0], direction[1] - gd[1]])
    data = torch.cat(gd)
    torch.testing.assert_close(torch.dot(projected, data), torch.tensor(0.0), atol=1e-6, rtol=0)
    torch.testing.assert_close(torch.linalg.vector_norm(projected), torch.linalg.vector_norm(data))
    assert metadata["conflict"] is True


def test_strict_balanced_projection_fails_closed():
    with pytest.raises(ValueError, match="data gradient norm"):
        strict_balanced_projected_direction((torch.zeros(2),), (torch.ones(2),), 1.0)
    with pytest.raises(ValueError, match="physics gradient norm"):
        strict_balanced_projected_direction((torch.ones(2),), (torch.zeros(2),), 1.0)
    with pytest.raises(ValueError, match="projected physics gradient is degenerate"):
        strict_balanced_projected_direction(
            (torch.tensor([1.0, 0.0]),), (torch.tensor([-2.0, 0.0]),), 1.0
        )
    with pytest.raises(ValueError, match="beta"):
        strict_balanced_projected_direction((torch.ones(1),), (torch.ones(1),), 0.0)

