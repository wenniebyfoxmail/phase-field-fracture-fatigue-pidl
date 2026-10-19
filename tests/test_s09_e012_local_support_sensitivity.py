from __future__ import annotations

from collections import OrderedDict
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))
SPEC = importlib.util.spec_from_file_location(
    "analyse_s09_e012_local_support_sensitivity",
    ROOT / "scripts/analyse_s09_e012_local_support_sensitivity.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_local_support_score_uses_fixed_target_mask() -> None:
    predicted = torch.tensor([4.0, 2.0, 1.0, 3.0], dtype=torch.float64)
    target = torch.tensor([0.0, 5.0, 0.0, 6.0], dtype=torch.float64)
    weight = torch.tensor([1.0, 2.0, 1.0, 1.0], dtype=torch.float64)
    score, record = MODULE.local_support_score(
        predicted, target, weight, threshold=1.0
    )
    expected_local = (2.0 * 2.0 + 3.0 * 1.0) / 3.0
    expected_background = (4.0 + 1.0) / 2.0
    torch.testing.assert_close(
        score, torch.tensor(expected_local - expected_background, dtype=torch.float64)
    )
    assert record["support_weight_fraction"] == 3.0 / 5.0
    assert record["predicted_increment_mass_fraction_in_support"] == 7.0 / 12.0


def test_ranking_gradient_algebra_matches_autograd() -> None:
    parameter = torch.tensor([1.0e-7, -2.0e-7], dtype=torch.float64, requires_grad=True)
    margin = 2.0 * parameter[0] - 3.0 * parameter[1]
    loss = torch.nn.functional.softplus(
        -margin / (MODULE.AMPLITUDE_NORMALISER * MODULE.RANK_TEMPERATURE)
    )
    expected = torch.autograd.grad(loss, parameter)[0]
    actual, coefficient = MODULE.ranking_gradient_from_margin(
        float(margin.detach()), torch.tensor([2.0, -3.0], dtype=torch.float64)
    )
    torch.testing.assert_close(actual, expected, rtol=1e-12, atol=1e-12)
    assert coefficient < 0


def test_adamw_displacement_from_state_dict_matches_closed_form() -> None:
    parameter = torch.nn.Parameter(torch.tensor([1.0, -2.0], dtype=torch.float64))
    gradient = torch.tensor([0.2, -0.4], dtype=torch.float64)
    state = {
        "state": {
            0: {
                "step": torch.tensor(4.0),
                "exp_avg": torch.tensor([0.1, -0.2], dtype=torch.float64),
                "exp_avg_sq": torch.tensor([0.01, 0.04], dtype=torch.float64),
            }
        },
        "param_groups": [{
            "params": [0], "lr": 3e-4, "betas": (0.9, 0.999), "eps": 1e-8,
            "weight_decay": 0.0, "amsgrad": False, "maximize": False,
        }],
    }
    actual = MODULE.adamw_displacement_from_state_dict(
        gradient, [("weight", parameter)], state
    )
    next_avg = 0.9 * state["state"][0]["exp_avg"] + 0.1 * gradient
    next_sq = 0.999 * state["state"][0]["exp_avg_sq"] + 0.001 * gradient.square()
    expected = -(3e-4 / (1 - 0.9**5)) * next_avg / (
        next_sq.sqrt() / np.sqrt(1 - 0.999**5) + 1e-8
    )
    torch.testing.assert_close(actual, expected, rtol=1e-12, atol=1e-12)
    torch.testing.assert_close(parameter, torch.tensor([1.0, -2.0], dtype=torch.float64))


def test_preclip_control_excludes_rank_component() -> None:
    gradients = OrderedDict(
        (name, torch.tensor([1.0, 0.0], dtype=torch.float64))
        for name in MODULE.OBJECTIVE_ORDER
    )
    gradients["L_R"] = torch.tensor([-1.0, 1.0], dtype=torch.float64)
    control, q_rank, _ = MODULE.preclip_merge(gradients, MODULE.ARM_CONTROL)
    ranking, q_rank_again, _ = MODULE.preclip_merge(gradients, MODULE.ARM_RANK)
    torch.testing.assert_close(q_rank, q_rank_again)
    torch.testing.assert_close(
        ranking - control, MODULE.RANK_COEFFICIENT * q_rank
    )


def test_preclip_projection_uses_stable_norm_and_matches_core_clip() -> None:
    gradients = OrderedDict(
        (name, torch.zeros(2, dtype=torch.float64))
        for name in MODULE.OBJECTIVE_ORDER
    )
    gradients["L_D"] = torch.tensor([1.0, 0.0], dtype=torch.float64)
    gradients["L_R"] = torch.tensor([1.0e200, 1.0e200], dtype=torch.float64)
    preclip, q_rank, _ = MODULE.preclip_merge(gradients, MODULE.ARM_RANK)
    postclip, _ = MODULE.merge_ranking_gradients(gradients, MODULE.ARM_RANK)
    independently_clipped, _ = MODULE.clip_complete_direction(preclip)
    assert torch.isfinite(q_rank).all()
    assert torch.linalg.vector_norm(q_rank) > 0
    assert torch.equal(independently_clipped, postclip)


def test_group_energy_sums_to_one() -> None:
    vector = np.asarray([1.0, 2.0, 3.0])
    fractions = MODULE.group_energy(
        vector,
        {"a": np.asarray([0, 1]), "b": np.asarray([2])},
    )
    assert abs(sum(fractions.values()) - 1.0) < 1e-15
    normalised = MODULE.normalise_fraction_map({"a": 0.3, "b": 0.3})
    assert abs(sum(normalised.values()) - 1.0) < 1e-15


def test_relative_pair_contrast_rejects_zero_row_normaliser() -> None:
    zeros = np.zeros(3)
    with pytest.raises(ValueError, match="undefined local-contrast normaliser"):
        MODULE.relative_pair_contrast(zeros, zeros, zeros)


def test_amplitude_replay_rejects_nonfinite_value() -> None:
    data = {"cycles": [1, 2], "values": {"global": np.asarray([0.0, np.nan])}}
    with pytest.raises(ValueError, match="nonfinite replayed amplitude"):
        MODULE.amplitude_replay_error(data, {1: 0.0, 2: 0.0})


def test_next_adamw_crossing_is_distinct_from_endpoint_displacement() -> None:
    evidence = MODULE.next_step_pair_evidence(7.0e-6, -1.3322578153409078e-5)
    assert evidence == {
        "adamw_next_global_margin": pytest.approx(-6.322578153409077e-6),
        "adamw_next_global_outcome": "LOSS",
        "adamw_next_global_crossing": True,
        "adamw_next_global_repair": False,
    }
    repair = MODULE.next_step_pair_evidence(-2.0e-6, 3.0e-6)
    assert repair["adamw_next_global_repair"] is True
    assert repair["adamw_next_global_crossing"] is False


def test_mean_group_allocation_survives_zero_component_medians() -> None:
    rows = np.eye(7)
    slices = {f"g{index}": np.asarray([index]) for index in range(7)}
    median = {
        group: float(np.median([MODULE.group_energy(row, slices)[group] for row in rows]))
        for group in slices
    }
    assert sum(median.values()) == 0.0
    mean = MODULE.normalise_fraction_map({
        group: float(np.mean([MODULE.group_energy(row, slices)[group] for row in rows]))
        for group in slices
    })
    assert sum(mean.values()) == pytest.approx(1.0)


def _route_rows(*, raw_helpful: bool, later_helpful: bool) -> list[dict]:
    rows = []
    for state in MODULE.STATE_ORDER:
        for index, (growth, stagnant) in enumerate(MODULE.PAIR_ORDER):
            initial = "LOSS" if index < 8 else "WIN"
            cosine = 0.5 if raw_helpful else -0.5
            later = 0.5 if later_helpful else -0.5
            rows.append({
                "state": state,
                "growth_cycle": growth,
                "stagnant_cycle": stagnant,
                "initial_outcome": initial,
                "local_contrast_to_row_rms": 0.5,
                "local_contrast_node_decoder_energy_fraction": 0.2,
                "raw_rank_local_cosine": cosine,
                "arms": {MODULE.ARM_RANK: {
                    "projected_rank_local_cosine": later,
                    "postclip_local_cosine": later,
                    "adamw_local_cosine": later,
                }},
            })
    return rows


def test_action_selector_separates_labels_from_fixed_priority() -> None:
    localisation = MODULE.choose_route(
        _route_rows(raw_helpful=False, later_helpful=False)
    )
    assert localisation["route"] == "LOCALISATION_AWARE_OBJECTIVE_PROBE"
    merger = MODULE.choose_route(
        _route_rows(raw_helpful=True, later_helpful=False)
    )
    assert merger["route"] == "MERGER_OR_PRECONDITIONER_REPAIR_PROBE"
    mixed = _route_rows(raw_helpful=False, later_helpful=False)
    for row in mixed:
        if row["state"] == MODULE.STATE_ORDER[0] and row["initial_outcome"] == "LOSS":
            row["raw_rank_local_cosine"] = 0.5
    result = MODULE.choose_route(mixed)
    assert result["route"] == "MERGER_OR_PRECONDITIONER_REPAIR_PROBE"
    assert result["action_candidates"] == [
        "MERGER_OR_PRECONDITIONER_REPAIR_PROBE",
        "LOCALISATION_AWARE_OBJECTIVE_PROBE",
    ]
    assert result["per_state"][MODULE.STATE_ORDER[0]]["mechanism_labels"] == [
        "DOWNSTREAM_DIRECTION_LOSS"
    ]
