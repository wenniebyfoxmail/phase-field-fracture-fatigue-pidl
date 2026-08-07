#!/usr/bin/env python3
"""Fail-closed gate for the LTPP 06-1253 single-annotator exploratory route."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_CONFIRMATORY_BLOCKERS = {
    "blind_pairing_not_ready",
    "missing_adjudicated_geometry_manifest",
}
EXPECTED_CANDIDATES = {
    "low_temp_exposure",
    "precipitation_rate",
    "temp_variation_rate",
}


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirmatory-preflight", type=Path, required=True)
    parser.add_argument("--primary-locked-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    confirmatory = load_json(args.confirmatory_preflight)
    primary = load_json(args.primary_locked_manifest)
    blockers: list[str] = []

    if confirmatory.get("route") != "observation_only_geometry_climate":
        blockers.append("unexpected_confirmatory_route")
    if confirmatory.get("decision") != "STOP_BEFORE_OBSERVATION_FIELD_ADAPTER":
        blockers.append("unexpected_confirmatory_preflight_decision")
    if set(confirmatory.get("blockers", [])) != EXPECTED_CONFIRMATORY_BLOCKERS:
        blockers.append("confirmatory_blockers_not_limited_to_annotation_evidence")
    if confirmatory.get("mechanical_manifest_required") is not False:
        blockers.append("mechanical_manifest_boundary_changed")
    if set(confirmatory.get("authorized_observed_candidates", [])) != EXPECTED_CANDIDATES:
        blockers.append("authorized_candidate_set_changed")

    files = primary.get("files")
    if primary.get("manifest_version") != "ltpp_06_1253_primary_locked_v2":
        blockers.append("unexpected_primary_manifest_version")
    if primary.get("all_locked") is not True:
        blockers.append("primary_not_fully_locked")
    if not isinstance(files, list) or len(files) != 9:
        blockers.append("primary_manifest_must_contain_nine_maps")
        files = []
    else:
        expected_ids = {f"P{index:02d}" for index in range(1, 10)}
        if {row.get("blind_id") for row in files} != expected_ids:
            blockers.append("primary_blind_id_set_mismatch")
        if not all(row.get("locked") is True for row in files):
            blockers.append("primary_file_not_locked")
        if not all(row.get("schema_version") == "line_area_v2" for row in files):
            blockers.append("primary_file_not_line_area_v2")
        if not all(
            isinstance(row.get("sha256"), str) and len(row["sha256"]) == 64
            for row in files
        ):
            blockers.append("primary_file_hash_missing_or_invalid")
        if sum(int(row.get("features", 0)) for row in files) != primary.get("total_features"):
            blockers.append("primary_feature_total_mismatch")
        if sum(int(row.get("lines", 0)) for row in files) != primary.get("total_lines"):
            blockers.append("primary_line_total_mismatch")
        if sum(int(row.get("polygons", 0)) for row in files) != primary.get("total_polygons"):
            blockers.append("primary_polygon_total_mismatch")

    decision = (
        "READY_FOR_EXPLORATORY_SINGLE_ANNOTATOR_FIELD_ADAPTER"
        if not blockers
        else "STOP_BEFORE_EXPLORATORY_FIELD_ADAPTER"
    )
    payload = {
        "section": "06-1253",
        "route": "observation_only_geometry_climate_single_annotator",
        "evidence_grade": "exploratory_single_annotator",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "blockers": blockers,
        "confirmatory_requirements_not_satisfied": sorted(EXPECTED_CONFIRMATORY_BLOCKERS),
        "authorized_observed_candidates": sorted(EXPECTED_CANDIDATES),
        "primary_geometry": {
            "maps": len(files),
            "features": primary.get("total_features"),
            "lines": primary.get("total_lines"),
            "polygons": primary.get("total_polygons"),
            "all_locked": primary.get("all_locked"),
        },
        "allowed_outputs": [
            "exploratory frozen observation-field reconstruction",
            "exploratory stability frequencies for authorized climate candidates",
            "exploratory comparison with single-shot and joint-training baselines",
        ],
        "prohibited_claims": [
            "ground-truth crack geometry",
            "annotation accuracy or cross-annotator reliability",
            "confirmatory real-road support recovery",
            "traffic, moisture, mechanics, or phase-field-teacher discovery",
            "natural crack width, microscopic morphology, or centimetre-scale true tip accuracy",
            "cross-road generalization",
        ],
        "future_upgrade_trigger": (
            "lock an independent secondary line-area-v2 pass, run blind pairing, "
            "adjudicate every mismatch, and issue a hashed adjudicated manifest"
        ),
        "inputs": {
            "confirmatory_preflight": str(args.confirmatory_preflight.resolve()),
            "confirmatory_preflight_sha256": sha256(args.confirmatory_preflight),
            "primary_locked_manifest": str(args.primary_locked_manifest.resolve()),
            "primary_locked_manifest_sha256": sha256(args.primary_locked_manifest),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "blockers": blockers}))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
