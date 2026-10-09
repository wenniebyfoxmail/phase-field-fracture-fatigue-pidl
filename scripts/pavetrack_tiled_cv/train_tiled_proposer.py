#!/usr/bin/env python3
"""Train the single frozen S01-E002 native-scale tiled proposer."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path


COMMON_DIR = Path(__file__).resolve().parents[1] / "pavetrack_cv"
sys.path.insert(0, str(COMMON_DIR))

from common import (  # noqa: E402
    frozen_ultralytics_device,
    sha256_file,
    validate_proposer_checkpoint,
)
from contracts import validate_data_lock, validate_tile_manifest_contract


PROTOCOL = "S01-E002-v1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--development-manifest", type=Path, required=True)
    parser.add_argument("--tile-manifest", type=Path, required=True)
    parser.add_argument("--data-lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="1")
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()

    from ultralytics import YOLO
    import torch

    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("protocol") != PROTOCOL:
        raise ValueError("run config has the wrong protocol")
    manifest = json.loads(args.tile_manifest.read_text(encoding="utf-8"))
    development = json.loads(args.development_manifest.read_text(encoding="utf-8"))
    lock = json.loads(args.data_lock.read_text(encoding="utf-8"))
    validate_data_lock(lock)
    if manifest.get("protocol") != PROTOCOL:
        raise ValueError("tile manifest has the wrong protocol")
    if manifest.get("run_config_sha256") != sha256_file(args.config):
        raise ValueError("tile manifest was prepared under a different run config")
    if manifest.get("data_lock_sha256") != sha256_file(args.data_lock):
        raise ValueError("tile manifest is not bound to this data lock")
    validate_tile_manifest_contract(
        manifest,
        data_lock_sha256=sha256_file(args.data_lock),
        run_config_sha256=sha256_file(args.config),
        workbook_sha256=lock["workbook_sha256"],
        source_manifest_sha256=sha256_file(args.development_manifest),
    )
    if development.get("protocol") != PROTOCOL:
        raise ValueError("development manifest has the wrong protocol")
    if development.get("data_lock_sha256") != sha256_file(args.data_lock):
        raise ValueError("development manifest is not bound to this data lock")
    if development.get("run_config_sha256") != sha256_file(args.config):
        raise ValueError("development manifest is not bound to this run config")
    if development.get("workbook_sha256") != lock["workbook_sha256"]:
        raise ValueError("development manifest is not bound to the locked workbook")
    for split, key in (("train", "train_locations"), ("validation", "validation_locations")):
        observed = {
            str(record["reid"])
            for record in manifest["records"]
            if record["split"] == split
        }
        if observed != set(lock[key]):
            raise ValueError(f"tile manifest {split} locations differ from data lock")
    if any(record["split"] not in {"train", "validation"} for record in manifest["records"]):
        raise ValueError("tile manifest contains a non-development record")
    if args.dataset.resolve().parent != args.tile_manifest.resolve().parent:
        raise ValueError("dataset YAML and tile manifest must share one prepared root")

    recorded_images = {Path(record["tile_image"]).resolve() for record in manifest["records"]}
    recorded_labels = {Path(record["tile_label"]).resolve() for record in manifest["records"]}
    actual_images = {
        path.resolve()
        for split in ("train", "validation")
        for path in (args.dataset.parent / "images" / split).glob("*.jpg")
    }
    actual_labels = {
        path.resolve()
        for split in ("train", "validation")
        for path in (args.dataset.parent / "labels" / split).glob("*.txt")
    }
    if recorded_images != actual_images or recorded_labels != actual_labels:
        raise ValueError("prepared tile files differ from tile manifest")
    for record in manifest["records"]:
        if sha256_file(Path(record["tile_image"])) != record["tile_image_sha256"]:
            raise ValueError(f"tile image content hash mismatch: {record['tile_image']}")
        if sha256_file(Path(record["tile_label"])) != record["tile_label_sha256"]:
            raise ValueError(f"tile label content hash mismatch: {record['tile_label']}")

    proposer = config["proposer"]
    initial_hash = sha256_file(args.weights)
    if initial_hash != proposer["initial_weights_sha256"]:
        raise ValueError(f"initial weights SHA-256 mismatch: {initial_hash}")
    device = frozen_ultralytics_device(config, args.device)
    model = YOLO(str(args.weights.resolve()))
    result = model.train(
        data=str(args.dataset.resolve()),
        epochs=int(proposer["epochs"]),
        patience=int(proposer["patience"]),
        imgsz=int(proposer["image_size"]),
        batch=int(proposer["batch_size"]),
        device=device,
        seed=int(config["seed"]),
        deterministic=True,
        workers=4,
        project=str(args.output.resolve()),
        name="tiled_proposer",
        exist_ok=False,
        plots=True,
        verbose=True,
    )
    best_model = Path(result.save_dir) / "weights" / "best.pt"
    validate_proposer_checkpoint(best_model, config)
    receipt = {
        "protocol": PROTOCOL,
        "stage": "tiled_proposer",
        "seed": int(config["seed"]),
        "initial_weights_sha256": initial_hash,
        "run_config_sha256": sha256_file(args.config),
        "dataset_sha256": sha256_file(args.dataset),
        "tile_manifest_sha256": sha256_file(args.tile_manifest),
        "development_manifest_sha256": sha256_file(args.development_manifest),
        "data_lock_sha256": sha256_file(args.data_lock),
        "workbook_sha256": manifest["workbook_sha256"],
        "epochs": int(proposer["epochs"]),
        "patience": int(proposer["patience"]),
        "imgsz": int(proposer["image_size"]),
        "batch": int(proposer["batch_size"]),
        "device": str(device),
        "hostname": platform.node(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "best_model": str(best_model.resolve()),
        "best_model_sha256": sha256_file(best_model),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "tiled_proposer_receipt.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
