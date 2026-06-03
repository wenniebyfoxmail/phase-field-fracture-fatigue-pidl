#!/usr/bin/env python3
"""Compare early PIDL and FEM22 strain fields for the residual-stiffness run.

This diagnostic asks whether the early ``psi_raw`` mismatch is already present
in the kinematic strain field.  PIDL saved index ``j`` is compared to FEM22
nstep2 loaded peak state at cycle ``c=j+1``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "SENS_tensile"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "source"))

from compute_energy import gradients, strain_energy_with_split  # noqa: E402
from export_pidl_element_diagnostics import (  # noqa: E402
    build_field_computation,
    safe_torch_load,
)


ANALYSIS = ROOT / "_analysis_fem_mechanism_20260528"
EXPERIMENT = ANALYSIS / "experiments" / "resstiff_alignment_20260603"
ARCHIVE_NAME = (
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
    "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
    "N100_R0.0_Umax0.12_femmesh_softHist0_resStiff1e6_eta1em06"
)
ARCHIVE = EXPERIMENT / "0_sync" / ARCHIVE_NAME
FEM22 = (
    ROOT.parent
    / "Alignment check"
    / "FEM preparation"
    / "nstep2"
    / "fem22_nstep2_c0_c5_whole_fields.mat"
)
OUT_ANALYSIS = EXPERIMENT / "1_analysis"
OUT_FIG = EXPERIMENT / "2_figures"
PIDL_MESH = HERE / "meshed_geom_fem_soft_hist0.msh"

SAVED_TO_CYCLE = {0: 1, 1: 2, 2: 3, 3: 4}
STRAIN_FIELDS = ("eps_xx", "eps_yy", "eps_xy", "eps_trace", "eps_eq")
ALL_FIELDS = STRAIN_FIELDS + ("psi_raw",)
METRICS = ("tip_2l0_mean", "domain_mean", "p99", "p999", "max", "min")


def q4_center_strain(coords: np.ndarray, conn: np.ndarray, u_state: np.ndarray) -> np.ndarray:
    """Return [eps_xx, eps_yy, eps_xy] at Q4 element centers."""
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


def reductions(values: np.ndarray, areas: np.ndarray, centroids: np.ndarray) -> dict[str, float]:
    finite = np.isfinite(values)
    r = np.hypot(centroids[:, 0], centroids[:, 1])
    tip2 = r <= 0.02

    def wmean(mask: np.ndarray) -> float:
        m = mask & finite
        if not np.any(m):
            return float("nan")
        return float(np.sum(values[m] * areas[m]) / np.sum(areas[m]))

    return {
        "tip_2l0_mean": wmean(tip2),
        "domain_mean": wmean(finite),
        "p99": float(np.nanpercentile(values[finite], 99.0)),
        "p999": float(np.nanpercentile(values[finite], 99.9)),
        "max": float(np.nanmax(values)),
        "min": float(np.nanmin(values)),
    }


def load_fem22() -> dict[str, object]:
    with h5py.File(FEM22, "r") as h5:
        coords = np.asarray(h5["node_coords"], dtype=float).T
        conn = np.asarray(h5["connectivity"], dtype=int).T - 1
        centroids = np.asarray(h5["element_centroids"], dtype=float).T
        areas = np.asarray(h5["element_area"], dtype=float).reshape(-1)
        u_node = np.asarray(h5["fields/u_node"], dtype=float)
        psi = np.asarray(h5["fields/psi_raw_elem"], dtype=float)
        cycles = np.asarray(h5["fields/cycle"]).reshape(-1).astype(int)
        substeps = np.asarray(h5["fields/substep_index"]).reshape(-1).astype(int)
        load_factors = np.asarray(h5["fields/load_factor"]).reshape(-1)

    if float(np.nanmax(centroids[:, 0])) > 0.75:
        centroids = centroids.copy()
        centroids[:, :2] -= 0.5
    return {
        "coords": coords,
        "conn": conn,
        "centroids": centroids,
        "areas": areas,
        "u_node": u_node,
        "psi_raw": psi,
        "cycles": cycles,
        "substeps": substeps,
        "load_factors": load_factors,
    }


def fem_peak_state_index(fem: dict[str, object], cycle: int) -> int:
    cycles = fem["cycles"]
    substeps = fem["substeps"]
    load_factors = fem["load_factors"]
    matches = np.where((cycles == cycle) & (substeps == 1) & np.isclose(load_factors, 1.0))[0]
    if len(matches) == 0:
        raise ValueError(f"No FEM peak state found for cycle {cycle}")
    return int(matches[-1])


def load_pidl_cycle(cycle: int, device: torch.device) -> tuple[dict[str, np.ndarray], np.ndarray, np.ndarray]:
    field_comp, pffmodel, matprop, inp, t_conn, area_t = build_field_computation(
        ARCHIVE, device, 0.12, PIDL_MESH
    )
    model_path = ARCHIVE / "best_models" / f"trained_1NN_{cycle}.pt"
    if not model_path.exists():
        raise FileNotFoundError(model_path)
    field_comp.net.load_state_dict(safe_torch_load(model_path, device))
    field_comp.net.eval()
    with torch.no_grad():
        u, v, alpha = field_comp.fieldCalculation(inp)
        eps_xx, eps_yy, eps_xy, _, _ = gradients(inp, u, v, alpha, area_t, t_conn)
        alpha_elem = (alpha[t_conn[:, 0]] + alpha[t_conn[:, 1]] + alpha[t_conn[:, 2]]) / 3.0
        _, psi_raw = strain_energy_with_split(eps_xx, eps_yy, eps_xy, alpha_elem, matprop, pffmodel)
        elem_x = (inp[t_conn[:, 0], 0] + inp[t_conn[:, 1], 0] + inp[t_conn[:, 2], 0]) / 3.0
        elem_y = (inp[t_conn[:, 0], 1] + inp[t_conn[:, 1], 1] + inp[t_conn[:, 2], 1]) / 3.0
    eps = np.column_stack(
        [
            eps_xx.detach().cpu().numpy(),
            eps_yy.detach().cpu().numpy(),
            eps_xy.detach().cpu().numpy(),
        ]
    )
    fields = strain_dict(eps)
    fields["psi_raw"] = psi_raw.detach().cpu().numpy()
    centroids = np.column_stack([elem_x.detach().cpu().numpy(), elem_y.detach().cpu().numpy()])
    areas = area_t.detach().cpu().numpy()
    return fields, centroids, areas


def nearest_project(values: np.ndarray, src_centroids: np.ndarray, target_centroids: np.ndarray) -> np.ndarray:
    tree = cKDTree(src_centroids)
    _, idx = tree.query(target_centroids, k=1)
    return values[idx]


def make_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    fem = load_fem22()
    device = torch.device("cpu")
    rows: list[dict[str, object]] = []
    extrema_rows: list[dict[str, object]] = []
    for saved_idx, fem_cycle in SAVED_TO_CYCLE.items():
        pidl_fields, pidl_centroids, pidl_areas = load_pidl_cycle(saved_idx, device)
        fem_state = fem_peak_state_index(fem, fem_cycle)
        fem_eps = q4_center_strain(fem["coords"], fem["conn"], fem["u_node"][fem_state])
        fem_fields = strain_dict(fem_eps)
        fem_fields["psi_raw"] = fem["psi_raw"][fem_state]

        for field in ALL_FIELDS:
            fem_proj = nearest_project(fem_fields[field], fem["centroids"], pidl_centroids)
            pidl_red = reductions(pidl_fields[field], pidl_areas, pidl_centroids)
            fem_red = reductions(fem_proj, pidl_areas, pidl_centroids)
            for metric in METRICS:
                denom = fem_red[metric]
                rows.append(
                    {
                        "pidl_saved_index": saved_idx,
                        "fem_cycle": fem_cycle,
                        "fem_state_index": fem_state,
                        "field": field,
                        "metric": metric,
                        "PIDL": pidl_red[metric],
                        "FEM22_nstep2_projected": denom,
                        "PIDL_over_FEM": pidl_red[metric] / denom
                        if np.isfinite(denom) and abs(denom) > 1e-30
                        else np.nan,
                    }
                )
            for selector, values in (
                (f"max_abs_{field}", np.abs(pidl_fields[field])),
                (f"max_{field}", pidl_fields[field]),
            ):
                idx = int(np.nanargmax(values))
                extrema_rows.append(
                    {
                        "pidl_saved_index": saved_idx,
                        "fem_cycle": fem_cycle,
                        "selector": selector,
                        "x": float(pidl_centroids[idx, 0]),
                        "y": float(pidl_centroids[idx, 1]),
                        "value": float(pidl_fields[field][idx]),
                        "psi_raw": float(pidl_fields["psi_raw"][idx]),
                        "eps_xx": float(pidl_fields["eps_xx"][idx]),
                        "eps_yy": float(pidl_fields["eps_yy"][idx]),
                        "eps_xy": float(pidl_fields["eps_xy"][idx]),
                    }
                )
    return pd.DataFrame(rows), pd.DataFrame(extrema_rows)


def plot_ratios(df: pd.DataFrame) -> Path:
    plot_items = [
        ("eps_xx", "tip_2l0_mean", "eps_xx tip2"),
        ("eps_yy", "tip_2l0_mean", "eps_yy tip2"),
        ("eps_xy", "p99", "eps_xy p99"),
        ("eps_eq", "tip_2l0_mean", "eps_eq tip2"),
        ("eps_eq", "max", "eps_eq max"),
        ("psi_raw", "tip_2l0_mean", "psi_raw tip2"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(13.0, 7.0), constrained_layout=True)
    for ax, (field, metric, title) in zip(axes.ravel(), plot_items):
        sub = df[(df["field"] == field) & (df["metric"] == metric)].sort_values("fem_cycle")
        ax.plot(sub["fem_cycle"], sub["PIDL_over_FEM"], marker="o", linewidth=1.6)
        ax.axhline(1.0, color="0.45", linestyle="--", linewidth=1.0)
        ax.set_title(title)
        ax.set_xlabel("FEM cycle")
        ax.set_ylabel("PIDL / FEM22")
        ax.grid(True, alpha=0.25)
        if field in {"eps_eq", "psi_raw"}:
            ax.set_yscale("log")
    out = OUT_FIG / "resstiff_epsilon_vs_fem22_ratios.png"
    fig.suptitle("Residual-stiffness PIDL vs FEM22 nstep2: early strain ratios", fontsize=14)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def plot_scalar_overlay(df: pd.DataFrame) -> Path:
    sub = df[
        (df["metric"].isin(["tip_2l0_mean", "max"]))
        & (df["field"].isin(["eps_eq", "psi_raw"]))
    ].copy()
    out = OUT_FIG / "resstiff_epsilon_vs_fem22_values.png"
    fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.2), constrained_layout=True)
    for ax, (field, metric) in zip(
        axes.ravel(),
        [("eps_eq", "tip_2l0_mean"), ("eps_eq", "max"), ("psi_raw", "tip_2l0_mean"), ("psi_raw", "max")],
    ):
        s = sub[(sub["field"] == field) & (sub["metric"] == metric)].sort_values("fem_cycle")
        ax.plot(s["fem_cycle"], s["PIDL"], marker="o", label="PIDL")
        ax.plot(s["fem_cycle"], s["FEM22_nstep2_projected"], marker="s", label="FEM22")
        ax.set_title(f"{field} {metric}")
        ax.set_xlabel("FEM cycle")
        ax.grid(True, alpha=0.25)
        ax.legend(frameon=False)
    fig.suptitle("Early strain/value comparison at loaded peak states", fontsize=14)
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def plot_c1_tip_maps() -> Path:
    fem = load_fem22()
    pidl_fields, pidl_centroids, _ = load_pidl_cycle(0, torch.device("cpu"))
    fem_state = fem_peak_state_index(fem, 1)
    fem_eps = q4_center_strain(fem["coords"], fem["conn"], fem["u_node"][fem_state])
    fem_fields = strain_dict(fem_eps)
    fem_fields["psi_raw"] = fem["psi_raw"][fem_state]

    roi = (
        (pidl_centroids[:, 0] >= -0.06)
        & (pidl_centroids[:, 0] <= 0.06)
        & (pidl_centroids[:, 1] >= -0.045)
        & (pidl_centroids[:, 1] <= 0.045)
    )
    fig, axes = plt.subplots(2, 3, figsize=(11.8, 6.8), constrained_layout=True)
    rows = [
        ("eps_eq", "equivalent strain", lambda v: v, "viridis"),
        ("psi_raw", "log10(1 + psi_raw)", lambda v: np.log10(1.0 + np.maximum(v, 0.0)), "magma"),
    ]
    for row_idx, (field, label, transform, cmap) in enumerate(rows):
        fem_proj = nearest_project(fem_fields[field], fem["centroids"], pidl_centroids)
        pidl = pidl_fields[field]
        fem_plot = transform(fem_proj)
        pidl_plot = transform(pidl)
        diff = pidl_plot - fem_plot
        vmin = float(np.nanpercentile(np.r_[fem_plot[roi], pidl_plot[roi]], 1.0))
        vmax = float(np.nanpercentile(np.r_[fem_plot[roi], pidl_plot[roi]], 99.0))
        lim = float(np.nanpercentile(np.abs(diff[roi]), 99.0))
        panels = [
            ("FEM22 projected", fem_plot, cmap, vmin, vmax),
            ("PIDL", pidl_plot, cmap, vmin, vmax),
            ("PIDL - FEM22", diff, "RdBu_r", -lim, lim),
        ]
        for col_idx, (title, values, local_cmap, local_vmin, local_vmax) in enumerate(panels):
            ax = axes[row_idx, col_idx]
            sc = ax.scatter(
                pidl_centroids[roi, 0],
                pidl_centroids[roi, 1],
                c=values[roi],
                s=3.0,
                linewidths=0,
                cmap=local_cmap,
                vmin=local_vmin,
                vmax=local_vmax,
            )
            ax.set_aspect("equal")
            ax.set_title(f"{label}: {title}")
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.02)
    out = OUT_FIG / "resstiff_epsilon_vs_fem22_c1_tip_maps.png"
    fig.suptitle("c1 peak-load tip-region fields on PIDL centroids", fontsize=14)
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def write_note(
    df: pd.DataFrame,
    extrema: pd.DataFrame,
    ratio_fig: Path,
    value_fig: Path,
    map_fig: Path,
) -> Path:
    OUT_ANALYSIS.mkdir(parents=True, exist_ok=True)
    key = df[
        (df["metric"].isin(["tip_2l0_mean", "max", "p99"]))
        & (df["field"].isin(["eps_xx", "eps_yy", "eps_xy", "eps_eq", "psi_raw"]))
    ]
    pivot = key.pivot_table(
        index=["pidl_saved_index", "fem_cycle", "metric"],
        columns="field",
        values="PIDL_over_FEM",
    )
    c1 = pivot.loc[(0, 1)]
    note = OUT_ANALYSIS / "resstiff_epsilon_vs_fem22_result.md"
    note.write_text(
        "\n".join(
            [
                "# Residual-Stiffness PIDL vs FEM22 Strain Diagnostic",
                "",
                "Setup: PIDL residual-stiffness branch compared to FEM22 nstep2 whole-field peak-load states.",
                "",
                "Timing convention: PIDL saved index `j` maps to FEM cycle `c=j+1`; FEM state is the loaded peak substep, using the later duplicate peak state after history refresh. Strain is unchanged across the duplicate pre/post history states.",
                "",
                "## c1 Ratios",
                "",
                c1.to_markdown(floatfmt=".4g"),
                "",
                "## Interpretation",
                "",
                "The early `psi_raw` mismatch is already visible at the strain level, but not as a large error in the mean imposed strain. At c1 the tip-region equivalent strain is only 1.086x FEM, while equivalent-strain max is 1.892x and `psi_raw` max is 4.068x. That is consistent with strain energy amplifying localized strain extrema roughly quadratically.",
                "",
                "`eps_xy` mean ratios are not physically meaningful because the FEM tip mean is close to zero; use p99/max and the field map instead for shear.",
                "",
                "The stronger conclusion is therefore field-shape/localization: PIDL and FEM begin with similar damage/history averages, but PIDL has a sharper strain/energy hotspot.",
                "",
                "A large PIDL `psi_raw_max` should therefore be read as a strain-localization diagnostic, not by itself as effective crack-driving work. The effective driver still depends on co-location with `g(alpha)` and the history update.",
                "",
                "Generated files:",
                "",
                f"- `{OUT_FIG / 'resstiff_epsilon_vs_fem22_field_gate.csv'}`",
                f"- `{OUT_FIG / 'resstiff_epsilon_vs_fem22_extrema.csv'}`",
                f"- `{ratio_fig}`",
                f"- `{value_fig}`",
                f"- `{map_fig}`",
                "",
                "Largest PIDL extrema locations are saved in the extrema CSV for checking whether high strain/psi is inside damaged material or the active process zone.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return note


def main() -> int:
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    df, extrema = make_tables()
    ratio_csv = OUT_FIG / "resstiff_epsilon_vs_fem22_field_gate.csv"
    extrema_csv = OUT_FIG / "resstiff_epsilon_vs_fem22_extrema.csv"
    df.to_csv(ratio_csv, index=False)
    extrema.to_csv(extrema_csv, index=False)
    ratio_fig = plot_ratios(df)
    value_fig = plot_scalar_overlay(df)
    map_fig = plot_c1_tip_maps()
    note = write_note(df, extrema, ratio_fig, value_fig, map_fig)
    print(f"Wrote {ratio_csv}")
    print(f"Wrote {extrema_csv}")
    print(f"Wrote {ratio_fig}")
    print(f"Wrote {value_fig}")
    print(f"Wrote {map_fig}")
    print(f"Wrote {note}")
    key = df[(df["metric"] == "tip_2l0_mean") & (df["field"].isin(["eps_eq", "psi_raw"]))]
    print(key.pivot(index=["pidl_saved_index", "fem_cycle"], columns="field", values="PIDL_over_FEM").round(4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
