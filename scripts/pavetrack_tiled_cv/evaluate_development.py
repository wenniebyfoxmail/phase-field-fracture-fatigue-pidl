#!/usr/bin/env python3
"""Evaluate the repaired route with a validation/test information firewall."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from audit_s01_e001 import maximum_match_count
from contracts import validate_data_lock, validate_tile_manifest_contract
from geometry import Candidate, deterministic_nms, tile_origins, to_full_image


COMMON_DIR = Path(__file__).resolve().parents[1] / "pavetrack_cv"
sys.path.insert(0, str(COMMON_DIR))

from common import (  # noqa: E402
    Detection,
    clip_proposal_or_none,
    frozen_ultralytics_device,
    pad_box,
    recall_at_fp_per_image,
    sha256_file,
    validate_proposer_checkpoint,
    validate_reranker_checkpoint,
)


PROTOCOL = "S01-E002-v1"


def oracle_coverage(
    proposals: list[dict], targets: dict[str, list], image_locations: dict[str, str]
) -> dict:
    proposals_by_image: dict[str, list] = defaultdict(list)
    for proposal in proposals:
        proposals_by_image[proposal["image_id"]].append(proposal["box_xyxy"])
    rows = []
    for location in sorted(set(image_locations.values())):
        image_ids = [key for key, value in image_locations.items() if value == location]
        target_count = sum(len(targets[image_id]) for image_id in image_ids)
        covered = sum(
            maximum_match_count(targets[image_id], proposals_by_image[image_id])
            for image_id in image_ids
        )
        rows.append(
            {
                "location": location,
                "targets": target_count,
                "covered": covered,
                "recall": covered / target_count if target_count else None,
            }
        )
    recalls = [row["recall"] for row in rows if row["recall"] is not None]
    return {
        "macro_location_recall": sum(recalls) / len(recalls) if recalls else None,
        "locations": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--tile-manifest", type=Path, required=True)
    parser.add_argument("--data-lock", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--baseline-proposer", type=Path, required=True)
    parser.add_argument("--tiled-proposer", type=Path, required=True)
    parser.add_argument("--tiled-proposer-receipt", type=Path, required=True)
    parser.add_argument("--reranker", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=("validation", "test"), required=True)
    parser.add_argument("--test-authorization", type=Path)
    parser.add_argument("--validation-evaluation", type=Path)
    parser.add_argument("--detector-device", default="1")
    parser.add_argument("--classifier-device", default="cuda:1")
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    lock = json.loads(args.data_lock.read_text(encoding="utf-8"))
    validate_data_lock(lock)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    tile_manifest = json.loads(args.tile_manifest.read_text(encoding="utf-8"))
    if config.get("protocol") != PROTOCOL:
        raise ValueError("run config has the wrong protocol")
    if manifest.get("protocol") != PROTOCOL:
        raise ValueError("evaluation manifest has the wrong protocol")
    if manifest.get("workbook_sha256") != lock.get("workbook_sha256"):
        raise ValueError("manifest workbook differs from data lock")
    if manifest.get("data_lock_sha256") != sha256_file(args.data_lock):
        raise ValueError("manifest differs from data lock")
    if manifest.get("run_config_sha256") != sha256_file(args.config):
        raise ValueError("manifest differs from run config")
    validate_tile_manifest_contract(
        tile_manifest,
        data_lock_sha256=sha256_file(args.data_lock),
        run_config_sha256=sha256_file(args.config),
        workbook_sha256=lock["workbook_sha256"],
        source_manifest_sha256=(
            sha256_file(args.manifest) if args.split == "validation" else None
        ),
    )
    authorization = None
    if args.split == "validation":
        if set(manifest.get("splits", ())) != {"train", "validation"}:
            raise ValueError("validation evaluation refuses any non-development split")
        expected_locations = set(lock["validation_locations"])
    else:
        if manifest.get("splits") != ["test"]:
            raise ValueError("confirmatory evaluation requires a test-only manifest")
        if args.test_authorization is None or args.validation_evaluation is None:
            raise ValueError("confirmatory evaluation requires frozen authorization and validation")
        authorization = json.loads(args.test_authorization.read_text(encoding="utf-8"))
        expected_authorization = {
            "protocol": PROTOCOL,
            "status": "authorized_after_model_and_validation_freeze",
            "data_lock_sha256": sha256_file(args.data_lock),
            "run_config_sha256": sha256_file(args.config),
            "baseline_proposer_sha256": sha256_file(args.baseline_proposer),
            "tiled_proposer_sha256": sha256_file(args.tiled_proposer),
            "tiled_proposer_receipt_sha256": sha256_file(args.tiled_proposer_receipt),
            "reranker_sha256": sha256_file(args.reranker),
            "validation_evaluation_sha256": sha256_file(args.validation_evaluation),
            "tile_manifest_sha256": sha256_file(args.tile_manifest),
        }
        for field, expected in expected_authorization.items():
            if authorization.get(field) != expected:
                raise ValueError(f"test authorization mismatch at {field}")
        if manifest.get("test_authorization_sha256") != sha256_file(args.test_authorization):
            raise ValueError("test manifest differs from authorization")
        expected_locations = set(lock["confirmatory_test_locations"])
    records = [record for record in manifest["records"] if record["split"] == args.split]
    observed = {str(record["reid"]) for record in records}
    if observed != expected_locations:
        raise ValueError(f"{args.split} locations differ from data lock")
    for record in records:
        if sha256_file(Path(record["prepared_image"])) != record["prepared_image_sha256"]:
            raise ValueError(f"prepared image content hash mismatch: {record['prepared_image']}")

    import torch
    from PIL import Image
    from torchvision import models, transforms
    from ultralytics import YOLO

    if args.detector_device != args.classifier_device.removeprefix("cuda:"):
        raise ValueError("detector and classifier must use the same frozen GPU")
    device = frozen_ultralytics_device(config, args.classifier_device)
    validate_proposer_checkpoint(args.baseline_proposer, config)
    validate_proposer_checkpoint(args.tiled_proposer, config)
    if sha256_file(args.baseline_proposer) != config["baseline_reuse"]["checkpoint_sha256"]:
        raise ValueError("baseline proposer differs from frozen S01-E001 checkpoint")
    receipt = json.loads(args.tiled_proposer_receipt.read_text(encoding="utf-8"))
    if receipt.get("protocol") != PROTOCOL:
        raise ValueError("tiled proposer receipt has the wrong protocol")
    if receipt.get("best_model_sha256") != sha256_file(args.tiled_proposer):
        raise ValueError("tiled proposer differs from its receipt")
    receipt_contract = {
        "run_config_sha256": sha256_file(args.config),
        "data_lock_sha256": sha256_file(args.data_lock),
        "workbook_sha256": lock["workbook_sha256"],
        "tile_manifest_sha256": sha256_file(args.tile_manifest),
        "development_manifest_sha256": tile_manifest["source_manifest_sha256"],
    }
    for field, expected in receipt_contract.items():
        if receipt.get(field) != expected:
            raise ValueError(f"tiled proposer receipt mismatch at {field}")
    expected_reranker_hash = config["reranker_reuse"]["checkpoint_sha256"]
    if sha256_file(args.reranker) != expected_reranker_hash:
        raise ValueError("reranker differs from frozen S01-E001 checkpoint")
    checkpoint = validate_reranker_checkpoint(args.reranker)

    baseline = YOLO(str(args.baseline_proposer.resolve()))
    tiled = YOLO(str(args.tiled_proposer.resolve()))
    classifier = models.mobilenet_v3_small(weights=None)
    classifier.classifier[-1] = torch.nn.Linear(classifier.classifier[-1].in_features, 2)
    classifier.load_state_dict(checkpoint["state_dict"])
    classifier.to(device).eval()
    transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )
    tile_config = config["tile"]
    proposer_config = config["proposer"]
    targets = {record["image_id"]: record["crack_boxes_xyxy"] for record in records}
    image_locations = {record["image_id"]: str(record["reid"]) for record in records}
    baseline_rows = []
    repaired_rows = []

    baseline_predictions = baseline.predict(
        source=[record["prepared_image"] for record in records],
        imgsz=int(config["baseline_reuse"]["image_size"]),
        conf=float(config["baseline_reuse"]["proposal_confidence_minimum"]),
        iou=float(config["baseline_reuse"]["nms_iou"]),
        max_det=int(config["baseline_reuse"]["maximum_detections_per_image"]),
        device=device,
        stream=True,
        verbose=False,
    )
    for record, prediction in zip(records, baseline_predictions, strict=True):
        for box, score in zip(
            prediction.boxes.xyxy.detach().cpu().tolist(),
            prediction.boxes.conf.detach().cpu().tolist(),
            strict=True,
        ):
            clipped = clip_proposal_or_none(box, int(record["width"]), int(record["height"]))
            if clipped is not None:
                baseline_rows.append(
                    {
                        "image_id": record["image_id"],
                        "reid": str(record["reid"]),
                        "box_xyxy": clipped,
                        "proposer_confidence": float(score),
                    }
                )

    with torch.inference_mode():
        for record in records:
            with Image.open(record["prepared_image"]) as opened:
                image = opened.convert("RGB")
                width, height = image.size
                tile_images = []
                origins = []
                for top in tile_origins(height, int(tile_config["size"]), int(tile_config["stride"])):
                    for left in tile_origins(width, int(tile_config["size"]), int(tile_config["stride"])):
                        tile_images.append(
                            image.crop(
                                (
                                    left,
                                    top,
                                    left + int(tile_config["size"]),
                                    top + int(tile_config["size"]),
                                )
                            )
                        )
                        origins.append((left, top))
                predictions = tiled.predict(
                    source=tile_images,
                    imgsz=int(proposer_config["image_size"]),
                    conf=float(proposer_config["proposal_confidence_minimum"]),
                    iou=float(proposer_config["within_tile_nms_iou"]),
                    max_det=int(proposer_config["maximum_detections_per_tile"]),
                    device=device,
                    verbose=False,
                )
                candidates = []
                for (left, top), prediction in zip(origins, predictions, strict=True):
                    for box, score in zip(
                        prediction.boxes.xyxy.detach().cpu().tolist(),
                        prediction.boxes.conf.detach().cpu().tolist(),
                        strict=True,
                    ):
                        mapped = to_full_image(box, left, top, width, height)
                        if mapped is not None:
                            candidates.append(Candidate(mapped, float(score), left, top))
                candidates = deterministic_nms(
                    candidates,
                    float(tile_config["cross_tile_nms_iou"]),
                    int(tile_config["maximum_reconstructed_candidates_per_image"]),
                )
                crops = [
                    transform(
                        image.crop(
                            tuple(
                                int(round(value))
                                for value in pad_box(candidate.box, width, height, 0.10)
                            )
                        )
                    )
                    for candidate in candidates
                ]
                probabilities = []
                for start in range(0, len(crops), 128):
                    batch = torch.stack(crops[start : start + 128]).to(device)
                    probabilities.extend(
                        classifier(batch).softmax(dim=1)[:, 1].cpu().tolist()
                    )
                for candidate, probability in zip(candidates, probabilities, strict=True):
                    repaired_rows.append(
                        {
                            "image_id": record["image_id"],
                            "reid": str(record["reid"]),
                            "box_xyxy": candidate.box,
                            "proposer_confidence": candidate.score,
                            "reranker_crack_probability": float(probability),
                            "geometric_mean": math.sqrt(candidate.score * float(probability)),
                        }
                    )

    baseline_detections = [
        Detection(row["image_id"], row["reid"], row["box_xyxy"], row["proposer_confidence"])
        for row in baseline_rows
    ]
    baseline_metrics = recall_at_fp_per_image(baseline_detections, targets, image_locations)
    score_fields = {
        "proposer_confidence": "proposer_confidence",
        "sqrt(proposer_confidence * reranker_crack_probability)": "geometric_mean",
        "reranker_crack_probability": "reranker_crack_probability",
    }
    if args.split == "validation":
        score_names = config["reranker_reuse"]["score_candidates"]
    else:
        score_names = [authorization["selected_score"]]
    repaired_metrics = {}
    for score_name in score_names:
        field = score_fields[score_name]
        detections = [
            Detection(row["image_id"], row["reid"], row["box_xyxy"], row[field])
            for row in repaired_rows
        ]
        repaired_metrics[score_name] = recall_at_fp_per_image(
            detections, targets, image_locations
        )
    if args.split == "validation":
        candidate_order = config["reranker_reuse"]["score_candidates"]
        selected_score = max(
            candidate_order,
            key=lambda name: (
                repaired_metrics[name]["macro_location_recall"],
                -candidate_order.index(name),
            ),
        )
    else:
        selected_score = authorization["selected_score"]
    baseline_oracle = oracle_coverage(baseline_rows, targets, image_locations)
    repaired_oracle = oracle_coverage(repaired_rows, targets, image_locations)
    repaired_value = repaired_metrics[selected_score]["macro_location_recall"]
    baseline_value = baseline_metrics["macro_location_recall"]
    primary_delta = repaired_value - baseline_value
    coverage_delta = (
        repaired_oracle["macro_location_recall"]
        - baseline_oracle["macro_location_recall"]
    )
    payload = {
        "protocol": PROTOCOL,
        "split": args.split,
        "manifest_sha256": sha256_file(args.manifest),
        "tile_manifest_sha256": sha256_file(args.tile_manifest),
        "data_lock_sha256": sha256_file(args.data_lock),
        "run_config_sha256": sha256_file(args.config),
        "baseline_proposer_sha256": sha256_file(args.baseline_proposer),
        "tiled_proposer_sha256": sha256_file(args.tiled_proposer),
        "tiled_proposer_receipt_sha256": sha256_file(args.tiled_proposer_receipt),
        "reranker_sha256": sha256_file(args.reranker),
        "baseline": baseline_metrics,
        "baseline_oracle_coverage": baseline_oracle,
        "repaired_score_candidates": repaired_metrics,
        "selected_score": selected_score,
        "repaired_oracle_coverage": repaired_oracle,
        "primary_delta_macro_location_R_at_1FP_per_image": primary_delta,
        "oracle_coverage_delta_macro_location_recall": coverage_delta,
        "primary_pass": (
            None
            if args.split == "validation"
            else primary_delta
            >= float(authorization["primary_delta_to_pass"])
            and coverage_delta >= float(authorization["coverage_delta_to_pass"])
        ),
        "targets": targets,
        "image_locations": image_locations,
        "test_authorization_sha256": (
            sha256_file(args.test_authorization) if args.test_authorization else None
        ),
        "baseline_proposals": baseline_rows,
        "repaired_proposals": repaired_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                key: value
                for key, value in payload.items()
                if key not in {"baseline_proposals", "repaired_proposals"}
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
