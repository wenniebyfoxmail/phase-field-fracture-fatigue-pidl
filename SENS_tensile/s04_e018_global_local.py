"""Pure S04-E018 UV representation; constructing/evaluating never trains.

``forward(normalized_xy)`` returns RAW UV, compatible with E013's outer BC
helper: normalized_xy = 2 * physical_xy. ``raw_physical`` takes physical XY;
``physical_uv`` applies the frozen BC exactly once. Geometry is determined only
from admitted same-state XY/damage, never supervised UV or residuals.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from network import NeuralNet, init_xavier  # noqa: E402

PADDING = 0.02
DAMAGE_THRESHOLD = 0.1
US = 0.11999988
PARAMETER_COUNT = 1_128_058
ARMS = ("control", "localized")


def damage_geometry(xy: np.ndarray, damage: np.ndarray,
                    mass: np.ndarray | None = None) -> dict:
    """Freeze a rectangular patch from allowed XY/damage information only."""
    xy = np.asarray(xy, dtype=np.float64)
    damage = np.asarray(damage, dtype=np.float64)
    if xy.ndim != 2 or xy.shape[1] != 2 or damage.shape != (len(xy),):
        raise ValueError("XY/damage shapes must be (N,2)/(N,)")
    if len(xy) == 0 or not np.isfinite(xy).all() or not np.isfinite(damage).all():
        raise ValueError("empty or nonfinite geometry")
    if np.any((damage < 0) | (damage > 1)) or np.any((xy < -0.5) | (xy > 0.5)):
        raise ValueError("damage or XY outside locked bounds")
    active = damage > DAMAGE_THRESHOLD
    if not active.any():
        raise ValueError("damage stratum must be nonempty")
    lower, upper = xy[active].min(0), xy[active].max(0)
    center = (lower + upper) / 2
    scale = (upper - lower) / 2 + PADDING
    support = np.all((xy > lower - PADDING) & (xy < upper + PADDING), axis=1)
    result = {
        "lower": lower.tolist(), "upper": upper.tolist(),
        "center": center.tolist(), "scale": scale.tolist(),
        "padding": PADDING, "damage_threshold": DAMAGE_THRESHOLD,
        "damage_nodes": int(active.sum()), "background_nodes": int((~active).sum()),
        "support_nodes": int(support.sum()),
    }
    if mass is not None:
        mass = np.asarray(mass, dtype=np.float64)
        if mass.shape != damage.shape or not np.isfinite(mass).all() or np.any(mass <= 0):
            raise ValueError("mass must be finite positive (N,)")
        result.update(total_mass=float(mass.sum()), damage_mass=float(mass[active].sum()),
                      background_mass=float(mass[~active].sum()), support_mass=float(mass[support].sum()),
                      background_support_mass=float(mass[support & ~active].sum()),
                      background_support_fraction=(float(mass[support & ~active].sum() / mass[~active].sum())
                                                   if (~active).any() else None))
    return result


def compact_window(physical_xy: torch.Tensor, lower: torch.Tensor,
                   upper: torch.Tensor) -> torch.Tensor:
    """C2 separable quintic window, one on core and zero outside padded core."""
    distance = torch.maximum(lower - physical_xy, physical_xy - upper).clamp(min=0)
    t = (distance / PADDING).clamp(min=0, max=1)
    smooth = 1 - 10 * t.pow(3) + 15 * t.pow(4) - 6 * t.pow(5)
    return smooth.prod(dim=1, keepdim=True)


class GlobalLocalUV(nn.Module):
    """Matched arms; geometry is checkpointed as nontrainable buffers.

    Construct with build_model, which guarantees float64/Xavier/seed order.
    ``components_physical`` exposes the actual additive raw contributions for
    diagnostics. It does not change branch weights or train either branch.
    """
    def __init__(self, arm: str, geometry: dict):
        super().__init__()
        if arm not in ARMS:
            raise ValueError(f"unknown arm {arm!r}")
        self.arm = arm
        if geometry.get("padding") != PADDING or geometry.get("damage_threshold") != DAMAGE_THRESHOLD:
            raise ValueError("geometry protocol constants mismatch")
        for name in ("lower", "upper", "center", "scale"):
            value = torch.as_tensor(geometry[name], dtype=torch.float64)
            if value.shape != (2,) or not torch.isfinite(value).all():
                raise ValueError(f"invalid geometry {name}")
            self.register_buffer(name, value.clone())
        if torch.any(self.upper < self.lower) or torch.any(self.scale <= 0):
            raise ValueError("invalid geometry bounds/scale")
        if not torch.equal(self.center, (self.lower + self.upper) / 2):
            raise ValueError("geometry center mismatch")
        if not torch.equal(self.scale, (self.upper - self.lower) / 2 + PADDING):
            raise ValueError("geometry scale mismatch")
        self.global_branch = NeuralNet(2, 2, 8, 283, "TrainableTanh", 1.0)
        init_xavier(self.global_branch)
        self.local_branch = NeuralNet(2, 2, 8, 283, "TrainableReLU", 1.0)
        init_xavier(self.local_branch)

    def components_physical(self, physical_xy: torch.Tensor) -> dict[str, torch.Tensor]:
        global_raw = self.global_branch(2 * physical_xy)
        if self.arm == "localized":
            local_coords = (physical_xy - self.center) / self.scale
            window = compact_window(physical_xy, self.lower, self.upper)
        else:
            local_coords = 2 * physical_xy
            window = torch.ones_like(physical_xy[:, :1])
        local_unwindowed = self.local_branch(local_coords)
        local_raw = window * local_unwindowed
        return {"global_raw": global_raw, "local_raw": local_raw,
                "local_unwindowed": local_unwindowed, "window": window,
                "local_coords": local_coords, "raw": global_raw + local_raw}

    def raw_physical(self, physical_xy: torch.Tensor) -> torch.Tensor:
        return self.components_physical(physical_xy)["raw"]

    def forward(self, normalized_xy: torch.Tensor) -> torch.Tensor:
        return self.raw_physical(normalized_xy / 2)

    def physical_uv(self, physical_xy: torch.Tensor) -> torch.Tensor:
        raw = self.raw_physical(physical_xy)
        y0, y1 = physical_xy[:, 1] + 0.5, 0.5 - physical_xy[:, 1]
        return torch.stack((y0 * y1 * raw[:, 0], y0 * y1 * raw[:, 1] + y0 * US), dim=1)


def build_model(seed: int, arm: str, geometry: dict) -> GlobalLocalUV:
    """Seed once; construct/init G, then construct/init L; restore caller RNG/dtype."""
    old_dtype = torch.get_default_dtype()
    try:
        torch.set_default_dtype(torch.float64)
        with torch.random.fork_rng(devices=[]):
            torch.random.default_generator.manual_seed(seed)
            model = GlobalLocalUV(arm, geometry)
    finally:
        torch.set_default_dtype(old_dtype)
    count = sum(p.numel() for p in model.parameters())
    if count != PARAMETER_COUNT or any(p.dtype != torch.float64 for p in model.parameters()):
        raise RuntimeError(f"invalid E018 parameter count/dtype: {count}")
    return model


def anchor_component_geometry(xy: np.ndarray, damage: np.ndarray,
                              conn: np.ndarray, mass: np.ndarray | None = None) -> dict:
    """R2 patch from the unique initial-notch-anchored active Q4-edge component.

    This selects local *support*, never changes the caller's damage, sampler
    strata, targets or loss domain. Consecutive Q4 edges define adjacency;
    diagonal cell corners are not connected. Component IDs follow smallest
    original node ID, independent of element ordering or union-find roots.
    """
    # Reuse r1 input validation without using its rectangle for selection.
    damage_geometry(xy, damage, mass)
    xy = np.asarray(xy, dtype=np.float64)
    damage = np.asarray(damage, dtype=np.float64)
    conn = np.asarray(conn)
    if conn.ndim != 2 or conn.shape[1] != 4 or not np.issubdtype(conn.dtype, np.integer):
        raise ValueError("connectivity must be integer (E,4)")
    if len(conn) == 0 or conn.min() < 0 or conn.max() >= len(xy):
        raise ValueError("empty or out-of-range connectivity")
    if np.any(np.diff(np.sort(conn, axis=1), axis=1) == 0):
        raise ValueError("Q4 connectivity contains repeated nodes")
    active = damage > DAMAGE_THRESHOLD
    active_ids = np.flatnonzero(active)
    edges = np.stack((conn, np.roll(conn, -1, axis=1)), axis=2).reshape(-1, 2)
    edges = edges[active[edges].all(axis=1)]
    parent = np.arange(len(xy), dtype=np.int64)
    size = np.ones(len(xy), dtype=np.int64)

    def root(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for left, right in edges:
        a, b = root(int(left)), root(int(right))
        if a != b:
            if size[a] < size[b]:
                a, b = b, a
            parent[b] = a
            size[a] += size[b]
    groups = {}
    for node in active_ids:
        groups.setdefault(root(int(node)), []).append(int(node))
    members = sorted((np.asarray(nodes, dtype=np.int64) for nodes in groups.values()),
                     key=lambda nodes: int(nodes[0]))
    anchor = (xy[:, 0] == -0.5) & (np.abs(xy[:, 1]) <= PADDING)
    anchored = [index for index, nodes in enumerate(members) if anchor[nodes].any()]
    if len(anchored) != 1:
        raise ValueError(f"expected unique notch-anchor component, found {len(anchored)}")
    selected_index = anchored[0]
    selected = members[selected_index]
    # A new private selector array is used only to reuse rectangle construction.
    # Original damage values/mask remain untouched and are restored in metadata.
    selector_damage = np.zeros(len(xy), dtype=np.float64)
    selector_damage[selected] = 1.0
    geometry = damage_geometry(xy, selector_damage)
    lower, upper = np.asarray(geometry["lower"]), np.asarray(geometry["upper"])
    support = np.all((xy > lower - PADDING) & (xy < upper + PADDING), axis=1)
    masses = None if mass is None else np.asarray(mass, dtype=np.float64)
    records = []
    for index, nodes in enumerate(members):
        records.append({"component_id": index, "minimum_node_id": int(nodes[0]),
                        "nodes": int(len(nodes)),
                        "mass": None if masses is None else float(masses[nodes].sum()),
                        "lower": xy[nodes].min(0).tolist(), "upper": xy[nodes].max(0).tolist(),
                        "touches_notch_anchor": bool(anchor[nodes].any()),
                        "anchor_nodes": int(anchor[nodes].sum()),
                        "selected_for_local_support": index == selected_index})
    excluded_mask = active.copy()
    excluded_mask[selected] = False
    geometry.update(
        localization_rule="q4_edge_unique_initial_notch_anchor_component",
        anchor_x=-0.5, anchor_abs_y_max=PADDING,
        component_count=len(records), components=records,
        anchor_component_id=selected_index,
        anchor_component_nodes=int(len(selected)),
        damage_nodes=int(active.sum()), background_nodes=int((~active).sum()),
        excluded_damage_nodes=int(excluded_mask.sum()), support_nodes=int(support.sum()),
    )
    if masses is not None:
        geometry.update(total_mass=float(masses.sum()), damage_mass=float(masses[active].sum()),
                        background_mass=float(masses[~active].sum()), support_mass=float(masses[support].sum()),
                        anchor_component_mass=float(masses[selected].sum()),
                        excluded_damage_mass=float(masses[excluded_mask].sum()),
                        excluded_damage_support_mass=float(masses[excluded_mask & support].sum()),
                        background_support_mass=float(masses[~active & support].sum()),
                        background_support_fraction=(float(masses[~active & support].sum() / masses[~active].sum())
                                                     if (~active).any() else None))
    return geometry
