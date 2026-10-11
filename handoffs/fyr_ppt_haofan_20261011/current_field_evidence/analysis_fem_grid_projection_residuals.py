#!/usr/bin/env python3
"""FEM-grid projected residual panels for hard-recovery PIDL vs SENS FEM.

The run archive stores PIDL element centroids and areas. The run settings point
to the corresponding FEM-soft-history PIDL triangular mesh, which is available
locally and is verified against the centroid/area export before projection.
PIDL element fields are therefore projected to the FEM quadrilateral grid by
true polygon-overlap area averaging.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import h5py
import meshio
import numpy as np
import scipy.io as sio
from matplotlib.path import Path as MplPath
from scipy.spatial import cKDTree

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import LogNorm, Normalize, TwoSlopeNorm
from shapely.geometry import Polygon
from shapely.strtree import STRtree

plt.rcParams.update(
    {
        "font.size": 11,
        "axes.titlesize": 11,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


ROOT = Path(
    "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/"
    "after_strict_setting_alignment/fem/three_case_compare_20260701"
)
EXTRACTED = ROOT / "extracted"
FEM_MAIN = EXTRACTED / "SENS_brittle_base_cyclic_u012_recovery_fatigueon_pidlstop_newtontol4em4"
FEM_STATE0 = (
    EXTRACTED
    / "SENS_brittle_base_cyclic_u012_recovery_fatigueon_pidlstop_newtontol4em4__state0_recovery_from_driver_folder"
)
PIDL_RUN = Path(
    "/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/"
    "hard_d1_u0_recovery_5step_0630_formal/raw/run"
)
PIDL_DIAG = PIDL_RUN / "element_diagnostics_probe_driver"
PIDL_FINE_MESH = (
    Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code")
    / "SENS_tensile"
    / "meshed_geom_fem_soft_hist0.msh"
)

OUT = ROOT / "analysis" / "state_mechanism_compare_20260701" / "projected_residuals"
FIG = OUT / "figures"
TAB = OUT / "tables"
DATA = OUT / "projected_npz"

PANEL_TITLE_SIZE = 11
TAIL_TITLE_SIZE = 10
TAIL_ROW_LABEL_SIZE = 10
CBAR_TICK_SIZE = 10
CBAR_LABEL_SIZE = 11
SUPTITLE_SIZE = 14
RESIDUAL_FIG_WIDTH = 7.4
RESIDUAL_ROW_HEIGHT = 2.2
TAIL_FIELD_FIGSIZE = (11.2, 7.7)
TAIL_RESIDUAL_FIGSIZE = (9.6, 7.8)


@dataclass(frozen=True)
class State:
    label: str
    fem_cycle: Optional[int]
    pidl_peak_step: int
    pidl_unload_step: int
    note: str


SELECTED_STATES: List[State] = [
    State("state0", None, 0, 0, "recovered zero-load state"),
    State("c1", 1, 4, 5, "early first-cycle state"),
    State("c20", 20, 99, 100, "early-middle state"),
    State("c40", 40, 199, 200, "middle state"),
    State("c69", 69, 344, 345, "legacy event-cycle reference"),
    State("c89", 89, 444, 445, "hard-recovery event-scale state"),
]

TAIL_STEPS: List[Tuple[str, int]] = [
    ("step444 c89 peak first hit", 444),
    ("step445 c89 unload", 445),
    ("step446 c90 substep 0.25", 446),
    ("step447 c90 substep 0.50 confirmed", 447),
]


def ensure_dirs() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)


def flat(a: np.ndarray) -> np.ndarray:
    return np.asarray(a).reshape(-1)


def finite(a: np.ndarray) -> np.ndarray:
    x = flat(np.asarray(a, dtype=float))
    return x[np.isfinite(x)]


def quad_area(verts: np.ndarray) -> np.ndarray:
    x = verts[:, :, 0]
    y = verts[:, :, 1]
    return 0.5 * np.abs(np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1))


def load_fem_mesh() -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mesh = meshio.read(FEM_MAIN / "fields_000001_008.vtk")
    points = np.asarray(mesh.points[:, :2], dtype=float)
    quads = None
    for block in mesh.cells:
        if block.type == "quad":
            quads = np.asarray(block.data, dtype=np.int64)
            break
    if quads is None:
        raise RuntimeError("No FEM quad cells found.")
    verts = points[quads]
    centers = verts.mean(axis=1)
    areas = quad_area(verts)
    return points, quads, verts, centers, areas


def load_fem_state0() -> Dict[str, np.ndarray]:
    with h5py.File(FEM_STATE0 / "state0_recovery.mat", "r") as h:
        return {
            "damage": flat(h["state0_d_elem"][()]),
            "history": flat(h["state0_alpha_bar_elem"][()]),
            "fatigue": flat(h["state0_f_alpha_elem"][()]),
            "driver": np.zeros_like(flat(h["state0_d_elem"][()]), dtype=float),
        }


def load_fem_cycle(cycle: int) -> Dict[str, np.ndarray]:
    d = sio.loadmat(FEM_MAIN / "psi_fields" / f"cycle_{cycle:04d}.mat", squeeze_me=True)
    return {
        "damage": flat(d["d_elem"]),
        "history": flat(d["alpha_bar_elem"]),
        "fatigue": flat(d["f_alpha_elem"]),
        "driver": flat(d["psi_elem"]),
    }


def load_fem_for_state(state: State, quantity: str) -> np.ndarray:
    if state.fem_cycle is None:
        return load_fem_state0()[quantity]
    return load_fem_cycle(state.fem_cycle)[quantity]


def load_pidl_step(step: int) -> Dict[str, np.ndarray]:
    z = np.load(PIDL_DIAG / f"element_fields_cycle_{step:04d}.npz")
    return {
        "x": flat(z["elem_x"]).astype(float),
        "y": flat(z["elem_y"]).astype(float),
        "area": flat(z["area_elem"]).astype(float),
        "damage": flat(z["alpha_elem"]).astype(float),
        "history": flat(z["hist_fat_elem"]).astype(float),
        "fatigue": flat(z["f_fatigue_elem"]).astype(float),
        "driver": flat(z["psi_active_elem"]).astype(float),
        "psi_raw": flat(z["psi_raw_elem"]).astype(float),
    }


def representative_pidl_geometry() -> Tuple[np.ndarray, np.ndarray]:
    z = np.load(PIDL_DIAG / "element_fields_cycle_0444.npz")
    xy = np.c_[flat(z["elem_x"]).astype(float), flat(z["elem_y"]).astype(float)]
    area = flat(z["area_elem"]).astype(float)
    return xy, area


def load_pidl_tri_mesh(reference_xy: np.ndarray, reference_area: np.ndarray) -> Tuple[np.ndarray, Dict[str, float]]:
    mesh = meshio.read(PIDL_FINE_MESH)
    triangles = None
    for block in mesh.cells:
        if block.type == "triangle":
            triangles = np.asarray(block.data, dtype=np.int64)
            break
    if triangles is None:
        raise RuntimeError(f"No PIDL triangles found in {PIDL_FINE_MESH}")

    points = np.asarray(mesh.points[:, :2], dtype=float)
    verts = points[triangles]
    centers = verts.mean(axis=1)
    areas = quad_area(verts)
    if len(verts) != len(reference_xy):
        raise RuntimeError(
            f"PIDL mesh/diagnostic element count mismatch: mesh={len(verts)} diagnostic={len(reference_xy)}"
        )

    geom_quality = {
        "pidl_mesh_path": str(PIDL_FINE_MESH),
        "pidl_mesh_n_triangles": int(len(verts)),
        "pidl_mesh_area_sum": float(np.sum(areas)),
        "pidl_diag_area_sum": float(np.sum(reference_area)),
        "pidl_centroid_max_abs_error": float(np.max(np.abs(centers - reference_xy))),
        "pidl_area_max_abs_error": float(np.max(np.abs(areas - reference_area))),
        "pidl_centroid_p99_abs_error": float(np.percentile(np.abs(centers - reference_xy), 99)),
        "pidl_area_p99_abs_error": float(np.percentile(np.abs(areas - reference_area), 99)),
    }
    return verts, geom_quality


def build_projection_map(verts: np.ndarray, centers: np.ndarray, pidl_xy: np.ndarray, pidl_area: np.ndarray) -> Dict[str, np.ndarray]:
    cache = DATA / "projection_map_centroid_area_fallback.npz"
    if cache.exists():
        loaded = dict(np.load(cache))
        return loaded

    tree = cKDTree(pidl_xy)
    dst_all: List[int] = []
    src_all: List[int] = []
    weight_all: List[float] = []
    fallback_src = np.empty(len(verts), dtype=np.int64)
    inside_count = np.zeros(len(verts), dtype=np.int32)
    inside_area = np.zeros(len(verts), dtype=float)

    for i, poly in enumerate(verts):
        lo = poly.min(axis=0) - 1e-10
        hi = poly.max(axis=0) + 1e-10
        radius = float(np.linalg.norm(hi - lo) / 2.0 + 0.003)
        cand = tree.query_ball_point(centers[i], radius)
        cand_arr = np.asarray(cand, dtype=np.int64)
        if cand_arr.size:
            in_bbox = (
                (pidl_xy[cand_arr, 0] >= lo[0])
                & (pidl_xy[cand_arr, 0] <= hi[0])
                & (pidl_xy[cand_arr, 1] >= lo[1])
                & (pidl_xy[cand_arr, 1] <= hi[1])
            )
            cand_arr = cand_arr[in_bbox]
        if cand_arr.size:
            inside = MplPath(poly).contains_points(pidl_xy[cand_arr], radius=1e-10)
            cand_arr = cand_arr[inside]

        if cand_arr.size:
            inside_count[i] = int(cand_arr.size)
            weights = pidl_area[cand_arr]
            inside_area[i] = float(np.sum(weights))
            dst_all.extend([i] * cand_arr.size)
            src_all.extend([int(v) for v in cand_arr])
            weight_all.extend([float(v) for v in weights])
            # fallback is still stored for completeness, but unused for this cell.
            fallback_src[i] = cand_arr[int(np.argmax(weights))]
        else:
            _dist, idx = tree.query(centers[i], k=1)
            fallback_src[i] = int(idx)

    out = {
        "dst": np.asarray(dst_all, dtype=np.int64),
        "src": np.asarray(src_all, dtype=np.int64),
        "weight": np.asarray(weight_all, dtype=float),
        "fallback_src": fallback_src,
        "inside_count": inside_count,
        "inside_area": inside_area,
    }
    np.savez(cache, **out)
    return out


def build_polygon_overlap_map(fem_verts: np.ndarray, fem_area: np.ndarray, pidl_verts: np.ndarray) -> Dict[str, np.ndarray]:
    cache = DATA / "projection_map_polygon_overlap.npz"
    if cache.exists():
        return dict(np.load(cache))

    pidl_polys = np.asarray([Polygon(v) for v in pidl_verts], dtype=object)
    tree = STRtree(pidl_polys)
    dst_all: List[int] = []
    src_all: List[int] = []
    weight_all: List[float] = []
    overlap_area = np.zeros(len(fem_verts), dtype=float)
    overlap_count = np.zeros(len(fem_verts), dtype=np.int32)

    for i, poly_verts in enumerate(fem_verts):
        poly = Polygon(poly_verts)
        if not poly.is_valid:
            poly = poly.buffer(0)
        cand_idx = np.asarray(tree.query(poly), dtype=np.int64)
        if cand_idx.size:
            for j in cand_idx:
                inter_area = float(poly.intersection(pidl_polys[int(j)]).area)
                if inter_area <= 1e-16:
                    continue
                dst_all.append(i)
                src_all.append(int(j))
                weight_all.append(inter_area)
                overlap_area[i] += inter_area
                overlap_count[i] += 1
        if (i + 1) % 10000 == 0:
            print(f"polygon overlap projection: {i + 1}/{len(fem_verts)} FEM cells")

    if np.any(overlap_count == 0):
        missing = int(np.sum(overlap_count == 0))
        raise RuntimeError(f"Polygon overlap projection left {missing} FEM cells without PIDL overlap.")

    out = {
        "dst": np.asarray(dst_all, dtype=np.int64),
        "src": np.asarray(src_all, dtype=np.int64),
        "weight": np.asarray(weight_all, dtype=float),
        "overlap_area": overlap_area,
        "overlap_count": overlap_count,
        "fem_area": np.asarray(fem_area, dtype=float),
    }
    np.savez(cache, **out)
    return out


def project_to_fem(values: np.ndarray, proj: Dict[str, np.ndarray], n_cells: int) -> np.ndarray:
    dst = proj["dst"]
    src = proj["src"]
    weight = proj["weight"]
    if "overlap_area" in proj:
        num = np.bincount(dst, weights=values[src] * weight, minlength=n_cells)
        den = np.bincount(dst, weights=weight, minlength=n_cells)
        out = np.full(n_cells, np.nan, dtype=float)
        ok = den > 0
        out[ok] = num[ok] / den[ok]
        return out

    inside_count = proj["inside_count"]
    fallback_src = proj["fallback_src"]
    out = np.empty(n_cells, dtype=float)
    has = inside_count > 0
    if dst.size:
        num = np.bincount(dst, weights=values[src] * weight, minlength=n_cells)
        den = np.bincount(dst, weights=weight, minlength=n_cells)
        out[has] = num[has] / den[has]
    out[~has] = values[fallback_src[~has]]
    return out


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    keys: List[str] = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def describe_projection(proj: Dict[str, np.ndarray], fem_area: np.ndarray) -> List[Dict[str, object]]:
    if "overlap_area" in proj:
        ratio = np.asarray(proj["overlap_area"], dtype=float) / np.asarray(fem_area, dtype=float)
        return [
            {
                "method": "polygon_overlap_area_weighted",
                "n_fem_cells": int(len(fem_area)),
                "n_projected_cells": int(np.sum(np.asarray(proj["overlap_count"]) > 0)),
                "n_overlap_pairs": int(len(proj["weight"])),
                "overlap_count_p50": float(np.percentile(proj["overlap_count"], 50)),
                "overlap_count_p90": float(np.percentile(proj["overlap_count"], 90)),
                "overlap_count_p99": float(np.percentile(proj["overlap_count"], 99)),
                "overlap_area_ratio_mean": float(np.mean(ratio)),
                "overlap_area_ratio_p01": float(np.percentile(ratio, 1)),
                "overlap_area_ratio_p50": float(np.percentile(ratio, 50)),
                "overlap_area_ratio_p99": float(np.percentile(ratio, 99)),
                "overlap_area_ratio_min": float(np.min(ratio)),
                "overlap_area_ratio_max": float(np.max(ratio)),
                "fem_area_mean": float(np.mean(fem_area)),
                "note": "PIDL triangle fields are area-averaged onto each FEM quadrilateral using polygon-overlap weights.",
            }
        ]

    inside = proj["inside_count"] > 0
    rows = [
        {
            "method": "centroid_in_fem_quad_area_weighted_then_nearest_fallback",
            "n_fem_cells": int(len(fem_area)),
            "n_inside_projected_cells": int(np.sum(inside)),
            "n_fallback_cells": int(np.sum(~inside)),
            "inside_projected_fraction": float(np.mean(inside)),
            "fallback_fraction": float(np.mean(~inside)),
            "inside_count_p50": float(np.percentile(proj["inside_count"][inside], 50)) if np.any(inside) else math.nan,
            "inside_count_p90": float(np.percentile(proj["inside_count"][inside], 90)) if np.any(inside) else math.nan,
            "inside_count_p99": float(np.percentile(proj["inside_count"][inside], 99)) if np.any(inside) else math.nan,
            "fem_area_mean": float(np.mean(fem_area)),
            "inside_pidl_area_mean": float(np.mean(proj["inside_area"][inside])) if np.any(inside) else math.nan,
            "note": "PIDL archive stores centroids/areas but no triangle connectivity; fallback cells use nearest PIDL centroid.",
        }
    ]
    return rows


def summarise_residual(quantity: str, state: str, fem: np.ndarray, pidl: np.ndarray, residual: np.ndarray, projection_note: str) -> Dict[str, object]:
    abs_res = np.abs(residual[np.isfinite(residual)])
    fem_f = finite(fem)
    pidl_f = finite(pidl)
    return {
        "quantity": quantity,
        "state": state,
        "projection_note": projection_note,
        "fem_mean": float(np.mean(fem_f)),
        "fem_p99": float(np.percentile(fem_f, 99)),
        "fem_max": float(np.max(fem_f)),
        "pidl_projected_mean": float(np.mean(pidl_f)),
        "pidl_projected_p99": float(np.percentile(pidl_f, 99)),
        "pidl_projected_max": float(np.max(pidl_f)),
        "residual_mean": float(np.mean(residual)),
        "residual_abs_mean": float(np.mean(abs_res)),
        "residual_abs_p99": float(np.percentile(abs_res, 99)),
        "residual_min": float(np.min(residual)),
        "residual_max": float(np.max(residual)),
    }


def make_collection(verts: np.ndarray, values: np.ndarray, cmap: str, norm) -> PolyCollection:
    coll = PolyCollection(
        verts,
        array=np.ma.masked_invalid(values),
        cmap=cmap,
        norm=norm,
        edgecolors="none",
        linewidths=0,
        rasterized=True,
    )
    return coll


def setup_cell_axis(ax) -> None:
    ax.set_aspect("equal")
    ax.set_xlim(-0.505, 0.505)
    ax.set_ylim(-0.505, 0.505)
    ax.set_xticks([])
    ax.set_yticks([])


def add_panel(ax, verts: np.ndarray, values: np.ndarray, cmap: str, norm, title: str) -> PolyCollection:
    coll = make_collection(verts, values, cmap, norm)
    ax.add_collection(coll)
    setup_cell_axis(ax)
    ax.set_title(title, fontsize=PANEL_TITLE_SIZE)
    return coll


def add_tail_panel(ax, verts: np.ndarray, values: np.ndarray, cmap: str, norm, title: str) -> PolyCollection:
    coll = make_collection(verts, values, cmap, norm)
    ax.add_collection(coll)
    setup_cell_axis(ax)
    ax.set_title(title, fontsize=TAIL_TITLE_SIZE)
    return coll


def tail_step_short(label: str) -> str:
    mapping = {
        "step444 c89 peak first hit": "step444\npeak\nfirst hit",
        "step445 c89 unload": "step445\nunload",
        "step446 c90 substep 0.25": "step446\nc90 0.25",
        "step447 c90 substep 0.50 confirmed": "step447\nc90 0.50\nconfirmed",
    }
    return mapping.get(label, label)


def robust_symmetric_norm(values: Sequence[np.ndarray], min_span: float = 1e-6, pct: float = 99.0) -> TwoSlopeNorm:
    all_abs = np.concatenate([np.abs(finite(v)) for v in values if finite(v).size])
    vmax = float(np.percentile(all_abs, pct)) if all_abs.size else min_span
    vmax = max(vmax, min_span)
    return TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)


def field_norm(quantity: str, fem_values: List[np.ndarray], pidl_values: List[np.ndarray]):
    if quantity in {"damage", "fatigue"}:
        return Normalize(vmin=0.0, vmax=1.0)
    if quantity == "history":
        vals = np.concatenate([finite(v) for v in fem_values + pidl_values if finite(v).size])
        vmax = max(float(np.percentile(vals, 99.5)), 1e-6) if vals.size else 1.0
        return Normalize(vmin=0.0, vmax=vmax)
    if quantity == "driver":
        positives = np.concatenate([finite(v)[finite(v) > 0] for v in fem_values + pidl_values if np.any(finite(v) > 0)])
        vmin = max(float(np.percentile(positives, 1.0)), 1e-9) if positives.size else 1e-9
        vmax = max(float(np.percentile(positives, 99.5)), vmin * 10.0) if positives.size else 1.0
        return LogNorm(vmin=vmin, vmax=vmax)
    raise ValueError(quantity)


def state_pidl_step_for_quantity(state: State, quantity: str) -> int:
    if state.label == "state0":
        return 0
    if quantity == "driver":
        return state.pidl_peak_step
    return state.pidl_unload_step


def selected_states_for_quantity(quantity: str) -> List[State]:
    if quantity == "driver":
        return [s for s in SELECTED_STATES if s.label != "state0"]
    return SELECTED_STATES


def plot_residual_figure(
    quantity: str,
    pretty: str,
    verts: np.ndarray,
    proj: Dict[str, np.ndarray],
    n_cells: int,
) -> Tuple[List[Path], List[Dict[str, object]]]:
    states = selected_states_for_quantity(quantity)
    fem_list: List[np.ndarray] = []
    pidl_list: List[np.ndarray] = []
    residual_list: List[np.ndarray] = []
    rows: List[Dict[str, object]] = []

    for st in states:
        fem = load_fem_for_state(st, quantity)
        pidl_raw = load_pidl_step(state_pidl_step_for_quantity(st, quantity))[quantity]
        pidl = project_to_fem(pidl_raw, proj, n_cells)
        if quantity == "driver":
            eps = 1e-10
            residual = np.log10(np.maximum(pidl, eps)) - np.log10(np.maximum(fem, eps))
            residual_name = "log10(PIDL/FEM)"
        else:
            residual = pidl - fem
            residual_name = "PIDL - FEM"
        fem_list.append(fem)
        pidl_list.append(pidl)
        residual_list.append(residual)
        rows.append(summarise_residual(quantity, st.label, fem, pidl, residual, residual_name))
        np.savez_compressed(DATA / f"projected_{quantity}_{st.label}.npz", fem=fem, pidl_projected=pidl, residual=residual)

    fnorm = field_norm(quantity, fem_list, pidl_list)
    rnorm = robust_symmetric_norm(residual_list, min_span=1e-5 if quantity != "driver" else 0.25, pct=99.0)
    fcmap = "magma" if quantity in {"driver", "fatigue"} else "viridis"
    rcmap = "RdBu_r"

    fig, axes = plt.subplots(
        len(states),
        3,
        figsize=(RESIDUAL_FIG_WIDTH, RESIDUAL_ROW_HEIGHT * len(states) + 0.9),
        constrained_layout=True,
    )
    if len(states) == 1:
        axes = np.asarray([axes])
    field_coll = None
    resid_coll = None
    for r, st in enumerate(states):
        field_coll = add_panel(axes[r, 0], verts, fem_list[r], fcmap, fnorm, f"{st.label}: FEM")
        add_panel(axes[r, 1], verts, pidl_list[r], fcmap, fnorm, f"{st.label}: PIDL -> FEM grid")
        resid_coll = add_panel(axes[r, 2], verts, residual_list[r], rcmap, rnorm, f"{st.label}: residual")
    if field_coll is not None:
        cb = fig.colorbar(field_coll, ax=axes[:, :2], fraction=0.018, pad=0.012)
        cb.ax.tick_params(labelsize=CBAR_TICK_SIZE)
        cb.set_label(pretty, fontsize=CBAR_LABEL_SIZE)
    if resid_coll is not None:
        cb = fig.colorbar(resid_coll, ax=axes[:, 2], fraction=0.03, pad=0.012)
        cb.ax.tick_params(labelsize=CBAR_TICK_SIZE)
        cb.set_label("log10(PIDL/FEM)" if quantity == "driver" else "PIDL - FEM", fontsize=CBAR_LABEL_SIZE)
    fig.suptitle(f"FEM-grid projected residuals: {pretty}", fontsize=SUPTITLE_SIZE)
    stem = f"projected_residual_{quantity}_selected_states"
    png = FIG / f"{stem}.png"
    pdf = FIG / f"{stem}.pdf"
    fig.savefig(png, dpi=300)
    fig.savefig(pdf)
    plt.close(fig)
    return [png, pdf], rows


def plot_tail_dense(verts: np.ndarray, proj: Dict[str, np.ndarray], n_cells: int) -> Tuple[List[Path], List[Dict[str, object]]]:
    fem_ref = load_fem_cycle(89)
    quantities = [
        ("damage", "damage alpha", Normalize(0.0, 1.0), "viridis"),
        ("history", "fatigue history", None, "viridis"),
        ("fatigue", "fatigue degradation f", Normalize(0.0, 1.0), "magma"),
    ]

    pidl_projected: Dict[Tuple[str, int], np.ndarray] = {}
    residuals: Dict[Tuple[str, int], np.ndarray] = {}
    rows: List[Dict[str, object]] = []
    for quantity, _pretty, _norm, _cmap in quantities:
        for label, step in TAIL_STEPS:
            pidl = project_to_fem(load_pidl_step(step)[quantity], proj, n_cells)
            pidl_projected[(quantity, step)] = pidl
            res = pidl - fem_ref[quantity]
            residuals[(quantity, step)] = res
            rows.append(summarise_residual(quantity, f"{label} vs FEM c89", fem_ref[quantity], pidl, res, "PIDL tail step - FEM c89"))
        np.savez_compressed(
            DATA / f"tail_dense_{quantity}_vs_fem_c89.npz",
            fem_c89=fem_ref[quantity],
            **{f"pidl_{step}": pidl_projected[(quantity, step)] for _label, step in TAIL_STEPS},
            **{f"residual_{step}": residuals[(quantity, step)] for _label, step in TAIL_STEPS},
        )

    # Field figure: FEM c89 plus PIDL 444-447, rows are quantities.
    fig, axes = plt.subplots(3, 5, figsize=TAIL_FIELD_FIGSIZE, constrained_layout=True)
    field_col_titles = ["FEM c89"] + [tail_step_short(label) for label, _step in TAIL_STEPS]
    field_row_titles = {
        "damage": "damage\nalpha",
        "history": "fatigue\nhistory",
        "fatigue": "fatigue\ndegradation f",
    }
    for r, (quantity, pretty, norm, cmap) in enumerate(quantities):
        if norm is None:
            vals = [fem_ref[quantity]] + [pidl_projected[(quantity, step)] for _label, step in TAIL_STEPS]
            vmax = max(float(np.percentile(finite(v), 99.5)) for v in vals if finite(v).size)
            norm = Normalize(0.0, max(vmax, 1e-6))
        coll = add_tail_panel(axes[r, 0], verts, fem_ref[quantity], cmap, norm, field_col_titles[0] if r == 0 else "")
        axes[r, 0].set_ylabel(
            field_row_titles[quantity],
            fontsize=TAIL_ROW_LABEL_SIZE,
            rotation=0,
            ha="right",
            va="center",
            labelpad=24,
        )
        for c, (label, step) in enumerate(TAIL_STEPS, start=1):
            add_tail_panel(
                axes[r, c],
                verts,
                pidl_projected[(quantity, step)],
                cmap,
                norm,
                field_col_titles[c] if r == 0 else "",
            )
        cb = fig.colorbar(coll, ax=axes[r, :], fraction=0.012, pad=0.006)
        cb.ax.tick_params(labelsize=CBAR_TICK_SIZE)
        cb.set_label(pretty, fontsize=CBAR_LABEL_SIZE)
    fig.suptitle("Projected tail dense fields on the FEM grid", fontsize=SUPTITLE_SIZE)
    png_field = FIG / "tail_dense_projected_fields_vs_fem_c89.png"
    pdf_field = FIG / "tail_dense_projected_fields_vs_fem_c89.pdf"
    fig.savefig(png_field, dpi=300)
    fig.savefig(pdf_field)
    plt.close(fig)

    # Residual figure: PIDL steps 444-447 minus FEM c89.
    fig, axes = plt.subplots(len(TAIL_STATES := TAIL_STEPS), 3, figsize=TAIL_RESIDUAL_FIGSIZE, constrained_layout=True)
    residual_col_titles = ["damage alpha\nresidual", "fatigue history\nresidual", "fatigue degradation f\nresidual"]
    q_res_norms = {
        quantity: robust_symmetric_norm([residuals[(quantity, step)] for _label, step in TAIL_STEPS], min_span=1e-5, pct=99)
        for quantity, _pretty, _norm, _cmap in quantities
    }
    for r, (label, step) in enumerate(TAIL_STEPS):
        for c, (quantity, pretty, _norm, _cmap) in enumerate(quantities):
            coll = add_tail_panel(
                axes[r, c],
                verts,
                residuals[(quantity, step)],
                "RdBu_r",
                q_res_norms[quantity],
                residual_col_titles[c] if r == 0 else "",
            )
        axes[r, 0].set_ylabel(
            tail_step_short(label),
            fontsize=TAIL_ROW_LABEL_SIZE,
            rotation=0,
            ha="right",
            va="center",
            labelpad=16,
        )
    for c, (quantity, pretty, _norm, _cmap) in enumerate(quantities):
        sm = plt.cm.ScalarMappable(norm=q_res_norms[quantity], cmap="RdBu_r")
        sm.set_array([])
        cb = fig.colorbar(sm, ax=axes[:, c], fraction=0.018, pad=0.008)
        cb.ax.tick_params(labelsize=CBAR_TICK_SIZE)
        cb.set_label(f"{pretty}: PIDL - FEM c89", fontsize=CBAR_LABEL_SIZE)
    fig.suptitle("Tail dense residuals relative to FEM c89", fontsize=SUPTITLE_SIZE)
    png_res = FIG / "tail_dense_projected_residuals_vs_fem_c89.png"
    pdf_res = FIG / "tail_dense_projected_residuals_vs_fem_c89.pdf"
    fig.savefig(png_res, dpi=300)
    fig.savefig(pdf_res)
    plt.close(fig)

    return [png_field, pdf_field, png_res, pdf_res], rows


def write_readme(figures: List[Path], projection_rows: List[Dict[str, object]]) -> None:
    p = OUT / "README_projected_residuals.md"
    quality = projection_rows[0]
    if quality["method"] == "polygon_overlap_area_weighted":
        projection_text = f"""PIDL element values are projected to the FEM quadrilateral grid using true
polygon-overlap area averaging between the PIDL triangular mesh and FEM quad
cells. The PIDL mesh is verified against the run diagnostic centroid/area export
before projection.

Projection coverage:

- FEM cells: `{quality['n_fem_cells']}`
- projected FEM cells: `{quality['n_projected_cells']}`
- overlap pairs: `{quality['n_overlap_pairs']}`
- overlap area ratio median: `{quality['overlap_area_ratio_p50']:.6f}`
- overlap area ratio 1st/99th percentiles: `{quality['overlap_area_ratio_p01']:.6f}` / `{quality['overlap_area_ratio_p99']:.6f}`
"""
        caption_caveat = (
            'Use the phrase "FEM-grid projection by polygon-overlap area averaging" '
            "in captions. The PIDL mesh source and centroid/area verification are recorded "
            "in `tables/projection_quality.csv`."
        )
    else:
        projection_text = f"""PIDL element values are projected to the FEM quadrilateral grid using
element-area weighted centroid-in-cell averaging. FEM cells with no PIDL
centroid inside use nearest PIDL centroid fallback.

This archive does not contain PIDL triangle connectivity, so these panels are
not exact polygon-overlap area averages. The projection coverage is:

- FEM cells: `{quality['n_fem_cells']}`
- centroid-in-cell projected cells: `{quality['n_inside_projected_cells']}`
- nearest fallback cells: `{quality['n_fallback_cells']}`
- fallback fraction: `{quality['fallback_fraction']:.3f}`
"""
        caption_caveat = (
            'Use the phrase "FEM-grid projected by area-weighted centroid-in-cell averaging '
            'with nearest fallback" unless exact PIDL triangle connectivity is recovered and '
            "the figures are regenerated with true polygon-overlap averaging."
        )
    text = f"""# FEM-grid projected residual panels

Created: 2026-07-01

## Figure purpose

Claim: the hard-recovery PIDL run is close to the FEM SENS recovery case in
event scale, but the field mechanism still differs. These panels compare fields
on one FEM cell grid instead of using separate FEM/PIDL centroid scatter plots.

## Data sources

- FEM reference: `{FEM_MAIN}`
- FEM state0 companion: `{FEM_STATE0}`
- PIDL diagnostics: `{PIDL_DIAG}`
- PIDL triangle mesh: `{PIDL_FINE_MESH}`

## Projection method

{projection_text}

## Outputs

"""
    for fig in figures:
        text += f"- `{fig}`\n"
    text += f"""
## Tables

- `tables/projection_quality.csv`: projection coverage and overlap-quality checks.
- `tables/projected_residual_summary.csv`: FEM, projected-PIDL and residual scalar reductions.
- `tables/tail_dense_projected_residual_summary.csv`: tail-window residual reductions.

## Caption note

{caption_caveat}
"""
    p.write_text(text)


def main() -> None:
    ensure_dirs()
    _points, _quads, verts, centers, fem_areas = load_fem_mesh()
    pidl_xy, pidl_area = representative_pidl_geometry()
    pidl_verts, pidl_geom_quality = load_pidl_tri_mesh(pidl_xy, pidl_area)
    proj = build_polygon_overlap_map(verts, fem_areas, pidl_verts)

    projection_rows = describe_projection(proj, fem_areas)
    projection_rows[0].update(pidl_geom_quality)
    write_csv(TAB / "projection_quality.csv", projection_rows)

    all_figs: List[Path] = []
    summary_rows: List[Dict[str, object]] = []
    specs = [
        ("damage", "damage / alpha"),
        ("history", "fatigue history"),
        ("fatigue", "fatigue degradation f"),
        ("driver", "active driver / psi field"),
    ]
    for quantity, pretty in specs:
        figs, rows = plot_residual_figure(quantity, pretty, verts, proj, len(fem_areas))
        all_figs.extend(figs)
        summary_rows.extend(rows)
    write_csv(TAB / "projected_residual_summary.csv", summary_rows)

    figs, tail_rows = plot_tail_dense(verts, proj, len(fem_areas))
    all_figs.extend(figs)
    write_csv(TAB / "tail_dense_projected_residual_summary.csv", tail_rows)

    write_readme(all_figs, projection_rows)
    manifest = {
        "output_root": str(OUT),
        "figures": [str(p) for p in all_figs],
        "tables": [
            str(TAB / "projection_quality.csv"),
            str(TAB / "projected_residual_summary.csv"),
            str(TAB / "tail_dense_projected_residual_summary.csv"),
        ],
        "projection": projection_rows[0],
    }
    (OUT / "analysis_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
