import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e009_four_arm import ARM_ANCHOR_25, amplitude_auc, arm_direction  # noqa: E402
from s09_e010_support_amplitude import (  # noqa: E402
    ARM_A25,
    ARM_B0,
    ARM_B25,
    BALANCED_OBJECTIVE_ORDER,
    DAMAGE_SCALE,
    PRIMARY_PAIR_SCORE_DELTA,
    SUPPORT_THRESHOLD,
    balanced_direction,
    balanced_direction_components,
    balanced_objectives,
    classify_e010,
    support_amplitude_losses,
    three_arm_direction,
)


def direct_losses(predicted, target, pre, weight):
    p = np.asarray(predicted) - np.asarray(pre)
    t = np.asarray(target) - np.asarray(pre)
    w = np.asarray(weight)
    mask = t > SUPPORT_THRESHOLD
    support = np.sum(w[mask] * ((p[mask] - t[mask]) / DAMAGE_SCALE) ** 2) / np.sum(
        w[mask]
    )
    p_amp = np.sum(w * np.abs(p)) / np.sum(w)
    t_amp = np.sum(w * np.abs(t)) / np.sum(w)
    amplitude = ((p_amp - t_amp) / DAMAGE_SCALE) ** 2
    return support, amplitude, p_amp, t_amp


def test_support_and_amplitude_losses_match_direct_per_cycle_calculation():
    predicted = torch.tensor(
        [0.1, 0.25, 0.31, 0.2], dtype=torch.float64, requires_grad=True
    )
    target = torch.tensor([0.1, 0.2, 0.4, 0.2], dtype=torch.float64)
    pre = torch.tensor([0.1, 0.2, 0.3, 0.2], dtype=torch.float64)
    weight = torch.tensor([1.0, 2.0, 3.0, 4.0], dtype=torch.float64)
    losses, record = support_amplitude_losses(
        predicted_peak=predicted,
        target_peak=target,
        damage_pre=pre,
        nodal_weight=weight,
    )
    expected = direct_losses(
        predicted.detach().numpy(), target.numpy(), pre.numpy(), weight.numpy()
    )
    assert losses["L_S"].item() == pytest.approx(expected[0])
    assert losses["L_A"].item() == pytest.approx(expected[1])
    assert record["predicted_amplitude"] == pytest.approx(expected[2])
    assert record["target_amplitude"] == pytest.approx(expected[3])
    assert record["support_node_count"] == 1
    amplitude_gradient = torch.autograd.grad(
        losses["L_A"], predicted, retain_graph=True
    )[0]
    assert torch.isfinite(amplitude_gradient).all()
    assert torch.count_nonzero(amplitude_gradient) > 0
    total = losses["L_S"] + losses["L_A"]
    gradient = torch.autograd.grad(total, predicted)[0]
    assert torch.isfinite(gradient).all()
    assert torch.count_nonzero(gradient) > 0


@pytest.mark.parametrize(
    ("target", "weight", "message"),
    [
        ([0.1, 0.2], [1.0, 1.0], "support is empty"),
        ([0.1, 0.3], [0.0, 0.0], "weight sum"),
        ([0.1, float("nan")], [1.0, 1.0], "nonfinite"),
    ],
)
def test_support_amplitude_invalid_inputs_fail_closed(target, weight, message):
    with pytest.raises((ValueError, FloatingPointError), match=message):
        support_amplitude_losses(
            predicted_peak=torch.tensor([0.1, 0.2], dtype=torch.float64),
            target_peak=torch.tensor(target, dtype=torch.float64),
            damage_pre=torch.tensor([0.1, 0.2], dtype=torch.float64),
            nodal_weight=torch.tensor(weight, dtype=torch.float64),
        )


def test_zero_increment_declares_zero_amplitude_gradient_but_active_support_gradient():
    predicted = torch.tensor([0.1, 0.2, 0.3], dtype=torch.float64, requires_grad=True)
    pre = torch.tensor([0.1, 0.2, 0.3], dtype=torch.float64)
    target = torch.tensor([0.1, 0.25, 0.3], dtype=torch.float64)
    losses, _ = support_amplitude_losses(
        predicted_peak=predicted,
        target_peak=target,
        damage_pre=pre,
        nodal_weight=torch.ones(3, dtype=torch.float64),
    )
    g_support = torch.autograd.grad(losses["L_S"], predicted, retain_graph=True)[0]
    g_amplitude = torch.autograd.grad(losses["L_A"], predicted)[0]
    assert torch.count_nonzero(g_support) > 0
    assert torch.count_nonzero(g_amplitude) == 0


def gradients(**overrides):
    values = {
        "L_D": (1.0, 0.0),
        "L_S": (-1.0, 1.0),
        "L_A": (0.0, 2.0),
        "L_U": (1.0, 1.0),
        "L_H": (-1.0, 0.0),
        "L_P": (-1.0, 2.0),
    }
    values.update(overrides)
    return {
        name: torch.tensor(values[name], dtype=torch.float64)
        for name in BALANCED_OBJECTIVE_ORDER
    }


def test_balanced_components_are_norm_matched_and_nonconflicting():
    source = gradients()
    components, record = balanced_direction_components(source)
    anchor_norm = source["L_D"].norm()
    for name in ("L_S", "L_A", "L_U", "L_H", "L_P"):
        assert components[name].norm() <= anchor_norm * 2**0.5 + 1e-12
        assert source["L_D"].dot(components[name]) >= -1e-12
        assert record["auxiliary"][name]["anchor_dot_projected"] >= -1e-12


def test_b25_minus_b0_is_exactly_quarter_physics_before_clip():
    source = gradients()
    components, _ = balanced_direction_components(source)
    pre_b0 = sum(components[name] for name in ("L_D", "L_S", "L_A", "L_U", "L_H"))
    pre_b25 = pre_b0 + 0.25 * components["L_P"]
    torch.testing.assert_close(
        pre_b25 - pre_b0, 0.25 * components["L_P"], rtol=1e-15, atol=1e-15
    )
    b0, record0 = balanced_direction(source, beta=0.0)
    b25, record25 = balanced_direction(source, beta=0.25)
    assert torch.isfinite(b0).all() and torch.isfinite(b25).all()
    assert record0["clip_count_for_complete_direction"] == 1
    assert record25["clip_count_for_complete_direction"] == 1
    assert b0.norm() <= 1 + 1e-12 and b25.norm() <= 1 + 1e-12


def test_zero_auxiliary_is_declared_without_changing_anchor():
    source = gradients(
        L_S=(0.0, 0.0), L_A=(0.0, 0.0), L_U=(0.0, 0.0), L_H=(0.0, 0.0), L_P=(0.0, 0.0)
    )
    direction, record = balanced_direction(source, beta=0.25)
    torch.testing.assert_close(direction, source["L_D"], rtol=0, atol=0)
    assert all(
        value["zero_reason"] == "AUXILIARY_NORM_AT_OR_BELOW_EPSILON"
        for value in record["auxiliary"].values()
    )


def toy_losses(model):
    x = torch.tensor([[1.0, -2.0]], dtype=torch.float64)
    y = model(x).sum()
    atomic = {
        "l_d": (y - 1).square(),
        "l_dr": (y + 0.5).square(),
        "l_u": (2 * y - 1).square(),
        "l_h": (y + 1).square(),
        "l_hr": (3 * y - 1).square(),
        "L_P": (y - 2).square(),
    }
    additions = {"L_S": (4 * y - 1).square(), "L_A": (5 * y + 1).square()}
    return atomic, additions


def test_a25_arm_is_bitwise_exact_e009_replay():
    first = torch.nn.Linear(2, 1, bias=True).double()
    second = torch.nn.Linear(2, 1, bias=True).double()
    second.load_state_dict(first.state_dict())
    atomic_first, additions = toy_losses(first)
    atomic_second, _ = toy_losses(second)
    expected, _ = arm_direction(first, atomic_first, ARM_ANCHOR_25)
    observed, record = three_arm_direction(second, atomic_second, additions, ARM_A25)
    torch.testing.assert_close(observed, expected, rtol=0, atol=0)
    assert record["exact_e009_a25_replay"] is True
    assert record["clip_count_for_complete_direction"] == 1


@pytest.mark.parametrize("arm", [ARM_B25, ARM_B0])
def test_balanced_arms_are_finite_clipped_and_reach_parameters(arm):
    model = torch.nn.Linear(2, 1, bias=True).double()
    atomic, additions = toy_losses(model)
    objectives = balanced_objectives(atomic, additions)
    assert tuple(objectives) == BALANCED_OBJECTIVE_ORDER
    direction, record = three_arm_direction(model, atomic, additions, arm)
    assert direction.numel() == sum(
        parameter.numel() for parameter in model.parameters()
    )
    assert torch.isfinite(direction).all()
    assert direction.norm() <= 1 + 1e-12
    assert record["clip_count_for_complete_direction"] == 1
    assert record["layout"]["objectives"]["L_S"]["unconnected_parameters"] == []
    assert record["layout"]["objectives"]["L_A"]["unconnected_parameters"] == []


def auc(wins, ties=0):
    losses = 25 - wins - ties
    return {
        "value": (wins + 0.5 * ties) / 25.0,
        "wins": wins,
        "ties": ties,
        "losses": losses,
    }


def score(value=1.0, auc_record=None):
    result = {
        name: value
        for name in ("G", "F", "L_P", "L_judge", "l_d", "l_dr", "l_u", "l_h", "l_hr")
    }
    result["amplitude_auc"] = auc_record or auc(10)
    return result


def test_classifier_uses_integer_pair_boundary_and_tradeoff_state():
    a25 = score(1.0, auc(17))
    replay = score(2.0, auc(17))
    below = score(1.0, auc(18, 1))  # delta pair score = 3
    result = classify_e010(b25=below, a25=a25, replay=replay, validity_status="VALID")
    assert result["primary"]["delta_pair_score"] == PRIMARY_PAIR_SCORE_DELTA - 1
    assert result["status"] == "NO_TARGETED_RANKING_SIGNAL"

    boundary = score(1.0, auc(19))  # delta pair score = 4
    boundary["F"] = 1.051
    result = classify_e010(
        b25=boundary, a25=a25, replay=replay, validity_status="VALID"
    )
    assert result["primary"]["delta_pair_score"] == PRIMARY_PAIR_SCORE_DELTA
    assert result["status"] == "TARGETED_RANKING_SIGNAL_WITH_TRADEOFF"


def test_classifier_cumulative_local_relative_and_nomination_levels():
    a25 = score(1.0, auc(17))
    replay = score(1.0, auc(17))
    local = score(1.0, auc(19))
    assert (
        classify_e010(b25=local, a25=a25, replay=replay, validity_status="VALID")[
            "status"
        ]
        == "BALANCED_LOCAL_REPAIR_SIGNAL"
    )

    relative_replay = score(1.0, auc(10))
    relative = score(0.5, auc(20))
    relative["G"] = 0.0006
    relative_replay["G"] = 0.001
    a25_relative = dict(relative)
    a25_relative["amplitude_auc"] = auc(18)
    assert (
        classify_e010(
            b25=relative,
            a25=a25_relative,
            replay=relative_replay,
            validity_status="VALID",
        )["status"]
        == "ORIGINAL_RELATIVE_REPAIR_SIGNAL"
    )
    relative["G"] = 0.0004
    assert (
        classify_e010(
            b25=relative,
            a25=a25_relative,
            replay=relative_replay,
            validity_status="VALID",
        )["status"]
        == "NOMINATE_CONFIRMATORY_P1"
    )


def test_classifier_canonicalises_auc_float_to_validated_pair_counts():
    a25 = score(0.5, auc(18))
    replay = score(1.0, auc(10))
    statuses = []
    replay_auc_values = []
    for supplied_value in (0.8, math.nextafter(0.8, 0.0)):
        candidate = score(
            0.5,
            {"value": supplied_value, "wins": 20, "ties": 0, "losses": 5},
        )
        candidate["G"] = 0.0004
        result = classify_e010(
            b25=candidate,
            a25=a25,
            replay=replay,
            validity_status="VALID",
        )
        statuses.append(result["status"])
        replay_auc_values.append(result["replay_relative"]["status"])

    assert statuses == ["NOMINATE_CONFIRMATORY_P1"] * 2
    assert replay_auc_values == ["NOMINATE_CONFIRMATORY_P1"] * 2


def test_classifier_rejects_auc_value_count_drift_and_serialises_strictly():
    b25, a25, replay = score(), score(), score()
    b25["amplitude_auc"] = {"value": 0.9, "wins": 10, "ties": 0, "losses": 15}
    with pytest.raises(ValueError, match="inconsistency"):
        classify_e010(b25=b25, a25=a25, replay=replay, validity_status="VALID")
    b25["amplitude_auc"] = amplitude_auc([2] * 5, [1] * 5)
    result = classify_e010(b25=b25, a25=a25, replay=replay, validity_status="VALID")
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("status", ["EXECUTION_INVALID", "METHOD_INAPPLICABLE"])
def test_classifier_validity_precedes_missing_performance_evidence(status):
    result = classify_e010(b25={}, a25={}, replay={}, validity_status=status)
    assert result["status"] == status
    assert result["primary"] is None
