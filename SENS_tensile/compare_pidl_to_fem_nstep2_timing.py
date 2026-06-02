#!/usr/bin/env python3
"""Compare strict FEM-mesh PIDL against FEM Request21 n_step=2.

This audit targets the cadence question directly.  FEM n_step=2 retains
`[peak, unload]` states and fractures at c70.  PIDL is mapped with the current
state-timing convention: FEM cycle c -> PIDL saved checkpoint j=c-1.

The output focuses on mechanism quantities rather than N_f alone:

* alpha_bar fatigue history,
* psi_raw,
* degradation g(alpha),
* psi_active = g(alpha) * psi_raw,
* Delta E_d from c1,
* per-cycle Delta alpha_bar increments.
"""
from __future__ import annotations

from pathlib import Path
import sys

import h5py
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
REQUEST21 = ANALYSIS / "request21_fem_nstep" / "source_handoff"
NSTEP2_DIR = REQUEST21 / "_pidl_handoff_reverseBC_u12_soft_hist0_nstep2_2026-05-29"
NSTEP2_MAT = NSTEP2_DIR / "reverseBC_u12_soft_hist0_nstep2_element_fields_c1_c70.mat"
NSTEP2_CSV = NSTEP2_DIR / "reverseBC_u12_soft_hist0_nstep2_cyclewise_mechanism_metrics.csv"
PIDL_ENERGY = ANALYSIS / "femmesh_pidl_vs_soft_hist0_incremental_energy_c1_ref.csv"
PIDL_ARCHIVE = (
    HERE
    / "hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_"
    "PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_"
    "N100_R0.0_Umax0.12_femmesh_softHist0"
)
PIDL_MESH = HERE / "meshed_geom_fem_soft_hist0.msh"

sys.path.insert(0, str(HERE))
from posthoc_mesh_probe_alignment import (  # noqa: E402
    build_assignment,
    metrics,
    mesh_from_settings,
    pidl_model_and_mesh,
    project_to_pidl,
)

CYCLES = (1, 2, 3, 20, 40, 69)
INCREMENT_PREV = {1: None, 2: 1, 3: 2, 20: 19, 40: 39, 69: 68}
FIELDS = ("alpha_bar", "psi_raw", "g_alpha", "psi_active", "delta_alpha_bar")
KEY_METRICS = ("tip_2l0_mean", "p99", "p999", "max", "domain_mean")


def load_fem_handoff(path: Path) -> dict[str, object]:
    with h5py.File(path, "r") as h5:
        cycles = np.asarray(h5["cycles"]).reshape(-1).astype(int)
        centroids = np.asarray(h5["element_centroids"], dtype=float).T
        if float(np.nanmax(centroids[:, 0])) > 0.75:
            centroids[:, :2] -= 0.5
        areas = np.asarray(h5["element_area"], dtype=float).reshape(-1)
        d = np.asarray(h5["d_elem"], dtype=float)
        alpha_bar = np.asarray(h5["alpha_bar_elem"], dtype=float)
        psi_raw = np.asarray(h5["psi_plus_elem"], dtype=float)
        # h5py sees MATLAB v7.3 arrays as cycle x element for this handoff.
        if d.shape[0] != len(cycles):
            d = d.T
            alpha_bar = alpha_bar.T
            psi_raw = psi_raw.T
    g_alpha = (1.0 - d) ** 2 + 1e-6
    psi_active = g_alpha * psi_raw
    return {
        "cycles": cycles,
        "centroids": centroids,
        "areas": areas,
        "fields": {
            "alpha_bar": alpha_bar,
            "psi_raw": psi_raw,
            "g_alpha": g_alpha,
            "psi_active": psi_active,
        },
    }


def safe_ratio(num: float, den: float) -> float:
    if not np.isfinite(num) or not np.isfinite(den) or abs(den) <= 1e-30:
        return float("nan")
    return float(num / den)


def field_at_cycle(fields: dict[str, np.ndarray], cycles: np.ndarray, name: str, cycle: int) -> np.ndarray:
    idx = np.where(cycles == cycle)[0]
    if len(idx) != 1:
        raise KeyError(f"cycle {cycle} not found in FEM handoff")
    return fields[name][int(idx[0])]


def compute_rows() -> tuple[pd.DataFrame, pd.DataFrame]:
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
    compact_rows: list[dict[str, object]] = []

    for cycle in CYCLES:
        pidl_idx = cycle - 1
        pidl = pidl_state(pidl_idx)

        fem_native = {
            name: field_at_cycle(fem_fields, fem_cycles, name, cycle)
            for name in ("alpha_bar", "psi_raw", "g_alpha", "psi_active")
        }
        pidl_native = {
            "alpha_bar": pidl["alpha_bar"],
            "psi_raw": pidl["psi_plus_raw"],
            "g_alpha": (1.0 - pidl["alpha"]) ** 2 + 1e-6,
            "psi_active": pidl["psi_plus_active"],
        }

        prev_cycle = INCREMENT_PREV[cycle]
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

        for field in FIELDS:
            fem_proj = project_to_pidl(
                fem_native[field],
                fem["areas"],
                assignment,
                len(pidl_native[field]),
            )
            fem_metrics = metrics(fem_proj, pidl["areas"], pidl["centroids"])
            pidl_metrics = metrics(pidl_native[field], pidl["areas"], pidl["centroids"])
            for metric in sorted(fem_metrics):
                fv = fem_metrics[metric]
                pv = pidl_metrics[metric]
                row = {
                    "reference": "FEM n_step2 [1,0]",
                    "cycle": cycle,
                    "fem_cycle": cycle,
                    "pidl_saved_index": pidl_idx,
                    "field": field,
                    "metric": metric,
                    "FEM_projected_to_PIDL": fv,
                    "PIDL_native": pv,
                    "PIDL_over_FEM_projected": safe_ratio(pv, fv),
                    "FEM_projected_over_PIDL": safe_ratio(fv, pv),
                }
                rows.append(row)
                if metric in KEY_METRICS:
                    compact_rows.append(row)

    compact = pd.DataFrame(compact_rows)

    fem_energy = pd.read_csv(NSTEP2_CSV)
    pidl_energy = pd.read_csv(PIDL_ENERGY)
    fem_energy = fem_energy[fem_energy["cycle"].isin(CYCLES)].copy()
    pidl_energy = pidl_energy[pidl_energy["cycle"].isin(CYCLES)].copy()
    fem_e1 = float(fem_energy.loc[fem_energy["cycle"] == 1, "E_d"].iloc[0])
    pidl_e1 = float(pidl_energy.loc[pidl_energy["cycle"] == 1, "pidl_E_d"].iloc[0])
    energy_rows = []
    for cycle in CYCLES:
        fem_ed = float(fem_energy.loc[fem_energy["cycle"] == cycle, "E_d"].iloc[0])
        pidl_ed = float(pidl_energy.loc[pidl_energy["cycle"] == cycle, "pidl_E_d"].iloc[0])
        delta_fem = fem_ed - fem_e1
        delta_pidl = pidl_ed - pidl_e1
        energy_rows.append(
            {
                "reference": "FEM n_step2 [1,0]",
                "cycle": cycle,
                "fem_cycle": cycle,
                "pidl_saved_index": cycle - 1,
                "field": "Delta_E_d",
                "metric": "from_c1",
                "FEM_projected_to_PIDL": delta_fem,
                "PIDL_native": delta_pidl,
                "PIDL_over_FEM_projected": safe_ratio(delta_pidl, delta_fem),
                "FEM_projected_over_PIDL": safe_ratio(delta_fem, delta_pidl),
                "fem_E_d_abs": fem_ed,
                "pidl_E_d_abs": pidl_ed,
                "abs_E_d_PIDL_over_FEM": safe_ratio(pidl_ed, fem_ed),
            }
        )

    full = pd.concat([pd.DataFrame(rows), pd.DataFrame(energy_rows)], ignore_index=True)
    compact = pd.concat([compact, pd.DataFrame(energy_rows)], ignore_index=True)
    return full, compact


def plot_compact(compact: pd.DataFrame, out_path: Path) -> None:
    selected = [
        ("alpha_bar", "tip_2l0_mean", "alpha_bar tip2"),
        ("alpha_bar", "p99", "alpha_bar p99"),
        ("delta_alpha_bar", "tip_2l0_mean", "Delta alpha_bar tip2"),
        ("psi_raw", "tip_2l0_mean", "psi_raw tip2"),
        ("g_alpha", "tip_2l0_mean", "g(alpha) tip2"),
        ("psi_active", "tip_2l0_mean", "psi_active tip2"),
        ("Delta_E_d", "from_c1", "Delta E_d"),
    ]
    fig, axes = plt.subplots(2, 4, figsize=(14.2, 7.1), constrained_layout=True)
    for ax, (field, metric, title) in zip(axes.ravel(), selected):
        sub = compact[(compact["field"] == field) & (compact["metric"] == metric)].sort_values("cycle")
        ax.plot(sub["cycle"], sub["PIDL_over_FEM_projected"], marker="o", lw=1.5, color="#0072B2")
        ax.axhline(1.0, color="0.45", ls="--", lw=1.0)
        ax.set_title(title)
        ax.set_xlabel("cycle")
        ax.set_ylabel("PIDL / FEM n_step2")
        ax.grid(alpha=0.25)
        if field in {"psi_active", "Delta_E_d", "delta_alpha_bar"}:
            ax.set_yscale("symlog", linthresh=0.05)
    axes.ravel()[-1].axis("off")
    fig.suptitle("Strict FEM-mesh PIDL vs FEM Request21 n_step=2 [1,0]")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def write_note(compact: pd.DataFrame, out_path: Path) -> None:
    def value(field: str, metric: str, cycle: int) -> float:
        sub = compact[
            (compact["field"] == field)
            & (compact["metric"] == metric)
            & (compact["cycle"] == cycle)
        ]
        if sub.empty:
            return float("nan")
        return float(sub["PIDL_over_FEM_projected"].iloc[0])

    lines = [
        "# PIDL vs FEM n_step=2 Timing Audit",
        "",
        "Reference: FEM Request21 `n_step=2`, retained load factors `[1, 0]`, `N_f=70`.",
        "PIDL mapping: FEM cycle `c` compared with PIDL saved checkpoint `j=c-1`.",
        "",
        "## Key Ratios",
        "",
        "| cycle | alpha_bar tip2 | Delta alpha_bar tip2 | psi_raw tip2 | g(alpha) tip2 | psi_active tip2 | Delta E_d |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for cycle in CYCLES:
        lines.append(
            f"| {cycle} | "
            f"{value('alpha_bar', 'tip_2l0_mean', cycle):.4g} | "
            f"{value('delta_alpha_bar', 'tip_2l0_mean', cycle):.4g} | "
            f"{value('psi_raw', 'tip_2l0_mean', cycle):.4g} | "
            f"{value('g_alpha', 'tip_2l0_mean', cycle):.4g} | "
            f"{value('psi_active', 'tip_2l0_mean', cycle):.4g} | "
            f"{value('Delta_E_d', 'from_c1', cycle):.4g} |"
        )
    lines += [
        "",
        "## Reading",
        "",
        "PIDL is intended as a cyclic 0-to-peak update where unload does not add positive `Delta psi`; it is therefore conceptually closer to FEM `[1,0]` than to FEM peak-only `[1]`, but it still does not solve a separate unloaded equilibrium field.",
        "",
        "This table should be read as a mechanism audit, not as a new fracture-cycle claim. `Delta E_d` is undefined at c1 because both references are zeroed at c1; later rows measure the incremental dissipated-energy growth relative to the same c1 convention.",
        "",
        "Generated files:",
        "",
        f"- `{OUT_DIR / 'pidl_vs_fem_nstep2_cadence_mechanism_full.csv'}`",
        f"- `{OUT_DIR / 'pidl_vs_fem_nstep2_cadence_mechanism_compact.csv'}`",
        f"- `{OUT_DIR / 'pidl_vs_fem_nstep2_cadence_mechanism_ratios.png'}`",
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    full, compact = compute_rows()
    full_path = OUT_DIR / "pidl_vs_fem_nstep2_cadence_mechanism_full.csv"
    compact_path = OUT_DIR / "pidl_vs_fem_nstep2_cadence_mechanism_compact.csv"
    fig_path = OUT_DIR / "pidl_vs_fem_nstep2_cadence_mechanism_ratios.png"
    note_path = EXPERIMENT / "1_analysis" / "pidl_vs_fem_nstep2_cadence_mechanism.md"

    full.to_csv(full_path, index=False)
    compact.to_csv(compact_path, index=False)
    plot_compact(compact, fig_path)
    write_note(compact, note_path)

    show = compact[
        (compact["field"].isin(["alpha_bar", "delta_alpha_bar", "psi_raw", "g_alpha", "psi_active", "Delta_E_d"]))
        & (compact["metric"].isin(["tip_2l0_mean", "from_c1"]))
    ].copy()
    print(show[["cycle", "field", "metric", "PIDL_over_FEM_projected"]].to_string(index=False))
    print(f"wrote {full_path}")
    print(f"wrote {compact_path}")
    print(f"wrote {fig_path}")
    print(f"wrote {note_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
