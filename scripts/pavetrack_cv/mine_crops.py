#!/usr/bin/env python3
"""Mine frozen positive and hard-negative crops from allowed PaveTrack splits."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from common import (
    PROTOCOL,
    box_iou,
    boxes_overlap,
    clip_proposal_or_none,
    frozen_ultralytics_device,
    load_data_lock,
    locations_for_splits,
    pad_box,
    sha256_file,
    validate_prepared_record_hashes,
    validate_proposer_checkpoint,
)


def crop_name(image_id: str, source: str, index: int) -> str:
    return f"{Path(image_id).stem}__{source}-{index:04d}.jpg"


def save_crop(image, box, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    integer_box = tuple(int(round(value)) for value in box)
    image.crop(integer_box).convert("RGB").save(target, quality=92)
    return sha256_file(target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-lock", type=Path, required=True)
    parser.add_argument("--proposer", type=Path, required=True)
    parser.add_argument("--proposer-receipt", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=("train", "validation"), required=True)
    parser.add_argument("--device", default="1")
    args = parser.parse_args()

    from PIL import Image
    from ultralytics import YOLO

    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    lock = load_data_lock(args.data_lock)
    if payload.get("protocol") != PROTOCOL:
        raise ValueError("development manifest has the wrong protocol")
    if payload.get("data_lock_sha256") != sha256_file(args.data_lock):
        raise ValueError("development manifest is not bound to this data lock")
    if payload.get("workbook_sha256") != lock["workbook_sha256"]:
        raise ValueError("development manifest has the wrong workbook identity")
    validate_prepared_record_hashes(payload)
    if args.split not in payload["splits"]:
        raise ValueError(f"manifest does not authorize split {args.split}")
    if "test" in payload["splits"]:
        raise ValueError("crop mining refuses any manifest that contains confirmatory test")

    allowed_locations = locations_for_splits(lock, [args.split])
    split_records = [record for record in payload["records"] if record["split"] == args.split]
    record_locations = {str(record["reid"]) for record in split_records}
    if record_locations != allowed_locations:
        raise ValueError(
            f"manifest {args.split} locations differ from data lock: "
            f"missing={sorted(allowed_locations - record_locations)}, "
            f"extra={sorted(record_locations - allowed_locations)}"
        )
    if any(
        record["split"] not in payload["splits"]
        or str(record["reid"]) not in locations_for_splits(lock, [record["split"]])
        for record in payload["records"]
    ):
        raise ValueError("manifest contains a retagged or unauthorized record")
    proposer_hash = sha256_file(args.proposer)
    proposer_receipt = json.loads(args.proposer_receipt.read_text(encoding="utf-8"))
    if proposer_receipt.get("protocol") != PROTOCOL:
        raise ValueError("proposer receipt has the wrong protocol")
    if proposer_receipt.get("best_model_sha256") != proposer_hash:
        raise ValueError("proposer receipt is not bound to this model")
    if proposer_receipt.get("development_manifest_sha256") != sha256_file(args.manifest):
        raise ValueError("proposer was fitted with a different development manifest")
    if proposer_receipt.get("data_lock_sha256") != sha256_file(args.data_lock):
        raise ValueError("proposer was fitted with a different data lock")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("protocol") != PROTOCOL:
        raise ValueError("run config has the wrong protocol")
    config_hash = sha256_file(args.config)
    if payload.get("run_config_sha256") != config_hash:
        raise ValueError("development manifest was prepared under a different run config")
    if proposer_receipt.get("run_config_sha256") != config_hash:
        raise ValueError("proposer was fitted under a different run config")
    prediction_device = frozen_ultralytics_device(config, args.device)
    validate_proposer_checkpoint(args.proposer, config)

    rng = random.Random(20261008)
    model = YOLO(str(args.proposer.resolve()))
    records = []
    skipped_overlapping_distress = 0
    skipped_empty_proposals = 0
    image_paths = [record["prepared_image"] for record in split_records]
    predictions = model.predict(
        source=image_paths,
        imgsz=1280,
        conf=0.001,
        iou=0.70,
        max_det=300,
        device=prediction_device,
        stream=True,
        verbose=False,
    )
    for record, prediction in zip(split_records, predictions, strict=True):
        image_path = Path(record["prepared_image"])
        with Image.open(image_path) as opened:
            image = opened.convert("RGB")
            width, height = image.size
            crack_boxes = [tuple(box) for box in record["crack_boxes_xyxy"]]
            all_boxes = [tuple(item["box_xyxy"]) for item in record["all_annotations"]]

            # Exact ground-truth crops are always included. Train receives two
            # deterministic padded variants; validation receives one.
            for index, box in enumerate(crack_boxes):
                fractions = (0.05, 0.15) if args.split == "train" else (0.10,)
                for variant, fraction in enumerate(fractions):
                    crop_box = pad_box(box, width, height, fraction)
                    name = crop_name(record["image_id"], f"gt{index}", variant)
                    target = args.output / args.split / "crack" / name
                    crop_hash = save_crop(image, crop_box, target)
                    records.append(
                        {
                            "split": args.split,
                            "label": 1,
                            "source_kind": "ground_truth_crack",
                            "image_id": record["image_id"],
                            "box_xyxy": crop_box,
                            "path": str(target.resolve()),
                            "sha256": crop_hash,
                        }
                    )

            # The same low-threshold proposals later used for evaluation supply
            # negatives. They are negative only when separated from every crack.
            boxes = prediction.boxes.xyxy.detach().cpu().tolist()
            confidences = prediction.boxes.conf.detach().cpu().tolist()
            proposal_positive_index = 0
            hard_negative_index = 0
            for box, confidence in zip(boxes, confidences, strict=True):
                clipped = clip_proposal_or_none(box, width, height)
                if clipped is None:
                    skipped_empty_proposals += 1
                    continue
                max_crack_iou = max(
                    (box_iou(clipped, target) for target in crack_boxes), default=0.0
                )
                if max_crack_iou >= 0.50:
                    if proposal_positive_index < 10:
                        crop_box = pad_box(clipped, width, height, 0.10)
                        name = crop_name(record["image_id"], "proposal-pos", proposal_positive_index)
                        target = args.output / args.split / "crack" / name
                        crop_hash = save_crop(image, crop_box, target)
                        records.append(
                            {
                                "split": args.split,
                                "label": 1,
                                "source_kind": "matched_proposal_positive",
                                "image_id": record["image_id"],
                                "box_xyxy": crop_box,
                                "proposal_confidence": float(confidence),
                                "max_crack_iou": max_crack_iou,
                                "path": str(target.resolve()),
                                "sha256": crop_hash,
                            }
                        )
                        proposal_positive_index += 1
                    continue
                if max_crack_iou > 0.05:
                    continue
                if hard_negative_index < 20:
                    crop_box = pad_box(clipped, width, height, 0.10)
                    name = crop_name(record["image_id"], "proposal-neg", hard_negative_index)
                    target = args.output / args.split / "background" / name
                    crop_hash = save_crop(image, crop_box, target)
                    records.append(
                        {
                            "split": args.split,
                            "label": 0,
                            "source_kind": "proposal_hard_negative",
                            "image_id": record["image_id"],
                            "box_xyxy": crop_box,
                            "proposal_confidence": float(confidence),
                            "max_crack_iou": max_crack_iou,
                            "path": str(target.resolve()),
                            "sha256": crop_hash,
                        }
                    )
                    hard_negative_index += 1

            # Pothole and patch annotations are explicit confounders.
            background_annotations = [
                item for item in record["all_annotations"] if item["category"] in {"Pothole", "Patch"}
            ]
            for index, item in enumerate(background_annotations):
                crop_box = pad_box(item["box_xyxy"], width, height, 0.10)
                if any(boxes_overlap(crop_box, crack_box) for crack_box in crack_boxes):
                    skipped_overlapping_distress += 1
                    continue
                name = crop_name(record["image_id"], "distress-neg", index)
                target = args.output / args.split / "background" / name
                crop_hash = save_crop(image, crop_box, target)
                records.append(
                    {
                        "split": args.split,
                        "label": 0,
                        "source_kind": f"annotated_{item['category'].lower()}",
                        "image_id": record["image_id"],
                        "box_xyxy": crop_box,
                        "path": str(target.resolve()),
                        "sha256": crop_hash,
                    }
                )

            # Two broad road-background crops prevent the classifier from seeing
            # only detector-specific false positives. Reject overlap with any label.
            random_index = 0
            attempts = 0
            while random_index < 2 and attempts < 200:
                attempts += 1
                crop_width = rng.uniform(0.20, 0.45) * width
                crop_height = rng.uniform(0.20, 0.45) * height
                x1 = rng.uniform(0, max(0.0, width - crop_width))
                y1 = rng.uniform(0, max(0.0, height - crop_height))
                crop_box = (x1, y1, x1 + crop_width, y1 + crop_height)
                if any(boxes_overlap(crop_box, target) for target in all_boxes):
                    continue
                name = crop_name(record["image_id"], "road-neg", random_index)
                target = args.output / args.split / "background" / name
                crop_hash = save_crop(image, crop_box, target)
                records.append(
                    {
                        "split": args.split,
                        "label": 0,
                        "source_kind": "random_road_background",
                        "image_id": record["image_id"],
                        "box_xyxy": crop_box,
                        "path": str(target.resolve()),
                        "sha256": crop_hash,
                    }
                )
                random_index += 1
            if random_index != 2:
                raise RuntimeError(
                    f"could not mine two annotation-free road crops for {record['image_id']}"
                )

    summary = {
        "protocol": PROTOCOL,
        "split": args.split,
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": sha256_file(args.manifest),
        "data_lock": str(args.data_lock.resolve()),
        "data_lock_sha256": sha256_file(args.data_lock),
        "workbook_sha256": payload["workbook_sha256"],
        "proposer": str(args.proposer.resolve()),
        "proposer_sha256": proposer_hash,
        "proposer_receipt": str(args.proposer_receipt.resolve()),
        "proposer_receipt_sha256": sha256_file(args.proposer_receipt),
        "run_config_sha256": proposer_receipt["run_config_sha256"],
        "seed": 20261008,
        "proposal_confidence_minimum": 0.001,
        "proposal_positive_min_crack_iou": 0.50,
        "hard_negative_max_crack_iou": 0.05,
        "crops": len(records),
        "positive_crops": sum(record["label"] == 1 for record in records),
        "negative_crops": sum(record["label"] == 0 for record in records),
        "skipped_overlapping_distress_annotations": skipped_overlapping_distress,
        "skipped_empty_proposals": skipped_empty_proposals,
        "records": records,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / f"crop_manifest_{args.split}.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in summary.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
