import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from road_observation_contract import (  # noqa: E402
    STATE_FIELDS,
    build_assimilated_state_package,
    default_road_observation_operator_spec,
    validate_assimilated_state_package,
    validate_operator_spec,
)


def test_hidden_fields_cannot_be_declared_direct_sensors() -> None:
    spec = default_road_observation_operator_spec()
    assert validate_operator_spec(spec) == []
    assert all(not channel["directly_observable"] for channel in spec["latent_state"].values())
    assert spec["channels"]["fem_raw_energy_probe"]["evidence_class_when_measured"] == "fem_oracle"


def test_operator_validation_rejects_oracle_relabeling() -> None:
    spec = default_road_observation_operator_spec()
    spec["channels"]["fem_raw_energy_probe"]["evidence_class_when_measured"] = "real_observation"
    errors = validate_operator_spec(spec)
    assert "FEM raw energy must remain fem_oracle" in errors


def test_frozen_state_package_tracks_observed_and_prior_sources(tmp_path: Path) -> None:
    node_count = 5
    dataset = tmp_path / "dataset.npz"
    analysis = tmp_path / "analysis.npz"
    output = tmp_path / "state.npz"
    np.savez_compressed(
        dataset,
        coordinates=np.arange(node_count * 2, dtype=np.float32).reshape(node_count, 2),
        areas=np.linspace(1.0, 2.0, node_count, dtype=np.float32),
        edge_index=np.array([[0, 1, 2, 3], [1, 2, 3, 4]], dtype=np.int64),
        edge_attr=np.ones((4, 2), dtype=np.float32),
        physics_family=np.asarray("unit_test_family"),
        trajectory_id=np.asarray("unit_test_trajectory"),
    )
    state = np.zeros((node_count, len(STATE_FIELDS)), dtype=np.float32)
    mask = np.array([True, False, False, True, False])
    np.savez_compressed(analysis, analysis_c87=state, observed_mask=mask)

    metadata = build_assimilated_state_package(
        operator_dataset=dataset,
        analysis_artifact=analysis,
        output_path=output,
        observation_operator_id="unit_test_oracle",
        prior_id="unit_test_prior",
        cycle=87,
    )
    assert metadata["source_evidence_class"] == "fem_oracle"
    assert metadata["real_road_compatible"] is False
    assert validate_assimilated_state_package(output) == []

    with np.load(output, allow_pickle=False) as package:
        observed = package["observed_channel_mask"]
        source = package["source_code"]
        std = package["state_std"]
        raw_index = STATE_FIELDS.index("log10_psi_raw")
        assert np.array_equal(observed[:, raw_index], mask)
        assert np.all(source[mask, raw_index] == 1)
        assert np.all(source[~mask, raw_index] == 2)
        assert np.all(source[:, :raw_index] == 0)
        assert np.isnan(std).all()
        saved_metadata = json.loads(str(package["metadata_json"].item()))
        assert saved_metadata["uncertainty_status"] == "uncalibrated_not_available"


def test_zero_uncertainty_is_rejected_when_uncalibrated(tmp_path: Path) -> None:
    path = tmp_path / "invalid.npz"
    node_count = 2
    metadata = {
        "source_evidence_class": "fem_oracle",
        "real_road_compatible": False,
        "uncertainty_status": "uncalibrated_not_available",
    }
    np.savez_compressed(
        path,
        schema_version=np.asarray("road_assimilated_state_v1"),
        metadata_json=np.asarray(json.dumps(metadata)),
        cycle=np.asarray(87),
        state_fields=np.asarray(STATE_FIELDS),
        coordinates=np.zeros((node_count, 2)),
        areas=np.ones(node_count),
        edge_index=np.zeros((2, 0), dtype=np.int64),
        edge_attr=np.zeros((0, 1)),
        state_mean=np.zeros((node_count, len(STATE_FIELDS))),
        state_std=np.zeros((node_count, len(STATE_FIELDS))),
        observed_channel_mask=np.zeros((node_count, len(STATE_FIELDS)), dtype=bool),
        source_code=np.zeros((node_count, len(STATE_FIELDS)), dtype=np.uint8),
    )
    assert "uncalibrated uncertainty must be represented by NaN, not zero" in validate_assimilated_state_package(path)
