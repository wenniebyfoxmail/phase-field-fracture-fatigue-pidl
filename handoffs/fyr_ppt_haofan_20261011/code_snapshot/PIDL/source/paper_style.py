"""
paper_style.py — Canonical figure style for Ch2 paper (and future chapters).

Palette: ggsci Lancet (biomedical journal) — 9 distinct colors, colorblind-safe.
Typography: sans-serif for axis labels/legend; math left to LaTeX at typesetting.
Layout: compact (CMAME double-column); no top/right spines; light inner ticks.

Method → color binding is CANONICAL across all Ch2 figures — never remap
per-figure; same method = same color everywhere.

Usage:
    from paper_style import apply_style, method_style, FIGSIZE_1COL
    apply_style()
    fig, ax = plt.subplots(figsize=FIGSIZE_1COL)
    ax.plot(x, y, **method_style("FEM", bw_safe=True, n_methods=3))
    ax.plot(x, y, **method_style("Baseline", bw_safe=True, n_methods=3))

B&W compatibility rule (automatic via n_methods arg):
  ≤ 4 methods on plot → linestyle + marker redundancy (B&W safe)
  ≥ 5 methods        → color only (B&W redundancy too noisy); use color grouping
"""
from __future__ import annotations
from typing import Optional

import matplotlib as mpl
import matplotlib.pyplot as plt


# ───────────────────────────────────────────────────────────────────────────
# ggsci Lancet palette — base colors
# ───────────────────────────────────────────────────────────────────────────
LANCET_PALETTE = {
    "deep_blue":   "#00468B",
    "red":         "#ED0000",
    "green":       "#42B540",
    "teal":        "#0099B4",
    "purple":      "#925E9F",
    "peach":       "#FDAF91",
    "dark_red":    "#AD002A",
    "gray":        "#ADB6B6",
    "black":       "#1B1919",
}


# ───────────────────────────────────────────────────────────────────────────
# Method → color binding (CANONICAL — do not change per figure)
# ───────────────────────────────────────────────────────────────────────────
METHOD_COLORS = {
    # Reference
    "FEM":             LANCET_PALETTE["black"],       # always black-ish
    "Baseline":        LANCET_PALETTE["deep_blue"],   # PIDL anchor

    # Input-enrichment family (Dir 4, Dir 2.1)
    "Williams":        LANCET_PALETTE["peach"],
    "Fourier":         LANCET_PALETTE["green"],

    # Output-enrichment (Dir 5) — primary method under test
    "Enriched":        LANCET_PALETTE["red"],

    # Fatigue-modulation family (Dir 6.1, Dir 6.2)
    "spAlphaT_narrow": LANCET_PALETTE["purple"],
    "spAlphaT_broad":  LANCET_PALETTE["gray"],
    "Golahmar":        LANCET_PALETTE["dark_red"],

    # Mechanism proof (supplementary, hack — not proposed method)
    "E2_psi_hack":     LANCET_PALETTE["teal"],
}


# ───────────────────────────────────────────────────────────────────────────
# B&W redundancy maps — only applied when n_methods ≤ _BW_THRESHOLD
# ───────────────────────────────────────────────────────────────────────────
METHOD_LINESTYLES_BW = {
    "FEM":             "-",
    "Baseline":        "--",
    "Enriched":        "-.",
    "E2_psi_hack":     ":",
    "Williams":        (0, (3, 1, 1, 1)),   # dash-dot-dot
    "Fourier":         (0, (5, 2)),         # long dash
    "spAlphaT_narrow": (0, (1, 1)),         # dense dots
    "Golahmar":        (0, (4, 2, 1, 2)),   # mixed
}

METHOD_MARKERS_BW = {
    "FEM":             "o",
    "Baseline":        "s",
    "Enriched":        "^",
    "E2_psi_hack":     "D",
    "Williams":        "v",
    "Fourier":         "p",
    "spAlphaT_narrow": "P",
    "Golahmar":        "X",
}

_BW_THRESHOLD = 4


# ───────────────────────────────────────────────────────────────────────────
# Figure sizes (CMAME double-column; override per-journal as needed)
# ───────────────────────────────────────────────────────────────────────────
FIGSIZE_1COL    = (3.5, 2.6)     # single column
FIGSIZE_1_5COL  = (5.0, 3.2)     # 1.5-column (for wider hero figs)
FIGSIZE_2COL    = (7.2, 4.0)     # double column, multi-panel
FIGSIZE_SQUARE  = (3.2, 3.2)     # square single column
FIGSIZE_HERO_2x2 = (6.5, 5.0)    # 2x2 hero grid, double column

DPI_PRINT       = 300
FONT_SIZE       = 9              # CMAME body 10pt minus 1
FONT_SIZE_SMALL = 7              # tick labels, minor annotations
LINEWIDTH       = 1.4
MARKERSIZE      = 4


# ───────────────────────────────────────────────────────────────────────────
# Style application
# ───────────────────────────────────────────────────────────────────────────
def apply_style() -> None:
    """Apply canonical Ch2 paper style to matplotlib rcParams.

    Call once at the top of any figure-generating script, before creating
    figures. All downstream plt.subplots / ax.plot calls will inherit.
    """
    mpl.rcParams.update({
        # Typography
        "font.family":      "sans-serif",
        "font.sans-serif":  ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size":        FONT_SIZE,
        "axes.labelsize":   FONT_SIZE,
        "axes.titlesize":   FONT_SIZE,
        "xtick.labelsize":  FONT_SIZE_SMALL,
        "ytick.labelsize":  FONT_SIZE_SMALL,
        "legend.fontsize":  FONT_SIZE_SMALL,

        # Figure output
        "figure.dpi":       100,           # on-screen preview
        "savefig.dpi":      DPI_PRINT,
        "savefig.bbox":     "tight",
        "savefig.pad_inches": 0.02,

        # Axes: remove top+right spines (clean look), light inner ticks
        "axes.spines.top":     False,
        "axes.spines.right":   False,
        "axes.linewidth":      0.6,
        "axes.grid":           True,
        "grid.alpha":          0.3,
        "grid.linestyle":      "-",
        "grid.linewidth":      0.3,

        # Ticks
        "xtick.direction":     "in",
        "ytick.direction":     "in",
        "xtick.major.width":   0.6,
        "ytick.major.width":   0.6,
        "xtick.minor.visible": False,
        "ytick.minor.visible": False,

        # Lines / markers
        "lines.linewidth":   LINEWIDTH,
        "lines.markersize":  MARKERSIZE,

        # Legend
        "legend.frameon":    False,
        "legend.borderpad":  0.3,
        "legend.handlelength": 1.8,
    })


def method_style(method: str,
                 bw_safe: bool = False,
                 n_methods: Optional[int] = None,
                 use_marker: bool = False) -> dict:
    """Return matplotlib kwargs dict for a named method.

    Args:
        method: name (must be in METHOD_COLORS; unknown → falls back to gray)
        bw_safe: request B&W-compatible linestyle/marker; auto-disabled if
                 n_methods > _BW_THRESHOLD (too many styles are visual noise)
        n_methods: total number of methods plotted on this ax — used to
                   auto-disable bw_safe when plot is too crowded for
                   linestyle-based redundancy to help
        use_marker: add marker symbol on top of color (use on sparse data)

    Returns:
        dict of kwargs suitable for ax.plot(**kwargs). Always contains
        'color' and 'label'; may contain 'linestyle' and 'marker'.

    Example:
        ax.plot(x, y, **method_style("FEM", bw_safe=True, n_methods=3))
    """
    if n_methods is not None and n_methods > _BW_THRESHOLD:
        bw_safe = False

    kw: dict = {
        "color": METHOD_COLORS.get(method, LANCET_PALETTE["gray"]),
        "label": method,
    }

    if bw_safe:
        ls = METHOD_LINESTYLES_BW.get(method)
        if ls is not None:
            kw["linestyle"] = ls
    if bw_safe or use_marker:
        mk = METHOD_MARKERS_BW.get(method)
        if mk is not None:
            kw["marker"] = mk

    return kw


def legend_methods(ax, methods: list[str], **kwargs) -> None:
    """Helper: add a legend showing ONLY the given method names, in canonical
    color + linestyle (auto B&W-safe if ≤ _BW_THRESHOLD methods). Useful when
    multiple ax.plot calls produce duplicate labels, and you want a clean
    order.
    """
    bw_safe = len(methods) <= _BW_THRESHOLD
    handles = []
    for m in methods:
        style = method_style(m, bw_safe=bw_safe, n_methods=len(methods))
        line = plt.Line2D([0], [0], **{k: v for k, v in style.items()
                                        if k != "label"})
        handles.append(line)
    ax.legend(handles, methods, **kwargs)


# ───────────────────────────────────────────────────────────────────────────
# Sanity check (run `python paper_style.py` to print palette)
# ───────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Lancet palette (ggsci):")
    for k, v in LANCET_PALETTE.items():
        print(f"  {k:12s} {v}")
    print(f"\nMethod → color binding (canonical):")
    for k, v in METHOD_COLORS.items():
        print(f"  {k:18s} {v}")
    print(f"\nFigsize presets: 1COL={FIGSIZE_1COL} 2COL={FIGSIZE_2COL}"
          f" HERO_2x2={FIGSIZE_HERO_2x2}")
    print(f"B&W threshold: ≤{_BW_THRESHOLD} methods/plot → linestyle+marker; "
          f"else color-only")
