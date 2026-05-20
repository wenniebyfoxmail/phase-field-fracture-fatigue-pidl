#!/usr/bin/env python3
"""Post-hoc FEM/PIDL fracture-criterion alignment audit.

This script does not train. It reads a PIDL archive and FEM handoff files, then
computes native and crossed boundary-damage criteria:

  - PIDL native: right-boundary count with alpha > 0.95.
  - FEM-style on PIDL: any external-boundary alpha > 0.95, excluding the
    initial notch mouth on the left edge.
  - PIDL-style on FEM snapshots: right-boundary-layer count with d > 0.95.
  - FEM-style on FEM snapshots: external-boundary-layer d > 0.95, excluding
    the initial notch mouth.

The goal is to separate a real field mismatch from a detector mismatch.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.io as sio
import torch

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from validate_pidl_archive import _rebuild_field_comp  # local post-hoc helper


DEFAULT_PIDL = (
    HERE
    / "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12"
)
DEFAULT_FEM_DIR = Path("/Users/wenxiaofang/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent")
DEFAULT_FEM_CSV = Path("/Users/wenxiaofang/Downloads/_pidl_handoff_v2/post_process/SENT_PIDL_12_timeseries.csv")


def _cycles_from_archive(archive: Path) -> list[int]:
    cycles: list[int] = []
    for p in sorted((archive / "best_models").glob("trained_1NN_*.pt")):
        m = re.search(r"trained_1NN_(\d+)\.pt$", p.name)
        if m:
            cycles.append(int(m.group(1)))
    return cycles


def _external_boundary_mask(xy: np.ndarray, tol: float, notch_half_width: float) -> np.ndarray:
    x, y = xy[:, 0], xy[:, 1]
    xmin, xmax = float(x.min()), float(x.max())
    ymin, ymax = float(y.min()), float(y.max())
    ext = (
        np.isclose(x, xmin, atol=tol)
        | np.isclose(x, xmax, atol=tol)
        | np.isclose(y, ymin, atol=tol)
        | np.isclose(y, ymax, atol=tol)
    )
    initial_notch_mouth = np.isclose(x, xmin, atol=tol) & (np.abs(y) <= notch_half_width)
    return ext & ~initial_notch_mouth


def _right_boundary_mask(xy: np.ndarray, x_min: float) -> np.ndarray:
    return xy[:, 0] >= x_min


def _first_cycle(rows: list[dict], key: str, threshold: float | int) -> int | None:
    for row in rows:
        value = row.get(key)
        if value is not None and value >= threshold:
            return int(row["cycle"])
    return None


def audit_pidl(archive: Path, threshold: float, nmin: int, cycles: list[int] | None) -> list[dict]:
    all_cycles = _cycles_from_archive(archive)
    if cycles is not None:
        wanted = set(cycles)
        all_cycles = [c for c in all_cycles if c in wanted]
    if not all_cycles:
        raise FileNotFoundError(f"No trained_1NN_<cycle>.pt files found in {archive / 'best_models'}")

    rows: list[dict] = []
    for cyc in all_cycles:
        rebuilt = _rebuild_field_comp(archive, cyc)
        field_comp = rebuilt["field_comp"]
        inp = rebuilt["inp"]
        with torch.no_grad():
            _, _, alpha = field_comp.fieldCalculation(inp)
        xy = inp.detach().cpu().numpy()
        a = alpha.detach().cpu().numpy().reshape(-1)

        bdy = _external_boundary_mask(xy, tol=1e-6, notch_half_width=0.02)
        right = _right_boundary_mask(xy, x_min=0.48)
        rows.append(
            {
                "method": "PIDL",
                "cycle": cyc,
                "native_right_count_gt095": int((a[right] > threshold).sum()),
                "native_right_max": float(a[right].max()) if right.any() else np.nan,
                "femstyle_external_count_gt095": int((a[bdy] > threshold).sum()),
                "femstyle_external_max": float(a[bdy].max()) if bdy.any() else np.nan,
                "n_right_probe": int(right.sum()),
                "n_external_probe": int(bdy.sum()),
                "source": rebuilt["nn_file"],
            }
        )
    return rows


def _load_fem_snapshot(path: Path) -> tuple[np.ndarray, np.ndarray]:
    data = sio.loadmat(path)
    for key in ("d_elem", "alpha_elem", "alpha_e", "alpha", "phi_elem"):
        if key in data:
            d = np.asarray(data[key]).reshape(-1)
            break
    else:
        raise KeyError(f"No damage key found in {path}; keys={sorted(k for k in data if not k.startswith('__'))}")
    return d, data


def audit_fem(fem_dir: Path, threshold: float, layer_tol: float) -> list[dict]:
    mesh = sio.loadmat(fem_dir / "mesh_geometry.mat")
    centroids = np.asarray(mesh["element_centroids"], dtype=float)
    x = centroids[:, 0]
    y = centroids[:, 1]
    xmin, xmax = float(x.min()), float(x.max())
    ymin, ymax = float(y.min()), float(y.max())
    ext = (
        (x <= xmin + layer_tol)
        | (x >= xmax - layer_tol)
        | (y <= ymin + layer_tol)
        | (y >= ymax - layer_tol)
    )
    initial_notch_mouth = (x <= xmin + layer_tol) & (np.abs(y) <= 0.02)
    ext = ext & ~initial_notch_mouth
    right = x >= xmax - layer_tol

    rows: list[dict] = []
    for path in sorted(fem_dir.glob("u12_cycle_*.mat")):
        m = re.search(r"cycle_(\d+)\.mat$", path.name)
        if not m:
            continue
        cyc = int(m.group(1))
        d, _ = _load_fem_snapshot(path)
        rows.append(
            {
                "method": "FEM",
                "cycle": cyc,
                "native_right_count_gt095": int((d[right] > threshold).sum()),
                "native_right_max": float(d[right].max()) if right.any() else np.nan,
                "femstyle_external_count_gt095": int((d[ext] > threshold).sum()),
                "femstyle_external_max": float(d[ext].max()) if ext.any() else np.nan,
                "n_right_probe": int(right.sum()),
                "n_external_probe": int(ext.sum()),
                "source": path.name,
            }
        )
    return rows


def summarize(rows: list[dict], nmin: int) -> dict:
    return {
        "first_native_right_count": _first_cycle(rows, "native_right_count_gt095", nmin),
        "first_femstyle_external_count": _first_cycle(rows, "femstyle_external_count_gt095", 1),
        "first_native_right_max": _first_cycle(rows, "native_right_max", 0.95),
        "first_femstyle_external_max": _first_cycle(rows, "femstyle_external_max", 0.95),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pidl-archive", type=Path, default=DEFAULT_PIDL)
    p.add_argument("--fem-dir", type=Path, default=DEFAULT_FEM_DIR)
    p.add_argument("--fem-csv", type=Path, default=DEFAULT_FEM_CSV)
    p.add_argument("--threshold", type=float, default=0.95)
    p.add_argument("--nmin", type=int, default=3)
    p.add_argument("--fem-layer-tol", type=float, default=0.02)
    p.add_argument("--cycles", default="all",
                   help="'all' or comma-separated PIDL cycles, e.g. 0,20,40,60,80,81,82,83")
    p.add_argument("--out", type=Path, default=HERE / "alignment_criteria_u012_baseline.csv")
    args = p.parse_args()

    cycles = None if args.cycles == "all" else [int(x) for x in args.cycles.split(",") if x.strip()]

    pidl_rows = audit_pidl(args.pidl_archive, args.threshold, args.nmin, cycles)
    fem_rows = audit_fem(args.fem_dir, args.threshold, args.fem_layer_tol)
    rows = sorted(pidl_rows + fem_rows, key=lambda r: (r["method"], r["cycle"]))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"saved {args.out}")
    print("\n=== PIDL summary ===")
    for k, v in summarize(pidl_rows, args.nmin).items():
        print(f"{k}: {v}")
    print("\n=== FEM snapshot summary ===")
    for k, v in summarize(fem_rows, args.nmin).items():
        print(f"{k}: {v}")

    if args.fem_csv.exists():
        fem_ts = pd.read_csv(args.fem_csv)
        if "d_max" in fem_ts.columns:
            first_dmax = fem_ts.loc[fem_ts["d_max"] >= args.threshold, "N"]
            print("\n=== FEM timeseries note ===")
            print(f"first global d_max >= {args.threshold}: "
                  f"{int(first_dmax.iloc[0]) if len(first_dmax) else None}")
            print("Note: d_max is global/timeseries, not necessarily the same as boundary-layer count.")

    print("\nDecision use: if crossed criteria move N_f by only 0-2 cycles, detector mismatch is minor; "
          "if they move it materially, claim native N_f separately from harmonized N_f.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
