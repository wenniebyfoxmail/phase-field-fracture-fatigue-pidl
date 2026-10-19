from collections import OrderedDict

import torch

from s09_e014_common_direction import (
    ARM_CANDIDATE, ARM_CONTROL, aggregate_rank_gradient, common_directions,
    classify, nullspace_local_secondary,
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


def test_protected_ratio_uses_true_small_positive_denominator() -> None:
    control = {"local_pair_score": 34, "global_pair_score": 34,
               "G": 1e-31, "F": 1.0, "L_P": 1.0, "L_judge": 1.0,
               "finite": True, "hard_constraint_violations": 0}
    candidate = {**control, "local_pair_score": 35, "G": 2e-31}
    result = classify(True, control, candidate, valid=True)
    assert result["level"] == 4
    assert result["protected_ratios"]["G"] == 2.0
    assert result["protected_ratios_ok"] is False


def test_zero_denominator_does_not_default_to_protected_pass() -> None:
    control = {"local_pair_score": 34, "global_pair_score": 34,
               "G": 0.0, "F": 1.0, "L_P": 1.0, "L_judge": 1.0,
               "finite": True, "hard_constraint_violations": 0}
    candidate = {**control, "local_pair_score": 35, "G": 1e-12}
    result = classify(True, control, candidate, valid=True)
    assert result["level"] == 4
    assert result["protected_ratios"]["G"] is None

    both_zero = {**candidate, "G": 0.0}
    result_both_zero = classify(True, control, both_zero, valid=True)
    assert result_both_zero["level"] == 4
    assert result_both_zero["protected_ratios"]["G"] is None


def test_classifier_rejects_hard_constraint_even_if_valid_flag_is_true() -> None:
    control = {"local_pair_score": 34, "global_pair_score": 34,
               "G": 1.0, "F": 1.0, "L_P": 1.0, "L_judge": 1.0,
               "finite": True, "hard_constraint_violations": 1}
    candidate = {**control, "local_pair_score": 35,
                 "hard_constraint_violations": 0}
    result = classify(True, control, candidate, valid=True)
    assert result == {"level": 1, "status": "EXECUTION_INVALID"}
