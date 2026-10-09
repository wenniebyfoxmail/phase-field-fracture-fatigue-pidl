#!/usr/bin/env python3
"""Freeze S01-E002 artifacts and validation selection before test access."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


COMMON_DIR = Path(__file__).resolve().parents[1] / "pavetrack_cv"
sys.path.insert(0, str(COMMON_DIR))

from common import sha256_file, validate_proposer_checkpoint, validate_reranker_checkpoint  # noqa: E402


PROTOCOL = "S01-E002-v1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validation-evaluation", type=Path, required=True)
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
    evaluation = json.loads(args.validation_evaluation.read_text(encoding="utf-8"))
    receipt = json.loads(args.tiled_proposer_receipt.read_text(encoding="utf-8"))
    if config.get("protocol") != PROTOCOL or evaluation.get("protocol") != PROTOCOL:
        raise ValueError("protocol mismatch")
    if evaluation.get("split") != "validation":
        raise ValueError("test freeze requires a validation evaluation")
    expected = {
        "data_lock_sha256": sha256_file(args.data_lock),
        "run_config_sha256": sha256_file(args.config),
        "baseline_proposer_sha256": sha256_file(args.baseline_proposer),
        "tiled_proposer_sha256": sha256_file(args.tiled_proposer),
        "tiled_proposer_receipt_sha256": sha256_file(args.tiled_proposer_receipt),
        "reranker_sha256": sha256_file(args.reranker),
    }
    for field, value in expected.items():
        if evaluation.get(field) != value:
            raise ValueError(f"validation evaluation mismatch at {field}")
    if receipt.get("protocol") != PROTOCOL:
        raise ValueError("tiled proposer receipt has the wrong protocol")
    if receipt.get("best_model_sha256") != expected["tiled_proposer_sha256"]:
        raise ValueError("tiled proposer receipt is not bound to checkpoint")
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
