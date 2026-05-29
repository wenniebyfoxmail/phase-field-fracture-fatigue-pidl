#!/usr/bin/env python3
"""Summarize soft-hist0 FEM/PIDL alignment diagnostics.

The audit is intentionally scalar and conservative.  It combines the FEM
one-factor checks with Taobo PIDL alignment runs, then records which comparisons
are cycle-aligned and which are only cycle-like until a PIDL state-timing export
exists.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_ANALYSIS_DIR = ROOT / "_analysis_fem_mechanism_20260528"
DEFAULT_TAOBO_DIR = DEFAULT_ANALYSIS_DIR / "taobo_alignment_diag_20260529"
DEFAULT_OUT = DEFAULT_ANALYSIS_DIR / "soft_hist0_alignment_audit_summary_20260529.csv"
DEFAULT_FIG = DEFAULT_ANALYSIS_DIR / "figures" / "soft_hist0_alignment_audit_scalars_20260529.png"

ONEDRIVE = Path(
    "/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result"
)
FEM_CASES = {
    "FEM soft-hist0": {
        "csv": ONEDRIVE
        / "_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28"
        / "reverseBC_u12_diffuse_precrack_soft_hist0_cyclewise_mechanism_metrics.csv",
        "nf": 69,
        "status": "penetrated",
    },
    "FEM tol_irrev=5e-3": {
        "csv": ONEDRIVE
        / "_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_tolir5e3_2026-05-29"
        / "reverseBC_u12_diffuse_precrack_soft_hist0_tolir5e3_cyclewise_mechanism_metrics.csv",
        "nf": 68,
        "status": "penetrated",
    },
    "FEM peak-only": {
        "csv": ONEDRIVE
        / "_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_peakonly_2026-05-29"
        / "reverseBC_u12_diffuse_precrack_soft_hist0_peakonly_cyclewise_mechanism_metrics.csv",
        "nf": np.nan,
        "status": "no penetration by c120",
    },
    "FEM res_stiff=0": {
        "csv": ONEDRIVE
        / "_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_resstiff0_2026-05-29"
        / "reverseBC_u12_diffuse_precrack_soft_hist0_resstiff0_cyclewise_mechanism_metrics.csv",
        "nf": 69,
        "status": "penetrated",
    },
}

PIDL_CASES = {
    "PIDL tol_ir=1e-3": {
        "dir": "tolir1e3",
        "log": "tolir1e3_u012_N100_seed1.log",
        "x_mode": "index_plus_one",
        "status": "confirmed",
    },
    "PIDL explicit substeps": {
        "dir": "explicit_cycle",
        "log": "explicit_cycle_u012_Nphys40_seed1.log",
        "x_mode": "substep_div_5",
        "status": "no fracture by 40 physical cycles",
    },
    "PIDL FEM-mesh": {
        "dir": "femmesh_softHist0",
        "log": "femmesh_softHist0_u012_N100_seed1_retry.log",
        "x_mode": "index_plus_one",
        "status": "confirmed",
    },
}


def safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def parse_fracture_log(path: Path) -> tuple[float, float]:
    if not path.is_file():
        return float("nan"), float("nan")
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(
        r"Fracture confirmed\] Stopping at cycle\s+(\d+)\. First detected at cycle\s+(\d+)",
        text,
    )
    if not match:
        return float("nan"), float("nan")
    return float(match.group(2)), float(match.group(1))


def load_pidl_case(base: Path, name: str, meta: dict[str, str]) -> tuple[pd.DataFrame, dict[str, float]]:
    run_dir = base / meta["dir"] / "best_models"
    eel = np.load(run_dir / "E_el_vs_cycle.npy")
    ab = np.load(run_dir / "alpha_bar_vs_cycle.npy")
    kt = np.load(run_dir / "Kt_vs_cycle.npy") if (run_dir / "Kt_vs_cycle.npy").is_file() else np.full(len(eel), np.nan)
    x_tip = np.load(run_dir / "x_tip_vs_cycle.npy") if (run_dir / "x_tip_vs_cycle.npy").is_file() else np.full(len(eel), np.nan)

    idx = np.arange(len(eel), dtype=float)
    if meta["x_mode"] == "substep_div_5":
        x = idx / 5.0
        index_note = "explicit substep index divided by 5; not a FEM-cycle equivalent until timing is audited"
    else:
        x = idx + 1.0
        index_note = "PIDL saved index j plotted as j+1; exact c1 timing still requires PIDL state export"

    df = pd.DataFrame(
        {
            "case": name,
            "family": "PIDL",
            "cycle_like_index": x,
            "stored_index": idx,
            "E_el": eel,
            "alpha_bar_max": ab[:, 0],
            "alpha_bar_mean": ab[:, 1],
            "f_min": ab[:, 2],
            "Kt": kt[: len(eel)],
            "x_tip": x_tip[: len(eel)],
        }
    )
    first_detected, confirmed = parse_fracture_log(base / "logs" / meta["log"])
    summary = {
        "case": name,
        "family": "PIDL",
        "status": meta["status"],
        "first_detected": first_detected,
        "confirmed_or_nf": confirmed,
        "last_cycle_like_index": float(df["cycle_like_index"].iloc[-1]),
        "last_E_el": float(df["E_el"].iloc[-1]),
        "last_alpha_bar_max": float(df["alpha_bar_max"].iloc[-1]),
        "last_alpha_bar_mean": float(df["alpha_bar_mean"].iloc[-1]),
        "last_f_min": float(df["f_min"].iloc[-1]),
        "last_Kt": float(df["Kt"].iloc[-1]) if np.isfinite(df["Kt"].iloc[-1]) else float("nan"),
        "last_x_tip": float(df["x_tip"].iloc[-1]),
        "rows": float(len(df)),
        "index_note": index_note,
    }
    return df, summary


def load_fem_case(name: str, meta: dict[str, object]) -> tuple[pd.DataFrame, dict[str, float]]:
    csv_path = Path(meta["csv"])
    df0 = pd.read_csv(csv_path)
    df = pd.DataFrame(
        {
            "case": name,
            "family": "FEM",
            "cycle_like_index": df0["cycle"].astype(float),
            "stored_index": df0["cycle"].astype(float),
            "E_el": df0["E_el"].astype(float),
            "alpha_bar_max": df0["alpha_bar_elem_max"].astype(float),
            "alpha_bar_mean": df0["alpha_bar_elem_mean"].astype(float),
            "f_min": df0["f_fatigue_min"].astype(float),
            "Kt": df0["Kt_proxy"].astype(float),
            "x_tip": df0["x_tip_d095"].astype(float),
        }
    )
    last = df.iloc[-1]
    summary = {
        "case": name,
        "family": "FEM",
        "status": str(meta["status"]),
        "first_detected": float("nan"),
        "confirmed_or_nf": safe_float(meta["nf"]),
        "last_cycle_like_index": float(last["cycle_like_index"]),
        "last_E_el": float(last["E_el"]),
        "last_alpha_bar_max": float(last["alpha_bar_max"]),
        "last_alpha_bar_mean": float(last["alpha_bar_mean"]),
        "last_f_min": float(last["f_min"]),
        "last_Kt": float(last["Kt"]),
        "last_x_tip": float(last["x_tip"]),
        "rows": float(len(df)),
        "index_note": "FEM exported cycle number",
    }
    return df, summary


def selected_ratios(analysis_dir: Path) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    inc_path = analysis_dir / "femmesh_pidl_vs_soft_hist0_incremental_energy_c1_ref.csv"
    probe_path = analysis_dir / "femmesh_pidl_vs_soft_hist0_fem_probe_c1_c69.csv"
    if inc_path.is_file():
        inc = pd.read_csv(inc_path)
        row = inc.loc[inc["cycle"] == 69]
        if not row.empty:
            r = row.iloc[0]
            out.append(
                {
                    "case": "FEM-mesh PIDL vs soft-hist0 FEM",
                    "family": "comparison",
                    "status": "cycle c69 selected ratio",
                    "first_detected": np.nan,
                    "confirmed_or_nf": np.nan,
                    "last_cycle_like_index": 69.0,
                    "last_E_el": np.nan,
                    "last_alpha_bar_max": np.nan,
                    "last_alpha_bar_mean": np.nan,
                    "last_f_min": np.nan,
                    "last_Kt": np.nan,
                    "last_x_tip": np.nan,
                    "rows": float(len(inc)),
                    "index_note": (
                        "At c69, Delta E_d PIDL/FEM="
                        f"{safe_float(r['ratio_delta_E_d_pidl_over_fem']):.3f}; "
                        "absolute-vs-incremental energy must stay separated"
                    ),
                }
            )
    if probe_path.is_file():
        probe = pd.read_csv(probe_path)
        keep = probe[
            (probe["cycle"] == 69)
            & (probe["field"].isin(["alpha_bar", "psi_plus_active", "damage_alpha"]))
            & (probe["metric"].isin(["max", "p99", "tip_2l0_mean"]))
        ]
        for _, r in keep.iterrows():
            ratio = safe_float(r.get("PIDL_over_FEM_projected", np.nan))
            out.append(
                {
                    "case": f"probe c69 {r['field']} {r['metric']}",
                    "family": "comparison",
                    "status": "common-probe PIDL/FEM ratio",
                    "first_detected": np.nan,
                    "confirmed_or_nf": np.nan,
                    "last_cycle_like_index": 69.0,
                    "last_E_el": np.nan,
                    "last_alpha_bar_max": ratio,
                    "last_alpha_bar_mean": np.nan,
                    "last_f_min": np.nan,
                    "last_Kt": np.nan,
                    "last_x_tip": np.nan,
                    "rows": float(len(probe)),
                    "index_note": f"PIDL/FEM={ratio:.3f}; value column reused for ratio",
                }
            )
    return out


def plot_scalars(series: pd.DataFrame, fig_path: Path) -> None:
    palette = {
        "FEM soft-hist0": "#0072B2",
        "FEM tol_irrev=5e-3": "#56B4E9",
        "FEM peak-only": "#009E73",
        "FEM res_stiff=0": "#E69F00",
        "PIDL tol_ir=1e-3": "#D55E00",
        "PIDL explicit substeps": "#CC79A7",
        "PIDL FEM-mesh": "#000000",
    }
    linestyles = {"FEM": "-", "PIDL": "--"}
    panels = [
        ("E_el", "elastic energy"),
        ("alpha_bar_max", "history max"),
        ("f_min", "fatigue degradation min"),
        ("Kt", "Kt proxy"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 7.2), constrained_layout=True)
    for ax, (col, title) in zip(axes.flat, panels):
        for case, g in series.groupby("case", sort=False):
            if case not in palette:
                continue
            y = g[col].to_numpy(dtype=float)
            if np.all(~np.isfinite(y)):
                continue
            ax.plot(
                g["cycle_like_index"],
                y,
                lw=1.45,
                color=palette[case],
                ls=linestyles.get(str(g["family"].iloc[0]), "-"),
                label=case,
            )
        ax.set_title(title)
        ax.set_xlabel("cycle-like index")
        ax.grid(True, color="0.86", lw=0.7)
    axes[1, 1].legend(frameon=False, fontsize=7, ncol=1, loc="best")
    fig.suptitle("Soft-hist0 alignment diagnostics: scalar trajectories")
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=220)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    parser.add_argument("--taobo-dir", type=Path, default=DEFAULT_TAOBO_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--fig", type=Path, default=DEFAULT_FIG)
    args = parser.parse_args()

    series_frames: list[pd.DataFrame] = []
    summary_rows: list[dict[str, object]] = []
    for name, meta in FEM_CASES.items():
        df, row = load_fem_case(name, meta)
        series_frames.append(df)
        summary_rows.append(row)
    for name, meta in PIDL_CASES.items():
        df, row = load_pidl_case(args.taobo_dir, name, meta)
        series_frames.append(df)
        summary_rows.append(row)
    summary_rows.extend(selected_ratios(args.analysis_dir))

    series = pd.concat(series_frames, ignore_index=True)
    summary = pd.DataFrame(summary_rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.out, index=False)
    plot_scalars(series, args.fig)

    print(summary[["case", "family", "status", "confirmed_or_nf", "last_cycle_like_index", "last_alpha_bar_max", "last_f_min", "last_Kt"]].to_string(index=False))
    print(f"Wrote {args.out}")
    print(f"Wrote {args.fig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
