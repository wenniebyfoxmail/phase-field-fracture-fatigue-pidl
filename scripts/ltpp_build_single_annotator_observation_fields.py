#!/usr/bin/env python3
"""Build frozen line/area observation fields from locked primary LTPP labels."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt


MAX_X_M = 15.24
MAX_Y_M = 5.0


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def point_in_polygon(grid_x: np.ndarray, grid_y: np.ndarray, ring: np.ndarray) -> np.ndarray:
    test_x = grid_x.ravel()
    test_y = grid_y.ravel()
    inside = np.zeros(test_x.shape, dtype=bool)
    if not np.allclose(ring[0], ring[-1]):
        ring = np.vstack((ring, ring[0]))
    for start, end in zip(ring[:-1], ring[1:]):
        x1, y1 = start
        x2, y2 = end
        crossing = (y1 > test_y) != (y2 > test_y)
        x_intersection = (x2 - x1) * (test_y - y1) / (y2 - y1 + 1e-15) + x1
        inside ^= crossing & (test_x < x_intersection)
    return inside.reshape(grid_x.shape)


def rasterize_line_seeds(
    seed: np.ndarray,
    coordinates: np.ndarray,
    x_values: np.ndarray,
    y_values: np.ndarray,
) -> None:
    dx = float(x_values[1] - x_values[0])
    dy = float(y_values[1] - y_values[0])
    step = min(dx, dy) / 2.0
    for start, end in zip(coordinates[:-1], coordinates[1:]):
        length = float(np.linalg.norm(end - start))
        count = max(2, int(math.ceil(length / step)) + 1)
        samples = np.linspace(start, end, count)
        x_index = np.clip(np.rint(samples[:, 0] / dx).astype(int), 0, len(x_values) - 1)
        y_index = np.clip(np.rint(samples[:, 1] / dy).astype(int), 0, len(y_values) - 1)
        seed[y_index, x_index] = True


def geometry_fields(
    payload: dict,
    x_values: np.ndarray,
    y_values: np.ndarray,
    sigma_m: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, int]:
    grid_x, grid_y = np.meshgrid(x_values, y_values)
    line_seed = np.zeros(grid_x.shape, dtype=bool)
    area = np.zeros(grid_x.shape, dtype=bool)
    line_count = 0
    polygon_count = 0
    for feature in payload.get("features", []):
        geometry = feature.get("geometry", {})
        geometry_type = geometry.get("type")
        if geometry_type == "LineString":
            coordinates = np.asarray(geometry["coordinates"], dtype=np.float64)
            rasterize_line_seeds(line_seed, coordinates, x_values, y_values)
            line_count += 1
        elif geometry_type == "Polygon":
            ring = np.asarray(geometry["coordinates"][0], dtype=np.float64)
            area |= point_in_polygon(grid_x, grid_y, ring)
            polygon_count += 1
        else:
            raise ValueError(f"unsupported geometry type: {geometry_type}")
    if line_seed.any():
        dx = float(x_values[1] - x_values[0])
        dy = float(y_values[1] - y_values[0])
        distance = distance_transform_edt(~line_seed, sampling=(dy, dx))
        line = np.exp(-0.5 * np.square(distance / sigma_m))
        line[distance > 3.0 * sigma_m] = 0.0
    else:
        line = np.zeros(grid_x.shape, dtype=np.float64)
    area_float = area.astype(np.float64)
    combined = np.maximum(line, area_float)
    return (
        line.astype(np.float32),
        area_float.astype(np.float32),
        combined.astype(np.float32),
        line_count,
        polygon_count,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--primary-manifest", type=Path, required=True)
    parser.add_argument("--sealed-mapping", type=Path, required=True)
    parser.add_argument("--interval-climate-features", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--resolution-m", type=float, default=0.04)
    parser.add_argument("--line-sigma-m", type=float, default=0.08)
    args = parser.parse_args()

    primary_manifest = load_json(args.primary_manifest)
    mapping = load_json(args.sealed_mapping)
    climate = load_json(args.interval_climate_features)
    if primary_manifest.get("all_locked") is not True:
        raise SystemExit("primary manifest is not fully locked")
    if len(primary_manifest.get("files", [])) != 9:
        raise SystemExit("primary manifest must contain nine files")

    primary_mapping = mapping.get("primary")
    if not isinstance(primary_mapping, list) or len(primary_mapping) != 9:
        raise SystemExit("sealed mapping must contain nine primary rows")
    chronological = sorted(primary_mapping, key=lambda row: row["survey_date"])
    if {row["blind_id"] for row in chronological} != {
        f"P{index:02d}" for index in range(1, 10)
    }:
        raise SystemExit("primary blind-ID set mismatch")

    file_hashes = {row["blind_id"]: row["sha256"] for row in primary_manifest["files"]}
    x_count = int(round(MAX_X_M / args.resolution_m)) + 1
    y_count = int(round(MAX_Y_M / args.resolution_m)) + 1
    x_values = np.linspace(0.0, MAX_X_M, x_count, dtype=np.float64)
    y_values = np.linspace(0.0, MAX_Y_M, y_count, dtype=np.float64)
    line_fields = []
    area_fields = []
    combined_fields = []
    observations = []

    for row in chronological:
        blind_id = row["blind_id"]
        path = args.packet_root / "primary" / "geojson" / f"{blind_id}.geojson"
        if sha256(path) != file_hashes[blind_id]:
            raise SystemExit(f"locked primary hash mismatch: {blind_id}")
        payload = load_json(path)
        if payload.get("properties", {}).get("locked") is not True:
            raise SystemExit(f"primary map is not locked: {blind_id}")
        line, area, combined, line_count, polygon_count = geometry_fields(
            payload, x_values, y_values, args.line_sigma_m
        )
        line_fields.append(line)
        area_fields.append(area)
        combined_fields.append(combined)
        observations.append(
            {
                "survey_date": row["survey_date"],
                "blind_id": blind_id,
                "line_count": line_count,
                "polygon_count": polygon_count,
                "source_geojson_sha256": file_hashes[blind_id],
            }
        )

    intervals = climate.get("intervals")
    if not isinstance(intervals, list) or len(intervals) != 8:
        raise SystemExit("interval climate package must contain eight transitions")
    authorized_indices = [
        index for index, interval in enumerate(intervals)
        if interval.get("confirmatory_forcing_authorized") is True
    ]
    if authorized_indices != list(range(7)):
        raise SystemExit("expected only the first seven climate transitions to be authorized")

    args.output_root.mkdir(parents=True, exist_ok=True)
    fields_path = args.output_root / "frozen_observation_fields.npz"
    np.savez_compressed(
        fields_path,
        x_m=x_values.astype(np.float32),
        y_m=y_values.astype(np.float32),
        line_damage=np.stack(line_fields),
        area_damage=np.stack(area_fields),
        combined_damage=np.stack(combined_fields),
        survey_dates=np.asarray([row["survey_date"] for row in observations]),
        authorized_transition_indices=np.asarray(authorized_indices, dtype=np.int64),
    )
    manifest = {
        "artifact_version": "ltpp_06_1253_single_annotator_observation_fields_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "section": "06-1253",
        "evidence_grade": "exploratory_single_annotator",
        "mapping_unsealed_for_machine_only": True,
        "secondary_isolation_required": True,
        "grid": {
            "shape_t_y_x": [9, len(y_values), len(x_values)],
            "nominal_resolution_m": args.resolution_m,
            "actual_dx_m": float(x_values[1] - x_values[0]),
            "actual_dy_m": float(y_values[1] - y_values[0]),
            "line_sigma_m": args.line_sigma_m,
        },
        "field_semantics": {
            "line_damage": "Gaussian distance field around mapped line-type distress centreline",
            "area_damage": "binary occupancy of mapped area-type distress extent",
            "combined_damage": "pointwise maximum of line_damage and area_damage",
            "claim_boundary": "mapped distress observation, not natural crack morphology or ground truth",
        },
        "observations": observations,
        "authorized_transition_indices": authorized_indices,
        "prohibited_transition_indices": [7],
        "inputs": {
            "primary_manifest": str(args.primary_manifest.resolve()),
            "primary_manifest_sha256": sha256(args.primary_manifest),
            "sealed_mapping_sha256": sha256(args.sealed_mapping),
            "interval_climate_features": str(args.interval_climate_features.resolve()),
            "interval_climate_features_sha256": sha256(args.interval_climate_features),
        },
        "outputs": {
            "fields_npz": str(fields_path.resolve()),
            "fields_npz_sha256": sha256(fields_path),
        },
    }
    manifest_path = args.output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output_root": str(args.output_root),
                "shape": manifest["grid"]["shape_t_y_x"],
                "authorized_transitions": authorized_indices,
                "fields_sha256": manifest["outputs"]["fields_npz_sha256"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
