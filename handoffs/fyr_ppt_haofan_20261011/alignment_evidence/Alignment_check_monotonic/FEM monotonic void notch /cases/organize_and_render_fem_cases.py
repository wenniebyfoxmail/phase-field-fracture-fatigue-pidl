#!/usr/bin/env python3
"""Organize FEM monotonic case resources and render available figures."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, PowerNorm
import meshio
import numpy as np
import pandas as pd
from matplotlib.tri import Triangulation


CASES_ROOT = Path(__file__).resolve().parent
DOC_SUMMARY = CASES_ROOT.parent / "docs" / "monotonic_four_case_summary.csv"
CASE_NAMES = ["umax020_fatigue_off", "umax020_fatigue_on"]
RAW_FILE_PATTERNS = [
    "CONV_*.log",
    "checkpoint.mat",
    "cputime.dat",
    "crack_regularized.dat",
    "extra_scalars.dat",
    "fields_*.vtk",
    "load_displ_*.out",
    "monitorcycle.dat",
    "peak_load_c1.vtk",
]
FIELD_QUANTITIES = ["d", "alpha", "H", "Dalpha", "f(alpha)"]
MANVAS_STEPS = [
    0.025,
    0.050,
    0.075,
    0.100,
    0.105,
    0.110,
    0.115,
    0.120,
    0.125,
    0.130,
    0.135,
    0.140,
    0.145,
    0.150,
    0.155,
    0.160,
    0.165,
    0.170,
    0.175,
    0.180,
    0.185,
    0.190,
    0.195,
    0.200,
]


def case_dirs() -> list[Path]:
    return [CASES_ROOT / name for name in CASE_NAMES if (CASES_ROOT / name).is_dir()]


def resources_dir(case_dir: Path) -> Path:
    return case_dir / "_source" / "resources"


def processed_dir(case_dir: Path) -> Path:
    return case_dir / "_source" / "processed"


def figures_dir(case_dir: Path) -> Path:
    return case_dir / "figures"


def organize_case(case_dir: Path) -> None:
    resources = resources_dir(case_dir)
    processed = processed_dir(case_dir)
    figures = figures_dir(case_dir)
    resources.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    for pattern in RAW_FILE_PATTERNS:
        for src in case_dir.glob(pattern):
            dst = resources / src.name
            if dst.exists():
                continue
            shutil.move(str(src), str(dst))

    psi_src = case_dir / "psi_fields"
    psi_dst = resources / "psi_fields"
    if psi_src.exists() and not psi_dst.exists():
        shutil.move(str(psi_src), str(psi_dst))


def read_fixed_width_table(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=r"\s+", engine="python")


def load_displacement(case_dir: Path) -> pd.DataFrame | None:
    files = sorted(resources_dir(case_dir).glob("load_displ_*.out"))
    if not files:
        return None
    df = read_fixed_width_table(files[0])
    df["U_prescribed"] = MANVAS_STEPS[: len(df)]
    out = processed_dir(case_dir) / f"{case_dir.name}_load_displacement.csv"
    df.to_csv(out, index=False)
    return df


def write_scalar_tables(case_dir: Path) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for name in ["extra_scalars.dat", "monitorcycle.dat", "crack_regularized.dat", "cputime.dat"]:
        path = resources_dir(case_dir) / name
        if not path.exists():
            continue
        df = read_fixed_width_table(path)
        out[name] = df
        df.to_csv(processed_dir(case_dir) / f"{case_dir.name}_{path.stem}.csv", index=False)
    return out


def quad_triangles(mesh: meshio.Mesh) -> np.ndarray:
    tris: list[np.ndarray] = []
    for block in mesh.cells:
        if block.type == "triangle":
            tris.append(block.data)
        elif block.type == "quad":
            q = block.data
            tris.append(q[:, [0, 1, 2]])
            tris.append(q[:, [0, 2, 3]])
    if not tris:
        raise ValueError("No triangle or quad cells found")
    return np.vstack(tris)


def scalar_array(mesh: meshio.Mesh, name: str) -> np.ndarray | None:
    if name not in mesh.point_data:
        return None
    arr = np.asarray(mesh.point_data[name])
    return np.squeeze(arr)


def collect_field_ranges(case_dirs_: list[Path]) -> dict[str, tuple[float, float]]:
    values: dict[str, list[float]] = {name: [] for name in FIELD_QUANTITIES}
    for case_dir in case_dirs_:
        for vtk in sorted(resources_dir(case_dir).glob("*.vtk")):
            mesh = meshio.read(vtk)
            for name in FIELD_QUANTITIES:
                arr = scalar_array(mesh, name)
                if arr is None:
                    continue
                finite = arr[np.isfinite(arr)]
                if finite.size:
                    values[name].extend([float(finite.min()), float(finite.max())])
    ranges = {}
    for name, vals in values.items():
        if not vals:
            continue
        lo, hi = min(vals), max(vals)
        if name in {"d", "alpha", "f(alpha)"}:
            lo = min(0.0, lo)
            hi = max(1.0, hi)
        if abs(hi - lo) < 1e-12:
            hi = lo + 1e-12
        ranges[name] = (lo, hi)
    return ranges


def vtk_cycle_label(case_dir: Path, vtk: Path, summary: pd.DataFrame) -> tuple[str, str]:
    if vtk.name == "peak_load_c1.vtk":
        row = summary[summary["case_key"] == case_dir.name]
        if not row.empty:
            step = int(row.iloc[0]["peak_step"])
            uy = float(row.iloc[0]["peak_uy"])
            return f"peak_cycle{step:02d}", f"peak step {step}, U={uy:.3f}"
        return "peak_load", "peak load"
    if vtk.name.startswith("fields_"):
        step = int(vtk.stem.split("_")[-1])
        uy = MANVAS_STEPS[step - 1] if 0 < step <= len(MANVAS_STEPS) else np.nan
        return f"cycle{step:02d}", f"final step {step}, U={uy:.3f}"
    return vtk.stem, vtk.stem


def render_field_figures(case_dir: Path, ranges: dict[str, tuple[float, float]], summary: pd.DataFrame) -> list[Path]:
    outputs: list[Path] = []
    manifest_rows = []
    for vtk in sorted(resources_dir(case_dir).glob("*.vtk")):
        mesh = meshio.read(vtk)
        points = mesh.points[:, :2]
        tri = Triangulation(points[:, 0], points[:, 1], quad_triangles(mesh))
        state_slug, state_label = vtk_cycle_label(case_dir, vtk, summary)

        for quantity in FIELD_QUANTITIES:
            arr = scalar_array(mesh, quantity)
            if arr is None:
                continue
            lo, hi = ranges[quantity]
            fig, ax = plt.subplots(figsize=(6.0, 4.8), constrained_layout=True)
            if quantity in {"d", "alpha", "H", "Dalpha"}:
                norm = PowerNorm(gamma=0.35, vmin=lo, vmax=hi)
                cmap = "magma"
            else:
                norm = Normalize(vmin=lo, vmax=hi)
                cmap = "viridis"
            im = ax.tripcolor(tri, arr, shading="gouraud", cmap=cmap, norm=norm)
            ax.set_aspect("equal")
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            ax.set_title(f"{case_dir.name} | {state_label} | {quantity}")
            cb = fig.colorbar(im, ax=ax, shrink=0.86)
            cb.set_label(f"{quantity} (shared scale)")
            safe_q = quantity.replace("(", "").replace(")", "").replace("/", "_")
            out = figures_dir(case_dir) / f"{case_dir.name}_{state_slug}_{safe_q}.png"
            fig.savefig(out, dpi=240)
            plt.close(fig)
            outputs.append(out)
            manifest_rows.append(
                {
                    "case": case_dir.name,
                    "source_vtk": vtk.name,
                    "state": state_label,
                    "quantity": quantity,
                    "figure": out.name,
                    "min": float(np.nanmin(arr)),
                    "max": float(np.nanmax(arr)),
                }
            )

    if manifest_rows:
        with (figures_dir(case_dir) / f"{case_dir.name}_field_figure_manifest.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(manifest_rows[0]))
            writer.writeheader()
            writer.writerows(manifest_rows)
    return outputs


def render_load_plot(case_dir: Path, summary: pd.DataFrame) -> Path | None:
    df = load_displacement(case_dir)
    if df is None:
        return None
    row = summary[summary["case_key"] == case_dir.name]
    fig, ax = plt.subplots(figsize=(6.0, 4.4), constrained_layout=True)
    ax.plot(df["u_y"], df["F_y"], marker="o", ms=3.8, lw=1.5, color="#1b6ca8")
    ax.set_xlabel("Prescribed vertical displacement U")
    ax.set_ylabel("Reaction force F_y")
    ax.set_title(f"{case_dir.name} | load-displacement")
    ax.grid(True, color="#dddddd", lw=0.6)
    if not row.empty:
        peak_step = int(row.iloc[0]["peak_step"])
        drop_step = row.iloc[0].get("drop_step")
        peak = df[df["step"] == peak_step]
        if not peak.empty:
            ax.scatter(peak["u_y"], peak["F_y"], s=50, color="#d55e00", label=f"peak step {peak_step}")
        if not pd.isna(drop_step) and str(drop_step) != "":
            drop_step_i = int(drop_step)
            drop = df[df["step"] == drop_step_i]
            if not drop.empty:
                ax.scatter(drop["u_y"], drop["F_y"], s=50, color="#009e73", label=f"drop step {drop_step_i}")
        ax.legend(frameon=False)
    out = figures_dir(case_dir) / f"{case_dir.name}_load_displacement.png"
    fig.savefig(out, dpi=240)
    plt.close(fig)
    return out


def render_combined_plots(case_dirs_: list[Path], summary: pd.DataFrame) -> list[Path]:
    root_figs = CASES_ROOT / "figures"
    root_figs.mkdir(exist_ok=True)
    outputs: list[Path] = []

    fig, ax = plt.subplots(figsize=(6.2, 4.4), constrained_layout=True)
    colors = {"umax020_fatigue_off": "#1b6ca8", "umax020_fatigue_on": "#d55e00"}
    for case_dir in case_dirs_:
        df = pd.read_csv(processed_dir(case_dir) / f"{case_dir.name}_load_displacement.csv")
        ax.plot(df["u_y"], df["F_y"], marker="o", ms=3.5, lw=1.5, label=case_dir.name, color=colors.get(case_dir.name))
    ax.set_xlabel("Prescribed vertical displacement U")
    ax.set_ylabel("Reaction force F_y")
    ax.set_title("FEM Umax0.2 load-displacement comparison")
    ax.grid(True, color="#dddddd", lw=0.6)
    ax.legend(frameon=False)
    out = root_figs / "fem_umax020_load_displacement_comparison.png"
    fig.savefig(out, dpi=240)
    plt.close(fig)
    outputs.append(out)

    subset = summary[summary["case_key"].isin([d.name for d in case_dirs_])].copy()
    subset.to_csv(CASES_ROOT / "fem_umax020_scalar_summary.csv", index=False)
    metrics = ["Kt", "f_mean", "alpha_bar_mean", "psi_peak"]
    fig, axes = plt.subplots(1, len(metrics), figsize=(11.0, 3.5), constrained_layout=True)
    for ax, metric in zip(axes, metrics):
        vals = subset[metric].astype(float).to_numpy()
        labels = ["off" if "off" in x else "on" for x in subset["case_key"]]
        ax.bar(labels, vals, color=["#1b6ca8", "#d55e00"][: len(vals)])
        ax.set_title(metric)
        ax.grid(True, axis="y", color="#dddddd", lw=0.6)
        if metric == "psi_peak":
            ax.set_yscale("log")
    fig.suptitle("FEM Umax0.2 scalar summaries")
    out = root_figs / "fem_umax020_scalar_summary.png"
    fig.savefig(out, dpi=240)
    plt.close(fig)
    outputs.append(out)
    return outputs


def write_case_readme(case_dirs_: list[Path]) -> None:
    lines = [
        "# FEM Monotonic Case Structure",
        "",
        "Each available FEM case is organized to match the PIDL monotonic case folders.",
        "",
        "- `_source/resources/`: original FEM handoff files (`*.vtk`, `*.dat`, `*.out`, `*.log`, checkpoint, and `psi_fields/`).",
        "- `_source/processed/`: parsed CSV tables generated from the FEM text resources.",
        "- `figures/`: rendered field and load-displacement figures for the available FEM snapshots.",
        "- `cases/figures/`: combined Umax0.2 comparison figures across the available fatigue-on/off cases.",
        "",
        "Current local availability: only `umax020_fatigue_off` and `umax020_fatigue_on` are present in this `cases/` folder.",
        "The handoff README documents Umax0.12 cases too, but those folders are not currently present locally.",
        "",
        "Field-figure caveat: the available FEM resources contain final `fields_000001_024.vtk` and `peak_load_c1.vtk`, not one VTK file per load step.",
    ]
    for case_dir in case_dirs_:
        figs = len(list(figures_dir(case_dir).glob("*.png")))
        lines.append(f"- `{case_dir.name}`: {figs} PNG figures generated.")
    (CASES_ROOT / "README_case_structure.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    cases = case_dirs()
    if not cases:
        raise SystemExit("No configured FEM case directories found")
    summary = pd.read_csv(DOC_SUMMARY)

    for case_dir in cases:
        organize_case(case_dir)
        write_scalar_tables(case_dir)
        load_displacement(case_dir)

    ranges = collect_field_ranges(cases)
    for case_dir in cases:
        render_field_figures(case_dir, ranges, summary)
        render_load_plot(case_dir, summary)

    render_combined_plots(cases, summary)
    write_case_readme(cases)
    print(f"Organized and rendered {len(cases)} FEM cases in {CASES_ROOT}")


if __name__ == "__main__":
    main()
