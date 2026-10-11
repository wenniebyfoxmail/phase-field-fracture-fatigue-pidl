#!/usr/bin/env python3
"""Compare FEM monotonic void/slit notch and soft-hist0 retained precrack cases."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


REPO = Path("/Users/wenxiaofang/phase-field-fracture-with-pidl")
OUT = REPO / "Alignment check" / "FEM monotonic notch comparison 20260609"
VOID = REPO / "Alignment check" / "FEM monotonic void notch " / "cases"
SOFT = REPO / "Alignment check" / "FEM monotonic match"


CASES = [
    {
        "family": "void_slit_notch",
        "label": "Void/slit notch, fatigue off",
        "case": "umax020_fatigue_off",
        "fatigue": "off",
        "path": VOID / "umax020_fatigue_off" / "_source" / "processed" / "umax020_fatigue_off_load_displacement.csv",
        "color": "#0072B2",
        "ls": "-",
    },
    {
        "family": "void_slit_notch",
        "label": "Void/slit notch, fatigue on",
        "case": "umax020_fatigue_on",
        "fatigue": "on",
        "path": VOID / "umax020_fatigue_on" / "_source" / "processed" / "umax020_fatigue_on_load_displacement.csv",
        "color": "#56B4E9",
        "ls": "--",
    },
    {
        "family": "soft_hist0_retained",
        "label": "Soft-hist0 retained, fatigue off",
        "case": "umax020_fatigue_off",
        "fatigue": "off",
        "path": SOFT / "raw_handoff" / "_pidl_handoff_soft_hist0_monotonic_24vtk_20260607" / "fatigue_off" / "load_displ_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_monotonic_fatigueoff_manvas_steps.out",
        "color": "#D55E00",
        "ls": "-",
    },
    {
        "family": "soft_hist0_retained",
        "label": "Soft-hist0 retained, fatigue on",
        "case": "umax020_fatigue_on",
        "fatigue": "on",
        "path": SOFT / "raw_handoff" / "_pidl_handoff_soft_hist0_monotonic_24vtk_20260607" / "fatigue_on" / "load_displ_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC_monotonic_manvas_steps.out",
        "color": "#E69F00",
        "ls": "--",
    },
]


def read_load(case: dict[str, object]) -> pd.DataFrame:
    path = Path(case["path"])
    if path.suffix == ".csv":
        df = pd.read_csv(path)
        df = df.rename(columns={"U_prescribed": "U"})
    else:
        df = pd.read_csv(path, sep=r"\s+", engine="python")
        df = df.rename(columns={"u_y": "U"})
    df["family"] = str(case["family"])
    df["case"] = str(case["case"])
    df["fatigue"] = str(case["fatigue"])
    df["label"] = str(case["label"])
    df["source"] = str(path)
    return df[["family", "case", "fatigue", "label", "step", "U", "F_y", "source"]]


def first_drop_after_peak(df: pd.DataFrame, ratio: float = 0.1) -> pd.Series:
    peak_idx = df["F_y"].idxmax()
    peak = df.loc[peak_idx]
    after = df[df["step"] > peak["step"]]
    drops = after[after["F_y"] < ratio * peak["F_y"]]
    if len(drops):
        return drops.iloc[0]
    return pd.Series({"step": pd.NA, "U": pd.NA, "F_y": pd.NA})


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, group in df.groupby(["family", "case", "fatigue", "label"], sort=False):
        peak = group.loc[group["F_y"].idxmax()]
        drop = first_drop_after_peak(group)
        final = group.sort_values("step").iloc[-1]
        rows.append(
            {
                "family": peak["family"],
                "case": peak["case"],
                "fatigue": peak["fatigue"],
                "label": peak["label"],
                "n_steps": int(group["step"].max()),
                "peak_step": int(peak["step"]),
                "peak_U": float(peak["U"]),
                "peak_Fy": float(peak["F_y"]),
                "drop_step_F_lt_0p1_peak": "" if pd.isna(drop["step"]) else int(drop["step"]),
                "drop_U_F_lt_0p1_peak": "" if pd.isna(drop["U"]) else float(drop["U"]),
                "drop_Fy": "" if pd.isna(drop["F_y"]) else float(drop["F_y"]),
                "final_U": float(final["U"]),
                "final_Fy": float(final["F_y"]),
                "source": peak["source"],
            }
        )
    return pd.DataFrame(rows)


def plot_load(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 5.0), constrained_layout=True)
    for case in CASES:
        sub = df[df["label"] == case["label"]].sort_values("U")
        ax.plot(
            sub["U"],
            sub["F_y"],
            marker="o",
            markersize=3.5,
            linewidth=1.7,
            linestyle=str(case["ls"]),
            color=str(case["color"]),
            label=str(case["label"]),
        )
    ax.axvline(0.145, color="#D55E00", linestyle=":", linewidth=1.1)
    ax.axvline(0.165, color="#56B4E9", linestyle=":", linewidth=1.1)
    ax.axvline(0.170, color="#0072B2", linestyle=":", linewidth=1.1)
    ax.set_xlabel("Applied displacement U")
    ax.set_ylabel("Reaction force Fy")
    ax.set_title("FEM monotonic notch representation comparison")
    ax.grid(True, color="0.88", linewidth=0.7)
    ax.legend(frameon=False, fontsize=8.5)
    fig.savefig(OUT / "fem_void_vs_soft_hist0_load_displacement.png", dpi=240)
    fig.savefig(OUT / "fem_void_vs_soft_hist0_load_displacement.pdf")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    load = pd.concat([read_load(case) for case in CASES], ignore_index=True)
    summary = summarize(load)
    load.to_csv(OUT / "fem_void_vs_soft_hist0_load_displacement.csv", index=False)
    summary.to_csv(OUT / "fem_void_vs_soft_hist0_summary.csv", index=False)
    plot_load(load)
    print(OUT / "fem_void_vs_soft_hist0_summary.csv")
    print(OUT / "fem_void_vs_soft_hist0_load_displacement.png")


if __name__ == "__main__":
    main()
