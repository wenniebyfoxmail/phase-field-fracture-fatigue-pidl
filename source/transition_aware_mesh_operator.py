"""Data-only transition-aware graph neural operator for FEM cycle peaks.

The module contains no equilibrium, phase-field, KKT, or constitutive residual.
It predicts the next archived FEM state and an auxiliary regime-transition
score from recent FEM states on the native element graph.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import torch
import torch.nn as nn

from fem_mechanism_operator import EdgeMessageBlock, StateStatistics, apply_state_constraints


def _mlp(sizes: list[int]) -> nn.Sequential:
    layers: list[nn.Module] = []
    for index, (in_dim, out_dim) in enumerate(zip(sizes[:-1], sizes[1:])):
        layers.append(nn.Linear(in_dim, out_dim))
        if index < len(sizes) - 2:
            layers.append(nn.GELU())
    return nn.Sequential(*layers)


def area_cluster_mean(
    values: torch.Tensor,
    cluster_index: torch.Tensor,
    areas: torch.Tensor,
    cluster_count: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return area-weighted cluster features and cluster areas."""
    area = areas.reshape(-1, 1).to(values.dtype)
    numerator = values.new_zeros((cluster_count, values.shape[-1]))
    numerator.index_add_(0, cluster_index, values * area)
    cluster_area = values.new_zeros((cluster_count, 1))
    cluster_area.index_add_(0, cluster_index, area)
    pooled = numerator / cluster_area.clamp_min(torch.finfo(values.dtype).eps)
    return pooled, cluster_area


def transition_node_features(
    history: torch.Tensor,
    graph: Mapping[str, torch.Tensor],
    statistics: StateStatistics,
    trajectory_metadata: torch.Tensor,
) -> torch.Tensor:
    """Build context-state, geometry, and known trajectory features.

    No cycle number, event distance, first-hit cycle, confirmed cycle, or future
    field is accepted by this function.
    """
    if history.ndim != 3 or history.shape[-1] != 4:
        raise ValueError("history must have shape [context, elements, 4]")
    if trajectory_metadata.shape != (4,):
        raise ValueError("trajectory_metadata must be [is_hard,is_soft,is_5step,is_8step]")
    normalized = (history - statistics.state_mean) / statistics.state_std
    flattened = normalized.permute(1, 0, 2).reshape(len(history[0]), -1)
    metadata = trajectory_metadata.reshape(1, 4).expand(len(flattened), 4)
    return torch.cat(
        [flattened, graph["coordinates"], graph["log_area"], metadata], dim=-1
    )


class TransitionAwareMeshOperator(nn.Module):
    """Local/coarse GNO with an auxiliary regime head feeding the field decoder."""

    def __init__(
        self,
        *,
        context: int = 3,
        hidden_dim: int = 80,
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
        self.transition_head = _mlp([hidden_dim, hidden_dim, 1])
        self.decoder = _mlp([3 * hidden_dim + 1, hidden_dim, hidden_dim, 4])

    def forward(
        self,
        history: torch.Tensor,
        graph: Mapping[str, torch.Tensor],
        statistics: StateStatistics,
        trajectory_metadata: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if len(history) != self.context:
            raise ValueError(f"expected context {self.context}, got {len(history)}")
        features = transition_node_features(history, graph, statistics, trajectory_metadata)
        encoded = self.encoder(features)
        local = encoded
        for block in self.local_blocks:
            local = block(local, graph["edge_index"], graph["edge_attr"])

        cluster_count = int(graph["cluster_index"].max().item()) + 1
        coarse, cluster_area = area_cluster_mean(
            local, graph["cluster_index"], graph["areas"], cluster_count
        )
        for block in self.coarse_blocks:
            coarse = block(coarse, graph["coarse_edge_index"], graph["coarse_edge_attr"])
        global_feature = (coarse * cluster_area).sum(0) / cluster_area.sum().clamp_min(
            torch.finfo(coarse.dtype).eps
        )
        transition_logit = self.transition_head(global_feature).reshape(())
        transition_feature = torch.sigmoid(transition_logit).reshape(1, 1).expand(len(local), 1)
        raw_update = self.decoder(
            torch.cat(
                [encoded, local, coarse[graph["cluster_index"]], transition_feature], dim=-1
            )
        )
        prediction = apply_state_constraints(history[-1], raw_update, statistics)
        return prediction, transition_logit


@dataclass(frozen=True)
class SupervisedTransitionLoss:
    total: torch.Tensor
    field: torch.Tensor
    transition: torch.Tensor


def supervised_transition_loss(
    field_loss: torch.Tensor,
    transition_logit: torch.Tensor,
    transition_target: torch.Tensor,
    *,
    transition_weight: float = 0.25,
) -> SupervisedTransitionLoss:
    """Combine FEM field supervision and binary transition supervision only."""
    if transition_target.shape != ():
        raise ValueError("transition_target must be a scalar tensor")
    transition = nn.functional.binary_cross_entropy_with_logits(
        transition_logit, transition_target.to(transition_logit.dtype)
    )
    total = field_loss + transition_weight * transition
    return SupervisedTransitionLoss(total=total, field=field_loss, transition=transition)
