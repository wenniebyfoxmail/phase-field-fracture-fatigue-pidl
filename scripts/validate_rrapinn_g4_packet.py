#!/usr/bin/env python3
"""Fail-closed static validator for the frozen, non-launchable G4 design."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_CANONICAL_SHA256 = "5f2ce2fb06b01e8e5dbfbd99310cafecb7090cc43e882c583ad4d07dfc959c94"
EXPECTED_BLOCKERS = {
    "qualified_c60_restart_materializer",
    "true_mechanical_residual_field_export",
    "exact_peak_c76_c82_c83_fem_bundle",
    "boundary_only_first_detect_receipt",
    "c60_to_c61_control_replay_sentinel",
    "c60_c76_c82_lambda_contribution_audit",
    "contained_domain_projector",
    "g4_validator_blind_analyzer_runtime_receipt",
}


def _canonical_sha256(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _all_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _all_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _all_strings(item)


def _contains_heldout_identifier(payload: dict) -> bool:
    forbidden = ("u0.11", "u0.13", "u011", "u013", "umax011", "umax013")
    return any(
        marker in text.lower().replace("_", "").replace("-", "")
        for text in _all_strings(payload)
        for marker in forbidden
    )


def validate(payload: dict) -> dict:
    arms = payload.get("arms", [])
    snapshot = payload.get("qualification_snapshot", {})
    prerequisite_status = {
        row.get("id"): row.get("status")
        for row in snapshot.get("prelaunch_prerequisites", [])
        if isinstance(row, dict)
    }
    checks = {
        "schema": payload.get("schema") == "rrapinn-g4-u012-preregistration-v1",
        "frozen_not_authorized": payload.get("design_frozen") is True
        and payload.get("training_authorized") is False,
        "development_only": payload.get("development_case") == "U0.12"
        and not _contains_heldout_identifier(payload),
        "c60_restart": payload.get("start_state") == {
            "label": "c60_unloaded_post_commit",
            "raw_step": 300,
            "next_raw_step": 301,
            "checkpoint_sha256": "771bf8122c34097ddaee55e9952c3bef187aa320dfcd02eed148febe6e10e729",
            "model_sha256": "1316984f53297075dccadd38efd04972ce3942caa294b4b0a4f61c3c87b10d41",
            "history_length": 301,
            "future_history_forbidden": True,
        },
        "exact_two_arms": len(arms) == 2
        and arms[0] == {"role": "control", "mechanical_risk_mode": "absent"}
        and arms[1] == {
            "role": "candidate",
            "mechanical_risk_mode": "on",
            "alpha": 0.85,
            "lambda": 0.000549728557462236,
            "E_ref": 1.0,
            "L_ref": 1.0,
        },
        "baseline_optimizer": payload.get("optimizer") == {
            "rprop_epochs": 10000,
            "lbfgs_epochs": 0,
            "relative_tolerance": 5e-7,
        },
        "first_detect_not_confirmation": payload.get("first_detect", {}).get("truth_cycle") == 83
        and payload.get("first_detect", {}).get("confirmation_cycle_used") is False
        and payload.get("first_detect", {}).get("control_expected_cycle") == 89
        and payload.get("first_detect", {}).get("candidate_allowed_cycles") == [80, 86]
        and payload.get("first_detect", {}).get("candidate_must_be_strictly_closer_to_truth") is True
        and payload.get("first_detect", {}).get("hard_outer_cycle") == 92
        and payload.get("first_detect", {}).get("boundary_x_min") == 0.48
        and payload.get("first_detect", {}).get("damage_threshold") == 0.95
        and payload.get("first_detect", {}).get("minimum_nodes") == 3
        and payload.get("first_detect", {}).get("energy_fallback_is_headline") is False,
        "residual_thresholds": payload.get("residual_gate", {}).get(
            "c76_cvar99_candidate_over_control_max"
        ) == 0.9
        and payload.get("residual_gate", {}).get(
            "c82_cvar99_candidate_over_control_max"
        ) == 0.8
        and payload.get("residual_gate", {}).get("mean_candidate_over_control_max") == 1.05,
        "field_thresholds": payload.get("field_gate", {}).get(
            "headline_domain"
        ) == "hash_locked_contained_projection_only"
        and payload.get("field_gate", {}).get("absolute_support_iou_min") == 0.1
        and payload.get("field_gate", {}).get("absolute_support_area_ratio_range") == [0.5, 2.0],
        "blind_before_unblind": payload.get("blind_analysis", {}).get("opaque_arm_ids") is True
        and payload.get("blind_analysis", {}).get("metrics_sealed_before_unblinding") is True,
        "requirement_catalog_complete": set(payload.get("launch_blockers", []))
        == EXPECTED_BLOCKERS,
        "current_external_input_blocker_exact": snapshot.get(
            "current_external_input_blockers"
        )
        == ["exact_peak_c76_c82_c83_fem_bundle"]
        and prerequisite_status.get("exact_peak_c76_c82_c83_fem_bundle")
        == "blocked_external_request_27",
        "post_run_evidence_not_misclassified": snapshot.get(
            "post_run_evidence_not_prelaunch_blockers"
        )
        == [
            "full_ab_runtime_receipts",
            "sealed_blind_metrics",
            "per_arm_first_detect_receipts",
        ]
        and prerequisite_status.get("g4_validator_blind_analyzer_runtime_receipt")
        == "framework_qualified_full_ab_receipts_post_run",
        "post_request27_prelaunch_closure_explicit": snapshot.get(
            "prelaunch_closure_after_request_27"
        )
        == [
            "independently_validate_exact_peak_fem_package",
            "lock_fem_and_input_hashes_into_packet",
            "seal_analysis_code_hash",
            "fresh_independent_launch_gate",
            "explicit_user_launch_authorization",
        ],
        "archive_routing_qualified": snapshot.get("archive_routing")
        == "qualified_canonical_target_via_checkout_compatibility_symlink",
        "host_path_access_ledger_required": payload.get("runtime_gate", {}).get(
            "host_path_access_ledger_required"
        )
        is True,
        "complete_packet_frozen": _canonical_sha256(payload) == EXPECTED_CANONICAL_SHA256,
    }
    return {
        "status": "pass_frozen_design_launch_blocked" if all(checks.values()) else "fail",
        "checks": checks,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("packet", type=Path)
    args = ap.parse_args()
    payload = json.loads(args.packet.read_text(encoding="utf-8"))
    result = validate(payload)
    print(json.dumps(result, indent=2))
    if result["status"] != "pass_frozen_design_launch_blocked":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
