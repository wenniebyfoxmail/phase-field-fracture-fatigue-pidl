#!/usr/bin/env python3
"""Development-only training-field view; no stage9 access or physical fit."""
import argparse
import json
from pathlib import Path
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from aa2024_triplet_structure import read_member, parse_nodemap


def main():
    p = argparse.ArgumentParser()
    p.add_argument("archive", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(args.archive) as z:
        nodes = [parse_nodemap(read_member(z, f"global_3d_dic/Nodemaps/global_3d_dic_results_1_{s}.txt"), allow_displacements=True) for s in (7, 8)]
    a, b = nodes
    if not np.array_equal(a["ids"], b["ids"]):
        raise ValueError("node identity order differs")
    mask = a["finite_xyz"] & b["finite_xyz"] & a["finite_u"] & b["finite_u"]
    xy = a["xyz"][mask, :2]
    du = b["u"][mask, :2] - a["u"][mask, :2]
    fig, axes = plt.subplots(1, 2, figsize=(10, 7), constrained_layout=True)
    limits = []
    for i, ax in enumerate(axes):
        lim = float(np.quantile(np.abs(du[:, i]), .99))
        limits.append(lim)
        artist = ax.scatter(xy[:, 0], xy[:, 1], c=du[:, i], s=1,
                            cmap="RdBu_r", vmin=-lim, vmax=lim, rasterized=True)
        ax.set_aspect("equal")
        ax.set_xlabel("reference x [mm]")
        ax.set_ylabel("reference y [mm]")
        ax.set_title(f"stage8-stage7: delta {'uv'[i]} [mm]")
        fig.colorbar(artist, ax=ax, label="mm; 99th-percentile display saturation")
    fig.suptitle("S03-E014 development inspection | cycle126873.5 | fit loads only\nFull view; no damage/geometry truth or inverse validation")
    fig.savefig(args.output / "training_increment.png", dpi=180)
    fig.savefig(args.output / "training_increment.pdf")
    plt.close(fig)
    summary = {"archive": str(args.archive.resolve()), "stages": [7, 8],
               "fit_joint_finite_nodes": int(mask.sum()),
               "display_limits_mm": limits,
               "values": "unmodified displacement differences; only color saturation",
               "stage9_access": False,
               "status": "exploratory_development_not_mechanical_admission"}
    (args.output / "view.json").write_text(json.dumps(summary, indent=2))
    doc = f"""# Training-only development view

Source: {args.archive.resolve()}; global nodemap stages7/8 only.
Cycle126873.5, fit loads approximately4.50/9.75kN. No high-load fields accessed.
Every jointly finite training node is displayed at serialized reference x/y
coordinates, in mm. Left/right: u/v displacement difference stage8-stage7.
Symmetric color limits use the99th percentile of absolute training differences
({limits}mm); extreme values saturate VISUALLY but numerical fields are not
clipped, smoothed or normalized. No rigid transform was reapplied.

Purpose: inspect whether a training-only crack/ROI can be defined. This is not
a damage map, registered true geometry, inverse result or scored validation.
Missing DIC facets are missing observations, not crack labels. Full measured
view is shown; no favorable field case or later cycle was selected.

Reading order: training_increment.png, then view.json. Both panels must be
visually checked. The image alone cannot verify exporter compensation or
justify a FEM boundary/phase-field basis. Next: qualify gauge and spatial assets.
"""
    (args.output / "training_increment.md").write_text(doc)
    (args.output / "README_analysis.md").write_text(doc)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
