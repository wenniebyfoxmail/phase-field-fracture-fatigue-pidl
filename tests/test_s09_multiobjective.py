import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_multiobjective import (
    data_anchored_projected_direction, gradient_statistics,
    linearized_changes, normalized_sum_direction, weighted_sum_direction,
)


def test_gradient_statistics_reports_scale_and_conflict():
    p1 = torch.nn.Parameter(torch.zeros(2))
    p2 = torch.nn.Parameter(torch.zeros(1))
    named = [("encoder.weight", p1), ("decoder.bias", p2)]
    gd = (torch.tensor([1.0, 0.0]), torch.tensor([1.0]))
    gp = (torch.tensor([-2.0, 0.0]), torch.tensor([0.0]))
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
        direction = data_anchored_projected_direction(gd, gp)
        change = linearized_changes(gd, gp, direction)
        assert change["delta_data_per_unit_lr"] <= 0


def test_weighted_direction_and_linearized_signs():
    gd = (torch.tensor([1.0, 0.0]),)
    gp = (torch.tensor([-10.0, 1.0]),)
    direction = weighted_sum_direction(gd, gp, 0.2)
    changes = linearized_changes(gd, gp, direction)
    assert changes["delta_data_per_unit_lr"] > 0
    assert changes["delta_physics_per_unit_lr"] < 0

