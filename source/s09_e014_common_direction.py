"""Pure common-direction construction for S09-E014."""
from __future__ import annotations

from collections import OrderedDict
import hashlib
import math
from typing import Any, Mapping

import torch

from s09_e009_four_arm import (
    GLOBAL_CLIP_NORM,
    NORM_EPSILON,
    _require_finite_same_shape,
    _stable_l2_norm,
    clip_complete_direction,
)
from s09_e010_support_amplitude import (
    BALANCED_OBJECTIVE_ORDER,
    balanced_direction_components,
)


ARM_CONTROL = "CG25_common_global_primary_control"
ARM_CANDIDATE = "CL25_common_global_primary_nullspace_local_secondary"
ARM_ORDER = (ARM_CONTROL, ARM_CANDIDATE)
GAMMA = 4096.0
NORMALISER_D = 0.00016864539921617467
TEMPERATURE = 0.01
PINV_RTOL = 1e-12


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def tensor_sha256(value: torch.Tensor) -> str:
    array = value.detach().cpu().contiguous().numpy()
    return hashlib.sha256(array.tobytes()).hexdigest()


def aggregate_rank_gradient(
    scores: Mapping[int, torch.Tensor],
    score_gradients: Mapping[int, torch.Tensor],
    pairs: tuple[tuple[int, int], ...],
    *,
    normaliser: float = NORMALISER_D,
    temperature: float = TEMPERATURE,
) -> tuple[torch.Tensor, torch.Tensor, list[dict[str, float]]]:
    """Differentiate the mean pairwise softplus loss from saved score Jacobians."""
    _require(math.isfinite(normaliser) and normaliser > 0, "invalid normaliser")
    _require(math.isfinite(temperature) and temperature > 0, "invalid temperature")
    _require(bool(pairs), "pair set is empty")
    needed = {cycle for pair in pairs for cycle in pair}
    _require(set(scores) == needed and set(score_gradients) == needed,
             "score/gradient cycle membership drift")
    gradients = list(score_gradients.values())
    _require_finite_same_shape(gradients)
    denom = normaliser * temperature
    total_loss = next(iter(scores.values())).new_zeros(())
    total_gradient = torch.zeros_like(gradients[0])
    rows: list[dict[str, float]] = []
    for growth, stagnant in pairs:
        margin = scores[growth] - scores[stagnant]
        loss = torch.nn.functional.softplus(-margin / denom)
        coefficient = -torch.sigmoid(-margin / denom) / denom / len(pairs)
        total_loss = total_loss + loss / len(pairs)
        total_gradient = total_gradient + coefficient * (
            score_gradients[growth] - score_gradients[stagnant]
        )
        rows.append({
            "growth_cycle": float(growth),
            "stagnant_cycle": float(stagnant),
            "margin": float(margin.detach().cpu()),
            "loss": float(loss.detach().cpu()),
            "mean_gradient_coefficient": float(coefficient.detach().cpu()),
        })
    _require(torch.isfinite(total_loss).item(), "nonfinite aggregate rank loss")
    _require(torch.isfinite(total_gradient).all().item(),
             "nonfinite aggregate rank gradient")
    return total_loss, total_gradient, rows


def _norm_matched_nonconflicting(
    anchor: torch.Tensor, raw: torch.Tensor, *, eps: float,
) -> tuple[torch.Tensor, dict[str, float]]:
    _require_finite_same_shape([anchor, raw])
    anchor_norm = _stable_l2_norm(anchor)
    raw_norm = _stable_l2_norm(raw)
    _require(anchor_norm > eps, "damage anchor is stationary")
    _require(raw_norm > eps, "aggregate global rank gradient is stationary")
    anchor_unit = anchor / anchor_norm
    raw_unit = raw / raw_norm
    cosine = anchor_unit.dot(raw_unit)
    component = anchor_norm * (
        raw_unit - torch.minimum(cosine, cosine.new_zeros(())) * anchor_unit
    )
    _require(torch.isfinite(component).all().item(), "invalid global component")
    return component, {
        "anchor_norm": float(anchor_norm.detach().cpu()),
        "raw_norm": float(raw_norm.detach().cpu()),
        "raw_anchor_cosine": float(cosine.detach().cpu()),
        "component_norm": float(_stable_l2_norm(component).detach().cpu()),
        "anchor_dot_component": float(anchor.dot(component).detach().cpu()),
    }


def nullspace_local_secondary(
    anchor: torch.Tensor,
    global_gradient: torch.Tensor,
    local_gradient: torch.Tensor,
    *,
    eps: float = NORM_EPSILON,
    rtol: float = PINV_RTOL,
) -> tuple[torch.Tensor, dict[str, Any]]:
    """Project norm-matched local gradient off anchor/global span via a 2x2 Gram."""
    _require_finite_same_shape([anchor, global_gradient, local_gradient])
    _require(math.isfinite(rtol) and rtol > 0, "invalid pseudoinverse tolerance")
    anchor_norm = _stable_l2_norm(anchor)
    local_norm = _stable_l2_norm(local_gradient)
    _require(anchor_norm > eps, "damage anchor is stationary")
    _require(local_norm > eps, "aggregate local rank gradient is stationary")
    local_balanced = anchor_norm * local_gradient / local_norm
    gram = torch.stack((
        torch.stack((anchor.dot(anchor), anchor.dot(global_gradient))),
        torch.stack((global_gradient.dot(anchor), global_gradient.dot(global_gradient))),
    )).to(torch.float64)
    rhs = torch.stack((anchor.dot(local_balanced),
                       global_gradient.dot(local_balanced))).to(torch.float64)
    pinv = torch.linalg.pinv(gram, rtol=rtol)
    coefficients = pinv.mv(rhs).to(local_balanced.dtype)
    projected = local_balanced - coefficients[0] * anchor - coefficients[1] * global_gradient
    _require(torch.isfinite(projected).all().item(), "nonfinite local projection")
    singular = torch.linalg.svdvals(gram)
    threshold = rtol * singular.max()
    rank = int((singular > threshold).sum().item())
    return projected, {
        "rtol": float(rtol),
        "gram": gram.detach().cpu().tolist(),
        "gram_pinv": pinv.detach().cpu().tolist(),
        "rhs": rhs.detach().cpu().tolist(),
        "coefficients": coefficients.detach().cpu().tolist(),
        "gram_rank": rank,
        "gram_singular_values": singular.detach().cpu().tolist(),
        "local_raw_norm": float(local_norm.detach().cpu()),
        "local_balanced_norm": float(_stable_l2_norm(local_balanced).detach().cpu()),
        "projected_norm": float(_stable_l2_norm(projected).detach().cpu()),
        "anchor_dot_projected": float(anchor.dot(projected).detach().cpu()),
        "global_dot_projected": float(global_gradient.dot(projected).detach().cpu()),
    }


def common_directions(
    base_gradients: Mapping[str, torch.Tensor],
    global_rank_gradient: torch.Tensor,
    local_rank_gradient: torch.Tensor,
    *,
    beta: float = 0.25,
    gamma: float = GAMMA,
    eps: float = NORM_EPSILON,
) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor], dict[str, Any]]:
    """Construct the unique control and nullspace-secondary complete directions."""
    _require(tuple(base_gradients) == BALANCED_OBJECTIVE_ORDER,
             "base gradient order drift")
    _require(beta == 0.25 and gamma == GAMMA, "frozen coefficient drift")
    components, base_record = balanced_direction_components(base_gradients, eps=eps)
    anchor = components["L_D"]
    base = (components["L_D"] + components["L_S"] + components["L_A"]
            + components["L_U"] + components["L_H"] + beta * components["L_P"])
    global_component, global_record = _norm_matched_nonconflicting(
        anchor, global_rank_gradient, eps=eps)
    local_component, local_record = nullspace_local_secondary(
        anchor, global_rank_gradient, local_rank_gradient, eps=eps)
    preclip = OrderedDict((
        (ARM_CONTROL, base + gamma * global_component),
        (ARM_CANDIDATE, base + gamma * global_component + gamma * local_component),
    ))
    directions: dict[str, torch.Tensor] = OrderedDict()
    clip_records = {}
    for arm, value in preclip.items():
        directions[arm], clip_records[arm] = clip_complete_direction(
            value, limit=GLOBAL_CLIP_NORM)
    return directions, {
        "base": base,
        "global_primary": global_component,
        "local_secondary": local_component,
    }, {
        "beta": beta,
        "gamma": gamma,
        "base": base_record,
        "global_primary": global_record,
        "local_secondary": local_record,
        "clip": clip_records,
        "hashes": {
            "base": tensor_sha256(base),
            "global_primary": tensor_sha256(global_component),
            "local_secondary": tensor_sha256(local_component),
            **{arm: tensor_sha256(value) for arm, value in directions.items()},
        },
    }


def pair_score(values: Mapping[int, float], pairs: tuple[tuple[int, int], ...]) -> dict[str, Any]:
    wins = ties = losses = 0
    rows = []
    for growth, stagnant in pairs:
        margin = float(values[growth] - values[stagnant])
        outcome = "WIN" if margin > 0 else "LOSS" if margin < 0 else "TIE"
        wins += outcome == "WIN"; ties += outcome == "TIE"; losses += outcome == "LOSS"
        rows.append({"growth_cycle": growth, "stagnant_cycle": stagnant,
                     "margin": margin, "outcome": outcome})
    return {"score_2W_plus_T": int(2 * wins + ties), "wins": int(wins),
            "ties": int(ties), "losses": int(losses), "pairs": rows}


def classify(common_secondary: bool, control: Mapping[str, Any],
             candidate: Mapping[str, Any], *, valid: bool) -> dict[str, Any]:
    valid = (valid and control.get("finite") is True and
             candidate.get("finite") is True and
             type(control.get("hard_constraint_violations")) is int and
             control["hard_constraint_violations"] == 0 and
             type(candidate.get("hard_constraint_violations")) is int and
             candidate["hard_constraint_violations"] == 0)
    if not valid:
        return {"level": 1, "status": "EXECUTION_INVALID"}
    if not common_secondary:
        return {"level": 2, "status": "NO_COMMON_NULLSPACE_SECONDARY"}
    local_gain = (candidate["local_pair_score"] - control["local_pair_score"])
    if local_gain < 1:
        return {"level": 3, "status": "COMMON_SECONDARY_AVAILABLE",
                "local_pair_score_gain": local_gain}
    protected_ratios = {}
    for name in ("G", "F", "L_P", "L_judge"):
        denominator = float(control[name])
        numerator = float(candidate[name])
        if denominator > 0.0:
            protected_ratios[name] = numerator / denominator
        else:
            protected_ratios[name] = None
    protected = all(value is not None and value <= 1.10
                    for value in protected_ratios.values())
    balanced = (candidate["global_pair_score"] >= control["global_pair_score"]
                and candidate["hard_constraint_violations"] == 0 and protected)
    return {"level": 5 if balanced else 4,
            "status": "BALANCED_ONE_STEP_SIGNAL" if balanced
                      else "ONE_STEP_LOCAL_COMPONENT_SIGNAL",
            "local_pair_score_gain": local_gain, "protected_ratios": protected_ratios,
            "protected_ratios_ok": protected}
