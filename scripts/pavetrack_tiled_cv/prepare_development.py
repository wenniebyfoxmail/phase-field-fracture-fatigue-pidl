#!/usr/bin/env python3
"""Prepare only S01-E002 train and validation full-image records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


COMMON_DIR = Path(__file__).resolve().parents[1] / "pavetrack_cv"
sys.path.insert(0, str(COMMON_DIR))

from common import CRACK_CLASSES, clip_xyxy, parse_numeric_list, sha256_file, xywh_to_xyxy  # noqa: E402
from prepare_dataset import find_source, materialize  # noqa: E402
from contracts import validate_data_lock


PROTOCOL = "S01-E002-v1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--data-lock", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--image-root", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("copy", "hardlink", "symlink"), default="copy")
    args = parser.parse_args()

    try:
        import pandas as pd
        from PIL import Image
    except ImportError as error:
        raise SystemExit(f"runtime dependency missing: {error}") from error

    config = json.loads(args.config.read_text(encoding="utf-8"))
    lock = json.loads(args.data_lock.read_text(encoding="utf-8"))
    validate_data_lock(lock)
    if config.get("protocol") != PROTOCOL:
        raise ValueError("run config has the wrong protocol")
    if sha256_file(args.workbook) != lock.get("workbook_sha256"):
        raise ValueError("workbook differs from data lock")
    split_by_location = {
        str(location): split
        for split, key in (("train", "train_locations"), ("validation", "validation_locations"))
        for location in lock[key]
    }
    frame = pd.read_excel(args.workbook)
    required_columns = {"reid", "img_name", "category", "bbox"}
    if not required_columns.issubset(frame.columns):
        raise ValueError("workbook lacks required columns")
    frame["reid"] = frame["reid"].astype(str)
    frame = frame[frame["reid"].isin(split_by_location)].copy()
    records = []
    missing = []
    for (reid, image_name), rows in frame.groupby(["reid", "img_name"], sort=True):
        source = find_source(args.image_root, reid, image_name)
        if source is None:
            missing.append(f"{reid}/{image_name}")
            continue
        with Image.open(source) as image:
            width, height = image.size
        annotations = [
            {
                "category": str(row.category),
                "box_xyxy": clip_xyxy(
                    xywh_to_xyxy(parse_numeric_list(row.bbox)), width, height
                ),
            }
            for row in rows.itertuples(index=False)
        ]
        split = split_by_location[reid]
        prepared_name = f"reid-{reid}__{image_name}"
        target = args.output / "images" / split / prepared_name
        materialize(source, target, args.mode)
        records.append(
            {
                "image_id": prepared_name,
                "reid": reid,
                "split": split,
                "source": str(source.resolve()),
                "prepared_image": str(target.resolve()),
                "prepared_image_sha256": sha256_file(target),
                "width": width,
                "height": height,
                "crack_boxes_xyxy": [
                    row["box_xyxy"]
                    for row in annotations
                    if row["category"] in CRACK_CLASSES
                ],
                "all_annotations": annotations,
            }
        )
    if missing:
        raise FileNotFoundError(f"{len(missing)} selected images are missing; first={missing[0]}")
    if {record["reid"] for record in records} != set(split_by_location):
        raise ValueError("one or more development locations have no workbook image")
    payload = {
        "protocol": PROTOCOL,
        "run_config_sha256": sha256_file(args.config),
        "data_lock_sha256": sha256_file(args.data_lock),
        "workbook_sha256": sha256_file(args.workbook),
        "splits": ["train", "validation"],
        "locations": sorted(split_by_location),
        "image_count": len(records),
        "crack_target_count": sum(len(record["crack_boxes_xyxy"]) for record in records),
        "records": records,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "manifest_train_validation.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in payload.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
