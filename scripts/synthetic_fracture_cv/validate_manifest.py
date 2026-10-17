#!/usr/bin/env python3
"""Validate the S02-E002 G1 manifest without inferring missing identity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

try:
    from .render_analytic_sequence import CASES, HEIGHT, MANIFEST_FIELDS, TEXTURE_SEEDS, WIDTH
except ImportError:  # direct script execution
    from render_analytic_sequence import CASES, HEIGHT, MANIFEST_FIELDS, TEXTURE_SEEDS, WIDTH


EXPECTED_STATUS = {case["case"]: case["status"] for case in CASES}
EXPECTED_OPENING = {case["case"]: float(case.get("opening_px", 0.0)) for case in CASES}
EXPECTED_PAIRS = {
    (case["case"], f"texture_{seed}")
    for seed in TEXTURE_SEEDS
    for case in CASES
}
FROZEN_TRAJECTORY = "analytic-straight-slit-v1"
FROZEN_LINEAGE = "analytic-straight-slit-lineage-v1"


def validate_records(records: list[dict[str, Any]], root: Path) -> list[str]:
    errors: list[str] = []
    if len(records) != len(EXPECTED_PAIRS):
        errors.append(f"expected exactly {len(EXPECTED_PAIRS)} frozen records, got {len(records)}")
    if len(records) > 96:
        errors.append(f"frame count {len(records)} exceeds frozen maximum 96")
    seeds = {record.get("reference_texture_id") for record in records}
    expected_seeds = {f"texture_{seed}" for seed in TEXTURE_SEEDS}
    if seeds != expected_seeds:
        errors.append(f"expected exactly two frozen texture ids, got {sorted(str(x) for x in seeds)}")
    observed_pairs = {(record.get("state_id"), record.get("reference_texture_id")) for record in records}
    if observed_pairs != EXPECTED_PAIRS:
        missing = sorted(EXPECTED_PAIRS - observed_pairs)
        extra = sorted(observed_pairs - EXPECTED_PAIRS, key=str)
        errors.append(f"frozen case/seed set mismatch; missing={missing}, extra={extra}")
    seen: set[tuple[Any, Any, Any]] = set()
    lineage_splits: dict[Any, set[Any]] = {}
    for index, record in enumerate(records):
        missing = [field for field in MANIFEST_FIELDS if field not in record]
        if missing:
            errors.append(f"record {index}: missing fields {missing}")
            continue
        key = (record["trajectory_id"], record["state_id"], record["reference_texture_id"])
        if key in seen:
            errors.append(f"record {index}: duplicate state/render key {key}")
        seen.add(key)
        lineage_splits.setdefault(record["lineage_id"], set()).add(record["split"])
        state_id = record["state_id"]
        expected_status = EXPECTED_STATUS.get(state_id)
        if record.get("target_status") != expected_status:
            errors.append(
                f"record {index}: target_status {record.get('target_status')!r} "
                f"does not match frozen {state_id!r} status {expected_status!r}"
            )
        if record["trajectory_id"] != FROZEN_TRAJECTORY:
            errors.append(f"record {index}: unexpected G1 trajectory_id")
        if record["lineage_id"] != FROZEN_LINEAGE or record["split_group"] != FROZEN_LINEAGE:
            errors.append(f"record {index}: unexpected G1 lineage or split_group")
        if record["split"] != "verification_only":
            errors.append(f"record {index}: G1 split must be 'verification_only'")
        if record["event_rule_id"] != "not_applicable_g1" or record["event_first_detect"] is not None:
            errors.append(f"record {index}: event fields are not inert G1 metadata")
        for field in ("displacement_path", "geometry_path", "image_path", "image_label_path"):
            path = root / record[field]
            if not path.is_file():
                errors.append(f"record {index}: missing {field} {path}")
        image_path = root / record["image_path"]
        if image_path.is_file() and Image.open(image_path).size != (WIDTH, HEIGHT):
            errors.append(f"record {index}: image is not {WIDTH}x{HEIGHT}")
        geometry_path = root / record["geometry_path"]
        if geometry_path.is_file() and state_id in EXPECTED_STATUS:
            try:
                geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
                if geometry.get("target_status") != expected_status:
                    errors.append(f"record {index}: geometry target_status disagrees with frozen semantics")
                if float(geometry.get("opening_px", 0.0)) != EXPECTED_OPENING[state_id]:
                    errors.append(f"record {index}: geometry opening disagrees with frozen case")
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
                errors.append(f"record {index}: invalid geometry JSON: {exc}")
        support_path = root / record["image_label_path"]
        if support_path.is_file() and state_id in EXPECTED_STATUS:
            try:
                support = np.load(support_path, allow_pickle=False)
                maximum = float(np.max(support))
                if expected_status == "closed" and maximum != 0.0:
                    errors.append(f"record {index}: closed target has nonzero optical support")
                if expected_status == "ambiguous" and not (0.0 < maximum < 1.0):
                    errors.append(f"record {index}: ambiguous target lacks fractional optical support")
                if expected_status == "resolved" and maximum != 1.0:
                    errors.append(f"record {index}: resolved target lacks full-pixel optical support")
            except (OSError, ValueError) as exc:
                errors.append(f"record {index}: invalid optical support: {exc}")
    for lineage, splits in lineage_splits.items():
        if len(splits) != 1:
            errors.append(f"lineage {lineage!r} crosses splits {sorted(splits)}")
    return errors


def validate_manifest(path: Path) -> list[str]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        return ["manifest root must be a list"]
    return validate_records(records, path.parent)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    errors = validate_manifest(args.manifest)
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
