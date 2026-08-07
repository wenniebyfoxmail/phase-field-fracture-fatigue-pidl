#!/usr/bin/env python3
"""Fail-closed preflight for the LTPP 06-1253 real-road FTS route."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


HASH_KEYS = {
    "snapshot_sha256",
    "ferrite_runtime_sha256",
    "reviewed_geojson_sha256",
}
MECHANICAL_COLUMNS = {
    "known_residual",
    "u",
    "v",
    "psi_plus",
    "psi_active",
    "alpha_bar",
    "f_alpha",
    "g_stiffness",
    "ell",
    "Gc_base",
}


def read_json(path: Path, label: str, blockers: list[str]) -> dict:
    if not path.is_file():
        blockers.append(f"missing_{label}:{path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        blockers.append(f"invalid_{label}:{exc}")
        return {}
    if not isinstance(payload, dict):
        blockers.append(f"invalid_{label}:root_not_object")
        return {}
    return payload


def is_sha256(value: object) -> bool:
    text = str(value).lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid-gate", type=Path, required=True)
    parser.add_argument("--forcing-audit", type=Path, required=True)
    parser.add_argument("--pairing-report", type=Path, required=True)
    parser.add_argument("--adjudicated-manifest", type=Path, required=True)
    parser.add_argument("--mechanical-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    blockers: list[str] = []
    warnings: list[str] = []
    grid = read_json(args.grid_gate, "grid_gate", blockers)
    forcing = read_json(args.forcing_audit, "forcing_audit", blockers)
    pairing = read_json(args.pairing_report, "pairing_report", blockers)
    adjudicated = read_json(args.adjudicated_manifest, "adjudicated_manifest", blockers)
    mechanical = read_json(args.mechanical_manifest, "mechanical_manifest", blockers)

    if grid:
        if grid.get("all_passed") is not True or grid.get("passed") != 9 or grid.get("total") != 9:
            blockers.append("grid_gate_not_9_of_9")

    if pairing:
        if pairing.get("status") != "paired_review_complete":
            blockers.append(f"pairing_not_complete:{pairing.get('status')}")
        if pairing.get("metrics_pass") is not True:
            blockers.append("pairing_metrics_not_passed")
        if pairing.get("sealed_mapping_read") is not True:
            blockers.append("blind_mapping_not_validly_unsealed")

    if adjudicated:
        if adjudicated.get("status") != "qualified":
            blockers.append("adjudicated_geometry_not_qualified")
        if adjudicated.get("uncertain_geometry_excluded") is not True:
            blockers.append("uncertain_geometry_not_excluded")
        if not is_sha256(adjudicated.get("reviewed_geojson_sha256")):
            blockers.append("reviewed_geojson_sha256_missing_or_invalid")
        if adjudicated.get("future_maps_used_during_annotation") is not False:
            blockers.append("future_map_label_leakage")

    climate_temperature = False
    climate_precipitation = False
    traffic_continuous = False
    moisture_observed = False
    if forcing:
        if forcing.get("section") != "06-1253" or forcing.get("ldw_section_id") != 2056:
            blockers.append("forcing_section_identity_mismatch")
        climate = forcing.get("climate", {})
        climate_temperature = climate.get("temperature", {}).get("status") == "available"
        climate_precipitation = climate.get("precipitation", {}).get("status") == "available"
        moisture_observed = climate.get("humidity", {}).get("status") == "available"
        traffic_continuous = forcing.get("traffic", {}).get("status") == "continuous_observed"
        if not climate_temperature:
            blockers.append("monthly_temperature_unavailable")
        if not climate_precipitation:
            blockers.append("monthly_precipitation_unavailable")
        if not traffic_continuous:
            warnings.append("traffic terms disabled: only five 1991-1992 snapshots exist")
        if not moisture_observed:
            warnings.append("moisture terms disabled: humidity and pavement moisture are absent")

    if mechanical:
        if mechanical.get("status") != "qualified":
            blockers.append("mechanical_package_not_qualified")
        if mechanical.get("section_id") != "06-1253":
            blockers.append("mechanical_section_identity_mismatch")
        if mechanical.get("source_kind") != "ltpp_observation_plus_ferrite_prior":
            blockers.append("mechanical_source_kind_must_declare_ferrite_prior")
        if mechanical.get("future_damage_used") is not False:
            blockers.append("mechanical_package_future_damage_leakage")
        columns = set(map(str, mechanical.get("field_columns", [])))
        missing_columns = sorted(MECHANICAL_COLUMNS.difference(columns))
        if missing_columns:
            blockers.append("mechanical_columns_missing:" + ",".join(missing_columns))
        for key in ("snapshot_sha256", "ferrite_runtime_sha256"):
            if not is_sha256(mechanical.get(key)):
                blockers.append(f"{key}_missing_or_invalid")
        fwd_dates = set(map(str, mechanical.get("fwd_calibration_dates", [])))
        expected_fwd = {
            "1989-11-14",
            "1991-06-10",
            "1993-07-14",
            "1995-10-24",
            "1997-02-28",
            "1998-04-07",
            "2003-05-15",
        }
        if not fwd_dates.issubset(expected_fwd) or not fwd_dates:
            blockers.append("fwd_calibration_dates_missing_or_unrecognized")

    candidate_authorization = {
        "hplus_low_temp": climate_temperature,
        "hplus_abs_temp_delta": climate_temperature,
        "hplus_monthly_precip": climate_precipitation,
        "hplus_log_traffic": traffic_continuous,
        "hplus_traffic_rate": traffic_continuous,
        "hplus_moisture": moisture_observed,
        "hplus_rain_7d": False,
        "traffic_temperature_interaction": traffic_continuous and climate_temperature,
        "traffic_moisture_interaction": traffic_continuous and moisture_observed,
    }
    authorized = not blockers
    payload = {
        "protocol_id": "ltpp_06_1253_real_route_preflight_v1",
        "section_id": "06-1253",
        "authorized_to_build_frozen_snapshot": authorized,
        "decision": "PASS" if authorized else "STOP_BEFORE_FIELD_ADAPTER",
        "blockers": blockers,
        "warnings": warnings,
        "candidate_authorization": candidate_authorization,
        "known_phase_field_terms_selectable": False,
        "source_claim": "hybrid road observation plus declared Ferrite mechanical prior",
        "prohibitions": [
            "no constant-filled mechanical fields",
            "no automatic v1-v5 crack candidates as observations",
            "no continuous traffic interpolation from five snapshots",
            "no moisture term without observed moisture",
            "no 7-day rain term from monthly precipitation",
            "no PIDL training before this preflight passes",
        ],
        "input_sha256": {
            label: hashlib.sha256(path.read_bytes()).hexdigest()
            for label, path in {
                "grid_gate": args.grid_gate,
                "forcing_audit": args.forcing_audit,
                "pairing_report": args.pairing_report,
                "adjudicated_manifest": args.adjudicated_manifest,
                "mechanical_manifest": args.mechanical_manifest,
            }.items()
            if path.is_file()
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": payload["decision"],
                "blocker_count": len(blockers),
                "authorized_terms": sorted(
                    term for term, allowed in candidate_authorization.items() if allowed
                ),
            }
        )
    )
    return 0 if authorized else 2


if __name__ == "__main__":
    raise SystemExit(main())
