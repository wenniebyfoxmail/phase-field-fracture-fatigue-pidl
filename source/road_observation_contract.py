"""Road-observation contract for latent fracture-state assimilation.

The contract separates FEM oracle fields, synthetic sensor renderings, and
real measurements. It intentionally does not implement a learned inverse.
Its main job is to prevent hidden phase-field variables from being presented
as direct road sensors and to give every predictor the same frozen analysis
state.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np


SCHEMA_VERSION = "road_assimilated_state_v1"
OBSERVATION_SPEC_VERSION = "road_observation_operator_v1"
STATE_FIELDS = ("damage", "alpha_bar", "fatigue_degradation", "log10_psi_raw")
EVIDENCE_CLASSES = ("fem_oracle", "synthetic_sensor", "real_observation")
SOURCE_CODES = {
    0: "transition_prior",
    1: "direct_observation_update",
    2: "observation_conditioned_variational_update",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def default_road_observation_operator_spec() -> dict[str, Any]:
    """Return the phase-1 road observation contract.

    The equations are semantic contracts, not calibrated road likelihoods.
    Any channel marked ``not_calibrated`` must remain out of scientific model
    ranking until paired laboratory or field data are available.
    """
    return {
        "spec_version": OBSERVATION_SPEC_VERSION,
        "equation": "y_t = H(z_t, theta, forcing_t) + epsilon_t",
        "scope": "road-facing phase-1 interface; no real-road calibration claim",
        "evidence_classes": {
            "fem_oracle": "hidden FEM state used only as a numerical upper bound",
            "synthetic_sensor": "measurement-like data rendered from FEM through a declared operator",
            "real_observation": "laboratory or in-service road measurement with provenance",
        },
        "latent_state": {
            "damage": {
                "directly_observable": False,
                "meaning": "phase-field damage; a crack mask is not identical to damage",
            },
            "alpha_bar": {
                "directly_observable": False,
                "meaning": "fatigue history accumulated by the transition model",
            },
            "fatigue_degradation": {
                "directly_observable": False,
                "meaning": "constitutive fatigue degradation state",
            },
            "g_alpha": {
                "directly_observable": False,
                "meaning": "stiffness degradation derived from latent damage and constitutive choice",
            },
            "psi_raw": {
                "directly_observable": False,
                "meaning": "raw tensile energy derived from reconstructed strain, material model, and tensile split",
            },
            "psi_active": {
                "directly_observable": False,
                "meaning": "degraded energetic driver derived from latent state",
            },
        },
        "exogenous_inputs": {
            "wim_axle_spectrum": {
                "role": "forcing",
                "measurement": "axle count, class, load, speed, and time aggregation",
            },
            "temperature": {"role": "environment", "measurement": "air and pavement temperature"},
            "moisture": {"role": "environment", "measurement": "layer water content or humidity proxy"},
            "maintenance": {"role": "state_intervention", "measurement": "treatment type, location, and timestamp"},
        },
        "channels": {
            "registered_crack_image": {
                "evidence_class_when_measured": "real_observation",
                "observable_features": [
                    "crack_probability_mask",
                    "crack_tip_xy",
                    "crack_length",
                    "crack_width_distribution",
                    "crack_area",
                    "orientation",
                    "connectivity",
                ],
                "operator": "registered image -> calibrated segmentation probability -> geometric summaries",
                "synthetic_operator": "latent damage -> declared visibility/blur/segmentation model; never alpha identity",
                "calibration_status": "not_calibrated_for_road_state_inversion",
            },
            "fwd_deflection_basin": {
                "evidence_class_when_measured": "real_observation",
                "observable_features": ["impulse_load", "deflection_by_offset", "test_location", "surface_temperature"],
                "operator": "structural response model H_FWD(z, layers, support, load)",
                "required_latent_or_parameters": ["mechanical_state", "layer_geometry", "stiffness", "support_conditions"],
                "calibration_status": "not_available_in_current_c87_dataset",
            },
            "strain_sensor": {
                "evidence_class_when_measured": "real_observation",
                "observable_features": ["strain_tensor_or_component", "sensor_location", "load_phase", "temperature"],
                "operator": "displacement gradient or FEM strain projected to sensor axis; psi_raw requires a separate constitutive split",
                "calibration_status": "not_available_in_current_c87_dataset",
            },
            "laboratory_dic": {
                "evidence_class_when_measured": "real_observation",
                "observable_features": ["registered_displacement", "derived_strain", "quality_mask"],
                "operator": "DIC displacement -> regularized strain -> constitutive tensile split -> optional psi_raw proxy",
                "deployment_role": "laboratory calibration, not assumed routine road instrumentation",
                "calibration_status": "synthetic_proxy_only_in_current_inverse_ladder",
            },
            "wim": {
                "evidence_class_when_measured": "real_observation",
                "observable_features": ["axle_load_spectrum", "vehicle_class", "speed", "timestamp"],
                "operator": "traffic stream -> equivalent load block and load-spectrum conditioning",
                "calibration_status": "not_ingested_in_current_c87_dataset",
            },
            "temperature_moisture": {
                "evidence_class_when_measured": "real_observation",
                "observable_features": ["air_temperature", "pavement_temperature", "layer_moisture", "timestamp"],
                "operator": "environment stream -> constitutive/transition conditioning",
                "calibration_status": "not_ingested_in_current_c87_dataset",
            },
            "fem_raw_energy_probe": {
                "evidence_class_when_measured": "fem_oracle",
                "observable_features": ["log10_psi_raw"],
                "operator": "direct access to FEM hidden field",
                "deployment_role": "upper bound only; never a road sensor",
                "calibration_status": "locked_single_trajectory_upper_bound",
            },
        },
        "error_model": {
            "image_registration": "spatially correlated coordinate perturbation plus session bias",
            "segmentation": "probability calibration, threshold sensitivity, false components, and missing crack pixels",
            "sensor_spatial_correlation": "block or Gaussian-process residual; iid noise alone is insufficient",
            "sensor_drift": "asset/session random intercept and time-dependent drift",
            "missing_data": "channel- and visit-specific mask recorded explicitly",
            "constitutive_uncertainty": "material parameters and tensile split propagated when deriving energetic proxies",
        },
        "budget_units": {
            "image": ["registered_inspection_count", "covered_area_m2", "ground_sample_distance", "inspection_interval"],
            "fwd": ["test_location_count", "deflection_offset_count", "repeat_drop_count", "survey_interval"],
            "strain": ["physical_sensor_count", "sample_rate_hz", "load_events_observed", "maintenance_rate"],
            "wim": ["station_count", "aggregation_interval", "valid_axle_fraction"],
            "environment": ["temperature_sensor_count", "moisture_sensor_count", "sample_interval"],
        },
        "fairness_contract": {
            "same_observations_for_all_predictors": True,
            "same_prior_for_all_predictors": True,
            "same_assimilated_state_hash_for_all_predictors": True,
            "model_specific_observation_selection_forbidden": True,
        },
        "identifiability_boundary": {
            "state_inverse": "only channels constrained by the declared H and prior may be discussed",
            "parameter_inverse": "not identified by the current single fixed-parameter trajectory",
            "future_forecast": "evaluated separately after the analysis state is frozen",
        },
    }


def validate_operator_spec(spec: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if spec.get("spec_version") != OBSERVATION_SPEC_VERSION:
        errors.append("unexpected spec_version")
    latent = spec.get("latent_state", {})
    required_latent = {"damage", "alpha_bar", "fatigue_degradation", "g_alpha", "psi_raw", "psi_active"}
    missing = sorted(required_latent - set(latent))
    if missing:
        errors.append(f"missing latent fields: {missing}")
    for name in required_latent & set(latent):
        if bool(latent[name].get("directly_observable", True)):
            errors.append(f"latent field {name} cannot be marked directly observable")
    channels = spec.get("channels", {})
    if channels.get("fem_raw_energy_probe", {}).get("evidence_class_when_measured") != "fem_oracle":
        errors.append("FEM raw energy must remain fem_oracle")
    fairness = spec.get("fairness_contract", {})
    for key in (
        "same_observations_for_all_predictors",
        "same_prior_for_all_predictors",
        "same_assimilated_state_hash_for_all_predictors",
        "model_specific_observation_selection_forbidden",
    ):
        if fairness.get(key) is not True:
            errors.append(f"fairness contract must enforce {key}")
    return errors


def build_assimilated_state_package(
    *,
    operator_dataset: Path,
    analysis_artifact: Path,
    output_path: Path,
    observation_operator_id: str,
    prior_id: str,
    cycle: int,
) -> dict[str, Any]:
    """Freeze one analysis state behind a predictor-independent interface."""
    with np.load(operator_dataset, allow_pickle=False) as dataset:
        coordinates = np.asarray(dataset["coordinates"], dtype=np.float32)
        areas = np.asarray(dataset["areas"], dtype=np.float32)
        edge_index = np.asarray(dataset["edge_index"], dtype=np.int64)
        edge_attr = np.asarray(dataset["edge_attr"], dtype=np.float32)
        physics_family = str(np.asarray(dataset["physics_family"]).item())
        trajectory_id = str(np.asarray(dataset["trajectory_id"]).item())
    with np.load(analysis_artifact, allow_pickle=False) as analysis:
        state_mean = np.asarray(analysis["analysis_c87"], dtype=np.float32)
        observed_mask = np.asarray(analysis["observed_mask"], dtype=bool)

    node_count = len(coordinates)
    if state_mean.shape != (node_count, len(STATE_FIELDS)):
        raise ValueError("analysis state shape does not match graph and field contract")
    if observed_mask.shape != (node_count,):
        raise ValueError("observed mask shape does not match graph")

    observed_channel_mask = np.zeros_like(state_mean, dtype=bool)
    observed_channel_mask[:, STATE_FIELDS.index("log10_psi_raw")] = observed_mask
    source_code = np.zeros_like(state_mean, dtype=np.uint8)
    raw_index = STATE_FIELDS.index("log10_psi_raw")
    source_code[:, raw_index] = 2
    source_code[observed_mask, raw_index] = 1
    state_std = np.full_like(state_mean, np.nan, dtype=np.float32)
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "cycle": int(cycle),
        "state_fields": list(STATE_FIELDS),
        "source_evidence_class": "fem_oracle",
        "observation_operator_id": observation_operator_id,
        "prior_id": prior_id,
        "physics_family": physics_family,
        "trajectory_id": trajectory_id,
        "fem_eta": 0.0,
        "uncertainty_status": "uncalibrated_not_available",
        "real_road_compatible": False,
        "claim": "synthetic upper-bound interface only",
        "source_codes": {str(key): value for key, value in SOURCE_CODES.items()},
        "input_sha256": {
            "operator_dataset": sha256(operator_dataset),
            "analysis_artifact": sha256(analysis_artifact),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        schema_version=np.asarray(SCHEMA_VERSION),
        metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)),
        cycle=np.asarray(cycle, dtype=np.int16),
        state_fields=np.asarray(STATE_FIELDS),
        coordinates=coordinates,
        areas=areas,
        edge_index=edge_index,
        edge_attr=edge_attr,
        state_mean=state_mean,
        state_std=state_std,
        observed_channel_mask=observed_channel_mask,
        source_code=source_code,
    )
    return metadata


def validate_assimilated_state_package(path: Path) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "metadata_json",
        "cycle",
        "state_fields",
        "coordinates",
        "areas",
        "edge_index",
        "edge_attr",
        "state_mean",
        "state_std",
        "observed_channel_mask",
        "source_code",
    }
    with np.load(path, allow_pickle=False) as package:
        missing = sorted(required - set(package.files))
        if missing:
            return [f"missing arrays: {missing}"]
        version = str(np.asarray(package["schema_version"]).item())
        if version != SCHEMA_VERSION:
            errors.append("unexpected assimilated-state schema version")
        fields = tuple(str(value) for value in np.asarray(package["state_fields"]).tolist())
        if fields != STATE_FIELDS:
            errors.append("state field order differs from contract")
        coordinates = np.asarray(package["coordinates"])
        areas = np.asarray(package["areas"])
        state = np.asarray(package["state_mean"])
        std = np.asarray(package["state_std"])
        observed = np.asarray(package["observed_channel_mask"])
        source = np.asarray(package["source_code"])
        if coordinates.ndim != 2 or coordinates.shape[1] != 2:
            errors.append("coordinates must have shape [N,2]")
        expected = (len(coordinates), len(STATE_FIELDS))
        for name, array in (("state_mean", state), ("state_std", std), ("observed_channel_mask", observed), ("source_code", source)):
            if array.shape != expected:
                errors.append(f"{name} must have shape {expected}")
        if areas.shape != (len(coordinates),) or not np.all(np.isfinite(areas)) or np.any(areas <= 0):
            errors.append("areas must be finite and positive with shape [N]")
        if not np.all(np.isfinite(state)):
            errors.append("state_mean must be finite")
        if not set(np.unique(source)).issubset(SOURCE_CODES):
            errors.append("source_code contains an undeclared value")
        metadata = json.loads(str(np.asarray(package["metadata_json"]).item()))
        if metadata.get("uncertainty_status") == "uncalibrated_not_available":
            if not np.isnan(std).all():
                errors.append("uncalibrated uncertainty must be represented by NaN, not zero")
        elif not np.all(np.isfinite(std)):
            errors.append("calibrated uncertainty must be finite")
        if metadata.get("source_evidence_class") not in EVIDENCE_CLASSES:
            errors.append("invalid source evidence class")
        if metadata.get("source_evidence_class") == "fem_oracle" and metadata.get("real_road_compatible") is not False:
            errors.append("FEM oracle package cannot be marked real-road compatible")
    return errors
