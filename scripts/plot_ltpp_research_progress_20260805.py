#!/usr/bin/env python3
"""Render a provenance-bounded visual checkpoint for the LTPP research route."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "figures"
PNG_PATH = OUTPUT_DIR / "ltpp_freeze_select_progress_20260805.png"
PDF_PATH = OUTPUT_DIR / "ltpp_freeze_select_progress_20260805.pdf"

# Values are frozen from:
# - local_archive/.../ltpp_geoforecast_multisection_gate_v2_20260805/multisection_gate.json
# - docs/ltpp_geoforecast_blind_packet_handoff_20260805.md
# - local_archive/.../ltpp_06_1253_observation_state_gate_v1_20260805/result.json
SECTIONS = ["06-1253", "06-2041", "06-8149", "06-2647", "06-8150", "06-8201"]
SURVEYS = [8, 8, 6, 5, 5, 5]
FOLDS = ["F1", "F2", "F3", "F4"]
BMAE = {
    "Persistence": [0.217099, 0.244634, 0.240770, 0.250953],
    "Smooth trend": [0.220607, 0.269427, 0.250469, 0.258217],
    "Latent history": [0.217283, 0.232975, 0.218904, 0.229741],
}

INK = "#17211b"
MUTED = "#68736c"
PAPER = "#f5f1e8"
CARD = "#fffdf8"
GRID = "#d8d3c8"
GREEN = "#2a7f62"
AMBER = "#d08c32"
RED = "#c4513f"
BLUE = "#3976a8"
GREY = "#a7aca8"
OKABE = {"Persistence": "#0072B2", "Smooth trend": "#E69F00", "Latent history": "#009E73"}


def card(ax, title, subtitle=None):
    ax.set_facecolor(CARD)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.text(0.02, 1.05, title, transform=ax.transAxes, fontsize=13, fontweight="bold", color=INK)
    if subtitle:
        ax.text(0.02, 1.005, subtitle, transform=ax.transAxes, fontsize=8.5, color=MUTED)


def rounded_label(ax, x, y, width, text, color, status):
    patch = FancyBboxPatch(
        (x, y - 0.055), width, 0.11,
        boxstyle="round,pad=0.012,rounding_size=0.025",
        linewidth=0, facecolor=color, alpha=0.13,
    )
    ax.add_patch(patch)
    ax.text(x + 0.018, y, text, va="center", fontsize=9.2, color=INK, fontweight="semibold")
    ax.text(x + width - 0.018, y, status, va="center", ha="right", fontsize=8.5, color=color, fontweight="bold")


def draw_pipeline(ax):
    card(ax, "A  Evidence ladder", "What is complete, what is pending, and what remains blocked")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    rows = [
        (0.88, "1. Source + geometry/climate qualification", GREEN, "6 sections / 37 states"),
        (0.70, "2. Independent vector annotation", AMBER, "human 37/37 frozen; AI primary 30/37"),
        (0.52, "3. Pairing + adjudication", GREY, "NOT READY"),
        (0.34, "4. Unseen-section forecast gate", GREY, "BLOCKED BY LABELS"),
        (0.16, "5. Freeze-Then-Select / PIDL comparison", GREY, "DOWNSTREAM BLOCKED"),
    ]
    for y, text, color, status in rows:
        rounded_label(ax, 0.02, y, 0.96, text, color, status)
    ax.annotate("", xy=(0.5, 0.58), xytext=(0.5, 0.64), arrowprops=dict(arrowstyle="-|>", color=AMBER, lw=1.5))
    ax.text(0.5, 0.61, "current bottleneck", ha="center", va="center", fontsize=7.8, color=AMBER,
            bbox=dict(facecolor=CARD, edgecolor="none", pad=1.5))


def draw_coverage(ax):
    card(ax, "B  Qualified multisection inventory", "Climate-complete 0-50 ft survey states; labels are not yet complete")
    order = np.arange(len(SECTIONS))[::-1]
    bars = ax.barh(order, SURVEYS, color=BLUE, alpha=0.82, height=0.62)
    ax.set_yticks(order, SECTIONS)
    ax.set_xlim(0, 9)
    ax.set_xlabel("qualified survey states", fontsize=9, color=MUTED)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK, labelsize=8.5)
    for bar, count in zip(bars, SURVEYS):
        ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height() / 2, str(count), va="center",
                fontsize=9, color=INK, fontweight="bold")
    ax.text(0.98, 0.05, "TOTAL = 37", transform=ax.transAxes, ha="right", fontsize=10,
            color=BLUE, fontweight="bold")


def draw_fold_metrics(ax):
    card(ax, "C  Single-section rolling forecast evidence", "Balanced MAE; lower is better; complete future fields held out")
    x = np.arange(1, 5)
    markers = {"Persistence": "o", "Smooth trend": "s", "Latent history": "D"}
    for name, values in BMAE.items():
        ax.plot(x, values, color=OKABE[name], marker=markers[name], ms=5.5, lw=1.8, label=name)
    ax.set_xticks(x, FOLDS)
    ax.set_ylim(0.205, 0.278)
    ax.set_ylabel("balanced MAE", fontsize=9, color=MUTED)
    ax.grid(color=GRID, lw=0.8)
    ax.tick_params(colors=INK, labelsize=8.5)
    ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper left")
    ax.annotate("L wins 3/4 vs persistence\nbut misses the median 10% gate",
                xy=(4, BMAE["Latent history"][3]), xytext=(2.45, 0.267),
                arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.2),
                fontsize=8.2, color=INK, ha="left")


def draw_gate_scorecard(ax):
    card(ax, "D  Predeclared gate scorecard", "No threshold was relaxed after seeing the result")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    rows = [
        ("bMAE L vs persistence", 7.57, 10.0, False, "% improvement"),
        ("bMAE L vs smooth", 11.80, 10.0, True, "% improvement"),
        ("bCRPS L vs persistence", 8.21, 5.0, True, "% improvement"),
        ("bCRPS L vs smooth", 13.86, 5.0, True, "% improvement"),
        ("Minimum interval coverage", 68.90, 70.0, False, "% coverage"),
    ]
    y_positions = np.linspace(0.84, 0.20, len(rows))
    for y, (label, value, threshold, passed, unit) in zip(y_positions, rows):
        color = GREEN if passed else RED
        ax.text(0.02, y + 0.045, label, fontsize=8.7, color=INK, fontweight="semibold")
        ax.text(0.98, y + 0.045, "PASS" if passed else "FAIL", fontsize=8.2, ha="right",
                color=color, fontweight="bold")
        scale_max = max(value, threshold) * 1.25
        ax.barh(y, value / scale_max, left=0.02, height=0.052, color=color, alpha=0.82)
        threshold_x = 0.02 + 0.96 * threshold / scale_max
        ax.plot([threshold_x, threshold_x], [y - 0.035, y + 0.035], color=INK, lw=1.2)
        ax.text(0.02 + 0.96, y, f"{value:.2f} / gate {threshold:.0f} {unit}", va="center", ha="right",
                fontsize=7.6, color=MUTED)
    ax.text(0.02, 0.055, "FINAL: FAIL_L_NOT_QUALIFIED", fontsize=11, color=RED, fontweight="bold")
    ax.text(0.98, 0.055, "signal found != growth model qualified", fontsize=8.2, color=MUTED, ha="right")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.titleweight": "bold",
        "axes.labelcolor": INK,
        "text.color": INK,
        "figure.facecolor": PAPER,
        "savefig.facecolor": PAPER,
    })
    fig = plt.figure(figsize=(15.2, 9.4), constrained_layout=False)
    fig.patch.set_facecolor(PAPER)
    gs = fig.add_gridspec(2, 2, left=0.055, right=0.975, top=0.875, bottom=0.105, wspace=0.18, hspace=0.30)
    axes = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])]
    draw_pipeline(axes[0])
    draw_coverage(axes[1])
    draw_fold_metrics(axes[2])
    draw_gate_scorecard(axes[3])

    fig.text(0.055, 0.955, "Road-crack PDE discovery: evidence checkpoint", fontsize=22, fontweight="bold", color=INK)
    fig.text(0.055, 0.915,
             "The field-representation problem is isolated; cross-section labels, not another 06-1253 model, are now the critical path.",
             fontsize=11, color=MUTED)
    fig.text(0.055, 0.035,
             "Scope: LTPP California, 0-50 ft panels. Single-section labels are exploratory; qualified multisection assets are not yet a reviewed label benchmark.",
             fontsize=8.5, color=MUTED)
    fig.text(0.975, 0.035, "Frozen evidence snapshot: 2026-08-05", fontsize=8.5, color=MUTED, ha="right")

    fig.savefig(PNG_PATH, dpi=220, bbox_inches="tight")
    fig.savefig(PDF_PATH, bbox_inches="tight")
    print(PNG_PATH)
    print(PDF_PATH)


if __name__ == "__main__":
    main()
