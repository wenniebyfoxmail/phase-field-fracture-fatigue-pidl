#!/usr/bin/env python3
"""Fail-closed static validator for the frozen, non-launchable G4 design."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_CANONICAL_SHA256 = "a6de35f131bf046261a2496c0acffd23b3860bb58288e604a1284a780f9e2d91"
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
    allowlist = {
        row.get("id"): row
        for row in payload.get("producer_input_allowlist", [])
        if isinstance(row, dict)
    }
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
        "morphology_definition": payload.get("field_gate", {}).get(
            "morphology_definition"
        ) == {
            "grid": "64x64_fixed_square_-0.5_to_0.5",
            "damage_support_threshold": 0.25,
            "connectivity": "four_neighbor",
            "mirror_axis": "y=0",
            "mirror_weighting": "minimum_paired_cell_area",
            "mirror_min_paired_area_coverage": 0.5,
            "actual_exact_domain_paired_area_coverage": 0.5193230827427459,
            "pidl_triangle_row_coordinate_atol": 3e-8,
        },
        "blind_before_unblind": payload.get("blind_analysis", {}).get("opaque_arm_ids") is True
        and payload.get("blind_analysis", {}).get("metrics_sealed_before_unblinding") is True,
        "requirement_catalog_complete": set(payload.get("launch_blockers", []))
        == EXPECTED_BLOCKERS,
        "exact_fem_input_qualified": snapshot.get(
            "current_external_input_blockers"
        ) == []
        and prerequisite_status.get("exact_peak_c76_c82_c83_fem_bundle")
        == "pass_exact_request_27_v2_1"
        and allowlist.get("u012_c76_c82_c83_exact_peak_fem_manifest") == {
            "id": "u012_c76_c82_c83_exact_peak_fem_manifest",
            "status": "qualified_request_27_v2_1",
            "manifest_sha256": "3a3d4cdd83a7dbb0303c9d77ad84e042cd661e3cfc9dee0b0fb7cca24fe5126e",
            "sha256s_sha256": "319ed492d93766f0ff442e04e9f1684e645b0a538ea01f45b7078da1b8fe85e1",
            "validation_receipt_sha256": "736839ecd475516c6e7e140e8e6ca06a4cb797630184696a437aafc6315285f8",
        },
        "exact_projector_v2_qualified": prerequisite_status.get(
            "contained_domain_projector"
        ) == "pass_exact_geometry_v2"
        and allowlist.get("u012_contained_domain_projector_manifest", {}).get(
            "status"
        ) == "qualified_exact_geometry_v2"
        and allowlist.get("u012_contained_domain_projector_manifest", {}).get(
            "builder_content_sha256"
        ) == "2782085ab78cbfd82a04b485422d642fb0b81275d56b695673fc5f43aa6612e7"
        and allowlist.get("u012_contained_domain_projector_manifest", {}).get(
            "npz_sha256"
        ) == "4dfc62e0dc14990254dff01d650e6c3962d725dd934e360b95ae6a593695c253"
        and allowlist.get("u012_contained_domain_projector_manifest", {}).get(
            "analysis_content_sha256"
        ) == "fbbe2b75a9733d4e9f242f5e3722a7abecee44323eb45988b34396203fabc4da"
        and allowlist.get("u012_contained_domain_projector_manifest", {}).get(
            "pidl_triangle_geometry_sha256"
        ) == "e1f215bdd8e13514d38db1a8f020f60e29e5884d875a15d82e6ff0271ca8ddbd",
        "post_run_evidence_not_misclassified": snapshot.get(
            "post_run_evidence_not_prelaunch_blockers"
        )
        == [
            "full_ab_runtime_receipts",
            "sealed_blind_metrics",
            "per_arm_first_detect_receipts",
        ]
        and prerequisite_status.get("g4_validator_blind_analyzer_runtime_receipt")
        == "real_analyzer_pass_local_full_ab_receipts_post_run",
        "post_request27_prelaunch_closure_explicit": snapshot.get(
            "prelaunch_closure_after_request_27"
        )
        == [
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
        "status": "pass_ready_for_prelaunch_lock_training_unauthorized" if all(checks.values()) else "fail",
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
