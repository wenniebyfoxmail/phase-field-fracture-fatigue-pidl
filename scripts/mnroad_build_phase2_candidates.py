#!/usr/bin/env python3
"""Build conservative phase-2 crack-identity candidates for MnROAD Cell 22.

The script never changes phase-1 geometry.  It assigns an identity only when a
target NWP segment has a unique one-to-one predecessor after map-grid
normalisation.  Split/merge cases remain unresolvable for owner review.
Concealed repeat pages are excluded from temporal evidence and receive only an
automatic nearest-primary inheritance for QC purposes.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


DATES = (
    "2017-03-20", "2018-03-14", "2018-04-27", "2018-08-23",
    "2019-03-22", "2019-04-16", "2019-10-23",
)

# Map-grid calibration in landscape display coordinates.  The 2018 scans use
# about 21.4 px/ft; the 2019 scans use about 20.1 px/ft with a shifted 0-ft
# origin.  Identity decisions additionally require close lateral agreement.
X_CALIBRATION = {
    "2017-03-20": (50.0, 21.4),
    "2018-03-14": (50.0, 21.4),
    "2018-04-27": (50.0, 21.4),
    "2018-08-23": (50.0, 21.4),
    "2019-03-22": (99.0, 20.1),
    "2019-04-16": (99.0, 20.1),
    "2019-10-23": (99.0, 20.1),
}


def load_annotator(path: Path):
    spec = importlib.util.spec_from_file_location("mnroad_annotator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def landscape_points(feature: dict, width: int, height: int, rotation: int) -> list[tuple[float, float]]:
    if rotation == 90:
        return [(height - point[1], point[0]) for point in feature["geometry"]["coordinates"]]
    return [(point[1], width - point[0]) for point in feature["geometry"]["coordinates"]]


def descriptor(feature: dict, date: str, width: int, height: int, rotation: int) -> dict:
    points = landscape_points(feature, width, height, rotation)
    origin, pixels_per_foot = X_CALIBRATION[date]
    x = [(point[0] - origin) / pixels_per_foot for point in points]
    y = [point[1] for point in points]
    return {
        "feature": feature,
        "segment_id": feature["properties"]["segment_id"],
        "x_min_ft": min(x),
        "x_max_ft": max(x),
        "y_mean_px": sum(y) / len(y),
    }


def candidate_edge(previous: dict, current: dict) -> dict | None:
    intersection = max(0.0, min(previous["x_max_ft"], current["x_max_ft"]) - max(previous["x_min_ft"], current["x_min_ft"]))
    shortest = max(0.01, min(previous["x_max_ft"] - previous["x_min_ft"], current["x_max_ft"] - current["x_min_ft"]))
    overlap = intersection / shortest
    lateral = abs(previous["y_mean_px"] - current["y_mean_px"])
    previous_center = (previous["x_min_ft"] + previous["x_max_ft"]) / 2
    current_center = (current["x_min_ft"] + current["x_max_ft"]) / 2
    short_fragment_match = abs(previous_center - current_center) <= 0.75
    if (overlap < 0.50 and not short_fragment_match) or lateral > 6.0:
        return None
    return {"overlap_of_shorter": overlap, "lateral_difference_px": lateral}


def is_extension(previous: dict, current: dict) -> bool:
    left = previous["x_min_ft"] - current["x_min_ft"]
    right = current["x_max_ft"] - previous["x_max_ft"]
    previous_length = max(0.01, previous["x_max_ft"] - previous["x_min_ft"])
    current_length = current["x_max_ft"] - current["x_min_ft"]
    return left > 1.5 or right > 1.5 or current_length > 1.25 * previous_length


def clear_link_fields(properties: dict) -> None:
    for key in (
        "link_confidence", "link_method", "link_reference_segment_ids",
        "link_reference_survey_date", "excluded_concealed_repeat",
    ):
        properties.pop(key, None)


def save_record(base_url: str, task_id: str, record: dict) -> None:
    payload = json.dumps(record).encode()
    request = urllib.request.Request(
        f"{base_url}/api/record/{task_id}?phase=2", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status} for {task_id}")
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"save failed for {task_id}: {error.read().decode()}") from error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--annotator", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8776")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    packet = args.packet.resolve()
    annotator = load_annotator(args.annotator.resolve())
    manifest = json.loads((packet / "manifest.json").read_text())
    private = json.loads((packet / "private_repeat_key.json").read_text())["tasks"]
    records = {
        row["task_id"]: json.loads((packet / "records" / f"{row['task_id']}.geojson").read_text())
        for row in manifest["tasks"]
    }
    if not all(record.get("phase1_locked") for record in records.values()):
        raise RuntimeError("all phase-1 records must be locked")
    if any(record.get("phase2_locked") for record in records.values()):
        raise RuntimeError("phase 2 is partly or fully locked; refusing bulk rewrite")

    primary = {
        (row["survey_date"], row["page"]): task_id
        for task_id, row in private.items() if not row["is_repeat"]
    }
    descriptors: dict[str, list[dict]] = {}
    for (date, page), task_id in primary.items():
        row = private[task_id]
        width, height = annotator.image_size(packet / "images" / row["image"])
        rotation = annotator.landscape_rotation_degrees(date)
        descriptors[task_id] = [
            descriptor(feature, date, width, height, rotation)
            for feature in annotator._target_features(records[task_id])
        ]

    ambiguities = []
    disappearances = []
    assignments = []
    next_identity = 1

    def new_identity() -> str:
        nonlocal next_identity
        value = f"C{next_identity:03d}"
        next_identity += 1
        return value

    for page in range(1, 11):
        previous: list[dict] = []
        previous_date: str | None = None
        for date in DATES:
            task_id = primary[(date, page)]
            record = records[task_id]
            current = descriptors[task_id]
            for feature in record["features"]:
                properties = feature["properties"]
                clear_link_fields(properties)
                properties["crack_id"] = ""
                properties["change_type"] = "unresolvable"
                if properties["lane"] != "Driving" or properties["distress_class"] != "NWP":
                    properties["link_method"] = "excluded_non_target_feature"

            if not current:
                if previous:
                    disappearances.extend({
                        "page": page, "from_date": previous_date, "to_date": date,
                        "previous_segment_id": item["segment_id"],
                        "crack_id": item["feature"]["properties"].get("crack_id", ""),
                    } for item in previous)
                previous = []
                previous_date = date
                continue

            if not previous:
                for item in current:
                    properties = item["feature"]["properties"]
                    properties["crack_id"] = new_identity()
                    properties["change_type"] = "nucleation"
                    properties["link_confidence"] = "high"
                    properties["link_method"] = "first_target_observation_after_empty_prior_map"
                    assignments.append({"task_id": task_id, "segment_id": item["segment_id"], "crack_id": properties["crack_id"], "change_type": "nucleation"})
                previous = current
                previous_date = date
                continue

            edges = []
            for old_index, old in enumerate(previous):
                for new_index, new in enumerate(current):
                    evidence = candidate_edge(old, new)
                    if evidence:
                        edges.append((old_index, new_index, evidence))
            old_degree = defaultdict(int)
            new_degree = defaultdict(int)
            for old_index, new_index, _ in edges:
                old_degree[old_index] += 1
                new_degree[new_index] += 1

            matched_old = set()
            for new_index, item in enumerate(current):
                candidates = [(old_index, evidence) for old_index, candidate_new, evidence in edges if candidate_new == new_index]
                properties = item["feature"]["properties"]
                if len(candidates) == 1:
                    old_index, evidence = candidates[0]
                    old = previous[old_index]
                    old_id = old["feature"]["properties"].get("crack_id", "")
                    if old_degree[old_index] == 1 and old_id:
                        change = "extension" if is_extension(old, item) else "persistent"
                        properties["crack_id"] = old_id
                        properties["change_type"] = change
                        properties["link_confidence"] = "high"
                        properties["link_method"] = "unique_one_to_one_grid_registered_overlap"
                        properties["link_reference_segment_ids"] = [old["segment_id"]]
                        properties["link_reference_survey_date"] = previous_date
                        assignments.append({"task_id": task_id, "segment_id": item["segment_id"], "crack_id": old_id, "change_type": change})
                        matched_old.add(old_index)
                        continue

                if candidates:
                    references = [previous[index]["segment_id"] for index, _ in candidates]
                    unresolved_predecessor = len(candidates) == 1 and old_degree[candidates[0][0]] == 1
                    reason = "predecessor_unresolved" if unresolved_predecessor else "split_or_merge"
                    properties["link_method"] = f"owner_review_required_{reason}"
                    properties["link_reference_segment_ids"] = references
                    properties["link_reference_survey_date"] = previous_date
                    ambiguities.append({
                        "task_id": task_id, "survey_date": date, "page": page,
                        "segment_id": item["segment_id"], "reason": reason,
                        "candidate_previous_segments": references,
                    })
                else:
                    def interval_gap(old: dict) -> float:
                        return max(0.0, item["x_min_ft"] - old["x_max_ft"], old["x_min_ft"] - item["x_max_ft"])
                    nearby = [
                        old for old in previous
                        if abs(old["y_mean_px"] - item["y_mean_px"]) <= 10.0 and interval_gap(old) <= 2.0
                    ]
                    if nearby:
                        references = [old["segment_id"] for old in nearby]
                        properties["link_method"] = "owner_review_required_possible_gap_extension"
                        properties["link_reference_segment_ids"] = references
                        properties["link_reference_survey_date"] = previous_date
                        ambiguities.append({
                            "task_id": task_id, "survey_date": date, "page": page,
                            "segment_id": item["segment_id"], "reason": "possible_gap_extension",
                            "candidate_previous_segments": references,
                        })
                    else:
                        properties["crack_id"] = new_identity()
                        properties["change_type"] = "nucleation"
                        properties["link_confidence"] = "high"
                        properties["link_method"] = "no_spatially_compatible_predecessor"
                        assignments.append({"task_id": task_id, "segment_id": item["segment_id"], "crack_id": properties["crack_id"], "change_type": "nucleation"})

            for old_index, old in enumerate(previous):
                if old_index not in matched_old and old["feature"]["properties"].get("crack_id"):
                    disappearances.append({
                        "page": page, "from_date": previous_date, "to_date": date,
                        "previous_segment_id": old["segment_id"],
                        "crack_id": old["feature"]["properties"]["crack_id"],
                    })
            previous = current
            previous_date = date

    # Repeat pages are never temporal observations.  Copy an identity only for
    # a unique geometric match to the corresponding primary feature.
    for repeat_task_id, row in private.items():
        if not row["is_repeat"]:
            continue
        primary_task_id = row["primary_task_id"]
        repeat_record = records[repeat_task_id]
        primary_record = records[primary_task_id]
        width, height = annotator.image_size(packet / "images" / row["image"])
        rotation = annotator.landscape_rotation_degrees(row["survey_date"])
        repeat_desc = [descriptor(feature, row["survey_date"], width, height, rotation) for feature in annotator._target_features(repeat_record)]
        primary_desc = descriptors[primary_task_id]
        for feature in repeat_record["features"]:
            properties = feature["properties"]
            clear_link_fields(properties)
            properties["crack_id"] = ""
            properties["change_type"] = "unresolvable"
            properties["excluded_concealed_repeat"] = True
            properties["link_method"] = "excluded_concealed_repeat"
        edges = []
        for primary_index, old in enumerate(primary_desc):
            for repeat_index, new in enumerate(repeat_desc):
                evidence = candidate_edge(old, new)
                if evidence:
                    edges.append((primary_index, repeat_index))
        p_degree = defaultdict(int)
        r_degree = defaultdict(int)
        for primary_index, repeat_index in edges:
            p_degree[primary_index] += 1
            r_degree[repeat_index] += 1
        for primary_index, repeat_index in edges:
            if p_degree[primary_index] != 1 or r_degree[repeat_index] != 1:
                continue
            source = primary_desc[primary_index]["feature"]["properties"]
            target = repeat_desc[repeat_index]["feature"]["properties"]
            if source.get("crack_id"):
                target["crack_id"] = source["crack_id"]
                target["change_type"] = source["change_type"]
                target["link_confidence"] = "high"
                target["link_method"] = "concealed_repeat_unique_primary_inheritance"
                target["link_reference_segment_ids"] = [primary_desc[primary_index]["segment_id"]]

    report = {
        "created_at_utc": utc_now(),
        "status": "PHASE2_CANDIDATES_NOT_LOCKED",
        "method": "unique one-to-one overlap after map-grid calibration; split/merge is unresolved",
        "calibration": X_CALIBRATION,
        "primary_assignments": assignments,
        "ambiguities": ambiguities,
        "disappearances_without_placeholder_geometry": disappearances,
        "counts": {
            "assigned_primary_features": len(assignments),
            "ambiguous_primary_features": len(ambiguities),
            "disappearances": len(disappearances),
            "next_unused_crack_number": next_identity,
        },
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "phase2_candidate_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if args.apply:
        for task_id, record in records.items():
            save_record(args.base_url.rstrip("/"), task_id, record)
    print(json.dumps(report["counts"] | {"applied": args.apply, "report": str((args.output / 'phase2_candidate_report.json').resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
