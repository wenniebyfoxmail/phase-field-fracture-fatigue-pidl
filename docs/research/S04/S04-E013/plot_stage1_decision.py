#!/usr/bin/env python3
"""Render the S04-E013 Stage 1 decision figure from the tracked aggregate CSV."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


STATES = ("c20s4", "c60s4", "c82s4", "c83s4")
PERIODS = ("early", "middle", "late", "transition")
METRICS = (
    ("displacement_mass_rms_over_abs_Us", 1e-3, "Displacement / gate", "#0072B2"),
    ("strain_relative_l2", 1e-2, "Strain / gate", "#D55E00"),
    ("predicted_rho_u", 1e-3, r"$\rho_u$ / gate", "#009E73"),
)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected = {(state, seed) for state in STATES for seed in ("1", "7", "19")}
    found = {(row["state"], row["seed"]) for row in rows}
    if len(rows) != 12 or found != expected:
        raise ValueError(f"expected frozen 12-row matrix, found {len(rows)} rows")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    rows = read_rows(args.metrics)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    by_state: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_state[row["state"]].append(row)

    x = np.arange(len(STATES))
    fig, axes = plt.subplots(1, 3, figsize=(10.8, 3.6), constrained_layout=True)
    for ax, (field, gate, label, color) in zip(axes, METRICS):
        values = np.array(
            [[float(row[field]) / gate for row in by_state[state]] for state in STATES]
        )
        for seed_idx, seed in enumerate((1, 7, 19)):
            ax.plot(
                x,
                values[:, seed_idx],
                color="#999999",
                alpha=0.55,
                linewidth=0.9,
                marker="o",
                markersize=3,
                label=f"seed {seed}" if ax is axes[0] else None,
            )
        means = values.mean(axis=1)
        ax.plot(x, means, color=color, linewidth=2.0, marker="o", markersize=5, label="mean")
        ax.axhline(1.0, color="#222222", linestyle="--", linewidth=1.2, label="frozen gate")
        ax.set_yscale("log")
        ax.set_xticks(x, [f"{state[:-2]}\n{period}" for state, period in zip(STATES, PERIODS)])
        ax.set_ylabel(label)
        ax.grid(axis="y", color="#dddddd", linewidth=0.7)
        ax.spines[["top", "right"]].set_visible(False)
        ax.text(
            0.03,
            0.94,
            f"{means.min():.1f}–{means.max():.1f}× gate",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8.5,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78, "pad": 1.5},
        )

    axes[0].legend(frameon=False, fontsize=7.5, ncol=2, loc="lower right")
    fig.suptitle(
        "S04-E013 Stage 1: all non-BC gates fail from the early state onward\n"
        "Three seeds per state; essential-BC error is exactly zero in all 12 runs",
        fontsize=11,
    )
    for suffix in ("png", "pdf"):
        fig.savefig(args.output_dir / f"stage1_gate_ratios.{suffix}", dpi=240, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
