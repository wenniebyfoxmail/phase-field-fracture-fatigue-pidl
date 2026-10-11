"""Generate clean Chapter 2 schematics for the FYR thesis.

These figures are original synthesis schematics. They summarise categories
supported by the cited literature, but they do not reproduce source figures.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import fill

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "Chapter2" / "Figs" / "PDF"
PNG_DIR = ROOT / "Chapter2" / "Figs" / "Raster"


INK = "#202124"
MUTED = "#5F6368"
LIGHT = "#F8F9FA"
GRID = "#DADCE0"
BLUE = "#2D5F8B"
GREEN = "#496D4B"
AMBER = "#9C6B1C"
RED = "#9A3B3B"
TEAL = "#168EA0"
PURPLE = "#5B4B8A"


def save(fig: plt.Figure, name: str) -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PDF_DIR / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(PNG_DIR / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def setup_axes(fig_w=7.2, fig_h=4.6):
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, fc="white", ec=INK, lw=0.9, fs=8.3, color=INK):
    rect = Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, linewidth=lw)
    ax.add_patch(rect)
    ax.text(
        x + w / 2,
        y + h / 2,
        fill(text, width=max(10, int(w * 90))),
        ha="center",
        va="center",
        fontsize=fs,
        color=color,
        linespacing=1.2,
    )
    return rect


def arrow(ax, start, end, color=MUTED, lw=1.0, ms=10):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=ms,
            linewidth=lw,
            color=color,
            shrinkA=1,
            shrinkB=1,
        )
    )


def draw_crack_mask(ax, x, y, w, h):
    ax.add_patch(Rectangle((x, y), w, h, facecolor="#F0F2F3", edgecolor=GRID, linewidth=0.6))
    pts = [
        (x + 0.15 * w, y + 0.66 * h),
        (x + 0.30 * w, y + 0.58 * h),
        (x + 0.43 * w, y + 0.62 * h),
        (x + 0.55 * w, y + 0.48 * h),
        (x + 0.72 * w, y + 0.43 * h),
        (x + 0.88 * w, y + 0.35 * h),
    ]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=INK, linewidth=1.4)
    ax.plot([x + 0.42 * w, x + 0.36 * w], [y + 0.61 * h, y + 0.75 * h], color=INK, linewidth=0.8)
    ax.plot([x + 0.55 * w, x + 0.62 * w], [y + 0.48 * h, y + 0.64 * h], color=INK, linewidth=0.8)


def draw_surface_profile(ax, x, y, w, h):
    ax.add_patch(Rectangle((x, y), w, h, facecolor="white", edgecolor=GRID, linewidth=0.6))
    xs = [x + i * w / 80 for i in range(81)]
    ys = []
    for i, xx in enumerate(xs):
        base = y + 0.58 * h
        dip = -0.23 * h if 35 <= i <= 42 else 0
        rut = -0.08 * h if 58 <= i <= 67 else 0
        ys.append(base + dip + rut + 0.018 * h * ((i % 7) - 3) / 3)
    ax.plot(xs, ys, color=TEAL, linewidth=1.2)
    ax.text(x + 0.5 * w, y + 0.17 * h, "range profile", ha="center", va="center", fontsize=6.5, color=MUTED)


def draw_deflection(ax, x, y, w, h):
    ax.add_patch(Rectangle((x, y), w, h, facecolor="white", edgecolor=GRID, linewidth=0.6))
    xs = [x + 0.08 * w + i * 0.84 * w / 80 for i in range(81)]
    ys = [y + 0.72 * h - 0.38 * h * (1 - abs((i - 40) / 40) ** 1.8) for i in range(81)]
    ax.plot(xs, ys, color=AMBER, linewidth=1.2)
    ax.add_patch(FancyArrowPatch((x + 0.5 * w, y + 0.93 * h), (x + 0.5 * w, y + 0.70 * h),
                                 arrowstyle="-|>", mutation_scale=8, linewidth=0.8, color=RED))
    ax.text(x + 0.5 * w, y + 0.16 * h, "deflection response", ha="center", va="center", fontsize=6.5, color=MUTED)


def draw_road_patch(ax, x, y, w, h, crack_color=INK, mask=False, bbox=False):
    ax.add_patch(Rectangle((x, y), w, h, facecolor="#ECEFF1", edgecolor=GRID, linewidth=0.7))
    for i in range(7):
        yy = y + (0.12 + i * 0.12) * h
        ax.plot([x + 0.05 * w, x + 0.95 * w], [yy, yy + 0.02 * h], color="#D5D9DC", linewidth=0.5)

    pts = [
        (x + 0.14 * w, y + 0.68 * h),
        (x + 0.30 * w, y + 0.58 * h),
        (x + 0.42 * w, y + 0.62 * h),
        (x + 0.55 * w, y + 0.48 * h),
        (x + 0.72 * w, y + 0.40 * h),
        (x + 0.88 * w, y + 0.32 * h),
    ]

    if mask:
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=RED, linewidth=6.5, alpha=0.25, solid_capstyle="round")
        ax.plot([x + 0.42 * w, x + 0.34 * w], [y + 0.62 * h, y + 0.77 * h], color=RED, linewidth=4.0, alpha=0.22, solid_capstyle="round")
        ax.plot([x + 0.55 * w, x + 0.64 * w], [y + 0.48 * h, y + 0.66 * h], color=RED, linewidth=4.0, alpha=0.22, solid_capstyle="round")

    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=crack_color, linewidth=1.5, solid_capstyle="round")
    ax.plot([x + 0.42 * w, x + 0.34 * w], [y + 0.62 * h, y + 0.77 * h], color=crack_color, linewidth=0.9)
    ax.plot([x + 0.55 * w, x + 0.64 * w], [y + 0.48 * h, y + 0.66 * h], color=crack_color, linewidth=0.9)

    if bbox:
        ax.add_patch(Rectangle((x + 0.09 * w, y + 0.23 * h), 0.84 * w, 0.55 * h, facecolor="none", edgecolor=GREEN, linewidth=1.5))


def figure_image_detection_segmentation():
    fig, ax = setup_axes(7.4, 3.8)
    ax.text(0.02, 0.96, "Image-based crack tasks and outputs", ha="left", va="top", fontsize=11.5, weight="bold", color=INK)
    ax.text(
        0.02,
        0.885,
        "Detection and segmentation use the same visual observation but return different levels of crack information.",
        ha="left",
        va="top",
        fontsize=8.3,
        color=MUTED,
    )

    panels = [
        ("Input pavement image", "visible crack texture", 0.04, None),
        ("Classification", "crack present / absent", 0.29, None),
        ("Detection", "bounding box around crack", 0.54, "bbox"),
        ("Segmentation", "pixel-level crack mask", 0.79, "mask"),
    ]

    for title, subtitle, x, mode in panels:
        ax.text(x + 0.08, 0.74, title, ha="center", va="center", fontsize=8.2, weight="bold", color=INK)
        ax.text(x + 0.08, 0.69, subtitle, ha="center", va="center", fontsize=6.9, color=MUTED)
        if mode is None:
            draw_road_patch(ax, x, 0.39, 0.16, 0.21)
        elif mode == "bbox":
            draw_road_patch(ax, x, 0.39, 0.16, 0.21, bbox=True)
        else:
            draw_road_patch(ax, x, 0.39, 0.16, 0.21, mask=True)

    box(ax, 0.31, 0.18, 0.14, 0.08, "image-level label", fc="#F4F7FB", ec=BLUE, lw=0.9, fs=7.1)
    box(ax, 0.56, 0.18, 0.14, 0.08, "object location", fc="#F4FBF7", ec=GREEN, lw=0.9, fs=7.1)
    box(ax, 0.81, 0.18, 0.14, 0.08, "crack geometry", fc="#FFF4F4", ec=RED, lw=0.9, fs=7.1)

    for start_x, end_x in [(0.21, 0.28), (0.46, 0.53), (0.71, 0.78)]:
        arrow(ax, (start_x, 0.50), (end_x, 0.50), color=MUTED, lw=1.0, ms=9)

    ax.text(
        0.50,
        0.07,
        "A segmentation mask carries more geometric information than an image label or bounding box, but it is still a surface observation.",
        ha="center",
        va="center",
        fontsize=7.5,
        color=INK,
    )
    save(fig, "c2_image_detection_segmentation_outputs")


def figure_inspection_methods():
    fig, ax = setup_axes(7.4, 4.8)
    ax.text(0.02, 0.97, "Inspection methods and outputs", ha="left", va="top", fontsize=11.5, weight="bold", color=INK)
    ax.text(
        0.02,
        0.91,
        "Inspection provides observed condition information, not a complete fracture-state field.",
        ha="left",
        va="top",
        fontsize=8.4,
        color=MUTED,
    )

    headers = [("Method family", 0.03, 0.77, 0.22), ("Measured information", 0.32, 0.77, 0.27), ("Output for prediction", 0.68, 0.77, 0.27)]
    for text, x, y, w in headers:
        box(ax, x, y, w, 0.075, text, fc="#EDEFF2", ec=GRID, lw=0.8, fs=8.0)

    rows = [
        ("Manual / condition survey", "Distress type, severity, extent, PCI", "Condition score or distress class", BLUE, "score"),
        ("Image-based inspection", "Classification, detection, segmentation", "Crack location and crack mask", GREEN, "mask"),
        ("3D surface sensing", "Laser profile, rutting, texture, crack width", "Surface geometry and discontinuities", TEAL, "profile"),
        ("Structural / subsurface", "FWD, TSD, GPR response and layer indicators", "Stiffness and layer-condition proxies", AMBER, "deflection"),
    ]

    y0 = 0.61
    for i, (method, measured, output, colour, icon) in enumerate(rows):
        y = y0 - i * 0.15
        h = 0.115
        box(ax, 0.03, y, 0.22, h, method, fc="white", ec=colour, lw=1.0, fs=7.8, color=INK)
        box(ax, 0.32, y, 0.27, h, measured, fc=LIGHT, ec=GRID, lw=0.8, fs=7.5, color=INK)
        ax.add_patch(Rectangle((0.68, y), 0.27, h, facecolor="#FFFFFF", edgecolor=GRID, linewidth=0.8))
        ax.text(
            0.815,
            y + 0.082,
            fill(output, width=23),
            ha="center",
            va="center",
            fontsize=7.35,
            color=INK,
            linespacing=1.1,
        )
        arrow(ax, (0.255, y + h / 2), (0.315, y + h / 2), color=colour, lw=1.0, ms=8)
        arrow(ax, (0.595, y + h / 2), (0.675, y + h / 2), color=colour, lw=1.0, ms=8)

        if icon == "score":
            for j, val in enumerate([0.80, 0.61, 0.43]):
                ax.add_patch(Rectangle((0.712, y + 0.018 + j * 0.015), 0.030, 0.007, facecolor=colour, edgecolor=colour))
                ax.plot([0.750, 0.900], [y + 0.0215 + j * 0.015] * 2, color=GRID, linewidth=0.85)
                ax.add_patch(Circle((0.750 + val * 0.15, y + 0.0215 + j * 0.015), 0.004, facecolor=INK, edgecolor=INK))
        elif icon == "mask":
            draw_crack_mask(ax, 0.722, y + 0.012, 0.18, 0.052)
        elif icon == "profile":
            draw_surface_profile(ax, 0.722, y + 0.010, 0.18, 0.054)
        else:
            draw_deflection(ax, 0.722, y + 0.010, 0.18, 0.054)

    box(ax, 0.22, 0.035, 0.56, 0.075, "Prediction still needs loading, material condition and hidden damage evolution.", fc="#FFF8E8", ec=AMBER, lw=0.9, fs=8.2)
    save(fig, "c2_inspection_methods_outputs")


def figure_prediction_levels():
    fig, ax = setup_axes(7.4, 4.35)
    ax.text(0.02, 0.96, "Prediction methods by physical detail", ha="left", va="top", fontsize=11.5, weight="bold", color=INK)
    ax.text(
        0.02,
        0.895,
        "The prediction target changes from section-level indicators to local fracture-state fields.",
        ha="left",
        va="top",
        fontsize=8.4,
        color=MUTED,
    )

    levels = [
        ("Empirical / statistical", "condition state, PCI, IRI, survival or transition probability", BLUE),
        ("Data-driven", "cracking amount, RUL, distress category or future index", GREEN),
        ("Physics-informed pavement", "performance indicators plus engineering constraints", AMBER),
        ("Physics-based fracture state", "damage, stress, energy, history and crack-driving force", RED),
    ]

    for i, (title, output, colour) in enumerate(levels):
        x = 0.08 + i * 0.225
        y = 0.20 + i * 0.085
        box(ax, x, y, 0.18, 0.22, title + "\n\n" + output, fc="white", ec=colour, lw=1.2, fs=6.7)
        if i < len(levels) - 1:
            arrow(ax, (x + 0.18, y + 0.12), (x + 0.222, y + 0.14), color=MUTED, lw=1.0, ms=9)

    ax.plot([0.07, 0.95], [0.12, 0.12], color=INK, linewidth=0.9)
    arrow(ax, (0.07, 0.12), (0.95, 0.12), color=INK, lw=0.9, ms=10)
    ax.text(0.51, 0.055, "Increasing physical detail and hidden-state demand", ha="center", va="center", fontsize=8.0, color=INK)

    ax.plot([0.055, 0.055], [0.17, 0.74], color=INK, linewidth=0.9)
    arrow(ax, (0.055, 0.17), (0.055, 0.74), color=INK, lw=0.9, ms=10)
    ax.text(0.022, 0.455, "Local mechanism", ha="center", va="center", rotation=90, fontsize=8.0, color=INK)

    save(fig, "c2_prediction_method_levels")


def draw_damage_field(ax, x, y, w, h):
    ax.add_patch(Rectangle((x, y), w, h, facecolor="#F8F3EE", edgecolor=GRID, linewidth=0.6))
    for i, alpha in enumerate([0.22, 0.32, 0.44, 0.58, 0.75]):
        ax.add_patch(Circle((x + (0.28 + i * 0.10) * w, y + (0.61 - i * 0.04) * h), 0.075 * w, facecolor=RED, edgecolor="none", alpha=alpha))
    ax.plot([x + 0.16 * w, x + 0.78 * w], [y + 0.63 * h, y + 0.45 * h], color=INK, linewidth=1.2)
    ax.text(x + 0.51 * w, y + 0.17 * h, "damage field d(x)", ha="center", va="center", fontsize=6.7, color=MUTED)


def figure_hidden_state_bridge():
    fig, ax = setup_axes(7.4, 4.5)
    ax.text(0.02, 0.96, "From inspection outputs to fracture-state prediction", ha="left", va="top", fontsize=11.5, weight="bold", color=INK)
    ax.text(
        0.02,
        0.895,
        "Inspection gives partial observations. Physics-based prediction requires hidden state variables.",
        ha="left",
        va="top",
        fontsize=8.4,
        color=MUTED,
    )

    box(ax, 0.04, 0.53, 0.24, 0.25, "Observed inspection outputs\n\ncrack mask\ngeometry\nsurface profile\nstructural proxies", fc="#F4F7FB", ec=BLUE, lw=1.1, fs=7.8)
    draw_crack_mask(ax, 0.07, 0.30, 0.18, 0.14)

    box(ax, 0.38, 0.53, 0.24, 0.25, "Hidden fracture state\n\ndamage d\nstress / strain\nstrain energy\nhistory variable\nactive driver", fc="#FFF8E8", ec=AMBER, lw=1.1, fs=7.8)
    draw_damage_field(ax, 0.41, 0.30, 0.18, 0.14)

    box(ax, 0.72, 0.53, 0.24, 0.25, "Prediction outputs\n\nfuture crack field\ncrack-growth path\nlocal reliability\nmaintenance evidence", fc="#F4FBF7", ec=GREEN, lw=1.1, fs=7.8)
    ax.add_patch(Rectangle((0.755, 0.30), 0.16, 0.14, facecolor="#F0F2F3", edgecolor=GRID, linewidth=0.6))
    ax.plot([0.775, 0.86, 0.895], [0.390, 0.350, 0.315], color=INK, linewidth=1.3)
    ax.plot([0.83, 0.89], [0.382, 0.410], color=INK, linewidth=0.75)
    ax.plot([0.86, 0.89], [0.350, 0.270], color=INK, linewidth=0.75)
    ax.text(0.835, 0.255, "future state", ha="center", va="center", fontsize=6.7, color=MUTED)

    arrow(ax, (0.29, 0.63), (0.37, 0.63), color=MUTED, lw=1.1, ms=10)
    arrow(ax, (0.63, 0.63), (0.71, 0.63), color=MUTED, lw=1.1, ms=10)
    ax.text(0.33, 0.69, "inference", ha="center", va="center", fontsize=7.5, color=MUTED)
    ax.text(0.67, 0.69, "evolution", ha="center", va="center", fontsize=7.5, color=MUTED)

    box(ax, 0.24, 0.10, 0.52, 0.10, "The report tests this middle link first using controlled phase-field simulations and PIDL.", fc="white", ec=PURPLE, lw=1.0, fs=8.0)
    save(fig, "c2_inspection_to_hidden_state_bridge")


def main() -> None:
    figure_inspection_methods()
    figure_image_detection_segmentation()
    figure_prediction_levels()
    figure_hidden_state_bridge()


if __name__ == "__main__":
    main()
