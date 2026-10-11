#!/usr/bin/env python3
"""Plot PIDL monotonic energy components for the four organized cases."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


CASES_ROOT = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl/Alignment check/PIDL monotonic/cases")
CASE_LABELS = {
    "softHist0_standard_pretrain_fatigue_off": "standard pretrain, fatigue off",
    "softHist0_standard_pretrain_fatigue_on": "standard pretrain, fatigue on",
    "softHist0_allFinePretrain_fatigue_off": "all-fine pretrain, fatigue off",
    "softHist0_allFinePretrain_fatigue_on": "all-fine pretrain, fatigue on",
}
COMPONENTS = [
    ("E_el", r"$E_{el}$"),
    ("E_d", r"$E_d$"),
    ("E_irrev", r"$E_{irrev}$"),
]
COLORS = {
    "softHist0_standard_pretrain_fatigue_off": "#0072B2",
    "softHist0_standard_pretrain_fatigue_on": "#D55E00",
    "softHist0_allFinePretrain_fatigue_off": "#009E73",
    "softHist0_allFinePretrain_fatigue_on": "#CC79A7",
}
LINESTYLES = {
    "softHist0_standard_pretrain_fatigue_off": "-",
    "softHist0_standard_pretrain_fatigue_on": "--",
    "softHist0_allFinePretrain_fatigue_off": "-",
    "softHist0_allFinePretrain_fatigue_on": "--",
}


def load_case(case: str) -> pd.DataFrame:
    csv_path = CASES_ROOT / case / "_source" / "energy_components" / f"{case}_energy_components.csv"
    df = pd.read_csv(csv_path)
    df.insert(0, "case", case)
    df.insert(1, "case_label", CASE_LABELS[case])
    return df


def style_axis(ax, ylabel: str) -> None:
    ax.set_ylabel(ylabel)
    ax.set_xlabel("applied displacement U")
    ax.grid(True, color="0.88", linewidth=0.7)
    ax.tick_params(labelsize=9)


def plot_all_cases(data: dict[str, pd.DataFrame]) -> Path:
    fig, axes = plt.subplots(3, 1, figsize=(8.4, 9.2), sharex=True, constrained_layout=True)
    for ax, (column, ylabel) in zip(axes, COMPONENTS):
        for case, df in data.items():
            ax.plot(
                df["U"],
                df[column],
                color=COLORS[case],
                linestyle=LINESTYLES[case],
                marker="o",
                markersize=3.4,
                linewidth=1.45,
                label=CASE_LABELS[case],
            )
        style_axis(ax, ylabel)
    axes[0].legend(loc="best", fontsize=8, frameon=False)
    fig.suptitle("PIDL monotonic energy components on softHist0 mesh", fontsize=12)
    out = CASES_ROOT / "pidl_monotonic_energy_components_all_cases.png"
    fig.savefig(out, dpi=240)
    plt.close(fig)
    return out


def plot_per_case(case: str, df: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 8.2), sharex=True, constrained_layout=True)
    for ax, (column, ylabel) in zip(axes, COMPONENTS):
        ax.plot(
            df["U"],
            df[column],
            color=COLORS[case],
            marker="o",
            markersize=3.5,
            linewidth=1.55,
        )
        style_axis(ax, ylabel)
    fig.suptitle(CASE_LABELS[case], fontsize=12)
    out = CASES_ROOT / f"{case}_energy_components.png"
    fig.savefig(out, dpi=240)
    plt.close(fig)
    return out


def main() -> None:
    data = {case: load_case(case) for case in CASE_LABELS}
    combined = pd.concat(data.values(), ignore_index=True)
    combined_csv = CASES_ROOT / "pidl_monotonic_energy_components_all_cases.csv"
    combined.to_csv(combined_csv, index=False)
    outputs = [plot_all_cases(data)]
    outputs.extend(plot_per_case(case, df) for case, df in data.items())
    print(f"combined_csv: {combined_csv}")
    for output in outputs:
        print(f"figure: {output}")


if __name__ == "__main__":
    main()
