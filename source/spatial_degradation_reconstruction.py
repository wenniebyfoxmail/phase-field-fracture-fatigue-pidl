"""Leakage-safe spatial degradation reconstruction primitives.

The models reconstruct a target-cycle damage field from an older irreversible
damage prior and declared observations.  They predict a bounded increment in

    z = -log10((1 - d)**2),

so the reconstructed damage cannot heal the supplied prior.  The pointwise and
one-ring variants receive identical node features; only the graph model can
exchange information across a shared FEM edge.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from fem_mechanism_operator import EdgeMessageBlock


Z_MAX = 12.0


def _mlp(sizes: list[int]) -> nn.Sequential:
    layers: list[nn.Module] = []
    for index, (input_dim, output_dim) in enumerate(zip(sizes[:-1], sizes[1:])):
        layers.append(nn.Linear(input_dim, output_dim))
        if index < len(sizes) - 2:
            layers.append(nn.GELU())
    return nn.Sequential(*layers)


def _initialize_increment_head(layer: nn.Linear) -> None:
    """Start close to persistence instead of degrading the whole domain."""
    nn.init.normal_(layer.weight, mean=0.0, std=1.0e-3)
    nn.init.constant_(layer.bias, -8.0)


def damage_to_z(
    damage: np.ndarray | torch.Tensor,
    *,
    z_max: float = Z_MAX,
) -> np.ndarray | torch.Tensor:
    """Convert bounded damage to bounded eta0 degradation depth."""
    if z_max <= 0.0:
        raise ValueError("z_max must be positive")
    if isinstance(damage, torch.Tensor):
        bounded = damage.clamp(0.0, 1.0)
        floor = 10.0 ** (-0.5 * z_max)
        return (-2.0 * torch.log10((1.0 - bounded).clamp_min(floor))).clamp(0.0, z_max)
    bounded = np.clip(np.asarray(damage, dtype=np.float64), 0.0, 1.0)
    floor = 10.0 ** (-0.5 * z_max)
    return np.clip(-2.0 * np.log10(np.maximum(1.0 - bounded, floor)), 0.0, z_max)


def z_to_damage(
    z: np.ndarray | torch.Tensor,
    *,
    z_max: float = Z_MAX,
) -> np.ndarray | torch.Tensor:
    """Convert degradation depth back to damage."""
    if isinstance(z, torch.Tensor):
        bounded = z.clamp(0.0, z_max)
        return 1.0 - torch.pow(bounded.new_tensor(10.0), -0.5 * bounded)
    bounded = np.clip(np.asarray(z, dtype=np.float64), 0.0, z_max)
    return 1.0 - np.power(10.0, -0.5 * bounded)


def target_increment(prior_damage: np.ndarray, target_damage: np.ndarray) -> np.ndarray:
    """Return degradation increment normalized by remaining bounded capacity."""
    prior_z = np.asarray(damage_to_z(prior_damage), dtype=np.float64)
    target_z = np.asarray(damage_to_z(target_damage), dtype=np.float64)
    if prior_z.shape != target_z.shape:
        raise ValueError("prior and target damage must have matching shapes")
    capacity = np.maximum(Z_MAX - prior_z, np.finfo(np.float64).eps)
    return np.clip((target_z - prior_z) / capacity, 0.0, 1.0)


def reconstruct_damage(
    prior_damage: torch.Tensor,
    raw_increment: torch.Tensor,
    *,
    core_mask: torch.Tensor | None = None,
    z_max: float = Z_MAX,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Decode a non-negative, bounded increment and enforce irreversibility."""
    prior_z = damage_to_z(prior_damage, z_max=z_max)
    fraction = torch.sigmoid(raw_increment.reshape(-1))
    predicted_z = prior_z + (z_max - prior_z) * fraction
    if core_mask is not None:
        core_mask = core_mask.reshape(-1).bool()
        core_z = float(-2.0 * np.log10(1.0 - 0.95))
        predicted_z = torch.where(
            core_mask,
            torch.maximum(predicted_z, predicted_z.new_tensor(core_z)),
            predicted_z,
        )
    damage = z_to_damage(predicted_z, z_max=z_max)
    return damage, predicted_z


class PointwiseDegradationReconstructor(nn.Module):
    """Pointwise control without mesh-neighbour communication."""

    def __init__(self, input_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.net = _mlp([input_dim, hidden_dim, hidden_dim, hidden_dim, 1])
        _initialize_increment_head(self.net[-1])

    def forward(
        self,
        node_features: torch.Tensor,
        edge_index: torch.Tensor | None = None,
        edge_attr: torch.Tensor | None = None,
    ) -> torch.Tensor:
        del edge_index, edge_attr
        return self.net(node_features).reshape(-1)


class OneRingDegradationReconstructor(nn.Module):
    """One shared-edge message pass with a direct high-frequency path."""

    def __init__(self, input_dim: int, hidden_dim: int, edge_dim: int = 4) -> None:
        super().__init__()
        self.encoder = _mlp([input_dim, hidden_dim, hidden_dim])
        self.message = EdgeMessageBlock(hidden_dim, edge_dim=edge_dim)
        self.decoder = _mlp([2 * hidden_dim, hidden_dim, hidden_dim, 1])
        _initialize_increment_head(self.decoder[-1])

    def forward(
        self,
        node_features: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
    ) -> torch.Tensor:
        encoded = self.encoder(node_features)
        local = self.message(encoded, edge_index, edge_attr)
        return self.decoder(torch.cat((encoded, local), dim=-1)).reshape(-1)


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


def matched_pointwise_width(
    input_dim: int,
    graph_hidden_dim: int,
    *,
    minimum: int = 8,
    maximum: int = 512,
) -> tuple[int, int, int]:
    """Find the closest pointwise width to the requested graph capacity."""
    graph_count = parameter_count(
        OneRingDegradationReconstructor(input_dim, graph_hidden_dim)
    )
    candidates = []
    for width in range(minimum, maximum + 1):
        count = parameter_count(PointwiseDegradationReconstructor(input_dim, width))
        candidates.append((abs(count - graph_count), width, count))
    _, width, count = min(candidates)
    return width, count, graph_count


@dataclass(frozen=True)
class ReconstructionLoss:
    total: torch.Tensor
    degradation: torch.Tensor
    damage: torch.Tensor
    core: torch.Tensor
    gradient: torch.Tensor


def reconstruction_loss(
    predicted_damage: torch.Tensor,
    predicted_z: torch.Tensor,
    target_damage: torch.Tensor,
    target_z: torch.Tensor,
    prior_z: torch.Tensor,
    core_mask: torch.Tensor,
    areas: torch.Tensor,
    edge_index: torch.Tensor,
    *,
    process_weight: float = 20.0,
    gradient_weight: float = 0.05,
) -> ReconstructionLoss:
    """Area-weighted field loss with process-zone and roughness controls."""
    noncore = ~core_mask.reshape(-1).bool()
    weights = areas.reshape(-1) * noncore
    weights = weights / weights.sum().clamp_min(torch.finfo(weights.dtype).eps)
    target_increment_z = (target_z - prior_z).clamp_min(0.0)
    emphasis = (
        1.0
        + process_weight
        * (target_increment_z / target_increment_z.max().clamp_min(1.0e-6)).sqrt()
    )
    emphasis = emphasis / torch.sum(weights * emphasis).clamp_min(1.0e-12)
    weighted = weights * emphasis

    degradation = torch.sum(
        weighted * F.smooth_l1_loss(predicted_z, target_z, reduction="none", beta=0.1)
    )
    damage = torch.sum(weighted * (predicted_damage - target_damage).square())

    core_values = predicted_damage[core_mask]
    core = (
        F.relu(0.95 - core_values).square().mean()
        if core_values.numel()
        else predicted_damage.new_tensor(0.0)
    )
    src, dst = edge_index
    predicted_jump = predicted_z[dst] - predicted_z[src]
    target_jump = target_z[dst] - target_z[src]
    gradient = F.smooth_l1_loss(predicted_jump, target_jump, beta=0.1)
    total = degradation + damage + gradient_weight * gradient
    return ReconstructionLoss(total, degradation, damage, core, gradient)
