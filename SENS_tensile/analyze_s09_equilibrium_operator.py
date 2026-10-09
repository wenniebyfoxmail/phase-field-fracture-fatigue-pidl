#!/usr/bin/env python3
"""Recompute and visualize the fixed S09-E004 final-step decision."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))


COLORS = {"data_only": "#0072B2", "equilibrium_informed": "#D55E00"}
LABELS = {"data_only": "Data only", "equilibrium_informed": "Equilibrium informed"}


def weighted_l2(prediction, target, area):
    return float(np.sqrt(((prediction-target)**2).sum(axis=1).dot(area)))


def load_json(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)

    metrics = load_json(args.run / "metrics.json")
    with np.load(args.run / "final_fields.npz", allow_pickle=False) as archive:
        fields = {key: archive[key] for key in archive.files}
    with np.load(args.packet, allow_pickle=False) as archive:
        packet = {key: archive[key] for key in archive.files}
    packet_identity = {"xy": packet["xy"], "area": packet["lumped_area"],
                       "cycle": packet["dev_cycle"], "damage": packet["dev_d"]}
    for key in ("xy", "area", "cycle", "damage"):
        if not np.array_equal(fields[key], packet_identity[key]):
            raise ValueError(f"field export identity mismatch: {key}")

    recomputed = {}
    denominators = []
    for state in range(3):
        denominators.append(weighted_l2(fields["affine"][state], fields["target"][state], fields["area"]))
    for arm in COLORS:
        numerators = [weighted_l2(fields[f"{arm}_prediction"][state], fields["target"][state], fields["area"])
                      for state in range(3)]
        recomputed[arm] = {
            "R": sum(numerators) / sum(denominators),
            "per_state_relative_to_affine": [left/right for left, right in zip(numerators, denominators)],
        }
        if not np.isclose(recomputed[arm]["R"], metrics["final"][arm]["R"], rtol=2e-6, atol=1e-8):
            raise ValueError(f"recomputed final metric mismatch: {arm}")
    ratio = recomputed["equilibrium_informed"]["R"] / recomputed["data_only"]["R"]
    if not np.isclose(ratio, metrics["primary"]["ratio"], rtol=2e-6, atol=1e-8):
        raise ValueError("recomputed primary ratio mismatch")
    recomputed["primary_ratio"] = ratio
    recomputed["primary_pass"] = bool(ratio <= .95)
    (args.out / "recomputed_metrics.json").write_text(json.dumps(recomputed, indent=2) + "\n")

    with (args.run / "history.csv").open(newline="") as stream:
        history = list(csv.DictReader(stream))
    fig, axes = plt.subplots(2, 2, figsize=(10.4, 7.4), constrained_layout=True)
    ax = axes[0, 0]
    for arm in COLORS:
        rows = [row for row in history if row["phase"] == "matched" and row["arm"] == arm]
        ax.plot([int(row["step"]) for row in rows], [float(row["development_R"]) for row in rows],
                marker="o", ms=3.2, lw=1.5, color=COLORS[arm], label=LABELS[arm])
    ax.set(xlabel="Matched update", ylabel=r"Development $R_m$", title="(a) Development trajectory")
    ax.grid(alpha=.22); ax.legend(frameon=False)

    ax = axes[0, 1]
    final = [recomputed[arm]["R"] for arm in COLORS]
    ax.bar(range(2), final, color=[COLORS[arm] for arm in COLORS], width=.62)
    ax.set_xticks(range(2), [LABELS[arm] for arm in COLORS])
    ax.axhline(1, color="0.35", ls="--", lw=1.2, label="Affine comparator")
    ax.set(ylabel=r"Final $R_m$ (lower is better)", title="(b) Frozen final decision")
    ax.text(.5, .84, f"ratio = {ratio:.3f} > 0.95  FAIL", transform=ax.transAxes,
            ha="center", va="top", color="#A51C30", weight="bold",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": .85, "pad": 2})
    ax.legend(frameon=False, loc="upper left")

    ax = axes[1, 0]
    x = np.arange(3); width = .36
    for offset, arm in zip((-.18, .18), COLORS):
        ax.bar(x+offset, recomputed[arm]["per_state_relative_to_affine"], width,
               color=COLORS[arm], label=LABELS[arm])
    ax.axhline(1, color="0.35", ls="--", lw=1.2)
    ax.set_xticks(x, [f"c{cycle}" for cycle in fields["cycle"]])
    ax.set(ylabel="Weighted error / affine error", title="(c) Final error by development state")
    ax.legend(frameon=False, loc="upper left")

    ax = axes[1, 1]
    residual = [[state["free_force_rms_ratio_to_affine"] for state in metrics["final"][arm]["states"]]
                for arm in COLORS]
    for offset, arm, values in zip((-.18, .18), COLORS, residual):
        ax.bar(x+offset, values, width, color=COLORS[arm], label=LABELS[arm])
    ax.axhline(1, color="0.35", ls="--", lw=1.2)
    ax.set_yscale("log"); ax.set_xticks(x, [f"c{cycle}" for cycle in fields["cycle"]])
    ax.set(ylabel="Free-force RMS / affine RMS", title="(d) Physics diagnostic (log scale)")
    ax.legend(frameon=False)
    for extension in ("png", "pdf"):
        fig.savefig(args.out / f"decision.{extension}", dpi=220)
    plt.close(fig)

    xy = fields["xy"]
    conn = packet["conn"]
    triangles = np.concatenate((conn[:, [0, 1, 2]], conn[:, [0, 2, 3]]), axis=0)
    triangulation = mtri.Triangulation(xy[:, 0], xy[:, 1], triangles)
    values = [fields["target"][:, :, 1], fields["data_only_prediction"][:, :, 1],
              fields["equilibrium_informed_prediction"][:, :, 1]]
    vmin = min(float(value.min()) for value in values)
    vmax = max(float(value.max()) for value in values)
    fig, axes = plt.subplots(3, 3, figsize=(10, 9.2), constrained_layout=True, sharex=True, sharey=True)
    rows = (("FEM exported $u_y$", values[0]), ("Data-only $u_y$", values[1]),
            ("Equilibrium-informed $u_y$", values[2]))
    image = None
    for row, (label, array) in enumerate(rows):
        for column, cycle in enumerate(fields["cycle"]):
            image = axes[row, column].tripcolor(triangulation, array[column], shading="gouraud",
                                                cmap="viridis", vmin=vmin, vmax=vmax, rasterized=True)
            axes[row, column].set_aspect("equal")
            axes[row, column].set_title(f"{label}, c{cycle}", fontsize=9)
            if row == 2: axes[row, column].set_xlabel("x")
            if column == 0: axes[row, column].set_ylabel("y")
    colorbar = fig.colorbar(image, ax=axes, location="right", shrink=.8)
    colorbar.set_label("Peak vertical displacement $u_y$")
    fig.savefig(args.out / "fields.png", dpi=220)
    plt.close(fig)
    print(json.dumps(recomputed))


if __name__ == "__main__":
    main()
