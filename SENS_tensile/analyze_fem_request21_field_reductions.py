#!/usr/bin/env python3
"""Analyze FEM Request 21 field reductions after OneDrive hydration.

Compares the strict soft-hist0 FEM reference against the Request 21
within-cycle cadence controls using common scalar reductions and recomputed
near-tip integrals from the exported MAT fields.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "_analysis_fem_mechanism_20260528" / "request21_fem_nstep"
FIG_DIR = ROOT / "_analysis_fem_mechanism_20260528" / "figures"
ONEDRIVE = (
    Path.home()
    / "Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result"
)
SOURCE_HANDOFF = ANALYSIS_DIR / "source_handoff"

RADII = (0.01, 0.02, 0.04)
RADIUS_LABELS = ("r1ell", "r2ell", "r4ell")
SELECTED_CYCLES = (1, 20, 40, 69, 70)


@dataclass(frozen=True)
class RunSpec:
    key: str
    label: str
    csv_path: Path
    mat_path: Path
    retained_loads: tuple[float, ...]
    nf: int


RUNS = [
    RunSpec(
        key="standard",
        label="standard [0.25,0.5,0.75,1,0]",
        csv_path=ONEDRIVE
        / "_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28"
        / "reverseBC_u12_diffuse_precrack_soft_hist0_cyclewise_mechanism_metrics.csv",
        mat_path=ONEDRIVE
        / "_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28"
        / "reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_c69.mat",
        retained_loads=(0.25, 0.5, 0.75, 1.0, 0.0),
        nf=69,
    ),
    RunSpec(
        key="nstep2",
        label="n_step=2 [1,0]",
        csv_path=SOURCE_HANDOFF
        / "_pidl_handoff_reverseBC_u12_soft_hist0_nstep2_2026-05-29"
        / "reverseBC_u12_soft_hist0_nstep2_cyclewise_mechanism_metrics.csv",
        mat_path=SOURCE_HANDOFF
        / "_pidl_handoff_reverseBC_u12_soft_hist0_nstep2_2026-05-29"
        / "reverseBC_u12_soft_hist0_nstep2_element_fields_c1_c70.mat",
        retained_loads=(1.0, 0.0),
        nf=70,
    ),
    RunSpec(
        key="nstep3",
        label="n_step=3 [0.5,1,0]",
        csv_path=SOURCE_HANDOFF
        / "_pidl_handoff_reverseBC_u12_soft_hist0_nstep3_2026-05-29"
        / "reverseBC_u12_soft_hist0_nstep3_cyclewise_mechanism_metrics.csv",
        mat_path=SOURCE_HANDOFF
        / "_pidl_handoff_reverseBC_u12_soft_hist0_nstep3_2026-05-29"
        / "reverseBC_u12_soft_hist0_nstep3_element_fields_c1_c70.mat",
        retained_loads=(0.5, 1.0, 0.0),
        nf=70,
    ),
    RunSpec(
        key="nstep10",
        label="n_step=10 [0.2,0.4,0.6,0.8,1,0]",
        csv_path=SOURCE_HANDOFF
        / "_pidl_handoff_reverseBC_u12_soft_hist0_nstep10_2026-05-29"
        / "reverseBC_u12_soft_hist0_nstep10_cyclewise_mechanism_metrics.csv",
        mat_path=SOURCE_HANDOFF
        / "_pidl_handoff_reverseBC_u12_soft_hist0_nstep10_2026-05-29"
        / "reverseBC_u12_soft_hist0_nstep10_element_fields_c1_c69.mat",
        retained_loads=(0.2, 0.4, 0.6, 0.8, 1.0, 0.0),
        nf=69,
    ),
]


def load_mat_fields(path: Path) -> dict[str, np.ndarray]:
    with h5py.File(path, "r") as mat:
        return {
            "cycles": np.asarray(mat["cycles"]).ravel().astype(int),
            "centroids": np.asarray(mat["element_centroids"]).T,
            "area": np.asarray(mat["element_area"]).ravel(),
            "d": np.asarray(mat["d_elem"]),
            "alpha": np.asarray(mat["alpha_bar_elem"]),
            "f": np.asarray(mat["f_fatigue_elem"]),
            "psi": np.asarray(mat["psi_plus_elem"]),
        }


def near_tip_xy(row: pd.Series) -> tuple[float, float]:
    for suffix in ("095", "090", "050"):
        x = row.get(f"x_tip_d{suffix}")
        y = row.get(f"y_tip_d{suffix}")
        if pd.notna(x) and pd.notna(y):
            return float(x), float(y)
    return np.nan, np.nan


def add_near_tip_integrals(table: pd.DataFrame, mat_fields: dict[str, np.ndarray]) -> pd.DataFrame:
    centroids = mat_fields["centroids"]
    area = mat_fields["area"]
    cycles = mat_fields["cycles"]
    cycle_to_index = {int(c): i for i, c in enumerate(cycles)}
    fields = {
        "d": mat_fields["d"],
        "alpha_bar": mat_fields["alpha"],
        "f_fatigue": mat_fields["f"],
        "psi_plus": mat_fields["psi"],
    }

    for field_name in fields:
        for label in RADIUS_LABELS:
            table[f"common_near_tip_int_{field_name}_{label}"] = np.nan

    for idx, row in table.iterrows():
        cycle = int(row["cycle"])
        if cycle not in cycle_to_index:
            continue
        x_tip, y_tip = near_tip_xy(row)
        if not np.isfinite(x_tip) or not np.isfinite(y_tip):
            continue
        distance = np.hypot(centroids[:, 0] - x_tip, centroids[:, 1] - y_tip)
        field_index = cycle_to_index[cycle]
        for radius, label in zip(RADII, RADIUS_LABELS):
            mask = distance <= radius
            for field_name, values in fields.items():
                table.loc[idx, f"common_near_tip_int_{field_name}_{label}"] = float(
                    np.nansum(values[field_index, mask] * area[mask])
                )
    return table


def load_run(spec: RunSpec) -> pd.DataFrame:
    table = pd.read_csv(spec.csv_path)
    mat_fields = load_mat_fields(spec.mat_path)
    table = add_near_tip_integrals(table, mat_fields)
    table.insert(0, "variant", spec.key)
    table.insert(1, "variant_label", spec.label)
    table["retained_positive_load_count"] = sum(v > 1.0e-12 for v in spec.retained_loads)
    table["retained_state_count"] = len(spec.retained_loads)
    table["nf"] = spec.nf
    return table


def safe_ratio(numer: float, denom: float) -> float:
    if not np.isfinite(numer) or not np.isfinite(denom) or abs(denom) < 1e-30:
        return np.nan
    return numer / denom


def build_selected_ratios(long_df: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "E_d",
        "alpha_bar_elem_max",
        "alpha_bar_elem_p999",
        "alpha_bar_elem_p99",
        "psi_plus_elem_max",
        "psi_plus_elem_p999",
        "psi_plus_elem_p99",
        "common_near_tip_int_alpha_bar_r2ell",
        "common_near_tip_int_psi_plus_r2ell",
        "x_tip_d095",
        "Kt_proxy",
    ]
    rows: list[dict[str, float | str | int]] = []
    standard = long_df[long_df["variant"] == "standard"].set_index("cycle")
    for _, row in long_df[long_df["cycle"].isin(SELECTED_CYCLES)].iterrows():
        cycle = int(row["cycle"])
        out: dict[str, float | str | int] = {
            "variant": row["variant"],
            "cycle": cycle,
            "nf": int(row["nf"]),
        }
        if cycle not in standard.index:
            continue
        ref = standard.loc[cycle]
        for metric in metrics:
            if metric not in long_df.columns:
                continue
            out[metric] = row.get(metric, np.nan)
            out[f"{metric}_ratio_vs_standard"] = safe_ratio(row.get(metric, np.nan), ref.get(metric, np.nan))
        rows.append(out)
    return pd.DataFrame(rows)


def build_summary(long_df: pd.DataFrame) -> pd.DataFrame:
    c69 = long_df[long_df["cycle"] == 69].copy()
    metrics = [
        "E_d",
        "alpha_bar_elem_max",
        "alpha_bar_elem_p999",
        "alpha_bar_elem_p99",
        "psi_plus_elem_max",
        "psi_plus_elem_p999",
        "psi_plus_elem_p99",
        "common_near_tip_int_alpha_bar_r2ell",
        "common_near_tip_int_psi_plus_r2ell",
        "x_tip_d095",
    ]
    ref = c69[c69["variant"] == "standard"].iloc[0]
    rows = []
    for _, row in c69.iterrows():
        out = {
            "variant": row["variant"],
            "nf": int(row["nf"]),
            "cycle": 69,
            "retained_positive_load_count": int(row["retained_positive_load_count"]),
        }
        for metric in metrics:
            out[metric] = row.get(metric, np.nan)
            out[f"{metric}_ratio_vs_standard"] = safe_ratio(row.get(metric, np.nan), ref.get(metric, np.nan))
        rows.append(out)
    return pd.DataFrame(rows)


def build_final_event_summary(long_df: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "E_d",
        "alpha_bar_elem_max",
        "alpha_bar_elem_p999",
        "alpha_bar_elem_p99",
        "psi_plus_elem_max",
        "psi_plus_elem_p999",
        "psi_plus_elem_p99",
        "common_near_tip_int_alpha_bar_r2ell",
        "common_near_tip_int_psi_plus_r2ell",
        "x_tip_d095",
        "right_boundary_d095_count",
    ]
    standard_final = long_df[(long_df["variant"] == "standard") & (long_df["cycle"] == 69)].iloc[0]
    rows = []
    for spec in RUNS:
        sub = long_df[long_df["variant"] == spec.key]
        row = sub[sub["cycle"] == spec.nf].iloc[0]
        out = {
            "variant": row["variant"],
            "event_cycle": int(row["cycle"]),
            "reference_variant": "standard",
            "reference_cycle": 69,
        }
        for metric in metrics:
            out[metric] = row.get(metric, np.nan)
            out[f"{metric}_ratio_vs_standard_event"] = safe_ratio(
                row.get(metric, np.nan), standard_final.get(metric, np.nan)
            )
        rows.append(out)
    return pd.DataFrame(rows)


def plot_trajectories(long_df: pd.DataFrame) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / "fem_request21_field_reductions_20260530.png"
    palette = {
        "standard": "#000000",
        "nstep2": "#0072B2",
        "nstep3": "#009E73",
        "nstep10": "#D55E00",
    }
    metrics = [
        ("alpha_bar_elem_max", r"$\max(\bar{\alpha})$"),
        ("alpha_bar_elem_p99", r"p99$(\bar{\alpha})$"),
        ("psi_plus_elem_max", r"$\max(\psi^+)$"),
        ("common_near_tip_int_alpha_bar_r2ell", r"$\int_{r \leq 2\ell}\bar{\alpha}\,dA$"),
        ("common_near_tip_int_psi_plus_r2ell", r"$\int_{r \leq 2\ell}\psi^+\,dA$"),
        ("x_tip_d095", r"$x_{\mathrm{tip}}(d\geq0.95)$"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(13.0, 7.2), constrained_layout=True)
    for ax, (metric, ylabel) in zip(axes.ravel(), metrics):
        for spec in RUNS:
            sub = long_df[long_df["variant"] == spec.key]
            ax.plot(
                sub["cycle"],
                sub[metric],
                label=spec.key,
                color=palette[spec.key],
                lw=1.5,
                alpha=0.92,
            )
        ax.set_title(ylabel, fontsize=10)
        ax.set_xlabel("cycle")
        ax.grid(alpha=0.25)
        if "psi_plus" in metric:
            ax.set_yscale("log")
        if metric == "x_tip_d095":
            ax.axhline(0.995, color="0.4", lw=1.0, ls="--")
    axes[0, 0].legend(frameon=False, fontsize=8, loc="upper left")
    fig.suptitle(
        "FEM Request 21 field reductions after OneDrive hydration: cadence variants vs standard",
        fontsize=12,
    )
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def plot_c69_ratio_heatmap(summary: pd.DataFrame) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / "fem_request21_c69_ratio_heatmap_20260530.png"
    metrics = [
        ("E_d", r"$E_d$"),
        ("alpha_bar_elem_max", r"$\max(\bar{\alpha})$"),
        ("alpha_bar_elem_p999", r"p999$(\bar{\alpha})$"),
        ("alpha_bar_elem_p99", r"p99$(\bar{\alpha})$"),
        ("psi_plus_elem_max", r"$\max(\psi^+)$"),
        ("psi_plus_elem_p999", r"p999$(\psi^+)$"),
        ("psi_plus_elem_p99", r"p99$(\psi^+)$"),
        ("common_near_tip_int_alpha_bar_r2ell", r"$\int_{2\ell}\bar{\alpha}$"),
        ("common_near_tip_int_psi_plus_r2ell", r"$\int_{2\ell}\psi^+$"),
        ("x_tip_d095", r"$x_{\mathrm{tip}}$"),
    ]
    variants = ["nstep2", "nstep3", "nstep10"]
    ratio_data = np.array(
        [
            [
                summary.loc[summary["variant"] == variant, f"{metric}_ratio_vs_standard"].iloc[0]
                for metric, _ in metrics
            ]
            for variant in variants
        ],
        dtype=float,
    )
    plot_data = np.log2(ratio_data)

    fig, ax = plt.subplots(figsize=(12.2, 3.6), constrained_layout=True)
    limit = float(np.nanmax(np.abs(plot_data)))
    image = ax.imshow(plot_data, cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks(np.arange(len(metrics)), [label for _, label in metrics], rotation=35, ha="right")
    ax.set_yticks(np.arange(len(variants)), variants)
    ax.set_title("Cycle 69 ratio to standard FEM; colour is log2(ratio), text is raw ratio")
    for i in range(ratio_data.shape[0]):
        for j in range(ratio_data.shape[1]):
            value = ratio_data[i, j]
            ax.text(j, i, f"{value:.3f}", ha="center", va="center", fontsize=8)
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("log2 ratio vs standard")
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def plot_event_ratio_heatmap(summary: pd.DataFrame) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / "fem_request21_event_ratio_heatmap_20260530.png"
    metrics = [
        ("E_d", r"$E_d$"),
        ("alpha_bar_elem_max", r"$\max(\bar{\alpha})$"),
        ("alpha_bar_elem_p999", r"p999$(\bar{\alpha})$"),
        ("alpha_bar_elem_p99", r"p99$(\bar{\alpha})$"),
        ("psi_plus_elem_max", r"$\max(\psi^+)$"),
        ("psi_plus_elem_p999", r"p999$(\psi^+)$"),
        ("psi_plus_elem_p99", r"p99$(\psi^+)$"),
        ("common_near_tip_int_alpha_bar_r2ell", r"$\int_{2\ell}\bar{\alpha}$"),
        ("common_near_tip_int_psi_plus_r2ell", r"$\int_{2\ell}\psi^+$"),
        ("x_tip_d095", r"$x_{\mathrm{tip}}$"),
    ]
    variants = ["nstep2", "nstep3", "nstep10"]
    ratio_data = np.array(
        [
            [
                summary.loc[
                    summary["variant"] == variant,
                    f"{metric}_ratio_vs_standard_event",
                ].iloc[0]
                for metric, _ in metrics
            ]
            for variant in variants
        ],
        dtype=float,
    )
    plot_data = np.log2(ratio_data)

    fig, ax = plt.subplots(figsize=(12.2, 3.6), constrained_layout=True)
    limit = float(np.nanmax(np.abs(plot_data)))
    image = ax.imshow(plot_data, cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks(np.arange(len(metrics)), [label for _, label in metrics], rotation=35, ha="right")
    ax.set_yticks(np.arange(len(variants)), variants)
    ax.set_title("Final/event cycle ratio to standard c69; colour is log2(ratio), text is raw ratio")
    for i in range(ratio_data.shape[0]):
        for j in range(ratio_data.shape[1]):
            value = ratio_data[i, j]
            ax.text(j, i, f"{value:.3f}", ha="center", va="center", fontsize=8)
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("log2 ratio vs standard c69")
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def main() -> int:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    long_df = pd.concat([load_run(spec) for spec in RUNS], ignore_index=True)
    selected = build_selected_ratios(long_df)
    summary = build_summary(long_df)
    event_summary = build_final_event_summary(long_df)

    long_path = ANALYSIS_DIR / "fem_request21_field_reductions_long.csv"
    selected_path = ANALYSIS_DIR / "fem_request21_selected_cycle_ratios.csv"
    summary_path = ANALYSIS_DIR / "fem_request21_c69_summary.csv"
    event_summary_path = ANALYSIS_DIR / "fem_request21_event_summary.csv"
    long_df.to_csv(long_path, index=False)
    selected.to_csv(selected_path, index=False)
    summary.to_csv(summary_path, index=False)
    event_summary.to_csv(event_summary_path, index=False)

    trajectory_png = plot_trajectories(long_df)
    heatmap_png = plot_c69_ratio_heatmap(summary)
    event_heatmap_png = plot_event_ratio_heatmap(event_summary)

    print(f"wrote {long_path}")
    print(f"wrote {selected_path}")
    print(f"wrote {summary_path}")
    print(f"wrote {event_summary_path}")
    print(f"wrote {trajectory_png}")
    print(f"wrote {heatmap_png}")
    print(f"wrote {event_heatmap_png}")
    print(summary[[
        "variant",
        "nf",
        "alpha_bar_elem_max_ratio_vs_standard",
        "psi_plus_elem_max_ratio_vs_standard",
        "common_near_tip_int_alpha_bar_r2ell_ratio_vs_standard",
        "common_near_tip_int_psi_plus_r2ell_ratio_vs_standard",
        "x_tip_d095_ratio_vs_standard",
    ]].to_string(index=False))
    print(event_summary[[
        "variant",
        "event_cycle",
        "alpha_bar_elem_max_ratio_vs_standard_event",
        "psi_plus_elem_max_ratio_vs_standard_event",
        "common_near_tip_int_alpha_bar_r2ell_ratio_vs_standard_event",
        "common_near_tip_int_psi_plus_r2ell_ratio_vs_standard_event",
        "x_tip_d095_ratio_vs_standard_event",
    ]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
