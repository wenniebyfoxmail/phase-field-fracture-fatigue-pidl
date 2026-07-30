#!/usr/bin/env python3
"""Build a provenance-checked, visual-only PaveTrack observation pilot."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


FILENAME_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<time>\d{2}-\d{2}-\d{2})-"
    r"(?P<millisecond>\d{3})-(?P<camera>n?\d+)\.(?:jpg|jpeg)$",
    re.IGNORECASE,
)
CRACK_CATEGORIES = {"Alligator Crack", "Transverse Crack"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_filename(name: str) -> tuple[datetime, str] | None:
    match = FILENAME_RE.match(name)
    if match is None:
        return None
    timestamp = datetime.strptime(
        f"{match.group('date')} {match.group('time')}.{match.group('millisecond')}",
        "%Y-%m-%d %H-%M-%S.%f",
    )
    return timestamp, match.group("camera")


def resolve_pair(root: Path, reid: str, image_name: str) -> tuple[Path, Path]:
    image = root / reid / image_name
    mask = root / "masks_png" / reid / f"{Path(image_name).stem}.png"
    return image, mask


def load_unique_records(manifest: Path) -> tuple[list[dict[str, str]], int]:
    with manifest.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    required = {"reid", "date", "category", "img_name"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"manifest must contain {sorted(required)}")

    unique: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["reid"].strip(), row["img_name"].strip())
        unique.setdefault(key, {key: value.strip() for key, value in row.items()})
    return list(unique.values()), len(rows)


def build_sequences(records: Iterable[dict[str, str]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[tuple[datetime, dict[str, str]]]] = {}
    for record in records:
        parsed = parse_filename(record["img_name"])
        if parsed is None or record["category"] not in CRACK_CATEGORIES:
            continue
        timestamp, camera = parsed
        key = (record["reid"], record["category"], camera)
        groups.setdefault(key, []).append((timestamp, record))

    sequences: list[dict[str, object]] = []
    for (reid, category, camera), items in groups.items():
        items.sort(key=lambda item: item[0])
        span_days = (items[-1][0] - items[0][0]).days
        sequences.append(
            {
                "reid": reid,
                "category": category,
                "camera_suffix": camera,
                "record_count": len(items),
                "span_days": span_days,
                "start_naive": items[0][0].isoformat(timespec="milliseconds"),
                "end_naive": items[-1][0].isoformat(timespec="milliseconds"),
                "items": items,
            }
        )
    return sorted(
        sequences,
        key=lambda row: (int(row["record_count"]), int(row["span_days"])),
        reverse=True,
    )


def evenly_spaced(items: list[tuple[datetime, dict[str, str]]], count: int) -> list[tuple[datetime, dict[str, str]]]:
    if len(items) <= count:
        return items
    indices = np.linspace(0, len(items) - 1, count).round().astype(int)
    return [items[index] for index in sorted(set(indices.tolist()))]


def mask_features(path: Path) -> dict[str, float | int]:
    with Image.open(path) as image:
        array = np.asarray(image.convert("L")) > 0
    height, width = array.shape
    y, x = np.nonzero(array)
    if x.size == 0:
        return {
            "image_width_px": width,
            "image_height_px": height,
            "mask_area_fraction": 0.0,
            "bbox_width_fraction": 0.0,
            "bbox_height_fraction": 0.0,
            "centroid_x_fraction": float("nan"),
            "centroid_y_fraction": float("nan"),
        }
    return {
        "image_width_px": width,
        "image_height_px": height,
        "mask_area_fraction": float(array.mean()),
        "bbox_width_fraction": float((x.max() - x.min() + 1) / width),
        "bbox_height_fraction": float((y.max() - y.min() + 1) / height),
        "centroid_x_fraction": float(x.mean() / width),
        "centroid_y_fraction": float(y.mean() / height),
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty table: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_package(root: Path, out: Path, sequence_count: int, samples_per_sequence: int) -> None:
    manifest = root / "manifest.csv"
    records, manifest_rows = load_unique_records(manifest)
    sequences = build_sequences(records)
    eligible = [
        row for row in sequences
        if int(row["record_count"]) >= 10 and int(row["span_days"]) >= 90
    ]
    selected = eligible[:sequence_count]
    if len(selected) < sequence_count:
        raise ValueError("not enough eligible crack sequences")

    missing_pairs = 0
    for record in records:
        image, mask = resolve_pair(root, record["reid"], record["img_name"])
        missing_pairs += int(not image.exists() or not mask.exists())

    out.mkdir(parents=True, exist_ok=True)
    sequence_rows: list[dict[str, object]] = []
    observation_rows: list[dict[str, object]] = []
    for sequence in selected:
        sequence_rows.append({key: value for key, value in sequence.items() if key != "items"})
        for timestamp, record in evenly_spaced(sequence["items"], samples_per_sequence):
            image, mask = resolve_pair(root, record["reid"], record["img_name"])
            if not image.exists() or not mask.exists():
                raise FileNotFoundError(f"selected pair is missing: {record['img_name']}")
            features = mask_features(mask)
            observation_rows.append(
                {
                    "reid": record["reid"],
                    "category": record["category"],
                    "camera_suffix": parse_filename(record["img_name"])[1],
                    "timestamp_local_naive": timestamp.isoformat(timespec="milliseconds"),
                    "timezone_status": "unknown_not_ingested",
                    "image_name": record["img_name"],
                    "image_sha256": sha256(image),
                    "mask_sha256": sha256(mask),
                    **features,
                    "spatial_unit": "pixel_fraction",
                    "cross_visit_registration": "absent",
                    "decision_eligible": False,
                }
            )

    write_csv(out / "selected_visual_sequences.csv", sequence_rows)
    write_csv(out / "sampled_visual_observations.csv", observation_rows)

    inventory = {
        "schema_version": "pavetrack_visual_inventory_v1",
        "evidence_class": "real_measurement_visual_only",
        "manifest_rows": manifest_rows,
        "unique_image_mask_pairs": len(records),
        "duplicate_manifest_rows": manifest_rows - len(records),
        "location_count": len({record["reid"] for record in records}),
        "filename_timestamp_parseable": sum(parse_filename(record["img_name"]) is not None for record in records),
        "missing_image_or_mask_pairs": missing_pairs,
        "eligible_crack_sequences": len(eligible),
        "selected_sequences": sequence_count,
        "sampled_pairs": len(observation_rows),
        "physical_pixel_scale_available": False,
        "timezone_declared": False,
        "cross_visit_registration_available": False,
        "paired_mechanical_channels_available": False,
        "measured_maintenance_records_available": False,
        "latent_fields_used": False,
        "claim_scope": "L1 image-space crack geometry availability only",
    }
    (out / "dataset_inventory.json").write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    figure, axis = plt.subplots(figsize=(8, 4.5))
    for sequence in sequence_rows:
        rows = [row for row in observation_rows if row["reid"] == sequence["reid"] and row["category"] == sequence["category"]]
        x = [datetime.fromisoformat(str(row["timestamp_local_naive"])) for row in rows]
        y = [float(row["mask_area_fraction"]) for row in rows]
        axis.plot(x, y, marker="o", label=f"{sequence['reid']} {sequence['category']}")
    axis.set_ylabel("Mask area fraction")
    axis.set_xlabel("Acquisition time (timezone unknown)")
    axis.set_title("PaveTrack visual-only sampled trajectories")
    axis.grid(alpha=0.25)
    axis.legend(fontsize=8)
    figure.autofmt_xdate()
    figure.tight_layout()
    figure.savefig(out / "sampled_mask_area_trajectories.png", dpi=180)
    plt.close(figure)

    decision = f"""# PaveTrack real-observation pilot

## Verdict

**Accepted as a real visual-geometry inventory; not accepted for model-state
assimilation, fracture-mechanism validation or RUL.**

The source manifest contains {manifest_rows} rows and {len(records)} unique
image-mask pairs across {inventory['location_count']} locations. All referenced
pairs were checked; missing pairs: {missing_pairs}. The pilot seals
{len(observation_rows)} observations from {sequence_count} long crack sequences
with image and mask SHA-256 hashes and image-space geometry features.

The observations have no physical pixel scale, declared timezone or cross-visit
registration. No paired DIC/strain, FWD, WIM, temperature or measured
maintenance record is present. Mask-area decreases therefore cannot be labelled
healing or maintenance. No FEM latent field was used.

The upstream report states 9,447 annotations and 8,625 images, which disagrees
with the manifest. This provenance discrepancy must be reconciled before a
formal train/test split. A later geometry forecast must split by location and
must remain a pixel-space task until calibration and registration are supplied.
"""
    (out / "decision.md").write_text(decision, encoding="utf-8")

    manifest_payload = {
        "schema_version": "pavetrack_visual_pilot_run_v1",
        "dataset_root": str(root),
        "source_manifest_sha256": sha256(manifest),
        "script_sha256": sha256(Path(__file__)),
        "parameters": {
            "sequence_count": sequence_count,
            "samples_per_sequence": samples_per_sequence,
            "eligibility": "crack category; >=10 records; >=90 day span; same camera suffix",
        },
        "outputs": [
            "dataset_inventory.json",
            "selected_visual_sequences.csv",
            "sampled_visual_observations.csv",
            "sampled_mask_area_trajectories.png",
            "decision.md",
        ],
    }
    (out / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    outputs = manifest_payload["outputs"] + ["RUN_MANIFEST.json"]
    (out / "HASHES.sha256").write_text(
        "".join(f"{sha256(out / name)}  {name}\n" for name in outputs),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sequence-count", type=int, default=3)
    parser.add_argument("--samples-per-sequence", type=int, default=8)
    args = parser.parse_args()
    build_package(args.dataset_root, args.out, args.sequence_count, args.samples_per_sequence)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
