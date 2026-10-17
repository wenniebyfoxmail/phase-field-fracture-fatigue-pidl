#!/usr/bin/env python3
"""Prepare one-owner geometry-assisted grid-control records for cross-state maps."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PACKETS = load_module(
    "cross_state_registration_packets",
    ROOT / "scripts" / "ltpp_prepare_cross_state_registration_review_packets.py",
)
PILOT = load_module(
    "geometry_assisted_grid_pilot",
    ROOT / "scripts" / "ltpp_geometry_assisted_grid_control_pilot_server.py",
)

STATUS = "EXPLORATORY_SINGLE_OWNER_ANNOTATION__NOT_INDEPENDENT"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rectangle_corners(row: dict) -> list[list[float]]:
    x0, y0, x1, y1 = (float(row[key]) for key in ("x0", "y0", "x1", "y1"))
    if not (x0 < x1 and y0 < y1):
        raise ValueError("automatic rectangle is unordered")
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def build_tasks(row: dict, left: int, top: int) -> dict:
    suggestions = PILOT.suggested_source_points(rectangle_corners(row))
    tasks = {}
    for candidate in PILOT.task_order("all66"):
        source_x, source_y = suggestions[candidate]
        crop_point = [round(source_x - left, 3), round(source_y - top, 3)]
        tasks[candidate] = {
            "status": "unreviewed",
            "suggested_crop_px": crop_point,
            "reviewed_crop_px": crop_point,
            "note": "",
        }
    return tasks


def run(
    project_root: Path,
    gate_specs: list[tuple[Path, str, int]],
    preregistration: Path,
    output: Path,
) -> dict:
    if output.exists():
        raise ValueError(f"refusing to overwrite owner packet: {output}")
    rows, gate_receipts = PACKETS.load_rows(project_root, gate_specs)
    dates = [row["survey_date"] for row in rows]
    if len(dates) != len(set(dates)):
        raise ValueError("survey dates must be unique across the owner packet")

    images = output / "images"
    records = output / "records"
    images.mkdir(parents=True)
    records.mkdir()
    inputs = []
    for row in rows:
        source = Path(row["source_path"])
        image = cv2.imread(str(source), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"cannot read source image: {source}")
        left, top, right, bottom = PACKETS.crop_bounds(row, image.shape)
        date = row["survey_date"]
        target = images / f"{date}.png"
        if not cv2.imwrite(str(target), image[top:bottom, left:right]):
            raise ValueError(f"cannot write owner image: {date}")
        record = {
            "schema_version": "ltpp_cross_state_single_owner_grid_annotation_v1",
            "classification": STATUS,
            "survey_date": date,
            "section": row["section"],
            "task_profile": "all66",
            "locked": False,
            "crop_source_px": {"left": left, "top": top, "right": right, "bottom": bottom},
            "tasks": build_tasks(row, left, top),
        }
        PILOT.atomic_json(records / f"{date}.json", record)
        inputs.append({
            "section": row["section"],
            "survey_date": date,
            "source_sha256": row["source_sha256"],
            "owner_image_sha256": sha256(target),
            "crop_source_px": record["crop_source_px"],
        })

    receipt = {
        "status": STATUS,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "single_annotator": "owner_user",
        "evidence_grade": "exploratory_single_owner",
        "maps": len(rows),
        "tasks_per_map": 66,
        "total_tasks": len(rows) * 66,
        "gate_receipts": gate_receipts,
        "preregistration": str(preregistration.resolve()),
        "preregistration_sha256": sha256(preregistration),
        "assistance": "frozen automatic rectangle gives projective suggestions; owner reviews every point",
        "formal_tier_b_controls_created": False,
        "independent_consensus_created": False,
        "transform_fit_authorized": False,
        "final_gate_run": False,
        "inputs": inputs,
    }
    PILOT.atomic_json(output / "input_receipt.json", receipt)
    (output / "README.md").write_text(
        "# Cross-state single-owner grid annotation\n\n"
        "Classification: `EXPLORATORY_SINGLE_OWNER_ANNOTATION__NOT_INDEPENDENT`.\n\n"
        "Review all 66 points on all 14 maps. Accept a green suggestion only when it is the printed-grid centre; otherwise move it or mark missing/occluded/ambiguous. "
        "Do not use cracks or handwriting as grid evidence. Lock each map only after all points are reviewed.\n",
        encoding="utf-8",
    )
    manifest_paths = list(images.glob("*.png")) + [output / "input_receipt.json", output / "README.md"]
    (output / "frozen_inputs.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(output)}\n" for path in sorted(manifest_paths)),
        encoding="ascii",
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--gate", action="append", type=PACKETS.parse_gate_spec, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = run(
        args.project_root.resolve(), args.gate, args.preregistration.resolve(),
        args.output_root.resolve(),
    )
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
