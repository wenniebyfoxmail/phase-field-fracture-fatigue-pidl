"""S09-E013 localisation-aware ranking-objective core.

This module compares the reviewed E011 global-amplitude ranking observable with
one target-localised support-contrast ranking observable.  The operator, base
objectives, projection, coefficient, clipping and optimiser remain unchanged.  It has no optimiser or I/O path.
"""
from __future__ import annotations

from collections import OrderedDict
import math
from typing import Any, Mapping

import torch

from s09_e009_four_arm import (
    GLOBAL_CLIP_NORM,
    NORM_EPSILON,
    _require_finite_same_shape,
    _stable_l2_norm,
    clip_complete_direction,
    flattened_objective_gradients,
)
from s09_e010_support_amplitude import (
    SUPPORT_THRESHOLD,
    balanced_direction_components,
)


ARM_GLOBAL = "G25_global_ranking_replay"
ARM_LOCAL = "L25_local_support_ranking_beta0p25"
ARM_ORDER = (ARM_GLOBAL, ARM_LOCAL)
OBJECTIVE_ORDER = ("L_D", "L_S", "L_A", "L_U", "L_H", "L_P", "L_R")
GROWTH_CYCLES = (1, 58, 60, 69, 70)
NEAR_STAGNANT_CYCLES = (3, 4, 71, 72, 73)
PAIR_ORDER = tuple(
    (growth, stagnant)
    for growth in GROWTH_CYCLES
    for stagnant in NEAR_STAGNANT_CYCLES
)
UPDATES_PER_ARM = 500
PAIR_REPETITIONS = 20
BETA = 0.25
# Prospective D2 amendment after A001 stopped before training: gamma=1 changed
# the wrong-pair merged derivatives by only 0.04--0.28% of the opposing B25
# term.  4096 is the next power of two above the largest observed zero-crossing
# requirement (~2.84e3); it is one fixed value, not a sweep.
RANK_COEFFICIENT = 4096.0
AMPLITUDE_NORMALISER = 0.00016864539921617467
RANK_TEMPERATURE = 0.01
RANK_MARGIN = 0.0
PRIMARY_PAIR_SCORE_GAIN = 2
ROBUST_PAIR_SCORE_GAIN = 4
PROTECTED_RATIO_LIMIT = 1.10


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def pair_schedule() -> tuple[tuple[int, int], ...]:
    schedule = PAIR_ORDER * PAIR_REPETITIONS
    _require(len(schedule) == UPDATES_PER_ARM, "pair schedule length drift")
    return schedule


def weighted_amplitude(
    predicted_peak: torch.Tensor,
    damage_pre: torch.Tensor,
    nodal_weight: torch.Tensor,
) -> torch.Tensor:
    _require(
        predicted_peak.ndim == damage_pre.ndim == nodal_weight.ndim == 1,
        "amplitude fields must be one-dimensional",
    )
    _require(
        predicted_peak.shape == damage_pre.shape == nodal_weight.shape,
        "amplitude field shape drift",
    )
    _require(
        torch.isfinite(predicted_peak).all()
        and torch.isfinite(damage_pre).all()
        and torch.isfinite(nodal_weight).all(),
        "nonfinite amplitude input",
    )
    weight_sum = nodal_weight.sum()
    _require(
        torch.isfinite(weight_sum).item() and weight_sum.item() > 0,
        "invalid nodal weight sum",
    )
    amplitude = ((predicted_peak - damage_pre).abs() * nodal_weight).sum() / weight_sum
    if amplitude.ndim != 0 or not torch.isfinite(amplitude):
        raise FloatingPointError("invalid predicted amplitude")
    return amplitude


def local_support_score(
    predicted_peak: torch.Tensor,
    damage_pre: torch.Tensor,
    target_peak: torch.Tensor,
    nodal_weight: torch.Tensor,
    *,
    support_threshold: float = SUPPORT_THRESHOLD,
) -> tuple[torch.Tensor, dict[str, float | int]]:
    """Return predicted growth on target support minus predicted background growth.

    The target-derived mask is used only to form a development-training loss. It
    is never an operator input or an inference-time post-processing mask.
    """
    tensors = (predicted_peak, damage_pre, target_peak, nodal_weight)
    _require(all(value.ndim == 1 for value in tensors), "local fields must be one-dimensional")
    _require(len({tuple(value.shape) for value in tensors}) == 1, "local field shape drift")
    _require(all(torch.isfinite(value).all() for value in tensors), "nonfinite local input")
    _require(math.isfinite(support_threshold) and support_threshold >= 0, "invalid support threshold")
    support = (target_peak - damage_pre) > support_threshold
    background = ~support
    support_weight = nodal_weight * support.to(nodal_weight.dtype)
    background_weight = nodal_weight * background.to(nodal_weight.dtype)
    support_mass = support_weight.sum()
    background_mass = background_weight.sum()
    _require(support_mass.item() > 0 and background_mass.item() > 0, "empty support/background")
    predicted_increment = torch.clamp(predicted_peak - damage_pre, min=0.0)
    support_mean = (predicted_increment * support_weight).sum() / support_mass
    background_mean = (predicted_increment * background_weight).sum() / background_mass
    score = support_mean - background_mean
    if score.ndim != 0 or not torch.isfinite(score):
        raise FloatingPointError("invalid local support score")
    return score, {
        "support_mean": float(support_mean.detach().cpu()),
        "background_mean": float(background_mean.detach().cpu()),
        "local_support_contrast": float(score.detach().cpu()),
        "support_node_count": int(support.sum().detach().cpu()),
        "background_node_count": int(background.sum().detach().cpu()),
        "support_weight": float(support_mass.detach().cpu()),
        "background_weight": float(background_mass.detach().cpu()),
        "support_threshold": float(support_threshold),
    }


def ranking_loss(
    growth_score: torch.Tensor,
    stagnant_score: torch.Tensor,
    *,
    normaliser: float = AMPLITUDE_NORMALISER,
    temperature: float = RANK_TEMPERATURE,
    margin: float = RANK_MARGIN,
) -> tuple[torch.Tensor, dict[str, float]]:
    """Smoothly penalise a stagnant scalar score that is not below growth."""
    _require(
        growth_score.ndim == stagnant_score.ndim == 0,
        "ranking scores must be scalar",
    )
    _require(
        torch.isfinite(growth_score).item()
        and torch.isfinite(stagnant_score).item(),
        "nonfinite ranking score",
    )
    _require(math.isfinite(normaliser) and normaliser > 0, "invalid normaliser")
    _require(math.isfinite(temperature) and temperature > 0, "invalid temperature")
    _require(math.isfinite(margin), "invalid margin")
    physical_margin = growth_score - stagnant_score
    normalised_margin = physical_margin / normaliser
    argument = (margin - normalised_margin) / temperature
    loss = torch.nn.functional.softplus(argument)
    if loss.ndim != 0 or not torch.isfinite(loss):
        raise FloatingPointError("invalid ranking loss")
    return loss, {
        "growth_score": float(growth_score.detach().cpu()),
        "stagnant_score": float(stagnant_score.detach().cpu()),
        "physical_margin": float(physical_margin.detach().cpu()),
        "normalised_margin": float(normalised_margin.detach().cpu()),
        "softplus_argument": float(argument.detach().cpu()),
        "normaliser": float(normaliser),
        "temperature": float(temperature),
        "margin": float(margin),
    }


def pair_mean_objectives(
    left: Mapping[str, torch.Tensor],
    right: Mapping[str, torch.Tensor],
    rank: torch.Tensor,
) -> OrderedDict[str, torch.Tensor]:
    base_names = OBJECTIVE_ORDER[:-1]
    _require(tuple(left) == base_names, "growth objective order drift")
    _require(tuple(right) == base_names, "stagnant objective order drift")
    objectives: OrderedDict[str, torch.Tensor] = OrderedDict(
        (name, (left[name] + right[name]) / 2.0) for name in base_names
    )
    objectives["L_R"] = rank
    for name, value in objectives.items():
        if value.ndim != 0 or not torch.isfinite(value):
            raise FloatingPointError(f"invalid pair objective: {name}")
    return objectives


def ranking_direction(
    model: torch.nn.Module,
    objectives: Mapping[str, torch.Tensor],
    arm: str,
    *,
    eps: float = NORM_EPSILON,
) -> tuple[torch.Tensor, dict[str, Any], dict[str, torch.Tensor]]:
    """Build the pair-batched B25 direction with one projected ranking term."""
    _require(arm in ARM_ORDER, "unknown E013 arm")
    _require(tuple(objectives) == OBJECTIVE_ORDER, "E013 objective order drift")
    gradients, layout = flattened_objective_gradients(model, objectives)
    direction, diagnostic = merge_ranking_gradients(
        gradients, arm, layout=layout, eps=eps
    )
    return direction, diagnostic, gradients


def merge_ranking_gradients(
    gradients: Mapping[str, torch.Tensor],
    arm: str,
    *,
    layout: Mapping[str, Any] | None = None,
    eps: float = NORM_EPSILON,
) -> tuple[torch.Tensor, dict[str, Any]]:
    """Merge already-flattened gradients using the frozen E011 merge rule."""
    _require(arm in ARM_ORDER, "unknown E013 arm")
    _require(tuple(gradients) == OBJECTIVE_ORDER, "E013 gradient order drift")
    base_gradients = OrderedDict(
        (name, gradients[name]) for name in OBJECTIVE_ORDER[:-1]
    )
    components, record = balanced_direction_components(base_gradients, eps=eps)
    rank_gradient = gradients["L_R"]
    anchor = components["L_D"]
    anchor_norm = _stable_l2_norm(anchor)
    rank_norm = _stable_l2_norm(rank_gradient)
    if rank_norm <= eps:
        q_rank = torch.zeros_like(rank_gradient)
        rank_zero_reason = "RANK_NORM_AT_OR_BELOW_EPSILON"
        balanced_rank_norm = 0.0
    else:
        balanced_rank = anchor_norm * rank_gradient / rank_norm
        cosine = anchor.dot(balanced_rank) / anchor_norm.square()
        q_rank = balanced_rank - torch.minimum(
            cosine, cosine.new_zeros(())
        ) * anchor
        rank_zero_reason = None if _stable_l2_norm(q_rank) > eps else (
            "RANK_PROJECTED_RESIDUAL_AT_OR_BELOW_EPSILON"
        )
        if rank_zero_reason is not None:
            q_rank = torch.zeros_like(rank_gradient)
        balanced_rank_norm = float(_stable_l2_norm(balanced_rank).detach().cpu())

    merged = (
        components["L_D"]
        + components["L_S"]
        + components["L_A"]
        + components["L_U"]
        + components["L_H"]
        + BETA * components["L_P"]
    )
    merged = merged + RANK_COEFFICIENT * q_rank
    _require_finite_same_shape([merged, q_rank])
    clipped, clip = clip_complete_direction(merged, limit=GLOBAL_CLIP_NORM)
    diagnostic = {
        **record,
        "arm": arm,
        "layout": None if layout is None else dict(layout),
        "beta": BETA,
        "rank_coefficient": RANK_COEFFICIENT,
        "rank": {
            "raw_norm": float(rank_norm.detach().cpu()),
            "balanced_norm": balanced_rank_norm,
            "projected_norm": float(_stable_l2_norm(q_rank).detach().cpu()),
            "anchor_dot_projected": float(anchor.dot(q_rank).detach().cpu()),
            "zero_reason": rank_zero_reason,
        },
        "preclip_component_norms": {
            **{
                name: float(_stable_l2_norm(value).detach().cpu())
                for name, value in components.items()
            },
            "L_R": float(_stable_l2_norm(q_rank).detach().cpu()),
        },
        **clip,
    }
    return clipped, diagnostic


def pair_score(auc: Mapping[str, Any]) -> int:
    wins, ties, losses = auc.get("wins"), auc.get("ties"), auc.get("losses")
    _require(
        all(type(value) is int and value >= 0 for value in (wins, ties, losses)),
        "invalid pair-count record",
    )
    _require(wins + ties + losses == len(PAIR_ORDER), "pair-count total drift")
    return 2 * wins + ties


def classify_e013(
    *,
    global_ranking: Mapping[str, Any],
    local_ranking: Mapping[str, Any],
    validity: bool,
) -> dict[str, Any]:
    if not validity:
        return {"status": "EXECUTION_INVALID", "validity": False}
    global_score = pair_score(global_ranking["local_support_auc"])
    local_score = pair_score(local_ranking["local_support_auc"])
    gain = local_score - global_score
    protected = {}
    for name in ("G", "F", "L_P", "L_judge"):
        denominator = float(global_ranking[name])
        value = None if denominator == 0 else float(local_ranking[name]) / denominator
        protected[name] = {"value": value, "limit": PROTECTED_RATIO_LIMIT}
    protected_pass = all(
        item["value"] is not None and math.isfinite(item["value"])
        and item["value"] <= item["limit"]
        for item in protected.values()
    )
    status = (
        "LOCALISED_OBJECTIVE_SIGNAL"
        if gain >= PRIMARY_PAIR_SCORE_GAIN
        else "NO_REALISED_LOCAL_SIGNAL"
    )
    tier = (
        "ROBUST_LOCAL_OBJECTIVE_REPAIR"
        if gain >= ROBUST_PAIR_SCORE_GAIN and protected_pass
        else "MINIMAL_LOCAL_SIGNAL"
        if gain >= PRIMARY_PAIR_SCORE_GAIN
        else "DIRECTIONAL_OR_NO_SIGNAL"
    )
    return {
        "status": status,
        "tier": tier,
        "validity": True,
        "primary": {
            "global_local_pair_score": global_score,
            "local_local_pair_score": local_score,
            "delta_pair_score": gain,
            "required_delta": PRIMARY_PAIR_SCORE_GAIN,
            "passed": gain >= PRIMARY_PAIR_SCORE_GAIN,
        },
        "protected_ratios": protected,
        "protected_passed": protected_pass,
    }
