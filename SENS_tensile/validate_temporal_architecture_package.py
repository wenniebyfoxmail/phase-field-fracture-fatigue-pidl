#!/usr/bin/env python3
"""Validate completeness and leakage declarations of a temporal-study package."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


CORE_FAMILIES = (
    "markov",
    "gru",
    "lstm",
    "tcn",
    "transformer",
    "diagonal_ssm",
)
REQUIRED_COMPARISONS = {
    "validation_rollout_c67_c76": {9},
    "reused_evaluation_rollout_c76_c89": {1, 3, 5, 10, 13},
    "reused_twenty_cycle_rollout_c69_c89": {20},
    "oracle_c87_raw_reset_c76_c89": {13},
    "oracle_c87_full_reset_c76_c89": {13},
    "oracle_true_history_restart_c87_c89": {2},
}
ANALYSIS_ASSETS = (
    "tables/seed_level_metrics.csv",
    "tables/seed_run_summary.csv",
    "tables/architecture_ablation_table.csv",
    "figures/rollout_horizon_curves.png",
    "figures/fem_field_residual_support_c89.png",
    "figures/transition_timing_signals.png",
    "figures/validation_context_ablation.png",
    "analysis_manifest.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--analysis-root", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path(__file__).with_name("temporal_architecture_protocol_v1.json"),
    )
    parser.add_argument("--ablation-family")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    errors: list[str] = []
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    actual_hash = sha256(args.dataset)
    if actual_hash != protocol["dataset"]["sha256"]:
        errors.append("dataset hash does not match the sealed protocol")

    core_runs: dict[tuple[str, int], tuple[Path, dict]] = {}
    ablation_tags: set[str] = set()
    for manifest_path in args.runs_root.rglob("RUN_MANIFEST.json"):
        run_dir = manifest_path.parent
        if "smoke" in run_dir.parts:
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        family = str(manifest.get("temporal_model", ""))
        seed = int(manifest.get("seed", -1))
        if run_dir.parent.name in {"core_1", "core_2"}:
            core_runs[(family, seed)] = (run_dir, manifest)
        elif run_dir.parent.name == "ablations":
            ablation_tags.add(run_dir.name)

    expected = {(family, seed) for family in CORE_FAMILIES for seed in (1, 2, 3)}
    missing = sorted(expected - set(core_runs))
    if missing:
        errors.append(f"missing core runs: {missing}")

    target = int(protocol["capacity_gate"]["target_parameters"])
    tolerance = float(protocol["capacity_gate"]["relative_tolerance"])
    for key, (run_dir, manifest) in sorted(core_runs.items()):
        label = f"{key[0]} seed {key[1]}"
        if manifest.get("claim_class") != "tooling-only":
            errors.append(f"{label}: claim_class is not tooling-only")
        if manifest.get("trajectory_generalization") is not False:
            errors.append(f"{label}: trajectory generalization must be false")
        features = manifest.get("features", {})
        if features.get("cycle_index") or features.get("cycle_to_failure"):
            errors.append(f"{label}: forbidden cycle feature is enabled")
        if features.get("loading_metadata"):
            errors.append(f"{label}: sealed dataset has no loading metadata")
        split = manifest.get("split", {})
        if split.get("normalization") != "c1-c67 only":
            errors.append(f"{label}: normalization split drift")
        parameters = int(manifest["parameter_breakdown"]["total"])
        if abs(parameters - target) / target > tolerance:
            errors.append(f"{label}: parameter gate failed")
        cost = manifest.get("cost", {})
        for cost_key in (
            "training_wall_seconds",
            "inference_seconds_per_cycle",
            "peak_cuda_memory_bytes",
        ):
            if float(cost.get(cost_key, 0)) <= 0:
                errors.append(f"{label}: invalid {cost_key}")

        metrics_path = run_dir / "fem_centred_metrics.csv"
        with metrics_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        coverage: dict[str, set[int]] = {}
        for row in rows:
            coverage.setdefault(row["comparison"], set()).add(int(row["horizon"]))
            for metric, value in row.items():
                if metric == "comparison":
                    continue
                number = float(value)
                if not math.isfinite(number) and not metric.endswith("correlation"):
                    errors.append(f"{label}: non-finite {metric}")
                    break
        for comparison, horizons in REQUIRED_COMPARISONS.items():
            absent = horizons - coverage.get(comparison, set())
            if absent:
                errors.append(f"{label}: {comparison} misses horizons {sorted(absent)}")

        event_path = run_dir / "event_timing.json"
        if not event_path.exists():
            errors.append(f"{label}: missing event_timing.json")
        else:
            event = json.loads(event_path.read_text(encoding="utf-8"))
            if int(event["true_event_cycle"]) != 87:
                errors.append(f"{label}: true transition cycle is not c87")
        predictions = run_dir / "reused_evaluation_predictions.npz"
        if not predictions.exists():
            errors.append(f"{label}: missing reused predictions")

    if args.ablation_family:
        required_tags = {
            f"{args.ablation_family}_context_{context}_seed1"
            for context in (1, 3, 5, 10, 20)
        }
        required_tags |= {
            f"{args.ablation_family}_{ablation}_seed{seed}"
            for ablation in ("pointwise", "teacher_forcing", "one_step")
            for seed in (1, 2, 3)
        }
        absent = sorted(required_tags - ablation_tags)
        if absent:
            errors.append(f"missing ablations: {absent}")

    for relative in ANALYSIS_ASSETS:
        path = args.analysis_root / relative
        if not path.exists() or path.stat().st_size == 0:
            errors.append(f"missing analysis asset: {relative}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(
        f"PASS: {len(core_runs)} core runs, {len(ablation_tags)} ablations, "
        f"{len(ANALYSIS_ASSETS)} analysis assets"
    )


if __name__ == "__main__":
    main()
