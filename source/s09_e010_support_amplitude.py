"""Frozen S09-E010 support/amplitude core with no execution path.

The module implements the design-reviewed per-cycle losses, three-arm gradient
directions and graded classifier.  It deliberately contains no optimiser step,
training loop, checkpoint selection or producer launch function.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

import torch

from s09_e009_four_arm import (
    ARM_ANCHOR_25,
    GLOBAL_CLIP_NORM,
    LOSS_ORDER,
    NORM_EPSILON,
    AnchorStationary,
    _require_finite_same_shape,
    _stable_l2_norm,
    arm_direction as e009_arm_direction,
    classify_a25,
    clip_complete_direction,
    flattened_objective_gradients,
    grouped_losses,
    safe_replay_ratio,
)


ARM_A25 = "A25_exact_e009_replay"
ARM_B25 = "B25_support_amplitude_beta0p25"
ARM_B0 = "B0_support_amplitude_beta0"
ARM_ORDER = (ARM_A25, ARM_B25, ARM_B0)
BALANCED_OBJECTIVE_ORDER = ("L_D", "L_S", "L_A", "L_U", "L_H", "L_P")
DAMAGE_SCALE = 0.006896013386826084
SUPPORT_THRESHOLD = 1e-15
PRIMARY_PAIR_SCORE_DELTA = 4
PERSISTENCE_BASELINE = 0.0005017354462152066


def _require(
    condition: bool, message: str, error: type[Exception] = ValueError
) -> None:
    if not condition:
        raise error(message)


def _finite_scalar(value: torch.Tensor, name: str) -> None:
    if value.ndim != 0 or not torch.isfinite(value):
        raise FloatingPointError(f"invalid scalar objective: {name}")


def support_amplitude_losses(
    *,
    predicted_peak: torch.Tensor,
    target_peak: torch.Tensor,
    damage_pre: torch.Tensor,
    nodal_weight: torch.Tensor,
    damage_scale: float = DAMAGE_SCALE,
    support_threshold: float = SUPPORT_THRESHOLD,
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    """Compute the reviewed per-cycle projected support and amplitude losses."""
    tensors = (predicted_peak, target_peak, damage_pre, nodal_weight)
    _require(
        all(value.ndim == 1 for value in tensors),
        "damage fields and nodal weights must be one-dimensional",
    )
    _require(
        len({tuple(value.shape) for value in tensors}) == 1,
        "damage fields and nodal weights must share shape",
    )
    _require(
        all(torch.isfinite(value).all() for value in tensors),
        "nonfinite support/amplitude input",
        FloatingPointError,
    )
    _require(torch.all(nodal_weight >= 0).item(), "nodal weights must be nonnegative")
    weight_sum = nodal_weight.sum()
    _require(
        torch.isfinite(weight_sum).item() and weight_sum > 0,
        "nodal weight sum must be finite and positive",
    )
    _require(
        math.isfinite(damage_scale) and damage_scale > 0,
        "damage scale must be finite and positive",
    )
    _require(
        math.isfinite(support_threshold) and support_threshold >= 0,
        "support threshold must be finite and nonnegative",
    )

    target_increment = target_peak - damage_pre
    predicted_increment = predicted_peak - damage_pre
    support = target_increment > support_threshold
    support_weight = nodal_weight * support.to(nodal_weight.dtype)
    support_weight_sum = support_weight.sum()
    _require(
        torch.isfinite(support_weight_sum).item() and support_weight_sum > 0,
        "target support is empty",
    )

    scaled_error = (predicted_increment - target_increment) / damage_scale
    support_loss = (support_weight * scaled_error.square()).sum() / support_weight_sum
    predicted_amplitude = (nodal_weight * predicted_increment.abs()).sum() / weight_sum
    target_amplitude = (nodal_weight * target_increment.abs()).sum() / weight_sum
    _require(
        torch.isfinite(target_amplitude).item() and target_amplitude > 0,
        "target amplitude must be finite and positive",
    )
    amplitude_loss = ((predicted_amplitude - target_amplitude) / damage_scale).square()
    _finite_scalar(support_loss, "L_S")
    _finite_scalar(amplitude_loss, "L_A")
    return {"L_S": support_loss, "L_A": amplitude_loss}, {
        "support_node_count": int(support.sum().detach().cpu()),
        "support_weight": float(support_weight_sum.detach().cpu()),
        "total_weight": float(weight_sum.detach().cpu()),
        "predicted_amplitude": float(predicted_amplitude.detach().cpu()),
        "target_amplitude": float(target_amplitude.detach().cpu()),
        "support_threshold": float(support_threshold),
        "damage_scale": float(damage_scale),
    }


def balanced_objectives(
    atomic: Mapping[str, torch.Tensor],
    additions: Mapping[str, torch.Tensor],
) -> dict[str, torch.Tensor]:
    """Build the six ordered objectives after per-cycle losses are formed."""
    if tuple(atomic) != LOSS_ORDER:
        raise ValueError("six ordered E009 atomic losses are required")
    if tuple(additions) != ("L_S", "L_A"):
        raise ValueError("ordered L_S and L_A additions are required")
    groups = grouped_losses(atomic)
    objectives = {
        "L_D": groups["L_D"],
        "L_S": additions["L_S"],
        "L_A": additions["L_A"],
        "L_U": groups["L_U"],
        "L_H": groups["L_H"],
        "L_P": groups["L_P"],
    }
    if tuple(objectives) != BALANCED_OBJECTIVE_ORDER:
        raise RuntimeError("balanced objective order drift")
    for name, value in objectives.items():
        _finite_scalar(value, name)
    return objectives


def balanced_direction_components(
    gradients: Mapping[str, torch.Tensor],
    *,
    eps: float = NORM_EPSILON,
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    """Norm-match and remove first-order conflict with the damage anchor."""
    if tuple(gradients) != BALANCED_OBJECTIVE_ORDER:
        raise ValueError("six ordered balanced gradients are required")
    if not math.isfinite(eps) or eps <= 0:
        raise ValueError("epsilon must be finite and positive")
    vectors = list(gradients.values())
    _require_finite_same_shape(vectors)
    anchor = gradients["L_D"]
    anchor_norm = _stable_l2_norm(anchor)
    if anchor_norm <= eps:
        raise AnchorStationary("ANCHOR_STATIONARY_OR_INAPPLICABLE")
    anchor_unit = anchor / anchor_norm

    components: dict[str, torch.Tensor] = {"L_D": anchor}
    records: dict[str, Any] = {}
    for name in ("L_S", "L_A", "L_U", "L_H", "L_P"):
        raw = gradients[name]
        raw_norm = _stable_l2_norm(raw)
        if raw_norm <= eps:
            balanced = torch.zeros_like(raw)
            projected = balanced
            zero_reason = "AUXILIARY_NORM_AT_OR_BELOW_EPSILON"
        else:
            raw_unit = raw / raw_norm
            cosine = anchor_unit.dot(raw_unit)
            if not torch.isfinite(cosine):
                raise FloatingPointError("nonfinite anchor cosine")
            balanced = anchor_norm * raw_unit
            projected = anchor_norm * (
                raw_unit - torch.minimum(cosine, cosine.new_zeros(())) * anchor_unit
            )
            _require_finite_same_shape([balanced, projected])
            if torch.count_nonzero(projected).item() == 0:
                zero_reason = "FULLY_PROJECTED_TO_ZERO"
            elif _stable_l2_norm(projected) <= eps:
                zero_reason = "PROJECTED_RESIDUAL_AT_OR_BELOW_EPSILON"
            else:
                zero_reason = None
        anchor_dot_projected = anchor.dot(projected)
        if not torch.isfinite(anchor_dot_projected):
            raise FloatingPointError("nonfinite anchor/projected dot product")
        components[name] = projected
        records[name] = {
            "raw_norm": float(raw_norm.detach().cpu()),
            "balanced_norm": float(_stable_l2_norm(balanced).detach().cpu()),
            "projected_norm": float(_stable_l2_norm(projected).detach().cpu()),
            "anchor_dot_projected": float(anchor_dot_projected.detach().cpu()),
            "zero_reason": zero_reason,
        }
    return components, {
        "epsilon": float(eps),
        "anchor_norm": float(anchor_norm.detach().cpu()),
        "auxiliary": records,
    }


def balanced_direction(
    gradients: Mapping[str, torch.Tensor],
    *,
    beta: float,
    eps: float = NORM_EPSILON,
) -> tuple[torch.Tensor, dict[str, Any]]:
    """Merge one B0/B25 direction and apply exactly one complete-vector clip."""
    if beta not in (0.0, 0.25):
        raise ValueError("reviewed beta must be 0 or 0.25")
    components, record = balanced_direction_components(gradients, eps=eps)
    merged = (
        components["L_D"]
        + components["L_S"]
        + components["L_A"]
        + components["L_U"]
        + components["L_H"]
        + beta * components["L_P"]
    )
    _require_finite_same_shape([merged])
    anchor_dot_merged = components["L_D"].dot(merged)
    if not torch.isfinite(anchor_dot_merged):
        raise FloatingPointError("nonfinite anchor/merged dot product")
    clipped, clip = clip_complete_direction(merged, limit=GLOBAL_CLIP_NORM)
    return clipped, {
        **record,
        "beta": float(beta),
        "gamma_S": 1.0,
        "gamma_A": 1.0,
        "preclip_anchor_dot_merged": float(anchor_dot_merged.detach().cpu()),
        "preclip_component_norms": {
            name: float(_stable_l2_norm(value).detach().cpu())
            for name, value in components.items()
        },
        **clip,
    }


def three_arm_direction(
    model: torch.nn.Module,
    atomic: Mapping[str, torch.Tensor],
    additions: Mapping[str, torch.Tensor],
    arm: str,
) -> tuple[torch.Tensor, dict[str, Any]]:
    """Return an exact A25 replay or one support/amplitude-balanced direction."""
    if arm not in ARM_ORDER:
        raise ValueError(f"unknown S09-E010 arm: {arm}")
    if arm == ARM_A25:
        direction, record = e009_arm_direction(model, atomic, ARM_ANCHOR_25)
        return direction, {**record, "arm": ARM_A25, "exact_e009_a25_replay": True}
    objectives = balanced_objectives(atomic, additions)
    gradients, layout = flattened_objective_gradients(model, objectives)
    direction, record = balanced_direction(
        gradients, beta=0.25 if arm == ARM_B25 else 0.0
    )
    return direction, {
        **record,
        "arm": arm,
        "layout": layout,
        "exact_e009_a25_replay": False,
    }


def _validated_auc(record: Mapping[str, Any]) -> dict[str, int | float]:
    required = {"value", "wins", "ties", "losses"}
    _require(set(record) == required, "AUC record keys drift")
    wins, ties, losses = record["wins"], record["ties"], record["losses"]
    _require(
        all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in (wins, ties, losses)
        ),
        "AUC pair counts must be native integers",
    )
    _require(
        all(value >= 0 for value in (wins, ties, losses))
        and wins + ties + losses == 25,
        "AUC pair counts must sum to 25",
    )
    expected = (2 * wins + ties) / 50.0
    value = float(record["value"])
    _require(
        math.isfinite(value) and abs(value - expected) <= 1e-15,
        "AUC value/count inconsistency",
    )
    return {"value": value, "wins": wins, "ties": ties, "losses": losses}


def classify_e010(
    *,
    b25: Mapping[str, Any],
    a25: Mapping[str, Any],
    replay: Mapping[str, Any],
    validity_status: str,
) -> dict[str, Any]:
    """Apply the frozen cumulative S09-E010 performance hierarchy."""
    if validity_status not in ("VALID", "EXECUTION_INVALID", "METHOD_INAPPLICABLE"):
        raise ValueError("unknown validity status")
    if validity_status != "VALID":
        return {
            "status": validity_status,
            "primary": None,
            "protected_ratios": None,
            "protected_limits": None,
            "protected_passed": None,
            "replay_relative": None,
        }
    required = {"G", "F", "L_P", "L_judge", *LOSS_ORDER, "amplitude_auc"}
    for name, score in (("B25", b25), ("A25", a25), ("R", replay)):
        _require(required <= set(score), f"{name} scorecard is incomplete")
        for metric in required - {"amplitude_auc"}:
            value = float(score[metric])
            _require(
                math.isfinite(value) and value >= 0,
                f"{name}/{metric} must be finite and nonnegative",
            )
    b_auc = _validated_auc(b25["amplitude_auc"])
    a_auc = _validated_auc(a25["amplitude_auc"])
    r_auc = _validated_auc(replay["amplitude_auc"])
    b_pair_score = 2 * int(b_auc["wins"]) + int(b_auc["ties"])
    a_pair_score = 2 * int(a_auc["wins"]) + int(a_auc["ties"])
    pair_score_delta = b_pair_score - a_pair_score
    targeted = pair_score_delta >= PRIMARY_PAIR_SCORE_DELTA

    protected_limits = {"G": 1.05, "F": 1.05, "L_P": 1.10, "L_judge": 1.05}
    protected_ratios = {
        metric: safe_replay_ratio(float(b25[metric]), float(a25[metric]))
        for metric in protected_limits
    }
    protected_pass = all(
        protected_ratios[name]["value"] is not None
        and protected_ratios[name]["value"] <= limit
        for name, limit in protected_limits.items()
    )

    b_flat = {name: float(b25[name]) for name in required - {"amplitude_auc"}}
    a_flat = {name: float(a25[name]) for name in required - {"amplitude_auc"}}
    r_flat = {name: float(replay[name]) for name in required - {"amplitude_auc"}}
    b_flat["AUC"], a_flat["AUC"], r_flat["AUC"] = (
        float(b_auc["value"]),
        float(a_auc["value"]),
        float(r_auc["value"]),
    )
    e009_replay_relative = classify_a25(b_flat, r_flat)

    if not targeted:
        status = "NO_TARGETED_RANKING_SIGNAL"
    elif not protected_pass:
        status = "TARGETED_RANKING_SIGNAL_WITH_TRADEOFF"
    elif e009_replay_relative["status"] == "NOMINATE_CONFIRMATORY_P1":
        status = "NOMINATE_CONFIRMATORY_P1"
    elif e009_replay_relative["status"] == "RELATIVE_REPAIR_SIGNAL":
        status = "ORIGINAL_RELATIVE_REPAIR_SIGNAL"
    else:
        status = "BALANCED_LOCAL_REPAIR_SIGNAL"
    return {
        "status": status,
        "primary": {
            "B25_pair_score_2W_plus_T": b_pair_score,
            "A25_pair_score_2W_plus_T": a_pair_score,
            "delta_pair_score": pair_score_delta,
            "required_delta": PRIMARY_PAIR_SCORE_DELTA,
            "passed": targeted,
        },
        "protected_ratios": protected_ratios,
        "protected_limits": protected_limits,
        "protected_passed": protected_pass,
        "replay_relative": e009_replay_relative,
    }
