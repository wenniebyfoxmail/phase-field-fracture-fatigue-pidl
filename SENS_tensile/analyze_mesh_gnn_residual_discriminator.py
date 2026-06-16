#!/usr/bin/env python3
"""Offline mesh-graph residual discriminator for FEM/PIDL field gaps.

This is a post-hoc analysis tool, not a PIDL training runner.  It asks whether
local mesh neighbourhood information can learn the FEM-PIDL residual in
``psi_active`` or ``alpha_bar`` on strict FEM-mesh checkpoints.  A positive
offline result would justify a later online residual-correction experiment; a
negative result closes this direction cheaply.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from scipy.io import loadmat
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from pidl_fem_alignment_protocol import (  # noqa: E402
    FEM_SOFT_HIST0_FIELDS,
    PIDL_FEMMESH_ARCHIVE,
    PIDL_FEMMESH_MESH,
    PIDL_SAVED_INDEX_OFFSET_FOR_FEM_CYCLE,
)

EPS = 1.0e-30


@dataclass
class CycleGraph:
    fem_cycle: int
    pidl_cycle: int
    x: np.ndarray
    y: np.ndarray
    area: np.ndarray
    features: np.ndarray
    target_residual: np.ndarray
    pidl_value: np.ndarray
    fem_value: np.ndarray
    edge_src: np.ndarray
    edge_dst: np.ndarray
    weights: np.ndarray


def _orient_by_last_dim(arr: np.ndarray, n_cols: int) -> np.ndarray:
    out = np.asarray(arr)
    if out.ndim == 2 and out.shape[0] == n_cols and out.shape[1] != n_cols:
        return out.T
    return out


def _center_if_unit_square(centroids: np.ndarray) -> np.ndarray:
    out = np.asarray(centroids, dtype=np.float64).copy()
    xy = out[:, :2]
    if (
        xy[:, 0].min() >= -1e-9
        and xy[:, 1].min() >= -1e-9
        and xy[:, 0].max() <= 1.0 + 1e-9
        and xy[:, 1].max() <= 1.0 + 1e-9
    ):
        out[:, :2] = xy - 0.5
    return out


def _cycle_by_elem_h5(h5: h5py.File, name: str, n_cycles: int) -> np.ndarray:
    arr = np.asarray(h5[name], dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"{name} must be 2-D, got {arr.shape}")
    if arr.shape[0] == n_cycles:
        return arr.T
    if arr.shape[1] == n_cycles:
        return arr
    raise ValueError(f"{name} shape {arr.shape} incompatible with {n_cycles} cycles")


def _cycle_by_elem_mat(data: dict, name: str, n_cycles: int) -> np.ndarray:
    arr = np.asarray(data[name], dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"{name} must be 2-D, got {arr.shape}")
    if arr.shape[0] == n_cycles:
        return arr.T
    if arr.shape[1] == n_cycles:
        return arr
    raise ValueError(f"{name} shape {arr.shape} incompatible with {n_cycles} cycles")


def _first_existing(container, names: tuple[str, ...]) -> str:
    for name in names:
        if name in container:
            return name
    raise KeyError(f"Missing FEM field; tried {names}")


def load_fem_combined(path: Path) -> dict:
    """Load compact FEM handoff into n_elem x n_cycle arrays."""
    path = path.expanduser()
    try:
        with h5py.File(path, "r") as h5:
            cycles = np.asarray(h5["cycles"]).reshape(-1).astype(int)
            fields = {}
            aliases = {
                "d_elem": ("d_elem", "alpha_elem"),
                "psi_elem": ("psi_elem", "psi_plus_elem"),
                "alpha_bar_elem": ("alpha_bar_elem", "hist_fat_elem"),
                "f_alpha_elem": ("f_alpha_elem", "f_fatigue_elem"),
            }
            for key, names in aliases.items():
                fields[key] = _cycle_by_elem_h5(
                    h5, _first_existing(h5, names), len(cycles)
                )
            centroids = _center_if_unit_square(
                _orient_by_last_dim(np.asarray(h5["element_centroids"]), 2)
            )
    except OSError:
        data = loadmat(str(path))
        cycles = np.asarray(data["cycles"]).reshape(-1).astype(int)
        fields = {}
        aliases = {
            "d_elem": ("d_elem", "alpha_elem"),
            "psi_elem": ("psi_elem", "psi_plus_elem"),
            "alpha_bar_elem": ("alpha_bar_elem", "hist_fat_elem"),
            "f_alpha_elem": ("f_alpha_elem", "f_fatigue_elem"),
        }
        for key, names in aliases.items():
            fields[key] = _cycle_by_elem_mat(
                data, _first_existing(data, names), len(cycles)
            )
        centroids = _center_if_unit_square(
            _orient_by_last_dim(np.asarray(data["element_centroids"]), 2)
        )
    return {"path": path, "cycles": cycles, "fields": fields, "centroids": centroids}


def parse_cycles(text: str) -> list[int]:
    return [int(x.strip()) for x in str(text).split(",") if x.strip()]


def ensure_pidl_npz(
    archive: Path,
    diag_dir: Path,
    pidl_cycle: int,
    umax: float,
    device: torch.device,
    mesh_file: Path | None,
) -> Path:
    diag_dir.mkdir(parents=True, exist_ok=True)
    path = diag_dir / f"element_fields_cycle_{pidl_cycle:04d}.npz"
    if path.exists():
        return path
    from export_pidl_element_diagnostics import export_cycle

    export_cycle(
        archive=archive,
        cycle=pidl_cycle,
        out_dir=diag_dir,
        device=device,
        umax=umax,
        write_fields=True,
        mesh_file=mesh_file,
    )
    return path


def npz_field(npz, name: str, default: float = 0.0) -> np.ndarray:
    if name in npz:
        return np.asarray(npz[name], dtype=np.float64).reshape(-1)
    n = len(np.asarray(npz["elem_x"]).reshape(-1))
    return np.full(n, float(default), dtype=np.float64)


def transform_target(name: str, values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if name == "alpha_bar":
        return np.log10(np.maximum(values, 0.0) + 1.0)
    if name == "psi_active":
        return np.log10(np.maximum(values, 0.0) + EPS)
    raise ValueError(f"unknown target {name!r}")


def inverse_target(name: str, values: np.ndarray) -> np.ndarray:
    if name == "alpha_bar":
        return np.maximum(np.power(10.0, values) - 1.0, 0.0)
    if name == "psi_active":
        return np.maximum(np.power(10.0, values) - EPS, 0.0)
    raise ValueError(f"unknown target {name!r}")


def make_features(npz, fem_cycle: int, cycle_scale: float) -> np.ndarray:
    x = npz_field(npz, "elem_x")
    y = npz_field(npz, "elem_y")
    area = npz_field(npz, "area_elem", 1.0)
    r0 = np.sqrt(x * x + y * y)
    base = [
        x,
        y,
        np.abs(y),
        r0,
        0.5 - x,
        np.maximum(x, 0.0),
        np.log10(np.maximum(area, EPS)),
        np.full_like(x, float(fem_cycle) / cycle_scale),
        (np.abs(y) <= 0.02).astype(np.float64),
        (r0 <= 0.02).astype(np.float64),
    ]
    positive = [
        "alpha_elem",
        "hist_fat_elem",
        "f_fatigue_elem",
        "g_alpha_elem",
        "psi_raw_elem",
        "psi_active_elem",
        "psi_plus_prev_elem",
        "E_el_elem",
        "E_d_elem",
        "E_hist_elem",
        "residual_abs_Eel_Ed",
        "eps_eq_elem",
    ]
    signed = [
        "eps_xx_elem",
        "eps_yy_elem",
        "eps_xy_elem",
        "sigma_raw_xx_elem",
        "sigma_raw_yy_elem",
        "sigma_raw_xy_elem",
        "sigma_effective_xx_elem",
        "sigma_effective_yy_elem",
        "sigma_effective_xy_elem",
    ]
    for name in positive:
        val = npz_field(npz, name)
        base.append(np.log10(np.maximum(np.abs(val), EPS)))
    for name in signed:
        val = npz_field(npz, name)
        scale = np.nanpercentile(np.abs(val), 99.0)
        if not np.isfinite(scale) or scale <= EPS:
            scale = 1.0
        base.append(np.clip(val / scale, -10.0, 10.0))
    features = np.vstack(base).T
    return np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)


def build_knn_edges(x: np.ndarray, y: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    xy = np.column_stack([x, y])
    n = len(xy)
    if n <= 1:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
    kk = min(int(k) + 1, n)
    _, ids = cKDTree(xy).query(xy, k=kk)
    ids = np.atleast_2d(ids)
    dst = np.repeat(np.arange(n), ids.shape[1] - 1)
    src = ids[:, 1:].reshape(-1)
    return src.astype(np.int64), dst.astype(np.int64)


def fem_target_on_pidl(
    fem: dict,
    fem_cycle: int,
    target: str,
    pidl_xy: np.ndarray,
) -> np.ndarray:
    cycles = fem["cycles"].tolist()
    if fem_cycle not in cycles:
        raise ValueError(f"FEM cycle {fem_cycle} absent from {fem['path']}")
    idx = cycles.index(fem_cycle)
    fields = fem["fields"]
    if target == "alpha_bar":
        fem_native = fields["alpha_bar_elem"][:, idx]
    elif target == "psi_active":
        d = fields["d_elem"][:, idx]
        psi = fields["psi_elem"][:, idx]
        fem_native = ((1.0 - d) ** 2 + 1.0e-6) * psi
    else:
        raise ValueError(f"unknown target {target!r}")
    _, nn_ids = cKDTree(fem["centroids"][:, :2]).query(pidl_xy, k=1)
    return np.asarray(fem_native[nn_ids], dtype=np.float64)


def build_cycle_graph(
    fem: dict,
    target: str,
    fem_cycle: int,
    pidl_cycle: int,
    npz_path: Path,
    k: int,
    tip_weight: float,
    tip_weight_radius: float,
    cycle_scale: float,
) -> CycleGraph:
    with np.load(npz_path) as npz:
        x = npz_field(npz, "elem_x")
        y = npz_field(npz, "elem_y")
        area = np.maximum(npz_field(npz, "area_elem", 1.0), EPS)
        pidl_value = (
            npz_field(npz, "hist_fat_elem")
            if target == "alpha_bar"
            else npz_field(npz, "psi_active_elem")
        )
        fem_value = fem_target_on_pidl(fem, fem_cycle, target, np.column_stack([x, y]))
        features = make_features(npz, fem_cycle, cycle_scale)
    pidl_log = transform_target(target, pidl_value)
    fem_log = transform_target(target, fem_value)
    residual = fem_log - pidl_log
    src, dst = build_knn_edges(x, y, k)
    r0 = np.sqrt(x * x + y * y)
    weights = area * (1.0 + float(tip_weight) * np.exp(-(r0 / tip_weight_radius) ** 2))
    weights = weights / np.nanmean(weights)
    return CycleGraph(
        fem_cycle=fem_cycle,
        pidl_cycle=pidl_cycle,
        x=x,
        y=y,
        area=area,
        features=features,
        target_residual=np.nan_to_num(residual, nan=0.0, posinf=0.0, neginf=0.0),
        pidl_value=np.nan_to_num(pidl_value, nan=0.0, posinf=0.0, neginf=0.0),
        fem_value=np.nan_to_num(fem_value, nan=0.0, posinf=0.0, neginf=0.0),
        edge_src=src,
        edge_dst=dst,
        weights=np.nan_to_num(weights, nan=1.0, posinf=1.0, neginf=1.0),
    )


class GraphResidualNet(nn.Module):
    def __init__(self, n_features: int, hidden: int, n_layers: int, dropout: float, use_graph: bool):
        super().__init__()
        self.use_graph = use_graph
        self.input_layer = nn.Linear(n_features, hidden)
        self.self_layers = nn.ModuleList(nn.Linear(hidden, hidden) for _ in range(n_layers))
        self.neigh_layers = nn.ModuleList(nn.Linear(hidden, hidden) for _ in range(n_layers))
        self.norms = nn.ModuleList(nn.LayerNorm(hidden) for _ in range(n_layers))
        self.out = nn.Linear(hidden, 1)
        self.dropout = nn.Dropout(float(dropout))

    @staticmethod
    def _neighbour_mean(h: torch.Tensor, src: torch.Tensor, dst: torch.Tensor) -> torch.Tensor:
        if src.numel() == 0:
            return torch.zeros_like(h)
        out = torch.zeros_like(h)
        out.index_add_(0, dst, h[src])
        deg = torch.zeros(h.shape[0], dtype=h.dtype, device=h.device)
        deg.index_add_(0, dst, torch.ones_like(dst, dtype=h.dtype))
        return out / deg.clamp_min(1.0).unsqueeze(1)

    def forward(self, graph: dict[str, torch.Tensor]) -> torch.Tensor:
        h = torch.relu(self.input_layer(graph["features"]))
        for self_layer, neigh_layer, norm in zip(self.self_layers, self.neigh_layers, self.norms):
            if self.use_graph:
                neigh = self._neighbour_mean(h, graph["edge_src"], graph["edge_dst"])
                h_new = self_layer(h) + neigh_layer(neigh)
            else:
                h_new = self_layer(h)
            h = norm(torch.relu(h_new))
            h = self.dropout(h)
        return self.out(h).squeeze(-1)


def standardize_graphs(train: list[CycleGraph], graphs: list[CycleGraph]) -> tuple[np.ndarray, np.ndarray]:
    all_train = np.vstack([g.features for g in train])
    mean = np.nanmean(all_train, axis=0)
    std = np.nanstd(all_train, axis=0)
    std[std < 1.0e-12] = 1.0
    for graph in graphs:
        graph.features = np.nan_to_num((graph.features - mean) / std)
    return mean, std


def to_torch_graph(graph: CycleGraph, device: torch.device) -> dict[str, torch.Tensor]:
    return {
        "features": torch.as_tensor(graph.features, dtype=torch.float32, device=device),
        "target": torch.as_tensor(graph.target_residual, dtype=torch.float32, device=device),
        "weights": torch.as_tensor(graph.weights, dtype=torch.float32, device=device),
        "edge_src": torch.as_tensor(graph.edge_src, dtype=torch.long, device=device),
        "edge_dst": torch.as_tensor(graph.edge_dst, dtype=torch.long, device=device),
    }


def weighted_loss(pred: torch.Tensor, target: torch.Tensor, weights: torch.Tensor) -> torch.Tensor:
    return torch.sum(weights * (pred - target) ** 2) / torch.sum(weights).clamp_min(1.0e-12)


def train_model(
    train_graphs: list[dict[str, torch.Tensor]],
    n_features: int,
    model_kind: str,
    args,
    device: torch.device,
) -> GraphResidualNet:
    model = GraphResidualNet(
        n_features=n_features,
        hidden=args.hidden,
        n_layers=args.layers,
        dropout=args.dropout,
        use_graph=(model_kind == "graph"),
    ).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    for epoch in range(1, args.epochs + 1):
        model.train()
        opt.zero_grad(set_to_none=True)
        losses = []
        for graph in train_graphs:
            losses.append(weighted_loss(model(graph), graph["target"], graph["weights"]))
        loss = torch.stack(losses).mean()
        loss.backward()
        opt.step()
        if args.print_every and (epoch == 1 or epoch % args.print_every == 0):
            print(f"[{model_kind}] epoch {epoch:04d} loss={float(loss.detach().cpu()):.6e}")
    return model


def weighted_mean(values: np.ndarray, weights: np.ndarray, mask: np.ndarray | None = None) -> float:
    if mask is None:
        mask = np.ones(values.shape, dtype=bool)
    mask = mask & np.isfinite(values) & np.isfinite(weights)
    if not np.any(mask):
        return float("nan")
    return float(np.sum(values[mask] * weights[mask]) / np.sum(weights[mask]))


def field_metrics(values: np.ndarray, area: np.ndarray, x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {}
    r0 = np.sqrt(x * x + y * y)
    return {
        "max": float(np.nanmax(values)),
        "p99": float(np.nanpercentile(values, 99.0)),
        "p999": float(np.nanpercentile(values, 99.9)),
        "domain_mean": weighted_mean(values, area),
        "tip_2l0_mean": weighted_mean(values, area, r0 <= 0.02),
        "tip_4l0_mean": weighted_mean(values, area, r0 <= 0.04),
        "right_band_mean": weighted_mean(values, area, x >= 0.45),
        "crack_strip_mean": weighted_mean(values, area, np.abs(y) <= 0.02),
    }


def evaluate_graph(
    graph: CycleGraph,
    model: GraphResidualNet,
    torch_graph: dict[str, torch.Tensor],
    target: str,
    model_kind: str,
    split: str,
    out_dir: Path,
    write_predictions: bool,
) -> tuple[list[dict], list[dict]]:
    model.eval()
    with torch.no_grad():
        pred = model(torch_graph).detach().cpu().numpy()
    true = graph.target_residual
    weights = graph.weights
    before_mae = weighted_mean(np.abs(true), weights)
    after_mae = weighted_mean(np.abs(true - pred), weights)
    before_rmse = math.sqrt(weighted_mean(true * true, weights))
    after_rmse = math.sqrt(weighted_mean((true - pred) ** 2, weights))
    pidl_log = transform_target(target, graph.pidl_value)
    corrected = inverse_target(target, pidl_log + pred)

    error_rows = [{
        "target": target,
        "model": model_kind,
        "split": split,
        "fem_cycle": graph.fem_cycle,
        "pidl_cycle": graph.pidl_cycle,
        "log_mae_before": before_mae,
        "log_mae_after": after_mae,
        "log_rmse_before": before_rmse,
        "log_rmse_after": after_rmse,
        "mae_improvement": 1.0 - after_mae / before_mae if before_mae > 0 else np.nan,
        "rmse_improvement": 1.0 - after_rmse / before_rmse if before_rmse > 0 else np.nan,
    }]

    metric_rows = []
    sources = {
        "FEM": graph.fem_value,
        "PIDL": graph.pidl_value,
        "corrected": corrected,
    }
    fem_metrics = field_metrics(graph.fem_value, graph.area, graph.x, graph.y)
    for source, values in sources.items():
        current = field_metrics(values, graph.area, graph.x, graph.y)
        for metric, value in current.items():
            fem_value = fem_metrics.get(metric, np.nan)
            metric_rows.append({
                "target": target,
                "model": model_kind,
                "split": split,
                "fem_cycle": graph.fem_cycle,
                "pidl_cycle": graph.pidl_cycle,
                "source": source,
                "metric": metric,
                "value": value,
                "over_fem": value / fem_value if abs(fem_value) > EPS else np.nan,
            })

    if write_predictions:
        np.savez_compressed(
            out_dir / f"{model_kind}_{target}_fem{graph.fem_cycle:04d}_pidl{graph.pidl_cycle:04d}.npz",
            x=graph.x.astype(np.float32),
            y=graph.y.astype(np.float32),
            area=graph.area.astype(np.float32),
            fem=graph.fem_value.astype(np.float32),
            pidl=graph.pidl_value.astype(np.float32),
            corrected=corrected.astype(np.float32),
            true_residual=true.astype(np.float32),
            predicted_residual=pred.astype(np.float32),
        )
    return error_rows, metric_rows


def plot_prediction(path: Path, graph: CycleGraph, corrected: np.ndarray, target: str, title: str) -> None:
    panels = [
        ("FEM target", graph.fem_value),
        ("PIDL", graph.pidl_value),
        ("corrected", corrected),
        ("corrected - FEM", corrected - graph.fem_value),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(13.0, 3.2), constrained_layout=True)
    vfinite = np.concatenate([graph.fem_value[np.isfinite(graph.fem_value)], graph.pidl_value[np.isfinite(graph.pidl_value)], corrected[np.isfinite(corrected)]])
    vmin, vmax = np.nanpercentile(vfinite, [1.0, 99.5])
    rlim = max(np.nanpercentile(np.abs(corrected - graph.fem_value), 99.0), EPS)
    for ax, (label, values) in zip(axes, panels):
        if " - " in label:
            im = ax.scatter(graph.x, graph.y, c=values, s=5, cmap="RdBu_r", vmin=-rlim, vmax=rlim)
        else:
            im = ax.scatter(graph.x, graph.y, c=values, s=5, cmap="magma", vmin=vmin, vmax=vmax)
        ax.set_title(label, fontsize=9)
        ax.set_aspect("equal")
        ax.set_xlim(-0.52, 0.52)
        ax.set_ylim(-0.08, 0.08)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
    fig.suptitle(f"{title}: {target}", fontsize=11)
    fig.savefig(path, dpi=220)
    plt.close(fig)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=PIDL_FEMMESH_ARCHIVE)
    parser.add_argument("--diagnostics-dir", type=Path, default=None)
    parser.add_argument("--fem-combined-mat", type=Path, default=FEM_SOFT_HIST0_FIELDS)
    parser.add_argument("--pidl-mesh", type=Path, default=PIDL_FEMMESH_MESH)
    parser.add_argument("--umax", type=float, default=0.12)
    parser.add_argument("--train-cycles", default="20,40")
    parser.add_argument("--test-cycles", default="69")
    parser.add_argument("--pidl-cycle-offset", type=int, default=PIDL_SAVED_INDEX_OFFSET_FOR_FEM_CYCLE)
    parser.add_argument("--targets", default="psi_active,alpha_bar")
    parser.add_argument("--models", default="graph,mlp", help="Comma-separated: graph,mlp")
    parser.add_argument("--knn", type=int, default=8)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.05)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--lr", type=float, default=1.0e-3)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--tip-weight", type=float, default=3.0)
    parser.add_argument("--tip-weight-radius", type=float, default=0.05)
    parser.add_argument("--cycle-scale", type=float, default=100.0)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--print-every", type=int, default=50)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--plot", action="store_true")
    parser.add_argument("--write-predictions", action="store_true")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "_analysis_fem_mechanism_20260528/experiments/mesh_gnn_residual_discriminator_20260616",
    )
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device(args.device)
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    fem = load_fem_combined(args.fem_combined_mat)
    train_cycles = parse_cycles(args.train_cycles)
    test_cycles = parse_cycles(args.test_cycles)
    all_cycles = train_cycles + [c for c in test_cycles if c not in train_cycles]
    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    diagnostics_dir = args.diagnostics_dir or (out_dir / "0_pidl_element_fields")

    all_error_rows: list[dict] = []
    all_metric_rows: list[dict] = []
    manifest_rows: list[dict] = []

    for target in targets:
        graphs: dict[int, CycleGraph] = {}
        for fem_cycle in all_cycles:
            pidl_cycle = fem_cycle + args.pidl_cycle_offset
            if pidl_cycle < 0:
                raise ValueError(f"FEM cycle {fem_cycle} maps to negative PIDL cycle {pidl_cycle}")
            npz_path = ensure_pidl_npz(
                archive=args.archive,
                diag_dir=diagnostics_dir,
                pidl_cycle=pidl_cycle,
                umax=args.umax,
                device=torch.device("cpu"),
                mesh_file=args.pidl_mesh,
            )
            graph = build_cycle_graph(
                fem=fem,
                target=target,
                fem_cycle=fem_cycle,
                pidl_cycle=pidl_cycle,
                npz_path=npz_path,
                k=args.knn,
                tip_weight=args.tip_weight,
                tip_weight_radius=args.tip_weight_radius,
                cycle_scale=args.cycle_scale,
            )
            graphs[fem_cycle] = graph
            manifest_rows.append({
                "target": target,
                "fem_cycle": fem_cycle,
                "pidl_cycle": pidl_cycle,
                "npz_path": str(npz_path),
                "n_elem": len(graph.x),
                "n_edges": len(graph.edge_src),
            })

        train_graphs_np = [graphs[c] for c in train_cycles]
        all_graphs_np = list(graphs.values())
        standardize_graphs(train_graphs_np, all_graphs_np)
        n_features = train_graphs_np[0].features.shape[1]
        torch_graphs = {c: to_torch_graph(g, device) for c, g in graphs.items()}

        for model_kind in models:
            if model_kind not in {"graph", "mlp"}:
                raise ValueError(f"Unknown model {model_kind!r}; expected graph or mlp")
            model = train_model(
                [torch_graphs[c] for c in train_cycles],
                n_features=n_features,
                model_kind=model_kind,
                args=args,
                device=device,
            )
            for fem_cycle, graph in graphs.items():
                split = "train" if fem_cycle in train_cycles else "test"
                error_rows, metric_rows = evaluate_graph(
                    graph=graph,
                    model=model,
                    torch_graph=torch_graphs[fem_cycle],
                    target=target,
                    model_kind=model_kind,
                    split=split,
                    out_dir=out_dir,
                    write_predictions=args.write_predictions,
                )
                all_error_rows.extend(error_rows)
                all_metric_rows.extend(metric_rows)
                if args.plot and split == "test":
                    with torch.no_grad():
                        pred = model(torch_graphs[fem_cycle]).detach().cpu().numpy()
                    corrected = inverse_target(target, transform_target(target, graph.pidl_value) + pred)
                    plot_prediction(
                        out_dir / f"{model_kind}_{target}_fem{fem_cycle:04d}.png",
                        graph,
                        corrected,
                        target,
                        f"{model_kind} FEM c{fem_cycle} / PIDL j{graph.pidl_cycle}",
                    )

    write_csv(out_dir / "mesh_gnn_residual_error_metrics.csv", all_error_rows)
    write_csv(out_dir / "mesh_gnn_residual_field_metrics.csv", all_metric_rows)
    write_csv(out_dir / "mesh_gnn_residual_manifest.csv", manifest_rows)

    print(f"wrote {out_dir / 'mesh_gnn_residual_error_metrics.csv'}")
    print(f"wrote {out_dir / 'mesh_gnn_residual_field_metrics.csv'}")
    for row in all_error_rows:
        if row["split"] == "test":
            print(
                f"{row['target']} {row['model']} FEM c{row['fem_cycle']} "
                f"MAE {row['log_mae_before']:.4g}->{row['log_mae_after']:.4g} "
                f"improve={row['mae_improvement']:.2%}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
