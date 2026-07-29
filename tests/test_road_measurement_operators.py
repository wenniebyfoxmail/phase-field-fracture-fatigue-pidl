from pathlib import Path
import sys

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from road_measurement_operators import (  # noqa: E402
    HANDOFF_VERSION,
    MeasurementRecord,
    adapt_fwd_observation,
    adapt_handoff_to_state_bundle_v1_observations,
    adapt_maintenance_event,
    adapt_registered_crack_observation,
    adapt_strain_sensor,
    adapt_temperature_time,
    adapt_wim_observation,
    assess_identifiability,
    build_measurement_handoff,
    derive_psi_raw_estimate_from_strain,
    estimate_small_strain_from_displacement,
    measurement_operator_spec,
    missing_record,
    validate_measurement_handoff_npz,
    validate_registration_contract,
    validate_timestamp,
    write_measurement_handoff_npz,
)


TIMESTAMP = "2026-07-29T12:00:00+00:00"


def registration() -> dict:
    return {
        "coordinate_frame_id": "camera_1",
        "target_frame_id": "road_asset_1",
        "registration_id": "reg_1",
        "transform_3x3": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "uncertainty_std_m": 0.001,
        "quality_score": 0.9,
        "source_sha256": {"image": "a" * 64},
    }


def test_timestamp_requires_timezone() -> None:
    with pytest.raises(ValueError, match="timezone"):
        validate_timestamp("2026-07-29T12:00:00")
    assert validate_timestamp(TIMESTAMP) == TIMESTAMP


def test_registration_requires_transform_uncertainty_and_hash() -> None:
    valid = validate_registration_contract(registration())
    assert valid["registration_id"] == "reg_1"
    broken = registration()
    broken["source_sha256"] = {"image": "short"}
    with pytest.raises(ValueError, match="SHA-256"):
        validate_registration_contract(broken)


@pytest.mark.parametrize("channel", ["alpha", "alpha_bar", "g_alpha", "psi_raw", "psi_raw_oracle", "psi_active"])
def test_latent_fields_are_rejected_as_direct_measurements(channel: str) -> None:
    with pytest.raises(ValueError, match="latent field"):
        MeasurementRecord(
            operator_id="bad",
            family="strain_sensor",
            channel_names=(channel,),
            units=("1",),
            values=np.asarray([[1.0]]),
            mask=np.asarray([[True]]),
            std=np.asarray([[0.1]]),
            timestamp=TIMESTAMP,
            evidence_class="real_measurement",
            registration=registration(),
            metadata={},
        ).validate()


def test_missing_values_require_nan_and_false_mask() -> None:
    record = missing_record(
        operator_id="missing_strain",
        family="strain_sensor",
        channel_names=("strain_axial",),
        units=("1",),
        timestamp=TIMESTAMP,
        evidence_class="real_measurement",
        registration=registration(),
    )
    assert np.isnan(record.values).all()
    assert not record.mask.any()
    broken = MeasurementRecord(**{**record.__dict__, "values": np.zeros_like(record.values)})
    with pytest.raises(ValueError, match="missing entries"):
        broken.validate()


def test_registered_crack_adapter_carries_units_and_registration() -> None:
    record = adapt_registered_crack_observation(
        crack_probability=[0.2, 0.9],
        mask=[True, True],
        std=[0.1, 0.05],
        timestamp=TIMESTAMP,
        evidence_class="real_measurement",
        registration=registration(),
        source_kind="registered_image_segmentation",
    )
    assert record.units == ("1",)
    assert record.registration["target_frame_id"] == "road_asset_1"


def test_dic_displacement_to_small_strain_is_geometrically_correct() -> None:
    coordinates = np.asarray([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=float)
    # u_x = 0.02 x + 0.01 y; u_y = -0.01 x + 0.04 y
    displacement = np.column_stack(
        (0.02 * coordinates[:, 0] + 0.01 * coordinates[:, 1], -0.01 * coordinates[:, 0] + 0.04 * coordinates[:, 1])
    )
    edges = np.asarray([[0, 0, 1, 1, 2, 2, 3, 3], [1, 2, 0, 3, 0, 3, 1, 2]])
    strain, mask = estimate_small_strain_from_displacement(coordinates, displacement, edges, np.ones(4, dtype=bool))
    assert mask.all()
    np.testing.assert_allclose(strain[:, 0], 0.02, atol=1e-12)
    np.testing.assert_allclose(strain[:, 1], 0.04, atol=1e-12)
    np.testing.assert_allclose(strain[:, 2], 0.0, atol=1e-12)


def test_psi_raw_derivation_requires_constitutive_and_stays_ineligible() -> None:
    strain = np.asarray([[0.01, 0.0, 0.0]])
    mask = np.ones_like(strain, dtype=bool)
    with pytest.raises(ValueError, match="constitutive_model_id"):
        derive_psi_raw_estimate_from_strain(
            strain=strain,
            mask=mask,
            youngs_modulus_pa=1e9,
            poisson_ratio=0.25,
            constitutive_model_id="",
            tensile_split_id="spectral_positive_strain",
            kinematic_assumption="plane_stress",
        )
    result = derive_psi_raw_estimate_from_strain(
        strain=strain,
        mask=mask,
        youngs_modulus_pa=1e9,
        poisson_ratio=0.25,
        constitutive_model_id="isotropic_linear_elastic_v1",
        tensile_split_id="spectral_positive_strain",
        kinematic_assumption="plane_stress",
    )
    assert result["values"][0] > 0
    assert result["direct_sensor_observation"] is False
    assert result["decision_eligible"] is False


def test_fwd_wim_temperature_and_strain_adapters_preserve_units_and_missingness() -> None:
    fwd = adapt_fwd_observation(
        load_n=40_000,
        offsets_m=[0, 0.3, 0.6],
        deflection_m=[0.001, 0.0005, np.nan],
        mask=[True, True, False],
        std_m=[1e-5, 1e-5, np.nan],
        timestamp=TIMESTAMP,
        evidence_class="real_measurement",
        registration=registration(),
    )
    assert fwd.units == ("N", "m", "m")
    assert fwd.metadata["basin_integral_m2"] is not None
    wim = adapt_wim_observation(
        axle_load_n=[80_000, 100_000],
        speed_mps=[20, 18],
        mask=[True, True],
        std=[[1000, 0.5], [1000, 0.5]],
        timestamp=TIMESTAMP,
        evidence_class="real_measurement",
        spectrum_edges_n=[0, 90_000, 120_000],
    )
    assert wim.metadata["equivalent_load_index"] is None
    assert sum(wim.metadata["spectrum_counts"]) == 2
    temperature = adapt_temperature_time(
        air_temperature_c=18,
        pavement_temperature_c=None,
        elapsed_s=3600,
        std=[0.5, None, 1.0],
        timestamp=TIMESTAMP,
        evidence_class="real_measurement",
    )
    assert not temperature.mask[0, 1]
    strain = adapt_strain_sensor(
        strain=[1e-4],
        mask=[True],
        std=[1e-6],
        sensor_axis_xy=[[1, 0]],
        timestamp=TIMESTAMP,
        evidence_class="real_measurement",
        registration=registration(),
    )
    assert strain.units == ("1",)


def test_maintenance_reset_requires_segment_metadata() -> None:
    with pytest.raises(ValueError, match="event_id"):
        adapt_maintenance_event(
            reset=True,
            event_id=None,
            event_code=1,
            new_state_segment_id=None,
            timestamp=TIMESTAMP,
            evidence_class="real_measurement",
        )
    record = adapt_maintenance_event(
        reset=True,
        event_id="resurface_1",
        event_code=1,
        new_state_segment_id="segment_1",
        timestamp=TIMESTAMP,
        evidence_class="real_measurement",
    )
    assert record.metadata["new_state_segment_id"] == "segment_1"


def test_identifiability_tasks_remain_separate() -> None:
    partial = assess_identifiability(
        families=["registered_crack_geometry", "fwd_load_deflection"],
        repeated_epochs=2,
        independent_load_cases=1,
        calibrated_uncertainty=False,
        multiple_assets=False,
    )
    assert partial["hidden_state_assimilation"] == "conditional_candidate"
    assert partial["material_parameter_inversion"] == "not_identified"
    assert partial["forecast_update"] == "context_only_or_not_ready"


def test_unknown_multitrajectory_schema_requires_versioned_adapter() -> None:
    record = missing_record(
        operator_id="missing",
        family="strain_sensor",
        channel_names=("strain_axial",),
        units=("1",),
        timestamp=TIMESTAMP,
        evidence_class="real_measurement",
        registration=registration(),
    )
    handoff = build_measurement_handoff(
        asset_id="a",
        trajectory_id="t",
        inspection_id="i",
        state_segment_id="s",
        records=[record],
        target_schema_requested="future_multi_trajectory_bundle_v9",
    )
    assert handoff["target_adapter"] is None
    assert handoff["adapter_status"] == "versioned_adapter_required_no_schema_guessing"
    assert handoff["decision_eligible"] is False


def test_derived_estimate_cannot_escape_handoff_firewall() -> None:
    record = missing_record(
        operator_id="missing",
        family="strain_sensor",
        channel_names=("strain_axial",),
        units=("1",),
        timestamp=TIMESTAMP,
        evidence_class="real_measurement",
        registration=registration(),
    )
    bad = {"direct_sensor_observation": True, "decision_eligible": True, "values": [1], "mask": [True]}
    with pytest.raises(ValueError, match="decision ineligible"):
        build_measurement_handoff(
            asset_id="a", trajectory_id="t", inspection_id="i", state_segment_id="s", records=[record], derived_estimates=[bad]
        )


def test_handoff_round_trip_and_firewall(tmp_path: Path) -> None:
    record = adapt_registered_crack_observation(
        crack_probability=[0.8], mask=[True], std=[0.1], timestamp=TIMESTAMP,
        evidence_class="synthetic_sensor_smoke", registration=registration(),
        source_kind="declared_synthetic_visibility_operator",
    )
    handoff = build_measurement_handoff(
        asset_id="a", trajectory_id="t", inspection_id="i", state_segment_id="s", records=[record]
    )
    path = tmp_path / "handoff.npz"
    write_measurement_handoff_npz(path, handoff, [record])
    assert validate_measurement_handoff_npz(path) == []
    assert handoff["schema_version"] == HANDOFF_VERSION
    assert handoff["decision_eligible"] is False


def test_state_bundle_adapter_maps_only_measurements_and_never_creates_state() -> None:
    record = adapt_registered_crack_observation(
        crack_probability=[0.8, 0.4], mask=[True, True], std=[0.1, 0.1],
        timestamp=TIMESTAMP, evidence_class="real_measurement", registration=registration(),
        source_kind="registered_image_segmentation", target_node_index=[1, 3],
    )
    handoff = build_measurement_handoff(
        asset_id="a", trajectory_id="t", inspection_id="i", state_segment_id="s", records=[record]
    )
    payload = adapt_handoff_to_state_bundle_v1_observations(handoff=handoff, records=[record], node_count=5)
    assert payload["node_observation_mask"][0, 1, 0]
    assert payload["node_observation_mask"][0, 3, 0]
    assert not payload["node_observation_mask"][:, :, 2].any()
    assert payload["state_mean_created"] is False
    assert payload["decision_eligible"] is False


def test_operator_spec_names_only_measurement_families() -> None:
    spec = measurement_operator_spec()
    assert "psi_raw" in spec["forbidden_direct_channels"]
    assert "registered_crack_geometry" in spec["allowed_families"]
