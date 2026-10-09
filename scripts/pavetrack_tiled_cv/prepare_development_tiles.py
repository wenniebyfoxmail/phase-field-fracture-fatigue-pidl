#!/usr/bin/env python3
"""Build the frozen S01-E002 train/validation tiled detector dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from geometry import clip_target_to_tile, tile_origins
from contracts import validate_data_lock


PROTOCOL = "S01-E002-v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def yolo_line(box: tuple[float, float, float, float], tile_size: int) -> str:
    x1, y1, x2, y2 = box
    return (
        f"0 {(x1 + x2) / (2 * tile_size):.8f} "
        f"{(y1 + y2) / (2 * tile_size):.8f} "
        f"{(x2 - x1) / tile_size:.8f} {(y2 - y1) / tile_size:.8f}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-lock", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        from PIL import Image
        import yaml
    except ImportError as error:
        raise SystemExit(f"runtime dependency missing: {error}") from error

    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("protocol") != PROTOCOL:
        raise ValueError("run config has the wrong protocol")
    tile_config = config["tile"]
    tile_size = int(tile_config["size"])
    stride = int(tile_config["stride"])
    ratio = float(tile_config["negative_to_positive_training_tile_ratio"])
    source = json.loads(args.manifest.read_text(encoding="utf-8"))
    data_lock = json.loads(args.data_lock.read_text(encoding="utf-8"))
    validate_data_lock(data_lock)
    if set(source.get("splits", ())) != {"train", "validation"}:
        raise ValueError("development tiling requires exactly train and validation splits")
    if source.get("protocol") != PROTOCOL:
        raise ValueError("development manifest has the wrong protocol")
    if source.get("data_lock_sha256") != sha256_file(args.data_lock):
        raise ValueError("development manifest is not bound to this data lock")
    if source.get("run_config_sha256") != sha256_file(args.config):
        raise ValueError("development manifest is not bound to this run config")
    if source.get("workbook_sha256") != data_lock.get("workbook_sha256"):
        raise ValueError("development manifest is not bound to the locked workbook")
    for split, key in (("train", "train_locations"), ("validation", "validation_locations")):
        observed = {str(record["reid"]) for record in source["records"] if record["split"] == split}
        if observed != set(data_lock[key]):
            raise ValueError(f"development {split} locations differ from data lock")

    candidates: dict[str, dict[str, list[dict]]] = {
        split: {"positive": [], "negative": []}
        for split in ("train", "validation")
    }
    for record in source["records"]:
        split = str(record["split"])
        if split not in candidates:
            raise ValueError(f"forbidden split in development manifest: {split}")
        image_path = Path(record["prepared_image"])
        if sha256_file(image_path) != record["prepared_image_sha256"]:
            raise ValueError(f"prepared image content hash mismatch: {image_path}")
        width, height = int(record["width"]), int(record["height"])
        for top in tile_origins(height, tile_size, stride):
            for left in tile_origins(width, tile_size, stride):
                boxes = [
                    clipped
                    for box in record["crack_boxes_xyxy"]
                    if (
                        clipped := clip_target_to_tile(
                            box,
                            left,
                            top,
                            tile_size,
                            float(tile_config["minimum_target_intersection_fraction"]),
                            float(tile_config["minimum_clipped_side_pixels"]),
                        )
                    )
                    is not None
                ]
                item = {
                    "split": split,
                    "image_id": record["image_id"],
                    "reid": record["reid"],
                    "source_image": str(image_path.resolve()),
                    "source_image_sha256": record["prepared_image_sha256"],
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height,
                    "boxes_xyxy_in_tile": boxes,
                }
                candidates[split]["positive" if boxes else "negative"].append(item)

    rng = random.Random(int(config["seed"]))
    selected: dict[str, list[dict]] = {}
    for split, groups in candidates.items():
        negatives = groups["negative"]
        if split == "train":
            maximum = round(len(groups["positive"]) * ratio)
            negatives = rng.sample(negatives, min(maximum, len(negatives)))
        selected[split] = sorted(
            groups["positive"] + negatives,
            key=lambda row: (row["image_id"], row["top"], row["left"]),
        )

    output_records = []
    for split, items in selected.items():
        image_dir = args.output / "images" / split
        label_dir = args.output / "labels" / split
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        for item in items:
            stem = Path(item["image_id"]).stem
            name = f"{stem}__x{item['left']}_y{item['top']}.jpg"
            image_target = image_dir / name
            label_target = label_dir / f"{Path(name).stem}.txt"
            with Image.open(item["source_image"]) as opened:
                tile = opened.convert("RGB").crop(
                    (
                        item["left"],
                        item["top"],
                        item["left"] + tile_size,
                        item["top"] + tile_size,
                    )
                )
                tile.save(image_target, quality=95, subsampling=0)
            label_target.write_text(
                "\n".join(yolo_line(box, tile_size) for box in item["boxes_xyxy_in_tile"])
                + ("\n" if item["boxes_xyxy_in_tile"] else ""),
                encoding="utf-8",
            )
            output_records.append(
                {
                    **item,
                    "tile_image": str(image_target.resolve()),
                    "tile_image_sha256": sha256_file(image_target),
                    "tile_label": str(label_target.resolve()),
                    "tile_label_sha256": sha256_file(label_target),
                }
            )

    args.output.mkdir(parents=True, exist_ok=True)
    payload = {
        "protocol": PROTOCOL,
        "source_manifest": str(args.manifest.resolve()),
        "source_manifest_sha256": sha256_file(args.manifest),
        "data_lock_sha256": sha256_file(args.data_lock),
        "workbook_sha256": source["workbook_sha256"],
        "run_config_sha256": sha256_file(args.config),
        "tile_size": tile_size,
        "stride": stride,
        "counts": {split: len(rows) for split, rows in selected.items()},
        "positive_counts": {
            split: len(groups["positive"]) for split, groups in candidates.items()
        },
        "records": output_records,
    }
    (args.output / "tile_manifest_train_validation.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    dataset = {
        "path": str(args.output.resolve()),
        "train": "images/train",
        "val": "images/validation",
        "names": {0: "Crack"},
    }
    (args.output / "dataset_train_validation.yaml").write_text(
        yaml.safe_dump(dataset, sort_keys=False), encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in payload.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
