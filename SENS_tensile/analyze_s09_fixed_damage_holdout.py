#!/usr/bin/env python3
"""Create the frozen minimum evidence figures and README for S09-E007."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np


def read_rows(path: Path) -> list[dict]:
    boolean_columns = {"candidate_affine_denominator_defined", "comparator_affine_denominator_defined"}
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for key, value in list(row.items()):
            if key in boolean_columns:
                if value not in ("True", "False"):
                    raise ValueError(f"invalid Boolean CSV value for {key}")
                row[key] = value == "True"
            elif key != "cycle":
                row[key] = None if value in ("", "None") else float(value)
        row["cycle"] = int(row["cycle"])
    if [row["cycle"] for row in rows] != list(range(1, 74)):
        raise ValueError("cycle evidence must be exact c1..c73")
    return rows


def plot_decision(metrics: dict, rows: list[dict], out: Path) -> None:
    primary = metrics["primary"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), constrained_layout=True)
    values = [primary["Q_f"], primary["Q_u"]]
    limits = [primary["Q_f_limit"], primary["Q_u_limit"]]
    heights = [np.nan if value is None else value for value in values]
    axes[0].bar(["Q_f", "Q_u"], heights, color=["#2A6F97", "#E07A5F"])
    for index, (value, limit) in enumerate(zip(values, limits)):
        axes[0].hlines(limit, index-.38, index+.38, colors="black", linestyles="--")
        axes[0].text(index, 0 if value is None else value, "undefined" if value is None else f"{value:.3f}", ha="center", va="bottom")
    axes[0].set_title(f"Frozen decision: {primary['decision']}")
    axes[0].set_ylabel("trajectory ratio (lower is better)")
    cycles = [row["cycle"] for row in rows]
    axes[1].plot(cycles, [row["cyclewise_equilibrium_ratio"] for row in rows], label="equilibrium ratio", color="#2A6F97")
    axes[1].plot(cycles, [row["cyclewise_displacement_ratio"] for row in rows], label="displacement ratio", color="#E07A5F")
    axes[1].axhline(.5, color="#2A6F97", linestyle="--", alpha=.6)
    axes[1].axhline(1.1, color="#E07A5F", linestyle="--", alpha=.6)
    axes[1].set(xlabel="cycle (correlated trajectory order)", ylabel="cyclewise diagnostic ratio")
    axes[1].legend(frameon=False)
    fig.savefig(out / "decision_and_cyclewise_ratios.png", dpi=220)
    plt.close(fig)


def plot_fields(fields_path: Path, out: Path) -> None:
    with np.load(fields_path, allow_pickle=False) as fields:
        data = {key: fields[key] for key in fields.files}
    xy, conn = data["xy"], data["conn"]
    triangles = np.vstack((conn[:, [0, 1, 2]], conn[:, [0, 2, 3]]))
    tri = mtri.Triangulation(xy[:, 0], xy[:, 1], triangles)
    cycles = data["selected_cycle"].astype(int).tolist()
    fig, axes = plt.subplots(len(cycles), 4, figsize=(13, 9), constrained_layout=True)
    for row, cycle in enumerate(cycles):
        stem = f"c{cycle:04d}"
        target = data[f"{stem}_candidate_target"]
        candidate = data[f"{stem}_candidate_prediction"]
        comparator = data[f"{stem}_comparator_prediction"]
        panels = [
            (data[f"{stem}_candidate_damage"], "damage d"),
            (target[:, 1], "FEM target u_y"),
            (np.linalg.norm(candidate-target, axis=1), "beta=.25 |error|"),
            (np.linalg.norm(comparator-target, axis=1), "data-only |error|"),
        ]
        for column, (values, title) in enumerate(panels):
            artist = axes[row, column].tripcolor(tri, values, shading="gouraud", cmap="viridis")
            axes[row, column].set_aspect("equal"); axes[row, column].set_axis_off()
            axes[row, column].set_title(f"c{cycle}: {title}")
            fig.colorbar(artist, ax=axes[row, column], shrink=.72)
    fig.savefig(out / "selected_field_views.png", dpi=220)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("analysis output must be fresh")
    args.out.mkdir(parents=True)
    metrics = json.loads((args.run_dir / "metrics.json").read_text(encoding="utf-8"))
    receipt = json.loads((args.run_dir / "receipt.json").read_text(encoding="utf-8"))
    if receipt.get("execution_status") != "succeeded":
        raise ValueError("analysis requires a completed run; preserve partial evidence separately")
    rows = read_rows(args.run_dir / "cycle_metrics.csv")
    plot_decision(metrics, rows, args.out)
    plot_fields(args.run_dir / "selected_fields.npz", args.out)
    p = metrics["primary"]
    readme = f"""# S09-E007 evidence analysis\n\n## Question\nDoes the frozen beta=0.25 fixed-damage operator retain its displacement/residual trade-off against the frozen data-only comparator on the complete U0.125 trajectory?\n\n## Evidence and reading order\n1. `decision_and_cyclewise_ratios.png`: primary Q_f={p['Q_f']} and Q_u={p['Q_u']} against frozen limits, followed by correlated cycle diagnostics.\n2. `selected_field_views.png`: predeclared c1/c37/c73 damage, target displacement, and both error fields.\n\n## Result\nDecision: `{p['decision']}`. Disposition: {p['disposition']}\n\n## Allowed conclusion\nOne non-blind post-selection synthetic U0.125 fixed-damage reconstruction result under the frozen native-Q4 mechanical-equilibrium metric.\n\n## Blocked conclusion\nThis is not damage evolution, autonomous forecasting, independent blind confirmation, exact equilibrium, seed robustness, cross-mesh transfer, FEM truth, or real-road validity. Consecutive cycles are correlated and are not independent samples.\n\n## Storyline impact\nFollow the frozen disposition above; diagnostics explain the result and do not vote or rescue it.\n"""
    (args.out / "README_analysis.md").write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    main()
