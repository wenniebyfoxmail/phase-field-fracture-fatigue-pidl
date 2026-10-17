#!/usr/bin/env python3
"""Freeze fitted artifacts before any confirmatory PaveTrack pixels are read."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from common import (
    PROTOCOL,
    sha256_file,
    validate_producer_runtime,
    validate_proposer_checkpoint,
    validate_reranker_checkpoint,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-lock", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--proposer", type=Path, required=True)
    parser.add_argument("--reranker", type=Path, required=True)
    parser.add_argument("--proposer-receipt", type=Path, required=True)
    parser.add_argument("--validation-evaluation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    validation = json.loads(args.validation_evaluation.read_text(encoding="utf-8"))
    if validation.get("protocol") != PROTOCOL or validation.get("split") != "validation":
        raise ValueError(f"validation evaluation does not match {PROTOCOL}")
    if validation.get("primary_pass") is not None:
        raise ValueError("validation output must not contain a confirmatory verdict")
    required_validation = {
        "manifest_sha256",
        "validation_manifest_sha256",
        "data_lock_sha256",
        "workbook_sha256",
        "proposer_sha256",
        "reranker_sha256",
        "reranker_lineage",
        "proposer_receipt_sha256",
        "run_config_sha256",
        "frozen_two_stage_score",
    }
    missing_validation = required_validation - set(validation)
    if missing_validation:
        raise ValueError(f"validation evaluation lacks fields: {sorted(missing_validation)}")
    data_lock_hash = sha256_file(args.data_lock)
    proposer_hash = sha256_file(args.proposer)
    reranker_hash = sha256_file(args.reranker)
    proposer_receipt_hash = sha256_file(args.proposer_receipt)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("protocol") != PROTOCOL:
        raise ValueError("run config has the wrong protocol")
    config_hash = sha256_file(args.config)
    if validation["run_config_sha256"] != config_hash:
        raise ValueError("validation evaluation uses a different run config")
    validate_proposer_checkpoint(args.proposer, config)
    validate_reranker_checkpoint(args.reranker, validation["reranker_lineage"])
    validate_producer_runtime(config, config["producer_runtime"]["device"])
    proposer_receipt = json.loads(args.proposer_receipt.read_text(encoding="utf-8"))
    if proposer_receipt.get("protocol") != PROTOCOL:
        raise ValueError("proposer receipt has the wrong protocol")
    if proposer_receipt.get("best_model_sha256") != proposer_hash:
        raise ValueError("proposer receipt is not bound to this checkpoint")
    if validation["data_lock_sha256"] != data_lock_hash:
        raise ValueError("validation evaluation uses a different data lock")
    if validation["proposer_sha256"] != proposer_hash:
        raise ValueError("validation evaluation uses a different proposer")
    if validation["reranker_sha256"] != reranker_hash:
        raise ValueError("validation evaluation uses a different reranker")
    if validation["proposer_receipt_sha256"] != proposer_receipt_hash:
        raise ValueError("validation evaluation uses a different proposer receipt")
    lineage = validation["reranker_lineage"]
    if lineage.get("manifest_sha256") != validation["manifest_sha256"]:
        raise ValueError("validation manifest differs from reranker fitting lineage")
    if lineage.get("data_lock_sha256") != data_lock_hash:
        raise ValueError("reranker fitting used a different data lock")
    if lineage.get("workbook_sha256") != validation["workbook_sha256"]:
        raise ValueError("reranker fitting used a different workbook")
    if lineage.get("proposer_sha256") != proposer_hash:
        raise ValueError("reranker crops came from a different proposer")
    if lineage.get("proposer_receipt_sha256") != proposer_receipt_hash:
        raise ValueError("reranker crops used a different proposer receipt")
    if lineage.get("run_config_sha256") != validation["run_config_sha256"]:
        raise ValueError("reranker fitting used a different run config")
    frozen_score = "sqrt(proposer_confidence * reranker_crack_probability)"
    if validation["frozen_two_stage_score"] != frozen_score:
        raise ValueError("validation evaluation used a different scoring rule")
    payload = {
        "protocol": PROTOCOL,
        "status": "authorized_after_model_freeze",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_lock": str(args.data_lock.resolve()),
        "data_lock_sha256": data_lock_hash,
        "workbook_sha256": validation["workbook_sha256"],
        "proposer": str(args.proposer.resolve()),
        "proposer_sha256": proposer_hash,
        "proposer_receipt": str(args.proposer_receipt.resolve()),
        "proposer_receipt_sha256": proposer_receipt_hash,
        "run_config_sha256": validation["run_config_sha256"],
        "reranker": str(args.reranker.resolve()),
        "reranker_sha256": reranker_hash,
        "validation_evaluation": str(args.validation_evaluation.resolve()),
        "validation_evaluation_sha256": sha256_file(args.validation_evaluation),
        "validation_manifest_sha256": validation["manifest_sha256"],
        "train_crop_manifest_sha256": lineage["train_crop_manifest_sha256"],
        "validation_crop_manifest_sha256": lineage["validation_crop_manifest_sha256"],
        "scoring_rule": frozen_score,
        "primary_metric": "macro-location R@1FP/image, one global threshold, IoU>=0.50",
        "primary_pass_delta": 0.10,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
