#!/usr/bin/env python3
"""Prepare only explicitly allowed PaveTrack splits for binary crack detection."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from common import (
    CRACK_CLASSES,
    PROTOCOL,
    clip_xyxy,
    load_data_lock,
    locations_for_splits,
    parse_numeric_list,
    sha256_file,
    validate_producer_runtime,
    verify_test_authorization_chain,
    xywh_to_xyxy,
    xyxy_to_yolo,
)


def find_source(image_roots: list[Path], reid: str, image_name: str) -> Path | None:
    for root in image_roots:
        candidate = root / reid / image_name
        if candidate.is_file():
            return candidate
    return None


def materialize(source: Path, target: Path, mode: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if target.is_symlink() and target.resolve() == source.resolve():
            return
        target.unlink()
    if mode == "copy":
        shutil.copy2(source, target)
    elif mode == "hardlink":
        os.link(source, target)
    elif mode == "symlink":
        target.symlink_to(source.resolve())
    else:
        raise ValueError(mode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--data-lock", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--image-root", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--splits",
        nargs="+",
        choices=("train", "validation", "test"),
        required=True,
    )
    parser.add_argument("--mode", choices=("copy", "hardlink", "symlink"), default="copy")
    parser.add_argument("--test-authorization", type=Path)
    parser.add_argument("--proposer", type=Path)
    parser.add_argument("--reranker", type=Path)
    parser.add_argument("--validation-evaluation", type=Path)
    parser.add_argument("--proposer-receipt", type=Path)
    args = parser.parse_args()

    # A test-only invocation is deliberate and easy to identify in the receipt.
    if "test" in args.splits and set(args.splits) != {"test"}:
        raise ValueError("test must be prepared in a separate test-only invocation")
    if args.splits == ["test"]:
        required_paths = {
            "--test-authorization": args.test_authorization,
            "--proposer": args.proposer,
            "--reranker": args.reranker,
            "--validation-evaluation": args.validation_evaluation,
            "--proposer-receipt": args.proposer_receipt,
        }
        missing_paths = [name for name, value in required_paths.items() if value is None]
        if missing_paths:
            raise ValueError(f"test preparation requires: {', '.join(missing_paths)}")
        authorization = verify_test_authorization_chain(
            args.test_authorization,
            args.data_lock,
            args.proposer,
            args.reranker,
            args.validation_evaluation,
            args.proposer_receipt,
            args.config,
        )

    try:
        import pandas as pd
        from PIL import Image
        import yaml
    except ImportError as error:
        raise SystemExit(f"runtime dependency missing: {error}") from error

    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("protocol") != PROTOCOL:
        raise ValueError("run config has the wrong protocol")
    validate_producer_runtime(config)

    lock = load_data_lock(args.data_lock)
    workbook_hash = sha256_file(args.workbook)
    if workbook_hash != lock["workbook_sha256"]:
        raise ValueError(f"workbook SHA-256 mismatch: {workbook_hash}")
    if args.splits == ["test"] and authorization["workbook_sha256"] != workbook_hash:
        raise ValueError("test authorization is not bound to this workbook")
    selected_locations = locations_for_splits(lock, args.splits)
    split_by_location = {
        location: split
        for split in args.splits
        for location in locations_for_splits(lock, [split])
    }

    frame = pd.read_excel(args.workbook)
    required = {"reid", "img_name", "category", "bbox"}
    missing_columns = required - set(frame.columns)
    if missing_columns:
        raise ValueError(f"workbook lacks columns: {sorted(missing_columns)}")
    frame["reid"] = frame["reid"].astype(str)
    frame = frame[frame["reid"].isin(selected_locations)].copy()

    records = []
    missing_images = []
    for (reid, image_name), rows in frame.groupby(["reid", "img_name"], sort=True):
        source = find_source(args.image_root, reid, image_name)
        if source is None:
            missing_images.append(f"{reid}/{image_name}")
            continue
        with Image.open(source) as image:
            width, height = image.size
        crack_boxes = []
        for row in rows.itertuples(index=False):
            if str(row.category) not in CRACK_CLASSES:
                continue
            box = clip_xyxy(xywh_to_xyxy(parse_numeric_list(row.bbox)), width, height)
            crack_boxes.append(box)

        split = split_by_location[reid]
        prepared_name = f"reid-{reid}__{image_name}"
        image_target = args.output / "images" / split / prepared_name
        label_target = args.output / "labels" / split / f"{Path(prepared_name).stem}.txt"
        materialize(source, image_target, args.mode)
        label_target.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for box in crack_boxes:
            center_x, center_y, box_width, box_height = xyxy_to_yolo(box, width, height)
            lines.append(
                f"0 {center_x:.8f} {center_y:.8f} {box_width:.8f} {box_height:.8f}"
            )
        label_target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        records.append(
            {
                "image_id": prepared_name,
                "reid": reid,
                "split": split,
                "source": str(source.resolve()),
                "prepared_image": str(image_target.resolve()),
                "prepared_image_sha256": sha256_file(image_target),
                "prepared_label": str(label_target.resolve()),
                "prepared_label_sha256": sha256_file(label_target),
                "width": width,
                "height": height,
                "crack_boxes_xyxy": crack_boxes,
                "all_annotations": [
                    {
                        "category": str(row.category),
                        "box_xyxy": clip_xyxy(
                            xywh_to_xyxy(parse_numeric_list(row.bbox)), width, height
                        ),
                    }
                    for row in rows.itertuples(index=False)
                ],
            }
        )

    if missing_images:
        raise FileNotFoundError(
            f"{len(missing_images)} selected images are missing; first={missing_images[0]}"
        )
    observed_locations = {record["reid"] for record in records}
    if observed_locations != selected_locations:
        absent = sorted(selected_locations - observed_locations)
        raise ValueError(f"selected locations have no workbook images: {absent}")

    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "protocol": PROTOCOL,
        "run_config": str(args.config.resolve()),
        "run_config_sha256": sha256_file(args.config),
        "data_lock": str(args.data_lock.resolve()),
        "data_lock_sha256": sha256_file(args.data_lock),
        "workbook": str(args.workbook.resolve()),
        "workbook_sha256": workbook_hash,
        "splits": args.splits,
        "locations": sorted(selected_locations),
        "image_count": len(records),
        "crack_target_count": sum(len(record["crack_boxes_xyxy"]) for record in records),
        "records": records,
        "test_authorization": (
            str(args.test_authorization.resolve()) if args.test_authorization else None
        ),
        "test_authorization_sha256": (
            sha256_file(args.test_authorization) if args.test_authorization else None
        ),
    }
    (args.output / f"manifest_{'_'.join(args.splits)}.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    dataset = {
        "path": str(args.output.resolve()),
        "train": "images/train" if "train" in args.splits else None,
        "val": "images/validation" if "validation" in args.splits else None,
        "test": "images/test" if "test" in args.splits else None,
        "names": {0: "Crack"},
    }
    (args.output / f"dataset_{'_'.join(args.splits)}.yaml").write_text(
        yaml.safe_dump(dataset, sort_keys=False), encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in manifest.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
