import json
from pathlib import Path
import sys

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from road_observation_state_bundle import (  # noqa: E402
    BUNDLE_VERSION,
    ENVIRONMENT_CHANNELS,
    GLOBAL_OBSERVATION_CHANNELS,
    NODE_OBSERVATION_CHANNELS,
    NODE_OBSERVATION_EVIDENCE,
    STATE_FIELDS,
    TRAFFIC_CHANNELS,
    agent2_innovation_packet,
    validate_agent2_packet,
    validate_bundle,
    validate_observation_channels,
    verify_sha256,
)


def _write_valid_bundle(path: Path, *, t_count: int = 1, node_count: int = 3) -> None:
    state = np.zeros((t_count, node_count, len(STATE_FIELDS)), dtype=np.float32)
    std = np.full_like(state, np.nan)
    node_values = np.full((t_count, node_count, len(NODE_OBSERVATION_CHANNELS)), np.nan, dtype=np.float32)
    node_mask = np.zeros_like(node_values, dtype=bool)
    global_values = np.full((t_count, len(GLOBAL_OBSERVATION_CHANNELS)), np.nan, dtype=np.float32)
    traffic_values = np.full((t_count, len(TRAFFIC_CHANNELS)), np.nan, dtype=np.float32)
    environment_values = np.full((t_count, len(ENVIRONMENT_CHANNELS)), np.nan, dtype=np.float32)
    metadata = {
        "schema_version": BUNDLE_VERSION,
        "evidence_class": "synthetic",
        "coordinate_frame": "unit_test_xy",
        "registration_id": "unit_test_registration",
        "uncertainty_kind": "std",
        "uncertainty_status": "uncalibrated_not_available",
        "source_sha256": {"fixture": "0" * 64},
        "source_schema_versions": {"fixture": "unit_test_v1"},
        "real_road_compatible": False,
    }
    np.savez_compressed(
        path,
        schema_version=np.asarray(BUNDLE_VERSION),
        metadata_json=np.asarray(json.dumps(metadata)),
        state_fields=np.asarray(STATE_FIELDS),
        coordinates=np.zeros((node_count, 2), dtype=np.float32),
        areas=np.ones(node_count, dtype=np.float32),
        edge_index=np.zeros((2, 0), dtype=np.int64),
        edge_attr=np.zeros((0, 1), dtype=np.float32),
        state_mean=state,
        state_std=std,
        observed_channel_mask=np.zeros_like(state, dtype=bool),
        source_code=np.zeros_like(state, dtype=np.uint8),
        node_observation_channels=np.asarray(NODE_OBSERVATION_CHANNELS),
        node_observation_evidence=np.asarray(NODE_OBSERVATION_EVIDENCE),
        node_observation_values=node_values,
        node_observation_mask=node_mask,
        global_observation_channels=np.asarray(GLOBAL_OBSERVATION_CHANNELS),
        global_observation_evidence=np.asarray(["synthetic"] * len(GLOBAL_OBSERVATION_CHANNELS)),
        global_observation_values=global_values,
        global_observation_mask=np.zeros_like(global_values, dtype=bool),
        timestamp=np.asarray([""] * t_count),
        timestamp_mask=np.zeros(t_count, dtype=bool),
        equivalent_load_index=np.full(t_count, np.nan),
        equivalent_load_index_mask=np.zeros(t_count, dtype=bool),
        delta_t=np.full(t_count, np.nan),
        delta_t_mask=np.zeros(t_count, dtype=bool),
        traffic_channels=np.asarray(TRAFFIC_CHANNELS),
        traffic_values=traffic_values,
        traffic_mask=np.zeros_like(traffic_values, dtype=bool),
        environment_channels=np.asarray(ENVIRONMENT_CHANNELS),
        environment_values=environment_values,
        environment_mask=np.zeros_like(environment_values, dtype=bool),
        maintenance_reset=np.zeros(t_count, dtype=bool),
        maintenance_reset_declared=np.zeros(t_count, dtype=bool),
        maintenance_event_id=np.asarray([""] * t_count),
        state_segment_id=np.zeros(t_count, dtype=np.int32),
    )


def _rewrite(path: Path, **updates: np.ndarray) -> None:
    with np.load(path, allow_pickle=False) as package:
        arrays = {name: np.asarray(package[name]) for name in package.files}
    arrays.update(updates)
    np.savez_compressed(path, **arrays)


def test_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"actual")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verify_sha256(path, "0" * 64)


def test_latent_fields_cannot_be_relabelled_as_road_sensors() -> None:
    errors = validate_observation_channels(
        ["psi_raw", "fatigue_history", "log10_psi_raw_oracle"],
        ["real", "synthetic", "oracle"],
    )
    assert any("psi_raw" in error for error in errors)
    assert any("fatigue_history" in error for error in errors)
    assert not any("log10_psi_raw_oracle" in error for error in errors)


def test_uncalibrated_uncertainty_requires_nan(tmp_path: Path) -> None:
    path = tmp_path / "bundle.npz"
    _write_valid_bundle(path)
    assert validate_bundle(path) == []
    _rewrite(path, state_std=np.zeros((1, 3, len(STATE_FIELDS)), dtype=np.float32))
    assert "uncalibrated uncertainty must be all NaN" in validate_bundle(path)


def test_missing_observation_requires_nan_and_false_mask(tmp_path: Path) -> None:
    path = tmp_path / "bundle.npz"
    _write_valid_bundle(path)
    with np.load(path, allow_pickle=False) as package:
        values = np.asarray(package["node_observation_values"]).copy()
    values[0, 0, 0] = 0.0
    _rewrite(path, node_observation_values=values)
    assert "node observations missing entries must be NaN with mask=false" in validate_bundle(path)


def test_maintenance_reset_requires_event_and_new_segment(tmp_path: Path) -> None:
    path = tmp_path / "bundle.npz"
    _write_valid_bundle(path, t_count=2)
    _rewrite(
        path,
        maintenance_reset=np.asarray([False, True]),
        maintenance_reset_declared=np.asarray([False, False]),
        maintenance_event_id=np.asarray(["", ""]),
        state_segment_id=np.asarray([0, 0], dtype=np.int32),
    )
    errors = validate_bundle(path)
    assert "maintenance reset requires declared metadata and event id" in errors
    assert "maintenance reset must start a new state segment" in errors


def test_missing_road_channels_remain_absent_in_agent2_packet(tmp_path: Path) -> None:
    path = tmp_path / "bundle.npz"
    _write_valid_bundle(path)
    packet = agent2_innovation_packet(path)
    assert validate_agent2_packet(packet) == []
    assert packet["decision_eligible"] is False
    assert all(item["value"] is None and item["mask"] is False for item in packet["innovations"].values())
    assert packet["audit_only_oracle"]["values_exported_to_trigger"] is False
