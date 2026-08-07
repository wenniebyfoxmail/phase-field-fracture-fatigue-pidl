#!/usr/bin/env python3
"""Fail-closed preflight for observation-only LTPP geometry/climate FTS."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from freeze_select.road_observation import LTPP_06_1253_CANDIDATE_STATUS, OBSERVED


EXPECTED_DATES = {
    "19910610", "19951024", "19970228", "19980407", "20010913",
    "20030514", "20071106", "20120417", "20150302",
}


def load_or_none(path: Path):
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_adjudicated_manifest(data: dict | None) -> list[str]:
    if data is None:
        return ["missing_adjudicated_geometry_manifest"]
    blockers = []
    if data.get("section") != "06-1253": blockers.append("wrong_adjudicated_section")
    if data.get("status") != "qualified": blockers.append("adjudicated_status_not_qualified")
    if data.get("future_geometry_used") is not False: blockers.append("future_geometry_boundary_not_clean")
    if data.get("pairing_metrics_passed") is not True: blockers.append("pairing_metrics_not_passed")
    records = data.get("geometry_records") or []
    if {str(record.get("survey_date")) for record in records} != EXPECTED_DATES:
        blockers.append("adjudicated_dates_incomplete")
    for record in records:
        path = Path(str(record.get("path", "")))
        expected = record.get("sha256")
        if not path.is_file() or not expected or file_sha256(path) != expected:
            blockers.append(f"invalid_geometry_record:{record.get('survey_date')}")
    if not data.get("reviewed_package_sha256"):
        blockers.append("missing_reviewed_package_sha256")
    return blockers


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid-gate", type=Path, required=True)
    parser.add_argument("--forcing-audit", type=Path, required=True)
    parser.add_argument("--interval-climate-features", type=Path, required=True)
    parser.add_argument("--pairing-readiness", type=Path, required=True)
    parser.add_argument("--adjudicated-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    grid = load_or_none(args.grid_gate)
    forcing = load_or_none(args.forcing_audit)
    interval_climate = load_or_none(args.interval_climate_features)
    pairing = load_or_none(args.pairing_readiness)
    adjudicated = load_or_none(args.adjudicated_manifest)
    blockers = []

    if grid is None or grid.get("all_passed") is not True or grid.get("passed") != 9:
        blockers.append("physical_grid_gate_not_passed")
    if grid and grid.get("semantic_boundary") != "ink outputs are not crack masks":
        blockers.append("grid_semantic_boundary_missing")
    climate = (forcing or {}).get("climate") or {}
    if (climate.get("temperature") or {}).get("status") != "available":
        blockers.append("monthly_temperature_unavailable")
    if (climate.get("precipitation") or {}).get("status") != "available":
        blockers.append("monthly_precipitation_unavailable")
    interval_rows = (interval_climate or {}).get("intervals") or []
    primary_candidates = (interval_climate or {}).get("primary_candidates") or {}
    if (
        len(interval_rows) != 8
        or sum(row.get("confirmatory_forcing_authorized") is True for row in interval_rows) != 7
        or interval_rows[-1].get("confirmatory_forcing_authorized") is not False
        or set(primary_candidates) != {
            "low_temp_exposure", "temp_variation_rate", "precipitation_rate"
        }
    ):
        blockers.append("interval_climate_features_not_qualified")
    if pairing is None or pairing.get("status") != "ready":
        blockers.append("blind_pairing_not_ready")
    blockers.extend(validate_adjudicated_manifest(adjudicated))

    decision = (
        "READY_FOR_OBSERVATION_FIELD_ADAPTER"
        if not blockers else "STOP_BEFORE_OBSERVATION_FIELD_ADAPTER"
    )
    report = {
        "decision": decision,
        "section": "06-1253",
        "route": "observation_only_geometry_climate",
        "mechanical_manifest_required": False,
        "prohibited_fabricated_fields": [
            "known_residual", "u", "v", "psi_plus", "psi_active",
            "alpha_bar", "f_alpha", "g_stiffness", "ell", "Gc_base",
        ],
        "candidate_status": LTPP_06_1253_CANDIDATE_STATUS,
        "authorized_observed_candidates": sorted(
            name for name, status in LTPP_06_1253_CANDIDATE_STATUS.items()
            if status == OBSERVED
        ),
        "blockers": blockers,
        "inputs": {
            "grid_gate": str(args.grid_gate),
            "forcing_audit": str(args.forcing_audit),
            "interval_climate_features": str(args.interval_climate_features),
            "pairing_readiness": str(args.pairing_readiness),
            "adjudicated_manifest": str(args.adjudicated_manifest),
        },
        "next_if_ready": (
            "build leakage-safe frozen damage transitions and weak systems"
            if not blockers else "complete independent pairing and adjudication"
        ),
        "claim_boundary": (
            "This route may test temperature/precipitation-conditioned geometry selection only. "
            "It cannot support traffic, moisture, mechanics, phase-field-teacher, or cross-road claims."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
