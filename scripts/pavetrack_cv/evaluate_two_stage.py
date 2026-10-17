#!/usr/bin/env python3
"""Evaluate identical proposals under raw and frozen two-stage scores."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from common import (
    Detection,
    PROTOCOL,
    clip_proposal_or_none,
    frozen_ultralytics_device,
    load_data_lock,
    pad_box,
    recall_at_fp_per_image,
    sha256_file,
    validate_evaluation_membership,
    validate_prepared_record_hashes,
    validate_proposer_checkpoint,
    validate_reranker_checkpoint,
    verify_test_authorization_chain,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--proposer", type=Path, required=True)
    parser.add_argument("--reranker", type=Path, required=True)
    parser.add_argument("--proposer-receipt", type=Path, required=True)
    parser.add_argument("--data-lock", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=("validation", "test"), required=True)
    parser.add_argument("--detector-device", default="1")
    parser.add_argument("--classifier-device", default="cuda:1")
    parser.add_argument("--test-authorization", type=Path)
    parser.add_argument("--validation-evaluation", type=Path)
    args = parser.parse_args()

    import torch
    from PIL import Image
    from torchvision import models, transforms
    from ultralytics import YOLO

    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    required_manifest = {
        "protocol",
        "data_lock_sha256",
        "workbook_sha256",
        "splits",
        "locations",
        "records",
        "test_authorization_sha256",
    }
    missing_manifest = required_manifest - set(payload)
    if missing_manifest:
        raise ValueError(f"evaluation manifest lacks fields: {sorted(missing_manifest)}")
    if payload["protocol"] != PROTOCOL:
        raise ValueError("evaluation manifest has the wrong protocol")
    lock = load_data_lock(args.data_lock)
    if payload["data_lock_sha256"] != sha256_file(args.data_lock):
        raise ValueError("evaluation manifest is not bound to this data lock")
    if payload["workbook_sha256"] != lock["workbook_sha256"]:
        raise ValueError("evaluation manifest is not bound to the locked workbook")
    validate_prepared_record_hashes(payload)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("protocol") != PROTOCOL:
        raise ValueError("run config has the wrong protocol")
    if payload.get("run_config_sha256") != sha256_file(args.config):
        raise ValueError("evaluation manifest was prepared under a different run config")
    if args.detector_device != args.classifier_device.removeprefix("cuda:"):
        raise ValueError("detector and classifier must use the same frozen GPU")
    device = frozen_ultralytics_device(config, args.classifier_device)
    split_records = validate_evaluation_membership(payload, lock, args.split)
    if args.split == "test" and payload["splits"] != ["test"]:
        raise ValueError("confirmatory evaluation requires a test-only manifest")
    if args.split == "validation" and (
        "validation" not in payload["splits"] or "test" in payload["splits"]
    ):
        raise ValueError("validation evaluation requires validation and refuses any test record")
    if args.split == "test":
        if args.test_authorization is None:
            raise ValueError("confirmatory evaluation requires --test-authorization")
        if args.validation_evaluation is None:
            raise ValueError("confirmatory evaluation requires --validation-evaluation")
        authorization = verify_test_authorization_chain(
            args.test_authorization,
            args.data_lock,
            args.proposer,
            args.reranker,
            args.validation_evaluation,
            args.proposer_receipt,
            args.config,
        )
        frozen_score = "sqrt(proposer_confidence * reranker_crack_probability)"
        frozen_metric = "macro-location R@1FP/image, one global threshold, IoU>=0.50"
        if authorization.get("scoring_rule") != frozen_score:
            raise ValueError("test authorization has a different scoring rule")
        if authorization.get("primary_metric") != frozen_metric:
            raise ValueError("test authorization has a different primary metric")
        if float(authorization.get("primary_pass_delta")) != 0.10:
            raise ValueError("test authorization has a different pass threshold")
        if authorization.get("proposer_sha256") != sha256_file(args.proposer):
            raise ValueError("proposer differs from frozen test authorization")
        if authorization.get("reranker_sha256") != sha256_file(args.reranker):
            raise ValueError("reranker differs from frozen test authorization")
        if payload.get("test_authorization_sha256") != sha256_file(args.test_authorization):
            raise ValueError("test manifest is not bound to this authorization")
        if payload["data_lock_sha256"] != authorization.get("data_lock_sha256"):
            raise ValueError("test manifest data lock differs from authorization")
        if payload["workbook_sha256"] != authorization.get("workbook_sha256"):
            raise ValueError("test manifest workbook differs from authorization")
    records = split_records
    if not records:
        raise ValueError(f"manifest contains no records for {args.split}")

    validate_proposer_checkpoint(args.proposer, config)
    detector = YOLO(str(args.proposer.resolve()))
    classifier = models.mobilenet_v3_small(weights=None)
    classifier.classifier[-1] = torch.nn.Linear(classifier.classifier[-1].in_features, 2)
    checkpoint = torch.load(args.reranker, map_location="cpu", weights_only=True)
    if checkpoint["class_to_idx"] != {"background": 0, "crack": 1}:
        raise ValueError(f"unexpected checkpoint mapping: {checkpoint['class_to_idx']}")
    lineage = checkpoint.get("lineage")
    if not isinstance(lineage, dict):
        raise ValueError("reranker checkpoint lacks lineage")
    proposer_hash = sha256_file(args.proposer)
    reranker_hash = sha256_file(args.reranker)
    proposer_receipt_hash = sha256_file(args.proposer_receipt)
    proposer_receipt = json.loads(args.proposer_receipt.read_text(encoding="utf-8"))
    if proposer_receipt.get("protocol") != PROTOCOL:
        raise ValueError("proposer receipt has the wrong protocol")
    if proposer_receipt.get("best_model_sha256") != proposer_hash:
        raise ValueError("proposer receipt is not bound to this proposer")
    if proposer_receipt.get("development_manifest_sha256") != lineage.get(
        "manifest_sha256"
    ):
        raise ValueError("proposer and reranker used different development manifests")
    if lineage.get("proposer_receipt_sha256") != proposer_receipt_hash:
        raise ValueError("reranker used a different proposer receipt")
    if lineage.get("proposer_sha256") != proposer_hash:
        raise ValueError("reranker was mined with a different proposer")
    if lineage.get("data_lock_sha256") != payload["data_lock_sha256"]:
        raise ValueError("reranker data lock differs from evaluation manifest")
    if lineage.get("workbook_sha256") != payload["workbook_sha256"]:
        raise ValueError("reranker workbook differs from evaluation manifest")
    if args.split == "validation" and lineage.get("manifest_sha256") != sha256_file(args.manifest):
        raise ValueError("reranker development manifest differs from validation manifest")
    if args.split == "test" and lineage.get("manifest_sha256") != authorization.get(
        "validation_manifest_sha256"
    ):
        raise ValueError("reranker development lineage differs from frozen authorization")
    validate_reranker_checkpoint(args.reranker, lineage)
    classifier.load_state_dict(checkpoint["state_dict"])
    classifier.to(device).eval()
    transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )

    predictions = detector.predict(
        source=[record["prepared_image"] for record in records],
        imgsz=1280,
        conf=0.001,
        iou=0.70,
        max_det=300,
        device=device,
        stream=True,
        verbose=False,
    )
    raw_detections = []
    fused_detections = []
    proposal_rows = []
    skipped_empty_proposals = 0
    targets = {}
    image_locations = {}
    with torch.inference_mode():
        for record, prediction in zip(records, predictions, strict=True):
            image_id = record["image_id"]
            location = record["reid"]
            targets[image_id] = record["crack_boxes_xyxy"]
            image_locations[image_id] = location
            with Image.open(record["prepared_image"]) as opened:
                image = opened.convert("RGB")
                width, height = image.size
                boxes = prediction.boxes.xyxy.detach().cpu().tolist()
                confidences = prediction.boxes.conf.detach().cpu().tolist()
                crops = []
                clipped_boxes = []
                retained_confidences = []
                for box, confidence in zip(boxes, confidences, strict=True):
                    clipped = clip_proposal_or_none(box, width, height)
                    if clipped is None:
                        skipped_empty_proposals += 1
                        continue
                    clipped_boxes.append(clipped)
                    retained_confidences.append(confidence)
                    crops.append(transform(image.crop(tuple(int(round(v)) for v in pad_box(clipped, width, height, 0.10)))))
                if crops:
                    batch = torch.stack(crops).to(device)
                    crack_probabilities = classifier(batch).softmax(dim=1)[:, 1].cpu().tolist()
                else:
                    crack_probabilities = []
            for box, proposer_score, crack_probability in zip(
                clipped_boxes, retained_confidences, crack_probabilities, strict=True
            ):
                fused_score = math.sqrt(float(proposer_score) * float(crack_probability))
                raw_detections.append(
                    Detection(image_id, location, box, float(proposer_score))
                )
                fused_detections.append(Detection(image_id, location, box, fused_score))
                proposal_rows.append(
                    {
                        "image_id": image_id,
                        "reid": location,
                        "box_xyxy": box,
                        "proposer_score": float(proposer_score),
                        "reranker_crack_probability": float(crack_probability),
                        "two_stage_score": fused_score,
                    }
                )

    raw_metrics = recall_at_fp_per_image(raw_detections, targets, image_locations)
    two_stage_metrics = recall_at_fp_per_image(fused_detections, targets, image_locations)
    raw_value = raw_metrics["macro_location_recall"]
    fused_value = two_stage_metrics["macro_location_recall"]
    delta = None if raw_value is None or fused_value is None else fused_value - raw_value
    summary = {
        "protocol": PROTOCOL,
        "split": args.split,
        "manifest_sha256": sha256_file(args.manifest),
        "validation_manifest_sha256": lineage["manifest_sha256"],
        "data_lock_sha256": payload["data_lock_sha256"],
        "workbook_sha256": payload["workbook_sha256"],
        "proposer_sha256": proposer_hash,
        "proposer_receipt_sha256": proposer_receipt_hash,
        "run_config_sha256": lineage["run_config_sha256"],
        "reranker_sha256": reranker_hash,
        "reranker_lineage": lineage,
        "same_proposal_count": len(proposal_rows),
        "skipped_empty_proposals": skipped_empty_proposals,
        "proposer": raw_metrics,
        "two_stage": two_stage_metrics,
        "primary_delta_macro_location_R_at_1FP_per_image": delta,
        "primary_pass": None if args.split != "test" or delta is None else delta >= 0.10,
        "frozen_two_stage_score": "sqrt(proposer_confidence * reranker_crack_probability)",
        "test_authorization": (
            str(args.test_authorization.resolve()) if args.test_authorization else None
        ),
        "test_authorization_sha256": (
            sha256_file(args.test_authorization) if args.test_authorization else None
        ),
        "validation_evaluation_sha256": (
            sha256_file(args.validation_evaluation) if args.validation_evaluation else None
        ),
        "proposals": proposal_rows,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / f"evaluation_{args.split}.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {key: value for key, value in summary.items() if key != "proposals"}, indent=2
        )
    )


if __name__ == "__main__":
    main()
