"""Frozen S09-E009 four-arm update and scorecard primitives.

This module deliberately contains no producer launch path.  It implements the
reviewed numerical contract so it can be tested locally without running PIDL
training.  The producer runner must call these primitives unchanged.
"""
from __future__ import annotations

import copy
import hashlib
import math
import operator
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from s09_multiobjective_update import merge_objective_gradients


ARM_REPLAY = "R_current_pino_replay"
ARM_SCALAR = "S_data_only_scalar"
ARM_ANCHOR_0 = "A0_damage_anchor_beta0"
ARM_ANCHOR_25 = "A25_damage_anchor_beta0p25"
ARM_ORDER = (ARM_REPLAY, ARM_SCALAR, ARM_ANCHOR_0, ARM_ANCHOR_25)
LOSS_ORDER = ("l_d", "l_dr", "l_u", "l_h", "l_hr", "L_P")
GROUP_ORDER = ("L_D", "L_U", "L_H", "L_P")
NORM_EPSILON = 1e-12
GLOBAL_CLIP_NORM = 1.0


class AnchorStationary(RuntimeError):
    """The reviewed damage-anchor rule is inapplicable at this state."""


def _require_finite_same_shape(vectors: Sequence[torch.Tensor]) -> None:
    if not vectors:
        raise ValueError("at least one gradient vector is required")
    shape = vectors[0].shape
    if any(value.ndim != 1 or value.shape != shape for value in vectors):
        raise ValueError("gradient vectors must share one flattened layout")
    if any(not torch.isfinite(value).all() for value in vectors):
        raise FloatingPointError("nonfinite gradient vector")


def _stable_l2_norm(vector: torch.Tensor) -> torch.Tensor:
    """Evaluate a finite vector norm without squaring large values directly."""
    _require_finite_same_shape([vector])
    scale = vector.abs().max()
    if scale == 0:
        return scale
    norm = scale * torch.linalg.vector_norm(vector / scale)
    if not torch.isfinite(norm):
        raise FloatingPointError("nonfinite derived L2 norm")
    return norm


def clip_complete_direction(direction: torch.Tensor,
                            limit: float = GLOBAL_CLIP_NORM) -> tuple[torch.Tensor, dict[str, Any]]:
    """Apply the one reviewed global L2 clip to a complete update direction."""
    _require_finite_same_shape([direction])
    if not math.isfinite(limit) or limit <= 0:
        raise ValueError("clip limit must be finite and positive")
    before = _stable_l2_norm(direction)
    clipped = direction if before <= limit else direction * (limit / before)
    _require_finite_same_shape([clipped])
    after = _stable_l2_norm(clipped)
    return clipped, {
        "clip_limit": float(limit),
        "norm_before_clip": float(before.detach().cpu()),
        "norm_after_clip": float(after.detach().cpu()),
        "clip_applied": bool(before > limit),
        "clip_count_for_complete_direction": 1,
    }


def scalar_data_direction(groups: Mapping[str, torch.Tensor]) -> tuple[torch.Tensor, dict[str, Any]]:
    """Return the S direction: g_D + g_U + g_H, followed by one clip."""
    if tuple(groups) != GROUP_ORDER:
        raise ValueError("four named ordered group gradients are required")
    vectors = [groups[name] for name in GROUP_ORDER]
    _require_finite_same_shape(vectors)
    unclipped = groups["L_D"] + groups["L_U"] + groups["L_H"]
    _require_finite_same_shape([unclipped])
    clipped, clip = clip_complete_direction(unclipped)
    return clipped, {
        "arm": ARM_SCALAR,
        "physics_gradient_evaluated": True,
        "physics_contribution_coefficient": 0.0,
        "raw_group_norms": {name: float(_stable_l2_norm(value).detach().cpu())
                            for name, value in groups.items()},
        **clip,
    }


def damage_anchor_direction(groups: Mapping[str, torch.Tensor], *, beta: float,
                            eps: float = NORM_EPSILON) -> tuple[torch.Tensor, dict[str, Any]]:
    """Reviewed pre-projection equalisation, projection, merge and one clip."""
    if tuple(groups) != GROUP_ORDER:
        raise ValueError("four named ordered group gradients are required")
    if beta not in (0.0, 0.25):
        raise ValueError("reviewed beta must be 0 or 0.25")
    if not math.isfinite(eps) or eps <= 0:
        raise ValueError("epsilon must be finite and positive")
    vectors = [groups[name] for name in GROUP_ORDER]
    _require_finite_same_shape(vectors)
    anchor = groups["L_D"]
    anchor_norm = _stable_l2_norm(anchor)
    if anchor_norm <= eps:
        raise AnchorStationary("ANCHOR_STATIONARY_OR_INAPPLICABLE")

    projected: dict[str, torch.Tensor] = {}
    records: dict[str, Any] = {}
    for name in ("L_U", "L_H", "L_P"):
        raw = groups[name]
        raw_norm = _stable_l2_norm(raw)
        if raw_norm <= eps:
            balanced = torch.zeros_like(raw)
            projection = balanced
            reason = "AUXILIARY_NORM_AT_OR_BELOW_EPSILON"
        else:
            anchor_unit = anchor / anchor_norm
            raw_unit = raw / raw_norm
            cosine = anchor_unit.dot(raw_unit)
            if not torch.isfinite(cosine):
                raise FloatingPointError("nonfinite anchor cosine")
            balanced = anchor_norm * raw_unit
            projection = anchor_norm * (
                raw_unit - torch.minimum(cosine, cosine.new_zeros(())) * anchor_unit)
            _require_finite_same_shape([balanced, projection])
            if torch.count_nonzero(projection).item() == 0:
                reason = "FULLY_PROJECTED_TO_ZERO"
            elif _stable_l2_norm(projection) <= eps:
                reason = "PROJECTED_RESIDUAL_AT_OR_BELOW_EPSILON"
            else:
                reason = None
        balanced_norm = _stable_l2_norm(balanced)
        projected_norm = _stable_l2_norm(projection)
        anchor_dot_balanced = anchor.dot(balanced)
        anchor_dot_projected = anchor.dot(projection)
        if not (torch.isfinite(anchor_dot_balanced) and torch.isfinite(anchor_dot_projected)):
            raise FloatingPointError("nonfinite derived anchor dot product")
        projected[name] = projection
        records[name] = {
            "raw_norm": float(raw_norm.detach().cpu()),
            "balanced_norm": float(balanced_norm.detach().cpu()),
            "projected_norm": float(projected_norm.detach().cpu()),
            "anchor_dot_balanced": float(anchor_dot_balanced.detach().cpu()),
            "anchor_dot_projected": float(anchor_dot_projected.detach().cpu()),
            "zero_reason": reason,
        }

    merged = anchor + projected["L_U"] + projected["L_H"] + beta * projected["L_P"]
    _require_finite_same_shape([merged])
    anchor_dot_merged = anchor.dot(merged)
    anchor_norm_squared = anchor_norm.square()
    if not (torch.isfinite(anchor_dot_merged) and torch.isfinite(anchor_norm_squared)):
        raise FloatingPointError("nonfinite derived anchor diagnostic")
    clipped, clip = clip_complete_direction(merged)
    return clipped, {
        "arm": ARM_ANCHOR_0 if beta == 0 else ARM_ANCHOR_25,
        "beta": beta,
        "epsilon": eps,
        "anchor_norm": float(anchor_norm.detach().cpu()),
        "preclip_anchor_dot_merged": float(anchor_dot_merged.detach().cpu()),
        "preclip_anchor_norm_squared": float(anchor_norm_squared.detach().cpu()),
        "auxiliary": records,
        **clip,
    }


def atomic_losses(runtime: Any, index: int) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    """Evaluate the six reviewed atomic losses from one E008-compatible runtime."""
    from s09_fem_physics import boundary, equilibrium
    from s09_stage0a_p1_trainer import _example, hard_constraint_report
    from s09_stage0a_transition import raw_increment_objectives

    inputs, target = _example(runtime, index)
    d_pre, history_pre, path = inputs
    output = runtime.model(d_pre, history_pre, path, runtime.graph, runtime.conn,
                           runtime.shape, runtime.det)
    hard_constraint_report(runtime, d_pre, history_pre, output)
    nodal, gp = output["nodal_weight"], output["gp_weight"]

    def weighted_mse(error: torch.Tensor, weight: torch.Tensor) -> torch.Tensor:
        if error.ndim == weight.ndim:
            return (error.square() * weight).sum() / weight.sum()
        return (error.square() * weight[..., None]).sum(
            dim=tuple(range(error.ndim - 1))) / weight.sum()

    l_d = weighted_mse((output["d_peak"] - target["d_peak"]) / runtime.scales["d"], nodal)
    l_u = weighted_mse((output["u_peak"] - target["u_peak"]) / runtime.scales["u"], nodal).mean()
    l_h = weighted_mse(
        (output["history_peak"] - target["history_peak"]) / runtime.scales["history"], gp).mean()
    raw = raw_increment_objectives(output, target, d_pre, history_pre, runtime.model)
    force, _ = equilibrium(output["u_peak"], output["d_peak"], runtime.conn,
                           runtime.shape, runtime.dshape, runtime.det)
    free = boundary(runtime.graph["xy"])
    l_p = force[free].square().mean() / float(runtime.equilibrium_scale)
    losses = {"l_d": l_d, "l_dr": raw["raw_nodal_increment"], "l_u": l_u,
              "l_h": l_h, "l_hr": raw["raw_gp_increment"], "L_P": l_p}
    if tuple(losses) != LOSS_ORDER or any(value.ndim != 0 or not torch.isfinite(value)
                                           for value in losses.values()):
        raise FloatingPointError("invalid atomic loss record")
    return losses, {"output": output, "target": target, "d_pre": d_pre,
                    "history_pre": history_pre}


def grouped_losses(losses: Mapping[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    if tuple(losses) != LOSS_ORDER:
        raise ValueError("six named ordered atomic losses are required")
    return {"L_D": losses["l_d"] + losses["l_dr"], "L_U": losses["l_u"],
            "L_H": losses["l_h"] + losses["l_hr"], "L_P": losses["L_P"]}


def replay_losses(losses: Mapping[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    if tuple(losses) != LOSS_ORDER:
        raise ValueError("six named ordered atomic losses are required")
    return {"J_N": (losses["l_d"] + losses["l_u"]) / 2 + losses["l_dr"],
            "J_H": losses["l_h"] + losses["l_hr"], "J_P": losses["L_P"]}


def flattened_objective_gradients(model: torch.nn.Module,
                                  objectives: Mapping[str, torch.Tensor]) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    """Flatten named objective gradients with zeros for unconnected blocks."""
    named = list(model.named_parameters())
    if not named or len({name for name, _ in named}) != len(named):
        raise ValueError("invalid model parameter layout")
    if not objectives:
        raise ValueError("objective mapping is empty")
    records: dict[str, Any] = {}
    vectors: dict[str, torch.Tensor] = {}
    items = list(objectives.items())
    for objective_index, (objective_name, objective) in enumerate(items):
        if objective.ndim != 0 or not torch.isfinite(objective):
            raise FloatingPointError(f"invalid objective: {objective_name}")
        grads = torch.autograd.grad(objective, [parameter for _, parameter in named],
                                    allow_unused=True,
                                    retain_graph=objective_index < len(items) - 1)
        blocks, unconnected = [], []
        for (name, parameter), gradient in zip(named, grads):
            if gradient is None:
                gradient = torch.zeros_like(parameter)
                unconnected.append(name)
            if gradient.shape != parameter.shape or not torch.isfinite(gradient).all():
                raise FloatingPointError(f"invalid gradient block: {objective_name}/{name}")
            blocks.append(gradient.reshape(-1))
        vectors[objective_name] = torch.cat(blocks)
        records[objective_name] = {"unconnected_parameters": unconnected,
                                   "vector_length": vectors[objective_name].numel()}
    _require_finite_same_shape(list(vectors.values()))
    return vectors, {"parameter_order": [name for name, _ in named],
                     "objectives": records}


def arm_direction(model: torch.nn.Module, losses: Mapping[str, torch.Tensor],
                  arm: str) -> tuple[torch.Tensor, dict[str, Any]]:
    """Build one frozen complete direction without mutating parameters."""
    if arm not in ARM_ORDER:
        raise ValueError(f"unknown arm: {arm}")
    if arm == ARM_REPLAY:
        vectors, layout = flattened_objective_gradients(model, replay_losses(losses))
        replay_norms = torch.stack([value.norm() for value in vectors.values()])
        if not torch.isfinite(replay_norms).all():
            raise FloatingPointError("nonfinite norm at frozen replay-merger boundary")
        merged, old = merge_objective_gradients(
            list(vectors.values()), clip_norm=GLOBAL_CLIP_NORM, eps=NORM_EPSILON)
        _require_finite_same_shape([merged])
        diagnostic_names = (
            "raw_norms", "reference_norm", "merged_norm_before_clip",
            "merged_norm_after_clip", "balanced_norms", "projected_norms")
        if any(not torch.isfinite(torch.as_tensor(old[name])).all()
               for name in diagnostic_names):
            raise FloatingPointError("nonfinite frozen replay-merger diagnostic")
        return merged, {"arm": arm, "layout": layout,
                        "clip_count_for_complete_direction": 1,
                        "exact_replay_merger": old}
    groups = grouped_losses(losses)
    vectors, layout = flattened_objective_gradients(model, groups)
    if arm == ARM_SCALAR:
        merged, diagnostic = scalar_data_direction(vectors)
    else:
        merged, diagnostic = damage_anchor_direction(
            vectors, beta=0.0 if arm == ARM_ANCHOR_0 else 0.25)
    return merged, {**diagnostic, "layout": layout}


def flattened_parameters(model: torch.nn.Module) -> tuple[torch.Tensor, list[str]]:
    named = list(model.named_parameters())
    if not named or len({name for name, _ in named}) != len(named):
        raise ValueError("invalid model parameter layout")
    flat = torch.cat([parameter.detach().reshape(-1) for _, parameter in named]).clone()
    if not torch.isfinite(flat).all():
        raise FloatingPointError("nonfinite parameter state")
    return flat, [name for name, _ in named]


def parameter_state_sha256(model: torch.nn.Module) -> str:
    state = model.state_dict()
    digest = hashlib.sha256()
    for name, value in state.items():
        digest.update(name.encode("utf-8") + b"\0")
        array = np.ascontiguousarray(value.detach().cpu().numpy())
        digest.update(array.dtype.str.encode("ascii") + b"\0")
        digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
        digest.update(array.tobytes())
    return digest.hexdigest()


def initialise_arm_states(base_model: torch.nn.Module, *, learning_rate: float,
                          betas: tuple[float, float], optimizer_epsilon: float,
                          weight_decay: float) -> tuple[dict[str, torch.nn.Module],
                                                        dict[str, torch.optim.AdamW],
                                                        dict[str, Any]]:
    """Create byte-identical, object-independent models and empty AdamW states."""
    if not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("learning rate must be finite and positive")
    models = {arm: copy.deepcopy(base_model) for arm in ARM_ORDER}
    optimizers = {
        arm: torch.optim.AdamW(model.parameters(), lr=learning_rate, betas=betas,
                               eps=optimizer_epsilon, weight_decay=weight_decay)
        for arm, model in models.items()
    }
    hashes = {arm: parameter_state_sha256(model) for arm, model in models.items()}
    if len(set(hashes.values())) != 1:
        raise RuntimeError("arm model states are not byte-identical")
    parameter_ids = [{id(parameter) for parameter in model.parameters()} for model in models.values()]
    for left in range(len(parameter_ids)):
        for right in range(left + 1, len(parameter_ids)):
            if parameter_ids[left] & parameter_ids[right]:
                raise RuntimeError("arm models share parameter objects")
    if any(optimizer.state for optimizer in optimizers.values()):
        raise RuntimeError("new AdamW state is not empty")
    return models, optimizers, {"initial_state_sha256": hashes,
                                "optimizer_states_empty": True,
                                "parameter_objects_disjoint": True}


def parameter_displacement_alignment(g_d: torch.Tensor, before: torch.Tensor,
                                     after: torch.Tensor,
                                     eps: float = NORM_EPSILON) -> dict[str, Any]:
    """Measure g_D dot (-delta_theta) for the actual optimiser displacement."""
    _require_finite_same_shape([g_d, before, after])
    descent_displacement = before - after
    _require_finite_same_shape([descent_displacement])
    dot = g_d.dot(descent_displacement)
    if not torch.isfinite(dot):
        raise FloatingPointError("nonfinite displacement dot product")
    g_norm = _stable_l2_norm(g_d)
    displacement_norm = _stable_l2_norm(descent_displacement)
    if g_norm <= eps or displacement_norm <= eps:
        cosine = None
    else:
        cosine_tensor = (g_d / g_norm).dot(descent_displacement / displacement_norm)
        if not torch.isfinite(cosine_tensor):
            raise FloatingPointError("nonfinite displacement cosine")
        cosine = float(cosine_tensor.detach().cpu())
    return {
        "g_D_dot_negative_delta_theta": float(dot.detach().cpu()),
        "cosine": cosine,
        "displacement_norm": float(displacement_norm.detach().cpu()),
    }


def frozen_tolerance(reference: float) -> float:
    if not math.isfinite(reference):
        raise ValueError("reference must be finite")
    return 1e-12 + 1e-9 * abs(reference)


def safe_replay_ratio(candidate: float, reference: float) -> dict[str, Any]:
    candidate, reference = float(candidate), float(reference)
    if not (math.isfinite(candidate) and math.isfinite(reference)) or candidate < 0 or reference < 0:
        raise ValueError("ratio inputs must be finite and nonnegative")
    if reference > 0:
        value = candidate / reference
        if not math.isfinite(value):
            raise FloatingPointError("nonfinite replay ratio")
        return {"value": value, "status": "DEFINED"}
    if candidate == 0:
        return {"value": 1.0, "status": "BOTH_ZERO"}
    return {"value": None, "status": "REFERENCE_ZERO_CANDIDATE_POSITIVE"}


def group_amplitude_ratio(growth_mean: float, stagnant_mean: float) -> dict[str, Any]:
    growth_mean, stagnant_mean = float(growth_mean), float(stagnant_mean)
    if not (math.isfinite(growth_mean) and math.isfinite(stagnant_mean)):
        raise ValueError("group amplitudes must be finite")
    if growth_mean < 0 or stagnant_mean < 0:
        raise ValueError("group amplitudes must be nonnegative")
    if stagnant_mean > 0:
        value = growth_mean / stagnant_mean
        if not math.isfinite(value):
            raise FloatingPointError("nonfinite group amplitude ratio")
        return {"value": value, "status": "DEFINED"}
    if growth_mean == 0:
        return {"value": None, "status": "ZERO_AMPLITUDE_BOTH_GROUPS"}
    return {"value": None, "status": "ZERO_STAGNANT_AMPLITUDE"}


def amplitude_auc(growth: Sequence[float], stagnant: Sequence[float]) -> dict[str, Any]:
    if len(growth) != 5 or len(stagnant) != 5:
        raise ValueError("reviewed AUC requires five growth and five stagnant values")
    growth_values = [float(value) for value in growth]
    stagnant_values = [float(value) for value in stagnant]
    values = [*growth_values, *stagnant_values]
    if any(not math.isfinite(value) for value in values):
        raise ValueError("AUC amplitudes must be finite")
    wins = ties = losses = 0
    for left in growth_values:
        for right in stagnant_values:
            wins += left > right
            ties += left == right
            losses += left < right
    return {"value": float((wins + 0.5 * ties) / 25.0),
            "wins": int(wins), "ties": int(ties), "losses": int(losses)}


def fixed_support_median(records: Mapping[int, float | None],
                         cycles: Sequence[int]) -> dict[str, Any]:
    try:
        cycle_ids = tuple(operator.index(cycle) for cycle in cycles)
        record_ids = tuple(operator.index(cycle) for cycle in records)
    except TypeError as error:
        raise ValueError("cycle identifiers must be exact integers") from error
    if record_ids != cycle_ids:
        raise ValueError("spatial records must use the exact fixed cycle order")
    values = {operator.index(cycle): value for cycle, value in records.items()}
    valid = [(cycle, values[cycle]) for cycle in cycle_ids if values[cycle] is not None]
    if any(value is not None and not math.isfinite(float(value)) for value in records.values()):
        raise ValueError("spatial correlation must be finite or null")
    subset = None if not valid else float(np.median([float(value) for _, value in valid]))
    complete = len(valid) == len(cycles)
    return {
        "primary_median": subset if complete else None,
        "primary_status": "DEFINED" if complete else "NA",
        "valid_count": len(valid),
        "valid_cycles": [cycle for cycle, _ in valid],
        "valid_subset_median": subset,
    }


def classify_a25(candidate: Mapping[str, float], replay: Mapping[str, float]) -> dict[str, Any]:
    """Apply the reviewed performance hierarchy after validity/applicability."""
    required = ("G", "F", "AUC", "L_P", "L_judge", *LOSS_ORDER)
    if any(name not in candidate or name not in replay for name in required):
        raise ValueError("incomplete scorecard")
    if any(not math.isfinite(float(values[name])) or float(values[name]) < 0
           for values in (candidate, replay) for name in required):
        raise ValueError("scorecard metrics must be finite and nonnegative")
    if any(float(values["AUC"]) > 1 for values in (candidate, replay)):
        raise ValueError("AUC must be within [0, 1]")
    ratios = {name: safe_replay_ratio(float(candidate[name]), float(replay[name]))
              for name in ("G", "F", "L_P", "L_judge")}
    q_value = None
    if ratios["G"]["value"] is not None and ratios["F"]["value"] is not None:
        left, right = ratios["G"]["value"], ratios["F"]["value"]
        q_value = 0.0 if left == 0 or right == 0 else math.exp(
            (math.log(left) + math.log(right)) / 2)
        if not math.isfinite(q_value):
            raise FloatingPointError("nonfinite Q_damage")
    relative = (
        q_value is not None and q_value <= 0.80
        and ratios["G"]["value"] is not None and ratios["G"]["value"] <= 1.05
        and ratios["F"]["value"] is not None and ratios["F"]["value"] <= 1.05
        and candidate["AUC"] >= 0.80
        and ratios["L_P"]["value"] is not None and ratios["L_P"]["value"] <= 1.10
        and ratios["L_judge"]["value"] is not None and ratios["L_judge"]["value"] <= 1.05
    )
    improvements = {}
    for name in ("G", "F", "L_P", "L_judge", *LOSS_ORDER):
        delta = float(replay[name]) - float(candidate[name])
        improvements[name] = delta > frozen_tolerance(float(replay[name]))
    auc_delta = float(candidate["AUC"]) - float(replay["AUC"])
    improvements["AUC"] = auc_delta > frozen_tolerance(float(replay["AUC"]))
    baseline = 0.0005017354462152066
    nominate = relative and float(candidate["G"]) <= baseline - frozen_tolerance(baseline)
    if nominate:
        status = "NOMINATE_CONFIRMATORY_P1"
    elif relative:
        status = "RELATIVE_REPAIR_SIGNAL"
    elif any(improvements.values()):
        status = "COMPONENT_SIGNAL_OR_MIXED_TRADEOFF"
    else:
        status = "NO_REPAIR_SIGNAL"
    return {"status": status, "ratios": ratios, "Q_damage": q_value,
            "component_improvements": improvements,
            "persistence_baseline": baseline,
            "nomination_growth_limit": baseline - frozen_tolerance(baseline)}
