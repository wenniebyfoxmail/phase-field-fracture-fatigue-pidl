#!/usr/bin/env python3
"""Audit FEM crack-tip psi peaks against mesh size.

The companion `audit_fem_psi_units.py` checks the far-field/unit scale.  This
script checks the next question: do large crack-tip `psi_peak` values grow in a
mesh-consistent way while the nominal/far-field psi remains stable?

Expected input per FEM run directory:
- `extra_scalars.dat` with cycle-wise `psi_peak`, `psi_tip`, `psi_nominal`.
- optional `mesh_geometry.mat` with centroids/areas, or any MAT file containing
  element centroids and areas.  If areas are missing, h is estimated from
  quadrilateral node coordinates when possible.

The script is deliberately tolerant because the FEM handoff files evolved over
time.  Missing data produces a manifest instead of a hard crash.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import scipy.io as sio


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "figures" / "fem_psi_audit"
DEFAULT_ROOTS = [
    Path.home() / "Downloads",
    Path.home()
    / "Library"
    / "CloudStorage"
    / "OneDrive-UniversityofCambridge"
    / "PIDL result",
    Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/GRIPHFiTH/Scripts/fatigue_fracture"),
]
RUN_NAME_RE = re.compile(r"SENT_PIDL_12(?:_fine|_mesh_[A-Za-z0-9_]+|_export)?$")


def _flatten_mat_array(value: Any) -> np.ndarray:
    return np.asarray(value, dtype=float).squeeze()


def find_run_dirs(roots: list[Path]) -> list[Path]:
    run_dirs: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_dir():
                continue
            if RUN_NAME_RE.search(path.name) and (
                (path / "extra_scalars.dat").exists()
                or (path / "psi_fields").exists()
                or (path / "mesh_geometry.mat").exists()
            ):
                run_dirs.add(path)
    return sorted(run_dirs)


def read_extra_scalars(path: Path) -> dict[str, np.ndarray]:
    lines = [line.strip() for line in path.read_text(errors="ignore").splitlines()]
    lines = [line for line in lines if line and not line.startswith("%")]
    if not lines:
        raise ValueError(f"{path} is empty")

    header_tokens: list[str] | None = None
    data_start = 0
    for i, line in enumerate(lines[:10]):
        tokens = re.split(r"[\s,]+", line.lstrip("#").strip())
        if any(re.search(r"[A-Za-z_]", token) for token in tokens):
            header_tokens = tokens
            data_start = i + 1
            break

    raw = np.genfromtxt(lines[data_start:], dtype=float)
    if raw.ndim == 1:
        raw = raw[None, :]

    if header_tokens and len(header_tokens) == raw.shape[1]:
        names = header_tokens
    else:
        fallback = [
            "cycle",
            "psi_peak",
            "psi_tip",
            "psi_nominal",
            "Kt",
            "f_mean",
            "alpha_mean",
            "alpha_max",
        ]
        names = fallback[: raw.shape[1]]
        names.extend(f"col_{i}" for i in range(len(names), raw.shape[1]))

    return {name: raw[:, i] for i, name in enumerate(names)}


def _find_key(data: dict[str, np.ndarray], *needles: str) -> str | None:
    lowered = {key.lower(): key for key in data}
    for needle in needles:
        for low, key in lowered.items():
            if needle.lower() == low or needle.lower() in low:
                return key
    return None


def load_mesh_h_tip(run_dir: Path, crack_tip: tuple[float, float], radius: float) -> float | None:
    mat_candidates = [run_dir / "mesh_geometry.mat", *sorted(run_dir.glob("*mesh*.mat"))]
    psi_dir = run_dir / "psi_fields"
    if psi_dir.exists():
        mat_candidates.extend(sorted(psi_dir.glob("cycle_*.mat")))

    for mat_path in mat_candidates:
        if not mat_path.exists():
            continue
        try:
            mat = sio.loadmat(mat_path)
        except Exception:
            continue

        centroids = None
        for key in ("centroids", "element_centroids", "elem_centroids"):
            if key in mat:
                centroids = _flatten_mat_array(mat[key])
                break
        if centroids is not None and centroids.ndim == 1:
            centroids = centroids.reshape((-1, 2))

        areas = None
        for key in ("areas", "element_areas", "elem_areas"):
            if key in mat:
                areas = _flatten_mat_array(mat[key]).ravel()
                break

        if areas is None and {"node_coords", "elements"}.issubset(mat):
            nodes = np.asarray(mat["node_coords"], dtype=float)
            elements = np.asarray(mat["elements"], dtype=int)
            if elements.min() == 1:
                elements = elements - 1
            pts = nodes[elements[:, :4], :2]
            x = pts[:, :, 0]
            y = pts[:, :, 1]
            areas = 0.5 * np.abs(
                np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1)
            )
            if centroids is None:
                centroids = pts.mean(axis=1)

        if centroids is None or areas is None:
            continue
        dist = np.hypot(centroids[:, 0] - crack_tip[0], centroids[:, 1] - crack_tip[1])
        mask = dist <= radius
        if not np.any(mask):
            mask = dist <= np.percentile(dist, 1.0)
        return float(np.sqrt(np.median(areas[mask])))
    return None


def summarize_run(run_dir: Path, crack_tip: tuple[float, float], radius: float) -> dict[str, float | str]:
    extra_path = run_dir / "extra_scalars.dat"
    if not extra_path.exists():
        return {"run": run_dir.name, "path": str(run_dir), "status": "missing extra_scalars.dat"}

    data = read_extra_scalars(extra_path)
    cycle_key = _find_key(data, "cycle")
    peak_key = _find_key(data, "psi_peak", "peak")
    tip_key = _find_key(data, "psi_tip", "tip")
    nominal_key = _find_key(data, "psi_nominal", "nominal", "far")

    if not peak_key and not tip_key:
        return {
            "run": run_dir.name,
            "path": str(run_dir),
            "status": f"missing psi peak/tip columns; found {','.join(data)}",
        }

    cycles = data[cycle_key] if cycle_key else np.arange(1, len(next(iter(data.values()))) + 1)
    peak = data[peak_key] if peak_key else data[tip_key]
    tip = data[tip_key] if tip_key else peak
    nominal = data[nominal_key] if nominal_key else np.full_like(peak, np.nan)
    h_tip = load_mesh_h_tip(run_dir, crack_tip, radius)

    last = int(np.nanargmax(cycles))
    peak_max_idx = int(np.nanargmax(peak))
    return {
        "run": run_dir.name,
        "path": str(run_dir),
        "status": "ok" if h_tip is not None else "missing mesh h",
        "N_rows": int(len(cycles)),
        "cycle_last": float(cycles[last]),
        "cycle_peak_max": float(cycles[peak_max_idx]),
        "psi_peak_max": float(peak[peak_max_idx]),
        "psi_tip_last": float(tip[last]),
        "psi_nominal_cycle1": float(nominal[0]),
        "psi_nominal_last": float(nominal[last]),
        "h_tip": float(h_tip) if h_tip is not None else np.nan,
        "psi_peak_times_h": float(peak[peak_max_idx] * h_tip) if h_tip is not None else np.nan,
        "psi_tip_last_times_h": float(tip[last] * h_tip) if h_tip is not None else np.nan,
    }


def write_outputs(rows: list[dict[str, float | str]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not rows:
        rows = [{"run": "", "path": "", "status": "no FEM mesh-variant run directories found"}]

    csv_path = OUT_DIR / "fem_psi_mesh_scaling_audit.csv"
    all_keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in all_keys:
                all_keys.append(key)
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys)
        writer.writeheader()
        writer.writerows(rows)

    md_path = OUT_DIR / "fem_psi_mesh_scaling_audit.md"
    ok_rows = [r for r in rows if r.get("status") == "ok"]
    with md_path.open("w") as f:
        f.write("# FEM psi mesh-scaling audit\n\n")
        if not rows:
            f.write("No FEM mesh-variant run directories were found in the configured roots.\n")
        else:
            f.write("| run | status | rows | last cycle | h_tip | psi_peak_max | psi_peak*h |\n")
            f.write("|---|---|---:|---:|---:|---:|---:|\n")
            for r in rows:
                f.write(
                    f"| {r.get('run')} | {r.get('status')} | {r.get('N_rows', '')} | "
                    f"{r.get('cycle_last', '')} | {r.get('h_tip', '')} | "
                    f"{r.get('psi_peak_max', '')} | {r.get('psi_peak_times_h', '')} |\n"
                )
        f.write("\n## Interpretation rule\n\n")
        f.write(
            "If far-field/nominal psi remains stable while `psi_peak` increases as `h_tip` "
            "decreases, the large tip energy is likely a localization/mesh-resolution effect. "
            "If nominal psi drifts with h or peak values vary erratically, reopen the FEM "
            "unit/export definition audit.\n"
        )

    if ok_rows:
        sorted_rows = sorted(ok_rows, key=lambda r: float(r["h_tip"]))
        h = np.array([float(r["h_tip"]) for r in sorted_rows])
        peak = np.array([float(r["psi_peak_max"]) for r in sorted_rows])
        nominal = np.array([float(r["psi_nominal_cycle1"]) for r in sorted_rows])
        labels = [str(r["run"]) for r in sorted_rows]

        fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8))
        axes[0].loglog(h, peak, "o-")
        axes[0].invert_xaxis()
        for x, y, label in zip(h, peak, labels):
            axes[0].annotate(label, (x, y), fontsize=7)
        axes[0].set_xlabel("h_tip")
        axes[0].set_ylabel("max psi_peak")
        axes[0].set_title("Crack-tip peak vs mesh size")

        axes[1].plot(h, nominal, "o-")
        axes[1].invert_xaxis()
        axes[1].set_xlabel("h_tip")
        axes[1].set_ylabel("cycle-1 psi_nominal")
        axes[1].set_title("Far-field stability check")
        fig.tight_layout()
        fig.savefig(OUT_DIR / "fem_psi_mesh_scaling_audit.png", dpi=220)
        fig.savefig(OUT_DIR / "fem_psi_mesh_scaling_audit.pdf")

    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", action="append", type=Path, help="Additional FEM handoff root")
    parser.add_argument("--crack-tip-x", type=float, default=0.0)
    parser.add_argument("--crack-tip-y", type=float, default=0.0)
    parser.add_argument("--tip-radius", type=float, default=0.03)
    args = parser.parse_args()

    roots = DEFAULT_ROOTS + (args.root or [])
    run_dirs = find_run_dirs(roots)
    rows = [
        summarize_run(run_dir, (args.crack_tip_x, args.crack_tip_y), args.tip_radius)
        for run_dir in run_dirs
    ]
    write_outputs(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
