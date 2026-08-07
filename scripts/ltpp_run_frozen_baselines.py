#!/usr/bin/env python3
"""Run frozen persistence, scalar-growth, and local-tip baselines for LTPP."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from shapely.geometry import GeometryCollection, LineString, Polygon, box
from shapely.ops import unary_union


CRACK_FAMILIES = {
    "transverse_crack",
    "longitudinal_crack",
    "fatigue_or_alligator_crack",
    "block_crack",
    "other_crack",
}
LINE_BUFFER_M = 0.05
DOMAIN = box(0.0, 0.0, 15.24, 5.0)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crack_lines(payload: dict) -> list[LineString]:
    return [
        LineString(feature["geometry"]["coordinates"])
        for feature in payload.get("features", [])
        if feature["geometry"]["type"] == "LineString"
        and feature["properties"]["distress_family"] in CRACK_FAMILIES
    ]


def uncertain_mask(payload: dict):
    geometries = []
    for feature in payload.get("features", []):
        if feature["properties"]["distress_family"] != "uncertain":
            continue
        geometry = feature["geometry"]
        if geometry["type"] == "LineString":
            geometries.append(LineString(geometry["coordinates"]).buffer(LINE_BUFFER_M))
        else:
            geometries.append(Polygon(geometry["coordinates"][0]))
    return unary_union(geometries) if geometries else GeometryCollection()


def buffered(lines: list[LineString]):
    return unary_union([line.buffer(LINE_BUFFER_M, cap_style=2, join_style=2) for line in lines]) if lines else GeometryCollection()


def extend_line(line: LineString, extension_each_end: float) -> LineString:
    coordinates = list(line.coords)
    if len(coordinates) < 2 or extension_each_end <= 0:
        return line
    start = np.asarray(coordinates[0], dtype=float)
    next_point = np.asarray(coordinates[1], dtype=float)
    end = np.asarray(coordinates[-1], dtype=float)
    previous = np.asarray(coordinates[-2], dtype=float)
    start_direction = start - next_point
    end_direction = end - previous
    if np.linalg.norm(start_direction) > 0:
        start = start + extension_each_end * start_direction / np.linalg.norm(start_direction)
    if np.linalg.norm(end_direction) > 0:
        end = end + extension_each_end * end_direction / np.linalg.norm(end_direction)
    extended = [tuple(start), *coordinates[1:-1], tuple(end)]
    return LineString(extended).intersection(DOMAIN)


def geometry_metrics(source_payload: dict, target_payload: dict, predicted_lines: list[LineString]) -> dict:
    source = buffered(crack_lines(source_payload))
    target = buffered(crack_lines(target_payload))
    predicted = buffered(predicted_lines)
    valid = DOMAIN.difference(unary_union([uncertain_mask(source_payload), uncertain_mask(target_payload)]))
    source = source.intersection(valid);target = target.intersection(valid);predicted = predicted.intersection(valid)
    intersection = predicted.intersection(target).area
    predicted_area = predicted.area
    target_area = target.area
    precision = intersection / predicted_area if predicted_area else float(target_area == 0)
    recall = intersection / target_area if target_area else float(predicted_area == 0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    union = predicted.union(target).area
    iou = intersection / union if union else 1.0
    actual_new = target.difference(source)
    predicted_new = predicted.difference(source)
    return {
        "buffered_precision": precision,
        "buffered_recall": recall,
        "buffered_f1": f1,
        "buffered_iou": iou,
        "new_geometry_symmetric_difference_m2": actual_new.symmetric_difference(predicted_new).area,
        "actual_new_buffered_area_m2": actual_new.area,
        "predicted_new_buffered_area_m2": predicted_new.area,
    }


def fit_nonnegative_rate(rows: list[dict]) -> float:
    durations = np.asarray([row["duration_years"] for row in rows], dtype=float)
    changes = np.asarray([row["raw_total_crack_length_change_m"] for row in rows], dtype=float)
    denominator = float(np.dot(durations, durations))
    return max(0.0, float(np.dot(durations, changes) / denominator)) if denominator else 0.0


def evaluation_splits(rows: list[dict]) -> list[dict]:
    sections = sorted({row["section"] for row in rows})
    splits = []
    for section in sections:
        splits.append(
            {
                "axis": "leave_one_section_out",
                "fold": f"LOSO-{section}",
                "held_out_section": section,
                "train": [row for row in rows if row["section"] != section and row["development_transition"]],
                "test": [row for row in rows if row["section"] == section],
            }
        )
    splits.append(
        {
            "axis": "future_time",
            "fold": "FUTURE-6",
            "held_out_section": None,
            "train": [row for row in rows if row["development_transition"]],
            "test": [row for row in rows if row["future_time_test"]],
        }
    )
    return splits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transitions-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    transition_root = args.transitions_root.resolve()
    manifest_path = transition_root / "transition_manifest.json"
    transitions_path = transition_root / "transitions.json"
    if not manifest_path.exists() or not transitions_path.exists():
        print(json.dumps({"status": "BLOCKED_NO_QUALIFIED_TRANSITIONS"}))
        return 42
    manifest = load_json(manifest_path)
    if manifest.get("status") != "PASS_31_ADJUDICATED_LEAKAGE_SAFE_TRANSITIONS":
        raise ValueError("Transition package is not qualified")
    rows = load_json(transitions_path)
    if len(rows) != 31:
        raise ValueError("Expected 31 transitions")
    payload_cache = {}
    def payload(path: str) -> dict:
        if path not in payload_cache:
            payload_cache[path] = load_json(Path(path))
        return payload_cache[path]

    predictions = []
    split_receipts = []
    for split in evaluation_splits(rows):
        beta = fit_nonnegative_rate(split["train"])
        split_receipts.append(
            {
                "axis": split["axis"],
                "fold": split["fold"],
                "held_out_section": split["held_out_section"],
                "training_transition_ids": [row["transition_id"] for row in split["train"]],
                "test_transition_ids": [row["transition_id"] for row in split["test"]],
                "nonnegative_growth_rate_m_per_year": beta,
            }
        )
        for row in split["test"]:
            source_payload = payload(row["source_geojson"])
            target_payload = payload(row["target_geojson"])
            source_lines = crack_lines(source_payload)
            source_length = row["source_geometry"]["crack_line_length_m"]
            target_length = row["target_geometry"]["crack_line_length_m"]
            predicted_increment = beta * row["duration_years"]
            extension = predicted_increment / (2 * len(source_lines)) if source_lines else 0.0
            local_lines = [extend_line(line, extension) for line in source_lines]
            for model, predicted_length, predicted_lines in (
                ("persistence", source_length, source_lines),
                ("scalar_linear_growth", source_length + predicted_increment, source_lines),
                ("local_tip_extrapolation", source_length + predicted_increment, local_lines),
            ):
                geometry = geometry_metrics(source_payload, target_payload, predicted_lines)
                predictions.append(
                    {
                        "axis": split["axis"],
                        "fold": split["fold"],
                        "held_out_section": split["held_out_section"],
                        "transition_id": row["transition_id"],
                        "section": row["section"],
                        "model": model,
                        "duration_years": row["duration_years"],
                        "source_crack_length_m": source_length,
                        "target_crack_length_m": target_length,
                        "predicted_crack_length_m": predicted_length,
                        "crack_length_absolute_error_m": abs(predicted_length - target_length),
                        **geometry,
                    }
                )

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    prediction_path = output / "baseline_predictions.csv"
    with prediction_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(predictions[0]))
        writer.writeheader();writer.writerows(predictions)
    aggregate = []
    grouped = defaultdict(list)
    for row in predictions:
        grouped[(row["axis"], row["fold"], row["model"])].append(row)
    for (axis, fold, model), group in sorted(grouped.items()):
        aggregate.append(
            {
                "axis": axis,
                "fold": fold,
                "model": model,
                "n": len(group),
                "crack_length_mae_m": float(np.mean([row["crack_length_absolute_error_m"] for row in group])),
                "mean_buffered_f1": float(np.mean([row["buffered_f1"] for row in group])),
                "mean_buffered_iou": float(np.mean([row["buffered_iou"] for row in group])),
                "mean_new_geometry_error_m2": float(np.mean([row["new_geometry_symmetric_difference_m2"] for row in group])),
            }
        )
    aggregate_path = output / "baseline_aggregate.json"
    aggregate_path.write_text(json.dumps(aggregate, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "status": "PASS_FROZEN_BASELINES_COMPLETE",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "transition_manifest": str(manifest_path),
        "transition_manifest_sha256": sha256(manifest_path),
        "models": ["persistence", "scalar_linear_growth", "local_tip_extrapolation"],
        "line_buffer_m": LINE_BUFFER_M,
        "scalar_growth_fit": "nonnegative_origin_constrained_OLS_on_training_transitions_only",
        "local_tip_rule": "distribute_scalar_predicted_increment_equally_across_source_line_endpoints_along_local_endpoint_tangents",
        "split_receipts": split_receipts,
        "prediction_sha256": sha256(prediction_path),
        "aggregate_sha256": sha256(aggregate_path),
        "claim_boundary": "Baselines are controls; no challenger success is implied.",
    }
    receipt_path = output / "baseline_manifest.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "predictions": len(predictions), "manifest_sha256": sha256(receipt_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
