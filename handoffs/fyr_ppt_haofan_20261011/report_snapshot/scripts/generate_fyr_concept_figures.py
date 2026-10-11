"""Generate conceptual FYR figures for the Overleaf thesis.

The figures in this script are schematics, not result plots. They support
Chapter 4 methodology claims and should not be read as quantitative evidence.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "Chapter4" / "Figs" / "PDF"
PNG_DIR = ROOT / "Chapter4" / "Figs" / "Raster"


INK = "#1F2933"
MUTED = "#52616B"
BLUE = "#2F6F9F"
TEAL = "#2A9D8F"
AMBER = "#D9902F"
RED = "#B24C4C"
GREEN = "#4F8A5B"
GREY = "#E8ECEF"
LIGHT_BLUE = "#EAF3FA"
LIGHT_TEAL = "#EAF8F5"
LIGHT_AMBER = "#FFF4E3"
LIGHT_RED = "#FBEAEA"
LIGHT_GREEN = "#EDF7EE"


def save(fig: plt.Figure, name: str) -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PDF_DIR / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(PNG_DIR / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def add_box(ax, xy, w, h, text, fc, ec=INK, fontsize=8.8, lw=1.1):
    patch = Rectangle(xy, w, h, facecolor=fc, edgecolor=ec, linewidth=lw)
    ax.add_patch(patch)
    ax.text(
        xy[0] + w / 2,
        xy[1] + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=INK,
        linespacing=1.2,
    )
    return patch


def arrow(ax, start, end, color=MUTED, lw=1.4, style="-|>", rad=0.0):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle=style,
            mutation_scale=12,
            linewidth=lw,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
        )
    )


def phase_field_variable_map():
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6.25)
    ax.axis("off")

    ax.text(0.2, 5.95, "Phase-field fatigue variables used for validation", fontsize=13.2, weight="bold", color=INK)
    ax.text(
        0.2,
        5.58,
        "Damage controls the elastic degradation $g(\\alpha)$; fatigue history is a separate accumulation state.",
        fontsize=10.5,
        color=MUTED,
    )

    add_box(ax, (0.35, 3.55), 1.55, 0.75, "Cyclic load\nand strain", LIGHT_BLUE)
    add_box(ax, (2.25, 3.55), 1.75, 0.75, "Raw tensile energy\n$\\psi^{+}$", LIGHT_BLUE)
    add_box(ax, (4.35, 4.65), 1.75, 0.75, "Fatigue history\n$\\bar{\\alpha}$", LIGHT_AMBER)
    add_box(ax, (4.35, 2.25), 1.75, 0.75, "Damage field\n$\\alpha$", LIGHT_TEAL)
    add_box(ax, (6.75, 4.65), 1.85, 0.75, "Fatigue degradation\nfrom $\\bar{\\alpha}$", LIGHT_AMBER)
    add_box(ax, (6.75, 2.25), 1.85, 0.75, "Elastic degradation\n$g(\\alpha)$", LIGHT_TEAL)
    add_box(ax, (6.75, 3.55), 1.85, 0.75, "Active driver\n$g(\\alpha)\\psi^{+}$", LIGHT_RED)
    add_box(ax, (9.35, 3.55), 1.85, 0.75, "Damage increment\n$\\Delta E_d$", LIGHT_AMBER)

    add_box(ax, (2.25, 0.85), 2.2, 0.8, "Scalar output\n$N_f$ / event cycle", "#F4F4F5", ec=MUTED)
    add_box(ax, (7.25, 0.85), 2.55, 0.8, "M2S target\nhidden mechanical state", "#F4F4F5", ec=MUTED)

    arrow(ax, (1.9, 3.93), (2.25, 3.93), BLUE)
    arrow(ax, (4.0, 4.05), (4.35, 5.02), AMBER)
    arrow(ax, (4.0, 3.78), (4.35, 2.62), TEAL)
    arrow(ax, (4.0, 3.93), (6.75, 3.93), BLUE)
    arrow(ax, (6.1, 5.02), (6.75, 5.02), AMBER)
    arrow(ax, (6.1, 2.62), (6.75, 2.62), TEAL)
    arrow(ax, (7.68, 3.0), (7.68, 3.55), TEAL)
    arrow(ax, (8.6, 3.93), (9.35, 3.93), RED)
    arrow(ax, (8.6, 5.02), (9.35, 4.3), AMBER)
    arrow(ax, (3.05, 3.55), (3.12, 1.65), MUTED, rad=0.2)
    arrow(ax, (7.68, 3.55), (8.45, 1.65), MUTED, rad=-0.2)

    ax.text(5.65, 1.9, "Field-level validation", ha="center", fontsize=10.5, color=INK)
    arrow(ax, (4.45, 1.25), (7.25, 1.25), MUTED)
    save(fig, "c4_phase_field_variable_map")


def sent_probe_zone_schematic():
    fig, ax = plt.subplots(figsize=(9.8, 5.35))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.25)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.text(0.1, 4.95, "Controlled SENT benchmark and comparison regions", fontsize=13.5, weight="bold", color=INK)
    ax.text(0.1, 4.62, "Schematic only: dimensions are not to scale.", fontsize=9.8, color=MUTED)

    domain = Rectangle((1.0, 0.7), 7.8, 3.1, facecolor="#FAFAFA", edgecolor=INK, linewidth=1.4)
    ax.add_patch(domain)

    # Notch and expected crack path.
    ax.plot([1.0, 2.3], [2.25, 2.25], color=INK, linewidth=3)
    ax.plot([2.3, 7.9], [2.25, 2.25], color=RED, linewidth=1.5, linestyle="--", alpha=0.75)
    ax.text(1.05, 2.47, "initial notch", fontsize=9.5, color=INK)

    # Boundary conditions and loading.
    ax.plot([1.0, 8.8], [0.7, 0.7], color=BLUE, linewidth=2.3)
    ax.text(4.9, 0.35, "bottom support / displacement constraint", ha="center", fontsize=9.5, color=BLUE)
    for x in [3.0, 4.5, 6.0, 7.5]:
        arrow(ax, (x, 4.28), (x, 3.82), BLUE, lw=1.6)
    ax.text(5.25, 4.36, r"cyclic displacement $U_{\max}$, $R=0$", ha="center", fontsize=10, color=BLUE)

    # Probe points and zones.
    probe_x = [2.6, 3.2, 3.8, 4.4, 5.0]
    for x in probe_x:
        ax.add_patch(Circle((x, 2.25), 0.07, facecolor=AMBER, edgecolor=INK, linewidth=0.7))
    ax.text(3.75, 2.55, "common probes", ha="center", fontsize=9.5, color=AMBER)

    ax.add_patch(Circle((2.3, 2.25), 0.55, facecolor="none", edgecolor=RED, linewidth=1.5))
    ax.text(2.65, 1.45, "crack-tip zone", fontsize=9.5, color=RED)

    ax.add_patch(Rectangle((8.35, 0.75), 0.35, 3.0, facecolor=LIGHT_RED, edgecolor=RED, linewidth=1.2))
    ax.text(8.55, 2.25, "event\nregion", ha="center", va="center", fontsize=8.5, color=RED, rotation=90)

    ax.add_patch(Rectangle((1.05, 3.52), 7.7, 0.22, facecolor=LIGHT_GREEN, edgecolor=GREEN, linewidth=1.0))
    ax.add_patch(Rectangle((1.05, 0.82), 7.7, 0.22, facecolor=LIGHT_GREEN, edgecolor=GREEN, linewidth=1.0))
    ax.text(8.95, 3.58, "guardrail\nregions", fontsize=9, color=GREEN, va="center")

    ax.text(
        5.15,
        1.22,
        r"Compare $\alpha$, $\bar{\alpha}$, $\psi^{+}$, active driver and $\Delta E_d$",
        ha="center",
        fontsize=10,
        color=MUTED,
    )

    save(fig, "c4_sent_probe_zone_schematic")


def validation_ladder():
    fig, ax = plt.subplots(figsize=(11.2, 5.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")

    ax.text(0.25, 5.55, "Validation ladder for fracture-aware PIDL", fontsize=14, weight="bold", color=INK)
    ax.text(
        0.25,
        5.2,
        "Scalar fatigue-life feasibility is an entry gate; field credibility controls whether M2S interpretation is trustworthy.",
        fontsize=10.5,
        color=MUTED,
    )

    stages = [
        ("1", "Scalar gate", "$N_f$ / event timing", LIGHT_BLUE, BLUE),
        ("2", "Field gate", "$\\bar{\\alpha}$, active driver,\n$\\Delta E_d$, morphology", LIGHT_RED, RED),
        ("3", "Diagnostics", "alignment, cadence,\nboundary, sampling,\narchitecture", LIGHT_AMBER, AMBER),
        ("4", "M2S rung", "held-out trajectories,\nsparse/noisy sensors", LIGHT_TEAL, TEAL),
        ("5", "Pavement route", "PF-CZM concrete\nand road-DT feasibility", LIGHT_GREEN, GREEN),
    ]

    x0 = 0.55
    w = 2.0
    gap = 0.25
    y = 3.15
    h = 1.25
    centers = []
    for i, (num, title, detail, fc, col) in enumerate(stages):
        x = x0 + i * (w + gap)
        centers.append((x + w / 2, y + h / 2))
        add_box(ax, (x, y), w, h, f"{num}. {title}\n{detail}", fc, ec=col, fontsize=8.2, lw=1.3)
        if i < len(stages) - 1:
            arrow(ax, (x + w, y + h / 2), (x + w + gap, y + h / 2), MUTED, lw=1.2)

    # Status band.
    add_box(ax, (0.75, 1.15), 2.7, 0.85, "Feasibility evidence\nnot final closure", "#F4F4F5", ec=BLUE, fontsize=9.5)
    add_box(ax, (4.05, 1.15), 2.7, 0.85, "Current blocker:\nfield gap unresolved", LIGHT_RED, ec=RED, fontsize=9.5)
    add_box(ax, (7.35, 1.15), 3.35, 0.85, "Future interpretation is conditional\non forward field credibility", "#F4F4F5", ec=MUTED, fontsize=9.5)

    arrow(ax, (1.65, 3.15), (2.1, 2.0), BLUE, rad=-0.1)
    arrow(ax, (3.95, 3.15), (5.4, 2.0), RED, rad=0.05)
    arrow(ax, (8.4, 3.15), (9.0, 2.0), MUTED, rad=0.12)

    ax.text(
        4.75,
        0.42,
        "Core message: a model can look useful at the scalar gate while still failing the field gate.",
        ha="center",
        fontsize=10.5,
        color=INK,
        weight="bold",
    )

    save(fig, "c4_validation_ladder_scalar_field_decoupling")


def main() -> None:
    phase_field_variable_map()
    sent_probe_zone_schematic()
    validation_ladder()


if __name__ == "__main__":
    main()
