#!/usr/bin/env python3
"""Plot FEM/PIDL residual fields on a shared probe grid.

The script is intentionally conservative: it only subtracts matched physical
fields, and uses log residuals for fields whose dynamic range is dominated by
local peaks.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import griddata


FIELD_MAP = {
    "damage": ("d_elem", "alpha_elem", "raw"),
    "hist": ("alpha_bar_elem", "hist_fat_elem", "log1p"),
    "f": ("f_fatigue_elem", "f_fatigue_elem", "logratio"),
    "psi": ("psi_plus_elem", "psi_plus_elem", "logratio"),
}


def _read_ref(file_handle: h5py.File, dataset: h5py.Dataset, index: int) -> np.ndarray:
    ref = np.asarray(dataset).ravel()[index]
    return np.asarray(file_handle[ref]).reshape(-1)


def load_fem_fields(mat_path: Path) -> dict[int, dict[str, np.ndarray]]:
    fields: dict[int, dict[str, np.ndarray]] = {}
    with h5py.File(mat_path, "r") as handle:
        cycles = [int(_read_ref(handle, handle["cycles/cycle"], i)[0]) for i in range(handle["cycles/cycle"].size)]
        centroids = np.asarray(handle["element_centroids"]).T
        for i, cycle in enumerate(cycles):
            fields[cycle] = {
                "x": centroids[:, 0],
                "y": centroids[:, 1],
            }
            for fem_key, _, _ in FIELD_MAP.values():
                fields[cycle][fem_key] = _read_ref(handle, handle[f"cycles/{fem_key}"], i)
    return fields


def load_pidl_field(npz_path: Path) -> dict[str, np.ndarray]:
    with np.load(npz_path) as data:
        return {key: np.asarray(data[key]).reshape(-1) for key in data.files}


def common_grid(fem: dict[str, np.ndarray], pidl: dict[str, np.ndarray], n_grid: int):
    xmin = max(float(np.nanmin(fem["x"])), float(np.nanmin(pidl["elem_x"])))
    xmax = min(float(np.nanmax(fem["x"])), float(np.nanmax(pidl["elem_x"])))
    ymin = max(float(np.nanmin(fem["y"])), float(np.nanmin(pidl["elem_y"])))
    ymax = min(float(np.nanmax(fem["y"])), float(np.nanmax(pidl["elem_y"])))
    gx = np.linspace(xmin, xmax, n_grid)
    gy = np.linspace(ymin, ymax, n_grid)
    return np.meshgrid(gx, gy)


def interp_to_grid(x: np.ndarray, y: np.ndarray, values: np.ndarray, grid_x: np.ndarray,
                   grid_y: np.ndarray) -> np.ndarray:
    points = np.column_stack([x, y])
    return griddata(points, values, (grid_x, grid_y), method="linear")


def residual_field(pidl_grid: np.ndarray, fem_grid: np.ndarray, mode: str, eps: float) -> np.ndarray:
    if mode == "raw":
        return pidl_grid - fem_grid
    if mode == "log1p":
        return np.log10(1.0 + np.maximum(pidl_grid, 0.0)) - np.log10(1.0 + np.maximum(fem_grid, 0.0))
    if mode == "logratio":
        return np.log10((np.maximum(pidl_grid, 0.0) + eps) / (np.maximum(fem_grid, 0.0) + eps))
    raise ValueError(f"Unknown residual mode: {mode}")


def robust_limits(*arrays: np.ndarray, q: float = 99.5) -> tuple[float, float]:
    values = np.concatenate([a[np.isfinite(a)].reshape(-1) for a in arrays])
    if values.size == 0:
        return 0.0, 1.0
    lo, hi = np.nanpercentile(values, [100 - q, q])
    if np.isclose(lo, hi):
        hi = lo + 1.0
    return float(lo), float(hi)


def signed_limit(values: np.ndarray, q: float = 99.0) -> float:
    finite = np.abs(values[np.isfinite(values)])
    if finite.size == 0:
        return 1.0
    lim = float(np.nanpercentile(finite, q))
    return max(lim, 1e-12)


def plot_residuals(fem_mat: Path, pidl_dir: Path, cycles: list[int], out_png: Path,
                   out_pdf: Path | None, out_csv: Path, n_grid: int) -> None:
    fem_fields = load_fem_fields(fem_mat)
    rows = []
    n_rows = len(cycles) * len(FIELD_MAP)
    fig, axes = plt.subplots(n_rows, 3, figsize=(10.5, 2.1 * n_rows), constrained_layout=True)
    if n_rows == 1:
        axes = np.asarray([axes])

    row_i = 0
    for cycle in cycles:
        if cycle not in fem_fields:
            raise KeyError(f"FEM cycle {cycle} is not available in {fem_mat}")
        pidl = load_pidl_field(pidl_dir / f"element_fields_cycle_{cycle:04d}.npz")
        fem = fem_fields[cycle]
        grid_x, grid_y = common_grid(fem, pidl, n_grid)
        for label, (fem_key, pidl_key, mode) in FIELD_MAP.items():
            fem_grid = interp_to_grid(fem["x"], fem["y"], fem[fem_key], grid_x, grid_y)
            pidl_grid = interp_to_grid(pidl["elem_x"], pidl["elem_y"], pidl[pidl_key], grid_x, grid_y)
            res = residual_field(pidl_grid, fem_grid, mode, eps=1e-12)
            vmin, vmax = robust_limits(fem_grid, pidl_grid)
            rlim = signed_limit(res)

            for ax in axes[row_i]:
                ax.set_aspect("equal")
                ax.set_xticks([])
                ax.set_yticks([])

            im0 = axes[row_i, 0].imshow(fem_grid, extent=[grid_x.min(), grid_x.max(), grid_y.min(), grid_y.max()],
                                         origin="lower", cmap="viridis", vmin=vmin, vmax=vmax)
            im1 = axes[row_i, 1].imshow(pidl_grid, extent=[grid_x.min(), grid_x.max(), grid_y.min(), grid_y.max()],
                                         origin="lower", cmap="viridis", vmin=vmin, vmax=vmax)
            im2 = axes[row_i, 2].imshow(res, extent=[grid_x.min(), grid_x.max(), grid_y.min(), grid_y.max()],
                                         origin="lower", cmap="RdBu_r", vmin=-rlim, vmax=rlim)
            axes[row_i, 0].set_title(f"FEM c{cycle} {label}")
            axes[row_i, 1].set_title(f"PIDL c{cycle} {label}")
            axes[row_i, 2].set_title(f"Residual c{cycle} {label}")
            fig.colorbar(im0, ax=axes[row_i, 0], fraction=0.046, pad=0.02)
            fig.colorbar(im1, ax=axes[row_i, 1], fraction=0.046, pad=0.02)
            fig.colorbar(im2, ax=axes[row_i, 2], fraction=0.046, pad=0.02)

            finite = res[np.isfinite(res)]
            rows.append({
                "cycle": cycle,
                "field": label,
                "residual_mode": mode,
                "res_mean": float(np.nanmean(finite)),
                "res_abs_p99": float(np.nanpercentile(np.abs(finite), 99)),
                "res_abs_p999": float(np.nanpercentile(np.abs(finite), 99.9)),
            })
            row_i += 1

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    if out_pdf is not None:
        fig.savefig(out_pdf)
    plt.close(fig)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fem-mat", type=Path, required=True)
    parser.add_argument("--pidl-dir", type=Path, required=True)
    parser.add_argument("--cycles", default="40,70")
    parser.add_argument("--out-png", type=Path, required=True)
    parser.add_argument("--out-pdf", type=Path, default=None)
    parser.add_argument("--out-csv", type=Path, required=True)
    parser.add_argument("--n-grid", type=int, default=260)
    args = parser.parse_args()

    cycles = [int(item.strip()) for item in args.cycles.split(",") if item.strip()]
    plot_residuals(args.fem_mat, args.pidl_dir, cycles, args.out_png, args.out_pdf, args.out_csv, args.n_grid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
