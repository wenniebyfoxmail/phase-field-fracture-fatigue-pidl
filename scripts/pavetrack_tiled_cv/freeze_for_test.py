#!/usr/bin/env python3
"""Freeze S01-E002 artifacts and validation selection before test access."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


COMMON_DIR = Path(__file__).resolve().parents[1] / "pavetrack_cv"
sys.path.insert(0, str(COMMON_DIR))

from common import Detection, recall_at_fp_per_image, sha256_file, validate_proposer_checkpoint, validate_reranker_checkpoint  # noqa: E402
from contracts import validate_data_lock, validate_tile_manifest_contract
from evaluate_development import oracle_coverage


PROTOCOL = "S01-E002-v1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validation-evaluation", type=Path, required=True)
    parser.add_argument("--development-manifest", type=Path, required=True)
    parser.add_argument("--tile-manifest", type=Path, required=True)
    parser.add_argument("--data-lock", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--baseline-proposer", type=Path, required=True)
    parser.add_argument("--tiled-proposer", type=Path, required=True)
    parser.add_argument("--tiled-proposer-receipt", type=Path, required=True)
    parser.add_argument("--reranker", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    lock = json.loads(args.data_lock.read_text(encoding="utf-8"))
    validate_data_lock(lock)
    evaluation = json.loads(args.validation_evaluation.read_text(encoding="utf-8"))
    manifest = json.loads(args.development_manifest.read_text(encoding="utf-8"))
    tile_manifest = json.loads(args.tile_manifest.read_text(encoding="utf-8"))
    receipt = json.loads(args.tiled_proposer_receipt.read_text(encoding="utf-8"))
    if config.get("protocol") != PROTOCOL or evaluation.get("protocol") != PROTOCOL:
        raise ValueError("protocol mismatch")
    if evaluation.get("split") != "validation":
        raise ValueError("test freeze requires a validation evaluation")
    if sha256_file(args.development_manifest) != evaluation.get("manifest_sha256"):
        raise ValueError("validation evaluation differs from development manifest")
    if manifest.get("protocol") != PROTOCOL or set(manifest.get("splits", ())) != {
        "train",
        "validation",
    }:
        raise ValueError("development manifest has the wrong protocol or splits")
    if manifest.get("data_lock_sha256") != sha256_file(args.data_lock):
        raise ValueError("development manifest differs from data lock")
    if manifest.get("run_config_sha256") != sha256_file(args.config):
        raise ValueError("development manifest differs from run config")
    if manifest.get("workbook_sha256") != lock["workbook_sha256"]:
        raise ValueError("development manifest differs from workbook lock")
    validate_tile_manifest_contract(
        tile_manifest,
        data_lock_sha256=sha256_file(args.data_lock),
        run_config_sha256=sha256_file(args.config),
        workbook_sha256=lock["workbook_sha256"],
        source_manifest_sha256=sha256_file(args.development_manifest),
    )
    expected = {
        "data_lock_sha256": sha256_file(args.data_lock),
        "run_config_sha256": sha256_file(args.config),
        "baseline_proposer_sha256": sha256_file(args.baseline_proposer),
        "tiled_proposer_sha256": sha256_file(args.tiled_proposer),
        "tiled_proposer_receipt_sha256": sha256_file(args.tiled_proposer_receipt),
        "reranker_sha256": sha256_file(args.reranker),
        "tile_manifest_sha256": sha256_file(args.tile_manifest),
    }
    for field, value in expected.items():
        if evaluation.get(field) != value:
            raise ValueError(f"validation evaluation mismatch at {field}")
    if receipt.get("protocol") != PROTOCOL:
        raise ValueError("tiled proposer receipt has the wrong protocol")
    if receipt.get("best_model_sha256") != expected["tiled_proposer_sha256"]:
        raise ValueError("tiled proposer receipt is not bound to checkpoint")
    for field, value in {
        "run_config_sha256": expected["run_config_sha256"],
        "data_lock_sha256": expected["data_lock_sha256"],
        "workbook_sha256": lock["workbook_sha256"],
        "tile_manifest_sha256": expected["tile_manifest_sha256"],
        "development_manifest_sha256": sha256_file(args.development_manifest),
    }.items():
        if receipt.get(field) != value:
            raise ValueError(f"tiled proposer receipt mismatch at {field}")
    validate_proposer_checkpoint(args.baseline_proposer, config)
    validate_proposer_checkpoint(args.tiled_proposer, config)
    validate_reranker_checkpoint(args.reranker)
    if expected["baseline_proposer_sha256"] != config["baseline_reuse"]["checkpoint_sha256"]:
        raise ValueError("baseline proposer differs from frozen S01-E001 checkpoint")
    if expected["reranker_sha256"] != config["reranker_reuse"]["checkpoint_sha256"]:
        raise ValueError("reranker differs from frozen S01-E001 checkpoint")
    selected = evaluation.get("selected_score")
    if selected not in config["reranker_reuse"]["score_candidates"]:
        raise ValueError("validation selected an unapproved score")
    targets = evaluation.get("targets")
    image_locations = evaluation.get("image_locations")
    baseline_rows = evaluation.get("baseline_proposals")
    repaired_rows = evaluation.get("repaired_proposals")
    if not all(isinstance(value, dict) for value in (targets, image_locations)):
        raise ValueError("validation evaluation lacks target identity for recomputation")
    if not all(isinstance(value, list) for value in (baseline_rows, repaired_rows)):
        raise ValueError("validation evaluation lacks proposal rows for recomputation")
    validation_records = [
        record for record in manifest["records"] if record["split"] == "validation"
    ]
    if {str(record["reid"]) for record in validation_records} != set(
        lock["validation_locations"]
    ):
        raise ValueError("development manifest validation locations differ from data lock")
    expected_targets = {
        record["image_id"]: record["crack_boxes_xyxy"] for record in validation_records
    }
    expected_locations = {
        record["image_id"]: str(record["reid"]) for record in validation_records
    }
    if targets != expected_targets or image_locations != expected_locations:
        raise ValueError("validation target identity differs from development manifest")
    for record in validation_records:
        if sha256_file(Path(record["prepared_image"])) != record["prepared_image_sha256"]:
            raise ValueError(f"prepared image content hash mismatch: {record['prepared_image']}")
    baseline_detections = [
        Detection(row["image_id"], row["reid"], row["box_xyxy"], row["proposer_confidence"])
        for row in baseline_rows
    ]
    recomputed_baseline = recall_at_fp_per_image(
        baseline_detections, targets, image_locations
    )
    if recomputed_baseline != evaluation.get("baseline"):
        raise ValueError("stored baseline metrics differ from recomputation")
    score_fields = {
        "proposer_confidence": "proposer_confidence",
        "sqrt(proposer_confidence * reranker_crack_probability)": "geometric_mean",
        "reranker_crack_probability": "reranker_crack_probability",
    }
    recomputed_candidates = {}
    for score_name in config["reranker_reuse"]["score_candidates"]:
        field = score_fields[score_name]
        detections = [
            Detection(row["image_id"], row["reid"], row["box_xyxy"], row[field])
            for row in repaired_rows
        ]
        recomputed_candidates[score_name] = recall_at_fp_per_image(
            detections, targets, image_locations
        )
    if recomputed_candidates != evaluation.get("repaired_score_candidates"):
        raise ValueError("stored repaired metrics differ from recomputation")
    candidate_order = config["reranker_reuse"]["score_candidates"]
    recomputed_selected = max(
        candidate_order,
        key=lambda name: (
            recomputed_candidates[name]["macro_location_recall"],
            -candidate_order.index(name),
        ),
    )
    if selected != recomputed_selected:
        raise ValueError("stored selected score differs from recomputation")
    recomputed_baseline_oracle = oracle_coverage(
        baseline_rows, targets, image_locations
    )
    recomputed_repaired_oracle = oracle_coverage(
        repaired_rows, targets, image_locations
    )
    if recomputed_baseline_oracle != evaluation.get("baseline_oracle_coverage"):
        raise ValueError("stored baseline oracle differs from recomputation")
    if recomputed_repaired_oracle != evaluation.get("repaired_oracle_coverage"):
        raise ValueError("stored repaired oracle differs from recomputation")
    recomputed_primary_delta = (
        recomputed_candidates[selected]["macro_location_recall"]
        - recomputed_baseline["macro_location_recall"]
    )
    recomputed_coverage_delta = (
        recomputed_repaired_oracle["macro_location_recall"]
        - recomputed_baseline_oracle["macro_location_recall"]
    )
    if recomputed_primary_delta != evaluation.get(
        "primary_delta_macro_location_R_at_1FP_per_image"
    ):
        raise ValueError("stored primary delta differs from recomputation")
    if recomputed_coverage_delta != evaluation.get(
        "oracle_coverage_delta_macro_location_recall"
    ):
        raise ValueError("stored coverage delta differs from recomputation")
    authorization = {
        "protocol": PROTOCOL,
        "status": "authorized_after_model_and_validation_freeze",
        **expected,
        "workbook_sha256": lock["workbook_sha256"],
        "validation_evaluation_sha256": sha256_file(args.validation_evaluation),
        "validation_manifest_sha256": evaluation["manifest_sha256"],
        "selected_score": selected,
        "primary_metric": "macro-location R@1FP/image, one global threshold, IoU>=0.50",
        "primary_delta_to_pass": config["primary_metric"][
            "absolute_delta_over_frozen_full_frame_baseline_to_pass"
        ],
        "coverage_delta_to_pass": config["necessary_coverage_gate"][
            "minimum_absolute_delta_over_full_frame_baseline"
        ],
        "confirmatory_test_locations": lock["confirmatory_test_locations"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(authorization, indent=2), encoding="utf-8")
    print(json.dumps(authorization, indent=2))


if __name__ == "__main__":
    main()
