#!/usr/bin/env python3
"""Run the predeclared 16-case Stage A2 synthetic robustness matrix."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from freeze_select.synthetic_forecast import (
    TRUE_DYNAMIC_BETA,
    ForecastConfig,
    run_stage_a2,
)


SEEDS = (11, 23, 37, 51)
OBSERVATION_RATES = (0.08, 0.20)
NOISE_SIGMAS = (0.01, 0.04)


def _method_row(frame: pd.DataFrame, method: str) -> pd.Series:
    rows = frame[frame["method"] == method]
    if len(rows) != 1:
        raise ValueError(f"Expected one forecast summary row for {method}")
    return rows.iloc[0]


def run_matrix(output_root: Path, *, n_trials: int = 64, n_windows: int = 384) -> dict[str, object]:
    output_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for seed, observation_rate, noise_sigma in itertools.product(
        SEEDS, OBSERVATION_RATES, NOISE_SIGMAS
    ):
        case_id = f"seed{seed}_obs{observation_rate:.2f}_noise{noise_sigma:.2f}".replace(".", "p")
        case_dir = output_root / case_id
        config = ForecastConfig(
            seed=seed,
            observation_rate=observation_rate,
            noise_sigma=noise_sigma,
            n_trials=n_trials,
            n_windows=n_windows,
        )
        result = run_stage_a2(config, case_dir)
        forecast = pd.read_csv(case_dir / "forecast_metrics.csv")
        support = pd.read_csv(case_dir / "support_summary.csv")
        fixed = _method_row(forecast, "fixed_physics_only")
        single = _method_row(forecast, "reconstructed_single_shot")
        svws = _method_row(forecast, "reconstructed_svws")
        true_frequency = support[support["term"].isin(TRUE_DYNAMIC_BETA)][
            "selection_frequency"
        ]
        false_frequency = support[~support["term"].isin(TRUE_DYNAMIC_BETA)][
            "selection_frequency"
        ]
        rows.append(
            {
                "case_id": case_id,
                "seed": seed,
                "observation_rate": observation_rate,
                "noise_sigma": noise_sigma,
                "limitation": result["limitation"],
                "oracle_gate": result["oracle_gate"],
                "adapter_gate": result["adapter_gate"],
                "support_gate": result["support_gate"],
                "forecast_gate": result["forecast_gate"],
                "adapter_rmse": result["adapter_pre_cutoff_validation_rmse"],
                "adapter_cutoff_iou_d050": result["adapter_cutoff_iou_d050"],
                "oracle_support_jaccard": result["support_metrics"]["oracle_svws"]["support_jaccard"],
                "svws_support_jaccard": result["support_metrics"]["reconstructed_svws"]["support_jaccard"],
                "single_support_jaccard": result["support_metrics"]["reconstructed_single_shot"]["support_jaccard"],
                "svws_minus_single_support_jaccard": result["support_metrics"]["reconstructed_svws"]["support_jaccard"]
                - result["support_metrics"]["reconstructed_single_shot"]["support_jaccard"],
                "minimum_true_term_frequency": float(true_frequency.min()),
                "maximum_false_term_frequency": float(false_frequency.max()),
                "fixed_iou_d050": float(fixed["final_iou_d050"]),
                "single_iou_d050": float(single["final_iou_d050"]),
                "svws_iou_d050": float(svws["final_iou_d050"]),
                "svws_minus_fixed_iou_d050": float(svws["final_iou_d050"] - fixed["final_iou_d050"]),
                "svws_minus_single_iou_d050": float(svws["final_iou_d050"] - single["final_iou_d050"]),
                "fixed_tip_error": float(fixed["final_tip_error"]),
                "single_tip_error": float(single["final_tip_error"]),
                "svws_tip_error": float(svws["final_tip_error"]),
                "svws_event_time_error": float(svws["event_time_error"]),
                "fixed_forecast_rmse": float(fixed["forecast_rmse"]),
                "single_forecast_rmse": float(single["forecast_rmse"]),
                "svws_forecast_rmse": float(svws["forecast_rmse"]),
                "svws_minus_single_forecast_rmse": float(svws["forecast_rmse"] - single["forecast_rmse"]),
            }
        )
    matrix = pd.DataFrame(rows)
    matrix.to_csv(output_root / "matrix_summary.csv", index=False)

    tip_cases = matrix[matrix["fixed_tip_error"] > 0.0]
    if tip_cases.empty:
        tip_gate_fraction = float(np.mean(matrix["svws_tip_error"] == 0.0))
    else:
        tip_gate_fraction = float(
            np.mean(tip_cases["svws_tip_error"] <= 0.85 * tip_cases["fixed_tip_error"])
        )
    paired_forecast_better = (
        (matrix["svws_iou_d050"] > matrix["single_iou_d050"])
        & (matrix["svws_forecast_rmse"] < matrix["single_forecast_rmse"])
    )
    aggregate = {
        "claim_class": "tooling-only",
        "n_cases": len(matrix),
        "oracle_exact_or_jaccard_ge_0p9_fraction": float(
            np.mean(matrix["oracle_support_jaccard"] >= 0.90)
        ),
        "median_oracle_support_jaccard": float(matrix["oracle_support_jaccard"].median()),
        "adapter_gate_fraction": float(matrix["adapter_gate"].mean()),
        "median_adapter_rmse": float(matrix["adapter_rmse"].median()),
        "median_adapter_cutoff_iou_d050": float(matrix["adapter_cutoff_iou_d050"].median()),
        "median_svws_support_jaccard": float(matrix["svws_support_jaccard"].median()),
        "median_single_support_jaccard": float(matrix["single_support_jaccard"].median()),
        "median_svws_minus_single_support_jaccard": float(
            matrix["svws_minus_single_support_jaccard"].median()
        ),
        "true_term_frequency_ge_0p75_fraction": float(
            np.mean(matrix["minimum_true_term_frequency"] >= 0.75)
        ),
        "false_term_frequency_le_0p45_fraction": float(
            np.mean(matrix["maximum_false_term_frequency"] <= 0.45)
        ),
        "median_svws_minus_fixed_iou_d050": float(
            matrix["svws_minus_fixed_iou_d050"].median()
        ),
        "median_svws_minus_single_iou_d050": float(
            matrix["svws_minus_single_iou_d050"].median()
        ),
        "tip_reduction_gate_fraction": tip_gate_fraction,
        "median_svws_event_time_error": float(matrix["svws_event_time_error"].median()),
        "paired_svws_forecast_better_than_single_fraction": float(paired_forecast_better.mean()),
        "stage_a2_pass_fraction": float(np.mean(matrix["limitation"] == "stage-a2-pass")),
        "joint_training_baseline_executed": False,
    }
    aggregate["oracle_matrix_gate"] = bool(
        aggregate["median_oracle_support_jaccard"] >= 0.90
        and aggregate["oracle_exact_or_jaccard_ge_0p9_fraction"] >= 0.80
    )
    aggregate["adapter_matrix_gate"] = bool(aggregate["adapter_gate_fraction"] >= 0.80)
    aggregate["support_matrix_gate"] = bool(
        aggregate["median_svws_support_jaccard"] >= 0.75
        and aggregate["true_term_frequency_ge_0p75_fraction"] >= 0.75
    )
    aggregate["forecast_matrix_gate"] = bool(
        aggregate["median_svws_minus_fixed_iou_d050"] >= 0.08
        and aggregate["tip_reduction_gate_fraction"] >= 0.75
        and aggregate["median_svws_event_time_error"] <= 2.0
    )
    aggregate["svws_superiority_gate"] = bool(
        aggregate["median_svws_minus_single_support_jaccard"] >= 0.10
        and aggregate["paired_svws_forecast_better_than_single_fraction"] > 0.50
    )
    aggregate["matrix_pass"] = bool(
        aggregate["oracle_matrix_gate"]
        and aggregate["adapter_matrix_gate"]
        and aggregate["support_matrix_gate"]
        and aggregate["forecast_matrix_gate"]
    )
    (output_root / "aggregate_metrics.json").write_text(json.dumps(aggregate, indent=2) + "\n")
    verdict = "PASS" if aggregate["matrix_pass"] else "FAIL"
    superiority = "PASS" if aggregate["svws_superiority_gate"] else "NOT ESTABLISHED"
    (output_root / "decision.md").write_text(
        "# Stage A2 Robustness Matrix Decision\n\n"
        f"- End-to-end matrix gate: **{verdict}**\n"
        f"- SVWS superiority gate: **{superiority}**\n"
        "- Claim class: `tooling-only`\n"
        f"- Cases: `{len(matrix)}`\n"
        f"- Median SVWS/single support Jaccard: "
        f"`{aggregate['median_svws_support_jaccard']:.3f}` / "
        f"`{aggregate['median_single_support_jaccard']:.3f}`\n"
        f"- Median SVWS IoU gain over fixed/single: "
        f"`{aggregate['median_svws_minus_fixed_iou_d050']:.3f}` / "
        f"`{aggregate['median_svws_minus_single_iou_d050']:.3f}`\n"
        "- Boundary: this matrix does not validate real roads, a neural PIDL "
        "adapter, causal mechanisms, or the real joint-training baseline.\n"
    )
    return aggregate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--n-trials", type=int, default=64)
    parser.add_argument("--n-windows", type=int, default=384)
    args = parser.parse_args()
    print(json.dumps(run_matrix(args.output_root, n_trials=args.n_trials, n_windows=args.n_windows), indent=2))


if __name__ == "__main__":
    main()
