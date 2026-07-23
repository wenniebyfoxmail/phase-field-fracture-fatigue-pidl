"""Factorised spatial-temporal mesh operator for FEM fracture trajectories.

The design deliberately avoids global space-time attention over all FEM
elements.  Fine-scale message passing is applied only to the latest mesh
state.  Every history state is area-pooled onto the existing coarse mesh graph,
encoded there, and processed causally and independently for each coarse token.

All temporal families share the same spatial encoder, mesh decoder, state
channels, and irreversible output parameterisation.  The only interchangeable
component is the causal temporal block.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import torch
import torch.nn as nn
import torch.nn.functional as F

from fem_mechanism_operator import (
    EdgeMessageBlock,
    StateStatistics,
    derived_active_log10,
    mechanism_loss,
    soft_support,
)


TEMPORAL_FAMILIES = (
    "markov",
    "gru",
    "lstm",
    "tcn",
    "transformer",
    "diagonal_ssm",
)


def _mlp(sizes: list[int]) -> nn.Sequential:
    layers: list[nn.Module] = []
    for index, (in_dim, out_dim) in enumerate(zip(sizes[:-1], sizes[1:])):
        layers.append(nn.Linear(in_dim, out_dim))
        if index < len(sizes) - 2:
            layers.append(nn.GELU())
    return nn.Sequential(*layers)


def count_parameters(module: nn.Module, *, trainable_only: bool = False) -> int:
    """Return a stable parameter count for manifests and capacity matching."""
    return sum(
        parameter.numel()
        for parameter in module.parameters()
        if not trainable_only or parameter.requires_grad
    )


def parameter_breakdown(module: nn.Module) -> dict[str, int]:
    """Count direct child modules without double counting the parent."""
    result = {name: count_parameters(child) for name, child in module.named_children()}
    result["total"] = count_parameters(module)
    result["trainable"] = count_parameters(module, trainable_only=True)
    return result


def weighted_cluster_mean(
    values: torch.Tensor,
    cluster_index: torch.Tensor,
    area_weights: torch.Tensor,
    cluster_count: int,
) -> torch.Tensor:
    """Area-weighted element-to-cluster pooling for one mesh state."""
    if values.ndim != 2:
        raise ValueError("weighted_cluster_mean expects [elements, channels]")
    area = area_weights.reshape(-1, 1).to(values.dtype)
    numerator = values.new_zeros((cluster_count, values.shape[-1]))
    numerator.index_add_(0, cluster_index, values * area)
    denominator = values.new_zeros((cluster_count, 1))
    denominator.index_add_(0, cluster_index, area)
    return numerator / denominator.clamp_min(torch.finfo(values.dtype).eps)


def normalized_mesh_features(
    state: torch.Tensor,
    coordinates: torch.Tensor,
    log_area: torch.Tensor,
    statistics: StateStatistics,
    metadata: torch.Tensor | None = None,
    node_metadata: torch.Tensor | None = None,
) -> torch.Tensor:
    """Build leakage-safe state and geometry features for one cycle.

    There is intentionally no cycle-number, cycle-to-failure, or ``cycle/89``
    feature.  Optional metadata must be known at forecast time.
    """
    normalized_state = (state - statistics.state_mean) / statistics.state_std
    features = [normalized_state, coordinates, log_area]
    if metadata is not None:
        if metadata.ndim != 1:
            raise ValueError("metadata for one cycle must be one-dimensional")
        features.append(metadata.reshape(1, -1).expand(len(state), -1))
    if node_metadata is not None:
        if node_metadata.ndim != 2 or node_metadata.shape[0] != len(state):
            raise ValueError(
                "node_metadata for one cycle must have shape [elements, channels]"
            )
        features.append(node_metadata)
    return torch.cat(features, dim=-1)


class FactorizedMeshEncoder(nn.Module):
    """Fine latest-state graph plus coarse graph tokens for the full history."""

    def __init__(
        self,
        input_dim: int,
        local_dim: int,
        token_dim: int,
        *,
        local_layers: int = 2,
        coarse_layers: int = 1,
        edge_dim: int = 4,
        graph_enabled: bool = True,
    ) -> None:
        super().__init__()
        self.graph_enabled = graph_enabled
        self.local_projection = _mlp([input_dim, local_dim, local_dim])
        self.token_projection = _mlp([input_dim, token_dim, token_dim])
        self.local_blocks = nn.ModuleList(
            EdgeMessageBlock(local_dim, edge_dim)
            for _ in range(local_layers if graph_enabled else 0)
        )
        self.coarse_blocks = nn.ModuleList(
            EdgeMessageBlock(token_dim, edge_dim)
            for _ in range(coarse_layers if graph_enabled else 0)
        )

    def _coarse_token(
        self,
        node_features: torch.Tensor,
        graph: Mapping[str, torch.Tensor],
    ) -> torch.Tensor:
        cluster_count = int(graph["cluster_index"].max().item()) + 1
        pooled = weighted_cluster_mean(
            node_features,
            graph["cluster_index"],
            graph["areas"],
            cluster_count,
        )
        token = self.token_projection(pooled)
        for block in self.coarse_blocks:
            token = block(
                token,
                graph["coarse_edge_index"],
                graph["coarse_edge_attr"],
            )
        return token

    def forward(
        self,
        history_states: torch.Tensor,
        graph: Mapping[str, torch.Tensor],
        statistics: StateStatistics,
        metadata_history: torch.Tensor | None = None,
        node_metadata_history: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Return latest node features/local state and coarse history tokens.

        ``history_states`` has shape ``[time, elements, 4]``.  Only coarse
        tokens are retained across time, keeping memory proportional to the
        roughly one-thousand coarse regions rather than all 86k elements.
        """
        if history_states.ndim != 3 or history_states.shape[-1] != 4:
            raise ValueError("history_states must have shape [time, elements, 4]")
        if (
            metadata_history is not None
            and len(metadata_history) != len(history_states)
        ):
            raise ValueError("metadata_history length must equal history length")
        if (
            node_metadata_history is not None
            and node_metadata_history.shape[:2] != history_states.shape[:2]
        ):
            raise ValueError(
                "node_metadata_history must have shape [time, elements, channels]"
            )

        tokens: list[torch.Tensor] = []
        latest_features: torch.Tensor | None = None
        for index, state in enumerate(history_states):
            metadata = None if metadata_history is None else metadata_history[index]
            node_metadata = (
                None
                if node_metadata_history is None
                else node_metadata_history[index]
            )
            features = normalized_mesh_features(
                state,
                graph["coordinates"],
                graph["log_area"],
                statistics,
                metadata,
                node_metadata,
            )
            tokens.append(self._coarse_token(features, graph))
            latest_features = features

        assert latest_features is not None
        local = self.local_projection(latest_features)
        for block in self.local_blocks:
            local = block(local, graph["edge_index"], graph["edge_attr"])
        # Temporal blocks use [coarse_token, time, channels].
        token_history = torch.stack(tokens, dim=1)
        return latest_features, local, token_history


class MarkovTemporal(nn.Module):
    def __init__(self, token_dim: int, width: int) -> None:
        super().__init__()
        self.net = _mlp([token_dim, width, width, token_dim])

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        return self.net(tokens[:, -1])


class RecurrentTemporal(nn.Module):
    def __init__(self, token_dim: int, width: int, *, cell: str) -> None:
        super().__init__()
        if cell == "gru":
            self.recurrent: nn.Module = nn.GRU(token_dim, width, batch_first=True)
        elif cell == "lstm":
            self.recurrent = nn.LSTM(token_dim, width, batch_first=True)
        else:
            raise ValueError(f"unsupported recurrent cell {cell}")
        self.output = nn.Linear(width, token_dim)

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        sequence, _ = self.recurrent(tokens)
        return self.output(sequence[:, -1])


class CausalConvBlock(nn.Module):
    def __init__(self, width: int, kernel_size: int = 3) -> None:
        super().__init__()
        self.kernel_size = kernel_size
        self.depthwise = nn.Conv1d(
            width, width, kernel_size, groups=width, bias=True
        )
        self.pointwise = nn.Conv1d(width, width, 1)
        self.norm = nn.LayerNorm(width)

    def forward(self, sequence: torch.Tensor) -> torch.Tensor:
        residual = sequence
        channels_first = sequence.transpose(1, 2)
        padded = F.pad(channels_first, (self.kernel_size - 1, 0))
        update = self.pointwise(F.gelu(self.depthwise(padded))).transpose(1, 2)
        return self.norm(residual + update)


class TCNTemporal(nn.Module):
    def __init__(self, token_dim: int, width: int, layers: int = 2) -> None:
        super().__init__()
        self.input = nn.Linear(token_dim, width)
        self.blocks = nn.ModuleList(CausalConvBlock(width) for _ in range(layers))
        self.output = nn.Linear(width, token_dim)

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        sequence = self.input(tokens)
        for block in self.blocks:
            sequence = block(sequence)
        return self.output(sequence[:, -1])


class TransformerTemporal(nn.Module):
    """Temporal-only attention; each coarse region is an independent batch."""

    def __init__(
        self,
        token_dim: int,
        width: int,
        *,
        layers: int = 2,
        heads: int = 4,
        max_context: int = 20,
    ) -> None:
        super().__init__()
        if width % heads:
            raise ValueError("Transformer width must be divisible by heads")
        self.max_context = max_context
        self.input = nn.Linear(token_dim, width)
        self.position = nn.Parameter(torch.zeros(max_context, width))
        layer = nn.TransformerEncoderLayer(
            d_model=width,
            nhead=heads,
            dim_feedforward=2 * width,
            dropout=0.0,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=layers)
        self.output = nn.Linear(width, token_dim)

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        length = tokens.shape[1]
        if length > self.max_context:
            raise ValueError(f"context {length} exceeds max_context {self.max_context}")
        sequence = self.input(tokens) + self.position[:length]
        causal_mask = torch.triu(
            torch.ones(length, length, device=tokens.device, dtype=torch.bool),
            diagonal=1,
        )
        encoded = self.encoder(sequence, mask=causal_mask)
        return self.output(encoded[:, -1])


class DiagonalSSMTemporal(nn.Module):
    """Stable diagonal linear SSM with pure-PyTorch parallel and scan paths.

    This is intentionally a small classical state-space block, not Mamba.  Its
    transition coefficients stay in ``(0, 1)`` and therefore cannot produce an
    unstable autonomous state.
    """

    def __init__(self, token_dim: int, width: int) -> None:
        super().__init__()
        self.input = nn.Linear(token_dim, width)
        initial_decay = torch.linspace(0.2, 0.98, width).clamp(1.0e-4, 1 - 1.0e-4)
        self.decay_logit = nn.Parameter(torch.logit(initial_decay))
        self.input_gate_logit = nn.Parameter(torch.zeros(width))
        self.output_gate = nn.Linear(width, width)
        self.norm = nn.LayerNorm(width)
        self.output = nn.Linear(width, token_dim)

    def coefficients(self) -> tuple[torch.Tensor, torch.Tensor]:
        decay = torch.sigmoid(self.decay_logit)
        input_gate = torch.sigmoid(self.input_gate_logit)
        return decay, input_gate

    def parallel_states(self, projected: torch.Tensor) -> torch.Tensor:
        """Evaluate the diagonal recurrence by grouped causal convolution."""
        batch, length, width = projected.shape
        decay, input_gate = self.coefficients()
        exponents = torch.arange(length - 1, -1, -1, device=projected.device)
        kernel = decay[:, None].pow(exponents[None, :]) * input_gate[:, None]
        padded = F.pad(projected.transpose(1, 2), (length - 1, 0))
        states = F.conv1d(padded, kernel[:, None, :], groups=width)
        return states.transpose(1, 2).reshape(batch, length, width)

    def recurrent_states(self, projected: torch.Tensor) -> torch.Tensor:
        """Reference recurrent scan used for seek-safe autoregressive rollout."""
        decay, input_gate = self.coefficients()
        hidden = projected.new_zeros((projected.shape[0], projected.shape[2]))
        states = []
        for current in projected.unbind(dim=1):
            hidden = decay * hidden + input_gate * current
            states.append(hidden)
        return torch.stack(states, dim=1)

    def forward(self, tokens: torch.Tensor, *, recurrent: bool = False) -> torch.Tensor:
        projected = self.input(tokens)
        states = (
            self.recurrent_states(projected)
            if recurrent
            else self.parallel_states(projected)
        )
        gate = torch.sigmoid(self.output_gate(projected[:, -1]))
        latest = self.norm(states[:, -1] * gate + projected[:, -1])
        return self.output(latest)


def build_temporal_module(
    family: str,
    token_dim: int,
    width: int,
    *,
    max_context: int = 20,
    transformer_heads: int = 4,
) -> nn.Module:
    if family == "markov":
        return MarkovTemporal(token_dim, width)
    if family in {"gru", "lstm"}:
        return RecurrentTemporal(token_dim, width, cell=family)
    if family == "tcn":
        return TCNTemporal(token_dim, width)
    if family == "transformer":
        return TransformerTemporal(
            token_dim,
            width,
            max_context=max_context,
            heads=transformer_heads,
        )
    if family == "diagonal_ssm":
        return DiagonalSSMTemporal(token_dim, width)
    raise ValueError(f"unknown temporal family {family!r}")


class TemporalMeshOperator(nn.Module):
    """Shared factorised mesh encoder + causal temporal block + mesh decoder."""

    def __init__(
        self,
        *,
        temporal_family: str,
        metadata_dim: int = 0,
        node_metadata_dim: int = 0,
        local_dim: int = 48,
        token_dim: int = 48,
        temporal_width: int = 64,
        local_layers: int = 2,
        coarse_layers: int = 1,
        graph_enabled: bool = True,
        max_context: int = 20,
        transformer_heads: int = 4,
    ) -> None:
        super().__init__()
        input_dim = 4 + 2 + 1 + metadata_dim + node_metadata_dim
        self.temporal_family = temporal_family
        self.metadata_dim = metadata_dim
        self.node_metadata_dim = node_metadata_dim
        self.encoder = FactorizedMeshEncoder(
            input_dim,
            local_dim,
            token_dim,
            local_layers=local_layers,
            coarse_layers=coarse_layers,
            graph_enabled=graph_enabled,
        )
        self.temporal = build_temporal_module(
            temporal_family,
            token_dim,
            temporal_width,
            max_context=max_context,
            transformer_heads=transformer_heads,
        )
        self.decoder = _mlp(
            [input_dim + local_dim + token_dim, local_dim + token_dim, local_dim, 4]
        )

    def forward(
        self,
        history_states: torch.Tensor,
        graph: Mapping[str, torch.Tensor],
        statistics: StateStatistics,
        metadata_history: torch.Tensor | None = None,
        node_metadata_history: torch.Tensor | None = None,
        *,
        recurrent_ssm: bool = False,
    ) -> torch.Tensor:
        latest_features, local, token_history = self.encoder(
            history_states,
            graph,
            statistics,
            metadata_history,
            node_metadata_history,
        )
        if isinstance(self.temporal, DiagonalSSMTemporal):
            predicted_token = self.temporal(token_history, recurrent=recurrent_ssm)
        else:
            predicted_token = self.temporal(token_history)
        broadcast = predicted_token[graph["cluster_index"]]
        return self.decoder(torch.cat([latest_features, local, broadcast], dim=-1))


def apply_directional_state_update(
    current_state: torch.Tensor,
    raw_update: torch.Tensor,
    statistics: StateStatistics,
    *,
    log_psi_bounds: tuple[float, float] = (-12.0, 6.0),
) -> torch.Tensor:
    """Decode physically directed state increments without hard max/min repair."""
    scale = statistics.residual_std.abs().clamp_min(1.0e-8)
    damage_increment = F.softplus(raw_update[:, 0]) * scale[:, 0]
    history_increment = F.softplus(raw_update[:, 1]) * scale[:, 1]
    fatigue_decrement = F.softplus(raw_update[:, 2]) * scale[:, 2]
    raw_residual = raw_update[:, 3] * scale[:, 3] + statistics.residual_mean[:, 3]

    damage = current_state[:, 0] + damage_increment
    damage = damage.clamp_max(1.0)
    history = current_state[:, 1] + history_increment
    fatigue = (current_state[:, 2] - fatigue_decrement).clamp_min(0.0)
    log_psi = (current_state[:, 3] + raw_residual).clamp(*log_psi_bounds)
    return torch.stack([damage, history, fatigue, log_psi], dim=-1)


def _support_moments(
    log_field: torch.Tensor,
    coordinates: torch.Tensor,
    area: torch.Tensor,
    threshold: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    support = soft_support(log_field, threshold)
    weights = support * area
    weights = weights / weights.sum().clamp_min(torch.finfo(weights.dtype).eps)
    centroid = torch.sum(weights[:, None] * coordinates, dim=0)
    variance = torch.sum(
        weights[:, None] * (coordinates - centroid[None, :]).square(), dim=0
    )
    return centroid, torch.sqrt(variance.clamp_min(0.0))


def temporal_mechanism_loss(
    prediction: torch.Tensor,
    target: torch.Tensor,
    graph: Mapping[str, torch.Tensor],
    *,
    active_weight: float = 1.0,
    support_weight: float = 0.25,
    gradient_weight: float = 0.1,
    morphology_weight: float = 0.25,
    active_roughness_weight: float = 0.05,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Shared FEM-centred loss with support morphology and active roughness."""
    base, parts = mechanism_loss(
        prediction,
        target,
        graph["areas"],
        graph["edge_index"],
        active_weight=active_weight,
        support_weight=support_weight,
        gradient_weight=gradient_weight,
    )
    active_prediction = derived_active_log10(prediction)
    active_target = derived_active_log10(target)
    area = graph["areas"].reshape(-1).to(prediction.dtype)
    order = torch.argsort(active_target)
    cumulative = torch.cumsum(area[order], dim=0)
    threshold_index = torch.searchsorted(
        cumulative, 0.99 * area.sum()
    ).clamp_max(len(order) - 1)
    threshold = active_target[order[threshold_index]].detach()
    pred_centroid, pred_width = _support_moments(
        active_prediction, graph["coordinates"], area, threshold
    )
    target_centroid, target_width = _support_moments(
        active_target, graph["coordinates"], area, threshold
    )
    morphology = (pred_centroid - target_centroid).square().mean()
    morphology = morphology + (pred_width - target_width).square().mean()

    src, dst = graph["edge_index"]
    pred_jump = active_prediction[dst] - active_prediction[src]
    target_jump = active_target[dst] - active_target[src]
    active_roughness = (pred_jump - target_jump).square().mean()
    total = (
        base
        + morphology_weight * morphology
        + active_roughness_weight * active_roughness
    )
    return total, {
        **parts,
        "morphology": morphology.detach(),
        "active_roughness": active_roughness.detach(),
        "total": total.detach(),
    }


@dataclass(frozen=True)
class CapacityMatch:
    family: str
    width: int
    parameters: int
    relative_error: float


def match_temporal_width(
    family: str,
    *,
    target_parameters: int,
    tolerance: float,
    model_kwargs: Mapping[str, object],
    candidate_widths: range = range(8, 257, 4),
) -> CapacityMatch:
    """Find the closest legal temporal width for a fixed shared architecture."""
    matches: list[CapacityMatch] = []
    for width in candidate_widths:
        if family == "transformer":
            heads = int(model_kwargs.get("transformer_heads", 4))
            if width % heads:
                continue
        model = TemporalMeshOperator(
            temporal_family=family,
            temporal_width=width,
            **model_kwargs,
        )
        parameters = count_parameters(model)
        relative_error = abs(parameters - target_parameters) / target_parameters
        matches.append(CapacityMatch(family, width, parameters, relative_error))
    if not matches:
        raise ValueError(f"no legal widths for {family}")
    best = min(matches, key=lambda match: (match.relative_error, match.width))
    if best.relative_error > tolerance:
        raise ValueError(
            f"{family} cannot match {target_parameters} parameters within "
            f"{tolerance:.1%}; "
            f"closest is width={best.width}, parameters={best.parameters}"
        )
    return best
