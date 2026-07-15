"""FEM-anchored temporal mesh operators for fracture mechanism states.

The operator predicts the next cycle-peak element state

    [damage, fatigue history, fatigue degradation, log10(raw driver)]

on the native FEM quad graph.  It deliberately predicts the archived raw
driver.  A comparable eta=0 active-like field is derived downstream as
``(1-damage)**2 * raw_driver`` and must remain labelled as derived.
"""
from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F


STATE_NAMES = ("damage", "alpha_bar", "fatigue_degradation", "log10_psi_raw")


def _mlp(sizes: list[int]) -> nn.Sequential:
    layers: list[nn.Module] = []
    for index, (in_dim, out_dim) in enumerate(zip(sizes[:-1], sizes[1:])):
        layers.append(nn.Linear(in_dim, out_dim))
        if index < len(sizes) - 2:
            layers.append(nn.GELU())
    return nn.Sequential(*layers)


def scatter_mean(
    values: torch.Tensor,
    index: torch.Tensor,
    count: int,
) -> torch.Tensor:
    """Dependency-free mean aggregation for node or cluster features."""
    result = values.new_zeros((count, values.shape[-1]))
    result.index_add_(0, index, values)
    degree = values.new_zeros((count, 1))
    degree.index_add_(0, index, values.new_ones((len(index), 1)))
    return result / degree.clamp_min(1.0)


class EdgeMessageBlock(nn.Module):
    """Residual edge-aware message passing with degree normalization."""

    def __init__(self, hidden_dim: int, edge_dim: int = 4) -> None:
        super().__init__()
        self.message = _mlp([2 * hidden_dim + edge_dim, hidden_dim, hidden_dim])
        self.update = _mlp([2 * hidden_dim, hidden_dim, hidden_dim])
        self.norm = nn.LayerNorm(hidden_dim)

    def forward(
        self,
        nodes: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
    ) -> torch.Tensor:
        src, dst = edge_index
        message = self.message(torch.cat([nodes[src], nodes[dst], edge_attr], dim=-1))
        aggregated = scatter_mean(message, dst, len(nodes))
        update = self.update(torch.cat([nodes, aggregated], dim=-1))
        return self.norm(nodes + update)


class PointwiseResidualOperator(nn.Module):
    """No-neighbour control with the same input/output contract."""

    def __init__(self, input_dim: int, hidden_dim: int = 96, output_dim: int = 4) -> None:
        super().__init__()
        self.net = _mlp([input_dim, hidden_dim, hidden_dim, hidden_dim, output_dim])

    def forward(
        self,
        node_features: torch.Tensor,
        edge_index: torch.Tensor | None = None,
        edge_attr: torch.Tensor | None = None,
        cluster_index: torch.Tensor | None = None,
        coarse_edge_index: torch.Tensor | None = None,
        coarse_edge_attr: torch.Tensor | None = None,
    ) -> torch.Tensor:
        del edge_index, edge_attr, cluster_index, coarse_edge_index, coarse_edge_attr
        return self.net(node_features)


class MultiScaleMeshResidualOperator(nn.Module):
    """Local FEM graph plus coarse-bin graph with a high-frequency skip.

    Local message passing resolves the process zone.  Element embeddings are
    pooled into fixed geometric bins, propagated on a coarse graph, and then
    broadcast back to the elements.  The decoder also receives the original
    encoded features, preserving a direct high-frequency path.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 96,
        output_dim: int = 4,
        local_layers: int = 3,
        coarse_layers: int = 2,
        edge_dim: int = 4,
    ) -> None:
        super().__init__()
        self.encoder = _mlp([input_dim, hidden_dim, hidden_dim])
        self.local_blocks = nn.ModuleList(
            EdgeMessageBlock(hidden_dim, edge_dim) for _ in range(local_layers)
        )
        self.coarse_blocks = nn.ModuleList(
            EdgeMessageBlock(hidden_dim, edge_dim) for _ in range(coarse_layers)
        )
        self.decoder = _mlp([3 * hidden_dim, hidden_dim, hidden_dim, output_dim])

    def forward(
        self,
        node_features: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        cluster_index: torch.Tensor,
        coarse_edge_index: torch.Tensor,
        coarse_edge_attr: torch.Tensor,
    ) -> torch.Tensor:
        encoded = self.encoder(node_features)
        local = encoded
        for block in self.local_blocks:
            local = block(local, edge_index, edge_attr)

        cluster_count = int(cluster_index.max().item()) + 1
        coarse = scatter_mean(local, cluster_index, cluster_count)
        for block in self.coarse_blocks:
            coarse = block(coarse, coarse_edge_index, coarse_edge_attr)
        broadcast = coarse[cluster_index]
        return self.decoder(torch.cat([encoded, local, broadcast], dim=-1))


@dataclass(frozen=True)
class StateStatistics:
    """Training-split normalization and residual scaling."""

    state_mean: torch.Tensor
    state_std: torch.Tensor
    residual_mean: torch.Tensor
    residual_std: torch.Tensor

    def to(self, device: torch.device) -> "StateStatistics":
        return StateStatistics(*(
            tensor.to(device) for tensor in (
                self.state_mean,
                self.state_std,
                self.residual_mean,
                self.residual_std,
            )
        ))


def normalized_node_features(
    current_state: torch.Tensor,
    coordinates: torch.Tensor,
    log_area: torch.Tensor,
    cycle: int | torch.Tensor,
    statistics: StateStatistics,
    max_cycle: int = 89,
) -> torch.Tensor:
    """Build state, geometry, and periodic cycle features for one graph."""
    normalized_state = (current_state - statistics.state_mean) / statistics.state_std
    if not isinstance(cycle, torch.Tensor):
        cycle = current_state.new_tensor(float(cycle))
    phase = cycle / float(max_cycle)
    phase = phase.reshape(1, 1).expand(len(current_state), 1)
    cycle_features = torch.cat(
        [phase, torch.sin(2.0 * torch.pi * phase), torch.cos(2.0 * torch.pi * phase)],
        dim=-1,
    )
    return torch.cat([normalized_state, coordinates, log_area, cycle_features], dim=-1)


def apply_state_constraints(
    current_state: torch.Tensor,
    normalized_residual: torch.Tensor,
    statistics: StateStatistics,
    log_psi_bounds: tuple[float, float] = (-12.0, 6.0),
) -> torch.Tensor:
    """Decode a residual while preserving irreversible FEM state channels."""
    residual = (
        normalized_residual * statistics.residual_std
        + statistics.residual_mean
    )
    proposal = current_state + residual
    damage = torch.maximum(current_state[:, 0], proposal[:, 0]).clamp(0.0, 1.0)
    history = torch.maximum(current_state[:, 1], proposal[:, 1]).clamp_min(0.0)
    fatigue = torch.minimum(current_state[:, 2], proposal[:, 2]).clamp(0.0, 1.0)
    log_psi = proposal[:, 3].clamp(*log_psi_bounds)
    return torch.stack([damage, history, fatigue, log_psi], dim=-1)


def derived_active_log10(state: torch.Tensor, floor: float = 1.0e-12) -> torch.Tensor:
    """Return log10 of eta=0 ``(1-d)^2 psi_raw`` derived support."""
    damage = state[:, 0].clamp(0.0, 1.0)
    log_raw = state[:, 3]
    log_g = 2.0 * torch.log10((1.0 - damage).clamp_min(floor))
    return (log_raw + log_g).clamp_min(torch.log10(state.new_tensor(floor)))


def soft_support(
    log_field: torch.Tensor,
    threshold: torch.Tensor,
    temperature: float = 0.15,
) -> torch.Tensor:
    """Differentiable support mask used only as a training loss."""
    return torch.sigmoid((log_field - threshold) / temperature)


def weighted_mean(values: torch.Tensor, weights: torch.Tensor) -> torch.Tensor:
    weights = weights / weights.sum().clamp_min(torch.finfo(weights.dtype).eps)
    return torch.sum(values * weights)


def mechanism_loss(
    prediction: torch.Tensor,
    target: torch.Tensor,
    area_weights: torch.Tensor,
    edge_index: torch.Tensor,
    *,
    active_weight: float = 1.0,
    support_weight: float = 0.25,
    gradient_weight: float = 0.1,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """FEM-centred state, derived-support, and edge-gradient objective."""
    area = area_weights.reshape(-1)
    channel_error = (prediction - target).square()
    state_loss = sum(weighted_mean(channel_error[:, i], area) for i in range(4))

    active_pred = derived_active_log10(prediction)
    active_target = derived_active_log10(target)
    active_loss = weighted_mean((active_pred - active_target).square(), area)

    order = torch.argsort(active_target)
    cumulative = torch.cumsum(area[order], dim=0)
    cutoff = 0.99 * area.sum()
    threshold_index = torch.searchsorted(cumulative, cutoff).clamp_max(len(order) - 1)
    threshold = active_target[order[threshold_index]].detach()
    target_support = (active_target >= threshold).to(prediction.dtype)
    predicted_support = soft_support(active_pred, threshold)
    support_weights = area / area.mean().clamp_min(torch.finfo(area.dtype).eps)
    support_loss = F.binary_cross_entropy(
        predicted_support, target_support, weight=support_weights
    )

    src, dst = edge_index
    pred_jump = prediction[dst, :3] - prediction[src, :3]
    target_jump = target[dst, :3] - target[src, :3]
    gradient_loss = (pred_jump - target_jump).square().mean()

    total = (
        state_loss
        + active_weight * active_loss
        + support_weight * support_loss
        + gradient_weight * gradient_loss
    )
    return total, {
        "state": state_loss.detach(),
        "active": active_loss.detach(),
        "support": support_loss.detach(),
        "gradient": gradient_loss.detach(),
        "total": total.detach(),
    }
