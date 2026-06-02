#!/usr/bin/env python3
"""Analyze the strict FEM-mesh FBPINN-chain discriminator against FEM n_step2."""
from __future__ import annotations

from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "_analysis_fem_mechanism_20260528"
EXPERIMENT = ANALYSIS / "experiments" / "fbpinn_chain_discriminator_20260530"
SYNC = EXPERIMENT / "0_sync" / "taobo_sens"
OUT_ANALYSIS = EXPERIMENT / "1_analysis"
OUT_FIG = EXPERIMENT / "2_figures"

ARCHIVE = (
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
    "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
    "N100_R0.0_Umax0.12_femmesh_softHist0_fbpinnChain_n6_wr0.12_"
    "x0.0to0.45_h3_n80_warm1500_j10000"
)

FEM_MAT = (
    ANALYSIS
    / "request21_fem_nstep"
    / "source_handoff"
    / "_pidl_handoff_reverseBC_u12_soft_hist0_nstep2_2026-05-29"
    / "reverseBC_u12_soft_hist0_nstep2_element_fields_c1_c70.mat"
)
FEM_CSV = (
    ANALYSIS
    / "request21_fem_nstep"
    / "source_handoff"
    / "_pidl_handoff_reverseBC_u12_soft_hist0_nstep2_2026-05-29"
    / "reverseBC_u12_soft_hist0_nstep2_cyclewise_mechanism_metrics.csv"
)

CYCLES = (20, 40, 69)
FIELDS = ("damage_alpha", "alpha_bar", "psi_raw", "g_alpha", "psi_active")
METRICS = ("tip_2l0_mean", "p99", "max", "domain_mean", "right_band_mean")


def load_fem() -> dict[str, object]:
    with h5py.File(FEM_MAT, "r") as h5:
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
            "damage_alpha": d,
            "alpha_bar": alpha_bar,
            "psi_raw": psi_raw,
            "g_alpha": g_alpha,
            "psi_active": g_alpha * psi_raw,
        },
    }


def fem_cycle_index(cycles: np.ndarray, cycle: int) -> int:
    idx = np.where(cycles == cycle)[0]
    if len(idx) != 1:
        raise KeyError(f"FEM cycle {cycle} not found")
    return int(idx[0])


def weighted_mean(values: np.ndarray, areas: np.ndarray, mask: np.ndarray) -> float:
    m = mask & np.isfinite(values)
    if not np.any(m):
        return float("nan")
    return float(np.sum(values[m] * areas[m]) / np.sum(areas[m]))


def reduce_metrics(values: np.ndarray, areas: np.ndarray, xy: np.ndarray) -> dict[str, float]:
    finite = np.isfinite(values)
    r = np.hypot(xy[:, 0], xy[:, 1])
    return {
        "max": float(np.nanmax(values)),
        "p999": float(np.nanpercentile(values[finite], 99.9)),
        "p99": float(np.nanpercentile(values[finite], 99.0)),
        "domain_mean": weighted_mean(values, areas, finite),
        "tip_2l0_mean": weighted_mean(values, areas, r <= 0.02),
        "tip_5l0_mean": weighted_mean(values, areas, r <= 0.05),
        "right_band_mean": weighted_mean(values, areas, xy[:, 0] >= 0.45),
    }


def project_to_pidl(fem_values: np.ndarray, fem_xy: np.ndarray, pidl_xy: np.ndarray) -> np.ndarray:
    tree = cKDTree(fem_xy)
    _, idx = tree.query(pidl_xy, k=1)
    return fem_values[idx]


def pidl_diag_path(cycle: int) -> Path:
    path = SYNC / ARCHIVE / "element_diagnostics" / f"element_fields_cycle_{cycle:04d}.npz"
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def load_pidl(cycle: int) -> dict[str, np.ndarray]:
    raw = np.load(pidl_diag_path(cycle))
    return {
        "xy": np.column_stack([raw["elem_x"], raw["elem_y"]]),
        "area": raw["area_elem"],
        "fields": {
            "damage_alpha": raw["alpha_elem"],
            "alpha_bar": raw["hist_fat_elem"],
            "psi_raw": raw["psi_raw_elem"],
            "g_alpha": raw["g_alpha_elem"],
            "psi_active": raw["psi_active_elem"],
        },
        "energy": {
            "E_el": float(np.nansum(raw["E_el_elem"])),
            "E_d": float(np.nansum(raw["E_d_elem"])),
            "E_hist": float(np.nansum(raw["E_hist_elem"])),
        },
    }


def build_field_table() -> pd.DataFrame:
    fem = load_fem()
    rows: list[dict[str, object]] = []
    for cycle in CYCLES:
        pidl = load_pidl(cycle)
        fidx = fem_cycle_index(fem["cycles"], cycle)
        for field in FIELDS:
            fem_projected = project_to_pidl(
                fem["fields"][field][fidx], fem["centroids"], pidl["xy"]
            )
            fem_metrics = reduce_metrics(fem_projected, pidl["area"], pidl["xy"])
            pidl_metrics = reduce_metrics(pidl["fields"][field], pidl["area"], pidl["xy"])
            for metric, fem_value in fem_metrics.items():
                pidl_value = pidl_metrics[metric]
                rows.append(
                    {
                        "cycle": cycle,
                        "field": field,
                        "metric": metric,
                        "FEM_nstep2_projected": fem_value,
                        "PIDL_fbpinn": pidl_value,
                        "PIDL_over_FEM": (
                            pidl_value / fem_value
                            if np.isfinite(fem_value) and abs(fem_value) > 1e-30
                            else np.nan
                        ),
                    }
                )
        energy = load_pidl(cycle)["energy"]
        for key, val in energy.items():
            rows.append(
                {
                    "cycle": cycle,
                    "field": key,
                    "metric": "integral_from_pidl_diag",
                    "FEM_nstep2_projected": np.nan,
                    "PIDL_fbpinn": val,
                    "PIDL_over_FEM": np.nan,
                }
            )
    return pd.DataFrame(rows)


def build_scalar_summary() -> pd.DataFrame:
    d = SYNC / ARCHIVE / "best_models"
    ab = np.load(d / "alpha_bar_vs_cycle.npy")
    xt = np.load(d / "x_tip_alpha_vs_cycle.npy")
    kt = np.load(d / "Kt_vs_cycle.npy")
    eel = np.load(d / "E_el_vs_cycle.npy")
    fem_metrics = pd.read_csv(FEM_CSV)
    row69 = fem_metrics[fem_metrics["cycle"] == 69].iloc[0].to_dict()
    return pd.DataFrame(
        [
            {
                "case": "PIDL FBPINN-chain",
                "n_saved": len(ab),
                "first_boundary_hit": (
                    int(np.argmax(xt >= 0.5)) if np.any(xt >= 0.5) else np.nan
                ),
                "last_index": len(ab) - 1,
                "x_tip_alpha_j68": float(xt[68]),
                "x_tip_alpha_last": float(xt[-1]),
                "alpha_bar_max_j68": float(ab[68, 0]),
                "alpha_bar_max_last": float(ab[-1, 0]),
                "f_min_j68": float(ab[68, 2]),
                "f_min_last": float(ab[-1, 2]),
                "Kt_j68": float(kt[68]),
                "Kt_last": float(kt[-1]),
                "E_el_j68": float(eel[68]),
                "E_el_last": float(eel[-1]),
                "FEM_nstep2_Nf": 70,
                "FEM_c69_alpha_bar_elem_max": row69.get("alpha_bar_elem_max", np.nan),
                "FEM_c69_f_fatigue_min": row69.get("f_fatigue_min", np.nan),
                "FEM_c69_Kt_proxy": row69.get("Kt_proxy", np.nan),
            }
        ]
    )


def plot_field_gate(table: pd.DataFrame) -> Path:
    labels = [
        ("damage_alpha", "tip_2l0_mean", "damage tip2"),
        ("alpha_bar", "tip_2l0_mean", "alpha_bar tip2"),
        ("psi_raw", "tip_2l0_mean", "psi_raw tip2"),
        ("g_alpha", "tip_2l0_mean", "g(alpha) tip2"),
        ("psi_active", "tip_2l0_mean", "psi_active tip2"),
        ("alpha_bar", "p99", "alpha_bar p99"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(13.2, 7.0), constrained_layout=True)
    for ax, (field, metric, title) in zip(axes.ravel(), labels):
        sub = table[(table["field"] == field) & (table["metric"] == metric)].sort_values("cycle")
        ax.plot(sub["cycle"], sub["PIDL_over_FEM"], marker="o", lw=1.6, color="#0072B2")
        ax.axhline(1.0, color="0.45", lw=1.0, ls="--")
        ax.set_title(title)
        ax.set_xlabel("cycle")
        ax.set_ylabel("FBPINN / FEM n_step2")
        ax.grid(alpha=0.25)
        if field in {"psi_active", "alpha_bar"}:
            ax.set_yscale("symlog", linthresh=0.05)
    fig.suptitle("FBPINN-chain field gate against FEM n_step2")
    out = OUT_FIG / "fbpinn_chain_vs_fem_nstep2_field_gate.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def plot_c69_residuals() -> Path:
    fem = load_fem()
    pidl = load_pidl(69)
    fidx = fem_cycle_index(fem["cycles"], 69)
    panels = [("alpha_bar", "alpha_bar"), ("psi_active", "active psi")]
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.6), constrained_layout=True)
    for row, (field, label) in enumerate(panels):
        fem_projected = project_to_pidl(fem["fields"][field][fidx], fem["centroids"], pidl["xy"])
        pidl_values = pidl["fields"][field]
        diff = pidl_values - fem_projected
        vmax = float(np.nanpercentile(np.r_[fem_projected, pidl_values], 99.5))
        vmax = max(vmax, 1e-12)
        dv = float(np.nanpercentile(np.abs(diff), 99.5))
        dv = max(dv, 1e-12)
        for col, (values, title, cmap, vmin, vmax_i) in enumerate(
            [
                (fem_projected, f"FEM {label}", "magma", 0.0, vmax),
                (pidl_values, f"FBPINN {label}", "magma", 0.0, vmax),
                (diff, "FBPINN - FEM", "RdBu_r", -dv, dv),
            ]
        ):
            ax = axes[row, col]
            sc = ax.scatter(
                pidl["xy"][:, 0],
                pidl["xy"][:, 1],
                c=values,
                s=1.0,
                cmap=cmap,
                vmin=vmin,
                vmax=vmax_i,
                rasterized=True,
            )
            ax.set_aspect("equal")
            ax.set_xlim(-0.05, 0.50)
            ax.set_ylim(-0.08, 0.08)
            ax.set_title(title)
            ax.set_xlabel("x")
            if col == 0:
                ax.set_ylabel("y")
            fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.02)
    fig.suptitle("c69 residual fields on PIDL/FEM common probe geometry")
    out = OUT_FIG / "fbpinn_chain_vs_fem_nstep2_c69_residual_fields.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def write_report(table: pd.DataFrame, scalar: pd.DataFrame, figs: list[Path]) -> Path:
    OUT_ANALYSIS.mkdir(parents=True, exist_ok=True)
    compact = table[
        (table["cycle"] == 69)
        & (table["metric"].isin(["tip_2l0_mean", "p99", "max", "domain_mean"]))
        & (table["field"].isin(FIELDS))
    ].copy()
    wide = compact.pivot_table(
        index=["field", "metric"],
        values="PIDL_over_FEM",
        aggfunc="first",
    ).reset_index()
    lines = [
        "# FBPINN-Chain vs FEM n_step2 Result",
        "",
        "Reference: FEM Request21 `n_step=2 [1,0]`, projected by nearest element centroid onto PIDL diagnostic elements.",
        "",
        "## Scalar Timing",
        "",
        scalar.to_markdown(index=False),
        "",
        "## c69 Field Gate Ratios",
        "",
        wide.to_markdown(index=False, floatfmt=".4g"),
        "",
        "## Reading",
        "",
        "FBPINN-chain changes the failure mode: it does not hit the right boundary by j99, unlike the strict baseline/local-patch cases.  That is useful negative/diagnostic evidence because local subdomain authority can suppress boundary saturation.",
        "",
        "It does not close the FEM mechanism.  At the matched c69 field gate, the crack-tip `alpha_bar` remains far below FEM and the active degraded driver remains much smaller than FEM.  The residual field also shows the active driver is off-location: FBPINN creates an interior active-psi packet around the middle of the crack path, while the FEM n_step2 field is already concentrated near the right process region.  The branch therefore trades the old boundary-saturation failure for slow/underdriven crack advance.",
        "",
        "Decision: do not rerun the same FBPINN-chain as a solution.  Use it as evidence that stronger local representation affects propagation mode, then test a true split-trunk/alternating solve only if it includes head-wise gradients and the same c20/c40/c69 field gate.",
        "",
        "Generated figures:",
    ]
    lines.extend(f"- `{p}`" for p in figs)
    out = OUT_ANALYSIS / "fbpinn_chain_vs_fem_nstep2_result.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> None:
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    table = build_field_table()
    scalar = build_scalar_summary()
    table_path = OUT_FIG / "fbpinn_chain_vs_fem_nstep2_field_gate.csv"
    scalar_path = OUT_FIG / "fbpinn_chain_vs_fem_nstep2_scalar_summary.csv"
    table.to_csv(table_path, index=False)
    scalar.to_csv(scalar_path, index=False)
    figs = [plot_field_gate(table), plot_c69_residuals()]
    report = write_report(table, scalar, figs)
    print(f"wrote {table_path}")
    print(f"wrote {scalar_path}")
    for fig in figs:
        print(f"wrote {fig}")
    print(f"wrote {report}")


if __name__ == "__main__":
    main()
