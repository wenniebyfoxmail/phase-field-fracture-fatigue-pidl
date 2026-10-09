"""Damage-conditioned native-Q4 equilibrium operator for S09-E004."""
from __future__ import annotations

import numpy as np
import torch
from torch import nn

from s09_operator import IntegralBlock, mlp


def _unique_edges(conn: np.ndarray) -> np.ndarray:
    ring = ((0, 1), (1, 2), (2, 3), (3, 0))
    pairs = []
    for left, right in ring:
        pairs.extend((conn[:, [left, right]], conn[:, [right, left]]))
    edges = np.concatenate(pairs, axis=0)
    keys = edges[:, 0].astype(np.int64) * (int(conn.max()) + 1) + edges[:, 1]
    return edges[np.sort(np.unique(keys, return_index=True)[1])]


def _edge_tensors(xy, edges, source_area):
    src, dst = edges.T
    relative_xy = xy[src] - xy[dst]
    span = np.maximum(xy.max(0) - xy.min(0), 1e-12)
    relative_xy = relative_xy / span
    relative = np.column_stack((relative_xy, np.linalg.norm(relative_xy, axis=1)))
    incoming = np.zeros(len(xy), dtype=np.float64)
    np.add.at(incoming, dst, source_area[src])
    if np.any(incoming <= 0):
        raise ValueError("graph contains a node without incoming support")
    weight = source_area[src] / incoming[dst]
    return edges.T, relative, weight


def build_graph(xy: np.ndarray, conn: np.ndarray, area: np.ndarray, bins: int = 24):
    """Build deterministic node and coarse graphs from native connectivity."""
    xy = np.asarray(xy, dtype=np.float64)
    conn = np.asarray(conn, dtype=np.int64)
    area = np.asarray(area, dtype=np.float64)
    node_edges = _unique_edges(conn)
    edges, relative, weight = _edge_tensors(xy, node_edges, area)

    span = np.maximum(xy.max(0) - xy.min(0), 1e-12)
    raw = np.floor((xy - xy.min(0)) / span * bins).astype(np.int64)
    raw = np.clip(raw, 0, bins - 1)
    labels = raw[:, 0] + bins * raw[:, 1]
    occupied, cluster = np.unique(labels, return_inverse=True)
    coarse_area = np.bincount(cluster, weights=area, minlength=len(occupied))
    coarse_xy = np.zeros((len(occupied), 2), dtype=np.float64)
    np.add.at(coarse_xy, cluster, xy * area[:, None])
    coarse_xy /= coarse_area[:, None]
    occupied_set = {int(value): i for i, value in enumerate(occupied)}
    coarse_pairs = []
    for value, index in occupied_set.items():
        ix, iy = value % bins, value // bins
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                other = (ix + dx) + bins * (iy + dy)
                if 0 <= ix+dx < bins and 0 <= iy+dy < bins and other in occupied_set:
                    coarse_pairs.append((index, occupied_set[other]))
    coarse_pairs = np.asarray(coarse_pairs, dtype=np.int64)
    coarse_edges, coarse_relative, coarse_weight = _edge_tensors(
        coarse_xy, coarse_pairs, coarse_area
    )
    boundary = np.isclose(xy[:, 1], xy[:, 1].min(), atol=1e-12, rtol=0) | np.isclose(
        xy[:, 1], xy[:, 1].max(), atol=1e-12, rtol=0
    )
    return {
        "xy": xy, "area": area, "boundary": boundary,
        "edges": edges, "relative": relative, "weight": weight,
        "cluster": cluster, "coarse_area": coarse_area,
        "coarse_edges": coarse_edges, "coarse_relative": coarse_relative,
        "coarse_weight": coarse_weight,
    }


def graph_to_torch(graph: dict, device, dtype=torch.float32):
    integer = {"edges", "cluster", "coarse_edges"}
    boolean = {"boundary"}
    result = {}
    for key, value in graph.items():
        if key in integer:
            result[key] = torch.as_tensor(value, dtype=torch.long, device=device)
        elif key in boolean:
            result[key] = torch.as_tensor(value, dtype=torch.bool, device=device)
        else:
            result[key] = torch.as_tensor(value, dtype=dtype, device=device)
    return result


class EquilibriumOperator(nn.Module):
    """Map prescribed nodal damage and scalar peak load to nodal displacement."""
    def __init__(self, correction_scale, load_scale=0.12, width=32, rank=8):
        super().__init__()
        self.register_buffer("correction_scale", torch.as_tensor(correction_scale, dtype=torch.float32))
        self.register_buffer("load_scale", torch.as_tensor(float(load_scale), dtype=torch.float32))
        self.encoder = mlp(5, width, width)
        self.blocks = nn.ModuleList([IntegralBlock(width, rank) for _ in range(2)])
        self.coarse = IntegralBlock(width, rank)
        self.decoder = mlp(3 * width, width, 2)
        nn.init.zeros_(self.decoder[-1].weight)
        nn.init.zeros_(self.decoder[-1].bias)

    def forward(self, damage, load, graph):
        if damage.shape != (len(graph["xy"]),):
            raise ValueError("damage must be one nodal scalar field")
        t = (graph["xy"][:, 1] - graph["xy"][:, 1].min())
        t = t / (graph["xy"][:, 1].max() - graph["xy"][:, 1].min())
        load_value = torch.as_tensor(load, dtype=damage.dtype, device=damage.device)
        features = torch.cat(
            (damage[:, None], graph["xy"], graph["boundary"][:, None].to(damage.dtype),
             (load_value / self.load_scale).expand(len(damage), 1)), dim=1
        )
        encoded = self.encoder(features)
        local = encoded
        for block in self.blocks:
            local = block(local, graph["edges"], graph["relative"], graph["weight"])
        coarse = local.new_zeros((len(graph["coarse_area"]), local.shape[1]))
        coarse.index_add_(0, graph["cluster"], local * graph["area"][:, None])
        coarse = coarse / graph["coarse_area"][:, None]
        coarse = self.coarse(
            coarse, graph["coarse_edges"], graph["coarse_relative"], graph["coarse_weight"]
        )
        raw = self.decoder(torch.cat((encoded, local, coarse[graph["cluster"]]), dim=1))
        base = torch.stack((torch.zeros_like(t), t), dim=1)
        normalized = base + (t * (1-t))[:, None] * raw * self.correction_scale
        return load_value * normalized


def affine_displacement(xy: torch.Tensor, load) -> torch.Tensor:
    t = (xy[:, 1] - xy[:, 1].min()) / (xy[:, 1].max() - xy[:, 1].min())
    return torch.stack((torch.zeros_like(t), t * load), dim=1)


def correction_scale(train_u, train_load, xy, area):
    """Frozen per-component RMS of normalized non-affine training correction."""
    t = (xy[:, 1] - xy[:, 1].min()) / (xy[:, 1].max() - xy[:, 1].min())
    base = np.column_stack((np.zeros(len(xy)), t))
    correction = train_u / train_load[:, None, None] - base[None]
    variance = (correction ** 2 * area[None, :, None]).sum(axis=(0, 1))
    variance /= area.sum() * len(train_u)
    scale = np.sqrt(variance)
    if not np.isfinite(scale).all() or np.any(scale <= 1e-12):
        raise ValueError("invalid correction scale")
    return scale


def area_mse(prediction, target, scale, area):
    error = ((prediction - target) / scale).square().mean(dim=1)
    return (error * area).sum() / area.sum()


def weighted_l2(prediction, target, area):
    return torch.sqrt((((prediction-target).square().sum(dim=1)) * area).sum())
