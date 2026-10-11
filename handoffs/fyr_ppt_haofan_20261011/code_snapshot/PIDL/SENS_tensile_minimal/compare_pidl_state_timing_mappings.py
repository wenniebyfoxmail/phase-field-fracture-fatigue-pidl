#!/usr/bin/env python3
"""Compare FEM c1 timing state against PIDL saved j=0/j=1 states.

FEM Request 20 proved that the old FEM c1 export is a mixed timing object:
damage/history/f are unloaded post-history-refresh fields, while psi is the
peak-to-date driver.  This script recreates that FEM c1 object from the state
timing handoff, projects it to PIDL probes, and compares it with two possible
PIDL mappings:

    FEM c1 -> PIDL saved j=0
    FEM c1 -> PIDL saved j=1

The PIDL states are post-hoc saved checkpoint states, i.e. post history refresh.
They are not clean pre-refresh states; the output labels keep that caveat.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from posthoc_mesh_probe_alignment import (  # noqa: E402
    build_assignment,
    load_combined_handoff,
    metrics,
    pidl_model_and_mesh,
    project_to_pidl,
)

DEFAULT_ARCHIVE = (
    HERE
    / "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
    "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
    "N100_R0.0_Umax0.12_femmesh_softHist0"
)
DEFAULT_FEM_STATE = (
    Path.home()
    / "Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result"
    / "_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_state_timing_2026-05-29"
)
DEFAULT_OUT_DIR = HERE.parent / "_analysis_fem_mechanism_20260528"

FIELDS = {
    "damage_alpha": {"label": "damage", "cmap": "viridis"},
    "alpha_bar": {"label": "fatigue history", "cmap": "magma"},
    "fatigue_f": {"label": "fatigue factor", "cmap": "viridis"},
    "psi_plus_active": {"label": "active tensile driver", "cmap": "magma"},
}
PIDL_FIELD_KEY = {
    "damage_alpha": "alpha",
    "alpha_bar": "alpha_bar",
    "fatigue_f": "f",
    "psi_plus_active": "psi_plus_active",
}


def find_state_index(df: pd.DataFrame, label: str) -> int:
    idx = df.index[df["state_label"].astype(str) == label]
    if len(idx) != 1:
        raise KeyError(f"Expected one FEM state label {label!r}, found {len(idx)}")
    return int(idx[0])


def load_fem_c1_mixed_state(fem_dir: Path) -> dict[str, np.ndarray]:
    df = pd.read_csv(fem_dir / "state_timing_metrics.csv")
    idx = find_state_index(df, "cycle1_unloaded_post_history_refresh")
    mat = fem_dir / "state_timing_element_fields.mat"
    with h5py.File(mat, "r") as f:
        centroids = np.asarray(f["element_centroids"], dtype=float).T
        centroids[:, :2] -= 0.5
        areas = np.asarray(f["element_area"], dtype=float).reshape(-1)
        d = np.asarray(f["d_elem"], dtype=float)[idx]
        alpha_bar = np.asarray(f["alpha_bar_elem"], dtype=float)[idx]
        fatigue_f = np.asarray(f["f_fatigue_elem"], dtype=float)[idx]
        psi_peak = np.asarray(f["psi_plus_peak_to_date_elem"], dtype=float)[idx]
    psi_active = ((1.0 - d) ** 2 + 1e-6) * psi_peak
    return {
        "centroids": centroids,
        "areas": areas,
        "damage_alpha": d,
        "alpha_bar": alpha_bar,
        "fatigue_f": fatigue_f,
        "psi_plus_active": psi_active,
    }


def safe_ratio(num: float, den: float) -> float:
    if not np.isfinite(den) or abs(den) <= 1e-30:
        return float("nan")
    return float(num / den)


def robust_limits(*arrays: np.ndarray, q: float = 99.5) -> tuple[float, float]:
    vals = np.concatenate([np.asarray(a)[np.isfinite(a)].reshape(-1) for a in arrays])
    if vals.size == 0:
        return 0.0, 1.0
    lo, hi = np.nanpercentile(vals, [100.0 - q, q])
    if np.isclose(lo, hi):
        hi = lo + 1.0
    return float(lo), float(hi)


def signed_limit(values: np.ndarray, q: float = 99.0) -> float:
    vals = np.abs(values[np.isfinite(values)])
    if vals.size == 0:
        return 1.0
    return max(float(np.nanpercentile(vals, q)), 1e-12)


def fill_nan_from_nearest(values: np.ndarray, centroids: np.ndarray) -> np.ndarray:
    """Fill projection gaps for plotting only."""
    out = np.asarray(values, dtype=float).copy()
    valid = np.isfinite(out)
    if valid.all() or not valid.any():
        return out
    tree = cKDTree(centroids[valid])
    _, idx = tree.query(centroids[~valid], k=1)
    out[~valid] = out[valid][idx]
    return out


def save_npz(
    out_path: Path,
    fem_projected: dict[str, np.ndarray],
    pidl_states: dict[int, dict[str, np.ndarray]],
    centroids: np.ndarray,
    areas: np.ndarray,
) -> None:
    payload = {
        "element_centroids": centroids.astype(np.float32),
        "element_area": areas.astype(np.float32),
    }
    for field, values in fem_projected.items():
        payload[f"fem_c1_mixed_{field}"] = values.astype(np.float32)
    for j, state in pidl_states.items():
        for field in FIELDS:
            payload[f"pidl_saved_j{j}_{field}"] = state[PIDL_FIELD_KEY[field]].astype(np.float32)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_path, **payload)


def plot_mapping(
    out_path: Path,
    triang: mtri.Triangulation,
    centroids: np.ndarray,
    fem_projected: dict[str, np.ndarray],
    pidl_states: dict[int, dict[str, np.ndarray]],
) -> None:
    rows = []
    for j, state in pidl_states.items():
        for field in ["damage_alpha", "alpha_bar", "psi_plus_active"]:
            rows.append((j, field, fill_nan_from_nearest(fem_projected[field], centroids), state[PIDL_FIELD_KEY[field]]))
    fig, axes = plt.subplots(len(rows), 3, figsize=(10.8, 2.35 * len(rows)), constrained_layout=True)
    for ax_row, (j, field, fem, pidl) in zip(axes, rows):
        residual = pidl - fem
        lo, hi = robust_limits(fem, pidl)
        rlim = signed_limit(residual)
        spec = FIELDS[field]
        panels = [
            (f"FEM c1 mixed {spec['label']}", fem, spec["cmap"], None, lo, hi),
            (f"PIDL saved j={j}", pidl, spec["cmap"], None, lo, hi),
            (f"PIDL j={j} - FEM", residual, "RdBu_r", TwoSlopeNorm(vmin=-rlim, vcenter=0.0, vmax=rlim), None, None),
        ]
        for ax, (title, values, cmap, norm, vmin, vmax) in zip(ax_row, panels):
            im = ax.tripcolor(triang, facecolors=values, shading="flat", cmap=cmap, norm=norm, vmin=vmin, vmax=vmax)
            ax.set_title(title, fontsize=8.5)
            ax.set_aspect("equal")
            ax.set_xlim(-0.52, 0.52)
            ax.set_ylim(-0.52, 0.52)
            ax.set_xticks([])
            ax.set_yticks([])
            fig.colorbar(im, ax=ax, fraction=0.042, pad=0.012)
    fig.suptitle("PIDL FEM-mesh saved-state timing mappings against FEM c1", fontsize=12)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--fem-state-dir", type=Path, default=DEFAULT_FEM_STATE)
    parser.add_argument("--cycles", default="0,1")
    parser.add_argument("--umax", type=float, default=0.12)
    parser.add_argument("--pidl-mesh", type=Path, default=HERE / "meshed_geom_fem_soft_hist0.msh")
    parser.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_DIR / "pidl_femmesh_state_timing_mapping_j0_j1.csv")
    parser.add_argument("--out-npz", type=Path, default=DEFAULT_OUT_DIR / "pidl_femmesh_state_timing_fields_j0_j1.npz")
    parser.add_argument("--out-fig", type=Path, default=DEFAULT_OUT_DIR / "figures" / "pidl_femmesh_state_timing_mapping_j0_j1.png")
    args = parser.parse_args()

    cycles = [int(x) for x in args.cycles.split(",") if x.strip()]
    fem = load_fem_c1_mixed_state(args.fem_state_dir)
    first = pidl_model_and_mesh(args.archive, args.umax, cycles[0], str(args.pidl_mesh))
    assignment = build_assignment(fem["centroids"], first["centroids"], first["inp"], first["conn"])
    triang = mtri.Triangulation(first["inp"][:, 0], first["inp"][:, 1], first["conn"])

    fem_projected = {
        field: project_to_pidl(fem[field], fem["areas"], assignment, len(first["areas"]))
        for field in FIELDS
    }
    pidl_states = {
        j: (first if j == cycles[0] else pidl_model_and_mesh(args.archive, args.umax, j, str(args.pidl_mesh)))
        for j in cycles
    }

    rows = []
    for j, pidl in pidl_states.items():
        for field in FIELDS:
            fem_metrics = metrics(fem_projected[field], pidl["areas"], pidl["centroids"])
            pidl_native = pidl[PIDL_FIELD_KEY[field]]
            pidl_metrics = metrics(pidl_native, pidl["areas"], pidl["centroids"])
            for metric_name in sorted(fem_metrics):
                fv = fem_metrics[metric_name]
                pv = pidl_metrics[metric_name]
                rows.append(
                    {
                        "mapping": f"FEM_c1_mixed_to_PIDL_saved_j{j}",
                        "pidl_saved_index": j,
                        "field": field,
                        "metric": metric_name,
                        "FEM_projected_to_PIDL": fv,
                        "PIDL_native": pv,
                        "PIDL_over_FEM_projected": safe_ratio(pv, fv),
                        "PIDL_minus_FEM": pv - fv,
                    }
                )
    df = pd.DataFrame(rows)
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out_csv, index=False)
    save_npz(args.out_npz, fem_projected, pidl_states, first["centroids"], first["areas"])
    plot_mapping(args.out_fig, triang, first["centroids"], fem_projected, pidl_states)

    keep = df[df["metric"].isin(["max", "p99", "tip_2l0_mean", "domain_mean"])]
    print(keep.to_string(index=False))
    print(f"Wrote {args.out_csv}")
    print(f"Wrote {args.out_npz}")
    print(f"Wrote {args.out_fig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
