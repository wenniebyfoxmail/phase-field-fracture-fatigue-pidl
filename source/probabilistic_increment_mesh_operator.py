"""Data-only t+1 probabilistic increment GNO for archived FEM cycle peaks.

The operator predicts a constrained four-field mean increment and a bounded
per-cell Laplace scale. It contains no governing-equation or physics residual.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import torch
import torch.nn as nn

from fem_mechanism_operator import (
    EdgeMessageBlock,
    StateStatistics,
    apply_state_constraints,
    weighted_mean,
)
from transition_aware_mesh_operator import area_cluster_mean, transition_node_features


LOG_SCALE_BOUNDS = (-5.0, 2.0)


def _mlp(sizes: list[int]) -> nn.Sequential:
    layers: list[nn.Module] = []
    for index, (input_dim, output_dim) in enumerate(zip(sizes[:-1], sizes[1:])):
        layers.append(nn.Linear(input_dim, output_dim))
        if index < len(sizes) - 2:
            layers.append(nn.GELU())
    return nn.Sequential(*layers)


@dataclass(frozen=True)
class ProbabilisticIncrementOutput:
    mean_state: torch.Tensor
    normalized_location: torch.Tensor
    normalized_log_scale: torch.Tensor


@dataclass(frozen=True)
class ConditionalScaleLoss:
    total: torch.Tensor
    channel_nll: torch.Tensor


class ProbabilisticIncrementMeshOperator(nn.Module):
    """Local/coarse GNO with separate increment-location and scale decoders."""

    def __init__(
        self,
        *,
        context: int = 3,
        hidden_dim: int = 96,
        local_layers: int = 3,
        coarse_layers: int = 2,
        edge_dim: int = 4,
    ) -> None:
        super().__init__()
        self.context = context
        input_dim = 4 * context + 2 + 1 + 4
        self.encoder = _mlp([input_dim, hidden_dim, hidden_dim])
        self.local_blocks = nn.ModuleList(
            EdgeMessageBlock(hidden_dim, edge_dim) for _ in range(local_layers)
        )
        self.coarse_blocks = nn.ModuleList(
            EdgeMessageBlock(hidden_dim, edge_dim) for _ in range(coarse_layers)
        )
        decoder_input_dim = 3 * hidden_dim
        self.mean_decoder = _mlp(
            [decoder_input_dim, hidden_dim, hidden_dim, 4]
        )
        self.scale_decoder = _mlp(
            [decoder_input_dim, hidden_dim, hidden_dim, 4]
        )

    def latent_features(
        self,
        history: torch.Tensor,
        graph: Mapping[str, torch.Tensor],
        statistics: StateStatistics,
        trajectory_metadata: torch.Tensor,
    ) -> torch.Tensor:
        if len(history) != self.context:
            raise ValueError(f"expected context {self.context}, got {len(history)}")
        features = transition_node_features(
            history, graph, statistics, trajectory_metadata
        )
        encoded = self.encoder(features)
        local = encoded
        for block in self.local_blocks:
            local = block(local, graph["edge_index"], graph["edge_attr"])

        cluster_count = int(graph["cluster_index"].max().item()) + 1
        coarse, _ = area_cluster_mean(
            local, graph["cluster_index"], graph["areas"], cluster_count
        )
        for block in self.coarse_blocks:
            coarse = block(
                coarse, graph["coarse_edge_index"], graph["coarse_edge_attr"]
            )
        return torch.cat(
            [encoded, local, coarse[graph["cluster_index"]]], dim=-1
        )

    def forward(
        self,
        history: torch.Tensor,
        graph: Mapping[str, torch.Tensor],
        statistics: StateStatistics,
        trajectory_metadata: torch.Tensor,
    ) -> ProbabilisticIncrementOutput:
        latent = self.latent_features(history, graph, statistics, trajectory_metadata)
        raw_location = self.mean_decoder(latent)
        mean_state = apply_state_constraints(history[-1], raw_location, statistics)
        normalized_location = (
            mean_state - history[-1] - statistics.residual_mean
        ) / statistics.residual_std.clamp_min(1.0e-6)

        raw_scale = self.scale_decoder(latent)
        lower, upper = LOG_SCALE_BOUNDS
        normalized_log_scale = lower + (upper - lower) * torch.sigmoid(raw_scale)
        return ProbabilisticIncrementOutput(
            mean_state=mean_state,
            normalized_location=normalized_location,
            normalized_log_scale=normalized_log_scale,
        )

    def set_mean_training(self) -> None:
        """Train the backbone and mean decoder; freeze the scale decoder."""
        for parameter in self.parameters():
            parameter.requires_grad_(True)
        for parameter in self.scale_decoder.parameters():
            parameter.requires_grad_(False)

    def set_scale_training(self) -> None:
        """Freeze the point predictor and train only the scale decoder."""
        for parameter in self.parameters():
            parameter.requires_grad_(False)
        for parameter in self.scale_decoder.parameters():
            parameter.requires_grad_(True)


def normalized_increment_target(
    current_state: torch.Tensor,
    target_state: torch.Tensor,
    statistics: StateStatistics,
) -> torch.Tensor:
    if current_state.shape != target_state.shape or current_state.shape[-1] != 4:
        raise ValueError("current and target states must have matching [elements,4] shape")
    return (
        target_state - current_state - statistics.residual_mean
    ) / statistics.residual_std.clamp_min(1.0e-6)


def conditional_laplace_scale_loss(
    output: ProbabilisticIncrementOutput,
    current_state: torch.Tensor,
    target_state: torch.Tensor,
    area_weights: torch.Tensor,
    statistics: StateStatistics,
) -> ConditionalScaleLoss:
    """Fit conditional scale around a detached, frozen mean increment."""
    target = normalized_increment_target(current_state, target_state, statistics)
    absolute_error = (target - output.normalized_location).detach().abs()
    log_scale = output.normalized_log_scale
    element_nll = absolute_error * torch.exp(-log_scale) + log_scale
    area = area_weights.reshape(-1)
    channel_nll = torch.stack(
        [weighted_mean(element_nll[:, index], area) for index in range(4)]
    )
    return ConditionalScaleLoss(total=channel_nll.sum(), channel_nll=channel_nll)


def normalized_laplace_interval(
    output: ProbabilisticIncrementOutput,
    central_coverage: float = 0.90,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return an uncalibrated central Laplace interval in normalized increments."""
    if not 0.0 < central_coverage < 1.0:
        raise ValueError("central_coverage must lie strictly between zero and one")
    multiplier = -torch.log(
        output.normalized_location.new_tensor(1.0 - central_coverage)
    )
    half_width = multiplier * torch.exp(output.normalized_log_scale)
    return output.normalized_location - half_width, output.normalized_location + half_width
