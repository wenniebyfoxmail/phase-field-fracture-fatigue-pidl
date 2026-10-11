"""Generate clean Chapter 3 figures for the FYR thesis.

Most figures are schematic/method figures.  The monotonic alignment figure is a
small setup-check plot generated from verified scalar outputs.  The visual style
is intentionally close to technical mechanics figures: thin lines and a small
number of clear colour accents.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "Chapter3" / "Figs" / "PDF"
PNG_DIR = ROOT / "Chapter3" / "Figs" / "Raster"


INK = "#202124"
MUTED = "#5F6368"
GRID = "#DADCE0"
LIGHT = "#F8F9FA"
BLUE = "#2D5F8B"
RED = "#9A3B3B"
AMBER = "#9C6B1C"
GREEN = "#496D4B"
CYAN = "#39C6D6"
CYAN_DARK = "#168EA0"
CYAN_LIGHT = "#E7FAFC"
MLP_BG = "#D7D7D7"
OI_ORANGE = "#E69F00"
OI_SKY = "#56B4E9"
MANAV_BLUE = "#1F77B4"
MANAV_ORANGE = "#FF7F0E"


def save(fig: plt.Figure, name: str) -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PDF_DIR / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(PNG_DIR / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def arrow(ax, start, end, color=INK, lw=1.0, rad=0.0, ms=10.0):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=ms,
            linewidth=lw,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
            shrinkA=0,
            shrinkB=0,
        )
    )


def box(ax, x, y, w, h, text, fc="white", ec=INK, fs=8.5, lw=0.9, align="center"):
    patch = Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, linewidth=lw)
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha=align,
        va="center",
        fontsize=fs,
        color=INK,
        linespacing=1.2,
    )
    return patch


def support_hatching(ax, x0, x1, y, spacing=0.045, height=0.035, color=INK):
    x = x0
    while x <= x1:
        ax.plot([x, x - height], [y, y - height], color=color, linewidth=0.65)
        x += spacing


def figure_benchmark_geometry() -> None:
    fig, ax = plt.subplots(figsize=(4.7, 4.05))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-0.74, 0.78)
    ax.set_ylim(-0.72, 0.78)

    # Domain, following the compact mechanics style used by Manav et al.
    domain = Rectangle((-0.5, -0.5), 1.0, 1.0, facecolor="white", edgecolor=INK, linewidth=1.15)
    ax.add_patch(domain)
    # Top and bottom constrained edges.  The top is prescribed in vertical
    # displacement for the tensile benchmark; side boundaries are natural.
    ax.plot([-0.5, 0.5], [0.535, 0.535], color=INK, linewidth=0.75)
    x = -0.49
    while x <= 0.5:
        ax.plot([x, x + 0.035], [0.535, 0.57], color=INK, linewidth=0.55)
        x += 0.045
    ax.plot([-0.5, 0.5], [-0.535, -0.535], color=INK, linewidth=0.75)
    support_hatching(ax, -0.49, 0.5, -0.535, spacing=0.045, height=0.035, color=INK)

    arrow(ax, (0.0, 0.555), (0.0, 0.70), color=INK, lw=0.9, ms=9)
    ax.text(0.028, 0.69, r"$U(t)$", fontsize=8.2, va="center", color=INK)
    ax.text(0.09, 0.61, r"$\omega=\pi/2$", fontsize=6.7, color=MUTED)
    ax.text(0.0, 0.47, r"$u=0,\ v=U(t)$", ha="center", fontsize=6.7, color=BLUE)
    ax.text(0.0, -0.47, r"$u=0,\ v=0$", ha="center", fontsize=6.7, color=BLUE)
    ax.text(0.535, 0.18, "free\nsides", ha="left", va="center", fontsize=6.5, color=MUTED)

    # Initial notch / diffuse pre-crack.
    ax.plot([-0.5, 0.0], [0.0, 0.0], color=RED, linewidth=1.35, solid_capstyle="butt")
    ax.plot([-0.5, 0.0], [0.015, 0.015], color=RED, linewidth=0.55, alpha=0.45)
    ax.plot([-0.5, 0.0], [-0.015, -0.015], color=RED, linewidth=0.55, alpha=0.45)
    ax.text(-0.36, -0.065, r"$\alpha=1$", fontsize=7.1, color=RED)
    ax.add_patch(Circle((0.0, 0.0), 0.060, facecolor="none", edgecolor=RED, linewidth=0.7, linestyle="--"))
    ax.text(0.055, -0.085, r"$l_0=0.01$", fontsize=6.8, color=RED)

    # Local coordinate axes.
    arrow(ax, (0.0, 0.0), (0.23, 0.0), color=INK, lw=0.75, ms=8)
    arrow(ax, (0.0, 0.0), (0.0, 0.24), color=INK, lw=0.75, ms=8)
    ax.text(0.25, -0.02, "$x$", fontsize=8.0)
    ax.text(-0.025, 0.255, "$y$", fontsize=8.0)

    # Dimension marks, split at the notch tip as in the reference schematic.
    ax.annotate("", xy=(-0.5, -0.61), xytext=(0.0, -0.61), arrowprops=dict(arrowstyle="<->", lw=0.65, color=INK))
    ax.annotate("", xy=(0.0, -0.61), xytext=(0.5, -0.61), arrowprops=dict(arrowstyle="<->", lw=0.65, color=INK))
    ax.plot([0.0, 0.0], [-0.585, -0.635], color=INK, linewidth=0.65)
    ax.text(-0.25, -0.68, r"$0.5$", ha="center", fontsize=7.0, color=INK)
    ax.text(0.25, -0.68, r"$0.5$", ha="center", fontsize=7.0, color=INK)
    ax.annotate("", xy=(-0.61, 0.0), xytext=(-0.61, 0.5), arrowprops=dict(arrowstyle="<->", lw=0.65, color=INK))
    ax.annotate("", xy=(-0.61, -0.5), xytext=(-0.61, 0.0), arrowprops=dict(arrowstyle="<->", lw=0.65, color=INK))
    ax.plot([-0.635, -0.585], [0.0, 0.0], color=INK, linewidth=0.65)
    ax.text(-0.68, 0.25, r"$0.5$", va="center", ha="center", fontsize=7.0, color=INK, rotation=90)
    ax.text(-0.68, -0.25, r"$0.5$", va="center", ha="center", fontsize=7.0, color=INK, rotation=90)

    save(fig, "c3_benchmark_geometry_loading")


def draw_mlp(ax, x0, y0):
    layers = [2, 5, 5, 5, 3]
    xs = [x0, x0 + 0.7, x0 + 1.4, x0 + 2.1, x0 + 2.8]
    bg = FancyBboxPatch(
        (x0 - 0.18, y0 - 0.72),
        3.18,
        1.42,
        boxstyle="round,pad=0.08,rounding_size=0.12",
        facecolor=MLP_BG,
        edgecolor="none",
        zorder=-3,
    )
    ax.add_patch(bg)
    nodes_by_layer = []
    for xi, n in zip(xs, layers):
        ys = [y0 + (i - (n - 1) / 2) * 0.23 for i in range(n)]
        nodes = []
        for yi in ys:
            c = Circle((xi, yi), 0.06, facecolor=CYAN, edgecolor=CYAN_DARK, linewidth=0.65)
            ax.add_patch(c)
            nodes.append((xi, yi))
        nodes_by_layer.append(nodes)
    for left, right in zip(nodes_by_layer[:-1], nodes_by_layer[1:]):
        for a in left:
            for b in right:
                ax.plot([a[0], b[0]], [a[1], b[1]], color="#59636A", linewidth=0.28, zorder=-1)
    box(ax, xs[0] - 0.35, y0 - 0.22, 0.34, 0.34, "$x$\n$y$", fc=CYAN_LIGHT, ec=CYAN_DARK, fs=7.0, lw=0.7)
    box(ax, xs[-1] + 0.2, y0 + 0.20, 0.34, 0.34, r"$\hat u$", fc=CYAN_LIGHT, ec=CYAN_DARK, fs=7.0, lw=0.7)
    box(ax, xs[-1] + 0.2, y0 - 0.17, 0.34, 0.34, r"$\hat v$", fc=CYAN_LIGHT, ec=CYAN_DARK, fs=7.0, lw=0.7)
    box(ax, xs[-1] + 0.2, y0 - 0.54, 0.34, 0.34, r"$\hat\alpha$", fc=CYAN_LIGHT, ec=CYAN_DARK, fs=7.0, lw=0.7)
    ax.text(x0 + 1.4, y0 + 0.82, r"shared MLP: 8 layers, 400 neurons", ha="center", fontsize=7.2, color=MUTED)


def figure_pidl_structure() -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.25))
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.2)

    ax.text(0.35, 4.88, "neural field", fontsize=8.6, color=INK)
    draw_mlp(ax, 0.65, 2.95)
    arrow(ax, (3.55, 2.95), (4.0, 2.95), color=INK, lw=0.9)

    box(ax, 4.0, 3.55, 1.82, 0.48, r"$u=f_u(x,y,\hat u)\,U(t)$", fs=7.4)
    box(ax, 4.0, 2.92, 1.82, 0.48, r"$v=f_v(x,y,\hat v)\,U(t)$", fs=7.4)
    box(ax, 4.0, 2.29, 1.82, 0.48, r"$\alpha=S_{\rm ns}(\hat\alpha)$", fs=7.4)
    ax.text(4.91, 4.2, "output transforms / BC ansatz", ha="center", fontsize=7.2, color=MUTED)

    for y in [3.79, 3.16, 2.53]:
        arrow(ax, (5.82, y), (6.35, 3.18), color=MUTED, lw=0.75, ms=7)
    box(ax, 6.35, 2.83, 1.16, 0.70, "AD field\ngradients", fc=LIGHT, ec=MUTED, fs=6.9)
    arrow(ax, (7.51, 3.18), (7.95, 3.18), color=INK, lw=0.85)
    box(ax, 7.95, 2.82, 1.32, 0.72, r"$E_{\rm el}$" + "\n" + r"$E_d,\ E_{\rm hist}$", fs=7.8)
    arrow(ax, (8.61, 2.82), (8.61, 2.27), color=INK, lw=0.85)
    box(
        ax,
        7.65,
        1.66,
        1.92,
        0.58,
        r"$\mathcal{L}_{\rm PIDL}$" + "\n" + r"$=\log_{10}(\cdots)+\lambda_w\Vert W\Vert^2$",
        fs=6.9,
    )
    box(ax, 5.98, 1.72, 1.28, 0.52, "RPROP /\nL-BFGS", fc=CYAN_LIGHT, ec=CYAN_DARK, fs=6.9)
    arrow(ax, (7.65, 1.95), (7.26, 1.98), color=INK, lw=0.8, ms=7)
    ax.plot([5.98, 3.78], [1.98, 1.98], color=INK, linewidth=0.72)
    arrow(ax, (3.78, 1.98), (3.58, 2.42), color=INK, lw=0.72, ms=7)
    ax.text(4.55, 2.08, r"update $\theta$", fontsize=6.6, color=INK)
    box(ax, 6.05, 1.30, 1.18, 0.30, r"rel. tol $<\epsilon$", fc="white", ec=MUTED, fs=6.2, lw=0.7)
    arrow(ax, (6.62, 1.72), (6.62, 1.60), color=MUTED, lw=0.6, ms=6)

    box(ax, 3.92, 0.62, 1.85, 0.62, r"$\alpha_{\rm hist}\leftarrow\max(\alpha_{\rm hist},\alpha)$", fc="white", ec=GREEN, fs=6.9)
    box(ax, 6.0, 0.62, 1.75, 0.62, r"$\bar\alpha\leftarrow\bar\alpha+\langle\psi_{\rm active}-\psi_{\rm prev}\rangle_+$", fc="white", ec=AMBER, fs=6.4)
    box(ax, 8.03, 0.62, 1.35, 0.62, r"$f_{\rm fatigue}(\bar\alpha)$" + "\n" + r"scales $E_d$", fc="white", ec=AMBER, fs=6.8)
    arrow(ax, (4.91, 2.29), (4.91, 1.24), color=GREEN, lw=0.75, ms=7)
    arrow(ax, (6.93, 2.83), (6.93, 1.24), color=AMBER, lw=0.75, ms=7)
    arrow(ax, (8.7, 1.24), (8.7, 2.82), color=AMBER, lw=0.75, ms=7, rad=-0.10)

    ax.text(0.65, 0.62, "after Manav et al. Deep Ritz scheme\nwith fatigue extension", fontsize=6.9, color=MUTED)
    save(fig, "c3_pidl_neural_field_structure")


def figure_alignment_protocol() -> None:
    fig, ax = plt.subplots(figsize=(7.6, 4.65))
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.7)

    ax.text(0.55, 5.32, "FEM--PIDL comparison protocol", fontsize=8.6, color=INK)

    box(ax, 0.55, 4.35, 2.45, 0.70, "finite-element reference\ndiffuse pre-crack\nunloading retained", fc="white", ec=BLUE, fs=6.9, lw=1.0)
    box(ax, 3.78, 4.35, 2.45, 0.70, "PIDL benchmark run\nFEM-derived mesh\nsame fatigue law", fc="white", ec=GREEN, fs=6.9, lw=1.0)
    box(ax, 7.0, 4.35, 2.45, 0.70, "common-probe evaluation\nsame coordinates\nscalar + field quantities", fc="white", ec=RED, fs=6.9, lw=1.0)
    arrow(ax, (3.0, 4.7), (3.78, 4.7), color=MUTED, lw=0.8)
    arrow(ax, (6.23, 4.7), (7.0, 4.7), color=MUTED, lw=0.8)

    # Alignment settings rail.
    ax.plot([0.9, 9.1], [3.75, 3.75], color=GRID, linewidth=0.9)
    settings = [
        ("retained material", 1.15),
        ("diffuse crack", 2.35),
        ("zero history", 3.55),
        ("no initial fatigue", 4.7),
        ("cyclic load", 6.2),
        ("states", 7.75),
        ("probes", 8.95),
    ]
    for label, x in settings:
        ax.add_patch(Circle((x, 3.75), 0.05, facecolor="white", edgecolor=INK, linewidth=0.7))
        ax.text(x, 3.53, label, ha="center", fontsize=6.4, color=MUTED)
    ax.text(0.55, 4.0, "matched settings", fontsize=7.2, color=INK)

    # State matching ladder.
    box(ax, 0.75, 2.25, 1.15, 0.40, r"FEM $c1$", fc=LIGHT, ec=BLUE, fs=7.2)
    box(ax, 2.1, 2.25, 1.15, 0.40, r"FEM $c20$", fc=LIGHT, ec=BLUE, fs=7.2)
    box(ax, 3.45, 2.25, 1.15, 0.40, r"FEM $c40$", fc=LIGHT, ec=BLUE, fs=7.2)
    box(ax, 4.8, 2.25, 1.15, 0.40, r"FEM $c69$", fc=LIGHT, ec=BLUE, fs=7.2)

    box(ax, 0.75, 1.55, 1.15, 0.40, r"PIDL $j0$", fc="white", ec=GREEN, fs=7.2)
    box(ax, 2.1, 1.55, 1.15, 0.40, r"PIDL $j19$", fc="white", ec=GREEN, fs=7.2)
    box(ax, 3.45, 1.55, 1.15, 0.40, r"PIDL $j39$", fc="white", ec=GREEN, fs=7.2)
    box(ax, 4.8, 1.55, 1.15, 0.40, r"PIDL $j68$", fc="white", ec=GREEN, fs=7.2)
    for x in [1.38, 2.78, 4.18, 5.58]:
        arrow(ax, (x, 2.25), (x, 1.95), color=MUTED, lw=0.7, ms=7)
    ax.text(6.45, 2.22, r"state map: FEM cycle $c$" + "\n" + r"$\rightarrow$ PIDL saved state $j=c-1$", fontsize=7.6, color=INK)
    ax.text(6.45, 1.62, r"first-cycle audit: $j0$ closer than $j1$" + "\n" + r"for $\bar\alpha$ timing", fontsize=6.9, color=MUTED)

    # Compared quantities.
    ax.text(0.75, 0.82, "compared quantities", fontsize=7.4, color=INK)
    quantities = [
        r"$N_f$ / event",
        r"crack tip",
        r"$\alpha$",
        r"$\bar\alpha$",
        r"$\psi_{\rm raw}$",
        r"$\psi_{\rm active}$",
        r"$E_{\rm el}$",
        r"$\Delta E_d$",
    ]
    x = 0.75
    for q in quantities:
        box(ax, x, 0.32, 0.98, 0.30, q, fc="white", ec=GRID, fs=6.8, lw=0.65)
        x += 1.08

    save(fig, "c3_fem_pidl_alignment_protocol")


def figure_monotonic_alignment() -> None:
    """Create the monotonic FEM--PIDL setup-check figure.

    Source:
      local_archive/.../Alignment_check_monotonic/
      monotonic_energy_comparison_20260607/
      fem_pidl_monotonic_Eel_Ed_comparison.csv,
      cases softHist0_allFinePretrain_fatigue_off and umax020_fatigue_off.

    This is setup evidence only.  It should not be read as fatigue validation or
    as proof of solver equivalence.
    """

    pidl_u = [
        0.025, 0.05, 0.075, 0.10, 0.105, 0.11, 0.115, 0.12,
        0.125, 0.13, 0.135, 0.14, 0.145, 0.15, 0.155, 0.16,
        0.165, 0.17, 0.175, 0.18, 0.185, 0.19, 0.195, 0.20,
    ]
    pidl_eel = [
        3.028783248737e-04, 1.200501807034e-03, 1.9058476900681e-03,
        3.3406498841941e-03, 3.6789192818105e-03, 4.033719189465e-03,
        4.4043161906301e-03, 4.7914767637848e-03, 5.1947003230452e-03,
        5.6120008230209e-03, 6.0175266116857e-03, 3.3906854223459e-03,
        1.5901718143140897e-05, 1.5243300367728809e-05,
        1.4600344002246857e-05, 1.4238652511266991e-05,
        1.410278673574794e-05, 1.3994496839586644e-05,
        1.372867336613126e-05, 1.3622440746985376e-05,
        1.3561810192186384e-05, 1.3099017451168038e-05,
        1.3129560102242976e-05, 1.335729939455632e-05,
    ]
    pidl_ed = [
        4.9954298883676e-03, 4.9910526722669e-03, 5.3965710103511e-03,
        5.4219588637351e-03, 5.4178796708583e-03, 5.4137334227561e-03,
        5.4101711139082e-03, 5.4063866846263e-03, 5.4031526669859e-03,
        5.4019014351069e-03, 5.426577758044e-03, 8.1987585872411e-03,
        1.06796156615018e-02, 1.06741897761821e-02,
        1.06679731979966e-02, 1.06617547571659e-02,
        1.06553137302398e-02, 1.06488848105072e-02,
        1.06426812708377e-02, 1.06362756341695e-02,
        1.06296502053737e-02, 1.06231849640607e-02,
        1.06165679171681e-02, 1.0609914548695e-02,
    ]

    fem_u = [
        0.025, 0.05, 0.075, 0.10, 0.105, 0.11, 0.115, 0.12,
        0.125, 0.13, 0.135, 0.14, 0.145, 0.15, 0.155, 0.16,
        0.165, 0.17, 0.175, 0.18, 0.185, 0.19, 0.195, 0.20,
    ]
    fem_eel = [
        3.034058939508286e-04, 1.1848294118358036e-03,
        2.062068581175011e-03, 3.55454214149397e-03,
        3.910432001312536e-03, 4.285167491139589e-03,
        4.678022981486504e-03, 5.0885654485522255e-03,
        5.516444721228533e-03, 5.96032125101059e-03,
        6.415783001863996e-03, 6.860229236757921e-03,
        1.2203159522859813e-05, 1.1863419857893144e-05,
        1.180314027066813e-05, 1.174158170259571e-05,
        1.1709411957396787e-05, 1.1709054897922357e-05,
        1.1724547756112869e-05, 1.1739395290494184e-05,
        1.1742962262487393e-05, 1.1729130639423035e-05,
        1.1693418207625407e-05, 1.1637029604427048e-05,
    ]
    fem_ed = [
        5.054492496020029e-03, 5.072353630462908e-03,
        5.523703429202437e-03, 5.652123905068141e-03,
        5.665475202441649e-03, 5.678280961808882e-03,
        5.689806102072851e-03, 5.700270180755598e-03,
        5.710039853832068e-03, 5.720258901477991e-03,
        5.736174919913706e-03, 5.772991720109924e-03,
        1.1059337526836965e-02, 1.1060401988593701e-02,
        1.1061629324960335e-02, 1.1062817783597061e-02,
        1.1063880379481639e-02, 1.1064803332804837e-02,
        1.1065610485558083e-02, 1.106633212449831e-02,
        1.106699153430711e-02, 1.1067604387699888e-02,
        1.10681831045514e-02, 1.1068729717569104e-02,
    ]

    fig, ax = plt.subplots(figsize=(4.7, 3.05))

    ax.plot(
        pidl_u,
        pidl_eel,
        color=MANAV_BLUE,
        linestyle="-",
        linewidth=1.55,
    )
    ax.plot(
        fem_u,
        fem_eel,
        color=MANAV_BLUE,
        linestyle="--",
        linewidth=1.55,
    )
    ax.plot(
        pidl_u,
        pidl_ed,
        color=MANAV_ORANGE,
        linestyle="-",
        linewidth=1.55,
    )
    ax.plot(
        fem_u,
        fem_ed,
        color=MANAV_ORANGE,
        linestyle="--",
        linewidth=1.55,
    )

    ax.axvspan(0.140, 0.145, color="0.75", alpha=0.22, linewidth=0)
    ax.axvline(0.145, color="0.35", linestyle="--", linewidth=0.85)
    ax.annotate(
        r"$0.140$--$0.145$",
        xy=(0.145, 0.0010),
        xytext=(0.092, 0.00135),
        arrowprops=dict(arrowstyle="->", color="0.35", linewidth=0.7),
        fontsize=7.5,
        color="0.25",
    )

    ax.set_xlim(0.02, 0.205)
    ax.set_ylim(-0.00035, 0.01185)
    ax.set_xlabel(r"$U_p$")
    ax.set_ylabel(r"$\mathcal{E}$")
    ax.grid(True, color="0.84", linestyle=":", linewidth=0.45, alpha=0.9)
    energy_legend = ax.legend(
        handles=[
            Line2D([0], [0], color=MANAV_BLUE, linewidth=1.55, label=r"$E_{\rm el}$"),
            Line2D([0], [0], color=MANAV_ORANGE, linewidth=1.55, label=r"$E_d$"),
        ],
        frameon=True,
        facecolor="white",
        edgecolor="0.82",
        framealpha=0.95,
        fontsize=7.0,
        loc="upper left",
        ncol=1,
        handlelength=2.0,
        borderpad=0.35,
    )
    ax.add_artist(energy_legend)
    ax.legend(
        handles=[
            Line2D([0], [0], color="0.25", linestyle="-", linewidth=1.55, label="PIDL"),
            Line2D([0], [0], color="0.25", linestyle="--", linewidth=1.55, label="FEM"),
        ],
        frameon=True,
        facecolor="white",
        edgecolor="0.82",
        framealpha=0.95,
        fontsize=7.0,
        loc="upper left",
        bbox_to_anchor=(0.185, 1.0),
        ncol=1,
        handlelength=2.0,
        borderpad=0.35,
    )
    ax.tick_params(labelsize=7.4, length=3.0, width=0.65)
    ax.xaxis.label.set_size(8.0)
    ax.yaxis.label.set_size(8.0)
    for spine in ax.spines.values():
        spine.set_linewidth(0.7)

    fig.tight_layout()
    save(fig, "c3_monotonic_fem_pidl_alignment")


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Serif",
            "mathtext.fontset": "dejavuserif",
            "axes.linewidth": 0.8,
        }
    )
    figure_benchmark_geometry()
    figure_pidl_structure()
    figure_alignment_protocol()
    figure_monotonic_alignment()


if __name__ == "__main__":
    main()
