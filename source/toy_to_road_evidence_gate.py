"""Validate the shared toy-to-road evidence contract.

The gate is intentionally independent of model code. It decides whether an
evidence package is ready for training or a stronger claim; it never launches a
solver or promotes a scientific result by itself.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "toy_to_road_evidence_v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

ALLOWED_FORECAST_MODELS = {"markov_graph", "tcn", "transformer"}
ALLOWED_DIRECT_OBSERVATIONS = {
    "crack_image",
    "crack_mask",
    "crack_length",
    "crack_width",
    "crack_connectivity",
    "dic_displacement",
    "dic_strain",
    "strain_sensor",
    "fwd_load",
    "fwd_deflection_basin",
    "wim_axle_load",
    "wim_speed",
    "wim_traffic_spectrum",
    "temperature",
    "elapsed_time",
    "maintenance_record",
}
FORBIDDEN_DIRECT_LATENTS = {
    "damage",
    "alpha",
    "alpha_bar",
    "history",
    "fatigue_degradation",
    "degradation",
    "g_alpha",
    "psi_raw",
    "raw_driver",
    "psi_active",
    "active_driver",
}
INDEPENDENT_VARIATION_AXES = {
    "initial_defect",
    "material_state",
    "loading_history",
}


class EvidenceValidationError(ValueError):
    """Raised when a package violates the shared evidence contract."""


@dataclass(frozen=True)
class GateResult:
    valid: bool
    training_ready: bool
    training_scope: str
    road_training_ready: bool
    road_validation_ready: bool
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "training_ready": self.training_ready,
            "within_benchmark_training_ready": self.training_ready,
            "training_scope": self.training_scope,
            "road_training_ready": self.road_training_ready,
            "road_validation_ready": self.road_validation_ready,
            "blockers": list(self.blockers),
        }


def _require(mapping: dict[str, Any], key: str, context: str) -> Any:
    if key not in mapping:
        raise EvidenceValidationError(f"{context} missing required key: {key}")
    return mapping[key]


def _validate_reference(reference: dict[str, Any], index: int) -> None:
    context = f"fem_references[{index}]"
    for key in (
        "reference_id",
        "mesh_sha256",
        "snapshot_sha256",
        "loading_substeps",
        "model_form",
        "event_rule",
        "first_hit_cycle",
        "confirmed_cycle",
        "event_phase",
        "loading_branch",
        "raw_step",
    ):
        _require(reference, key, context)

    for key in ("mesh_sha256", "snapshot_sha256"):
        value = reference[key]
        if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
            raise EvidenceValidationError(f"{context}.{key} is not SHA-256")

    substeps = reference["loading_substeps"]
    if not isinstance(substeps, list) or not substeps:
        raise EvidenceValidationError(f"{context}.loading_substeps must be non-empty")
    if reference["event_phase"] not in {"first-hit", "confirmed", "pre-event"}:
        raise EvidenceValidationError(f"{context}.event_phase is not explicit")
    if int(reference["confirmed_cycle"]) < int(reference["first_hit_cycle"]):
        raise EvidenceValidationError(f"{context} confirms before first hit")


def _validate_scale_contract(package: dict[str, Any]) -> None:
    scale = _require(package, "scale_contract", "package")
    if scale.get("w1") != "Gc/ell":
        raise EvidenceValidationError("scale_contract.w1 must equal Gc/ell")
    if scale.get("cw_applications") != 1:
        raise EvidenceValidationError("c_w must be applied exactly once")
    if scale.get("legacy_cw_scaled_runs") != "quarantined":
        raise EvidenceValidationError("legacy c_w-scaled runs must be quarantined")


def _validate_independent_fem(
    track: dict[str, Any]
) -> tuple[bool, bool, list[str]]:
    blockers: list[str] = []
    trajectories = track.get("trajectories", [])
    if not isinstance(trajectories, list):
        raise EvidenceValidationError("independent_fem.trajectories must be a list")

    independent = []
    road_like = []
    for index, trajectory in enumerate(trajectories):
        if not isinstance(trajectory, dict):
            raise EvidenceValidationError(
                f"independent_fem.trajectories[{index}] must be an object"
            )
        axes = set(trajectory.get("variation_axes", []))
        if axes & INDEPENDENT_VARIATION_AXES:
            independent.append(trajectory)
        if trajectory.get("independence_scope") == "road_like":
            road_like.append(trajectory)

    if len(independent) < 3:
        blockers.append("fewer_than_three_independent_trajectories")
    road_ready = len(road_like) >= 3
    if not road_ready:
        blockers.append("fewer_than_three_road_like_trajectories")

    split = track.get("split_lock", {})
    if split.get("type") != "leave-one-entire-trajectory-out":
        blockers.append("leave_one_entire_trajectory_out_not_locked")
    split_sha = split.get("sha256")
    if not isinstance(split_sha, str) or not SHA256_RE.fullmatch(split_sha):
        blockers.append("split_lock_sha256_missing")
    if split.get("cycle_or_node_leakage") is not False:
        blockers.append("trajectory_leakage_not_excluded")

    within_blockers = [
        blocker
        for blocker in blockers
        if blocker != "fewer_than_three_road_like_trajectories"
    ]
    return not within_blockers, road_ready and not within_blockers, blockers


def _validate_forecast(
    track: dict[str, Any], independent_ready: bool
) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    candidates = set(track.get("candidates", []))
    extra = candidates - ALLOWED_FORECAST_MODELS
    if extra:
        raise EvidenceValidationError(
            f"forecast contains unapproved architecture(s): {sorted(extra)}"
        )
    if "markov_graph" not in candidates:
        blockers.append("matched_markov_graph_control_missing")
    if track.get("training_started") and not independent_ready:
        raise EvidenceValidationError(
            "forecast training started before independent FEM readiness"
        )
    if track.get("split_type") != "leave-one-entire-trajectory-out":
        blockers.append("forecast_split_is_not_trajectory_holdout")
    tasks = set(track.get("tasks", []))
    required_tasks = {
        "observed_state_h1_h3",
        "transition_warning",
        "observation_reset_propagation",
    }
    if not required_tasks.issubset(tasks):
        blockers.append("forecast_task_set_incomplete")
    return not blockers, blockers


def _validate_observations(track: dict[str, Any]) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    direct = set(track.get("direct_channels", []))
    forbidden = direct & FORBIDDEN_DIRECT_LATENTS
    if forbidden:
        raise EvidenceValidationError(
            f"latent fields declared as direct sensors: {sorted(forbidden)}"
        )
    unknown = direct - ALLOWED_DIRECT_OBSERVATIONS
    if unknown:
        raise EvidenceValidationError(
            f"unknown direct observation channels: {sorted(unknown)}"
        )

    derived = track.get("derived_channels", [])
    for index, channel in enumerate(derived):
        if channel.get("classification") != "derived_latent_estimate":
            raise EvidenceValidationError(
                f"derived_channels[{index}] lacks derived_latent_estimate label"
            )
        for key in ("measurement_operator", "uncertainty", "units"):
            if not channel.get(key):
                raise EvidenceValidationError(
                    f"derived_channels[{index}] missing {key}"
                )

    if not track.get("missingness_masked", False):
        blockers.append("observation_missingness_contract_missing")
    if not track.get("latent_to_sensor_firewall", False):
        blockers.append("latent_to_sensor_firewall_missing")
    if not track.get("identifiability_matrix", False):
        blockers.append("identifiability_matrix_missing")
    return not blockers, blockers


def validate_package(package: dict[str, Any]) -> GateResult:
    if package.get("schema_version") != SCHEMA_VERSION:
        raise EvidenceValidationError(
            f"schema_version must equal {SCHEMA_VERSION}"
        )
    _validate_scale_contract(package)

    references = _require(package, "fem_references", "package")
    if not isinstance(references, list) or not references:
        raise EvidenceValidationError("package requires at least one FEM reference")
    ids: list[str] = []
    for index, reference in enumerate(references):
        _validate_reference(reference, index)
        ids.append(reference["reference_id"])
    if len(set(ids)) != len(ids):
        raise EvidenceValidationError("FEM reference IDs must be unique")

    tracks = _require(package, "tracks", "package")
    for key in (
        "dimensionless_transfer",
        "independent_fem",
        "forecast",
        "reality_observation",
    ):
        _require(tracks, key, "tracks")

    dimensionless = tracks["dimensionless_transfer"]
    blockers: list[str] = []
    if not dimensionless.get("exact_pi_positive_control_passed", False):
        blockers.append("exact_pi_positive_control_not_passed")
        if dimensionless.get("producer_access") == "blocked":
            blockers.append("f1b_producer_access_blocked")
    if not dimensionless.get("model_form_negative_control_passed", False):
        blockers.append("model_form_negative_control_not_passed")

    independent_ready, road_independent_ready, independent_blockers = _validate_independent_fem(
        tracks["independent_fem"]
    )
    blockers.extend(independent_blockers)

    forecast_ready, forecast_blockers = _validate_forecast(
        tracks["forecast"], independent_ready
    )
    blockers.extend(forecast_blockers)

    observation_ready, observation_blockers = _validate_observations(
        tracks["reality_observation"]
    )
    blockers.extend(observation_blockers)

    training_ready = independent_ready and not forecast_blockers
    road_training_ready = road_independent_ready and not forecast_blockers
    dimensionless_ready = (
        dimensionless.get("exact_pi_positive_control_passed", False)
        and dimensionless.get("model_form_negative_control_passed", False)
    )
    forecast = tracks["forecast"]
    evaluation_completed = forecast.get(
        "held_out_evaluation_completed",
        forecast.get("held_out_results_passed", False),
    )
    forecast_task_gate_passed = forecast.get(
        "forecast_task_gate_passed",
        forecast.get("held_out_results_passed", False),
    )
    road_validation_ready = (
        dimensionless_ready
        and road_training_ready
        and forecast_ready
        and observation_ready
        and evaluation_completed
        and forecast_task_gate_passed
        and tracks["reality_observation"].get("real_data_evaluated", False)
    )
    if not evaluation_completed:
        blockers.append("held_out_trajectory_forecast_not_evaluated")
        if forecast.get("producer_access") == "blocked_authentication":
            blockers.append("forecast_producer_access_blocked")
    elif not forecast_task_gate_passed:
        blockers.append("held_out_trajectory_forecast_gate_not_passed")
    if not tracks["reality_observation"].get("real_data_evaluated", False):
        blockers.append("real_road_data_not_evaluated")

    return GateResult(
        valid=True,
        training_ready=training_ready,
        training_scope=(
            "road_like_leave_one_trajectory_out"
            if road_training_ready
            else "within_benchmark_factorial"
            if training_ready
            else "not_ready"
        ),
        road_training_ready=road_training_ready,
        road_validation_ready=road_validation_ready,
        blockers=tuple(dict.fromkeys(blockers)),
    )


def load_and_validate(path: Path) -> GateResult:
    with path.open("r", encoding="utf-8") as handle:
        package = json.load(handle)
    if not isinstance(package, dict):
        raise EvidenceValidationError("top-level JSON must be an object")
    return validate_package(package)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    try:
        result = load_and_validate(args.package)
    except (OSError, json.JSONDecodeError, EvidenceValidationError) as exc:
        payload = {"valid": False, "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 2

    payload = result.to_dict()
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    print(rendered)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
