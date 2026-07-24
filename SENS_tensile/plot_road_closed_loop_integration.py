#!/usr/bin/env python3
"""Render the evidence-bounded road closed-loop integration status."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


COLORS = {
    "pass_tooling_only": "#2A9D8F",
    "negative_reality_facing_result": "#E9C46A",
    "unavailable_untrained": "#E76F51",
    "interface_only": "#6C8EBF",
    "not_achieved": "#9B9B9B",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with args.status.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    display = [rows[index] for index in (0, 1, 2, 3, 4)]
    fig, ax = plt.subplots(figsize=(15, 6.6))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 6.6)
    ax.axis("off")

    titles = [
        "Observation\nassimilation",
        "Direct h1-h3\nfield forecast",
        "Innovation / OOD\ntrigger",
        "Re-assimilate\nor continue",
        "Scenario risk\nand RUL",
    ]
    x_positions = [0.4, 3.35, 6.3, 9.25, 12.2]
    for index, (row, title, x_pos) in enumerate(zip(display, titles, x_positions)):
        color = COLORS[row["status"]]
        box = FancyBboxPatch(
            (x_pos, 3.4),
            2.4,
            1.65,
            boxstyle="round,pad=0.04,rounding_size=0.08",
            linewidth=1.5,
            edgecolor="#263238",
            facecolor=color,
            alpha=0.94,
        )
        ax.add_patch(box)
        ax.text(
            x_pos + 1.2,
            4.47,
            title,
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
            color="white" if row["status"] != "negative_reality_facing_result" else "#263238",
        )
        ax.text(
            x_pos + 1.2,
            3.78,
            row["status"].replace("_", " "),
            ha="center",
            va="center",
            fontsize=9.2,
            color="white" if row["status"] != "negative_reality_facing_result" else "#263238",
        )
        if index < len(display) - 1:
            ax.add_patch(
                FancyArrowPatch(
                    (x_pos + 2.42, 4.22),
                    (x_positions[index + 1] - 0.08, 4.22),
                    arrowstyle="-|>",
                    mutation_scale=18,
                    linewidth=1.8,
                    color="#263238",
                )
            )

    ax.text(
        0.4,
        6.15,
        "Road closed-loop fracture forecasting: integration evidence map",
        fontsize=20,
        fontweight="bold",
        color="#1F2933",
    )
    ax.text(
        0.4,
        5.68,
        "FEM eta0 is the numerical reference. Tooling compatibility is not real-road validation.",
        fontsize=11.5,
        color="#455A64",
    )

    evidence_lines = [
        "PASS: identical analysis/mask/scenario hashes; legacy h1 error = 0; latent-to-sensor leak = 0",
        "NEGATIVE: image-like innovation detects at the hidden support-failure step, not earlier",
        "UNAVAILABLE: calibrated road time, observation-aware h2-h3 performance, uncertainty, hazard and RUL",
        "REALITY GATE: synchronized image + FWD/strain + WIM + environment + maintenance, grouped by road/asset",
    ]
    evidence_colors = ["#19776C", "#9A6A00", "#B3432F", "#555555"]
    for offset, (line, color) in enumerate(zip(evidence_lines, evidence_colors)):
        ax.text(
            0.55,
            2.6 - 0.5 * offset,
            line,
            fontsize=11,
            color=color,
            fontweight="bold" if offset == 0 else "normal",
        )

    ax.text(
        14.55,
        0.24,
        "Status frozen 2026-07-24",
        ha="right",
        fontsize=8.5,
        color="#777777",
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=200, bbox_inches="tight", facecolor="white")
    fig.savefig(args.out.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
