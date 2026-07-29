from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from toy_to_road_evidence_gate import (  # noqa: E402
    EvidenceValidationError,
    validate_package,
)


SHA_A = "a" * 64
SHA_B = "b" * 64


def valid_package() -> dict:
    trajectories = [
        {
            "trajectory_id": "defect",
            "variation_axes": ["initial_defect"],
            "independence_scope": "road_like",
        },
        {
            "trajectory_id": "material",
            "variation_axes": ["material_state"],
            "independence_scope": "road_like",
        },
        {
            "trajectory_id": "history",
            "variation_axes": ["loading_history"],
            "independence_scope": "road_like",
        },
        {"trajectory_id": "u012", "variation_axes": ["load_amplitude"]},
    ]
    return {
        "schema_version": "toy_to_road_evidence_v1",
        "scale_contract": {
            "w1": "Gc/ell",
            "cw_applications": 1,
            "legacy_cw_scaled_runs": "quarantined",
        },
        "fem_references": [
            {
                "reference_id": "hard5_eta0_u012_5step_20260729_first_hit",
                "mesh_sha256": SHA_A,
                "snapshot_sha256": SHA_B,
                "loading_substeps": [0.25, 0.5, 0.75, 1.0, 0.0],
                "model_form": "AT1_plane_strain",
                "event_rule": "connected_3_node_d095_x048_confirm3",
                "first_hit_cycle": 83,
                "confirmed_cycle": 86,
                "event_phase": "first-hit",
                "loading_branch": "peak",
                "raw_step": 414,
            }
        ],
        "tracks": {
            "dimensionless_transfer": {
                "exact_pi_positive_control_passed": True,
                "model_form_negative_control_passed": True,
            },
            "independent_fem": {
                "trajectories": trajectories,
                "split_lock": {
                    "type": "leave-one-entire-trajectory-out",
                    "sha256": SHA_A,
                    "cycle_or_node_leakage": False,
                },
            },
            "forecast": {
                "candidates": ["markov_graph", "tcn", "transformer"],
                "training_started": True,
                "split_type": "leave-one-entire-trajectory-out",
                "tasks": [
                    "observed_state_h1_h3",
                    "transition_warning",
                    "observation_reset_propagation",
                ],
                "held_out_results_passed": True,
            },
            "reality_observation": {
                "direct_channels": [
                    "crack_image",
                    "dic_displacement",
                    "fwd_deflection_basin",
                    "wim_axle_load",
                    "temperature",
                    "maintenance_record",
                ],
                "derived_channels": [
                    {
                        "name": "psi_raw_estimate",
                        "classification": "derived_latent_estimate",
                        "measurement_operator": "constitutive_tensile_split_v1",
                        "uncertainty": "ensemble_covariance",
                        "units": "Pa",
                    }
                ],
                "missingness_masked": True,
                "latent_to_sensor_firewall": True,
                "identifiability_matrix": True,
                "real_data_evaluated": True,
            },
        },
    }


def test_valid_complete_package_is_training_and_road_ready() -> None:
    result = validate_package(valid_package())
    assert result.valid
    assert result.training_ready
    assert result.road_training_ready
    assert result.training_scope == "road_like_leave_one_trajectory_out"
    assert result.road_validation_ready
    assert not result.blockers


def test_umax_only_family_does_not_unlock_training() -> None:
    package = valid_package()
    package["tracks"]["independent_fem"]["trajectories"] = [
        {"trajectory_id": f"u{value}", "variation_axes": ["load_amplitude"]}
        for value in (11, 12, 13)
    ]
    package["tracks"]["forecast"]["training_started"] = False
    result = validate_package(package)
    assert not result.training_ready
    assert not result.road_training_ready
    assert "fewer_than_three_independent_trajectories" in result.blockers


def test_training_before_independent_readiness_is_rejected() -> None:
    package = valid_package()
    package["tracks"]["independent_fem"]["trajectories"] = []
    with pytest.raises(EvidenceValidationError, match="before independent FEM"):
        validate_package(package)


def test_factorial_trajectories_unlock_only_within_benchmark_training() -> None:
    package = valid_package()
    package["tracks"]["independent_fem"]["trajectories"] = [
        {
            "trajectory_id": f"factorial_{index}",
            "variation_axes": ["initial_defect", "loading_history"],
            "independence_scope": "within_hard5_factorial",
        }
        for index in range(4)
    ]
    package["tracks"]["reality_observation"]["real_data_evaluated"] = False
    result = validate_package(package)
    assert result.training_ready
    assert result.training_scope == "within_benchmark_factorial"
    assert not result.road_training_ready
    assert not result.road_validation_ready
    assert "fewer_than_three_road_like_trajectories" in result.blockers


def test_latent_field_cannot_be_a_direct_sensor() -> None:
    package = valid_package()
    package["tracks"]["reality_observation"]["direct_channels"].append(
        "psi_raw"
    )
    with pytest.raises(EvidenceValidationError, match="latent fields"):
        validate_package(package)


def test_event_phase_is_required() -> None:
    package = valid_package()
    del package["fem_references"][0]["event_phase"]
    with pytest.raises(EvidenceValidationError, match="event_phase"):
        validate_package(package)


def test_extra_architecture_is_rejected() -> None:
    package = deepcopy(valid_package())
    package["tracks"]["forecast"]["candidates"].append("new_attention_model")
    with pytest.raises(EvidenceValidationError, match="unapproved architecture"):
        validate_package(package)
