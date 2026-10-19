from collections import OrderedDict

import torch

from s09_e014_common_direction import (
    ARM_CANDIDATE, ARM_CONTROL, aggregate_rank_gradient, common_directions,
    nullspace_local_secondary,
)


def test_aggregate_rank_gradient_matches_autograd() -> None:
    theta = torch.tensor([0.2, -0.3], dtype=torch.float64, requires_grad=True)
    jac = {1: torch.tensor([1.0, 0.0], dtype=torch.float64),
           2: torch.tensor([0.0, 2.0], dtype=torch.float64),
           3: torch.tensor([-1.0, 1.0], dtype=torch.float64)}
    values = {cycle: vector.dot(theta) for cycle, vector in jac.items()}
    pairs = ((1, 2), (3, 2))
    loss, gradient, _ = aggregate_rank_gradient(values, jac, pairs,
                                                 normaliser=1.0, temperature=.7)
    expected = torch.autograd.grad(sum(
        torch.nn.functional.softplus(-(values[g] - values[s]) / .7)
        for g, s in pairs) / len(pairs), theta)[0]
    assert torch.allclose(gradient, expected, atol=1e-12, rtol=1e-12)
    assert torch.isfinite(loss)


def test_nullspace_secondary_is_orthogonal_to_span() -> None:
    anchor = torch.tensor([1.0, 0.0, 0.0], dtype=torch.float64)
    global_gradient = torch.tensor([1.0, 1.0, 0.0], dtype=torch.float64)
    local_gradient = torch.tensor([2.0, 3.0, 4.0], dtype=torch.float64)
    projected, record = nullspace_local_secondary(anchor, global_gradient, local_gradient)
    assert torch.allclose(projected, torch.tensor([0.0, 0.0, 4.0 / (29.0**.5)],
                                                  dtype=torch.float64), atol=1e-12)
    assert abs(anchor.dot(projected)) < 1e-12
    assert abs(global_gradient.dot(projected)) < 1e-12
    assert record["gram_rank"] == 2


def test_common_candidate_adds_one_shared_secondary() -> None:
    gradients = OrderedDict((name, torch.tensor(value, dtype=torch.float64)) for name, value in (
        ("L_D", [1., 0., 0., 0.]), ("L_S", [0., 1., 0., 0.]),
        ("L_A", [0., 0., 1., 0.]), ("L_U", [1., 1., 0., 0.]),
        ("L_H", [0., 1., 1., 0.]), ("L_P", [1., 0., 1., 0.]),
    ))
    directions, components, record = common_directions(
        gradients, torch.tensor([0., 1., 0., 0.], dtype=torch.float64),
        torch.tensor([1., 1., 1., 1.], dtype=torch.float64))
    assert tuple(directions) == (ARM_CONTROL, ARM_CANDIDATE)
    assert components["local_secondary"].norm() > 0
    assert record["local_secondary"]["gram_rank"] == 2
    assert not torch.equal(directions[ARM_CONTROL], directions[ARM_CANDIDATE])
