#!/usr/bin/env python3
"""Build tiered aligned FEM/PIDL reference comparisons.

This uses the strict soft-hist0 FEM-mesh PIDL common-probe comparison already
generated for the standard FEM reference, then adds Request 21 n_step10 as a
second FEM reference on the same PIDL triangular probes.  The goal is to keep
the comparison protocol explicit:

* fixed-cycle tiers: c1/c20/c40/c69,
* fields: damage, alpha_bar, raw psi+, active/degraded psi+, fatigue factor,
* metrics: near-tip, p99/p999/max, right band,
* energy: absolute vs c1-incremental E_d kept separate.
"""
from __future__ import annotations

from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
SENS = ROOT / "SENS_tensile"
ANALYSIS = ROOT / "_analysis_fem_mechanism_20260528"
FIG_DIR = ANALYSIS / "figures"
REQUEST21 = ANALYSIS / "request21_fem_nstep"
ONEDRIVE = Path.home() / "Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result"

STANDARD_COMMON_PROBE = ANALYSIS / "femmesh_pidl_vs_soft_hist0_fem_probe_j0map_c1_c20_c40_c69.csv"
STANDARD_ENERGY = ANALYSIS / "femmesh_pidl_vs_soft_hist0_incremental_energy_c1_ref.csv"
NSTEP10_MAT = (
    REQUEST21
    / "source_handoff"
    / "_pidl_handoff_reverseBC_u12_soft_hist0_nstep10_2026-05-29"
    / "reverseBC_u12_soft_hist0_nstep10_element_fields_c1_c69.mat"
)
NSTEP10_CSV = (
    REQUEST21
    / "source_handoff"
    / "_pidl_handoff_reverseBC_u12_soft_hist0_nstep10_2026-05-29"
    / "reverseBC_u12_soft_hist0_nstep10_cyclewise_mechanism_metrics.csv"
)

PIDL_MESH = SENS / "meshed_geom_fem_soft_hist0.msh"
OUT_COMMON = ANALYSIS / "aligned_fem_pidl_reference_tiers.csv"
OUT_ENERGY = ANALYSIS / "aligned_fem_pidl_energy_tiers.csv"
OUT_SUMMARY = ANALYSIS / "aligned_fem_pidl_reference_tier_summary.csv"
OUT_FIG = FIG_DIR / "aligned_fem_pidl_reference_tiers_20260530.png"

CYCLES = (1, 20, 40, 69)
FIELDS = ("damage_alpha", "alpha_bar", "psi_plus_raw", "psi_plus_active", "fatigue_f")
KEY_METRICS = ("tip_2l0_mean", "p99", "p999", "max", "right_band_mean")


def parse_simple_gmsh_v41(path: Path) -> tuple[np.ndarray, np.ndarray]:
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        nodes_i = lines.index("$Nodes")
        elements_i = lines.index("$Elements")
    except ValueError as exc:
        raise ValueError(f"{path} does not look like a Gmsh 4.1 ASCII mesh") from exc

    node_header = [int(v) for v in lines[nodes_i + 1].split()]
    n_nodes = node_header[1]
    block_header_i = nodes_i + 2
    node_block = lines[block_header_i].split()
    nodes_in_block = int(node_block[3])
    if nodes_in_block != n_nodes:
        raise ValueError("Only single-block node meshes are supported here")
    tag_start = block_header_i + 1
    coord_start = tag_start + n_nodes
    tags = np.array([int(lines[tag_start + i]) for i in range(n_nodes)], dtype=int)
    coords = np.array(
        [[float(v) for v in lines[coord_start + i].split()[:2]] for i in range(n_nodes)],
        dtype=float,
    )
    order = np.argsort(tags)
    nodes = coords[order]

    elem_header = [int(v) for v in lines[elements_i + 1].split()]
    n_elems = elem_header[1]
    elem_block = lines[elements_i + 2].split()
    elem_type = int(elem_block[2])
    elems_in_block = int(elem_block[3])
    if elem_type != 2 or elems_in_block != n_elems:
        raise ValueError("Only single-block triangular meshes are supported here")
    elem_start = elements_i + 3
    conn = np.empty((n_elems, 3), dtype=int)
    for i in range(n_elems):
        vals = [int(v) for v in lines[elem_start + i].split()]
        conn[i] = np.array(vals[1:4], dtype=int) - 1
    return nodes, conn


def triangle_geometry(nodes: np.ndarray, conn: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    pts = nodes[conn]
    centroids = pts.mean(axis=1)
    x = pts[:, :, 0]
    y = pts[:, :, 1]
    area = 0.5 * np.abs(
        (x[:, 1] - x[:, 0]) * (y[:, 2] - y[:, 0])
        - (x[:, 2] - x[:, 0]) * (y[:, 1] - y[:, 0])
    )
    return centroids, area


def load_hdf_fields(path: Path) -> dict[str, np.ndarray]:
    with h5py.File(path, "r") as h5:
        cycles = np.asarray(h5["cycles"]).ravel().astype(int)
        centroids = np.asarray(h5["element_centroids"]).T.astype(float) - 0.5
        area = np.asarray(h5["element_area"]).ravel().astype(float)
        fields = {
            "damage_alpha": np.asarray(h5["d_elem"], dtype=float),
            "alpha_bar": np.asarray(h5["alpha_bar_elem"], dtype=float),
            "fatigue_f": np.asarray(h5["f_fatigue_elem"], dtype=float),
            "psi_plus_raw": np.asarray(h5["psi_plus_elem"], dtype=float),
        }
        fields["psi_plus_active"] = ((1.0 - fields["damage_alpha"]) ** 2 + 1e-6) * fields["psi_plus_raw"]
    return {"cycles": cycles, "centroids": centroids, "area": area, "fields": fields}


def point_in_triangle(p: np.ndarray, tri: np.ndarray, tol: float = 1e-12) -> bool:
    v1, v2, v3 = tri
    denom = (v2[1] - v3[1]) * (v1[0] - v3[0]) + (v3[0] - v2[0]) * (v1[1] - v3[1])
    if abs(denom) < tol:
        return False
    a = ((v2[1] - v3[1]) * (p[0] - v3[0]) + (v3[0] - v2[0]) * (p[1] - v3[1])) / denom
    b = ((v3[1] - v1[1]) * (p[0] - v3[0]) + (v1[0] - v3[0]) * (p[1] - v3[1])) / denom
    c = 1.0 - a - b
    return a >= -tol and b >= -tol and c >= -tol


def build_assignment(source_centroids: np.ndarray, target_centroids: np.ndarray, nodes: np.ndarray, conn: np.ndarray) -> np.ndarray:
    tree = cKDTree(target_centroids)
    assignment = np.empty(len(source_centroids), dtype=int)
    fallback = 0
    for i, xy in enumerate(source_centroids):
        _, ids = tree.query(xy, k=16)
        found = -1
        for idx in np.atleast_1d(ids):
            tri = nodes[conn[int(idx)]]
            if point_in_triangle(xy, tri):
                found = int(idx)
                break
        if found < 0:
            found = int(np.atleast_1d(ids)[0])
            fallback += 1
        assignment[i] = found
    print(f"assignment fallback: {fallback}/{len(source_centroids)}")
    return assignment


def project_to_pidl(values: np.ndarray, source_area: np.ndarray, assignment: np.ndarray, n_target: int) -> np.ndarray:
    sums = np.zeros(n_target, dtype=float)
    areas = np.zeros(n_target, dtype=float)
    np.add.at(sums, assignment, values * source_area)
    np.add.at(areas, assignment, source_area)
    out = np.full(n_target, np.nan, dtype=float)
    mask = areas > 0
    out[mask] = sums[mask] / areas[mask]
    return out


def weighted_mean(values: np.ndarray, areas: np.ndarray, mask: np.ndarray) -> float:
    m = mask & np.isfinite(values)
    if not np.any(m):
        return float("nan")
    return float(np.sum(values[m] * areas[m]) / np.sum(areas[m]))


def reductions(values: np.ndarray, areas: np.ndarray, centroids: np.ndarray) -> dict[str, float]:
    finite = np.isfinite(values)
    out = {
        "max": float(np.nanmax(values)),
        "p999": float(np.nanpercentile(values, 99.9)),
        "p99": float(np.nanpercentile(values, 99.0)),
        "domain_mean": weighted_mean(values, areas, finite),
    }
    radius = np.hypot(centroids[:, 0], centroids[:, 1])
    masks = {
        "tip_l0": radius <= 0.01,
        "tip_2l0": radius <= 0.02,
        "tip_4l0": radius <= 0.04,
        "right_band": centroids[:, 0] >= 0.45,
        "crack_strip": np.abs(centroids[:, 1]) <= 0.02,
    }
    for name, mask in masks.items():
        out[f"{name}_mean"] = weighted_mean(values, areas, mask)
        out[f"{name}_integral"] = float(np.nansum(values[mask] * areas[mask]))
    return out


def build_nstep10_common_probe(standard_probe: pd.DataFrame) -> pd.DataFrame:
    nodes, conn = parse_simple_gmsh_v41(PIDL_MESH)
    pidl_centroids, pidl_area = triangle_geometry(nodes, conn)
    fem = load_hdf_fields(NSTEP10_MAT)
    assignment = build_assignment(fem["centroids"], pidl_centroids, nodes, conn)
    pidl_lookup = standard_probe.set_index(["cycle", "field", "metric"])["PIDL_native"]

    rows = []
    cycle_to_index = {int(c): i for i, c in enumerate(fem["cycles"])}
    for cycle in CYCLES:
        field_index = cycle_to_index[cycle]
        for field in FIELDS:
            projected = project_to_pidl(
                fem["fields"][field][field_index],
                fem["area"],
                assignment,
                len(pidl_area),
            )
            for metric, fem_value in reductions(projected, pidl_area, pidl_centroids).items():
                pidl_value = pidl_lookup.get((cycle, field, metric), np.nan)
                rows.append(
                    {
                        "reference": "FEM n_step10",
                        "comparison_tier": "fixed_cycle",
                        "cycle": cycle,
                        "fem_cycle": cycle,
                        "pidl_saved_index": cycle - 1,
                        "field": field,
                        "metric": metric,
                        "FEM_projected_to_PIDL": fem_value,
                        "PIDL_native": pidl_value,
                        "PIDL_over_FEM_projected": pidl_value / fem_value
                        if np.isfinite(fem_value) and abs(fem_value) > 1e-30
                        else np.nan,
                        "FEM_projected_over_PIDL": fem_value / pidl_value
                        if np.isfinite(pidl_value) and abs(pidl_value) > 1e-30
                        else np.nan,
                    }
                )
    return pd.DataFrame(rows)


def build_standard_common_probe() -> pd.DataFrame:
    table = pd.read_csv(STANDARD_COMMON_PROBE)
    table.insert(0, "reference", "FEM standard")
    table.insert(1, "comparison_tier", "fixed_cycle")
    return table


def build_energy_tiers() -> pd.DataFrame:
    standard = pd.read_csv(STANDARD_ENERGY)
    standard = standard[standard["cycle"].isin(CYCLES)].copy()
    standard.insert(0, "reference", "FEM standard")
    base_cols = [
        "reference",
        "cycle",
        "fem_E_el",
        "fem_E_d",
        "fem_total_energy",
        "pidl_E_el",
        "pidl_E_d",
        "pidl_E_hist",
        "pidl_E_el_outside_precrack",
        "pidl_E_d_outside_precrack",
        "pidl_total_energy",
    ]
    standard = standard[base_cols]
    nstep10 = pd.read_csv(NSTEP10_CSV)
    nstep10 = nstep10[nstep10["cycle"].isin(CYCLES)].copy()
    nstep10 = nstep10.rename(
        columns={"E_el": "fem_E_el", "E_d": "fem_E_d", "total_energy": "fem_total_energy"}
    )
    pidl_cols = [
        "cycle",
        "pidl_E_el",
        "pidl_E_d",
        "pidl_E_hist",
        "pidl_E_el_outside_precrack",
        "pidl_E_d_outside_precrack",
        "pidl_total_energy",
    ]
    nstep10 = nstep10.merge(standard[pidl_cols], on="cycle", how="left")
    nstep10.insert(0, "reference", "FEM n_step10")

    combined = pd.concat([standard, nstep10[base_cols]], ignore_index=True)
    for reference, ref_rows in combined.groupby("reference"):
        c1 = ref_rows.loc[ref_rows["cycle"] == 1].iloc[0]
        mask = combined["reference"] == reference
        for col in ("fem_E_el", "fem_E_d", "fem_total_energy", "pidl_E_el", "pidl_E_d", "pidl_E_hist", "pidl_total_energy"):
            combined.loc[mask, f"delta_{col}_from_c1"] = combined.loc[mask, col] - c1[col]
        combined.loc[mask, "ratio_abs_E_d_pidl_over_fem"] = combined.loc[mask, "pidl_E_d"] / combined.loc[mask, "fem_E_d"]
        combined.loc[mask, "ratio_delta_E_d_pidl_over_fem"] = (
            combined.loc[mask, "delta_pidl_E_d_from_c1"] / combined.loc[mask, "delta_fem_E_d_from_c1"]
        )
    return combined


def build_summary(common: pd.DataFrame, energy: pd.DataFrame) -> pd.DataFrame:
    key_rows = common[
        common["field"].isin(["damage_alpha", "alpha_bar", "psi_plus_raw", "psi_plus_active"])
        & common["metric"].isin(["tip_2l0_mean", "p99", "max"])
        & common["cycle"].isin(CYCLES)
    ].copy()
    summary = key_rows[
        [
            "reference",
            "comparison_tier",
            "cycle",
            "field",
            "metric",
            "PIDL_over_FEM_projected",
            "FEM_projected_to_PIDL",
            "PIDL_native",
        ]
    ]
    e = energy[["reference", "cycle", "ratio_abs_E_d_pidl_over_fem", "ratio_delta_E_d_pidl_over_fem"]].copy()
    e["comparison_tier"] = "fixed_cycle"
    e["field"] = "energy"
    e["metric"] = "E_d_abs_and_delta"
    e["PIDL_over_FEM_projected"] = e["ratio_delta_E_d_pidl_over_fem"]
    e["FEM_projected_to_PIDL"] = np.nan
    e["PIDL_native"] = np.nan
    return pd.concat([summary, e[summary.columns]], ignore_index=True)


def plot_summary(summary: pd.DataFrame) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    selected = [
        ("damage_alpha", "tip_2l0_mean", "damage tip2"),
        ("alpha_bar", "tip_2l0_mean", "alpha_bar tip2"),
        ("alpha_bar", "p99", "alpha_bar p99"),
        ("psi_plus_raw", "tip_2l0_mean", "raw psi tip2"),
        ("psi_plus_active", "tip_2l0_mean", "active psi tip2"),
        ("energy", "E_d_abs_and_delta", "Delta E_d"),
    ]
    refs = ["FEM standard", "FEM n_step10"]
    fig, axes = plt.subplots(2, 3, figsize=(13.0, 7.2), constrained_layout=True)
    colors = {"FEM standard": "#000000", "FEM n_step10": "#0072B2"}
    for ax, (field, metric, title) in zip(axes.ravel(), selected):
        for ref in refs:
            sub = summary[
                (summary["reference"] == ref)
                & (summary["field"] == field)
                & (summary["metric"] == metric)
            ].sort_values("cycle")
            ax.plot(
                sub["cycle"],
                sub["PIDL_over_FEM_projected"],
                marker="o",
                lw=1.5,
                label=ref,
                color=colors[ref],
            )
        ax.axhline(1.0, color="0.5", lw=1.0, ls="--")
        ax.set_title(title)
        ax.set_xlabel("FEM cycle, PIDL saved j=c-1")
        ax.set_ylabel("PIDL / FEM")
        ax.grid(alpha=0.25)
        if field in {"psi_plus_active", "energy"}:
            ax.set_yscale("symlog", linthresh=0.05)
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle("Aligned FEM/PIDL tiers: standard vs n_step10 FEM reference on common PIDL probes")
    fig.savefig(OUT_FIG, dpi=220)
    plt.close(fig)


def main() -> int:
    standard = build_standard_common_probe()
    nstep10 = build_nstep10_common_probe(standard)
    common = pd.concat([standard, nstep10], ignore_index=True)
    energy = build_energy_tiers()
    summary = build_summary(common, energy)

    OUT_COMMON.parent.mkdir(parents=True, exist_ok=True)
    common.to_csv(OUT_COMMON, index=False)
    energy.to_csv(OUT_ENERGY, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    plot_summary(summary)

    key = summary[
        (summary["cycle"] == 69)
        & (
            ((summary["field"] == "alpha_bar") & summary["metric"].isin(["tip_2l0_mean", "p99"]))
            | ((summary["field"] == "psi_plus_active") & (summary["metric"] == "tip_2l0_mean"))
            | ((summary["field"] == "energy") & (summary["metric"] == "E_d_abs_and_delta"))
        )
    ]
    print(key[["reference", "field", "metric", "PIDL_over_FEM_projected"]].to_string(index=False))
    print(f"wrote {OUT_COMMON}")
    print(f"wrote {OUT_ENERGY}")
    print(f"wrote {OUT_SUMMARY}")
    print(f"wrote {OUT_FIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
