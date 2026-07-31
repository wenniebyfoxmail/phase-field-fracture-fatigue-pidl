from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "producer_handoffs" / "toy_to_road_independent_fem_20260731"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def test_parent_lock_is_latest_c83_c86_baseline() -> None:
    lock = load_json(HANDOFF / "PARENT_LOCK.json")
    assert lock["parent_reference_id"] == "hard5_eta0_u012_5step_20260729"
    assert lock["event"] == {"first_hit": 83, "confirmed": 86}
    assert lock["physics"]["eta"] == 0.0
    assert lock["physics"]["n_substeps"] == 5
    assert lock["mesh"]["num_elem"] == 86408
    assert lock["state_semantics_id"] == "cycle_peak_coherent_v1"


def test_parent_lock_keeps_physical_source_and_analysis_bundle_authoritative() -> None:
    lock = load_json(HANDOFF / "PARENT_LOCK.json")
    assert (
        lock["physical_source_package_id"]
        == "Hard5_eta0_5step_Umax_011_012_013_20260729"
    )
    assert lock["physical_source_role"] == "consumed_physical_bytes_and_windows_paths"
    analysis_bundle = lock["authoritative_analysis_bundle"]
    assert analysis_bundle["role"] == "consumed_mac_analysis_bundle_contract"
    assert analysis_bundle["bundle_id"] == "bundle::hard5_eta0_u012_5step_20260729"
    assert (
        analysis_bundle["package_id"]
        == "Hard5_eta0_5step_Umax_0.12_20260729"
    )
    assert (
        analysis_bundle["bundle_manifest_sha256"]
        == "ce36913ed75bbf2830a3016c442953317d6e968eff074e73c988704dbec118b3"
    )
    assert "non_authoritative_logical_mac_bundle_alias" not in lock


def test_parent_lock_prohibits_road_sensor_claims_and_network_training() -> None:
    lock = load_json(HANDOFF / "PARENT_LOCK.json")
    policy = lock["immutable_policy"]
    assert not policy["latent_fem_fields_are_direct_road_sensors"]
    assert not policy["pidl_network_training_authorized"]
    assert policy["claim_scope"] == "synthetic_whole_trajectory_loto_only"
    assert not policy["road_validation_authorized"]
