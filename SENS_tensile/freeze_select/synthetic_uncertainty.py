"""Stage A3 uncertainty-aware synthetic Freeze-Then-Select development loop."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

import numpy as np
import pandas as pd

from .library import DYNAMIC_TERM_NAMES
from .structured_adapter import AdapterConfig
from .synthetic_forecast import (
    ForecastConfig,
    _event_index,
    _mask_iou,
    _rollout_section,
    _tip,
    bootstrap_adapter_ensemble,
    generate_dynamic_truth,
    run_stage_a2,
    sample_sparse_observations,
)
from .uncertainty_selector import uncertainty_aware_select
from .weak_system import assemble_dynamic_weak_system


def _support_metrics(support: set[str], truth: set[str]) -> dict[str, float | bool]:
    intersection = support & truth
    union = support | truth
    precision = 1.0 if not support else len(intersection) / len(support)
    recall = len(intersection) / len(truth)
    return {
        "exact_support": support == truth,
        "support_jaccard": len(intersection) / len(union),
        "support_precision": precision,
        "support_recall": recall,
    }


def run_stage_a3(
    config: ForecastConfig,
    output_dir: Path,
    *,
    n_adapters: int = 8,
    n_replicates: int = 128,
) -> dict[str, object]:
    from .synthetic_forecast import TRUE_DYNAMIC_BETA

    output_dir.mkdir(parents=True, exist_ok=True)
    baseline_dir = output_dir / "a2_baselines"
    a2 = run_stage_a2(config, baseline_dir)
    truth = generate_dynamic_truth(config)
    observations = sample_sparse_observations(truth, config)
    members, manifests, hashes = bootstrap_adapter_ensemble(
        truth,
        observations,
        config,
        AdapterConfig(),
        n_adapters=n_adapters,
    )
    train_ids = [f"synthetic_section_{index}" for index in range(config.n_sections - 3)]
    validation_id = f"synthetic_section_{config.n_sections - 3}"
    holdout_ids = [
        f"synthetic_section_{config.n_sections - 2}",
        f"synthetic_section_{config.n_sections - 1}",
    ]
    train_systems = []
    validation_systems = []
    for member in members:
        train_frame = member[
            member["trajectory_id"].isin(train_ids)
            & (member["cycle"] <= config.cutoff_index)
        ]
        validation_frame = member[
            (member["trajectory_id"] == validation_id)
            & (member["cycle"] <= config.cutoff_index)
        ]
        train_systems.append(
            assemble_dynamic_weak_system(
                train_frame,
                term_names=DYNAMIC_TERM_NAMES,
                n_windows=config.n_windows,
                seed=config.seed,
            )
        )
        validation_systems.append(
            assemble_dynamic_weak_system(
                validation_frame,
                term_names=DYNAMIC_TERM_NAMES,
                n_windows=max(96, config.n_windows // 2),
                seed=config.seed + 1000,
            )
        )
    selected = uncertainty_aware_select(
        train_systems,
        validation_systems,
        n_replicates=n_replicates,
        seed=config.seed,
    )
    beta = {
        name: float(value)
        for name, value in selected.coefficients.items()
        if abs(value) > 1e-12
    }
    mean_frozen = members[0].copy()
    mean_frozen["d"] = np.mean(
        np.stack([member["d"].to_numpy(float) for member in members]), axis=0
    )
    x = np.linspace(0.0, 1.0, config.nx)
    y = np.linspace(-0.5, 0.5, config.ny)
    x_grid, _ = np.meshgrid(x, y)
    rows = []
    for trajectory_id in holdout_ids:
        section = int(trajectory_id.rsplit("_", 1)[1])
        true_states = truth[truth["trajectory_id"] == trajectory_id].sort_values(
            ["cycle", "cell_id"]
        )["d"].to_numpy(float).reshape(config.n_times, config.ny, config.nx)[
            config.cutoff_index :
        ]
        initial = mean_frozen[
            (mean_frozen["trajectory_id"] == trajectory_id)
            & (mean_frozen["cycle"] == config.cutoff_index)
        ].sort_values("cell_id")["d"].to_numpy(float).reshape(config.ny, config.nx)
        prediction = _rollout_section(initial, section, config, beta)
        rows.append(
            {
                "trajectory_id": trajectory_id,
                "method": "a3_uncertainty_svws",
                "final_iou_d025": _mask_iou(prediction[-1], true_states[-1], 0.25),
                "final_iou_d050": _mask_iou(prediction[-1], true_states[-1], 0.50),
                "final_iou_d075": _mask_iou(prediction[-1], true_states[-1], 0.75),
                "final_tip_error": abs(_tip(prediction[-1], x_grid) - _tip(true_states[-1], x_grid)),
                "event_time_error": abs(
                    _event_index(prediction, config.event_area_fraction)
                    - _event_index(true_states, config.event_area_fraction)
                ),
                "forecast_rmse": float(np.sqrt(np.mean(np.square(prediction - true_states)))),
            }
        )
    section_metrics = pd.DataFrame(rows)
    forecast = section_metrics.mean(numeric_only=True).to_dict()
    truth_support = set(TRUE_DYNAMIC_BETA)
    support = _support_metrics(set(selected.support), truth_support)
    baseline_forecast = pd.read_csv(baseline_dir / "forecast_metrics.csv")
    a2_svws = baseline_forecast[baseline_forecast["method"] == "reconstructed_svws"].iloc[0]
    single = baseline_forecast[
        baseline_forecast["method"] == "reconstructed_single_shot"
    ].iloc[0]
    fixed = baseline_forecast[baseline_forecast["method"] == "fixed_physics_only"].iloc[0]
    result = {
        "claim_class": "tooling-only-development",
        "support_metrics": support,
        "a2_svws_support_jaccard": a2["support_metrics"]["reconstructed_svws"]["support_jaccard"],
        "single_support_jaccard": a2["support_metrics"]["reconstructed_single_shot"]["support_jaccard"],
        "forecast": forecast,
        "a3_minus_fixed_iou_d050": float(forecast["final_iou_d050"] - fixed["final_iou_d050"]),
        "a3_minus_a2_iou_d050": float(forecast["final_iou_d050"] - a2_svws["final_iou_d050"]),
        "a3_minus_single_iou_d050": float(forecast["final_iou_d050"] - single["final_iou_d050"]),
        "uncertainty_metrics": selected.metrics,
        "adapter_hashes": hashes,
        "confirmation_seeds_used": False,
        "joint_training_baseline_executed": False,
    }
    selected.support_summary.to_csv(output_dir / "support_summary_by_stratum.csv", index=False)
    selected.replicate_coefficients.to_csv(
        output_dir / "selection_replicates.csv", index=False
    )
    selected.validation_trace.to_csv(output_dir / "support_validation_trace.csv", index=False)
    selected.uncertainty_table.to_csv(output_dir / "uncertainty_calibration.csv", index=False)
    section_metrics.to_csv(output_dir / "section_metrics.csv", index=False)
    (output_dir / "adapter_hash_manifest.json").write_text(
        json.dumps({"hashes": hashes, "manifests": manifests}, indent=2) + "\n"
    )
    (output_dir / "config.yaml").write_text(json.dumps(asdict(config), indent=2) + "\n")
    mechanism_pass = bool(
        support["support_jaccard"] > max(
            result["a2_svws_support_jaccard"], result["single_support_jaccard"]
        )
        and selected.metrics["tip_total_weight_fraction"] >= 0.10
    )
    (output_dir / "decision.md").write_text(
        "# Stage A3 Development Decision\n\n"
        f"- Mechanism development gate: **{'PASS' if mechanism_pass else 'FAIL'}**\n"
        "- Claim class: `tooling-only-development`\n"
        f"- A3/A2/single support Jaccard: `{support['support_jaccard']:.3f}` / "
        f"`{result['a2_svws_support_jaccard']:.3f}` / `{result['single_support_jaccard']:.3f}`\n"
        f"- Tip weak-weight fraction: `{selected.metrics['tip_total_weight_fraction']:.3f}`\n"
        "- Boundary: confirmation seeds remain unopened; no road, PIDL, or causal claim.\n"
    )
    result["mechanism_development_gate"] = mechanism_pass
    (output_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
