"""Gradient diagnostics and two-objective update rules for S09.

The helpers operate on already-computed parameter gradients.  They contain no
optimizer step and are kept independent of the full native mesh so the
multi-objective algebra can be tested cheaply on Mac.
"""
from __future__ import annotations

from collections import defaultdict

import torch


GROUP_PREFIXES = {
    "encoder": ("encoder.",),
    "local": ("blocks.",),
    "coarse": ("coarse.",),
    "decoder": ("decoder.",),
}


def parameter_group(name: str) -> str:
    for group, prefixes in GROUP_PREFIXES.items():
        if name.startswith(prefixes):
            return group
    return "other"


def _validate_gradients(named_parameters, data_gradients, physics_gradients):
    named_parameters = list(named_parameters)
    data_gradients = list(data_gradients)
    physics_gradients = list(physics_gradients)
    if not (len(named_parameters) == len(data_gradients) == len(physics_gradients)):
        raise ValueError("parameter and gradient sequence lengths differ")
    seen = defaultdict(lambda: {"tensors": 0, "coordinates": 0})
    for (name, parameter), gd, gp in zip(named_parameters, data_gradients, physics_gradients):
        group = parameter_group(name)
        if group == "other":
            raise ValueError(f"unexpected parameter group for {name}")
        if gd is None or gp is None:
            raise ValueError(f"missing gradient for {name}")
        if gd.shape != parameter.shape or gp.shape != parameter.shape:
            raise ValueError(f"gradient shape mismatch for {name}")
        if not torch.isfinite(gd).all() or not torch.isfinite(gp).all():
            raise ValueError(f"non-finite gradient for {name}")
        seen[group]["tensors"] += 1
        seen[group]["coordinates"] += parameter.numel()
    missing = sorted(set(GROUP_PREFIXES) - set(seen))
    if missing:
        raise ValueError(f"missing declared parameter groups: {missing}")
    return named_parameters, data_gradients, physics_gradients, dict(seen)


def _positive_norm(gradients, label):
    norm = torch.sqrt(sum(g.detach().double().square().sum() for g in gradients))
    if not torch.isfinite(norm) or float(norm) <= 0.0:
        raise ValueError(f"{label} gradient norm is zero or non-finite")
    return norm


def gradient_statistics(named_parameters, data_gradients, physics_gradients):
    """Return global and blockwise norm ratios/cosines without changing grads."""
    named_parameters, data_gradients, physics_gradients, coverage = _validate_gradients(
        named_parameters, data_gradients, physics_gradients
    )
    accum = defaultdict(lambda: {"data_sq": 0.0, "physics_sq": 0.0, "dot": 0.0})
    for (name, _), gd, gp in zip(named_parameters, data_gradients, physics_gradients):
        values = (gd.detach().double(), gp.detach().double())
        for group in ("global", parameter_group(name)):
            accum[group]["data_sq"] += float(values[0].square().sum())
            accum[group]["physics_sq"] += float(values[1].square().sum())
            accum[group]["dot"] += float((values[0] * values[1]).sum())
    result = {}
    for group, item in accum.items():
        nd = item["data_sq"] ** 0.5
        np_ = item["physics_sq"] ** 0.5
        if not (nd > 0.0 and np_ > 0.0):
            raise ValueError(f"undefined gradient statistic for zero-norm group {group}")
        denom = nd * np_
        result[group] = {
            "data_norm": nd,
            "physics_norm": np_,
            "physics_to_data_norm": np_ / nd,
            "dot": item["dot"],
            "cosine": item["dot"] / denom,
            "parameter_tensors": coverage.get(group, {}).get(
                "tensors", sum(item["tensors"] for item in coverage.values())
            ),
            "parameter_coordinates": coverage.get(group, {}).get(
                "coordinates", sum(item["coordinates"] for item in coverage.values())
            ),
        }
    return result


def linearized_changes(data_gradients, physics_gradients, direction):
    """First-order loss changes for a unit learning-rate step ``-direction``."""
    if not (len(data_gradients) == len(physics_gradients) == len(direction)):
        raise ValueError("gradient and direction sequence lengths differ")
    for index, (gd, gp, step) in enumerate(zip(data_gradients, physics_gradients, direction)):
        if gd.shape != gp.shape or gd.shape != step.shape:
            raise ValueError(f"direction shape mismatch at index {index}")
        if not torch.isfinite(gd).all() or not torch.isfinite(gp).all() or not torch.isfinite(step).all():
            raise ValueError(f"non-finite direction input at index {index}")
    data_dot = sum(float((gd.detach().double() * step.detach().double()).sum())
                   for gd, step in zip(data_gradients, direction))
    physics_dot = sum(float((gp.detach().double() * step.detach().double()).sum())
                      for gp, step in zip(physics_gradients, direction))
    return {"delta_data_per_unit_lr": -data_dot,
            "delta_physics_per_unit_lr": -physics_dot}


def weighted_sum_direction(data_gradients, physics_gradients, weight: float):
    if len(data_gradients) != len(physics_gradients) or not torch.isfinite(torch.tensor(weight)):
        raise ValueError("invalid weighted-sum inputs")
    return [gd.detach() + float(weight) * gp.detach()
            for gd, gp in zip(data_gradients, physics_gradients)]


def normalized_sum_direction(data_gradients, physics_gradients):
    if len(data_gradients) != len(physics_gradients):
        raise ValueError("gradient sequence lengths differ")
    nd = _positive_norm(data_gradients, "data")
    np_ = _positive_norm(physics_gradients, "physics")
    return [gd.detach() / nd.to(gd) + gp.detach() / np_.to(gp)
            for gd, gp in zip(data_gradients, physics_gradients)]


def data_anchored_projected_direction(data_gradients, physics_gradients):
    """Add an equal-norm physics direction that cannot oppose data to first order.

    If the objectives conflict, project the physics gradient onto the halfspace
    orthogonal to the data gradient.  The surviving physics component is then
    scaled to the data-gradient norm.  If projection removes the full physics
    direction, the update falls back to the data gradient.
    """
    if len(data_gradients) != len(physics_gradients):
        raise ValueError("gradient sequence lengths differ")
    data_norm = _positive_norm(data_gradients, "data")
    physics_norm = _positive_norm(physics_gradients, "physics")
    dd = data_norm.square()
    dot = sum((gd.detach().double() * gp.detach().double()).sum()
              for gd, gp in zip(data_gradients, physics_gradients))
    coefficient = torch.minimum(dot / dd.clamp_min(1e-300), dot.new_zeros(()))
    projected = [gp.detach() - coefficient.to(gp) * gd.detach()
                 for gd, gp in zip(data_gradients, physics_gradients)]
    projected_norm = torch.sqrt(sum(g.double().square().sum() for g in projected))
    if not torch.isfinite(projected_norm):
        raise ValueError("projected physics gradient is non-finite")
    if float(projected_norm) <= torch.finfo(torch.float64).eps * float(physics_norm):
        return [gd.detach().clone() for gd in data_gradients], {
            "conflict": bool(float(dot) < 0.0),
            "fallback_to_data_only": True,
            "projected_physics_norm": float(projected_norm),
        }
    scale = data_norm / projected_norm
    return [gd.detach() + scale.to(gp) * gp for gd, gp in zip(data_gradients, projected)], {
        "conflict": bool(float(dot) < 0.0),
        "fallback_to_data_only": False,
        "projected_physics_norm": float(projected_norm),
    }

