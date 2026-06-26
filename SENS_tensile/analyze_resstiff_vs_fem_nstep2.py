#!/usr/bin/env python3
"""Analyze the PIDL residual-stiffness discriminator against FEM n_step=2.

The PIDL archive is the strict FEM-mesh soft-hist0 benchmark with only
``g(alpha)`` changed to ``(1-alpha)^2 + 1e-6``.  PIDL saved index ``j`` maps to
FEM cycle ``c=j+1`` under the current state-timing convention.
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
EXPERIMENT = ANALYSIS / "experiments" / "resstiff_alignment_20260603"
SYNC = EXPERIMENT / "0_sync"
OUT_ANALYSIS = EXPERIMENT / "1_analysis"
OUT_FIG = EXPERIMENT / "2_figures"
ARCHIVE_NAME = (
    "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
    "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
    "N100_R0.0_Umax0.12_femmesh_softHist0_resStiff1e6_eta1em06"
)
ARCHIVE = SYNC / ARCHIVE_NAME
NSTEP2_DIR = (
    ANALYSIS
    / "request21_fem_nstep"
    / "source_handoff"
    / "_pidl_handoff_reverseBC_u12_soft_hist0_nstep2_2026-05-29"
)
NSTEP2_MAT = NSTEP2_DIR / "reverseBC_u12_soft_hist0_nstep2_element_fields_c1_c70.mat"

SAVED_TO_FEM = {0: 1, 1: 2, 2: 3, 3: 4, 19: 20, 39: 40, 68: 69, 82: 83, 85: 86}
FIELDS = ("alpha_bar", "delta_alpha_bar", "psi_raw", "g_alpha", "psi_active")
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


def cycle_index(cycles: np.ndarray, cycle: int) -> int | None:
    idx = np.where(cycles == cycle)[0]
    return int(idx[0]) if len(idx) == 1 else None


def weighted_mean(values: np.ndarray, areas: np.ndarray, mask: np.ndarray) -> float:
    m = mask & np.isfinite(values)
    if not np.any(m):
        return float("nan")
    return float(np.sum(values[m] * areas[m]) / np.sum(areas[m]))


def reductions(values: np.ndarray, areas: np.ndarray, centroids: np.ndarray) -> dict[str, float]:
    finite = np.isfinite(values)
    r = np.hypot(centroids[:, 0], centroids[:, 1])
    tip2 = r <= 0.02
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
    return {
        "max": float(np.nanmax(values)),
        "p999": float(np.nanpercentile(values[finite], 99.9)),
        "p99": float(np.nanpercentile(values[finite], 99.0)),
        "domain_mean": weighted_mean(values, areas, finite),
        "tip_2l0_mean": weighted_mean(values, areas, tip2),
        "tip_2l0_integral": float(np.nansum(values[tip2] * areas[tip2])),
        "right_band_mean": weighted_mean(values, areas, centroids[:, 0] >= 0.45),
    }


def project_nearest(fem_values: np.ndarray, fem_centroids: np.ndarray, pidl_centroids: np.ndarray) -> np.ndarray:
    tree = cKDTree(fem_centroids)
    _, idx = tree.query(pidl_centroids, k=1)
    return fem_values[idx]


def load_pidl(saved_idx: int) -> dict[str, np.ndarray]:
    path = ARCHIVE / "element_diagnostics" / f"element_fields_cycle_{saved_idx:04d}.npz"
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


def pidl_fields(raw: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        "alpha_bar": raw["hist_fat_elem"],
        "delta_alpha_bar": pidl_delta_alpha_bar(raw),
        "psi_raw": raw["psi_raw_elem"],
        "g_alpha": raw["g_alpha_elem"],
        "psi_active": raw["psi_active_elem"],
    }


def build_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fem = load_fem()
    rows: list[dict[str, object]] = []
    scalar_rows: list[dict[str, object]] = []
    extrema_rows: list[dict[str, object]] = []

    pidl_cache = {j: load_pidl(j) for j in SAVED_TO_FEM}
    for saved_idx, fem_cycle in SAVED_TO_FEM.items():
        pidl_raw = pidl_cache[saved_idx]
        centroids = np.column_stack([pidl_raw["elem_x"], pidl_raw["elem_y"]])
        areas = pidl_raw["area_elem"]
        pfields = pidl_fields(pidl_raw)

        fidx = cycle_index(fem["cycles"], fem_cycle)
        if fidx is None:
            scalar_rows.append(
                {
                    "saved_index": saved_idx,
                    "fem_cycle": fem_cycle,
                    "note": "FEM n_step2 cycle missing; PIDL event beyond available c70 reference",
                    "alpha_bar_max": float(np.nanmax(pfields["alpha_bar"])),
                    "f_min": float(np.nanmin(pidl_raw["f_fatigue_elem"])),
                    "psi_raw_max": float(np.nanmax(pfields["psi_raw"])),
                    "psi_active_max": float(np.nanmax(pfields["psi_active"])),
                    "E_el": float(np.nansum(pidl_raw["E_el_elem"])),
                    "E_d": float(np.nansum(pidl_raw["E_d_elem"])),
                }
            )
            continue

        fem_fields = {
            name: fem["fields"][name][fidx]
            for name in ("alpha_bar", "psi_raw", "g_alpha", "psi_active")
        }
        if fem_cycle == 1:
            fem_fields["delta_alpha_bar"] = fem_fields["alpha_bar"]
        else:
            prev_fidx = cycle_index(fem["cycles"], fem_cycle - 1)
            fem_fields["delta_alpha_bar"] = (
                fem_fields["alpha_bar"] - fem["fields"]["alpha_bar"][prev_fidx]
            )

        scalar_rows.append(
            {
                "saved_index": saved_idx,
                "fem_cycle": fem_cycle,
                "note": "PIDL saved index j mapped to FEM cycle c=j+1",
                "alpha_bar_max": float(np.nanmax(pfields["alpha_bar"])),
                "f_min": float(np.nanmin(pidl_raw["f_fatigue_elem"])),
                "psi_raw_max": float(np.nanmax(pfields["psi_raw"])),
                "psi_active_max": float(np.nanmax(pfields["psi_active"])),
                "g_min": float(np.nanmin(pfields["g_alpha"])),
                "E_el": float(np.nansum(pidl_raw["E_el_elem"])),
                "E_d": float(np.nansum(pidl_raw["E_d_elem"])),
            }
        )

        for field in FIELDS:
            fem_proj = project_nearest(fem_fields[field], fem["centroids"], centroids)
            fem_red = reductions(fem_proj, areas, centroids)
            pidl_red = reductions(pfields[field], areas, centroids)
            for metric, fem_value in fem_red.items():
                pidl_value = pidl_red[metric]
                rows.append(
                    {
                        "saved_index": saved_idx,
                        "fem_cycle": fem_cycle,
                        "field": field,
                        "metric": metric,
                        "FEM_nstep2_projected": fem_value,
                        "PIDL_resstiff": pidl_value,
                        "PIDL_over_FEM": (
                            pidl_value / fem_value
                            if np.isfinite(fem_value) and abs(fem_value) > 1e-30
                            else np.nan
                        ),
                    }
                )
            if field != FIELDS[-1]:
                continue
            for selector, values in (
                ("max_psi_raw", pfields["psi_raw"]),
                ("max_psi_active", pfields["psi_active"]),
                ("max_delta_alpha_bar", pfields["delta_alpha_bar"]),
            ):
                if not np.any(np.isfinite(values)):
                    extrema_rows.append(
                        {
                            "saved_index": saved_idx,
                            "fem_cycle": fem_cycle,
                            "selector": selector,
                            "x": np.nan,
                            "y": np.nan,
                            "alpha_bar": np.nan,
                            "psi_raw": np.nan,
                            "g_alpha": np.nan,
                            "psi_active": np.nan,
                            "delta_alpha_bar": np.nan,
                            "note": "unavailable in legacy PIDL diagnostics",
                        }
                    )
                    continue
                idx = int(np.nanargmax(values))
                extrema_rows.append(
                    {
                        "saved_index": saved_idx,
                        "fem_cycle": fem_cycle,
                        "selector": selector,
                        "x": float(centroids[idx, 0]),
                        "y": float(centroids[idx, 1]),
                        "alpha_bar": float(pfields["alpha_bar"][idx]),
                        "psi_raw": float(pfields["psi_raw"][idx]),
                        "g_alpha": float(pfields["g_alpha"][idx]),
                        "psi_active": float(pfields["psi_active"][idx]),
                        "delta_alpha_bar": float(pfields["delta_alpha_bar"][idx]),
                        "note": "",
                    }
                )
    return pd.DataFrame(rows), pd.DataFrame(scalar_rows), pd.DataFrame(extrema_rows)


def plot_gate(ratios: pd.DataFrame, scalars: pd.DataFrame) -> Path:
    selected = [
        ("alpha_bar", "tip_2l0_mean", "alpha_bar tip2"),
        ("delta_alpha_bar", "tip_2l0_mean", "Delta alpha_bar tip2"),
        ("psi_raw", "tip_2l0_mean", "psi_raw tip2"),
        ("g_alpha", "tip_2l0_mean", "g(alpha) tip2"),
        ("psi_active", "tip_2l0_mean", "psi_active tip2"),
        ("psi_active", "max", "psi_active max"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(13.2, 7.0), constrained_layout=True)
    for ax, (field, metric, title) in zip(axes.ravel(), selected):
        sub = ratios[(ratios["field"] == field) & (ratios["metric"] == metric)].sort_values("fem_cycle")
        ax.plot(sub["fem_cycle"], sub["PIDL_over_FEM"], marker="o", lw=1.5, color="#0072B2")
        ax.axhline(1.0, color="0.45", lw=1.0, ls="--")
        ax.set_title(title)
        ax.set_xlabel("FEM cycle mapped from PIDL j")
        ax.set_ylabel("PIDL / FEM n_step2")
        ax.set_yscale("symlog", linthresh=0.05)
        ax.grid(alpha=0.25)
    fig.suptitle("Residual-stiffness PIDL vs FEM n_step2 field gate")
    out = OUT_FIG / "resstiff_vs_fem_nstep2_field_gate.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 4.3), constrained_layout=True)
    scalars = scalars.sort_values("saved_index")
    ax.plot(scalars["saved_index"], scalars["alpha_bar_max"], marker="o", label="alpha_bar max")
    ax2 = ax.twinx()
    ax2.plot(scalars["saved_index"], scalars["psi_raw_max"], marker="s", color="#D55E00", label="psi_raw max")
    ax.set_xlabel("PIDL saved index j")
    ax.set_ylabel("alpha_bar max")
    ax2.set_ylabel("psi_raw max")
    ax.grid(alpha=0.25)
    lines = ax.get_lines() + ax2.get_lines()
    ax.legend(lines, [line.get_label() for line in lines], loc="upper left")
    fig.suptitle("Residual-stiffness PIDL scalar trajectory")
    scalar_out = OUT_FIG / "resstiff_scalar_alpha_bar_psi_raw.png"
    fig.savefig(scalar_out, dpi=220)
    plt.close(fig)
    return out


def write_note(ratios: pd.DataFrame, scalars: pd.DataFrame, extrema: pd.DataFrame, fig_path: Path) -> Path:
    OUT_ANALYSIS.mkdir(parents=True, exist_ok=True)
    early = ratios[
        ratios["fem_cycle"].isin([1, 2, 3, 4])
        & ratios["field"].isin(["alpha_bar", "psi_raw", "g_alpha", "psi_active", "delta_alpha_bar"])
        & ratios["metric"].eq("tip_2l0_mean")
    ].pivot_table(index=["saved_index", "fem_cycle"], columns="field", values="PIDL_over_FEM")
    c69 = ratios[
        ratios["fem_cycle"].eq(69)
        & ratios["field"].isin(["alpha_bar", "psi_raw", "g_alpha", "psi_active"])
        & ratios["metric"].eq("tip_2l0_mean")
    ].pivot_table(index=["saved_index", "fem_cycle"], columns="field", values="PIDL_over_FEM")
    lines = [
        "# Residual-Stiffness Alignment Discriminator",
        "",
        "Setup: strict FEM-mesh soft-hist0 PIDL, with only `g(alpha)` changed to `(1-alpha)^2 + 1e-6`.",
        "",
        "Timing convention: PIDL saved index `j` is compared to FEM n_step2 cycle `c=j+1`. Therefore PIDL `cycle_0000` is not pristine FEM state0; it maps to FEM c1.",
        "",
        "## Event",
        "",
        "- first boundary hit: PIDL j82",
        "- confirmed stop: PIDL j85",
        "- FEM n_step2 reference: N_f about c70",
        "",
        "## Early Tip-2l0 Ratios",
        "",
        early.to_markdown(floatfmt=".4g"),
        "",
        "## c69 Tip-2l0 Ratios",
        "",
        c69.to_markdown(floatfmt=".4g"),
        "",
        "## Interpretation",
        "",
        "Adding FEM-style residual stiffness does not close the mechanism gap. It preserves a nonzero `g_alpha` floor in fully damaged elements, but the active process-zone comparison is still governed by spatial co-location: raw tensile energy, degradation, and fatigue increments do not line up FEM-like near the tip.",
        "",
        "The run still shows late active-driver collapse. At PIDL j82-j85, `psi_raw_max` remains around 2.4e3 while `psi_active_max` is only about 1.2e-2 because the raw-psi maximum sits in nearly fully damaged material where `g_alpha` is near the residual floor.",
        "",
        "Generated files:",
        "",
        f"- `{OUT_FIG / 'resstiff_vs_fem_nstep2_field_gate.csv'}`",
        f"- `{OUT_FIG / 'resstiff_vs_fem_nstep2_scalars.csv'}`",
        f"- `{OUT_FIG / 'resstiff_vs_fem_nstep2_extrema.csv'}`",
        f"- `{fig_path}`",
        f"- `{OUT_FIG / 'resstiff_scalar_alpha_bar_psi_raw.png'}`",
    ]
    out = OUT_ANALYSIS / "resstiff_vs_fem_nstep2_result.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    ratios, scalars, extrema = build_tables()
    ratio_path = OUT_FIG / "resstiff_vs_fem_nstep2_field_gate.csv"
    scalar_path = OUT_FIG / "resstiff_vs_fem_nstep2_scalars.csv"
    extrema_path = OUT_FIG / "resstiff_vs_fem_nstep2_extrema.csv"
    ratios.to_csv(ratio_path, index=False)
    scalars.to_csv(scalar_path, index=False)
    extrema.to_csv(extrema_path, index=False)
    fig_path = plot_gate(ratios, scalars)
    note_path = write_note(ratios, scalars, extrema, fig_path)
    print(scalars.to_string(index=False))
    print(f"wrote {ratio_path}")
    print(f"wrote {scalar_path}")
    print(f"wrote {extrema_path}")
    print(f"wrote {fig_path}")
    print(f"wrote {note_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
