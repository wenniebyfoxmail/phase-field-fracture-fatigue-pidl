import sys
import json
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_e009_four_arm import (
    AnchorStationary,
    amplitude_auc,
    arm_direction,
    classify_a25,
    damage_anchor_direction,
    fixed_support_median,
    frozen_tolerance,
    group_amplitude_ratio,
    grouped_losses,
    initialise_arm_states,
    parameter_displacement_alignment,
    safe_replay_ratio,
    scalar_data_direction,
    replay_losses,
)


def groups(d=(1.0, 0.0), u=(-1.0, 1e-14), h=(0.0, 2.0), p=(-1.0, 2.0)):
    return {name: torch.tensor(value, dtype=torch.float64)
            for name, value in zip(("L_D", "L_U", "L_H", "L_P"), (d, u, h, p))}


def test_anchor_equalises_before_projection_without_amplifying_residue():
    merged, record = damage_anchor_direction(groups(), beta=0.25)
    assert record["auxiliary"]["L_U"]["projected_norm"] == pytest.approx(1e-14)
    assert record["auxiliary"]["L_U"]["zero_reason"] == "PROJECTED_RESIDUAL_AT_OR_BELOW_EPSILON"
    assert record["preclip_anchor_dot_merged"] >= record["preclip_anchor_norm_squared"] - 1e-14
    assert torch.isfinite(merged).all()
    assert record["norm_after_clip"] <= 1.0 + 1e-12


def test_anchor_zero_policies_are_distinct():
    with pytest.raises(AnchorStationary, match="ANCHOR_STATIONARY"):
        damage_anchor_direction(groups(d=(0.0, 0.0)), beta=0.0)
    _, record = damage_anchor_direction(groups(h=(0.0, 0.0)), beta=0.0)
    assert record["auxiliary"]["L_H"]["zero_reason"] == "AUXILIARY_NORM_AT_OR_BELOW_EPSILON"
    with pytest.raises(FloatingPointError):
        damage_anchor_direction(groups(p=(float("nan"), 0.0)), beta=0.25)


def test_exact_zero_and_near_zero_projection_labels_are_distinct():
    _, exact = damage_anchor_direction(
        groups(u=(-1.0, 0.0), h=(0.0, 0.0), p=(0.0, 0.0)), beta=0.0)
    _, near = damage_anchor_direction(
        groups(u=(-1.0, 1e-14), h=(0.0, 0.0), p=(0.0, 0.0)), beta=0.0)
    assert exact["auxiliary"]["L_U"]["zero_reason"] == "FULLY_PROJECTED_TO_ZERO"
    assert near["auxiliary"]["L_U"]["zero_reason"] == (
        "PROJECTED_RESIDUAL_AT_OR_BELOW_EPSILON")


def test_scalar_uses_no_physics_contribution_and_one_clip():
    merged, record = scalar_data_direction(groups(d=(2.0, 0.0), u=(2.0, 0.0), h=(2.0, 0.0)))
    assert record["physics_gradient_evaluated"] is True
    assert record["physics_contribution_coefficient"] == 0
    assert record["clip_count_for_complete_direction"] == 1
    assert merged.norm() == pytest.approx(1.0)


def test_atomic_grouping_and_replay_keep_raw_damage_coefficient_one():
    values = {name: torch.tensor(float(index + 1), requires_grad=True)
              for index, name in enumerate(("l_d", "l_dr", "l_u", "l_h", "l_hr", "L_P"))}
    grouped = grouped_losses(values)
    replay = replay_losses(values)
    assert grouped["L_D"].item() == 3
    assert replay["J_N"].item() == pytest.approx((1 + 3) / 2 + 2)
    assert torch.autograd.grad(replay["J_N"], values["l_dr"])[0].item() == 1


def test_all_four_arm_directions_are_finite_and_clipped_on_toy_model():
    for arm in ("R_current_pino_replay", "S_data_only_scalar",
                "A0_damage_anchor_beta0", "A25_damage_anchor_beta0p25"):
        model = torch.nn.Linear(2, 1, bias=True).double()
        x = torch.tensor([[1.0, -2.0]], dtype=torch.float64)
        y = model(x).sum()
        losses = {
            "l_d": (y - 1).square(), "l_dr": (y + 0.5).square(),
            "l_u": (2 * y - 1).square(), "l_h": (y + 1).square(),
            "l_hr": (3 * y - 1).square(), "L_P": (y - 2).square(),
        }
        direction, record = arm_direction(model, losses, arm)
        assert torch.isfinite(direction).all()
        assert direction.norm() <= 1 + 1e-12
        assert record["clip_count_for_complete_direction"] == 1


def test_actual_displacement_alignment_can_disagree_with_pre_adam_geometry():
    g_d = torch.tensor([2.0, 1.0])
    before = torch.tensor([0.0, 0.0])
    after = torch.tensor([1.0, -1.0])
    result = parameter_displacement_alignment(g_d, before, after)
    assert result["g_D_dot_negative_delta_theta"] == pytest.approx(-1.0)
    assert result["cosine"] < 0


def test_arm_initialisation_is_byte_identical_disjoint_and_optimizer_empty():
    base = torch.nn.Sequential(torch.nn.Linear(2, 3), torch.nn.BatchNorm1d(3)).double()
    models, optimizers, record = initialise_arm_states(
        base, learning_rate=3e-4, betas=(0.9, 0.999),
        optimizer_epsilon=1e-8, weight_decay=0.0)
    assert len(set(record["initial_state_sha256"].values())) == 1
    assert record["optimizer_states_empty"] is True
    assert record["parameter_objects_disjoint"] is True
    assert all(not optimizer.state for optimizer in optimizers.values())
    with torch.no_grad():
        next(models["R_current_pino_replay"].parameters()).add_(1)
    assert not torch.equal(next(models["R_current_pino_replay"].parameters()),
                           next(models["S_data_only_scalar"].parameters()))


def test_amplitude_zero_rules_and_auc_ties():
    assert group_amplitude_ratio(0, 0)["status"] == "ZERO_AMPLITUDE_BOTH_GROUPS"
    assert group_amplitude_ratio(1, 0)["status"] == "ZERO_STAGNANT_AMPLITUDE"
    assert group_amplitude_ratio(2, 1)["value"] == 2
    assert amplitude_auc([0] * 5, [0] * 5) == {"value": 0.5, "wins": 0, "ties": 25, "losses": 0}


def test_numpy_scorecard_outputs_are_strict_json_serialisable():
    auc = amplitude_auc([np.float64(0)] * 5, [np.float64(0)] * 5)
    spatial = fixed_support_median(
        {np.int64(index): np.float64(index) for index in range(1, 17)},
        tuple(np.int64(index) for index in range(1, 17)))
    json.dumps({"auc": auc, "spatial": spatial}, allow_nan=False)
    assert all(type(auc[name]) is int for name in ("wins", "ties", "losses"))
    assert all(type(cycle) is int for cycle in spatial["valid_cycles"])


def test_large_finite_direction_uses_stable_norm_and_clip():
    from s09_e009_four_arm import clip_complete_direction

    direction = torch.tensor([1e200, 1e200], dtype=torch.float64)
    clipped, record = clip_complete_direction(direction)
    assert torch.isfinite(clipped).all()
    assert clipped.norm() == pytest.approx(1.0)
    assert record["norm_before_clip"] == pytest.approx(2 ** 0.5 * 1e200)


def test_large_finite_arm_gradients_never_return_nonfinite_direction():
    for arm in ("R_current_pino_replay", "S_data_only_scalar",
                "A0_damage_anchor_beta0", "A25_damage_anchor_beta0p25"):
        model = torch.nn.Linear(1, 1, bias=False).double()
        with torch.no_grad():
            model.weight.zero_()
        output = model(torch.ones((1, 1), dtype=torch.float64)).sum()
        losses = {name: (1 + 5e199 * output).square() for name in
                  ("l_d", "l_dr", "l_u", "l_h", "l_hr", "L_P")}
        try:
            direction, _ = arm_direction(model, losses, arm)
        except FloatingPointError:
            continue
        assert torch.isfinite(direction).all()


def test_replay_fails_closed_before_frozen_merger_norm_overflow():
    model = torch.nn.Linear(1, 1, bias=True).double()
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
    output = model(torch.ones((1, 1), dtype=torch.float64)).sum()
    losses = {name: (1 + 5e199 * output).square() for name in
              ("l_d", "l_dr", "l_u", "l_h", "l_hr", "L_P")}
    with pytest.raises(FloatingPointError, match="replay-merger boundary"):
        arm_direction(model, losses, "R_current_pino_replay")


def test_nonfinite_derived_diagnostics_fail_closed():
    with pytest.raises(FloatingPointError, match="displacement dot"):
        parameter_displacement_alignment(
            torch.tensor([1e200], dtype=torch.float64),
            torch.tensor([1e200], dtype=torch.float64),
            torch.tensor([-1e200], dtype=torch.float64))
    with pytest.raises(FloatingPointError, match="replay ratio"):
        safe_replay_ratio(1.0, 1e-320)
    with pytest.raises(FloatingPointError, match="group amplitude ratio"):
        group_amplitude_ratio(1.0, 1e-320)


def test_replay_ratio_undefined_propagation_inputs():
    assert safe_replay_ratio(0, 0) == {"value": 1.0, "status": "BOTH_ZERO"}
    assert safe_replay_ratio(1, 0)["value"] is None
    assert safe_replay_ratio(1, 0)["status"] == "REFERENCE_ZERO_CANDIDATE_POSITIVE"


def test_fixed_support_median_does_not_drop_na_from_primary():
    cycles = (1, 2, 3)
    complete = fixed_support_median({1: 0.1, 2: 0.2, 3: 0.3}, cycles)
    assert complete["primary_median"] == pytest.approx(0.2)
    partial = fixed_support_median({1: 0.1, 2: None, 3: 0.3}, cycles)
    assert partial["primary_median"] is None
    assert partial["valid_subset_median"] == pytest.approx(0.2)
    assert partial["valid_cycles"] == [1, 3]


def score(value=1.0):
    return {name: value for name in
            ("G", "F", "L_P", "L_judge", "l_d", "l_dr", "l_u", "l_h", "l_hr")}


def full_score(value=1.0, auc=0.5):
    result = score(value)
    result["AUC"] = auc
    return result


def test_decision_hierarchy_covers_no_repair_and_component_signal():
    replay = full_score()
    assert classify_a25(dict(replay), replay)["status"] == "NO_REPAIR_SIGNAL"
    candidate = dict(replay)
    candidate["l_d"] -= 2 * frozen_tolerance(replay["l_d"])
    assert classify_a25(candidate, replay)["status"] == "COMPONENT_SIGNAL_OR_MIXED_TRADEOFF"


def test_decision_hierarchy_relative_and_nomination_are_separate():
    replay = full_score()
    candidate = full_score(0.5, 0.9)
    candidate["G"] = 0.0006
    replay["G"] = 0.001
    candidate["F"] = 0.5
    assert classify_a25(candidate, replay)["status"] == "RELATIVE_REPAIR_SIGNAL"
    candidate["G"] = 0.0004
    assert classify_a25(candidate, replay)["status"] == "NOMINATE_CONFIRMATORY_P1"
