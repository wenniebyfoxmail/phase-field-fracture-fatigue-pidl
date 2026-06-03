#!/usr/bin/env python3
"""Analyze the c1 alternate-minimisation probe against FEM22 c1 peak fields."""
from __future__ import annotations

from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "_analysis_fem_mechanism_20260528"
EXPERIMENT = ANALYSIS / "experiments" / "c1_altmin_20260603"
SYNC = EXPERIMENT / "0_sync"
OUT_ANALYSIS = EXPERIMENT / "1_analysis"
OUT_FIG = EXPERIMENT / "2_figures"
ALTM_NPZ = SYNC / "c1_altmin_fields.npz"
ALTM_TRACE = SYNC / "c1_altmin_trace.csv"
FEM22 = (
    ROOT.parent
    / "Alignment check"
    / "FEM preparation"
    / "nstep2"
    / "fem22_nstep2_c0_c5_whole_fields.mat"
)

FIELDS = ("alpha", "eps_eq", "psi_raw", "g_alpha", "psi_active")
METRICS = ("tip_2l0_mean", "domain_mean", "p99", "p999", "max")


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
        alpha = np.asarray(h5["fields/d_elem"], dtype=float)[state_idx]
        g_alpha = np.asarray(h5["fields/damage_degradation_elem"], dtype=float)[state_idx]
        psi_raw = np.asarray(h5["fields/psi_raw_elem"], dtype=float)[state_idx]
        psi_active = np.asarray(h5["fields/active_psi_positive_elem"], dtype=float)[state_idx]
    eps = q4_center_strain(coords, conn, u_state)
    return {
        "centroids": centroids,
        "alpha": alpha,
        "eps_eq": np.sqrt(eps[:, 0] ** 2 + eps[:, 1] ** 2 + 2.0 * eps[:, 2] ** 2),
        "psi_raw": psi_raw,
        "g_alpha": g_alpha,
        "psi_active": psi_active,
    }


def load_altmin() -> dict[str, np.ndarray]:
    raw = np.load(ALTM_NPZ)
    return {
        "labels": np.asarray(raw["labels"]).astype(str),
        "centroids": np.column_stack([raw["elem_x"], raw["elem_y"]]).astype(float),
        "areas": raw["area_elem"].astype(float),
        "alpha": raw["alpha_elem"].astype(float),
        "eps_eq": raw["eps_eq_elem"].astype(float),
        "psi_raw": raw["psi_raw_elem"].astype(float),
        "g_alpha": raw["g_alpha_elem"].astype(float),
        "psi_active": raw["psi_active_elem"].astype(float),
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
    }


def build_ratio_table() -> pd.DataFrame:
    fem = load_fem22_c1_peak()
    alt = load_altmin()
    rows: list[dict[str, object]] = []
    for field in FIELDS:
        fem_proj = project(fem[field], fem["centroids"], alt["centroids"])
        f_red = reductions(fem_proj, alt["areas"], alt["centroids"])
        for i, label in enumerate(alt["labels"]):
            p_red = reductions(alt[field][i], alt["areas"], alt["centroids"])
            for metric in METRICS:
                denom = f_red[metric]
                rows.append(
                    {
                        "label": label,
                        "field": field,
                        "metric": metric,
                        "PIDL": p_red[metric],
                        "FEM22_projected": denom,
                        "PIDL_over_FEM": p_red[metric] / denom
                        if np.isfinite(denom) and abs(denom) > 1e-30
                        else np.nan,
                    }
                )
    return pd.DataFrame(rows)


def plot_trace() -> Path:
    trace = pd.read_csv(ALTM_TRACE)
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.0), constrained_layout=True)
    x = np.arange(len(trace))
    axes[0].plot(x, trace["E_el"], marker="o", label="E_el")
    axes[0].plot(x, trace["E_d"], marker="o", label="E_d")
    axes[0].plot(x, trace["E_hist"].clip(lower=1e-12), marker="o", label="E_hist")
    axes[0].set_yscale("log")
    axes[0].set_ylabel("energy term")
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].plot(x, trace["psi_raw_max"], marker="o", label="psi_raw max")
    axes[1].plot(x, trace["psi_active_max"], marker="o", label="psi_active max")
    axes[1].set_yscale("log")
    axes[1].set_ylabel("field maximum")
    axes[1].legend(frameon=False, fontsize=8)
    axes[2].plot(x, trace["grad_logEel"], marker="o", label="grad logE_el")
    axes[2].plot(x, trace["grad_logEd"], marker="o", label="grad logE_d")
    axes[2].plot(x, trace["grad_logEhist"], marker="o", label="grad logE_hist")
    axes[2].set_yscale("log")
    axes[2].set_ylabel("active-head grad norm")
    axes[2].legend(frameon=False, fontsize=8)
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(trace["label"], rotation=35, ha="right")
        ax.grid(True, alpha=0.25)
    fig.suptitle("C1 alternate-minimisation scalar trace")
    out = OUT_FIG / "c1_altmin_scalar_trace.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def plot_key_ratios(df: pd.DataFrame) -> Path:
    key = df[
        df["field"].isin(["eps_eq", "psi_raw", "psi_active", "alpha"])
        & df["metric"].isin(["tip_2l0_mean", "max"])
    ].copy()
    key["series"] = key["field"] + " " + key["metric"]
    labels = list(dict.fromkeys(key["label"]))
    fig, axes = plt.subplots(2, 2, figsize=(12.6, 7.0), sharex=True, constrained_layout=True)
    series = [
        "eps_eq tip_2l0_mean",
        "psi_raw max",
        "psi_active tip_2l0_mean",
        "alpha max",
    ]
    for ax, name in zip(axes.ravel(), series):
        sub = key[key["series"] == name].set_index("label").reindex(labels)
        ax.plot(np.arange(len(labels)), sub["PIDL_over_FEM"], marker="o", linewidth=1.5)
        ax.axhline(1.0, color="0.3", linestyle="--", linewidth=1.0)
        ax.set_yscale("log")
        ax.set_title(name)
        ax.grid(True, alpha=0.25)
    for ax in axes[-1]:
        ax.set_xticks(np.arange(len(labels)))
        ax.set_xticklabels(labels, rotation=35, ha="right")
    fig.suptitle("C1 alternate-minimisation ratios against FEM22 c1 peak")
    out = OUT_FIG / "c1_altmin_vs_fem22_key_ratios.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def plot_tip_maps() -> Path:
    fem = load_fem22_c1_peak()
    alt = load_altmin()
    selected = ["initial_joint", "r1_uv", "r2_uv", "r3_uv", "r3_alpha"]
    idxs = [int(np.where(alt["labels"] == label)[0][0]) for label in selected]
    roi = (
        (alt["centroids"][:, 0] >= -0.06)
        & (alt["centroids"][:, 0] <= 0.06)
        & (alt["centroids"][:, 1] >= -0.045)
        & (alt["centroids"][:, 1] <= 0.045)
    )
    fem_proj = {
        field: project(fem[field], fem["centroids"], alt["centroids"])
        for field in ("psi_raw", "psi_active")
    }
    fig, axes = plt.subplots(2, 6, figsize=(15.0, 5.8), constrained_layout=True)
    for row, field in enumerate(("psi_raw", "psi_active")):
        all_vals = [np.log10(np.maximum(fem_proj[field][roi], 1e-12))]
        all_vals += [np.log10(np.maximum(alt[field][idx][roi], 1e-12)) for idx in idxs]
        vmin = min(float(np.nanpercentile(vals, 1.0)) for vals in all_vals)
        vmax = max(float(np.nanpercentile(vals, 99.5)) for vals in all_vals)
        panels = [("FEM22 c1 peak", fem_proj[field])] + [(label, alt[field][idx]) for label, idx in zip(selected, idxs)]
        for col, (title, values) in enumerate(panels):
            ax = axes[row, col]
            sc = ax.scatter(
                alt["centroids"][roi, 0],
                alt["centroids"][roi, 1],
                c=np.log10(np.maximum(values[roi], 1e-12)),
                s=2.0,
                cmap="magma",
                vmin=vmin,
                vmax=vmax,
                linewidths=0,
            )
            ax.axhline(0.0, color="white", linewidth=0.4, alpha=0.7)
            ax.axvline(0.0, color="white", linewidth=0.4, alpha=0.7)
            ax.set_aspect("equal")
            ax.set_title(title, fontsize=8)
            ax.set_xticks([])
            ax.set_yticks([])
        cbar = fig.colorbar(sc, ax=axes[row, :], shrink=0.82)
        cbar.set_label(f"log10 {field}")
        axes[row, 0].set_ylabel(field)
    out = OUT_FIG / "c1_altmin_tip_maps.png"
    fig.savefig(out, dpi=240)
    plt.close(fig)
    return out


def write_summary(df: pd.DataFrame, figs: list[Path]) -> Path:
    trace = pd.read_csv(ALTM_TRACE)

    def val(label: str, field: str, metric: str) -> float:
        row = df[(df["label"] == label) & (df["field"] == field) & (df["metric"] == metric)]
        return float(row["PIDL_over_FEM"].iloc[0])

    lines = [
        "# C1 Alt-Min vs FEM22 Result",
        "",
        "## Key Scalar Trace",
        "",
        trace.to_markdown(index=False),
        "",
        "## Key FEM Ratios",
        "",
        "| state | eps_eq tip2 | psi_raw max | psi_active tip2 | alpha max |",
        "|---|---:|---:|---:|---:|",
    ]
    for label in trace["label"]:
        lines.append(
            f"| {label} | "
            f"{val(label, 'eps_eq', 'tip_2l0_mean'):.4g} | "
            f"{val(label, 'psi_raw', 'max'):.4g} | "
            f"{val(label, 'psi_active', 'tip_2l0_mean'):.4g} | "
            f"{val(label, 'alpha', 'max'):.4g} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- The first fixed-alpha uv solve cools the raw hotspot strongly: `psi_raw_max` falls from the pretrained coupled value to the same order as the frozen-alpha diagnostic.",
        "- The first alpha-only solve does not restore the raw hotspot. It mainly changes alpha/dissipation under a very large `grad_logEhist` signal.",
        "- The raw hotspot reappears during later uv re-equilibration after alpha has moved: `r2_uv` raises `psi_raw_max`, and `r3_uv` returns it close to the original coupled hotspot.",
        "- This points to a feedback loop: alpha update changes degradation/stiffness, then the uv equilibrium stage relocates/concentrates raw strain around that updated damage field.",
        "",
        "## Figures",
        "",
    ]
    lines += [f"- `{path}`" for path in figs]
    out = OUT_ANALYSIS / "c1_altmin_vs_fem22_result.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    OUT_ANALYSIS.mkdir(parents=True, exist_ok=True)
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    df = build_ratio_table()
    csv = OUT_FIG / "c1_altmin_vs_fem22_field_gate.csv"
    df.to_csv(csv, index=False)
    figs = [plot_trace(), plot_key_ratios(df), plot_tip_maps()]
    summary = write_summary(df, figs)
    print(f"wrote {csv}")
    for fig in figs:
        print(f"wrote {fig}")
    print(f"wrote {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
