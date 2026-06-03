#!/usr/bin/env python3
"""Analyze the frozen-alpha elastic probe against FEM22 c1 peak fields."""
from __future__ import annotations

from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "_analysis_fem_mechanism_20260528"
EXPERIMENT = ANALYSIS / "experiments" / "frozen_alpha_elastic_20260603"
SYNC = EXPERIMENT / "0_sync"
OUT_ANALYSIS = EXPERIMENT / "1_analysis"
OUT_FIG = EXPERIMENT / "2_figures"
FROZEN_NPZ = SYNC / "frozen_alpha_elastic_fields.npz"
FROZEN_LOSS = SYNC / "frozen_alpha_elastic_loss.csv"
FEM22 = (
    ROOT.parent
    / "Alignment check"
    / "FEM preparation"
    / "nstep2"
    / "fem22_nstep2_c0_c5_whole_fields.mat"
)
COUPLED_CSV = (
    ANALYSIS
    / "experiments"
    / "resstiff_alignment_20260603"
    / "2_figures"
    / "resstiff_epsilon_vs_fem22_field_gate.csv"
)
COUPLED_ACTIVE_CSV = (
    ANALYSIS
    / "experiments"
    / "resstiff_alignment_20260603"
    / "2_figures"
    / "resstiff_vs_fem_nstep2_field_gate.csv"
)

FIELDS = ("eps_xx", "eps_yy", "eps_xy", "eps_trace", "eps_eq", "psi_raw", "psi_active")
METRICS = ("tip_2l0_mean", "domain_mean", "p99", "p999", "max", "min")


def q4_center_strain(coords: np.ndarray, conn: np.ndarray, u_state: np.ndarray) -> np.ndarray:
    dN_dxi = np.array([-0.25, 0.25, 0.25, -0.25])
    dN_deta = np.array([-0.25, -0.25, 0.25, 0.25])
    xy = coords[conn]
    ue = u_state[:, conn].transpose(1, 2, 0)
    eps = np.empty((conn.shape[0], 3), dtype=float)
    for e in range(conn.shape[0]):
        jac = np.array(
            [
                [np.dot(dN_dxi, xy[e, :, 0]), np.dot(dN_deta, xy[e, :, 0])],
                [np.dot(dN_dxi, xy[e, :, 1]), np.dot(dN_deta, xy[e, :, 1])],
            ]
        )
        dN = np.linalg.inv(jac).T @ np.vstack([dN_dxi, dN_deta])
        du_dx = np.dot(dN[0], ue[e, :, 0])
        du_dy = np.dot(dN[1], ue[e, :, 0])
        dv_dx = np.dot(dN[0], ue[e, :, 1])
        dv_dy = np.dot(dN[1], ue[e, :, 1])
        eps[e, 0] = du_dx
        eps[e, 1] = dv_dy
        eps[e, 2] = 0.5 * (du_dy + dv_dx)
    return eps


def strain_dict(eps: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "eps_xx": eps[:, 0],
        "eps_yy": eps[:, 1],
        "eps_xy": eps[:, 2],
        "eps_trace": eps[:, 0] + eps[:, 1],
        "eps_eq": np.sqrt(eps[:, 0] ** 2 + eps[:, 1] ** 2 + 2.0 * eps[:, 2] ** 2),
    }


def load_fem22_c1_peak() -> dict[str, np.ndarray]:
    with h5py.File(FEM22, "r") as h5:
        coords = np.asarray(h5["node_coords"], dtype=float).T
        conn = np.asarray(h5["connectivity"], dtype=int).T - 1
        centroids = np.asarray(h5["element_centroids"], dtype=float).T
        if float(np.nanmax(centroids[:, 0])) > 0.75:
            centroids = centroids.copy()
            centroids[:, :2] -= 0.5
        cycles = np.asarray(h5["fields/cycle"]).reshape(-1).astype(int)
        substeps = np.asarray(h5["fields/substep_index"]).reshape(-1).astype(int)
        load_factors = np.asarray(h5["fields/load_factor"]).reshape(-1)
        state_idx = int(np.where((cycles == 1) & (substeps == 1) & np.isclose(load_factors, 1.0))[0][-1])
        u_state = np.asarray(h5["fields/u_node"], dtype=float)[state_idx]
        psi_raw = np.asarray(h5["fields/psi_raw_elem"], dtype=float)[state_idx]
        active_psi = np.asarray(h5["fields/active_psi_positive_elem"], dtype=float)[state_idx]
    eps = q4_center_strain(coords, conn, u_state)
    fields = strain_dict(eps)
    fields["psi_raw"] = psi_raw
    fields["psi_active"] = active_psi
    fields["centroids"] = centroids
    return fields


def load_frozen() -> dict[str, np.ndarray]:
    raw = np.load(FROZEN_NPZ)
    return {
        "centroids": np.column_stack([raw["elem_x"], raw["elem_y"]]).astype(float),
        "areas": raw["area_elem"].astype(float),
        "eps_xx": raw["eps_xx_elem"].astype(float),
        "eps_yy": raw["eps_yy_elem"].astype(float),
        "eps_xy": raw["eps_xy_elem"].astype(float),
        "eps_trace": raw["eps_trace_elem"].astype(float),
        "eps_eq": raw["eps_eq_elem"].astype(float),
        "psi_raw": raw["psi_raw_elem"].astype(float),
        "psi_active": raw["psi_active_elem"].astype(float),
        "alpha_fixed": raw["alpha_fixed_elem"].astype(float),
        "g_alpha": raw["g_alpha_elem"].astype(float),
    }


def project(values: np.ndarray, src_centroids: np.ndarray, target_centroids: np.ndarray) -> np.ndarray:
    _, idx = cKDTree(src_centroids).query(target_centroids, k=1)
    return values[idx]


def reductions(values: np.ndarray, areas: np.ndarray, centroids: np.ndarray) -> dict[str, float]:
    finite = np.isfinite(values)
    tip = np.hypot(centroids[:, 0], centroids[:, 1]) <= 0.02

    def wmean(mask: np.ndarray) -> float:
        m = mask & finite
        return float(np.sum(values[m] * areas[m]) / np.sum(areas[m])) if np.any(m) else float("nan")

    return {
        "tip_2l0_mean": wmean(tip),
        "domain_mean": wmean(finite),
        "p99": float(np.nanpercentile(values[finite], 99.0)),
        "p999": float(np.nanpercentile(values[finite], 99.9)),
        "max": float(np.nanmax(values)),
        "min": float(np.nanmin(values)),
    }


def build_table() -> pd.DataFrame:
    fem = load_fem22_c1_peak()
    frozen = load_frozen()
    rows: list[dict[str, object]] = []
    for field in FIELDS:
        fem_proj = project(fem[field], fem["centroids"], frozen["centroids"])
        f_red = reductions(fem_proj, frozen["areas"], frozen["centroids"])
        p_red = reductions(frozen[field], frozen["areas"], frozen["centroids"])
        for metric in METRICS:
            denom = f_red[metric]
            rows.append(
                {
                    "case": "frozen_alpha_elastic",
                    "field": field,
                    "metric": metric,
                    "PIDL": p_red[metric],
                    "FEM22_projected": denom,
                    "PIDL_over_FEM": p_red[metric] / denom
                    if np.isfinite(denom) and abs(denom) > 1e-30
                    else np.nan,
                }
            )
    if COUPLED_CSV.exists():
        coupled = pd.read_csv(COUPLED_CSV)
        coupled = coupled[
            (coupled["pidl_saved_index"] == 0)
            & (coupled["fem_cycle"] == 1)
            & (coupled["field"].isin(FIELDS))
            & (coupled["metric"].isin(METRICS))
        ].copy()
        for _, row in coupled.iterrows():
            rows.append(
                {
                    "case": "coupled_resstiff_c1",
                    "field": row["field"],
                    "metric": row["metric"],
                    "PIDL": row["PIDL"],
                    "FEM22_projected": row["FEM22_nstep2_projected"],
                    "PIDL_over_FEM": row["PIDL_over_FEM"],
                }
            )
    if COUPLED_ACTIVE_CSV.exists():
        active = pd.read_csv(COUPLED_ACTIVE_CSV)
        active = active[
            (active["saved_index"] == 0)
            & (active["fem_cycle"] == 1)
            & (active["field"] == "psi_active")
            & (active["metric"].isin(METRICS))
        ].copy()
        for _, row in active.iterrows():
            rows.append(
                {
                    "case": "coupled_resstiff_c1",
                    "field": row["field"],
                    "metric": row["metric"],
                    "PIDL": row["PIDL_resstiff"],
                    "FEM22_projected": row["FEM_nstep2_projected"],
                    "PIDL_over_FEM": row["PIDL_over_FEM"],
                }
            )
    return pd.DataFrame(rows)


def plot_key_ratios(df: pd.DataFrame) -> Path:
    key = df[
        df["field"].isin(["eps_eq", "eps_yy", "psi_raw", "psi_active"])
        & df["metric"].isin(["tip_2l0_mean", "max"])
    ].copy()
    key["label"] = key["field"] + " " + key["metric"]
    order = [
        "eps_eq tip_2l0_mean",
        "eps_eq max",
        "eps_yy tip_2l0_mean",
        "eps_yy max",
        "psi_raw tip_2l0_mean",
        "psi_raw max",
        "psi_active tip_2l0_mean",
        "psi_active max",
    ]
    fig, ax = plt.subplots(figsize=(10.8, 5.0), constrained_layout=True)
    width = 0.38
    x = np.arange(len(order))
    colors = {"coupled_resstiff_c1": "#0072B2", "frozen_alpha_elastic": "#D55E00"}
    for offset, case in [(-width / 2, "coupled_resstiff_c1"), (width / 2, "frozen_alpha_elastic")]:
        vals = (
            key[key["case"] == case]
            .set_index("label")
            .reindex(order)["PIDL_over_FEM"]
            .to_numpy()
        )
        ax.bar(x + offset, vals, width=width, label=case, color=colors[case])
    ax.axhline(1.0, color="0.3", linestyle="--", linewidth=1.0)
    ax.set_xticks(x)
    ax.set_xticklabels(order, rotation=35, ha="right")
    ax.set_ylabel("PIDL / FEM22")
    ax.set_yscale("log")
    ax.set_title("Frozen-alpha elastic probe vs coupled c1: key field ratios")
    ax.legend(frameon=False)
    out = OUT_FIG / "frozen_alpha_elastic_vs_coupled_c1_ratios.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def plot_c1_maps() -> Path:
    fem = load_fem22_c1_peak()
    frozen = load_frozen()
    roi = (
        (frozen["centroids"][:, 0] >= -0.06)
        & (frozen["centroids"][:, 0] <= 0.06)
        & (frozen["centroids"][:, 1] >= -0.045)
        & (frozen["centroids"][:, 1] <= 0.045)
    )
    fig, axes = plt.subplots(2, 3, figsize=(11.8, 6.8), constrained_layout=True)
    for row_i, (field, title, transform, cmap) in enumerate(
        [
            ("eps_eq", "equivalent strain", lambda a: a, "viridis"),
            ("psi_raw", "log10(1 + psi_raw)", lambda a: np.log10(1.0 + np.maximum(a, 0.0)), "magma"),
        ]
    ):
        fem_proj = project(fem[field], fem["centroids"], frozen["centroids"])
        fem_vals = transform(fem_proj)
        pidl_vals = transform(frozen[field])
        diff = pidl_vals - fem_vals
        vmin = float(np.nanpercentile(np.r_[fem_vals[roi], pidl_vals[roi]], 1))
        vmax = float(np.nanpercentile(np.r_[fem_vals[roi], pidl_vals[roi]], 99))
        lim = float(np.nanpercentile(np.abs(diff[roi]), 99))
        for col_i, (panel_title, vals, local_cmap, local_vmin, local_vmax) in enumerate(
            [
                ("FEM22 projected", fem_vals, cmap, vmin, vmax),
                ("frozen-alpha PIDL", pidl_vals, cmap, vmin, vmax),
                ("PIDL - FEM22", diff, "RdBu_r", -lim, lim),
            ]
        ):
            ax = axes[row_i, col_i]
            sc = ax.scatter(
                frozen["centroids"][roi, 0],
                frozen["centroids"][roi, 1],
                c=vals[roi],
                s=3.0,
                linewidths=0,
                cmap=local_cmap,
                vmin=local_vmin,
                vmax=local_vmax,
            )
            ax.set_title(f"{title}: {panel_title}")
            ax.set_aspect("equal")
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.02)
    fig.suptitle("Frozen-alpha elastic c1 peak fields", fontsize=14)
    out = OUT_FIG / "frozen_alpha_elastic_c1_tip_maps.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def write_note(df: pd.DataFrame, ratio_fig: Path, map_fig: Path) -> Path:
    OUT_ANALYSIS.mkdir(parents=True, exist_ok=True)
    key = df[
        df["field"].isin(["eps_eq", "eps_yy", "psi_raw", "psi_active"])
        & df["metric"].isin(["tip_2l0_mean", "max"])
    ].copy()
    pivot = key.pivot_table(index=["field", "metric"], columns="case", values="PIDL_over_FEM")
    note = OUT_ANALYSIS / "frozen_alpha_elastic_vs_fem22_result.md"
    loss = pd.read_csv(FROZEN_LOSS)
    lines = [
        "# Frozen-Alpha Elastic Probe Result",
        "",
        "Setup: fixed analytic soft-hist0 alpha, displacement-only elastic optimisation, started from the residual-stiffness post-pretraining checkpoint.",
        "",
        "## Loss",
        "",
        f"- initial logged `E_el`: `{loss['E_el'].iloc[0]:.6e}`",
        f"- final logged `E_el`: `{loss['E_el'].iloc[-1]:.6e}`",
        f"- logged reduction: `{loss['E_el'].iloc[-1] / loss['E_el'].iloc[0]:.4f}x`",
        "",
        "## Key PIDL/FEM22 Ratios",
        "",
        pivot.to_markdown(floatfmt=".4g"),
        "",
        "## Interpretation",
        "",
        "Frozen-alpha elastic optimisation removes the coupled c1 raw-energy hotspot too strongly. Compared with FEM22, frozen-alpha gives `eps_eq` tip mean 0.581x, `psi_raw` tip mean 0.250x, and `psi_raw` max 0.0527x. The coupled c1 checkpoint had the opposite problem: `eps_eq` tip mean 1.086x, `psi_raw` tip mean 2.336x, and `psi_raw` max 4.068x.",
        "",
        "The effective active driver is mixed: frozen-alpha `psi_active` tip mean is below FEM, while its max can sit above FEM because the maximum moves into less-degraded material. Therefore max alone is not a clean gate; tip/process-zone reductions and co-location remain necessary.",
        "",
        "The useful conclusion is that the fixed initial alpha/precrack does not force the oversharp `psi_raw` spike. The spike is introduced by the coupled elastic-damage optimisation path. But freezing alpha completely under-drives the crack line, so the answer is not permanent alpha-freezing; it is a FEM-like alternate micro-solve that controls when u/v and alpha are allowed to relax.",
        "",
        "Next diagnostic should be a true alternate-minimisation micro-solve at c1: freeze alpha -> solve u/v, then freeze u/v -> solve alpha, repeat a few times, exporting epsilon/psi after each substage.",
        "",
        "Generated files:",
        "",
        f"- `{OUT_FIG / 'frozen_alpha_elastic_vs_fem22_field_gate.csv'}`",
        f"- `{ratio_fig}`",
        f"- `{map_fig}`",
        "",
    ]
    note.write_text("\n".join(lines), encoding="utf-8")
    return note


def main() -> int:
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    df = build_table()
    csv = OUT_FIG / "frozen_alpha_elastic_vs_fem22_field_gate.csv"
    df.to_csv(csv, index=False)
    ratio_fig = plot_key_ratios(df)
    map_fig = plot_c1_maps()
    note = write_note(df, ratio_fig, map_fig)
    print(f"Wrote {csv}")
    print(f"Wrote {ratio_fig}")
    print(f"Wrote {map_fig}")
    print(f"Wrote {note}")
    key = df[
        df["field"].isin(["eps_eq", "psi_raw", "psi_active"])
        & df["metric"].isin(["tip_2l0_mean", "max"])
    ].pivot_table(index=["field", "metric"], columns="case", values="PIDL_over_FEM")
    print(key.round(4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
