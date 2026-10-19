#!/usr/bin/env python3
"""Summarise and plot the stopped S09-E013 zero-step admission."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ARM_GLOBAL = "G25_global_ranking_replay"
ARM_LOCAL = "L25_local_support_ranking_beta0p25"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(args.receipt.read_text())
    audit = payload["audit"]
    rows = audit["records"]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    global_margin = np.asarray([row["initial_global_margin"] for row in rows])
    local_margin = np.asarray([row["initial_local_margin"] for row in rows])
    global_win = global_margin > 0
    local_win = local_margin > 0
    global_after_g = global_margin + np.asarray([
        row["arms"][ARM_GLOBAL]["predicted_adamw_global_margin_change"]
        for row in rows
    ])
    global_after_l = global_margin + np.asarray([
        row["arms"][ARM_LOCAL]["predicted_adamw_global_margin_change"]
        for row in rows
    ])

    summary = {
        "schema_version": "s09-e013-zero-step-analysis-v2-pair-specific",
        "assay_type": "PAIR_SPECIFIC_DIAGONAL_DIRECTIONAL_ASSAY",
        "shared_parameter_direction_across_pairs": False,
        "source_receipt": str(args.receipt.resolve()),
        "source_receipt_sha256": sha256(args.receipt),
        "status": audit["status"],
        "optimizer_steps_performed": payload["optimizer_steps_performed"],
        "pair_count": len(rows),
        "initial_global_win_count": int(global_win.sum()),
        "initial_global_loss_count": int((~global_win).sum()),
        "initial_local_win_count": int(local_win.sum()),
        "initial_local_loss_count": int((~local_win).sum()),
        "opposite_global_and_local_sign_count": int((global_win != local_win).sum()),
        "pearson_global_vs_local_margin": float(np.corrcoef(global_margin, local_margin)[0, 1]),
        "linearised_global_win_count_after_global_arm_step": int((global_after_g > 0).sum()),
        "linearised_global_win_count_after_local_arm_step": int((global_after_l > 0).sum()),
        "local_arm_flips_initial_global_wins_to_losses": int(
            np.logical_and(global_win, global_after_l <= 0).sum()
        ),
        "local_arm_repairs_initial_global_losses": int(
            np.logical_and(~global_win, global_after_l > 0).sum()
        ),
        "global_arm_flips_initial_global_wins_to_losses": int(
            np.logical_and(global_win, global_after_g <= 0).sum()
        ),
        "global_arm_repairs_initial_global_losses": int(
            np.logical_and(~global_win, global_after_g > 0).sum()
        ),
        "interpretation_boundary": (
            "Each row uses its own pair-specific exact next-AdamW displacement. "
            "Counts are diagonal tallies, not one shared update. No optimizer step "
            "or post-step forward evaluation was performed."
        ),
    }
    summary_path = args.output_dir / "zero_step_analysis.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    scale = 1e6
    colors = np.where(global_win, "#2a6f97", "#d97706")
    fig, axes = plt.subplots(1, 3, figsize=(15.2, 4.8), constrained_layout=True)

    ax = axes[0]
    ax.scatter(global_margin * scale, local_margin * scale, c=colors, s=52,
               edgecolor="white", linewidth=0.7, alpha=0.92)
    ax.axhline(0, color="#6b7280", linewidth=0.9)
    ax.axvline(0, color="#6b7280", linewidth=0.9)
    ax.set_xlabel(r"Initial global amplitude margin ($\times 10^{-6}$)")
    ax.set_ylabel(r"Initial local-support margin ($\times 10^{-6}$)")
    ax.set_title("A  B25 predictions disagree on 25/25 pairs", loc="left", fontweight="bold")
    ax.text(0.03, 0.03, f"Pearson r = {summary['pearson_global_vs_local_margin']:.3f}",
            transform=ax.transAxes, fontsize=10,
            bbox={"facecolor": "white", "edgecolor": "#d1d5db", "alpha": 0.9})

    ax = axes[1]
    ax.scatter(global_margin * scale, global_after_l * scale, c=colors, s=52,
               edgecolor="white", linewidth=0.7, alpha=0.92)
    bounds = np.asarray([global_margin.min(), global_margin.max(),
                         global_after_l.min(), global_after_l.max()]) * scale
    lo, hi = float(bounds.min()), float(bounds.max())
    pad = 0.08 * max(hi - lo, 1e-12)
    ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], "--", color="#9ca3af", linewidth=1)
    ax.axhline(0, color="#6b7280", linewidth=0.9)
    ax.axvline(0, color="#6b7280", linewidth=0.9)
    ax.set_xlim(lo - pad, hi + pad)
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_xlabel(r"Initial global margin ($\times 10^{-6}$)")
    ax.set_ylabel(r"Linearised margin after one L25 step ($\times 10^{-6}$)")
    ax.set_title("B  Pair-own L25 directions regress global rows", loc="left", fontweight="bold")
    ax.text(0.03, 0.03, "15/17 protected wins flip\n0/8 losses are repaired",
            transform=ax.transAxes, fontsize=10,
            bbox={"facecolor": "white", "edgecolor": "#d1d5db", "alpha": 0.9})

    ax = axes[2]
    values = [int(global_win.sum()), int((global_after_g > 0).sum()),
              int((global_after_l > 0).sum())]
    labels = ["Initial\nB25", "Pair-own G25\n(diagonal)", "Pair-own L25\n(diagonal)"]
    bars = ax.bar(labels, values, color=["#64748b", "#2a9d8f", "#d97706"], width=0.65)
    ax.axhline(17, color="#64748b", linestyle="--", linewidth=1)
    ax.set_ylim(0, 26)
    ax.set_ylabel("Global-amplitude WIN pairs (of 25)")
    ax.set_title("C  Pair-specific next-step tally", loc="left", fontweight="bold")
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.5, str(value),
                ha="center", va="bottom", fontweight="bold")
    ax.text(0.5, -0.22, "25 different hypothetical updates; zero optimiser steps",
            transform=ax.transAxes, ha="center", fontsize=10, color="#374151")

    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="both", color="#e5e7eb", linewidth=0.65, alpha=0.75)
        ax.set_axisbelow(True)

    fig.suptitle(
        "S09-E013 stopped before training: pair-specific directions conflict",
        fontsize=15, fontweight="bold",
    )
    figure_path = args.output_dir / "zero_step_global_local_conflict.png"
    fig.savefig(figure_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps({
        "figure": str(figure_path),
        "summary": str(summary_path),
        "summary_values": summary,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
