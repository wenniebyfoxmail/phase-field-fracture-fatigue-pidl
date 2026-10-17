#!/usr/bin/env python3
"""Draw the proposed observation-conditioned latent-temporal fracture figures."""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle


OUT = Path(__file__).resolve().parent

INK = "#263238"
MUTED = "#64748B"
GRID = "#CBD5E1"
PAPER = "#FFFFFF"
INPUT = "#F8FAFC"
SPATIAL = "#F4C77C"
SPATIAL_DARK = "#C9852B"
TEMPORAL = "#C9B6E4"
TEMPORAL_DARK = "#7958A6"
FUSION = "#F3AAA8"
FUSION_DARK = "#B65C5A"
OUTPUT = "#CFE8F6"
OUTPUT_DARK = "#4C8EAD"
VALID = "#D9EAD3"
VALID_DARK = "#5D8B55"
WARNING = "#F7E0A3"


def configure_style():
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.linewidth": 0.8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def box(ax, x, y, w, h, title, subtitle="", fc=INPUT, ec=INK, dashed=False,
        title_size=10.2, subtitle_size=8.0, lw=1.15, radius=0.12, zorder=3):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.025,rounding_size={radius}",
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
        linestyle=(0, (4, 3)) if dashed else "solid",
        zorder=zorder,
    )
    ax.add_patch(patch)
    ty = y + h * (0.61 if subtitle else 0.50)
    ax.text(x + w / 2, ty, title, ha="center", va="center", color=INK,
            fontsize=title_size, weight="semibold", zorder=zorder + 1)
    if subtitle:
        ax.text(x + w / 2, y + h * 0.29, subtitle, ha="center", va="center",
                color=MUTED, fontsize=subtitle_size, linespacing=1.15,
                zorder=zorder + 1)
    return patch


def arrow(ax, start, end, color=INK, lw=1.4, dashed=False, curve=0.0,
          mutation=12, zorder=4):
    a = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=mutation,
        linewidth=lw,
        color=color,
        linestyle=(0, (4, 3)) if dashed else "solid",
        connectionstyle=f"arc3,rad={curve}",
        shrinkA=1.5,
        shrinkB=1.5,
        zorder=zorder,
    )
    ax.add_patch(a)
    return a


def band(ax, x, y, w, h, label, fc, ec):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.12",
        facecolor=fc, edgecolor=ec, linewidth=0.9, alpha=0.38, zorder=0,
    )
    ax.add_patch(patch)
    ax.text(x + 0.15, y + h - 0.18, label.upper(), ha="left", va="top",
            color=ec, fontsize=7.5, weight="bold", zorder=1)


def badge(ax, x, y, text, fc=VALID, ec=VALID_DARK):
    width = 0.105 * len(text) + 0.38
    box(ax, x, y, width, 0.34, text, fc=fc, ec=ec, title_size=7.2,
        lw=0.8, radius=0.16)


def graph_icon(ax, x, y, w=1.4, h=0.65, color=SPATIAL_DARK):
    pts = [
        (x + 0.08*w, y + 0.20*h), (x + 0.25*w, y + 0.78*h),
        (x + 0.48*w, y + 0.42*h), (x + 0.68*w, y + 0.83*h),
        (x + 0.90*w, y + 0.32*h), (x + 0.73*w, y + 0.12*h),
    ]
    edges = [(0,1),(0,2),(1,2),(1,3),(2,3),(2,4),(2,5),(3,4),(4,5)]
    for i, j in edges:
        ax.plot([pts[i][0], pts[j][0]], [pts[i][1], pts[j][1]],
                color=color, lw=0.85, alpha=0.8, zorder=5)
    for px, py in pts:
        ax.plot(px, py, "o", ms=3.2, color=PAPER, mec=color, mew=0.9, zorder=6)


def field_tiles(ax, x, y, w=1.5, h=0.58):
    colors = ["#E6F2F7", "#C7E0EC", "#F4D39E", "#E99994"]
    for i, c in enumerate(colors):
        ax.add_patch(Rectangle((x + i*w/4, y), w/4 - 0.025, h,
                               facecolor=c, edgecolor=PAPER, linewidth=0.7,
                               zorder=5))
        ax.plot([x + i*w/4 + 0.05, x + (i+1)*w/4 - 0.07],
                [y + 0.17 + 0.08*(i % 2), y + h - 0.12],
                color=OUTPUT_DARK if i < 2 else FUSION_DARK,
                lw=1.0, zorder=6)


def save_all(fig, stem):
    for suffix in ("png", "pdf", "svg"):
        kwargs = {"bbox_inches": "tight", "facecolor": PAPER}
        if suffix == "png":
            kwargs["dpi"] = 320
        fig.savefig(OUT / f"{stem}.{suffix}", **kwargs)
    plt.close(fig)


def draw_framework():
    fig, ax = plt.subplots(figsize=(16.8, 8.8))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 10)
    ax.axis("off")

    ax.text(0.35, 9.62, "Proposed observation-conditioned latent-temporal fracture surrogate",
            fontsize=17, weight="bold", color=INK, ha="left", va="center")
    ax.text(0.35, 9.22,
            "Static context conditions the dynamics; evolving observations update the state; FEM remains the training and validation reference.",
            fontsize=9.4, color=MUTED, ha="left", va="center")
    badge(ax, 15.10, 9.36, "PROPOSED ARCHITECTURE", fc=WARNING, ec=SPATIAL_DARK)

    band(ax, 0.25, 6.65, 17.45, 2.15, "Invariant context", "#FFF7E8", SPATIAL_DARK)
    band(ax, 0.25, 2.72, 17.45, 3.45, "Evolving fracture state", "#F6F2FB", TEMPORAL_DARK)
    band(ax, 0.25, 0.35, 17.45, 1.78, "FEM-centred training and validation only", "#EFF8ED", VALID_DARK)

    # Static context branch.
    box(ax, 0.65, 7.08, 2.60, 1.20, "Static context",
        "mesh + notch\nmaterial + BC", dashed=True)
    graph_icon(ax, 0.90, 7.33, 0.72, 0.48)
    box(ax, 3.92, 7.08, 2.30, 1.20, "Context graph encoder", r"$E_g(\mathcal{G},x_g)$",
        fc=SPATIAL, ec=SPATIAL_DARK)
    box(ax, 6.95, 7.24, 1.35, 0.88, r"$z_g$", "context latent",
        fc="#FBE7BE", ec=SPATIAL_DARK, title_size=13)
    arrow(ax, (3.25, 7.68), (3.92, 7.68), color=SPATIAL_DARK)
    arrow(ax, (6.22, 7.68), (6.95, 7.68), color=SPATIAL_DARK)

    # Evolving-state branch.
    box(ax, 0.65, 4.06, 2.60, 1.48, "", dashed=True)
    ax.text(1.95, 5.18, "Observed state at $t$", ha="center", va="center", fontsize=10.5, weight="bold")
    field_tiles(ax, 0.98, 4.50, 1.92, 0.31)
    ax.text(1.95, 4.27,
            r"$\alpha_t,\bar\alpha_t$ + DIC/force + sparse probes",
            ha="center", va="center", color=MUTED, fontsize=6.6, zorder=6)
    box(ax, 3.92, 4.13, 2.30, 1.34, "State graph encoder", r"$E_s(s_t^{obs})$",
        fc=SPATIAL, ec=SPATIAL_DARK)
    box(ax, 6.95, 4.31, 1.35, 0.98, r"$z_t$", "state latent",
        fc="#FBE7BE", ec=SPATIAL_DARK, title_size=13)
    arrow(ax, (3.25, 4.80), (3.92, 4.80), color=SPATIAL_DARK)
    arrow(ax, (6.22, 4.80), (6.95, 4.80), color=SPATIAL_DARK)

    # Temporal branch and fusion.
    box(ax, 8.94, 4.02, 2.10, 1.56, "GRU state update",
        r"$h_t=T(h_{t-1},z_t,\Delta u_t)$", fc=TEMPORAL, ec=TEMPORAL_DARK)
    box(ax, 8.94, 3.08, 2.10, 0.60, "Known load increment", r"$\Delta u_t$ / path metadata",
        dashed=True, title_size=8.7, subtitle_size=7.2)
    arrow(ax, (8.30, 4.80), (8.94, 4.80), color=TEMPORAL_DARK)
    arrow(ax, (9.99, 3.68), (9.99, 4.02), color=TEMPORAL_DARK)
    arrow(ax, (10.79, 5.30), (9.20, 5.58), color=TEMPORAL_DARK, curve=0.32, lw=1.1)
    ax.text(10.46, 5.74, r"$h_{t-1}$", fontsize=8.2, color=TEMPORAL_DARK,
            ha="center", va="bottom")

    box(ax, 11.79, 4.13, 1.82, 1.34, "FiLM coupling",
        r"$\tilde h_t=(1+\gamma(z_g))\odot h_t+\beta(z_g)$",
        fc=FUSION, ec=FUSION_DARK, subtitle_size=7.0)
    arrow(ax, (11.04, 4.80), (11.79, 4.80), color=FUSION_DARK)
    arrow(ax, (7.62, 7.24), (12.22, 5.48), color=SPATIAL_DARK, curve=-0.10)

    box(ax, 14.22, 4.13, 1.62, 1.34, "Graph decoder", r"$D_g(\tilde h_t)$",
        fc=SPATIAL, ec=SPATIAL_DARK)
    arrow(ax, (13.61, 4.80), (14.22, 4.80), color=SPATIAL_DARK)
    box(ax, 16.20, 3.83, 1.38, 1.94, r"$\hat s_{t+1}$",
        "damage\nhistory\nraw driver\nactive driver",
        fc=OUTPUT, ec=OUTPUT_DARK, title_size=13, subtitle_size=6.8)
    arrow(ax, (15.84, 4.80), (16.20, 4.80), color=OUTPUT_DARK)

    # FEM-centred reference branch.
    box(ax, 1.02, 0.74, 2.55, 0.92, "FEM mechanism fields",
        "aligned cycle / load / event state", fc=VALID, ec=VALID_DARK, dashed=True)
    box(ax, 5.12, 0.69, 2.72, 1.02, "Mechanism-aware objective",
        "field residual + support + morphology", fc=VALID, ec=VALID_DARK)
    box(ax, 9.16, 0.69, 3.25, 1.02, "FEM-centred validation gate",
        "h1-h3 | transition | reset propagation", fc=VALID, ec=VALID_DARK)
    box(ax, 13.45, 0.69, 3.55, 1.02, "Required evidence",
        "log-MAE | p99 IoU | area ratio | symmetry", fc=VALID, ec=VALID_DARK)
    arrow(ax, (3.57, 1.20), (5.12, 1.20), color=VALID_DARK, dashed=True)
    arrow(ax, (7.84, 1.20), (9.16, 1.20), color=VALID_DARK, dashed=True)
    arrow(ax, (12.41, 1.20), (13.45, 1.20), color=VALID_DARK, dashed=True)
    arrow(ax, (16.88, 3.83), (6.60, 1.71), color=VALID_DARK, dashed=True, curve=0.08)
    ax.text(12.55, 2.33, "prediction enters the loss only during training",
            color=VALID_DARK, fontsize=7.6, style="italic", ha="center")

    # Legend.
    legend_y = 2.38
    for i, (label, fc, ec) in enumerate(
        [
            ("graph representation", SPATIAL, SPATIAL_DARK),
            ("temporal dynamics", TEMPORAL, TEMPORAL_DARK),
            ("context-state fusion", FUSION, FUSION_DARK),
            ("predicted fields", OUTPUT, OUTPUT_DARK),
        ]
    ):
        x = 0.70 + i * 2.65
        ax.add_patch(Rectangle((x, legend_y), 0.28, 0.16, facecolor=fc,
                               edgecolor=ec, linewidth=0.8))
        ax.text(x + 0.38, legend_y + 0.08, label, va="center", ha="left",
                fontsize=7.2, color=MUTED)
    ax.plot([11.70, 12.20], [legend_y + 0.08]*2, color=INK, lw=1.0,
            linestyle=(0, (4, 3)))
    ax.text(12.30, legend_y + 0.08, "observed/reference input",
            va="center", fontsize=7.2, color=MUTED)

    save_all(fig, "fig01_proposed_observation_conditioned_latent_temporal_framework")


def slab(ax, x, y, w, h, depth, fc, ec, label, dim, scale=1.0):
    dx, dy = depth, depth * 0.55
    front = Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec,
                      linewidth=1.0, zorder=4)
    side = Polygon([(x+w, y), (x+w+dx, y+dy), (x+w+dx, y+h+dy), (x+w, y+h)],
                   closed=True, facecolor=mpl.colors.to_rgba(fc, 0.72),
                   edgecolor=ec, linewidth=0.8, zorder=3)
    top = Polygon([(x, y+h), (x+dx, y+h+dy), (x+w+dx, y+h+dy), (x+w, y+h)],
                  closed=True, facecolor=mpl.colors.to_rgba(fc, 0.52),
                  edgecolor=ec, linewidth=0.8, zorder=3)
    ax.add_patch(side)
    ax.add_patch(top)
    ax.add_patch(front)
    ax.text(x + w/2, y - 0.26, label, ha="center", va="top",
            fontsize=8.1*scale, color=INK, weight="semibold")
    ax.text(x + w/2, y + h + dy + 0.13, dim, ha="center", va="bottom",
            fontsize=7.4*scale, color=MUTED)
    return (x+w+dx, y+h/2+dy/2)


def draw_latent_module():
    fig, ax = plt.subplots(figsize=(17.2, 8.8))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 10)
    ax.axis("off")

    ax.text(0.40, 9.60, "Proposed mechanism-preserving graph latent representation module",
            fontsize=17, weight="bold", color=INK, ha="left", va="center")
    ax.text(0.40, 9.18,
            "Symbolic dimensions are shown because pooling ratios and latent width remain experiment-controlled design choices.",
            fontsize=9.3, color=MUTED, ha="left")
    badge(ax, 17.05, 9.34, "DESIGN SPECIFICATION", fc=WARNING, ec=SPATIAL_DARK)

    # Input and encoder slabs.
    slab(ax, 0.55, 3.85, 0.42, 3.25, 0.15, INPUT, INK,
         "mesh state", r"$N_0\times C_0$")
    graph_icon(ax, 0.60, 5.05, 0.34, 0.85, color=INK)
    slab(ax, 2.00, 4.05, 0.52, 2.85, 0.17, "#F8DCA9", SPATIAL_DARK,
         "MP block 1", r"$N_0\times32$")
    slab(ax, 3.55, 4.30, 0.60, 2.35, 0.18, "#F6CF8B", SPATIAL_DARK,
         "coarsen 1", r"$N_1\times64$")
    slab(ax, 5.15, 4.55, 0.68, 1.85, 0.19, "#F2BF66", SPATIAL_DARK,
         "MP block 2", r"$N_1\times128$")
    slab(ax, 6.90, 4.80, 0.75, 1.35, 0.20, "#EFAE45", SPATIAL_DARK,
         "coarsen 2", r"$N_L\times C_L$")

    for s, e in [((1.12,5.48),(2.00,5.48)),((2.69,5.48),(3.55,5.48)),
                 ((4.33,5.48),(5.15,5.48)),((6.02,5.48),(6.90,5.48))]:
        arrow(ax, s, e, color=SPATIAL_DARK, lw=1.35)

    # Probabilistic bottleneck.
    box(ax, 8.33, 5.56, 1.50, 0.65, r"$\mu_t$", "latent mean",
        fc="#FFF1D4", ec=SPATIAL_DARK, title_size=11, subtitle_size=6.8)
    box(ax, 8.33, 4.55, 1.50, 0.65, r"$\log\sigma_t^2$", "latent uncertainty",
        fc="#FFF1D4", ec=SPATIAL_DARK, title_size=10.2, subtitle_size=6.8)
    box(ax, 10.10, 4.84, 1.78, 1.05, "Reparameterize",
        r"$z_t=\mu_t+\sigma_t\odot\epsilon$", fc=FUSION, ec=FUSION_DARK,
        title_size=8.2, subtitle_size=6.5)
    arrow(ax, (7.85,5.48),(8.33,5.88), color=SPATIAL_DARK)
    arrow(ax, (7.85,5.48),(8.33,4.88), color=SPATIAL_DARK)
    arrow(ax, (9.83,5.88),(10.10,5.50), color=FUSION_DARK)
    arrow(ax, (9.83,4.88),(10.10,5.18), color=FUSION_DARK)

    # Decoder slabs.
    slab(ax, 12.28, 4.80, 0.75, 1.35, 0.20, "#EFAE45", SPATIAL_DARK,
         "latent map", r"$N_L\times d_z$")
    slab(ax, 14.05, 4.55, 0.68, 1.85, 0.19, "#F2BF66", SPATIAL_DARK,
         "MP block 3", r"$N_1\times128$")
    slab(ax, 15.65, 4.30, 0.60, 2.35, 0.18, "#F6CF8B", SPATIAL_DARK,
         "refine 1", r"$N_0\times64$")
    slab(ax, 17.18, 4.05, 0.52, 2.85, 0.17, "#F8DCA9", SPATIAL_DARK,
         "MP block 4", r"$N_0\times32$")
    slab(ax, 18.72, 3.85, 0.42, 3.25, 0.15, OUTPUT, OUTPUT_DARK,
         "mechanism fields", r"$N_0\times C_{out}$")
    field_tiles(ax, 18.75, 5.10, 0.34, 0.78)

    arrow(ax, (11.88,5.36),(12.28,5.48), color=FUSION_DARK)
    for s, e in [((13.23,5.48),(14.05,5.48)),((14.92,5.48),(15.65,5.48)),
                 ((16.43,5.48),(17.18,5.48)),((17.87,5.48),(18.72,5.48))]:
        arrow(ax, s, e, color=SPATIAL_DARK, lw=1.35)

    # Skip connections preserve local support.
    arrow(ax, (2.28,7.02), (17.45,7.02), color=OUTPUT_DARK, lw=1.0,
          dashed=True, curve=-0.10, mutation=10)
    arrow(ax, (3.85,6.78), (15.95,6.78), color=OUTPUT_DARK, lw=1.0,
          dashed=True, curve=-0.08, mutation=10)
    arrow(ax, (5.48,6.55), (14.38,6.55), color=OUTPUT_DARK, lw=1.0,
          dashed=True, curve=-0.06, mutation=10)
    ax.text(10.0, 7.62, "multiscale skip features preserve crack-tip and process-zone localization",
            ha="center", va="center", fontsize=8.0, color=OUTPUT_DARK,
            style="italic")

    # Configuration key.
    ax.add_patch(FancyBboxPatch((0.55,0.55),18.75,2.10,
                                boxstyle="round,pad=0.03,rounding_size=0.10",
                                facecolor="#FAFBFC", edgecolor=GRID,
                                linewidth=0.9, zorder=0))
    ax.text(0.83,2.36,"CONFIGURATION KEY",fontsize=7.6,weight="bold",
            color=MUTED,va="top")

    ax.text(0.83,1.95,"Input node channels",fontsize=8.8,weight="semibold",color=INK)
    ax.text(0.83,1.53,
            r"coordinates + $\alpha_t$ + $\bar\alpha_t$ + $\psi_{raw,t}$" + "\n" +
            "observation mask + DIC/strain/force-derived features",
            fontsize=7.7,color=MUTED,linespacing=1.35)

    ax.text(5.47,1.95,"Message-passing block",fontsize=8.8,weight="semibold",color=INK)
    ax.text(5.47,1.53,
            "edge-relative geometry -> normalized aggregation\nresidual node update -> normalization + SiLU",
            fontsize=7.7,color=MUTED,linespacing=1.35)

    ax.text(10.40,1.95,"Mechanism-preserving objective",fontsize=8.8,weight="semibold",color=INK)
    ax.text(10.40,1.53,
            "field reconstruction + active-support loss\ncentroid/width + neighbour-jump diagnostics",
            fontsize=7.7,color=MUTED,linespacing=1.35)

    ax.text(15.28,1.95,"Output channels",fontsize=8.8,weight="semibold",color=INK)
    ax.text(15.28,1.53,
            r"$\hat\alpha_{t+1},\hat{\bar\alpha}_{t+1},\hat\psi_{raw,t+1}$" + "\n" +
            r"$\hat\psi_{active,t+1}$ + calibrated uncertainty",
            fontsize=7.7,color=MUTED,linespacing=1.35)

    ax.text(0.83,0.83,
            r"$N_0$: original mesh nodes/elements;  $N_1,N_L$: coarsened graph levels;  "
            r"$C_0,C_L,d_z$: feature widths selected by ablation.  FEM values supervise training only and are absent at inference.",
            fontsize=7.5,color=MUTED,ha="left",va="center")

    save_all(fig, "fig02_proposed_graph_latent_representation_configuration")


if __name__ == "__main__":
    configure_style()
    OUT.mkdir(parents=True, exist_ok=True)
    draw_framework()
    draw_latent_module()
