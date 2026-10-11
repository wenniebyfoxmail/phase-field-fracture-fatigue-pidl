#!/usr/bin/env python3
"""Render per-step FEM damage fields from the 2026-06-07 24-VTK handoff."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import PowerNorm
from matplotlib.tri import Triangulation
import meshio
import numpy as np
from PIL import Image, ImageStat


REPO_ROOT = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl")
CASES_ROOT = REPO_ROOT / "Alignment check" / "FEM monotonic match" / "cases"
PACKAGE_ROOT = (
    REPO_ROOT
    / "Alignment check"
    / "FEM monotonic match"
    / "raw_handoff"
    / "_pidl_handoff_soft_hist0_monotonic_24vtk_20260607"
)

CASE_MAP = {
    "fatigue_off": "umax020_fatigue_off",
    "fatigue_on": "umax020_fatigue_on",
}

STEP_RE = re.compile(r"fields_000001_(\d{3})\.vtk$")


def step_from_vtk(path: Path) -> int:
    match = STEP_RE.match(path.name)
    if not match:
        raise ValueError(f"Unexpected VTK name: {path.name}")
    return int(match.group(1))


def read_load_table(case_source: Path) -> dict[int, tuple[float, float]]:
    files = sorted(case_source.glob("load_displ_*.out"))
    if not files:
        return {}
    rows: dict[int, tuple[float, float]] = {}
    with files[0].open("r", encoding="utf-8-sig") as handle:
        header = handle.readline()
        if "step" not in header:
            raise ValueError(f"Unexpected load table header in {files[0]}")
        for line in handle:
            parts = line.split()
            if len(parts) < 5:
                continue
            step = int(parts[0])
            uy = float(parts[3])
            fy = float(parts[4])
            rows[step] = (uy, fy)
    return rows


def quad_triangles(mesh: meshio.Mesh) -> np.ndarray:
    blocks: list[np.ndarray] = []
    for block in mesh.cells:
        if block.type == "triangle":
            blocks.append(block.data)
        elif block.type == "quad":
            quads = block.data
            blocks.append(quads[:, [0, 1, 2]])
            blocks.append(quads[:, [0, 2, 3]])
    if not blocks:
        raise ValueError("No triangle or quad cells found in VTK")
    return np.vstack(blocks)


def damage_array(mesh: meshio.Mesh) -> np.ndarray:
    if "d" not in mesh.point_data:
        raise ValueError("VTK is missing point_data['d']")
    return np.squeeze(np.asarray(mesh.point_data["d"], dtype=float))


def collect_damage_range(vtks: list[Path]) -> tuple[float, float]:
    max_damage = 0.0
    for vtk in vtks:
        values = damage_array(meshio.read(vtk))
        finite = values[np.isfinite(values)]
        if finite.size:
            max_damage = max(max_damage, float(np.nanmax(finite)))
    return 0.0, max(1.0, max_damage)


def render_damage(
    vtk: Path,
    out_path: Path,
    case_name: str,
    step: int,
    uy: float | None,
    fy: float | None,
    vmin: float,
    vmax: float,
) -> dict[str, object]:
    mesh = meshio.read(vtk)
    points = np.asarray(mesh.points[:, :2], dtype=float)
    tri = Triangulation(points[:, 0], points[:, 1], quad_triangles(mesh))
    damage = damage_array(mesh)

    fig, ax = plt.subplots(figsize=(6.0, 4.8), constrained_layout=True)
    image = ax.tripcolor(
        tri,
        damage,
        shading="gouraud",
        cmap="magma",
        norm=PowerNorm(gamma=0.35, vmin=vmin, vmax=vmax),
    )
    ax.set_aspect("equal")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    subtitle = f"step {step:02d}"
    if uy is not None and fy is not None:
        subtitle += f", U={uy:.3f}, F={fy:.4g}"
    ax.set_title(f"{case_name} | {subtitle} | d")
    cbar = fig.colorbar(image, ax=ax, shrink=0.86)
    cbar.set_label("damage d (shared scale)")
    fig.savefig(out_path, dpi=240)
    plt.close(fig)

    return {
        "case": case_name,
        "step": step,
        "uy": "" if uy is None else uy,
        "fy": "" if fy is None else fy,
        "source_vtk": str(vtk),
        "figure": str(out_path),
        "d_min": float(np.nanmin(damage)),
        "d_max": float(np.nanmax(damage)),
    }


def qa_png(path: Path) -> tuple[float, float]:
    with Image.open(path) as img:
        gray = img.convert("L")
        stat = ImageStat.Stat(gray)
        return float(stat.mean[0]), float(stat.stddev[0])


def main() -> None:
    all_vtks = sorted(PACKAGE_ROOT.glob("fatigue_*/fields_000001_*.vtk"), key=lambda p: (p.parent.name, step_from_vtk(p)))
    if len(all_vtks) != 48:
        raise SystemExit(f"Expected 48 VTKs, found {len(all_vtks)} in {PACKAGE_ROOT}")

    vmin, vmax = collect_damage_range(all_vtks)
    manifest_rows: list[dict[str, object]] = []

    for source_folder, case_name in CASE_MAP.items():
        case_source = PACKAGE_ROOT / source_folder
        case_dir = CASES_ROOT / case_name
        out_dir = case_dir / "figures" / "damage_steps_20260607"
        out_dir.mkdir(parents=True, exist_ok=True)

        load_rows = read_load_table(case_source)
        vtks = sorted(case_source.glob("fields_000001_*.vtk"), key=step_from_vtk)
        if len(vtks) != 24:
            raise SystemExit(f"Expected 24 VTKs in {case_source}, found {len(vtks)}")

        for vtk in vtks:
            step = step_from_vtk(vtk)
            uy, fy = load_rows.get(step, (None, None))
            out_path = out_dir / f"{case_name}_cycle{step:02d}.png"
            row = render_damage(vtk, out_path, case_name, step, uy, fy, vmin, vmax)
            mean, stddev = qa_png(out_path)
            row["png_gray_mean"] = mean
            row["png_gray_stddev"] = stddev
            manifest_rows.append(row)

        case_manifest = out_dir / f"{case_name}_damage_steps_manifest.csv"
        with case_manifest.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[-1]))
            writer.writeheader()
            writer.writerows([row for row in manifest_rows if row["case"] == case_name])

    combined_manifest = CASES_ROOT / "soft_hist0_monotonic_24vtk_damage_manifest_20260607.csv"
    with combined_manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0]))
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Rendered {len(manifest_rows)} damage figures")
    print(f"Shared damage scale: [{vmin:.6g}, {vmax:.6g}]")
    print(f"Manifest: {combined_manifest}")


if __name__ == "__main__":
    main()
