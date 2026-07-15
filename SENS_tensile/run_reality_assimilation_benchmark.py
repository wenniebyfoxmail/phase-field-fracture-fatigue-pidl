#!/usr/bin/env python3
"""Run the first reality-facing sequential-assimilation benchmark.

This is an analysis-only FEM-library benchmark.  It does not enter the PIDL
training loop and is therefore safe to run on Mac-PIDL.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from reality_assimilation import (
    DEFAULT_SYNTHETIC_SENSOR_MODEL,
    OBSERVATION_TIERS,
    SensorObservationModel,
    feature_catalog_frame,
    run_leave_one_trajectory_out,
    summarize_parameter_predictions,
    trajectory_from_handoff,
    trajectories_from_manifest,
    validate_physics_library,
)
from run_m2s_next_stage_feasibility import DEFAULT_FIELD_ROOT, discover_field_handoffs
from observable_growth_baseline import (
    run_observable_growth_leave_one_out,
    summarize_observable_growth_stages,
)
from validate_reality_assimilation_package import validate_package


DEFAULT_OUT_DIR = Path(__file__).resolve().parents[1] / "_analysis_reality_assimilation_20260715"


def infer_id(path: Path) -> str:
    match = re.search(r"nstep(\d+)", str(path))
    return f"strict_u12_nstep{int(match.group(1)):02d}" if match else path.stem


def plot_summary(summary: pd.DataFrame, out_dir: Path) -> None:
    agg = summary[summary["heldout_trajectory"] == "ALL"].copy()
    if agg.empty:
        return
    fig, axes = plt.subplots(1, 3, figsize=(12.2, 3.8))
    x = range(len(agg))
    labels = agg["tier"].str.replace("_", "\n").tolist()
    axes[0].bar(x, agg["rul_mae"], color="#0072B2")
    axes[0].set_ylabel("RUL MAE (cycles)")
    axes[1].bar(x, agg["rul_90_coverage"], color="#009E73")
    axes[1].axhline(0.9, color="0.3", ls="--", lw=1.0)
    axes[1].set_ylabel("90% interval coverage")
    axes[1].set_ylim(0.0, 1.05)
    axes[2].bar(x, agg["future_tip_mae"], color="#D55E00")
    axes[2].set_ylabel("Future crack-tip MAE")
    for ax in axes:
        ax.set_xticks(list(x), labels, fontsize=7)
        ax.grid(axis="y", color="0.9", lw=0.6)
    fig.suptitle("Reality-facing FEM-library assimilation: sensor-tier ablation", fontsize=11)
    fig.tight_layout()
    fig.savefig(out_dir / "reality_assimilation_sensor_ablation.png", dpi=220)
    fig.savefig(out_dir / "reality_assimilation_sensor_ablation.pdf")
    plt.close(fig)


def write_decision(
    path: Path,
    *,
    summary: pd.DataFrame,
    field_paths: list[Path],
    trajectories,
    transition_comparison: pd.DataFrame,
    growth_stage_summary: pd.DataFrame,
    args: argparse.Namespace,
) -> None:
    agg = summary[summary["heldout_trajectory"] == "ALL"].copy()
    best = agg.sort_values(["rul_crps", "rul_mae"]).iloc[0]
    deployable = agg[~agg["tier"].eq("oracle_hidden_state")]
    best_deployable = deployable.sort_values(["rul_crps", "rul_mae"]).iloc[0]
    n_umax = len({t.umax for t in trajectories})
    physics_families = sorted({t.physics_family for t in trajectories})
    mixed_physics = len(physics_families) != 1
    nf_values = [int(t.failure_cycle) for t in trajectories if not t.censored]
    n_censored = sum(t.censored for t in trajectories)
    too_easy = (
        mixed_physics
        or n_umax < 2
        or len(nf_values) < 3
        or (max(nf_values) - min(nf_values) <= 2)
    )

    lines = [
        "# Reality-Facing Assimilation Decision",
        "",
        "## Gate status",
        "",
        "This package is an analysis-only framework-validation asset. It launches no PIDL/FEM training.",
        "",
        "1. **Mechanism question**: which reality-facing observation tier first makes future crack geometry and RUL probabilistically identifiable?",
        "2. **Claim change**: success promotes a sensor tier into the laboratory validation design; failure shows which additional modality is required.",
        "3. **Cheaper diagnostic**: leave-one-FEM-trajectory-out library assimilation on existing exports, completed here before any producer run.",
        "4. **Minimal asset**: posterior prediction table, sensor-ablation summary, inverse-parameter summary, observability catalog, and this decision note.",
        "5. **Registry path**: `docs/reality_assimilation_framework_2026-07-15.md` and the M2S branch of `docs/research_frontier.md`.",
        "",
        "## Implemented closed loop",
        "",
        "At every synthetic inspection, permitted observations update posterior weights over the held-out FEM library. The posterior is propagated to remaining life, declared FEM/model parameters, and the crack-tip position at the requested forecast horizon. Hidden `alpha_bar`, fatigue degradation, and active driver are excluded from deployable tiers and appear only in an oracle ceiling.",
        "",
        "## Aggregate results",
        "",
        "| tier | RUL MAE | CRPS | 90% coverage | interval width | future-tip MAE |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in agg.iterrows():
        lines.append(
            f"| `{row['tier']}` | {row['rul_mae']:.3g} | {row['rul_crps']:.3g} | "
            f"{row['rul_90_coverage']:.3f} | {row['rul_90_width']:.3g} | {row['future_tip_mae']:.3g} |"
        )
    if not transition_comparison.empty:
        lines.extend(
            [
                "",
                "## Same-observation transition baseline",
                "",
                "Both rows below use only registered `crack_tip_x_d09`; the observation-only model receives no FEM hidden state or extra vision geometry.",
                "",
                "| transition model | RUL MAE | CRPS | 90% coverage | future-tip MAE |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for _, row in transition_comparison.iterrows():
            lines.append(
                f"| `{row['transition_model']}` | {row['rul_mae']:.3g} | {row['rul_crps']:.3g} | "
                f"{row['rul_90_coverage']:.3f} | {row['future_tip_mae']:.3g} |"
            )
    if not growth_stage_summary.empty:
        lines.extend(
            [
                "",
                "### Observation-only stage split",
                "",
                "| visible crack stage | updates | RUL MAE | CRPS | 90% coverage | future-tip MAE |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for _, row in growth_stage_summary.iterrows():
            lines.append(
                f"| `{row['observation_stage']}` | {row['n_updates']:.0f} | {row['rul_mae']:.3g} | "
                f"{row['rul_crps']:.3g} | {row['rul_90_coverage']:.3f} | {row['future_tip_mae']:.3g} |"
            )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- Best deployable synthetic tier by CRPS: `{best_deployable['tier']}`.",
            f"- Overall best tier, including oracle: `{best['tier']}`.",
            f"- Current library: {len(field_paths)} trajectories ({n_censored} right-censored), Umax diversity={n_umax}, observed failure cycles={min(nf_values)}..{max(nf_values)}.",
            f"- Physics family: {', '.join(f'`{family}`' for family in physics_families)}.",
        ]
    )
    if too_easy and not mixed_physics:
        lines.append(
            "- **Do not promote a scientific sensor claim from these scores.** The current strict field library is nearly one trajectory repeated at different numerical cadence, so this run validates code and output semantics, not real observability."
        )
    if mixed_physics:
        lines.append(
            "- **Quarantine:** trajectories cross physics families, so load/material inference is confounded by incompatible solver/BC/constitutive semantics even when the command was explicitly allowed as a tooling stress test."
        )
    lines.extend(
        [
            "",
            "## Next evidence required",
            "",
            "1. Export strict full-field FEM trajectories varying physical load spectrum, material/fatigue parameters, initial crack/precrack severity, and environment proxy; numerical cadence alone is not trajectory diversity.",
            "2. Replace `mechanical_energy_*_proxy` with an explicit observation model for DIC/sparse strain and replace `ae_*_proxy` with an AE likelihood calibrated from a fatigue experiment.",
            "3. Feed registered crack-probability masks through the locked CV observation operator, then test segmentation/registration uncertainty rather than phase-field-label agreement.",
            "4. Run the same locked leave-one-trajectory-out protocol, then design the smallest laboratory fatigue test only for the first sensor tier that improves CRPS and calibrated coverage.",
            "",
            "## Run configuration",
            "",
            f"- Inspection stride: {args.inspection_stride} cycles",
            f"- Forecast horizon: {args.forecast_horizon} cycles",
            f"- Likelihood sigma: {args.likelihood_sigma} robust feature scales",
            f"- Right-censor exponential tail scale: {args.censor_tail_scale} cycles",
            f"- Right-censor quadrature points: {args.censor_quadrature_points}",
            f"- Sensor observation model: `{args.sensor_model_json or 'synthetic_proxy_identity_v1'}`",
            f"- Sensor noise multiplier: {args.sensor_noise_multiplier}",
            f"- Sensor missing probability: {args.sensor_missing_probability}",
            f"- Random seed: {args.random_seed}",
            f"- Observable-growth rate particles: {args.growth_rate_particles}",
            f"- Observable-growth tip sigma: {args.growth_tip_sigma}",
            f"- Observable-growth process relative sigma: {args.growth_process_relative_sigma}",
            f"- Observable-growth forgetting: {args.growth_forgetting}",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--field-root", type=Path, default=DEFAULT_FIELD_ROOT)
    parser.add_argument(
        "--trajectory-manifest",
        type=Path,
        default=None,
        help="Mixed combined/keyframe trajectory library; overrides --field-root.",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--umax", type=float, default=0.12)
    parser.add_argument("--inspection-stride", type=int, default=5)
    parser.add_argument("--forecast-horizon", type=int, default=5)
    parser.add_argument("--likelihood-sigma", type=float, default=0.5)
    parser.add_argument(
        "--tiers",
        default=",".join(OBSERVATION_TIERS),
        help="Comma-separated observation tiers; use tip_only/vision_only for historical observation CSVs.",
    )
    parser.add_argument(
        "--censor-tail-scale",
        type=float,
        default=50.0,
        help="Mean exponential life beyond a right-censor lower bound, in cycles.",
    )
    parser.add_argument("--censor-quadrature-points", type=int, default=11)
    parser.add_argument(
        "--sensor-model-json",
        type=Path,
        default=None,
        help="Versioned DIC/AE observation calibration; default is a declared synthetic identity bridge.",
    )
    parser.add_argument("--sensor-noise-multiplier", type=float, default=0.0)
    parser.add_argument("--sensor-missing-probability", type=float, default=0.0)
    parser.add_argument("--random-seed", type=int, default=0)
    parser.add_argument(
        "--allow-mixed-physics-family",
        action="store_true",
        help="Tooling stress only; mixed-family results are automatically quarantined.",
    )
    parser.add_argument("--growth-rate-particles", type=int, default=101)
    parser.add_argument("--growth-tip-sigma", type=float, default=0.002)
    parser.add_argument("--growth-process-relative-sigma", type=float, default=0.35)
    parser.add_argument("--growth-forgetting", type=float, default=0.5)
    parser.add_argument(
        "--skip-observable-growth-baseline",
        action="store_true",
        help="Skip the crack-tip-only probabilistic data baseline.",
    )
    args = parser.parse_args()
    selected_tiers = tuple(item.strip() for item in args.tiers.split(",") if item.strip())
    unknown_tiers = sorted(set(selected_tiers) - set(OBSERVATION_TIERS))
    if not selected_tiers or unknown_tiers:
        raise ValueError(f"Invalid --tiers selection; unknown={unknown_tiers}")

    sensor_model = (
        SensorObservationModel.from_json(args.sensor_model_json)
        if args.sensor_model_json is not None
        else DEFAULT_SYNTHETIC_SENSOR_MODEL
    )

    if args.trajectory_manifest is not None:
        trajectories = trajectories_from_manifest(args.trajectory_manifest)
        field_paths = [trajectory.source_path for trajectory in trajectories]
    else:
        field_paths = discover_field_handoffs(args.field_root)
        if len(field_paths) < 3:
            raise RuntimeError(f"Need at least three cycle-resolved FEM handoffs in {args.field_root}")
        trajectories = [
            trajectory_from_handoff(
                path,
                trajectory_id=infer_id(path),
                umax=args.umax,
                physics_family="strict_reverseBC_softHist0",
            )
            for path in field_paths
        ]
    if len(trajectories) < 3:
        raise RuntimeError("Reality assimilation benchmark needs at least three trajectories")
    if not any(not trajectory.censored for trajectory in trajectories):
        raise RuntimeError("Benchmark needs at least one uncensored holdout with exact RUL truth")
    try:
        physics_families = list(
            validate_physics_library(
                trajectories,
                allow_mixed=args.allow_mixed_physics_family,
            )
        )
    except ValueError as error:
        raise RuntimeError(
            f"{error}. Use a compatible family or pass --allow-mixed-physics-family "
            "for an automatically quarantined tooling stress test."
        ) from error
    predictions, summary = run_leave_one_trajectory_out(
        trajectories,
        tiers=selected_tiers,
        inspection_stride=args.inspection_stride,
        forecast_horizon=args.forecast_horizon,
        likelihood_sigma=args.likelihood_sigma,
        censor_tail_scale=args.censor_tail_scale,
        censor_quadrature_points=args.censor_quadrature_points,
        sensor_model=sensor_model,
        sensor_noise_multiplier=args.sensor_noise_multiplier,
        sensor_missing_probability=args.sensor_missing_probability,
        random_seed=args.random_seed,
    )
    growth_predictions = pd.DataFrame()
    growth_summary = pd.DataFrame()
    growth_stage_summary = pd.DataFrame()
    if not args.skip_observable_growth_baseline and len(physics_families) == 1:
        growth_predictions, growth_summary = run_observable_growth_leave_one_out(
            trajectories,
            inspection_stride=args.inspection_stride,
            forecast_horizon=args.forecast_horizon,
            rate_particles=args.growth_rate_particles,
            tip_sigma=args.growth_tip_sigma,
            process_relative_sigma=args.growth_process_relative_sigma,
            forgetting=args.growth_forgetting,
        )
        growth_stage_summary = summarize_observable_growth_stages(growth_predictions)

    comparison_rows = []
    direct_tip = summary[
        (summary["heldout_trajectory"] == "ALL") & (summary["tier"] == "tip_only")
    ]
    if not direct_tip.empty:
        comparison_rows.append(
            {
                "transition_model": "direct_fem_library",
                "observation_contract": "crack_tip_x_d09_only",
                **direct_tip.iloc[0][
                    ["rul_mae", "rul_rmse", "rul_crps", "rul_90_coverage", "rul_90_width", "future_tip_mae"]
                ].to_dict(),
            }
        )
    if not growth_summary.empty:
        growth_all = growth_summary[growth_summary["heldout_trajectory"] == "ALL"].iloc[0]
        comparison_rows.append(
            {
                "transition_model": "observable_growth_particles",
                "observation_contract": "crack_tip_x_d09_only",
                **growth_all[
                    ["rul_mae", "rul_rmse", "rul_crps", "rul_90_coverage", "rul_90_width", "future_tip_mae"]
                ].to_dict(),
            }
        )
    transition_comparison = pd.DataFrame(comparison_rows)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(args.out_dir / "reality_assimilation_predictions.csv", index=False)
    summary.to_csv(args.out_dir / "reality_assimilation_summary.csv", index=False)
    if not growth_predictions.empty:
        growth_predictions.to_csv(args.out_dir / "observable_growth_predictions.csv", index=False)
        growth_summary.to_csv(args.out_dir / "observable_growth_summary.csv", index=False)
        growth_stage_summary.to_csv(
            args.out_dir / "observable_growth_stage_summary.csv", index=False
        )
    transition_comparison.to_csv(args.out_dir / "transition_model_comparison.csv", index=False)
    summarize_parameter_predictions(predictions).to_csv(
        args.out_dir / "reality_assimilation_parameter_summary.csv", index=False
    )
    feature_catalog_frame().to_csv(args.out_dir / "sensor_observability_catalog.csv", index=False)
    plot_summary(summary, args.out_dir)
    write_decision(
        args.out_dir / "decision.md",
        summary=summary,
        field_paths=field_paths,
        trajectories=trajectories,
        transition_comparison=transition_comparison,
        growth_stage_summary=growth_stage_summary,
        args=args,
    )
    manifest = {
        "claim_class": "framework-validation",
        "analysis_only": True,
        "training_launched": False,
        "field_paths": [str(path) for path in field_paths],
        "trajectory_manifest": str(args.trajectory_manifest) if args.trajectory_manifest else None,
        "tiers": list(selected_tiers),
        "inspection_stride": args.inspection_stride,
        "forecast_horizon": args.forecast_horizon,
        "likelihood_sigma": args.likelihood_sigma,
        "censor_tail_scale": args.censor_tail_scale,
        "censor_quadrature_points": args.censor_quadrature_points,
        "sensor_observation_model_id": sensor_model.model_id,
        "sensor_calibration_status": sensor_model.calibration_status,
        "sensor_approved_for_inference": sensor_model.approved_for_inference,
        "sensor_model_json": str(args.sensor_model_json) if args.sensor_model_json else None,
        "sensor_noise_multiplier": args.sensor_noise_multiplier,
        "sensor_missing_probability": args.sensor_missing_probability,
        "random_seed": args.random_seed,
        "observable_growth_baseline": not growth_predictions.empty,
        "growth_rate_particles": args.growth_rate_particles,
        "growth_tip_sigma": args.growth_tip_sigma,
        "growth_process_relative_sigma": args.growth_process_relative_sigma,
        "growth_forgetting": args.growth_forgetting,
        "physics_families": physics_families,
        "mixed_physics_family": len(physics_families) > 1,
        "claim_quarantined": len(physics_families) > 1,
        "primary_asset": "decision.md",
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    validation_errors = validate_package(args.out_dir)
    validation = {
        "valid": not validation_errors,
        "errors": validation_errors,
        "validator": "validate_reality_assimilation_package.py",
    }
    (args.out_dir / "validation.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )
    if validation_errors:
        raise RuntimeError(f"Reality-assimilation package validation failed: {validation_errors}")
    print(f"Wrote reality-facing assimilation package to {args.out_dir}")
    print(summary[summary["heldout_trajectory"] == "ALL"].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
