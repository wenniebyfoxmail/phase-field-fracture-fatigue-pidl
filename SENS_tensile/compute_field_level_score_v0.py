#!/usr/bin/env python3
"""Field-level FEM/PIDL comparison score, v0.

This script scores the field-comparison artifacts that already exist in the
repo. It deliberately separates strict same-probe metrics from weaker summary
metrics so that a montage-derived impression cannot masquerade as a FEM/PIDL
field proof.

Inputs used by default:
  - alignment_mesh_probe_u012_baseline.csv
  - alignment_mesh_probe_u012_reverseBC.csv
  - alignment_mesh_probe_u012_femAnchorBC.csv
  - alignment_compare_baseline_vs_femAnchorBC.csv
  - docs/figures/adaptive_sampling/.../field_level_compare_v4_baseline_fem.csv
  - docs/figures/tiplocal_exp18_20260528/finished_runs_field_energy_summary.csv

Outputs:
  - SENS_tensile/field_level_score_v0_details.csv
  - SENS_tensile/field_level_score_v0_summary.csv
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SENS = ROOT / "SENS_tensile"
EPS = 1e-12
L0 = 0.01

STRICT_CYCLES = {40, 70, 82}
STRICT_FIELDS = {"damage_alpha", "psi_plus", "alpha_bar", "fatigue_f"}
STRICT_METRICS = {
    "max",
    "p99",
    "top1_mean",
    "tip_l0_mean",
    "tip_2l0_mean",
    "crack_strip_mean",
    "right_band_mean",
}


def finite_positive(x) -> bool:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v) and v > EPS


def abs_log_ratio(pidl, fem) -> float:
    if not finite_positive(pidl) or not finite_positive(fem):
        return float("nan")
    return abs(math.log(float(pidl) / float(fem)))


def add_detail(rows, method, evidence, component, field, metric, cycle, value, note=""):
    if math.isfinite(value):
        rows.append({
            "method": method,
            "evidence": evidence,
            "component": component,
            "field": field,
            "metric": metric,
            "cycle": cycle,
            "score": value,
            "note": note,
        })


def score_mesh_probe(path: Path, method: str, rows: list[dict]):
    if not path.is_file():
        return
    df = pd.read_csv(path)
    df = df[df["cycle"].isin(STRICT_CYCLES)]
    df = df[df["field"].isin(STRICT_FIELDS)]
    df = df[df["metric"].isin(STRICT_METRICS)]
    for _, r in df.iterrows():
        component = "strict_probe"
        field = str(r["field"])
        metric = str(r["metric"])
        if field == "psi_plus" and "tip" in metric:
            component = "strict_tip_driver"
        elif "right_band" in metric:
            component = "strict_boundary_band"
        elif field in {"damage_alpha", "alpha_bar"}:
            component = "strict_damage_history"
        score = abs_log_ratio(r["PIDL_native"], r["FEM_projected_to_PIDL"])
        add_detail(
            rows, method, "same_probe_projected_FEM_to_PIDL",
            component, field, metric, int(r["cycle"]), score,
        )


def score_direct_compare(path: Path, rows: list[dict]):
    """Score the compact baseline-vs-femAnchorBC comparison table."""
    if not path.is_file():
        return
    df = pd.read_csv(path)

    mesh = df[df["audit"] == "mesh_probe"].copy()
    for method, col in [("baseline", "baseline_ratio"), ("femAnchorBC", "femAnchor_ratio")]:
        for _, r in mesh.iterrows():
            field_metric = str(r["field_metric"])
            field, _, metric = field_metric.partition(":")
            component = "compact_probe"
            if field == "psi_plus" and "tip" in metric:
                component = "compact_tip_driver"
            elif "right_band" in metric:
                component = "compact_boundary_band"
            score = abs(math.log(float(r[col]))) if finite_positive(r[col]) else float("nan")
            add_detail(rows, method, "same_probe_compact", component, field, metric, int(r["cycle"]), score)

    reaction = df[df["audit"] == "reaction"].copy()
    for method, col in [("baseline", "baseline_ratio"), ("femAnchorBC", "femAnchor_ratio")]:
        for _, r in reaction.iterrows():
            score = abs(math.log(float(r[col]))) if finite_positive(r[col]) else float("nan")
            add_detail(
                rows, method, "energy_reaction_proxy",
                "reaction_guardrail", "reaction", str(r["field_metric"]),
                int(r["cycle"]), score,
                note="large late-cycle values can be amplified by near-zero FEM reaction",
            )

    v7 = df[df["audit"] == "v7_global"].copy()
    for method, col in [("baseline", "baseline_PIDL"), ("femAnchorBC", "femAnchor_PIDL")]:
        for _, r in v7.iterrows():
            val = float(r[col])
            if not math.isfinite(val):
                continue
            add_detail(
                rows, method, "boundary_residual_raw",
                "v7_guardrail", "v7", str(r["field_metric"]),
                int(r["cycle"]), val,
                note="raw residual; lower is better, not a log-ratio to FEM",
            )


def score_adaptive_summary(path: Path, rows: list[dict]):
    if not path.is_file():
        return
    df = pd.read_csv(path)
    fem = df[df["kind"] == "FEM"].iloc[0]
    pidl_rows = df[df["kind"].isin(["PIDL", "PIDL-v4"])]
    metric_map = {
        "alpha_bar_max": "summary_history",
        "alpha_bar_mean_area": "summary_history",
        "f_min": "summary_fatigue",
        "f_mean_area": "summary_fatigue",
        "d_max": "summary_damage",
        "d_mean_area": "summary_damage",
        "area_alpha_bar_gt_0p5": "summary_morphology",
        "area_d_gt_0p5": "summary_morphology",
        "area_d_gt_0p9": "summary_morphology",
    }
    for _, r in pidl_rows.iterrows():
        method = str(r["source"])
        for metric, component in metric_map.items():
            score = abs_log_ratio(r.get(metric), fem.get(metric))
            add_detail(
                rows, method, "native_summary_vs_FEM_summary",
                component, metric.split("_")[0], metric, int(r["snapshot_cycle"]), score,
                note="not same-probe; useful as summary-level field audit",
            )
        for metric in ["x_tip_d_gt_0p5", "x_tip_d_gt_0p9"]:
            if pd.notna(r.get(metric)) and pd.notna(fem.get(metric)):
                score = abs(float(r[metric]) - float(fem[metric])) / L0
                add_detail(
                    rows, method, "native_summary_vs_FEM_summary",
                    "summary_morphology", "damage", metric, int(r["snapshot_cycle"]), score,
                    note="x-tip distance normalized by l0",
                )


def score_exp18_summary(path: Path, adaptive_path: Path, rows: list[dict]):
    if not path.is_file() or not adaptive_path.is_file():
        return
    exp = pd.read_csv(path)
    fem = pd.read_csv(adaptive_path)
    fem = fem[fem["kind"] == "FEM"].iloc[0]

    reps = {
        "mlp_s1_alpha",
        "mlp_s2_all",
        "fourier_s2_all",
        "siren_s2_all_adapthist_wr010",
    }
    exp = exp[exp["run"].isin(reps)].copy()
    mapping = [
        ("alpha_snapshot_max", "d_max", "partial_damage"),
        ("alpha_snapshot_mean", "d_mean_unweighted", "partial_damage"),
        ("frac_alpha_gt_0p5", "area_d_gt_0p5", "partial_morphology"),
        ("frac_alpha_gt_0p9", "area_d_gt_0p9", "partial_morphology"),
        ("alpha_bar_max_final", "alpha_bar_max", "partial_history"),
        ("alpha_bar_mean_final", "alpha_bar_mean_unweighted", "partial_history"),
        ("f_min_or_f_slot_final", "f_min", "partial_fatigue"),
    ]
    for _, r in exp.iterrows():
        method = "Exp18 " + str(r["run"])
        cycle = int(r["snapshot_cycle"])
        for pidl_col, fem_col, component in mapping:
            fem_val = fem.get(fem_col)
            if fem_col.startswith("area_"):
                fem_val = float(fem_val) / float(fem["area_total"])
            score = abs_log_ratio(r.get(pidl_col), fem_val)
            add_detail(
                rows, method, "exp18_summary_partial",
                component, pidl_col.split("_")[0], f"{pidl_col}_vs_{fem_col}",
                cycle, score,
                note="partial only: Exp18 artifact is not projected to the FEM/PIDL common probes",
            )
        if pd.notna(r.get("x_tip_alpha_gt_0p5")) and pd.notna(fem.get("x_tip_d_gt_0p5")):
            score = abs(float(r["x_tip_alpha_gt_0p5"]) - float(fem["x_tip_d_gt_0p5"])) / L0
            add_detail(
                rows, method, "exp18_summary_partial",
                "partial_morphology", "damage", "x_tip_alpha_gt_0p5_vs_FEM",
                cycle, score,
                note="partial only; x-tip distance normalized by l0",
            )


def summarize(details: pd.DataFrame) -> pd.DataFrame:
    if details.empty:
        return pd.DataFrame()
    grouped = (
        details
        .groupby(["method", "evidence", "component"], dropna=False)
        .agg(
            n_metrics=("score", "count"),
            score_mean=("score", "mean"),
            score_median=("score", "median"),
            score_max=("score", "max"),
        )
        .reset_index()
    )

    strict_components = {
        "strict_probe", "strict_tip_driver", "strict_boundary_band",
        "strict_damage_history", "compact_probe", "compact_tip_driver",
        "compact_boundary_band",
    }
    rollup_rows = []
    for method, sub in details.groupby("method"):
        strict = sub[sub["component"].isin(strict_components)]
        summary = sub[sub["component"].str.startswith(("summary_", "partial_"), na=False)]
        guard = sub[sub["component"].str.endswith("_guardrail", na=False)]
        if not strict.empty:
            rollup_rows.append({
                "method": method, "evidence": "ROLLUP", "component": "strict_available_mean",
                "n_metrics": len(strict), "score_mean": strict["score"].mean(),
                "score_median": strict["score"].median(), "score_max": strict["score"].max(),
            })
        if not summary.empty:
            rollup_rows.append({
                "method": method, "evidence": "ROLLUP", "component": "summary_or_partial_mean",
                "n_metrics": len(summary), "score_mean": summary["score"].mean(),
                "score_median": summary["score"].median(), "score_max": summary["score"].max(),
            })
        if not guard.empty:
            rollup_rows.append({
                "method": method, "evidence": "ROLLUP", "component": "guardrail_raw_or_log_mean",
                "n_metrics": len(guard), "score_mean": guard["score"].mean(),
                "score_median": guard["score"].median(), "score_max": guard["score"].max(),
            })
    if rollup_rows:
        grouped = pd.concat([grouped, pd.DataFrame(rollup_rows)], ignore_index=True)
    return grouped.sort_values(["component", "score_mean", "method"], na_position="last")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-details", type=Path, default=SENS / "field_level_score_v0_details.csv")
    ap.add_argument("--out-summary", type=Path, default=SENS / "field_level_score_v0_summary.csv")
    args = ap.parse_args()

    rows: list[dict] = []
    score_mesh_probe(SENS / "alignment_mesh_probe_u012_baseline.csv", "baseline", rows)
    score_mesh_probe(SENS / "alignment_mesh_probe_u012_reverseBC.csv", "baseline_vs_reverseBC", rows)
    score_mesh_probe(SENS / "alignment_mesh_probe_u012_femAnchorBC.csv", "femAnchorBC", rows)
    score_direct_compare(SENS / "alignment_compare_baseline_vs_femAnchorBC.csv", rows)

    adaptive = ROOT / "docs/figures/adaptive_sampling/field_compare_v4_baseline_fem/field_level_compare_v4_baseline_fem.csv"
    score_adaptive_summary(adaptive, rows)

    exp18 = ROOT / "docs/figures/tiplocal_exp18_20260528/finished_runs_field_energy_summary.csv"
    score_exp18_summary(exp18, adaptive, rows)

    details = pd.DataFrame(rows)
    summary = summarize(details)
    args.out_details.parent.mkdir(parents=True, exist_ok=True)
    details.to_csv(args.out_details, index=False)
    summary.to_csv(args.out_summary, index=False)

    print(f"saved {args.out_details}")
    print(f"saved {args.out_summary}")
    if not summary.empty:
        rollup = summary[summary["evidence"] == "ROLLUP"]
        print("\nROLLUP")
        print(rollup.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
