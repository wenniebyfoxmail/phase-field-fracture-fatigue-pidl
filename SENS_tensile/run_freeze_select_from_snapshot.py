#!/usr/bin/env python3
"""Run stability-validated weak selection on a declared frozen-snapshot CSV."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from freeze_select import (
    DEFAULT_TERM_NAMES,
    assemble_weak_system,
    stability_validated_select,
    validate_frozen_snapshots,
)
from freeze_select.library import DYNAMIC_TERM_NAMES
from freeze_select.multi_environment import active_measure_normalize


def run(
    input_csv: Path,
    output_dir: Path,
    *,
    claim_class: str,
    seed: int,
    n_trials: int,
    n_windows: int,
    normalize_active_measure: bool = False,
    candidate_library: str = "static",
) -> dict[str, object]:
    frame = pd.read_csv(input_csv)
    report = validate_frozen_snapshots(frame, claim_class=claim_class)
    term_names = DEFAULT_TERM_NAMES if candidate_library == "static" else DYNAMIC_TERM_NAMES
    system = assemble_weak_system(frame, term_names=term_names, n_windows=n_windows, seed=seed)
    if normalize_active_measure:
        system = active_measure_normalize(system)
    result = stability_validated_select(system, n_trials=n_trials, seed=seed)
    sensitivity = {}
    for threshold in (0.60, 0.70, 0.80, 0.90):
        selected = result.support_summary[
            (result.support_summary["selection_frequency"] >= threshold)
            & (result.support_summary["sign_consistency"] >= 0.85)
        ]["term"]
        sensitivity[f"{threshold:.2f}"] = sorted(selected.astype(str).tolist())

    output_dir.mkdir(parents=True, exist_ok=True)
    system.as_frame().to_csv(output_dir / "weak_system.csv", index=False)
    result.trial_coefficients.to_csv(output_dir / "trial_coefficients.csv", index=False)
    result.support_summary.to_csv(output_dir / "support_summary.csv", index=False)
    result.final_coefficients.rename_axis("term").reset_index().to_csv(
        output_dir / "final_coefficients.csv", index=False
    )
    metrics = dict(result.metrics)
    metrics.update(
        {
            "claim_class": claim_class,
            "schema_report": report.__dict__,
            "stable_support_by_frequency_threshold": sensitivity,
            "road_mechanism_claim_allowed": False,
        }
    )
    manifest = {
        "protocol_id": "freeze_select_frozen_snapshot_v1",
        "claim_class": claim_class,
        "input_csv": str(input_csv.resolve()),
        "input_sha256": hashlib.sha256(input_csv.read_bytes()).hexdigest(),
        "physics_families": list(report.physics_families),
        "known_phase_field_terms_selectable": False,
        "joint_training_baseline_executed": False,
        "seed": seed,
        "n_trials": n_trials,
        "n_windows": n_windows,
        "candidate_terms": list(term_names),
        "candidate_library": candidate_library,
        "active_measure_normalized": normalize_active_measure,
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    stable = sorted(result.stable_support)
    sensitive = len({tuple(value) for value in sensitivity.values()}) > 1
    (output_dir / "decision.md").write_text(
        "# Frozen-Snapshot Selection Decision\n\n"
        f"- Claim class: `{claim_class}`\n"
        f"- Stable support at frequency 0.75: `{stable}`\n"
        f"- Threshold-sensitive support: `{sensitive}`\n"
        f"- Mean grouped holdout improvement over fixed-physics-only residual: "
        f"`{float(metrics['mean_holdout_improvement_vs_null']):.6f}`\n"
        "- Boundary: association in a frozen residual library is not a causal "
        "road mechanism, a joint-training comparison, or a crack-forecast result.\n"
    )
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--claim-class",
        choices=("tooling-only", "diagnostic", "road-observation"),
        required=True,
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--n-trials", type=int, default=64)
    parser.add_argument("--n-windows", type=int, default=256)
    parser.add_argument("--active-measure-normalize", action="store_true")
    parser.add_argument(
        "--candidate-library", choices=("static", "damage_weighted"), default="static"
    )
    args = parser.parse_args()
    metrics = run(
        args.input_csv,
        args.output_dir,
        claim_class=args.claim_class,
        seed=args.seed,
        n_trials=args.n_trials,
        n_windows=args.n_windows,
        normalize_active_measure=args.active_measure_normalize,
        candidate_library=args.candidate_library,
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
