"""Pure no-I/O numerical core for the S09-E017 factorised-head pilot.

This module contains the reviewed factorised damage decoder, common decoded-
field observables, four objective helpers, frozen PCGrad merge and deterministic
profile classifier.  It deliberately contains no model forward, optimiser,
training loop, packet reader, producer launch or holdout access.
"""
from __future__ import annotations

from collections import OrderedDict
import math
import random
from typing import Any, Mapping, Sequence

import torch


ARM_DIRECT = "D_DIRECT"
ARM_AMPLITUDE = "F_AMP"
ARM_AMPLITUDE_SHAPE = "F_AMP_SHAPE"
ARM_ORDER = (ARM_DIRECT, ARM_AMPLITUDE, ARM_AMPLITUDE_SHAPE)

GROUP_ORDER = ("A", "S", "R", "P")
ACTIVE_GROUPS = {
    ARM_DIRECT: GROUP_ORDER,
    ARM_AMPLITUDE: ("A", "R", "P"),
    ARM_AMPLITUDE_SHAPE: GROUP_ORDER,
}
GROUP_WEIGHTS = {"A": 1.0, "S": 1.0, "R": 1.0, "P": 0.25}
SHAPE_SEED_EPSILON = 1.0e-6
GRADIENT_EPSILON = 1.0e-12
GLOBAL_CLIP_NORM = 1.0
FLOAT64_EPSILON = torch.finfo(torch.float64).eps

DISCRETE_COMPONENTS = {"A": (1,), "S": (0,), "R": (), "P": ()}
GROUP_COMPONENT_COUNTS = {"A": 2, "S": 6, "R": 2, "P": 4}
ROUNDTRIP_RTOL = 64.0 * FLOAT64_EPSILON


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _vector(value: torch.Tensor, name: str) -> torch.Tensor:
    _require(value.ndim == 1 and value.numel() > 0, f"{name} must be a vector")
    _require(value.dtype == torch.float64, f"{name} must be float64")
    _require(torch.isfinite(value).all().item(), f"{name} must be finite")
    return value


def normalised_weights(weights: torch.Tensor) -> torch.Tensor:
    value = _vector(weights, "nodal weights")
    _require(torch.all(value > 0).item(), "nodal weights must be strictly positive")
    total = value.sum()
    _require(torch.isfinite(total).item() and total > 0, "invalid nodal-weight sum")
    return value / total


def capacity_supported_seed(
    b25_shape: torch.Tensor,
    damage_pre: torch.Tensor,
    nodal_weight: torch.Tensor,
    *,
    epsilon: float = SHAPE_SEED_EPSILON,
) -> tuple[torch.Tensor, torch.Tensor, dict[str, float | int]]:
    """Construct the exact positive-mass entry seed on the capacity domain."""
    shape = _vector(b25_shape, "B25 shape")
    pre = _vector(damage_pre, "damage_pre")
    weights = normalised_weights(nodal_weight)
    _require(shape.shape == pre.shape == weights.shape, "seed input shape drift")
    _require(epsilon == SHAPE_SEED_EPSILON, "shape seed epsilon drift")
    _require(torch.all((pre >= 0) & (pre <= 1)).item(), "damage_pre outside [0,1]")
    _require(torch.all(shape >= 0).item(), "B25 shape must be nonnegative")
    capacity_mask = (1.0 - pre) > 0.0
    _require(capacity_mask.any().item(), "empty positive-capacity domain")
    _require(
        torch.all(shape[~capacity_mask] == 0).item(), "shape mass at zero capacity"
    )
    mass = torch.dot(weights, shape)
    _require(
        torch.isclose(
            mass,
            mass.new_tensor(1.0),
            atol=64.0 * FLOAT64_EPSILON,
            rtol=0.0,
        ).item(),
        "B25 shape is not weighted-normalised",
    )

    indicator = capacity_mask.to(torch.float64)
    uniform = indicator / torch.dot(weights, indicator)
    seed = (1.0 - epsilon) * shape + epsilon * uniform
    _require(
        torch.all(seed[capacity_mask] > 0).item(), "mass-entry seed is not positive"
    )
    _require(torch.all(seed[~capacity_mask] == 0).item(), "seed mass at zero capacity")
    seed_mass = torch.dot(weights, seed)
    tv = 0.5 * torch.dot(weights, torch.abs(seed - shape))
    _require(
        torch.isclose(
            seed_mass,
            seed_mass.new_tensor(1.0),
            atol=64.0 * FLOAT64_EPSILON,
            rtol=0.0,
        ).item(),
        "seed normalisation drift",
    )
    _require(tv <= epsilon + 64.0 * FLOAT64_EPSILON, "seed TV bound violated")
    return seed, uniform, {
        "epsilon": float(epsilon),
        "positive_capacity_nodes": int(capacity_mask.sum().item()),
        "weighted_total_variation": float(tv.detach().cpu()),
    }


def learnable_shape(
    seed_shape: torch.Tensor,
    logits: torch.Tensor,
    damage_pre: torch.Tensor,
    nodal_weight: torch.Tensor,
) -> torch.Tensor:
    """Capacity-mask and weighted-normalise ``seed * exp(logits)`` stably."""
    seed = _vector(seed_shape, "seed shape")
    z = _vector(logits, "shape logits")
    pre = _vector(damage_pre, "damage_pre")
    weights = normalised_weights(nodal_weight)
    _require(seed.shape == z.shape == pre.shape == weights.shape, "shape input drift")
    mask = (1.0 - pre) > 0.0
    _require(
        torch.all(seed[mask] > 0).item(), "seed must be positive on capacity domain"
    )
    _require(torch.all(seed[~mask] == 0).item(), "seed mass at zero capacity")

    log_mass = torch.log(seed[mask]) + z[mask]
    shift = log_mass.max()
    numerator = torch.exp(log_mass - shift)
    denominator = torch.dot(weights[mask], numerator)
    _require(
        torch.isfinite(denominator).item() and denominator > 0, "invalid shape mass"
    )
    shape = torch.zeros_like(seed)
    shape[mask] = numerator / denominator
    _require(torch.isfinite(shape).all().item(), "nonfinite learned shape")
    return shape


def amplitude_from_residual(
    baseline_amplitude: torch.Tensor, residual: torch.Tensor
) -> torch.Tensor:
    """Positive amplitude parameterisation with exact zero-residual replay."""
    _require(baseline_amplitude.ndim == residual.ndim == 0, "amplitude must be scalar")
    _require(
        baseline_amplitude.dtype == residual.dtype == torch.float64,
        "amplitude must be float64",
    )
    _require(
        torch.isfinite(baseline_amplitude).item()
        and torch.isfinite(residual).item()
        and baseline_amplitude > 0,
        "invalid amplitude parameter",
    )
    value = baseline_amplitude * torch.exp(residual)
    _require(torch.isfinite(value).item() and value >= 0, "nonfinite head amplitude")
    return value


def decode_factorised_increment(
    damage_pre: torch.Tensor,
    amplitude: torch.Tensor,
    shape: torch.Tensor,
) -> torch.Tensor:
    """Decode a bounded irreversible damage increment."""
    pre = _vector(damage_pre, "damage_pre")
    field = _vector(shape, "shape")
    _require(pre.shape == field.shape, "decoder shape drift")
    _require(
        amplitude.ndim == 0 and amplitude.dtype == torch.float64, "invalid amplitude"
    )
    _require(torch.isfinite(amplitude).item() and amplitude >= 0, "invalid amplitude")
    _require(torch.all((pre >= 0) & (pre <= 1)).item(), "damage_pre outside [0,1]")
    _require(torch.all(field >= 0).item(), "shape must be nonnegative")
    capacity = torch.clamp(1.0 - pre, min=0.0, max=1.0)
    _require(torch.all(field[capacity == 0] == 0).item(), "shape mass at zero capacity")
    increment = capacity * (-torch.expm1(-amplitude * field))
    _require(torch.isfinite(increment).all().item(), "nonfinite decoded increment")
    _require(
        torch.all((increment >= 0) & (increment <= capacity)).item(),
        "decoder bound failure",
    )
    return increment


def effective_factorisation(
    damage_pre: torch.Tensor,
    increment: torch.Tensor,
    nodal_weight: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, bool]:
    """Differentiably recover the common E016 hazard observables from a field."""
    pre = _vector(damage_pre, "damage_pre")
    delta = _vector(increment, "damage increment")
    weights = normalised_weights(nodal_weight)
    _require(pre.shape == delta.shape == weights.shape, "factorisation shape drift")
    capacity = torch.clamp(1.0 - pre, min=0.0, max=1.0)
    _require(
        torch.all((delta >= 0) & (delta <= capacity)).item(),
        "increment outside capacity",
    )
    usable = capacity > 0
    q = torch.zeros_like(delta)
    q_max = torch.nextafter(delta.new_tensor(1.0), delta.new_tensor(0.0))
    q[usable] = torch.clamp(delta[usable] / capacity[usable], min=0.0, max=q_max)
    hazard = -torch.log1p(-q)
    amplitude = torch.dot(weights, hazard)
    _require(
        torch.isfinite(amplitude).item() and amplitude >= 0,
        "invalid effective amplitude",
    )
    positive_event = bool(torch.any(delta > 0).detach().cpu())
    valid = bool(amplitude.detach().cpu() > 0)
    if not valid:
        _require(not positive_event, "positive event lost by numerical factorisation")
        shape = torch.zeros_like(hazard)
    else:
        shape = hazard / amplitude
        _require(
            torch.isfinite(shape).all().item() and torch.all(shape >= 0).item(),
            "invalid effective shape",
        )
        shape_mass = torch.dot(weights, shape)
        _require(
            torch.isfinite(shape_mass).item()
            and torch.abs(shape_mass - 1.0) <= ROUNDTRIP_RTOL,
            "weighted shape normalisation drift",
        )

    reconstructed = capacity * (-torch.expm1(-amplitude * shape))
    encoded = capacity * q
    residual = reconstructed - encoded
    positive_encoded = encoded > 0
    _require(
        torch.all(residual[~positive_encoded] == 0).item(),
        "zero encoded increment did not round trip exactly",
    )
    if positive_encoded.any():
        relative = torch.abs(residual[positive_encoded]) / encoded[positive_encoded]
        _require(
            torch.isfinite(relative).all().item()
            and torch.all(relative <= ROUNDTRIP_RTOL).item(),
            "effective factorisation round-trip drift",
        )
    return amplitude, shape, valid


def amplitude_objective(
    predicted: torch.Tensor,
    target: torch.Tensor,
    amplitude_scale: float,
    pair_indices: Sequence[tuple[int, int]],
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Equal-weight scalar scaled-log and signed pair-contrast regression."""
    pred = _vector(predicted, "predicted amplitudes")
    truth = _vector(target, "target amplitudes")
    _require(pred.shape == truth.shape, "amplitude target shape drift")
    _require(torch.all((pred >= 0) & (truth >= 0)).item(), "negative amplitude")
    _require(math.isfinite(amplitude_scale) and amplitude_scale > 0, "invalid A_scale")
    _require(bool(pair_indices), "pair set is empty")
    z_pred = torch.log1p(pred / amplitude_scale)
    z_target = torch.log1p(truth / amplitude_scale)
    scalar = torch.mean((z_pred - z_target).square())
    pair_terms = []
    for first, second in pair_indices:
        _require(0 <= first < len(pred) and 0 <= second < len(pred), "pair index drift")
        pair_terms.append(
            (
                (z_pred[first] - z_pred[second]) - (z_target[first] - z_target[second])
            ).square()
        )
    pair = torch.stack(pair_terms).mean()
    value = 0.5 * (scalar + pair)
    _require(torch.isfinite(value).item(), "nonfinite amplitude objective")
    return value, {"scalar": scalar, "pair_contrast": pair}


def shape_objective(
    predicted_shape: torch.Tensor,
    target_shape: torch.Tensor,
    nodal_weight: torch.Tensor,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Equal-weight support-free half-L1 and one-minus-cosine objective."""
    predicted = _vector(predicted_shape, "predicted shape")
    target = _vector(target_shape, "target shape")
    weights = normalised_weights(nodal_weight)
    _require(predicted.shape == target.shape == weights.shape, "shape objective drift")
    _require(torch.all((predicted >= 0) & (target >= 0)).item(), "negative shape")
    half_l1 = 0.5 * torch.dot(weights, torch.abs(predicted - target))
    wp = torch.sqrt(weights) * predicted
    wt = torch.sqrt(weights) * target
    denominator = torch.linalg.vector_norm(wp) * torch.linalg.vector_norm(wt)
    _require(denominator > 0, "undefined shape objective")
    cosine_error = 1.0 - torch.dot(wp, wt) / denominator
    value = 0.5 * (half_l1 + cosine_error)
    _require(torch.isfinite(value).item(), "nonfinite shape objective")
    return value, {"half_l1": half_l1, "one_minus_cosine": cosine_error}


def reconstruction_objective(
    predicted_increment: torch.Tensor,
    target_increment: torch.Tensor,
    nodal_weight: torch.Tensor,
    frozen_cycle_scale: torch.Tensor,
) -> torch.Tensor:
    """Mean cycle-balanced weighted MSE with precomputed positive scales."""
    _require(
        predicted_increment.ndim == target_increment.ndim == 2,
        "reconstruction fields must be [cycle,node]",
    )
    _require(
        predicted_increment.shape == target_increment.shape,
        "reconstruction target shape drift",
    )
    _require(
        predicted_increment.dtype == target_increment.dtype == torch.float64,
        "reconstruction fields must be float64",
    )
    _require(
        torch.isfinite(predicted_increment).all().item()
        and torch.isfinite(target_increment).all().item(),
        "nonfinite reconstruction field",
    )
    scales = _vector(frozen_cycle_scale, "frozen cycle scale")
    _require(scales.shape == (len(predicted_increment),), "cycle-scale shape drift")
    _require(torch.all(scales > 0).item(), "cycle scales must be positive")
    weights = normalised_weights(nodal_weight)
    _require(weights.shape == (predicted_increment.shape[1],), "weight shape drift")
    error = (predicted_increment - target_increment) / scales[:, None]
    value = (error.square() * weights[None, :]).sum(dim=1).mean()
    _require(torch.isfinite(value).item(), "nonfinite reconstruction objective")
    return value


def freeze_gradient_scales(
    gradients: Mapping[str, torch.Tensor],
    *,
    epsilon: float = GRADIENT_EPSILON,
) -> tuple[OrderedDict[str, float], dict[str, bool]]:
    """Freeze update-zero norms, using one only for near-zero groups."""
    _require(
        tuple(gradients) in tuple(ACTIVE_GROUPS.values()), "active group order drift"
    )
    _require(epsilon == GRADIENT_EPSILON, "gradient epsilon drift")
    vectors = [_vector(value, name) for name, value in gradients.items()]
    _require(
        len({tuple(value.shape) for value in vectors}) == 1, "gradient shape drift"
    )
    scales: OrderedDict[str, float] = OrderedDict()
    zero_scale: dict[str, bool] = {}
    for name, value in gradients.items():
        norm_tensor = torch.linalg.vector_norm(value)
        _require(torch.isfinite(norm_tensor).item(), "nonfinite frozen gradient norm")
        norm = float(norm_tensor.detach().cpu())
        zero = norm <= epsilon
        scales[name] = 1.0 if zero else norm
        zero_scale[name] = zero
    return scales, zero_scale


def pcgrad_merge(
    gradients: Mapping[str, torch.Tensor],
    scales: Mapping[str, float],
    *,
    seed: int,
    update: int,
    epsilon: float = GRADIENT_EPSILON,
    clip_norm: float = GLOBAL_CLIP_NORM,
) -> tuple[torch.Tensor, dict[str, Any]]:
    """Apply the frozen weighted-normalised PCGrad contract to flat gradients."""
    names = tuple(gradients)
    _require(names in tuple(ACTIVE_GROUPS.values()), "active group order drift")
    _require(tuple(scales) == names, "gradient scale order drift")
    _require(
        isinstance(seed, int)
        and not isinstance(seed, bool)
        and isinstance(update, int)
        and not isinstance(update, bool)
        and update >= 0,
        "invalid seed/update",
    )
    _require(
        epsilon == GRADIENT_EPSILON and clip_norm == GLOBAL_CLIP_NORM,
        "merge constant drift",
    )
    vectors = [_vector(value, name) for name, value in gradients.items()]
    _require(
        len({tuple(value.shape) for value in vectors}) == 1, "gradient shape drift"
    )

    scaled: OrderedDict[str, torch.Tensor] = OrderedDict()
    for name, gradient in gradients.items():
        scale = float(scales[name])
        _require(math.isfinite(scale) and scale > 0, "invalid frozen gradient scale")
        scaled_value = GROUP_WEIGHTS[name] * gradient / scale
        _require(torch.isfinite(scaled_value).all().item(), "nonfinite scaled gradient")
        scaled[name] = scaled_value

    pairwise: list[dict[str, Any]] = []
    for first_index, first_name in enumerate(names):
        for second_name in names[first_index + 1 :]:
            entry: dict[str, Any] = {"first": first_name, "second": second_name}
            for label, collection in (("raw", gradients), ("scaled", scaled)):
                first = collection[first_name]
                second = collection[second_name]
                dot = torch.dot(first, second)
                first_norm = torch.linalg.vector_norm(first)
                second_norm = torch.linalg.vector_norm(second)
                denominator = first_norm * second_norm
                _require(
                    torch.isfinite(dot).item()
                    and torch.isfinite(first_norm).item()
                    and torch.isfinite(second_norm).item()
                    and torch.isfinite(denominator).item(),
                    "nonfinite PCGrad pairwise geometry",
                )
                cosine = (
                    None
                    if denominator <= epsilon
                    else float((dot / denominator).detach().cpu())
                )
                entry[label] = {
                    "dot": float(dot.detach().cpu()),
                    "cosine": cosine,
                    "conflict": bool(dot.detach().cpu() < 0),
                }
            pairwise.append(entry)

    order = list(names)
    random.Random(seed + update).shuffle(order)
    projected: OrderedDict[str, torch.Tensor] = OrderedDict()
    logs: dict[str, list[dict[str, Any]]] = {}
    for name in names:
        working = scaled[name].clone()
        entries = []
        for reference_name in order:
            if reference_name == name:
                continue
            reference = scaled[reference_name]
            denominator = torch.dot(reference, reference)
            _require(
                torch.isfinite(denominator).item(),
                "nonfinite PCGrad projection geometry",
            )
            skipped = bool(torch.sqrt(denominator).detach().cpu() <= epsilon)
            dot_before = torch.dot(working, reference)
            _require(
                torch.isfinite(dot_before).item(),
                "nonfinite PCGrad projection geometry",
            )
            applied = False
            if not skipped and dot_before < 0:
                working = working - dot_before / denominator * reference
                _require(
                    torch.isfinite(working).all().item(),
                    "nonfinite projected gradient",
                )
                applied = True
            entries.append(
                {
                    "reference": reference_name,
                    "skipped_near_zero": skipped,
                    "projection_applied": applied,
                    "dot_before": float(dot_before.detach().cpu()),
                }
            )
        projected[name] = working
        logs[name] = entries

    merged = torch.stack(tuple(projected.values())).mean(dim=0)
    _require(torch.isfinite(merged).all().item(), "nonfinite PCGrad direction")
    preclip_norm = torch.linalg.vector_norm(merged)
    _require(torch.isfinite(preclip_norm).item(), "nonfinite PCGrad preclip norm")
    if preclip_norm > clip_norm:
        merged = merged * (clip_norm / preclip_norm)
    _require(torch.isfinite(merged).all().item(), "nonfinite PCGrad direction")
    postclip_norm = torch.linalg.vector_norm(merged)
    _require(torch.isfinite(postclip_norm).item(), "nonfinite PCGrad postclip norm")

    diagnostic_norms: dict[str, dict[str, float]] = {}
    for label, collection in (
        ("raw", gradients),
        ("scaled", scaled),
        ("projected", projected),
    ):
        values: dict[str, float] = {}
        for name, value in collection.items():
            norm = torch.linalg.vector_norm(value)
            _require(
                torch.isfinite(norm).item(), f"nonfinite {label} diagnostic norm"
            )
            values[name] = float(norm.detach().cpu())
        diagnostic_norms[label] = values

    raw_dot_merged: dict[str, float] = {}
    for name, value in gradients.items():
        dot = torch.dot(value, merged)
        _require(
            torch.isfinite(dot).item(), "nonfinite raw-group merged-direction dot"
        )
        raw_dot_merged[name] = float(dot.detach().cpu())
    return merged, {
        "seed": seed,
        "update": update,
        "permutation": order,
        "frozen_scales": {name: float(scales[name]) for name in names},
        "weights": {name: GROUP_WEIGHTS[name] for name in names},
        "active_group_count": len(names),
        "preclip_norm": float(preclip_norm.detach().cpu()),
        "postclip_norm": float(postclip_norm.detach().cpu()),
        "projection_log": logs,
        "pairwise_geometry": pairwise,
        "raw_norms": diagnostic_norms["raw"],
        "scaled_norms": diagnostic_norms["scaled"],
        "projected_norms": diagnostic_norms["projected"],
        "raw_group_dot_merged_direction": raw_dot_merged,
    }


def amplitude_priority_pcgrad_merge(
    gradients: Mapping[str, torch.Tensor],
    scales: Mapping[str, float],
    *,
    seed: int,
    update: int,
    epsilon: float = GRADIENT_EPSILON,
    clip_norm: float = GLOBAL_CLIP_NORM,
) -> tuple[torch.Tensor, dict[str, Any]]:
    """Merge factorised-head gradients without allowing secondary groups to oppose A.

    The symmetric PCGrad projection is retained for all secondary objectives.
    Its aggregate is then projected out of the negative half-space of the
    scaled amplitude direction.  This produces a first-order descent direction
    for ``A`` while retaining every secondary objective as far as that protected
    constraint permits.
    """
    names = tuple(gradients)
    _require(
        names == ACTIVE_GROUPS[ARM_AMPLITUDE_SHAPE],
        "amplitude-priority merge requires factorised amplitude-plus-shape groups",
    )
    symmetric, diagnostics = pcgrad_merge(
        gradients,
        scales,
        seed=seed,
        update=update,
        epsilon=epsilon,
        clip_norm=clip_norm,
    )
    del symmetric
    scaled = OrderedDict(
        (
            name,
            GROUP_WEIGHTS[name] * gradients[name] / float(scales[name]),
        )
        for name in names
    )
    projected: OrderedDict[str, torch.Tensor] = OrderedDict()
    for name in names:
        working = scaled[name].clone()
        for entry in diagnostics["projection_log"][name]:
            reference = scaled[entry["reference"]]
            if entry["projection_applied"]:
                denominator = torch.dot(reference, reference)
                working = (
                    working - torch.dot(working, reference) / denominator * reference
                )
        projected[name] = working
    amplitude = scaled["A"]
    secondary = torch.stack(
        tuple(projected[name] for name in names if name != "A")
    ).mean(dim=0)
    denominator = torch.dot(amplitude, amplitude)
    _require(
        torch.isfinite(denominator).item(), "nonfinite amplitude priority geometry"
    )
    dot_before = torch.dot(secondary, amplitude)
    _require(
        torch.isfinite(dot_before).item(), "nonfinite amplitude priority geometry"
    )
    priority_projection_applied = False
    if torch.sqrt(denominator) > epsilon and dot_before < 0:
        secondary = secondary - dot_before / denominator * amplitude
        priority_projection_applied = True
    merged = amplitude + secondary
    preclip_norm = torch.linalg.vector_norm(merged)
    _require(torch.isfinite(preclip_norm).item(), "nonfinite amplitude priority direction")
    if preclip_norm > clip_norm:
        merged = merged * (clip_norm / preclip_norm)
    postclip_norm = torch.linalg.vector_norm(merged)
    _require(torch.isfinite(postclip_norm).item(), "nonfinite amplitude priority direction")
    _require(
        torch.dot(merged, amplitude) >= -epsilon,
        "amplitude-priority merge opposes amplitude",
    )
    result = dict(diagnostics)
    result.update(
        {
            "merge_strategy": "AMPLITUDE_PRIORITY_PCG",
            "preclip_norm": float(preclip_norm.detach().cpu()),
            "postclip_norm": float(postclip_norm.detach().cpu()),
            "amplitude_priority": {
                "dot_before": float(dot_before.detach().cpu()),
                "projection_applied": priority_projection_applied,
                "merged_dot_scaled_amplitude": float(
                    torch.dot(merged, amplitude).detach().cpu()
                ),
            },
        }
    )
    return merged, result


def decision_amplitude_error(
    predicted: torch.Tensor, target: torch.Tensor, amplitude_scale: float
) -> torch.Tensor:
    """Zero-compatible per-cycle amplitude error used by the verdict."""
    pred = _vector(predicted, "predicted amplitudes")
    truth = _vector(target, "target amplitudes")
    _require(pred.shape == truth.shape, "amplitude decision shape drift")
    _require(torch.all((pred >= 0) & (truth >= 0)).item(), "negative amplitude")
    _require(math.isfinite(amplitude_scale) and amplitude_scale > 0, "invalid A_scale")
    value = torch.abs(
        torch.log1p(pred / amplitude_scale) - torch.log1p(truth / amplitude_scale)
    )
    _require(torch.isfinite(value).all().item(), "nonfinite amplitude decision error")
    return value


def decision_shape_values(
    raw_values: Sequence[float | None], *, predicted_shape_valid: bool
) -> tuple[tuple[float | None, ...], tuple[float, ...]]:
    """Preserve raw NA while supplying the reviewed finite decision penalties."""
    _require(len(raw_values) == 5, "five raw shape metrics are required")
    if predicted_shape_valid:
        _require(
            all(value is not None and math.isfinite(value) for value in raw_values),
            "valid shape requires finite metrics",
        )
        return tuple(raw_values), (0.0, *(float(value) for value in raw_values))
    _require(
        all(value is None for value in raw_values),
        "undefined shape raw metrics must be NA",
    )
    return tuple(raw_values), (1.0, 1.0, 1.0, 1.0, 1.0, 1.0)


def _tolerance(first: float, second: float, *, discrete: bool) -> float:
    if discrete:
        return 0.0
    return max(
        1.0e-12, 64.0 * float(FLOAT64_EPSILON) * max(1.0, abs(first), abs(second))
    )


def _signs(
    first: Sequence[float], second: Sequence[float], discrete: set[int]
) -> tuple[int, ...]:
    _require(len(first) == len(second) and len(first) > 0, "comparison vector drift")
    result = []
    for index, (left, right) in enumerate(zip(first, second, strict=True)):
        _require(
            math.isfinite(left) and math.isfinite(right), "nonfinite decision metric"
        )
        tolerance = _tolerance(left, right, discrete=index in discrete)
        difference = left - right
        result.append(
            -1 if difference < -tolerance else 1 if difference > tolerance else 0
        )
    return tuple(result)


def _pareto_dominates(
    first: Sequence[float], second: Sequence[float], discrete: set[int]
) -> bool:
    signs = _signs(first, second, discrete)
    return -1 in signs and 1 not in signs


def _no_worse(
    first: Sequence[float], second: Sequence[float], discrete: set[int]
) -> bool:
    return 1 not in _signs(first, second, discrete)


def _concatenate(
    values: Mapping[str, Sequence[float]], groups: Sequence[str]
) -> tuple[tuple[float, ...], set[int]]:
    flat: list[float] = []
    discrete: set[int] = set()
    for group in groups:
        offset = len(flat)
        flat.extend(float(value) for value in values[group])
        discrete.update(offset + index for index in DISCRETE_COMPONENTS[group])
    return tuple(flat), discrete


def classify_profiles(
    errors: Mapping[str, Mapping[int, Mapping[str, Sequence[float]]]],
    *,
    execution_valid: bool,
) -> dict[str, bool]:
    """Evaluate the exact deterministic multi-label update-64 profiles."""
    names = (
        "VALID_FACTORISATION_SIGNAL",
        "VALID_SHAPE_OBJECTIVE_SIGNAL",
        "VALID_AMPLITUDE_ONLY_SIGNAL",
        "VALID_NO_HEAD_SEPARATION",
        "VALID_MIXED_TRADEOFF",
        "INVALID_EXECUTION",
    )
    if not execution_valid:
        return {name: name == "INVALID_EXECUTION" for name in names}
    _require(tuple(errors) == ARM_ORDER, "arm order drift")
    for arm in ARM_ORDER:
        _require(tuple(errors[arm]) == (0, 64), f"evaluation schedule drift: {arm}")
        for update in (0, 64):
            _require(
                tuple(errors[arm][update]) == GROUP_ORDER, "metric group order drift"
            )
            for group in GROUP_ORDER:
                values = errors[arm][update][group]
                _require(
                    len(values) == GROUP_COMPONENT_COUNTS[group],
                    f"metric component width drift: {group}",
                )
                for index in DISCRETE_COMPONENTS[group]:
                    count = values[index]
                    _require(
                        isinstance(count, (int, float))
                        and not isinstance(count, bool)
                        and math.isfinite(float(count))
                        and float(count).is_integer(),
                        f"noninteger decision count: {group}",
                    )
                    upper = 25 if group == "A" else 16
                    _require(
                        0 <= int(count) <= upper,
                        f"decision count outside range: {group}",
                    )

    start: dict[str, dict[str, tuple[float, ...]]] = {}
    end: dict[str, dict[str, tuple[float, ...]]] = {}
    change: dict[str, dict[str, tuple[float, ...]]] = {}
    for arm in ARM_ORDER:
        start[arm], end[arm], change[arm] = {}, {}, {}
        for group in GROUP_ORDER:
            begin = tuple(float(value) for value in errors[arm][0][group])
            finish = tuple(float(value) for value in errors[arm][64][group])
            _signs(begin, finish, set(DISCRETE_COMPONENTS[group]))
            start[arm][group], end[arm][group] = begin, finish
            change[arm][group] = tuple(
                b - a for a, b in zip(begin, finish, strict=True)
            )

    zero = {
        group: tuple(0.0 for _ in change[ARM_DIRECT][group]) for group in GROUP_ORDER
    }
    d, fa, fas = ARM_DIRECT, ARM_AMPLITUDE, ARM_AMPLITUDE_SHAPE

    fas_asr, asr_discrete = _concatenate(change[fas], ("A", "S", "R"))
    d_asr, _ = _concatenate(change[d], ("A", "S", "R"))
    fas_end_asr, _ = _concatenate(end[fas], ("A", "S", "R"))
    d_end_asr, _ = _concatenate(end[d], ("A", "S", "R"))
    factorisation = (
        _pareto_dominates(change[fas]["A"], zero["A"], set(DISCRETE_COMPONENTS["A"]))
        and _pareto_dominates(
            change[fas]["S"], zero["S"], set(DISCRETE_COMPONENTS["S"])
        )
        and _pareto_dominates(fas_asr, d_asr, asr_discrete)
        and _no_worse(fas_end_asr, d_end_asr, asr_discrete)
        and _no_worse(change[fas]["P"], change[d]["P"], set())
        and _no_worse(end[fas]["P"], end[d]["P"], set())
    )

    shape_signal = (
        _pareto_dominates(
            change[fas]["S"], change[fa]["S"], set(DISCRETE_COMPONENTS["S"])
        )
        and _no_worse(end[fas]["S"], end[fa]["S"], set(DISCRETE_COMPONENTS["S"]))
        and _no_worse(change[fas]["A"], change[fa]["A"], set(DISCRETE_COMPONENTS["A"]))
        and _no_worse(end[fas]["A"], end[fa]["A"], set(DISCRETE_COMPONENTS["A"]))
    )
    amplitude_only = (
        _pareto_dominates(change[fa]["A"], zero["A"], set(DISCRETE_COMPONENTS["A"]))
        and _pareto_dominates(
            change[fa]["A"], change[fas]["A"], set(DISCRETE_COMPONENTS["A"])
        )
        and _no_worse(end[fa]["A"], end[fas]["A"], set(DISCRETE_COMPONENTS["A"]))
    )

    separation = []
    for arm in (fa, fas):
        arm_change, discrete = _concatenate(change[arm], ("A", "S", "R"))
        arm_end, _ = _concatenate(end[arm], ("A", "S", "R"))
        separation.append(
            _pareto_dominates(arm_change, d_asr, discrete)
            and _no_worse(arm_end, d_end_asr, discrete)
        )
    no_separation = not any(separation)

    all_groups = ("A", "S", "R", "P")
    mixed = False
    change_vectors: dict[str, tuple[tuple[float, ...], set[int]]] = {}
    for arm in ARM_ORDER:
        vector, discrete = _concatenate(change[arm], all_groups)
        change_vectors[arm] = (vector, discrete)
        signs = _signs(vector, tuple(0.0 for _ in vector), discrete)
        mixed = mixed or (-1 in signs and 1 in signs)
    for index, first in enumerate(ARM_ORDER):
        for second in ARM_ORDER[index + 1 :]:
            vector_first, discrete = change_vectors[first]
            vector_second, _ = change_vectors[second]
            signs = _signs(vector_first, vector_second, discrete)
            mixed = mixed or (-1 in signs and 1 in signs)

    return {
        "VALID_FACTORISATION_SIGNAL": factorisation,
        "VALID_SHAPE_OBJECTIVE_SIGNAL": shape_signal,
        "VALID_AMPLITUDE_ONLY_SIGNAL": amplitude_only,
        "VALID_NO_HEAD_SEPARATION": no_separation,
        "VALID_MIXED_TRADEOFF": mixed,
        "INVALID_EXECUTION": False,
    }
