#!/usr/bin/env python3
"""Validate completeness and fairness labels of the multi-origin package."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np


FAMILIES = {"markov", "gru", "lstm", "tcn", "transformer", "diagonal_ssm"}
EXPECTED_COUNTS = {
    "observed_fem_history_same_regime": 11,
    "autonomous_transition_stress_c76_c89": 13,
    "free_history_c87_raw_reset": 2,
    "free_history_c87_full_reset": 2,
    "oracle_history_shared_sparse_c87_assimilation": 2,
    "free_history_shared_sparse_c87_assimilation": 2,
}
PREDICTION_KEYS = {
    "c78_from_c76_h2",
    "c80_from_c79_h1",
    "free_c86",
    "free_c87",
    "free_c89",
    "raw_reset_c89",
    "full_reset_c89",
    "sparse_oracle_history_c89",
    "sparse_free_history_c89",
    "sparse_c87",
    "sparse_observed_mask",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--analysis-root", type=Path, required=True)
    parser.add_argument("--expected-dataset-sha256", required=True)
    parser.add_argument("--expected-sparse-sha256", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifests = sorted(args.results_root.rglob("MULTI_ORIGIN_MANIFEST.json"))
    if len(manifests) != 18:
        raise ValueError(f"expected 18 manifests, found {len(manifests)}")
    matrix = set()
    canonical_sparse = None
    canonical_mask = None
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        family = manifest["temporal_model"]
        seed = int(manifest["seed"])
        matrix.add((family, seed))
        if manifest["dataset_sha256"] != args.expected_dataset_sha256:
            raise ValueError(f"dataset hash mismatch in {manifest_path}")
        if manifest["sparse_c87_sha256"] != args.expected_sparse_sha256:
            raise ValueError(f"sparse c87 hash mismatch in {manifest_path}")
        if manifest["weights_changed"] or manifest["selection_changed"]:
            raise ValueError(f"checkpoint mutation claimed in {manifest_path}")
        if manifest["historical_multiscale_ranking_eligible"]:
            raise ValueError("historical multiscale cannot be ranking eligible")
        metrics_path = manifest_path.parent / "multi_origin_metrics.csv"
        with metrics_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        counts = Counter(row["comparison"] for row in rows)
        if counts != Counter(EXPECTED_COUNTS):
            raise ValueError(f"task row counts mismatch in {metrics_path}: {counts}")
        same_regime = [row for row in rows if row["comparison"] == "observed_fem_history_same_regime"]
        if any(int(float(row["cycle"])) >= 87 for row in same_regime):
            raise ValueError("same-regime task crosses the c87 transition")
        if any(row["conditioning"] != "identical_true_FEM_history_to_origin" for row in same_regime):
            raise ValueError("same-regime histories are not identically labelled")
        predictions = np.load(manifest_path.parent / "multi_origin_predictions.npz")
        if set(predictions.files) != PREDICTION_KEYS:
            raise ValueError(f"prediction keys mismatch in {manifest_path.parent}")
        sparse = np.asarray(predictions["sparse_c87"])
        mask = np.asarray(predictions["sparse_observed_mask"])
        if canonical_sparse is None:
            canonical_sparse = sparse
            canonical_mask = mask
        elif not np.array_equal(sparse, canonical_sparse) or not np.array_equal(mask, canonical_mask):
            raise ValueError("not every checkpoint received the identical sparse c87 state/mask")
    expected_matrix = {(family, seed) for family in FAMILIES for seed in (1, 2, 3)}
    if matrix != expected_matrix:
        raise ValueError(f"formal matrix mismatch: {matrix}")

    required = (
        "tables/seed_level_multi_origin_metrics.csv",
        "tables/per_seed_task_metrics.csv",
        "tables/matched_multi_origin_summary.csv",
        "tables/paired_seed_differences_vs_markov.csv",
        "tables/historical_cycle_conditioned_multiscale.csv",
        "figures/figure_a_multi_origin_h1_h3.png",
        "figures/figure_b_representative_c78_c80_fields.png",
        "figures/supplementary_all_models_c78_c80_fields.png",
        "figures/figure_c_transition_reset_metrics.png",
        "figures/figure_c_transition_reset_fields.png",
        "analysis_manifest.json",
    )
    missing = [relative for relative in required if not (args.analysis_root / relative).exists()]
    if missing:
        raise ValueError(f"analysis package missing assets: {missing}")
    summary_path = args.analysis_root / "tables/matched_multi_origin_summary.csv"
    with summary_path.open(newline="", encoding="utf-8") as handle:
        summary = list(csv.DictReader(handle))
    summary_families = {row["family"] for row in summary}
    if summary_families != FAMILIES:
        raise ValueError(f"formal summary families are not exactly matched core: {summary_families}")
    if any("multiscale" in row["family"] for row in summary):
        raise ValueError("historical multiscale leaked into formal summary")
    historical_path = args.analysis_root / "tables/historical_cycle_conditioned_multiscale.csv"
    with historical_path.open(newline="", encoding="utf-8") as handle:
        historical = list(csv.DictReader(handle))
    if not historical or any(row["ranking_eligible"].lower() != "false" for row in historical):
        raise ValueError("historical reference lacks explicit ranking exclusion")
    paired_path = args.analysis_root / "tables/paired_seed_differences_vs_markov.csv"
    with paired_path.open(newline="", encoding="utf-8") as handle:
        paired = list(csv.DictReader(handle))
    if not paired or any(row["reference"] != "markov" for row in paired):
        raise ValueError("paired table lacks Markov-only reference")
    if any(row["inference_note"] != "n=3 descriptive interval; not a significance test" for row in paired):
        raise ValueError("paired interval caveat is missing")
    print("PASS: 18 matched checkpoints, 6 task labels, 11 analysis assets, historical baseline excluded")


if __name__ == "__main__":
    main()
