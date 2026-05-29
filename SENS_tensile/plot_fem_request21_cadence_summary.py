#!/usr/bin/env python3
"""Plot FEM Request 21 substep/history cadence controls.

The source data are the verified Windows-FEM outbox values for Request 19/21.
This figure is intentionally scalar-only: the OneDrive field CSV/MAT files can
be used later for field-level probes once macOS has hydrated them locally.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


OUT_DIR = Path(__file__).resolve().parent.parent / "_analysis_fem_mechanism_20260528" / "figures"


RUNS = [
    {
        "label": "peak-only\nReq19",
        "retained": [1.0],
        "nf": 120.0,
        "censored": True,
        "note": "no penetration by c120",
    },
    {
        "label": "n_step=2\n[1,0]",
        "retained": [1.0, 0.0],
        "nf": 70.0,
        "censored": False,
        "note": "Nf=70",
    },
    {
        "label": "n_step=3\n[0.5,1,0]",
        "retained": [0.5, 1.0, 0.0],
        "nf": 70.0,
        "censored": False,
        "note": "Nf=70",
    },
    {
        "label": "standard\n[.25,.5,.75,1,0]",
        "retained": [0.25, 0.5, 0.75, 1.0, 0.0],
        "nf": 69.0,
        "censored": False,
        "note": "Nf=69",
    },
    {
        "label": "n_step=10\n[.2,.4,.6,.8,1,0]",
        "retained": [0.2, 0.4, 0.6, 0.8, 1.0, 0.0],
        "nf": 69.0,
        "censored": False,
        "note": "Nf=69",
    },
]


def plot() -> tuple[Path, Path]:
    labels = [r["label"] for r in RUNS]
    nf = np.array([r["nf"] for r in RUNS], dtype=float)
    retained_counts = np.array([len(r["retained"]) for r in RUNS], dtype=float)
    nonzero_counts = np.array([sum(v > 1e-8 for v in r["retained"]) for r in RUNS], dtype=float)
    has_unload = np.array([any(abs(v) <= 1e-8 for v in r["retained"]) for r in RUNS])

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8), constrained_layout=True)
    palette = np.where(has_unload, "#0072B2", "#D55E00")

    ax = axes[0]
    x = np.arange(len(RUNS))
    bars = ax.bar(x, nf, color=palette, alpha=0.88)
    bars[0].set_hatch("//")
    ax.axhline(69, color="0.35", lw=1.0, ls="--", label="soft-hist0 standard Nf=69")
    ax.set_xticks(x, labels)
    ax.set_ylabel("penetration cycle")
    ax.set_title("FEM fatigue life vs retained load cadence")
    ax.set_ylim(0, 132)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    for i, r in enumerate(RUNS):
        text = ">120" if r["censored"] else f"{int(r['nf'])}"
        ax.text(i, nf[i] + 3, text, ha="center", va="bottom", fontsize=9)

    ax = axes[1]
    ax.plot(nonzero_counts, nf, marker="o", lw=1.6, color="#009E73", label="with unload except peak-only")
    ax.scatter(nonzero_counts[0], nf[0], marker="^", s=90, color="#D55E00", label="right-censored peak-only")
    for i, r in enumerate(RUNS):
        ax.annotate(r["label"].split("\n")[0], (nonzero_counts[i], nf[i]), xytext=(5, 5),
                    textcoords="offset points", fontsize=8)
    ax.axhline(69, color="0.35", lw=1.0, ls="--")
    ax.set_xlabel("number of retained positive load levels")
    ax.set_ylabel("penetration cycle")
    ax.set_title("After unload is retained, cadence effect is small")
    ax.set_ylim(64, 132)
    ax.set_xlim(0.6, max(nonzero_counts) + 0.5)
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=8, loc="upper right")

    fig.suptitle("Request 21: FEM substep/history cadence controls, soft-hist0 reverseBC", fontsize=13)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_png = OUT_DIR / "fem_request21_cadence_summary_20260530.png"
    out_pdf = OUT_DIR / "fem_request21_cadence_summary_20260530.pdf"
    fig.savefig(out_png, dpi=220)
    fig.savefig(out_pdf)
    plt.close(fig)
    return out_png, out_pdf


def main() -> int:
    out_png, out_pdf = plot()
    print(f"wrote {out_png}")
    print(f"wrote {out_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
