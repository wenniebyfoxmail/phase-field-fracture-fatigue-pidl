from collections import OrderedDict

import pytest
import torch

from s09_e011_ranking_objective import (
    AMPLITUDE_NORMALISER,
    ARM_CONTROL,
    ARM_RANK,
    OBJECTIVE_ORDER,
    PAIR_ORDER,
    PRIMARY_PAIR_SCORE_GAIN,
    classify_e011,
    pair_mean_objectives,
    pair_schedule,
    ranking_direction,
    ranking_loss,
    weighted_amplitude,
)
from s09_e011_producer import _adamw_displacement
from s09_stage0a_p1_trainer import assign_merged_gradient


def test_pair_schedule_is_fixed_complete_and_repeated_twenty_times():
    schedule = pair_schedule()
    assert len(PAIR_ORDER) == 25
    assert len(schedule) == 500
    assert schedule[:25] == PAIR_ORDER
    assert schedule[-25:] == PAIR_ORDER
    assert all(schedule.count(pair) == 20 for pair in PAIR_ORDER)


def test_ranking_loss_descent_increases_growth_minus_stagnant_margin():
    growth = torch.tensor(2.0e-6, dtype=torch.float64, requires_grad=True)
    stagnant = torch.tensor(3.0e-6, dtype=torch.float64, requires_grad=True)
    loss, record = ranking_loss(growth, stagnant)
    dg, ds = torch.autograd.grad(loss, (growth, stagnant))
    margin_change_under_descent = float((-dg) - (-ds))
    assert record["physical_margin"] == pytest.approx(-1.0e-6)
    assert record["normalised_margin"] == pytest.approx(-1.0e-6 / AMPLITUDE_NORMALISER)
    assert margin_change_under_descent > 0


def test_weighted_amplitude_uses_damage_increment_and_weights():
    peak = torch.tensor([0.1, 0.4], dtype=torch.float64)
    pre = torch.tensor([0.0, 0.2], dtype=torch.float64)
    weight = torch.tensor([1.0, 3.0], dtype=torch.float64)
    assert weighted_amplitude(peak, pre, weight).item() == pytest.approx(0.175)


def _objectives(model):
    p = next(model.parameters()).reshape(-1)
    left = OrderedDict(
        (name, (index + 1.0) * (p.square().sum() + 0.1 * p.sum()))
        for index, name in enumerate(OBJECTIVE_ORDER[:-1])
    )
    right = OrderedDict(
        (name, (index + 0.5) * ((p - 0.2).square().sum() + 0.2 * p.sum()))
        for index, name in enumerate(OBJECTIVE_ORDER[:-1])
    )
    rank = (p[0] - 2.0 * p[1]).square() + 0.25 * p[2]
    return pair_mean_objectives(left, right, rank)


def test_ranking_arm_changes_only_the_single_rank_component():
    model_control = torch.nn.Linear(3, 1, bias=False, dtype=torch.float64)
    model_rank = torch.nn.Linear(3, 1, bias=False, dtype=torch.float64)
    state = {"weight": torch.tensor([[0.2, -0.3, 0.4]], dtype=torch.float64)}
    model_control.load_state_dict(state)
    model_rank.load_state_dict(state)
    control, control_record, _ = ranking_direction(
        model_control, _objectives(model_control), ARM_CONTROL
    )
    ranked, rank_record, _ = ranking_direction(
        model_rank, _objectives(model_rank), ARM_RANK
    )
    assert control_record["rank_coefficient"] == 0.0
    assert rank_record["rank_coefficient"] == 4096.0
    assert rank_record["rank"]["raw_norm"] > 0
    assert not torch.equal(control, ranked)
    assert torch.isfinite(control).all() and torch.isfinite(ranked).all()
    assert control.norm() <= 1.0 + 1e-12
    assert ranked.norm() <= 1.0 + 1e-12


def _metric(wins, ties, losses, **overrides):
    result = {
        "amplitude_auc": {
            "wins": wins,
            "ties": ties,
            "losses": losses,
            "value": (wins + 0.5 * ties) / 25,
        },
        "G": 1.0,
        "F": 1.0,
        "L_P": 1.0,
        "L_judge": 1.0,
    }
    result.update(overrides)
    return result


def test_classifier_uses_one_net_pair_as_exploratory_primary():
    result = classify_e011(
        control=_metric(17, 0, 8),
        ranking=_metric(18, 0, 7),
        validity=True,
    )
    assert PRIMARY_PAIR_SCORE_GAIN == 2
    assert result["primary"]["delta_pair_score"] == 2
    assert result["status"] == "OBJECTIVE_REPAIR_SIGNAL"


def test_classifier_preserves_primary_miss_and_component_ratios():
    result = classify_e011(
        control=_metric(17, 0, 8),
        ranking=_metric(17, 0, 8, F=0.5),
        validity=True,
    )
    assert result["status"] == "NO_REALISED_RANKING_REPAIR"
    assert result["primary"]["passed"] is False
    assert result["protected_ratios"]["F"]["value"] == pytest.approx(0.5)


def test_invalid_result_is_not_scored():
    assert classify_e011(
        control=_metric(17, 0, 8), ranking=_metric(18, 0, 7), validity=False
    ) == {"status": "EXECUTION_INVALID", "validity": False}


def test_analytic_next_adamw_displacement_matches_real_cloned_step():
    model = torch.nn.Linear(3, 1, bias=True, dtype=torch.float64)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=3e-4, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.0
    )
    first = sum(parameter.square().sum() for parameter in model.parameters())
    first.backward()
    optimizer.step()
    clone = torch.nn.Linear(3, 1, bias=True, dtype=torch.float64)
    clone.load_state_dict(model.state_dict())
    clone_optimizer = torch.optim.AdamW(
        clone.parameters(), lr=3e-4, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.0
    )
    clone_optimizer.load_state_dict(optimizer.state_dict())
    names = [name for name, _ in clone.named_parameters()]
    direction = torch.linspace(
        -0.4, 0.7, sum(parameter.numel() for parameter in clone.parameters()),
        dtype=torch.float64,
    )
    predicted = _adamw_displacement(clone, clone_optimizer, direction, names)
    before = torch.cat([parameter.detach().reshape(-1) for parameter in clone.parameters()])
    assign_merged_gradient(clone, direction, names)
    clone_optimizer.step()
    after = torch.cat([parameter.detach().reshape(-1) for parameter in clone.parameters()])
    assert torch.allclose(after - before, predicted, atol=1e-15, rtol=1e-12)
