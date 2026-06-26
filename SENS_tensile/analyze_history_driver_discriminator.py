#!/usr/bin/env python3
"""Analyze history-driver discriminator outputs against FEM n_step=2.

Inputs are lightweight Taobo sync artifacts: scalar histories and
element_diagnostics_history_driver_*/*.npz.  PIDL saved index j maps to FEM
cycle c=j+1 under the strict state-timing convention.
"""
from __future__ import annotations

from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "_analysis_fem_mechanism_20260528"
EXPERIMENT = ANALYSIS / "experiments" / "history_driver_discriminator_20260602"
SYNC = EXPERIMENT / "0_sync" / "taobo_sens"
OUT_ANALYSIS = EXPERIMENT / "1_analysis"
OUT_FIG = EXPERIMENT / "2_figures"
NSTEP2_MAT = (
    ANALYSIS
    / "request21_fem_nstep"
    / "source_handoff"
    / "_pidl_handoff_reverseBC_u12_soft_hist0_nstep2_2026-05-29"
    / "reverseBC_u12_soft_hist0_nstep2_element_fields_c1_c70.mat"
)
NSTEP2_CSV = (
    ANALYSIS
    / "request21_fem_nstep"
    / "source_handoff"
    / "_pidl_handoff_reverseBC_u12_soft_hist0_nstep2_2026-05-29"
    / "reverseBC_u12_soft_hist0_nstep2_cyclewise_mechanism_metrics.csv"
)

MODES = ("current_active", "lagged_g", "raw")
MODE_LABEL = {
    "current_active": "current active",
    "lagged_g": "lagged g",
    "raw": "raw driver",
}
MODE_ARCHIVE = {
    mode: (
        "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
        "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
        f"N100_R0.0_Umax0.12_femmesh_softHist0_{mode}"
    )
    for mode in MODES
}
SAVED_TO_FEM = {0: 1, 1: 2, 2: 3, 19: 20, 39: 40, 68: 69}
FIELDS = ("alpha_bar", "delta_alpha_bar", "psi_raw", "g_alpha", "psi_active", "history_driver")
KEY_METRICS = ("tip_2l0_mean", "p99", "max", "domain_mean")


def load_fem() -> dict[str, object]:
    with h5py.File(NSTEP2_MAT, "r") as h5:
        cycles = np.asarray(h5["cycles"]).reshape(-1).astype(int)
        centroids = np.asarray(h5["element_centroids"], dtype=float).T
        if float(np.nanmax(centroids[:, 0])) > 0.75:
            centroids[:, :2] -= 0.5
        areas = np.asarray(h5["element_area"], dtype=float).reshape(-1)
        d = np.asarray(h5["d_elem"], dtype=float)
        alpha_bar = np.asarray(h5["alpha_bar_elem"], dtype=float)
        psi_raw = np.asarray(h5["psi_plus_elem"], dtype=float)
        if d.shape[0] != len(cycles):
            d = d.T
            alpha_bar = alpha_bar.T
            psi_raw = psi_raw.T
    g_alpha = (1.0 - d) ** 2 + 1e-6
    return {
        "cycles": cycles,
        "centroids": centroids,
        "areas": areas,
        "fields": {
            "alpha_bar": alpha_bar,
            "psi_raw": psi_raw,
            "g_alpha": g_alpha,
            "psi_active": g_alpha * psi_raw,
        },
    }


def cycle_index(cycles: np.ndarray, cycle: int) -> int:
    idx = np.where(cycles == cycle)[0]
    if len(idx) != 1:
        raise KeyError(f"FEM cycle {cycle} not found")
    return int(idx[0])


def weighted_mean(values: np.ndarray, areas: np.ndarray, mask: np.ndarray) -> float:
    m = mask & np.isfinite(values)
    if not np.any(m):
        return float("nan")
    return float(np.sum(values[m] * areas[m]) / np.sum(areas[m]))


def metrics(values: np.ndarray, areas: np.ndarray, centroids: np.ndarray) -> dict[str, float]:
    finite = np.isfinite(values)
    r = np.hypot(centroids[:, 0], centroids[:, 1])
    if not np.any(finite):
        return {
            "max": float("nan"),
            "p999": float("nan"),
            "p99": float("nan"),
            "domain_mean": float("nan"),
            "tip_2l0_mean": float("nan"),
            "tip_2l0_integral": float("nan"),
            "right_band_mean": float("nan"),
        }
    out = {
        "max": float(np.nanmax(values)),
        "p999": float(np.nanpercentile(values[finite], 99.9)),
        "p99": float(np.nanpercentile(values[finite], 99.0)),
        "domain_mean": weighted_mean(values, areas, finite),
        "tip_2l0_mean": weighted_mean(values, areas, r <= 0.02),
        "tip_2l0_integral": float(np.nansum(values[r <= 0.02] * areas[r <= 0.02])),
        "right_band_mean": weighted_mean(values, areas, centroids[:, 0] >= 0.45),
    }
    return out


def project_nearest(fem_values: np.ndarray, fem_centroids: np.ndarray, pidl_centroids: np.ndarray) -> np.ndarray:
    # Both meshes are already close in this strict FEM-mesh diagnostic.  Nearest
    # projection is enough for reductions and avoids needing node connectivity
    # in the synced PIDL artifacts.
    tree = cKDTree(fem_centroids)
    _, idx = tree.query(pidl_centroids, k=1)
    return fem_values[idx]


def load_pidl_npz(mode: str, saved_idx: int) -> dict[str, np.ndarray]:
    d = SYNC / MODE_ARCHIVE[mode] / f"element_diagnostics_history_driver_{mode}"
    path = d / f"element_fields_cycle_{saved_idx:04d}.npz"
    if not path.exists():
        raise FileNotFoundError(path)
    raw = np.load(path)
    return {k: raw[k] for k in raw.files}


def pidl_delta_alpha_bar(raw: dict[str, np.ndarray]) -> np.ndarray:
    if "delta_alpha_bar_input_elem" in raw:
        return raw["delta_alpha_bar_input_elem"]
    # Legacy diagnostics did not save the increment separately.  Do not infer
    # it from the history driver; that would mix driver magnitude with increment.
    return np.full_like(raw["hist_fat_elem"], np.nan, dtype=float)


def fields_from_npz(raw: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        "alpha_bar": raw["hist_fat_elem"],
        "delta_alpha_bar": pidl_delta_alpha_bar(raw),
        "psi_raw": raw["psi_raw_elem"],
        "g_alpha": raw["g_alpha_elem"],
        "psi_active": raw["psi_active_elem"],
        "history_driver": raw["psi_history_driver_elem"],
    }


def build_field_ratios() -> pd.DataFrame:
    fem = load_fem()
    rows: list[dict[str, object]] = []
    for mode in MODES:
        for saved_idx, fem_cycle in SAVED_TO_FEM.items():
            pidl_raw = load_pidl_npz(mode, saved_idx)
            pidl_centroids = np.column_stack([pidl_raw["elem_x"], pidl_raw["elem_y"]])
            pidl_areas = pidl_raw["area_elem"]
            pidl_fields = fields_from_npz(pidl_raw)
            fidx = cycle_index(fem["cycles"], fem_cycle)
            fem_fields = {
                "alpha_bar": fem["fields"]["alpha_bar"][fidx],
                "psi_raw": fem["fields"]["psi_raw"][fidx],
                "g_alpha": fem["fields"]["g_alpha"][fidx],
                "psi_active": fem["fields"]["psi_active"][fidx],
            }
            if fem_cycle == 1:
                fem_fields["delta_alpha_bar"] = fem_fields["alpha_bar"]
            else:
                prev = cycle_index(fem["cycles"], fem_cycle - 1)
                fem_fields["delta_alpha_bar"] = (
                    fem_fields["alpha_bar"] - fem["fields"]["alpha_bar"][prev]
                )
            fem_fields["history_driver"] = fem_fields["delta_alpha_bar"]

            for field in FIELDS:
                fem_projected = project_nearest(
                    fem_fields[field], fem["centroids"], pidl_centroids
                )
                fem_metrics = metrics(fem_projected, pidl_areas, pidl_centroids)
                pidl_metrics = metrics(pidl_fields[field], pidl_areas, pidl_centroids)
                for metric, fem_value in fem_metrics.items():
                    pidl_value = pidl_metrics[metric]
                    rows.append(
                        {
                            "mode": mode,
                            "mode_label": MODE_LABEL[mode],
                            "saved_index": saved_idx,
                            "fem_cycle": fem_cycle,
                            "field": field,
                            "metric": metric,
                            "FEM_nstep2_projected": fem_value,
                            "PIDL": pidl_value,
                            "PIDL_over_FEM": pidl_value / fem_value
                            if np.isfinite(fem_value) and abs(fem_value) > 1e-30
                            else np.nan,
                        }
                    )
    return pd.DataFrame(rows)


def build_scalar_summary() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for mode in MODES:
        d = SYNC / MODE_ARCHIVE[mode]
        ab = np.load(d / "best_models" / "alpha_bar_vs_cycle.npy")
        xt = np.load(d / "best_models" / "x_tip_alpha_vs_cycle.npy")
        kt = np.load(d / "best_models" / "Kt_vs_cycle.npy")
        eel = np.load(d / "best_models" / "E_el_vs_cycle.npy")
        rows.append(
            {
                "mode": mode,
                "mode_label": MODE_LABEL[mode],
                "n_saved": len(ab),
                "first_boundary_hit": int(np.argmax(xt >= 0.5)) if np.any(xt >= 0.5) else np.nan,
                "confirmed_stop_index": len(ab) - 1,
                "alpha_bar_max_final": float(ab[-1, 0]),
                "alpha_bar_mean_final": float(ab[-1, 1]),
                "f_min_final": float(ab[-1, 2]),
                "Kt_final": float(kt[-1]),
                "E_el_final": float(eel[-1]),
            }
        )
    return pd.DataFrame(rows)


def plot_gate(field_ratios: pd.DataFrame, scalar: pd.DataFrame) -> Path:
    selected = [
        ("alpha_bar", "tip_2l0_mean", "alpha_bar tip2"),
        ("delta_alpha_bar", "tip_2l0_mean", "Delta alpha_bar tip2"),
        ("psi_raw", "tip_2l0_mean", "psi_raw tip2"),
        ("g_alpha", "tip_2l0_mean", "g(alpha) tip2"),
        ("psi_active", "tip_2l0_mean", "psi_active tip2"),
        ("history_driver", "tip_2l0_mean", "history driver tip2"),
    ]
    colors = {"current_active": "#0072B2", "lagged_g": "#D55E00", "raw": "#009E73"}
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.2), constrained_layout=True)
    for ax, (field, metric, title) in zip(axes.ravel(), selected):
        for mode in MODES:
            sub = field_ratios[
                (field_ratios["mode"] == mode)
                & (field_ratios["field"] == field)
                & (field_ratios["metric"] == metric)
            ].sort_values("fem_cycle")
            ax.plot(
                sub["fem_cycle"],
                sub["PIDL_over_FEM"],
                marker="o",
                lw=1.5,
                color=colors[mode],
                label=MODE_LABEL[mode],
            )
        ax.axhline(1.0, color="0.45", ls="--", lw=1)
        ax.set_title(title)
        ax.set_xlabel("FEM cycle")
        ax.set_ylabel("PIDL / FEM n_step2")
        ax.grid(alpha=0.25)
        if field in {"delta_alpha_bar", "psi_active", "history_driver"}:
            ax.set_yscale("symlog", linthresh=0.05)
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle("History-driver discriminator: field-level gate vs FEM n_step2")
    out = OUT_FIG / "history_driver_discriminator_field_gate.png"
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
    ax.bar(scalar["mode_label"], scalar["first_boundary_hit"], color=[colors[m] for m in scalar["mode"]])
    ax.axhline(70, color="0.2", ls="--", lw=1.2, label="FEM n_step2 N_f=70")
    ax.set_ylabel("first boundary hit / cycle index")
    ax.set_title("History driver changes history magnitude, not event timing enough")
    ax.legend(frameon=False)
    out2 = OUT_FIG / "history_driver_discriminator_event_timing.png"
    fig.savefig(out2, dpi=220)
    plt.close(fig)
    return out


def write_report(field_ratios: pd.DataFrame, scalar: pd.DataFrame) -> Path:
    OUT_ANALYSIS.mkdir(parents=True, exist_ok=True)
    report = OUT_ANALYSIS / "history_driver_discriminator_result.md"
    key = field_ratios[
        (field_ratios["fem_cycle"] == 69)
        & (field_ratios["metric"] == "tip_2l0_mean")
        & field_ratios["field"].isin(["alpha_bar", "delta_alpha_bar", "psi_raw", "g_alpha", "psi_active", "history_driver"])
    ]
    pivot = key.pivot(index="mode_label", columns="field", values="PIDL_over_FEM")
    lines = [
        "# History-Driver Discriminator Result",
        "",
        "Reference: FEM Request21 `n_step=2 [1,0]`. PIDL saved index `j` maps to FEM cycle `c=j+1`.",
        "",
        "## Event Timing",
        "",
        "| mode | first boundary hit | confirmed stop | final alpha_bar max | final f_min |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, row in scalar.iterrows():
        lines.append(
            f"| {row['mode_label']} | {int(row['first_boundary_hit'])} | "
            f"{int(row['confirmed_stop_index'])} | {row['alpha_bar_max_final']:.4g} | "
            f"{row['f_min_final']:.4g} |"
        )
    lines += [
        "",
        "## c69 Tip-Region Ratios",
        "",
        "| mode | alpha_bar | Delta alpha_bar | psi_raw | g(alpha) | psi_active | history driver |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for mode_label, row in pivot.iterrows():
        lines.append(
            f"| {mode_label} | {row.get('alpha_bar', np.nan):.4g} | "
            f"{row.get('delta_alpha_bar', np.nan):.4g} | "
            f"{row.get('psi_raw', np.nan):.4g} | "
            f"{row.get('g_alpha', np.nan):.4g} | "
            f"{row.get('psi_active', np.nan):.4g} | "
            f"{row.get('history_driver', np.nan):.4g} |"
        )
    lines += [
        "",
        "## Reading",
        "",
        "`lagged_g` and `raw` dramatically increase the accumulated history magnitude, "
        "but neither moves the event timing close to FEM `N_f=70`. The field gate is "
        "therefore more important than scalar `alpha_bar_max`: the driver can become "
        "huge while still not repairing the FEM-like process-zone evolution.",
        "",
        "Generated files:",
        "",
        f"- `{OUT_FIG / 'history_driver_discriminator_field_gate.csv'}`",
        f"- `{OUT_FIG / 'history_driver_discriminator_scalar_summary.csv'}`",
        f"- `{OUT_FIG / 'history_driver_discriminator_field_gate.png'}`",
        f"- `{OUT_FIG / 'history_driver_discriminator_event_timing.png'}`",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    field_ratios = build_field_ratios()
    scalar = build_scalar_summary()
    field_ratios.to_csv(OUT_FIG / "history_driver_discriminator_field_gate.csv", index=False)
    scalar.to_csv(OUT_FIG / "history_driver_discriminator_scalar_summary.csv", index=False)
    plot_gate(field_ratios, scalar)
    report = write_report(field_ratios, scalar)
    print(scalar.to_string(index=False))
    key = field_ratios[
        (field_ratios["fem_cycle"] == 69)
        & (field_ratios["metric"] == "tip_2l0_mean")
        & field_ratios["field"].isin(["alpha_bar", "delta_alpha_bar", "psi_raw", "g_alpha", "psi_active", "history_driver"])
    ]
    print(key[["mode_label", "field", "PIDL_over_FEM"]].to_string(index=False))
    print(f"wrote {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
