#!/usr/bin/env python3
"""Plot a compact PIDL method promise summary under the soft-hist0 protocol."""
from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_DIR = ROOT / "_analysis_fem_mechanism_20260528" / "variant_rescore_j0map"
FIG_DIR = ROOT / "_analysis_fem_mechanism_20260528" / "figures"


METHOD_FILES = {
    "baseline geom2": DATA_DIR / "baseline_geom2.csv",
    "FEM-mesh softHist0": DATA_DIR / "femmesh_softHist0.csv",
    "softHist0/tol_ir=0.001": DATA_DIR / "reverseBC_softHist0_forward_tolir0p001.csv",
    "spatial alphaT b=0.8": DATA_DIR / "spAlphaT_b08.csv",
    "Williams v4": DATA_DIR / "williams_v4.csv",
    "psiHack": DATA_DIR / "psiHack.csv",
}

METRICS = [
    ("damage_tip2", "damage\nnear tip"),
    ("alpha_tip2", "history\nnear tip"),
    ("alpha_p99", "history\np99"),
    ("active_psi_tip2", "active driver\nnear tip"),
    ("active_psi_p99", "active driver\np99"),
]


def read_direct_summary(path: Path, cycle: int) -> dict[str, float]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    hit = [row for row in rows if int(row["cycle"]) == cycle]
    if len(hit) != 1:
        raise ValueError(f"Expected one row for cycle {cycle} in {path}, found {len(hit)}")
    return {key: float(hit[0][key]) for key, _ in METRICS}


def read_long_summary(path: Path, cycle: int) -> dict[str, float]:
    want = {
        ("damage_alpha", "tip_2l0_mean"): "damage_tip2",
        ("alpha_bar", "tip_2l0_mean"): "alpha_tip2",
        ("alpha_bar", "p99"): "alpha_p99",
        ("psi_plus_active", "tip_2l0_mean"): "active_psi_tip2",
        ("psi_plus_active", "p99"): "active_psi_p99",
    }
    out = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if int(row["cycle"]) != cycle:
                continue
            key = want.get((row["field"], row["metric"]))
            if key:
                out[key] = float(row["PIDL_over_FEM_projected"])
    missing = {v for v in want.values()} - set(out)
    if missing:
        raise ValueError(f"Missing {sorted(missing)} in {path}")
    return out


def load_method_rows(cycle: int = 69) -> dict[str, dict[str, float]]:
    rows = {}
    for method, path in METHOD_FILES.items():
        if not path.exists():
            continue
        if "cycle,fem_cycle" in path.read_text(encoding="utf-8", errors="ignore")[:80]:
            rows[method] = read_long_summary(path, cycle)
        else:
            rows[method] = read_direct_summary(path, cycle)
    return rows


def log_score(values: list[float]) -> float:
    vals = [abs(math.log(max(v, 1e-12), 2.0)) for v in values if np.isfinite(v)]
    return float(np.mean(vals)) if vals else float("nan")


def plot_summary(rows: dict[str, dict[str, float]]) -> tuple[Path, Path]:
    methods = list(rows)
    ratio = np.array([[rows[m][key] for key, _ in METRICS] for m in methods], dtype=float)
    log_ratio = np.log2(np.clip(ratio, 1e-6, 1e6))
    clipped = np.clip(log_ratio, -5.0, 5.0)

    damage_score = [log_score([rows[m]["damage_tip2"]]) for m in methods]
    mechanism_score = [
        log_score([rows[m]["alpha_tip2"], rows[m]["alpha_p99"], rows[m]["active_psi_tip2"]])
        for m in methods
    ]

    selected = ["FEM-mesh softHist0", "softHist0/tol_ir=0.001"]
    selected = [m for m in selected if m in rows]
    paradox_vals = np.array(
        [[rows[m]["damage_tip2"], rows[m]["alpha_tip2"], rows[m]["active_psi_tip2"]] for m in selected],
        dtype=float,
    )

    fig = plt.figure(figsize=(13.8, 7.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.45, 1.0], height_ratios=[1.05, 0.95])

    ax0 = fig.add_subplot(gs[:, 0])
    im = ax0.imshow(clipped, cmap="RdBu_r", norm=TwoSlopeNorm(vmin=-5, vcenter=0, vmax=5), aspect="auto")
    ax0.set_xticks(range(len(METRICS)), [label for _, label in METRICS])
    ax0.set_yticks(range(len(methods)), methods)
    ax0.set_title("c69 PIDL/FEM ratios on common probes")
    ax0.tick_params(axis="x", labelrotation=0)
    for i in range(len(methods)):
        for j in range(len(METRICS)):
            val = ratio[i, j]
            color = "white" if abs(clipped[i, j]) > 2.4 else "black"
            ax0.text(j, i, f"{val:.2g}", ha="center", va="center", fontsize=8, color=color)
    cb = fig.colorbar(im, ax=ax0, fraction=0.046, pad=0.02)
    cb.set_label("log2(PIDL/FEM), clipped")
    ax0.axvline(0.5, color="0.35", lw=0.8)

    ax1 = fig.add_subplot(gs[0, 1])
    y = np.arange(len(methods))
    ax1.barh(y - 0.18, damage_score, height=0.34, color="#0072B2", label="damage only")
    ax1.barh(y + 0.18, mechanism_score, height=0.34, color="#D55E00", label="history + active driver")
    ax1.set_yticks(y, methods)
    ax1.invert_yaxis()
    ax1.set_xlabel("mean |log2 ratio|, lower is better")
    ax1.set_title("Damage close != mechanism close")
    ax1.grid(axis="x", alpha=0.25)
    ax1.legend(frameon=False, fontsize=8)

    ax2 = fig.add_subplot(gs[1, 1])
    if selected:
        x = np.arange(len(selected))
        width = 0.24
        labels = ["damage\nnear tip", "history\nnear tip", "active driver\nnear tip"]
        colors = ["#0072B2", "#E69F00", "#D55E00"]
        for j in range(paradox_vals.shape[1]):
            ax2.bar(x + (j - 1) * width, paradox_vals[:, j], width, label=labels[j], color=colors[j])
        ax2.axhline(1.0, color="0.25", lw=1.0, ls="--")
        ax2.set_xticks(x, selected, rotation=12, ha="right")
        ax2.set_yscale("log")
        ax2.set_ylim(0.02, 2.5)
        ax2.set_ylabel("PIDL/FEM ratio")
        ax2.set_title("More damage, weaker driver")
        ax2.grid(axis="y", alpha=0.25, which="both")
        ax2.legend(frameon=False, fontsize=8, loc="upper right")

    fig.suptitle("PIDL method promise under the soft-hist0 state-timing protocol", fontsize=13)
    out_png = FIG_DIR / "pidl_method_promise_summary_20260529.png"
    out_pdf = FIG_DIR / "pidl_method_promise_summary_20260529.pdf"
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=220)
    fig.savefig(out_pdf)
    plt.close(fig)
    return out_png, out_pdf


def main() -> int:
    rows = load_method_rows(cycle=69)
    out_png, out_pdf = plot_summary(rows)
    print(f"wrote {out_png}")
    print(f"wrote {out_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
