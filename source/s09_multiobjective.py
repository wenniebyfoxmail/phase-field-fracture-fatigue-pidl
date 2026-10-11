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


def gradient_statistics(named_parameters, data_gradients, physics_gradients):
    """Return global and blockwise norm ratios/cosines without changing grads."""
    accum = defaultdict(lambda: {"data_sq": 0.0, "physics_sq": 0.0, "dot": 0.0})
    for (name, _), gd, gp in zip(named_parameters, data_gradients, physics_gradients):
        if gd is None or gp is None:
            raise ValueError(f"missing gradient for {name}")
        values = (gd.detach().double(), gp.detach().double())
        for group in ("global", parameter_group(name)):
            accum[group]["data_sq"] += float(values[0].square().sum())
            accum[group]["physics_sq"] += float(values[1].square().sum())
            accum[group]["dot"] += float((values[0] * values[1]).sum())
    result = {}
    for group, item in accum.items():
        nd = item["data_sq"] ** 0.5
        np_ = item["physics_sq"] ** 0.5
        denom = nd * np_
        result[group] = {
            "data_norm": nd,
            "physics_norm": np_,
            "physics_to_data_norm": np_ / max(nd, 1e-300),
            "dot": item["dot"],
            "cosine": item["dot"] / max(denom, 1e-300),
        }
    return result


def linearized_changes(data_gradients, physics_gradients, direction):
    """First-order loss changes for a unit learning-rate step ``-direction``."""
    data_dot = sum(float((gd.detach().double() * step.detach().double()).sum())
                   for gd, step in zip(data_gradients, direction))
    physics_dot = sum(float((gp.detach().double() * step.detach().double()).sum())
                      for gp, step in zip(physics_gradients, direction))
    return {"delta_data_per_unit_lr": -data_dot,
            "delta_physics_per_unit_lr": -physics_dot}


def weighted_sum_direction(data_gradients, physics_gradients, weight: float):
    return [gd.detach() + float(weight) * gp.detach()
            for gd, gp in zip(data_gradients, physics_gradients)]


def normalized_sum_direction(data_gradients, physics_gradients):
    nd = torch.sqrt(sum(gd.detach().double().square().sum() for gd in data_gradients))
    np_ = torch.sqrt(sum(gp.detach().double().square().sum() for gp in physics_gradients))
    return [gd.detach() / nd.to(gd) + gp.detach() / np_.to(gp)
            for gd, gp in zip(data_gradients, physics_gradients)]


def data_anchored_projected_direction(data_gradients, physics_gradients):
    """Add an equal-norm physics direction that cannot oppose data to first order.

    If the objectives conflict, project the physics gradient onto the halfspace
    orthogonal to the data gradient.  The surviving physics component is then
    scaled to the data-gradient norm.  If projection removes the full physics
    direction, the update falls back to the data gradient.
    """
    dd = sum(g.detach().double().square().sum() for g in data_gradients)
    pp = sum(g.detach().double().square().sum() for g in physics_gradients)
    dot = sum((gd.detach().double() * gp.detach().double()).sum()
              for gd, gp in zip(data_gradients, physics_gradients))
    coefficient = torch.minimum(dot / dd.clamp_min(1e-300), dot.new_zeros(()))
    projected = [gp.detach() - coefficient.to(gp) * gd.detach()
                 for gd, gp in zip(data_gradients, physics_gradients)]
    projected_norm = torch.sqrt(sum(g.double().square().sum() for g in projected))
    if float(projected_norm) <= 1e-30:
        return [gd.detach().clone() for gd in data_gradients]
    data_norm = torch.sqrt(dd)
    scale = data_norm / projected_norm
    return [gd.detach() + scale.to(gp) * gp for gd, gp in zip(data_gradients, projected)]

