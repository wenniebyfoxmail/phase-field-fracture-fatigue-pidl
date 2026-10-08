#!/usr/bin/env python3
"""Train the single frozen MobileNetV3-small proposal reranker."""

from __future__ import annotations

import argparse
import json
import platform
import random
from pathlib import Path

from common import (
    PROTOCOL,
    load_data_lock,
    sha256_file,
    validate_prepared_record_hashes,
    validate_producer_runtime,
    validate_reranker_checkpoint,
)


def validate_crop_manifest(path: Path, expected_split: str, crops_root: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "protocol",
        "split",
        "manifest_sha256",
        "data_lock_sha256",
        "workbook_sha256",
        "proposer_sha256",
        "proposer_receipt_sha256",
        "run_config_sha256",
        "records",
    }
    missing = required - set(payload)
    if missing:
        raise ValueError(f"crop manifest lacks fields: {sorted(missing)}")
    if payload["protocol"] != PROTOCOL or payload["split"] != expected_split:
        raise ValueError(f"wrong crop-manifest identity for {expected_split}")
    records = payload["records"]
    if any(record.get("split") != expected_split for record in records):
        raise ValueError(f"crop manifest contains records outside {expected_split}")
    recorded_paths = {Path(record["path"]).resolve() for record in records}
    actual_paths = {
        candidate.resolve() for candidate in (crops_root / expected_split).glob("*/*.jpg")
    }
    if recorded_paths != actual_paths:
        raise ValueError(
            f"crop files differ from {expected_split} manifest: "
            f"missing={len(recorded_paths - actual_paths)}, extra={len(actual_paths - recorded_paths)}"
        )
    for record in records:
        expected_class = "crack" if int(record["label"]) == 1 else "background"
        if Path(record["path"]).parent.name != expected_class:
            raise ValueError(f"crop class directory disagrees with label: {record['path']}")
        if record.get("sha256") != sha256_file(Path(record["path"])):
            raise ValueError(f"crop content hash mismatch: {record['path']}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crops", type=Path, required=True)
    parser.add_argument("--train-crop-manifest", type=Path, required=True)
    parser.add_argument("--validation-crop-manifest", type=Path, required=True)
    parser.add_argument("--development-manifest", type=Path, required=True)
    parser.add_argument("--data-lock", type=Path, required=True)
    parser.add_argument("--pretrained-state-dict", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:1")
    args = parser.parse_args()

    import numpy as np
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, WeightedRandomSampler
    from torchvision import datasets, models, transforms

    seed = 20261008
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)

    train_manifest = validate_crop_manifest(args.train_crop_manifest, "train", args.crops)
    validation_manifest = validate_crop_manifest(
        args.validation_crop_manifest, "validation", args.crops
    )
    lineage_fields = (
        "manifest_sha256",
        "data_lock_sha256",
        "workbook_sha256",
        "proposer_sha256",
        "proposer_receipt_sha256",
        "run_config_sha256",
    )
    for field in lineage_fields:
        if train_manifest[field] != validation_manifest[field]:
            raise ValueError(f"train and validation crop lineage differ at {field}")
    lock = load_data_lock(args.data_lock)
    development = json.loads(args.development_manifest.read_text(encoding="utf-8"))
    if development.get("protocol") != PROTOCOL or "test" in development.get(
        "splits", []
    ):
        raise ValueError("development manifest has the wrong protocol or contains test")
    validate_prepared_record_hashes(development)
    if train_manifest["manifest_sha256"] != sha256_file(args.development_manifest):
        raise ValueError("crop manifests are not bound to this development manifest")
    if train_manifest["data_lock_sha256"] != sha256_file(args.data_lock):
        raise ValueError("crop manifests are not bound to this data lock")
    if train_manifest["workbook_sha256"] != lock["workbook_sha256"]:
        raise ValueError("crop manifests are not bound to the locked workbook")
    for split, crop_manifest in (
        ("train", train_manifest),
        ("validation", validation_manifest),
    ):
        allowed_images = {
            record["image_id"]
            for record in development["records"]
            if record["split"] == split
        }
        crop_images = {record["image_id"] for record in crop_manifest["records"]}
        if not crop_images.issubset(allowed_images):
            raise ValueError(f"{split} crops contain images outside development manifest")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("protocol") != PROTOCOL:
        raise ValueError("run config has the wrong protocol")
    if train_manifest["run_config_sha256"] != sha256_file(args.config):
        raise ValueError("crop manifests were generated under a different run config")
    if development.get("run_config_sha256") != sha256_file(args.config):
        raise ValueError("development manifest was prepared under a different run config")
    validate_producer_runtime(config, args.device)
    expected_pretrained_hash = config["reranker"]["initial_weights_sha256"]
    pretrained_hash = sha256_file(args.pretrained_state_dict)
    if pretrained_hash != expected_pretrained_hash:
        raise ValueError(f"pretrained state-dict SHA-256 mismatch: {pretrained_hash}")

    train_transform = transforms.Compose(
        [
            transforms.Resize((256, 256)),
            transforms.RandomResizedCrop(224, scale=(0.80, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.15, contrast=0.15),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )
    validation_transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )
    train_data = datasets.ImageFolder(args.crops / "train", transform=train_transform)
    validation_data = datasets.ImageFolder(
        args.crops / "validation", transform=validation_transform
    )
    if train_data.class_to_idx != {"background": 0, "crack": 1}:
        raise ValueError(f"unexpected class mapping: {train_data.class_to_idx}")
    if validation_data.class_to_idx != train_data.class_to_idx:
        raise ValueError(f"validation class mapping differs: {validation_data.class_to_idx}")
    generator = torch.Generator().manual_seed(seed)
    class_counts = {
        class_index: sum(target == class_index for target in train_data.targets)
        for class_index in train_data.class_to_idx.values()
    }
    if any(count == 0 for count in class_counts.values()):
        raise ValueError(f"empty training class: {class_counts}")
    sample_weights = [1.0 / class_counts[target] for target in train_data.targets]
    sampler = WeightedRandomSampler(
        sample_weights, num_samples=len(sample_weights), replacement=True, generator=generator
    )
    loaders = {
        "train": DataLoader(
            train_data, batch_size=64, sampler=sampler, num_workers=4, generator=generator
        ),
        "validation": DataLoader(
            validation_data, batch_size=64, shuffle=False, num_workers=4
        ),
    }

    device = torch.device(args.device)
    model = models.mobilenet_v3_small(weights=None)
    model.load_state_dict(
        torch.load(args.pretrained_state_dict, map_location="cpu", weights_only=True)
    )
    model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, 2)
    model.to(device)
    loss_function = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    args.output.mkdir(parents=True, exist_ok=True)

    history = []
    best_loss = float("inf")
    best_epoch = None
    for epoch in range(1, 16):
        epoch_row = {"epoch": epoch}
        for phase in ("train", "validation"):
            model.train(phase == "train")
            running_loss = 0.0
            correct = 0
            count = 0
            for images, labels in loaders[phase]:
                images, labels = images.to(device), labels.to(device)
                optimizer.zero_grad(set_to_none=True)
                with torch.set_grad_enabled(phase == "train"):
                    logits = model(images)
                    loss = loss_function(logits, labels)
                    if phase == "train":
                        loss.backward()
                        optimizer.step()
                running_loss += float(loss.item()) * len(labels)
                correct += int((logits.argmax(dim=1) == labels).sum().item())
                count += len(labels)
            epoch_row[f"{phase}_loss"] = running_loss / count
            epoch_row[f"{phase}_accuracy"] = correct / count
        history.append(epoch_row)
        print(json.dumps(epoch_row), flush=True)
        if epoch_row["validation_loss"] < best_loss:
            best_loss = epoch_row["validation_loss"]
            best_epoch = epoch
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "class_to_idx": train_data.class_to_idx,
                    "epoch": epoch,
                    "validation_loss": best_loss,
                    "lineage": {
                        **{field: train_manifest[field] for field in lineage_fields},
                        "train_crop_manifest_sha256": sha256_file(args.train_crop_manifest),
                        "validation_crop_manifest_sha256": sha256_file(
                            args.validation_crop_manifest
                        ),
                        "pretrained_state_dict_sha256": pretrained_hash,
                        "data_lock_file_sha256": sha256_file(args.data_lock),
                        "run_config_sha256": sha256_file(args.config),
                    },
                },
                args.output / "best_reranker.pt",
            )

    best_model = args.output / "best_reranker.pt"
    validate_reranker_checkpoint(best_model)
    receipt = {
        "protocol": PROTOCOL,
        "stage": "reranker",
        "seed": seed,
        "architecture": "torchvision_mobilenet_v3_small_imagenet",
        "pretrained_state_dict": str(args.pretrained_state_dict.resolve()),
        "pretrained_state_dict_sha256": pretrained_hash,
        "run_config_sha256": sha256_file(args.config),
        "train_crop_manifest_sha256": sha256_file(args.train_crop_manifest),
        "validation_crop_manifest_sha256": sha256_file(args.validation_crop_manifest),
        "development_manifest_sha256": train_manifest["manifest_sha256"],
        "data_lock_file_sha256": sha256_file(args.data_lock),
        "data_lock_sha256": train_manifest["data_lock_sha256"],
        "workbook_sha256": train_manifest["workbook_sha256"],
        "proposer_sha256": train_manifest["proposer_sha256"],
        "proposer_receipt_sha256": train_manifest["proposer_receipt_sha256"],
        "epochs": 15,
        "batch": 64,
        "learning_rate": 1e-4,
        "weight_decay": 1e-4,
        "selection": "minimum validation cross-entropy",
        "training_sampling": "inverse-frequency weighted sampling with replacement",
        "training_class_counts": class_counts,
        "best_epoch": best_epoch,
        "best_validation_loss": best_loss,
        "best_model": str(best_model.resolve()),
        "best_model_sha256": sha256_file(best_model),
        "device": args.device,
        "hostname": platform.node(),
        "torch": torch.__version__,
        "history": history,
    }
    (args.output / "reranker_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in receipt.items() if key != "history"}, indent=2))


if __name__ == "__main__":
    main()
