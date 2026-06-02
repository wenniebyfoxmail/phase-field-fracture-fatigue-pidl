#!/usr/bin/env python3
"""Diagnose co-location of raw psi, degradation, active driver, and history.

The previous n_step=2 audit showed a key paradox: late PIDL has larger
near-tip raw psi than FEM, but much smaller active psi = g(alpha) * psi_raw
and much smaller fatigue-history increments.  This script asks whether those
quantities are co-located on the same PIDL probes.

Both FEM Request21 n_step=2 fields and PIDL fields are evaluated on the PIDL
FEM-derived triangular mesh.  FEM fields are area-projected to the PIDL probes.
"""
from __future__ import annotations

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ANALYSIS = ROOT / "_analysis_fem_mechanism_20260528"
EXPERIMENT = (
    ANALYSIS
    / "experiments"
    / "strict_femmesh_soft_hist0_alignment_20260529"
)
OUT_DIR = EXPERIMENT / "2_figures"

sys.path.insert(0, str(HERE))
from compare_pidl_to_fem_nstep2_timing import (  # noqa: E402
    CYCLES,
    INCREMENT_PREV,
    NSTEP2_MAT,
    PIDL_ARCHIVE,
    PIDL_MESH,
    field_at_cycle,
    load_fem_handoff,
)
from posthoc_mesh_probe_alignment import (  # noqa: E402
    build_assignment,
    mesh_from_settings,
    pidl_model_and_mesh,
    project_to_pidl,
)


def finite_mask(*arrays: np.ndarray) -> np.ndarray:
    mask = np.ones_like(np.asarray(arrays[0], dtype=float), dtype=bool)
    for arr in arrays:
        mask &= np.isfinite(arr)
    return mask


def weighted_mean(values: np.ndarray, weights: np.ndarray, mask: np.ndarray) -> float:
    m = mask & np.isfinite(values)
    if not np.any(m):
        return float("nan")
    return float(np.sum(values[m] * weights[m]) / np.sum(weights[m]))


def weighted_corr(x: np.ndarray, y: np.ndarray, weights: np.ndarray, mask: np.ndarray) -> float:
    m = mask & finite_mask(x, y)
    if np.count_nonzero(m) < 3:
        return float("nan")
    w = weights[m]
    xv = x[m]
    yv = y[m]
    wx = np.sum(w * xv) / np.sum(w)
    wy = np.sum(w * yv) / np.sum(w)
    cov = np.sum(w * (xv - wx) * (yv - wy)) / np.sum(w)
    vx = np.sum(w * (xv - wx) ** 2) / np.sum(w)
    vy = np.sum(w * (yv - wy) ** 2) / np.sum(w)
    if vx <= 0.0 or vy <= 0.0:
        return float("nan")
    return float(cov / np.sqrt(vx * vy))


def top_mask(values: np.ndarray, base_mask: np.ndarray, q: float = 99.0) -> np.ndarray:
    m = base_mask & np.isfinite(values)
    out = np.zeros_like(base_mask, dtype=bool)
    if not np.any(m):
        return out
    threshold = np.nanpercentile(values[m], q)
    out[m] = values[m] >= threshold
    return out


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    den = np.count_nonzero(a | b)
    if den == 0:
        return float("nan")
    return float(np.count_nonzero(a & b) / den)


def argmax_row(
    label: str,
    cycle: int,
    selector: str,
    values: np.ndarray,
    fields: dict[str, np.ndarray],
    centroids: np.ndarray,
    mask: np.ndarray,
) -> dict[str, object]:
    m = mask & np.isfinite(values)
    if not np.any(m):
        return {}
    ids = np.where(m)[0]
    idx = int(ids[np.nanargmax(values[m])])
    return {
        "method": label,
        "cycle": cycle,
        "selector": selector,
        "elem_idx": idx,
        "x": float(centroids[idx, 0]),
        "y": float(centroids[idx, 1]),
        "alpha_bar": float(fields["alpha_bar"][idx]),
        "delta_alpha_bar": float(fields["delta_alpha_bar"][idx]),
        "psi_raw": float(fields["psi_raw"][idx]),
        "g_alpha": float(fields["g_alpha"][idx]),
        "psi_active": float(fields["psi_active"][idx]),
    }


def method_summary(
    label: str,
    cycle: int,
    fields: dict[str, np.ndarray],
    centroids: np.ndarray,
    areas: np.ndarray,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    r = np.hypot(centroids[:, 0], centroids[:, 1])
    domain = finite_mask(fields["alpha_bar"], fields["psi_raw"], fields["g_alpha"], fields["psi_active"])
    tip2 = domain & (r <= 0.02)
    raw_top = top_mask(fields["psi_raw"], domain, 99.0)
    active_top = top_mask(fields["psi_active"], domain, 99.0)
    delta_top = top_mask(fields["delta_alpha_bar"], domain, 99.0)

    raw_tip = weighted_mean(fields["psi_raw"], areas, tip2)
    active_tip = weighted_mean(fields["psi_active"], areas, tip2)
    row = {
        "method": label,
        "cycle": cycle,
        "tip2_alpha_bar_mean": weighted_mean(fields["alpha_bar"], areas, tip2),
        "tip2_delta_alpha_bar_mean": weighted_mean(fields["delta_alpha_bar"], areas, tip2),
        "tip2_psi_raw_mean": raw_tip,
        "tip2_g_alpha_mean": weighted_mean(fields["g_alpha"], areas, tip2),
        "tip2_psi_active_mean": active_tip,
        "tip2_effective_g": active_tip / raw_tip if abs(raw_tip) > 1e-30 else np.nan,
        "tip2_corr_raw_g": weighted_corr(fields["psi_raw"], fields["g_alpha"], areas, tip2),
        "tip2_corr_raw_active": weighted_corr(fields["psi_raw"], fields["psi_active"], areas, tip2),
        "tip2_corr_active_delta_alpha_bar": weighted_corr(
            fields["psi_active"], fields["delta_alpha_bar"], areas, tip2
        ),
        "domain_corr_raw_g": weighted_corr(fields["psi_raw"], fields["g_alpha"], areas, domain),
        "domain_corr_active_delta_alpha_bar": weighted_corr(
            fields["psi_active"], fields["delta_alpha_bar"], areas, domain
        ),
        "domain_top_raw_g_mean": weighted_mean(fields["g_alpha"], areas, raw_top),
        "domain_top_raw_active_mean": weighted_mean(fields["psi_active"], areas, raw_top),
        "domain_top_active_raw_mean": weighted_mean(fields["psi_raw"], areas, active_top),
        "domain_top_raw_active_jaccard": jaccard(raw_top, active_top),
        "domain_top_active_delta_jaccard": jaccard(active_top, delta_top),
    }

    extrema = [
        argmax_row(label, cycle, "max_psi_raw", fields["psi_raw"], fields, centroids, domain),
        argmax_row(label, cycle, "max_psi_active", fields["psi_active"], fields, centroids, domain),
        argmax_row(label, cycle, "max_delta_alpha_bar", fields["delta_alpha_bar"], fields, centroids, domain),
    ]
    extrema = [item for item in extrema if item]
    if len(extrema) >= 2:
        raw = extrema[0]
        active = extrema[1]
        row["distance_max_raw_to_max_active"] = float(
            np.hypot(float(raw["x"]) - float(active["x"]), float(raw["y"]) - float(active["y"]))
        )
    else:
        row["distance_max_raw_to_max_active"] = np.nan
    return row, extrema


def build_fields() -> tuple[pd.DataFrame, pd.DataFrame]:
    fem = load_fem_handoff(NSTEP2_MAT)
    fem_cycles = fem["cycles"]
    fem_fields = fem["fields"]
    pidl_mesh = mesh_from_settings(PIDL_ARCHIVE, PIDL_MESH)
    first = pidl_model_and_mesh(PIDL_ARCHIVE, 0.12, 0, pidl_mesh)
    assignment = build_assignment(
        fem["centroids"],
        first["centroids"],
        first["inp"],
        first["conn"],
    )
    pidl_cache: dict[int, dict[str, np.ndarray]] = {0: first}

    def pidl_state(saved_index: int) -> dict[str, np.ndarray]:
        if saved_index not in pidl_cache:
            pidl_cache[saved_index] = pidl_model_and_mesh(PIDL_ARCHIVE, 0.12, saved_index, pidl_mesh)
        return pidl_cache[saved_index]

    rows: list[dict[str, object]] = []
    extrema_rows: list[dict[str, object]] = []

    for cycle in CYCLES:
        prev_cycle = INCREMENT_PREV[cycle]
        pidl_idx = cycle - 1
        pidl = pidl_state(pidl_idx)

        fem_native = {
            "alpha_bar": field_at_cycle(fem_fields, fem_cycles, "alpha_bar", cycle),
            "psi_raw": field_at_cycle(fem_fields, fem_cycles, "psi_raw", cycle),
            "g_alpha": field_at_cycle(fem_fields, fem_cycles, "g_alpha", cycle),
            "psi_active": field_at_cycle(fem_fields, fem_cycles, "psi_active", cycle),
        }
        pidl_native = {
            "alpha_bar": pidl["alpha_bar"],
            "psi_raw": pidl["psi_plus_raw"],
            "g_alpha": (1.0 - pidl["alpha"]) ** 2 + 1e-6,
            "psi_active": pidl["psi_plus_active"],
        }
        if prev_cycle is None:
            fem_native["delta_alpha_bar"] = fem_native["alpha_bar"]
            pidl_native["delta_alpha_bar"] = pidl_native["alpha_bar"]
        else:
            prev_pidl = pidl_state(prev_cycle - 1)
            fem_native["delta_alpha_bar"] = (
                fem_native["alpha_bar"]
                - field_at_cycle(fem_fields, fem_cycles, "alpha_bar", prev_cycle)
            )
            pidl_native["delta_alpha_bar"] = pidl_native["alpha_bar"] - prev_pidl["alpha_bar"]

        fem_projected = {
            key: project_to_pidl(value, fem["areas"], assignment, len(pidl["areas"]))
            for key, value in fem_native.items()
        }
        for label, fields in (("FEM_nstep2_projected", fem_projected), ("PIDL", pidl_native)):
            row, extrema = method_summary(label, cycle, fields, pidl["centroids"], pidl["areas"])
            rows.append(row)
            extrema_rows.extend(extrema)
    return pd.DataFrame(rows), pd.DataFrame(extrema_rows)


def add_ratio_rows(summary: pd.DataFrame) -> pd.DataFrame:
    ratio_rows: list[dict[str, object]] = []
    value_cols = [col for col in summary.columns if col not in {"method", "cycle"}]
    for cycle in CYCLES:
        fem = summary[(summary["method"] == "FEM_nstep2_projected") & (summary["cycle"] == cycle)]
        pidl = summary[(summary["method"] == "PIDL") & (summary["cycle"] == cycle)]
        if fem.empty or pidl.empty:
            continue
        row: dict[str, object] = {"method": "PIDL_over_FEM_nstep2", "cycle": cycle}
        for col in value_cols:
            fval = float(fem[col].iloc[0])
            pval = float(pidl[col].iloc[0])
            row[col] = pval / fval if np.isfinite(fval) and abs(fval) > 1e-30 else np.nan
        ratio_rows.append(row)
    return pd.concat([summary, pd.DataFrame(ratio_rows)], ignore_index=True)


def plot_summary(summary: pd.DataFrame, out_path: Path) -> None:
    ratio = summary[summary["method"] == "PIDL_over_FEM_nstep2"].sort_values("cycle")
    panels = [
        ("tip2_effective_g", "effective g in tip2"),
        ("tip2_corr_raw_g", "corr(raw psi, g) in tip2"),
        ("domain_top_raw_g_mean", "g on top raw-psi elements"),
        ("domain_top_raw_active_jaccard", "top raw vs top active overlap"),
        ("domain_top_active_delta_jaccard", "top active vs top d-alpha overlap"),
        ("distance_max_raw_to_max_active", "distance max raw to max active"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(13.2, 7.0), constrained_layout=True)
    for ax, (col, title) in zip(axes.ravel(), panels):
        ax.plot(ratio["cycle"], ratio[col], marker="o", lw=1.5, color="#D55E00")
        ax.axhline(1.0, color="0.45", lw=1.0, ls="--")
        ax.set_title(title)
        ax.set_xlabel("cycle")
        ax.set_ylabel("PIDL / FEM n_step2")
        ax.grid(alpha=0.25)
        if col in {"tip2_effective_g", "domain_top_raw_g_mean", "domain_top_raw_active_jaccard"}:
            ax.set_yscale("symlog", linthresh=0.05)
    fig.suptitle("Why high PIDL raw psi does not become high active driver")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def write_note(summary: pd.DataFrame, extrema: pd.DataFrame, out_path: Path) -> None:
    ratio = summary[summary["method"] == "PIDL_over_FEM_nstep2"].set_index("cycle")
    lines = [
        "# Active Driver Co-location Audit",
        "",
        "Question: why can PIDL have high raw `psi` but tiny active `g(alpha) * psi_raw` and tiny history increments?",
        "",
        "Reference: FEM Request21 `n_step=2` (`[1,0]`) projected onto the strict FEM-mesh PIDL probes.",
        "",
        "## Ratio Summary",
        "",
        "| cycle | effective g tip2 | corr(raw,g) tip2 | top raw/active overlap | top active/dalpha overlap | distance max raw-active |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for cycle in CYCLES:
        row = ratio.loc[cycle]
        lines.append(
            f"| {cycle} | "
            f"{row['tip2_effective_g']:.4g} | "
            f"{row['tip2_corr_raw_g']:.4g} | "
            f"{row['domain_top_raw_active_jaccard']:.4g} | "
            f"{row['domain_top_active_delta_jaccard']:.4g} | "
            f"{row['distance_max_raw_to_max_active']:.4g} |"
        )
    lines += [
        "",
        "## Reading",
        "",
        "The late-cycle failure is not simply that PIDL lacks raw tensile energy. The audit checks whether raw tensile energy is spatially aligned with low damage/degradation, active driver, and the fatigue-history increment. If the top raw-psi elements do not overlap the top active-driver/history-increment elements, the crack-tip mechanism is de-coupled even when scalar raw `psi` is large.",
        "",
        "The extrema table records the element and location of max raw `psi`, max active `psi`, and max `Delta alpha_bar` for each method/cycle.",
        "",
        "Generated files:",
        "",
        f"- `{OUT_DIR / 'pidl_vs_fem_nstep2_active_driver_colocation_summary.csv'}`",
        f"- `{OUT_DIR / 'pidl_vs_fem_nstep2_active_driver_colocation_extrema.csv'}`",
        f"- `{OUT_DIR / 'pidl_vs_fem_nstep2_active_driver_colocation_ratios.png'}`",
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary, extrema = build_fields()
    summary = add_ratio_rows(summary)
    summary_path = OUT_DIR / "pidl_vs_fem_nstep2_active_driver_colocation_summary.csv"
    extrema_path = OUT_DIR / "pidl_vs_fem_nstep2_active_driver_colocation_extrema.csv"
    fig_path = OUT_DIR / "pidl_vs_fem_nstep2_active_driver_colocation_ratios.png"
    note_path = EXPERIMENT / "1_analysis" / "pidl_vs_fem_nstep2_active_driver_colocation.md"
    summary.to_csv(summary_path, index=False)
    extrema.to_csv(extrema_path, index=False)
    plot_summary(summary, fig_path)
    write_note(summary, extrema, note_path)
    ratio = summary[summary["method"] == "PIDL_over_FEM_nstep2"]
    keep = [
        "cycle",
        "tip2_effective_g",
        "tip2_corr_raw_g",
        "domain_top_raw_active_jaccard",
        "domain_top_active_delta_jaccard",
        "distance_max_raw_to_max_active",
    ]
    print(ratio[keep].to_string(index=False))
    print(f"wrote {summary_path}")
    print(f"wrote {extrema_path}")
    print(f"wrote {fig_path}")
    print(f"wrote {note_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
