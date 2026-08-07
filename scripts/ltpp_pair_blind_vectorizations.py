#!/usr/bin/env python3
"""Fail-closed pairing of locked primary and secondary LTPP annotations."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist


MAX_X_M = 15.24
MAX_Y_M = 5.0
AREA_GRID_M = 0.02
CRACK_FAMILIES = {
    "transverse_crack",
    "longitudinal_crack",
    "fatigue_or_alligator_crack",
    "block_crack",
    "other_crack",
}


def load_geojson(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "FeatureCollection":
        raise ValueError(f"not a FeatureCollection: {path}")
    return payload


def lock_inventory(packet_root: Path) -> tuple[list[dict], list[str]]:
    inventory = []
    unlocked = []
    for role, prefix in (("primary", "P"), ("secondary", "S")):
        paths = sorted((packet_root / role / "geojson").glob(f"{prefix}[0-9][0-9][0-9].geojson"))
        if not paths:
            raise ValueError(f"no blind labels found for role {role}")
        for path in paths:
            blind_id = path.stem
            payload = load_geojson(path)
            locked = bool(payload.get("properties", {}).get("locked"))
            inventory.append(
                {
                    "role": role,
                    "blind_id": blind_id,
                    "locked": locked,
                    "features": len(payload.get("features", [])),
                }
            )
            if not locked:
                unlocked.append(f"{role}:{blind_id}")
    return inventory, unlocked


def resample_line(coordinates: list[list[float]], spacing: float = 0.02) -> np.ndarray:
    points = np.asarray(coordinates, dtype=np.float64)
    if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] != 2:
        raise ValueError("invalid LineString coordinates")
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
    total = float(cumulative[-1])
    if total <= 1e-9:
        return points[:1]
    samples = np.linspace(0.0, total, max(2, int(math.ceil(total / spacing)) + 1))
    return np.column_stack(
        (
            np.interp(samples, cumulative, points[:, 0]),
            np.interp(samples, cumulative, points[:, 1]),
        )
    )


def centerline_distance(first: np.ndarray, second: np.ndarray) -> float:
    distances = cdist(first, second)
    return float((distances.min(axis=1).mean() + distances.min(axis=0).mean()) / 2.0)


def tip_distance(first: np.ndarray, second: np.ndarray) -> float:
    direct = np.linalg.norm(first[0] - second[0]) + np.linalg.norm(first[-1] - second[-1])
    reversed_cost = np.linalg.norm(first[0] - second[-1]) + np.linalg.norm(first[-1] - second[0])
    return float(min(direct, reversed_cost) / 2.0)


def feature_id(feature: dict) -> str:
    properties = feature.get("properties", {})
    return str(properties.get("feature_id") or properties["line_id"])


def polygon_exterior(feature: dict) -> np.ndarray:
    coordinates = feature.get("geometry", {}).get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) != 1:
        raise ValueError("Polygon must contain one exterior ring")
    points = np.asarray(coordinates[0], dtype=np.float64)
    if points.ndim != 2 or points.shape[0] < 4 or points.shape[1] != 2:
        raise ValueError("invalid Polygon exterior ring")
    return points


def polygon_centroid(points: np.ndarray) -> np.ndarray:
    ring = points[:-1] if np.allclose(points[0], points[-1]) else points
    return ring.mean(axis=0)


def polygon_mask(points: np.ndarray) -> np.ndarray:
    x_values = np.arange(AREA_GRID_M / 2.0, MAX_X_M, AREA_GRID_M)
    y_values = np.arange(AREA_GRID_M / 2.0, MAX_Y_M, AREA_GRID_M)
    grid_x, grid_y = np.meshgrid(x_values, y_values)
    test_x = grid_x.ravel()
    test_y = grid_y.ravel()
    inside = np.zeros(test_x.shape, dtype=bool)
    ring = points if np.allclose(points[0], points[-1]) else np.vstack((points, points[0]))
    for start, end in zip(ring[:-1], ring[1:]):
        x1, y1 = start
        x2, y2 = end
        crossing = (y1 > test_y) != (y2 > test_y)
        x_intersection = (x2 - x1) * (test_y - y1) / (y2 - y1 + 1e-15) + x1
        inside ^= crossing & (test_x < x_intersection)
    return inside.reshape(grid_x.shape)


def polygon_iou(first: np.ndarray, second: np.ndarray) -> float:
    union = np.logical_or(first, second).sum()
    if union == 0:
        return 0.0
    return float(np.logical_and(first, second).sum() / union)


def confirmatory_features(payload: dict) -> list[dict]:
    return [
        feature
        for feature in payload.get("features", [])
        if feature.get("properties", {}).get("distress_family") in CRACK_FAMILIES
    ]


def pair_lines(first: list[dict], second: list[dict]) -> dict:
    if not first or not second:
        return {
            "matches": [],
            "unmatched_primary": [feature_id(feature) for feature in first],
            "unmatched_secondary": [feature_id(feature) for feature in second],
            "family_disagreements": [],
        }
    first_lines = [resample_line(feature["geometry"]["coordinates"]) for feature in first]
    second_lines = [resample_line(feature["geometry"]["coordinates"]) for feature in second]
    costs = np.empty((len(first), len(second)), dtype=np.float64)
    details = {}
    for i, first_line in enumerate(first_lines):
        for j, second_line in enumerate(second_lines):
            centre = centerline_distance(first_line, second_line)
            tip = tip_distance(first_line, second_line)
            same_family = (
                first[i]["properties"]["distress_family"]
                == second[j]["properties"]["distress_family"]
            )
            costs[i, j] = centre + 0.35 * tip + (0.20 if not same_family else 0.0)
            details[(i, j)] = (centre, tip, same_family)
    rows, columns = linear_sum_assignment(costs)
    matches = []
    used_first = set()
    used_second = set()
    family_disagreements = []
    for i, j in zip(rows.tolist(), columns.tolist()):
        centre, tip, same_family = details[(i, j)]
        if centre > 0.25 or tip > 0.50:
            continue
        first_id = feature_id(first[i])
        second_id = feature_id(second[j])
        match = {
            "geometry_type": "LineString",
            "primary_feature_id": first_id,
            "secondary_feature_id": second_id,
            "centerline_distance_m": centre,
            "tip_distance_m": tip,
            "same_family": same_family,
        }
        matches.append(match)
        used_first.add(i)
        used_second.add(j)
        if not same_family:
            family_disagreements.append(match)
    return {
        "matches": matches,
        "unmatched_primary": [
            feature_id(feature) for index, feature in enumerate(first) if index not in used_first
        ],
        "unmatched_secondary": [
            feature_id(feature) for index, feature in enumerate(second) if index not in used_second
        ],
        "family_disagreements": family_disagreements,
    }


def pair_areas(first: list[dict], second: list[dict]) -> dict:
    if not first or not second:
        return {
            "matches": [],
            "unmatched_primary": [feature_id(feature) for feature in first],
            "unmatched_secondary": [feature_id(feature) for feature in second],
            "family_disagreements": [],
        }
    first_polygons = [polygon_exterior(feature) for feature in first]
    second_polygons = [polygon_exterior(feature) for feature in second]
    first_masks = [polygon_mask(points) for points in first_polygons]
    second_masks = [polygon_mask(points) for points in second_polygons]
    first_centroids = [polygon_centroid(points) for points in first_polygons]
    second_centroids = [polygon_centroid(points) for points in second_polygons]
    costs = np.empty((len(first), len(second)), dtype=np.float64)
    details = {}
    for i in range(len(first)):
        for j in range(len(second)):
            overlap = polygon_iou(first_masks[i], second_masks[j])
            centroid = float(np.linalg.norm(first_centroids[i] - second_centroids[j]))
            same_family = (
                first[i]["properties"]["distress_family"]
                == second[j]["properties"]["distress_family"]
            )
            costs[i, j] = (1.0 - overlap) + 0.25 * centroid + (0.20 if not same_family else 0.0)
            details[(i, j)] = (overlap, centroid, same_family)
    rows, columns = linear_sum_assignment(costs)
    matches = []
    used_first = set()
    used_second = set()
    family_disagreements = []
    for i, j in zip(rows.tolist(), columns.tolist()):
        overlap, centroid, same_family = details[(i, j)]
        if overlap < 0.20 or centroid > 0.75:
            continue
        match = {
            "geometry_type": "Polygon",
            "primary_feature_id": feature_id(first[i]),
            "secondary_feature_id": feature_id(second[j]),
            "area_iou": overlap,
            "centroid_distance_m": centroid,
            "same_family": same_family,
        }
        matches.append(match)
        used_first.add(i)
        used_second.add(j)
        if not same_family:
            family_disagreements.append(match)
    return {
        "matches": matches,
        "unmatched_primary": [
            feature_id(feature) for index, feature in enumerate(first) if index not in used_first
        ],
        "unmatched_secondary": [
            feature_id(feature) for index, feature in enumerate(second) if index not in used_second
        ],
        "family_disagreements": family_disagreements,
    }


def pair_asset(primary: dict, secondary: dict, asset: dict) -> dict:
    first = confirmatory_features(primary)
    second = confirmatory_features(secondary)
    first_lines = [feature for feature in first if feature.get("geometry", {}).get("type") == "LineString"]
    second_lines = [feature for feature in second if feature.get("geometry", {}).get("type") == "LineString"]
    first_areas = [feature for feature in first if feature.get("geometry", {}).get("type") == "Polygon"]
    second_areas = [feature for feature in second if feature.get("geometry", {}).get("type") == "Polygon"]
    if len(first_lines) + len(first_areas) != len(first) or len(second_lines) + len(second_areas) != len(second):
        raise ValueError("confirmatory geometry must be LineString or Polygon")
    lines = pair_lines(first_lines, second_lines)
    areas = pair_areas(first_areas, second_areas)
    return {
        "asset_key": asset["asset_key"],
        "section": asset["section"],
        "construction_number": asset["construction_number"],
        "panel_start_ft": asset["panel_start_ft"],
        "survey_date": asset["survey_date"],
        "primary_features": len(first),
        "secondary_features": len(second),
        "primary_lines": len(first_lines),
        "secondary_lines": len(second_lines),
        "primary_areas": len(first_areas),
        "secondary_areas": len(second_areas),
        "line_matches": lines["matches"],
        "area_matches": areas["matches"],
        "unmatched_primary": lines["unmatched_primary"] + areas["unmatched_primary"],
        "unmatched_secondary": lines["unmatched_secondary"] + areas["unmatched_secondary"],
        "family_disagreements": lines["family_disagreements"] + areas["family_disagreements"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    inventory, unlocked = lock_inventory(args.packet_root)
    if unlocked:
        payload = {
            "status": "not_ready",
            "reason": "all blind maps in both roles must be locked before unsealing",
            "sealed_mapping_read": False,
            "unlocked_count": len(unlocked),
            "unlocked": unlocked,
            "inventory": inventory,
        }
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps({"status": "not_ready", "unlocked_count": len(unlocked)}))
        return 2

    mapping_path = (
        args.packet_root
        / "sealed_do_not_open_during_annotation"
        / "blind_id_asset_mapping.json"
    )
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    primary_by_asset = {row["asset_key"]: row for row in mapping["primary"]}
    secondary_by_asset = {row["asset_key"]: row for row in mapping["secondary"]}
    if set(primary_by_asset) != set(secondary_by_asset):
        raise SystemExit("primary and secondary asset sets differ")

    asset_reports = []
    for asset_key in sorted(primary_by_asset):
        primary_row = primary_by_asset[asset_key]
        secondary_row = secondary_by_asset[asset_key]
        primary = load_geojson(
            args.packet_root / "primary" / "geojson" / f"{primary_row['blind_id']}.geojson"
        )
        secondary = load_geojson(
            args.packet_root / "secondary" / "geojson" / f"{secondary_row['blind_id']}.geojson"
        )
        asset_reports.append(pair_asset(primary, secondary, primary_row))

    line_matches = [match for report in asset_reports for match in report["line_matches"]]
    area_matches = [match for report in asset_reports for match in report["area_matches"]]
    matches = line_matches + area_matches
    primary_total = sum(report["primary_features"] for report in asset_reports)
    secondary_total = sum(report["secondary_features"] for report in asset_reports)
    matched_total = len(matches)
    precision = matched_total / max(1, secondary_total)
    recall = matched_total / max(1, primary_total)
    f1 = 2.0 * precision * recall / max(1e-12, precision + recall)
    unmatched = sum(
        len(report["unmatched_primary"]) + len(report["unmatched_secondary"])
        for report in asset_reports
    )
    disagreements = sum(len(report["family_disagreements"]) for report in asset_reports)
    mean_centerline = float(np.mean([match["centerline_distance_m"] for match in line_matches])) if line_matches else None
    mean_tip = float(np.mean([match["tip_distance_m"] for match in line_matches])) if line_matches else None
    mean_area_iou = float(np.mean([match["area_iou"] for match in area_matches])) if area_matches else None
    mean_area_centroid = float(np.mean([match["centroid_distance_m"] for match in area_matches])) if area_matches else None
    line_geometry_present = any(report["primary_lines"] or report["secondary_lines"] for report in asset_reports)
    area_geometry_present = any(report["primary_areas"] or report["secondary_areas"] for report in asset_reports)
    line_metrics_pass = bool(
        not line_geometry_present
        or (
            line_matches
            and mean_centerline is not None
            and mean_centerline <= 0.10
            and mean_tip is not None
            and mean_tip <= 0.20
        )
    )
    area_metrics_pass = bool(
        not area_geometry_present
        or (
            area_matches
            and mean_area_iou is not None
            and mean_area_iou >= 0.65
            and mean_area_centroid is not None
            and mean_area_centroid <= 0.20
        )
    )
    metrics_pass = bool(
        matches
        and f1 >= 0.80
        and line_metrics_pass
        and area_metrics_pass
    )
    payload = {
        "status": "requires_adjudication" if unmatched or disagreements else "paired_review_complete",
        "sealed_mapping_read": True,
        "metrics_pass": metrics_pass,
        "geometry_level_precision": precision,
        "geometry_level_recall": recall,
        "geometry_level_f1": f1,
        "line_metrics_pass": line_metrics_pass,
        "area_metrics_pass": area_metrics_pass,
        "mean_centerline_distance_m": mean_centerline,
        "mean_tip_distance_m": mean_tip,
        "mean_area_iou": mean_area_iou,
        "mean_area_centroid_distance_m": mean_area_centroid,
        "unmatched_geometry_count": unmatched,
        "family_disagreement_count": disagreements,
        "qualification_boundary": "pairing alone never creates adjudicated ground truth",
        "assets": asset_reports,
    }
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("status", "metrics_pass", "geometry_level_f1", "unmatched_geometry_count")}))
    return 0 if payload["status"] == "paired_review_complete" and metrics_pass else 3


if __name__ == "__main__":
    raise SystemExit(main())
