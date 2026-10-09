#!/usr/bin/env python3
"""Train the single frozen YOLO11n PaveTrack proposal detector."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

from common import (
    PROTOCOL,
    frozen_ultralytics_device,
    load_data_lock,
    locations_for_splits,
    sha256_file,
    validate_prepared_record_hashes,
    validate_proposer_checkpoint,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--development-manifest", type=Path, required=True)
    parser.add_argument("--data-lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="1")
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()

    from ultralytics import YOLO
    import torch

    seed = 20261008
    lock = load_data_lock(args.data_lock)
    development = json.loads(args.development_manifest.read_text(encoding="utf-8"))
    if development.get("protocol") != PROTOCOL or "test" in development.get(
        "splits", []
    ):
        raise ValueError("development manifest has the wrong protocol or contains test")
    if development.get("data_lock_sha256") != sha256_file(args.data_lock):
        raise ValueError("development manifest is not bound to this data lock")
    if development.get("workbook_sha256") != lock["workbook_sha256"]:
        raise ValueError("development manifest is not bound to the locked workbook")
    validate_prepared_record_hashes(development)
    for split in ("train", "validation"):
        observed = {
            str(record["reid"])
            for record in development["records"]
            if record["split"] == split
        }
        expected = locations_for_splits(lock, [split])
        if observed != expected:
            raise ValueError(f"development {split} locations differ from data lock")
    if any(record["split"] not in {"train", "validation"} for record in development["records"]):
        raise ValueError("development manifest contains a non-development record")
    if args.dataset.resolve().parent != args.development_manifest.resolve().parent:
        raise ValueError("dataset YAML and development manifest must share one prepared root")
    recorded_images = {Path(record["prepared_image"]).resolve() for record in development["records"]}
    actual_images = {
        path.resolve()
        for split in ("train", "validation")
        for path in (args.dataset.parent / "images" / split).glob("*.jpg")
    }
    if recorded_images != actual_images:
        raise ValueError("prepared detector images differ from development manifest")
    label_files = {
        path.resolve()
        for split in ("train", "validation")
        for path in (args.dataset.parent / "labels" / split).glob("*.txt")
    }
    if len(label_files) != len(recorded_images):
        raise ValueError("prepared detector label count differs from development manifest")
    recorded_labels = {Path(record["prepared_label"]).resolve() for record in development["records"]}
    if recorded_labels != label_files:
        raise ValueError("prepared detector labels differ from development manifest")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("protocol") != PROTOCOL:
        raise ValueError("run config has the wrong protocol")
    if development.get("run_config_sha256") != sha256_file(args.config):
        raise ValueError("development manifest was prepared under a different run config")
    training_device = frozen_ultralytics_device(config, args.device)
    expected_weights_hash = config["proposer"]["initial_weights_sha256"]
    actual_weights_hash = sha256_file(args.weights)
    if actual_weights_hash != expected_weights_hash:
        raise ValueError(f"initial weights SHA-256 mismatch: {actual_weights_hash}")
    model = YOLO(str(args.weights.resolve()))
    result = model.train(
        data=str(args.dataset.resolve()),
        epochs=50,
        patience=10,
        imgsz=1280,
        batch=8,
        device=training_device,
        seed=seed,
        deterministic=True,
        workers=4,
        project=str(args.output.resolve()),
        name="proposer",
        exist_ok=False,
        plots=True,
        verbose=True,
    )
    best_model = Path(result.save_dir) / "weights" / "best.pt"
    validate_proposer_checkpoint(best_model, config)
    receipt = {
        "protocol": PROTOCOL,
        "stage": "proposer",
        "seed": seed,
        "weights_initial": str(args.weights.resolve()),
        "weights_initial_sha256": actual_weights_hash,
        "run_config_sha256": sha256_file(args.config),
        "dataset": str(args.dataset.resolve()),
        "dataset_sha256": sha256_file(args.dataset),
        "development_manifest": str(args.development_manifest.resolve()),
        "development_manifest_sha256": sha256_file(args.development_manifest),
        "data_lock_sha256": sha256_file(args.data_lock),
        "workbook_sha256": development["workbook_sha256"],
        "epochs": 50,
        "patience": 10,
        "imgsz": 1280,
        "batch": 8,
        "device": str(training_device),
        "hostname": platform.node(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "ultralytics_result_dir": str(result.save_dir),
        "best_model": str(best_model.resolve()),
        "best_model_sha256": sha256_file(best_model),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "proposer_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
