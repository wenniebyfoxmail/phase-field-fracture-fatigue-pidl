#!/usr/bin/env python3
"""Plot adaptive lambda_hist trace for the all-FEM-mesh PIDL run."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_analysis_fem_mechanism_20260528" / "allfemmesh_lambda_hist_20260607"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    lam = np.load(OUT / "lambda_hist_vs_cycle.npy")
    alpha = np.load(OUT / "alpha_bar_vs_cycle.npy")
    xtip = np.load(OUT / "x_tip_alpha_vs_cycle.npy")

    df = pd.DataFrame(
        lam,
        columns=[
            "cycle",
            "lambda_hist",
            "lambda_hat",
            "grad_E_el",
            "grad_E_d",
            "grad_E_hist",
        ],
    )
    df["cycle"] = df["cycle"].astype(int)
    df["alpha_bar_max"] = alpha[: len(df), 0]
    df["f_min"] = alpha[: len(df), 2]
    df["x_tip_alpha"] = xtip[: len(df)]
    df["hist_over_max_phys"] = df["grad_E_hist"] / np.maximum(
        df[["grad_E_el", "grad_E_d"]].max(axis=1), 1e-30
    )
    df["max_phys_over_hist"] = np.maximum(
        df[["grad_E_el", "grad_E_d"]].max(axis=1), 1e-30
    ) / np.maximum(df["grad_E_hist"], 1e-30)
    df.to_csv(OUT / "allfemmesh_adapthist_lambda_trace.csv", index=False)

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(8.2, 8.8),
        sharex=True,
        gridspec_kw={"height_ratios": [1.2, 1.6, 1.0, 1.0]},
        constrained_layout=True,
    )

    ax = axes[0]
    ax.plot(df["cycle"], df["lambda_hist"], color="#0072B2", lw=1.6, label=r"$\lambda_{hist}$")
    ax.scatter(df["cycle"], df["lambda_hist"], color="#0072B2", s=10)
    ax.axhline(1.0, color="0.35", lw=0.9, ls="--", label="upper clip")
    ax.axhline(1.0e-3, color="0.65", lw=0.8, ls=":", label="lower clip")
    ax.set_yscale("log")
    ax.set_ylabel(r"$\lambda_{hist}$")
    ax.set_title("Adaptive E_irres/lambda_hist trace: all-FEM-mesh PIDL")
    ax.grid(True, which="both", color="0.9", lw=0.6)
    ax.legend(loc="lower right", fontsize=8, frameon=False)

    ax = axes[1]
    ax.plot(df["cycle"], df["grad_E_el"], color="#009E73", lw=1.3, label=r"$||\nabla \log E_{el}||_2$")
    ax.plot(df["cycle"], df["grad_E_d"], color="#D55E00", lw=1.3, label=r"$||\nabla \log E_d||_2$")
    ax.plot(df["cycle"], df["grad_E_hist"], color="#CC79A7", lw=1.3, label=r"$||\nabla \log E_{irres}||_2$")
    ax.set_yscale("log")
    ax.set_ylabel("gradient L2 norm")
    ax.grid(True, which="both", color="0.9", lw=0.6)
    ax.legend(loc="upper left", fontsize=8, frameon=False, ncol=1)

    ax = axes[2]
    ax.plot(df["cycle"], df["x_tip_alpha"], color="#E69F00", lw=1.4, label=r"$x_{tip}$ by alpha")
    ax.axhline(0.46, color="0.45", lw=0.9, ls="--", label="near right boundary")
    ax.axhline(0.50, color="0.25", lw=0.9, ls=":", label="right boundary")
    ax.set_ylabel(r"$L_\infty$ crack length")
    ax.grid(True, color="0.9", lw=0.6)
    ax.legend(loc="upper left", fontsize=8, frameon=False)

    ax = axes[3]
    ax.plot(df["cycle"], df["alpha_bar_max"], color="#56B4E9", lw=1.4, label=r"$\bar{\alpha}_{max}$")
    ax2 = ax.twinx()
    ax2.plot(df["cycle"], df["f_min"], color="#000000", lw=1.2, ls="--", label=r"$f_{min}$")
    ax.set_ylabel(r"$\bar{\alpha}_{max}$")
    ax2.set_ylabel(r"$f_{min}$")
    ax.set_xlabel("cycle")
    ax.grid(True, color="0.9", lw=0.6)
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="center left", fontsize=8, frameon=False)

    for frac_cycle, label in [(88, "detected"), (91, "confirmed")]:
        for ax in axes:
            ax.axvline(frac_cycle, color="0.25", lw=0.8, ls="--", alpha=0.55)
        axes[0].text(
            frac_cycle + 0.4,
            0.002 if frac_cycle == 88 else 0.004,
            label,
            fontsize=8,
            rotation=90,
            va="bottom",
            color="0.25",
        )

    png = OUT / "allfemmesh_adapthist_lambda_trace.png"
    pdf = OUT / "allfemmesh_adapthist_lambda_trace.pdf"
    fig.savefig(png, dpi=220)
    fig.savefig(pdf)
    plt.close(fig)
    print(png)
    print(pdf)
    print(OUT / "allfemmesh_adapthist_lambda_trace.csv")


if __name__ == "__main__":
    main()
