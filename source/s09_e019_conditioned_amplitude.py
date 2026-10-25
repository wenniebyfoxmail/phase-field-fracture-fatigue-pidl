"""Conditioned, zero-replay amplitude readout for the S09-E019 exploration.

The module is deliberately I/O-free.  It adds capacity only to the scalar
factorised amplitude readout: the spatial-shape decoder, the frozen transition
network, objective groups, and constrained damage decoder remain outside it.
"""
from __future__ import annotations

from collections.abc import Sequence

import torch
from torch import nn


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def condition_features(
    damage_pre: torch.Tensor,
    history_pre: torch.Tensor,
    path: torch.Tensor,
    nodal_weight: torch.Tensor,
) -> torch.Tensor:
    """Build causal scalar features available at the transition origin.

    History is reduced only over its terminal nodal axis; its leading temporal
    and channel axes remain explicit.  The load path is retained in full.  No
    cycle label, target damage, post-state, or holdout statistic is admitted.
    """
    _require(damage_pre.ndim == 1, "damage_pre must be one-dimensional")
    _require(nodal_weight.shape == damage_pre.shape, "nodal weights drift")
    _require(history_pre.ndim >= 1, "history_pre must have a nodal axis")
    _require(history_pre.shape[-1] == damage_pre.numel(), "history nodal axis drift")
    _require(path.numel() > 0, "empty load path")
    _require(
        all(
            torch.isfinite(value).all().item()
            for value in (damage_pre, history_pre, path, nodal_weight)
        ),
        "nonfinite conditioning input",
    )
    total_weight = nodal_weight.sum()
    _require(torch.isfinite(total_weight).item() and total_weight > 0, "invalid nodal weights")
    normalised = nodal_weight / total_weight
    damage_mean = torch.sum(normalised * damage_pre)
    damage_square_mean = torch.sum(normalised * damage_pre.square())
    capacity_mean = torch.sum(normalised * (1.0 - damage_pre))
    history_means = torch.sum(history_pre * normalised, dim=-1).reshape(-1)
    result = torch.cat(
        (
            torch.stack((damage_mean, damage_square_mean, capacity_mean)),
            history_means,
            path.reshape(-1),
        )
    )
    _require(torch.isfinite(result).all().item(), "nonfinite conditioning feature")
    return result


def frozen_feature_statistics(rows: Sequence[torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor]:
    """Freeze normalisation from admitted transition-origin features only."""
    _require(len(rows) > 0, "no feature rows")
    first = rows[0]
    _require(first.ndim == 1 and first.numel() > 0, "invalid first feature row")
    _require(all(row.shape == first.shape for row in rows), "feature width drift")
    matrix = torch.stack(tuple(rows), dim=0)
    _require(torch.isfinite(matrix).all().item(), "nonfinite feature rows")
    mean = matrix.mean(dim=0)
    # A constant causal channel remains usable and must not divide by zero.
    scale = torch.clamp(matrix.std(dim=0, unbiased=False), min=1.0e-12)
    return mean, scale


class ConditionedAmplitudeResidual(nn.Module):
    """A bounded nonlinear residual with exact update-zero replay.

    The final layer starts at zero.  Therefore the initial residual is exactly
    zero for every admissible condition, and the existing exponential amplitude
    parameterisation exactly reproduces its frozen baseline at update zero.
    """

    def __init__(
        self,
        *,
        pooled_width: int,
        condition_mean: torch.Tensor,
        condition_scale: torch.Tensor,
        bottleneck_width: int = 16,
        residual_limit: float = 8.0,
    ) -> None:
        super().__init__()
        _require(pooled_width > 0, "invalid pooled width")
        _require(bottleneck_width > 0, "invalid bottleneck width")
        _require(residual_limit > 0, "invalid residual limit")
        _require(
            condition_mean.ndim == condition_scale.ndim == 1
            and condition_mean.shape == condition_scale.shape
            and condition_mean.numel() > 0,
            "invalid frozen condition statistics",
        )
        _require(
            torch.isfinite(condition_mean).all().item()
            and torch.isfinite(condition_scale).all().item()
            and torch.all(condition_scale > 0).item(),
            "nonfinite frozen condition statistics",
        )
        self.pooled_width = pooled_width
        self.condition_width = condition_mean.numel()
        self.residual_limit = float(residual_limit)
        self.register_buffer("condition_mean", condition_mean.detach().clone())
        self.register_buffer("condition_scale", condition_scale.detach().clone())
        self.hidden = nn.Linear(pooled_width + self.condition_width, bottleneck_width)
        self.out = nn.Linear(bottleneck_width, 1)
        nn.init.zeros_(self.out.weight)
        nn.init.zeros_(self.out.bias)

    def forward(self, pooled_hidden: torch.Tensor, condition: torch.Tensor) -> torch.Tensor:
        _require(pooled_hidden.ndim == condition.ndim == 1, "readout inputs must be vectors")
        _require(pooled_hidden.numel() == self.pooled_width, "pooled width drift")
        _require(condition.numel() == self.condition_width, "condition width drift")
        _require(
            pooled_hidden.dtype == condition.dtype == self.condition_mean.dtype,
            "readout dtype drift",
        )
        _require(
            all(torch.isfinite(value).all().item() for value in (pooled_hidden, condition)),
            "nonfinite readout input",
        )
        standardised = (condition - self.condition_mean) / self.condition_scale
        joined = torch.cat((pooled_hidden, standardised))
        raw = self.out(torch.nn.functional.gelu(self.hidden(joined))).squeeze(0)
        residual = self.residual_limit * torch.tanh(raw / self.residual_limit)
        _require(torch.isfinite(residual).item(), "nonfinite amplitude residual")
        return residual
