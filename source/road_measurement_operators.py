"""Executable contracts for real-measurable road observations.

The module intentionally stops at measurement-space handoff. Hidden fracture
fields and constitutive estimates are never accepted as direct observations.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import string
from typing import Any, Mapping, Sequence

import numpy as np


MEASUREMENT_SPEC_VERSION = "road_measurement_operator_v1"
HANDOFF_VERSION = "road_measurement_handoff_v1"
STATE_BUNDLE_ADAPTER_VERSION = "road_observation_state_bundle_v1_adapter_v1"
DERIVED_ESTIMATE_VERSION = "road_derived_latent_estimate_v1"

EVIDENCE_CLASSES = ("real_measurement", "synthetic_sensor_smoke")
OBSERVATION_FAMILIES = (
    "registered_crack_geometry",
    "dic_displacement",
    "strain_sensor",
    "fwd_load_deflection",
    "wim_traffic",
    "temperature_time",
    "maintenance_reset",
)

FORBIDDEN_DIRECT_CHANNELS = {
    "alpha",
    "damage",
    "alpha_bar",
    "fatigue_history",
    "g",
    "g_alpha",
    "fatigue_degradation",
    "psi_raw",
    "log10_psi_raw",
    "raw_driver",
    "psi_active",
    "active_driver",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _as_float(values: Any) -> np.ndarray:
    return np.asarray(values, dtype=np.float64)


def _as_mask(mask: Any, shape: tuple[int, ...]) -> np.ndarray:
    result = np.asarray(mask, dtype=bool)
    if result.shape != shape:
        raise ValueError(f"mask shape {result.shape} differs from values shape {shape}")
    return result


def _validate_missing(values: np.ndarray, mask: np.ndarray, label: str) -> None:
    if values.shape != mask.shape:
        raise ValueError(f"{label}: values and mask shapes differ")
    if np.any(mask & ~np.isfinite(values)):
        raise ValueError(f"{label}: observed entries must be finite")
    if np.any(~mask & ~np.isnan(values)):
        raise ValueError(f"{label}: missing entries must be NaN with mask=false")


def _validate_std(std: np.ndarray, mask: np.ndarray, label: str) -> None:
    if std.shape != mask.shape:
        raise ValueError(f"{label}: uncertainty and mask shapes differ")
    if np.any(mask & (~np.isfinite(std) | (std < 0))):
        raise ValueError(f"{label}: observed uncertainty must be finite and nonnegative")
    if np.any(~mask & ~np.isnan(std)):
        raise ValueError(f"{label}: missing uncertainty must be NaN")


def validate_timestamp(timestamp: str) -> str:
    if not timestamp:
        raise ValueError("timestamp is required")
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return timestamp


def validate_registration_contract(registration: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "coordinate_frame_id",
        "target_frame_id",
        "registration_id",
        "transform_3x3",
        "uncertainty_std_m",
        "source_sha256",
    }
    missing = sorted(required - set(registration))
    if missing:
        raise ValueError(f"registration missing fields: {missing}")
    transform = _as_float(registration["transform_3x3"])
    if transform.shape != (3, 3) or not np.all(np.isfinite(transform)):
        raise ValueError("registration transform_3x3 must be finite [3,3]")
    uncertainty = float(registration["uncertainty_std_m"])
    if not np.isfinite(uncertainty) or uncertainty < 0:
        raise ValueError("registration uncertainty_std_m must be finite and nonnegative")
    source_hashes = registration["source_sha256"]
    if not isinstance(source_hashes, Mapping) or not source_hashes:
        raise ValueError("registration source_sha256 must be a non-empty mapping")
    if any(len(str(value)) != 64 for value in source_hashes.values()):
        raise ValueError("registration source hashes must be SHA-256 hex strings")
    if any(any(character not in string.hexdigits for character in str(value)) for value in source_hashes.values()):
        raise ValueError("registration source hashes must be SHA-256 hex strings")
    quality = registration.get("quality_score")
    if quality is not None and (not np.isfinite(float(quality)) or not 0 <= float(quality) <= 1):
        raise ValueError("registration quality_score must be within [0,1]")
    return {
        "coordinate_frame_id": str(registration["coordinate_frame_id"]),
        "target_frame_id": str(registration["target_frame_id"]),
        "registration_id": str(registration["registration_id"]),
        "transform_3x3": transform.tolist(),
        "uncertainty_std_m": uncertainty,
        "quality_score": None if quality is None else float(quality),
        "source_sha256": {str(key): str(value) for key, value in source_hashes.items()},
    }


@dataclass(frozen=True)
class MeasurementRecord:
    operator_id: str
    family: str
    channel_names: tuple[str, ...]
    units: tuple[str, ...]
    values: np.ndarray
    mask: np.ndarray
    std: np.ndarray
    timestamp: str
    evidence_class: str
    registration: Mapping[str, Any] | None
    metadata: Mapping[str, Any]

    def validate(self) -> None:
        if self.family not in OBSERVATION_FAMILIES:
            raise ValueError(f"unsupported observation family: {self.family}")
        if self.evidence_class not in EVIDENCE_CLASSES:
            raise ValueError(f"unsupported evidence class: {self.evidence_class}")
        validate_timestamp(self.timestamp)
        if len(self.channel_names) != len(self.units):
            raise ValueError("channel and unit counts differ")
        if self.values.ndim < 1 or self.values.shape[-1] != len(self.channel_names):
            raise ValueError("last values dimension must match channels")
        _validate_missing(self.values, self.mask, self.operator_id)
        _validate_std(self.std, self.mask, self.operator_id)
        for channel in self.channel_names:
            normalized = channel.strip().lower()
            base = normalized.removesuffix("_oracle")
            if base in FORBIDDEN_DIRECT_CHANNELS:
                raise ValueError(f"latent field cannot be a direct sensor observation: {channel}")
        if self.registration is not None:
            validate_registration_contract(self.registration)

    def descriptor(self) -> dict[str, Any]:
        self.validate()
        return {
            "operator_id": self.operator_id,
            "family": self.family,
            "channel_names": list(self.channel_names),
            "units": list(self.units),
            "shape": list(self.values.shape),
            "timestamp": self.timestamp,
            "evidence_class": self.evidence_class,
            "registration": self.registration,
            "metadata": dict(self.metadata),
        }


def _record(
    *,
    operator_id: str,
    family: str,
    channel_names: Sequence[str],
    units: Sequence[str],
    values: Any,
    mask: Any,
    std: Any,
    timestamp: str,
    evidence_class: str,
    registration: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> MeasurementRecord:
    array = _as_float(values)
    result = MeasurementRecord(
        operator_id=operator_id,
        family=family,
        channel_names=tuple(channel_names),
        units=tuple(units),
        values=array,
        mask=_as_mask(mask, array.shape),
        std=_as_float(std),
        timestamp=validate_timestamp(timestamp),
        evidence_class=evidence_class,
        registration=None if registration is None else validate_registration_contract(registration),
        metadata={} if metadata is None else dict(metadata),
    )
    result.validate()
    return result


def missing_record(
    *,
    operator_id: str,
    family: str,
    channel_names: Sequence[str],
    units: Sequence[str],
    timestamp: str,
    evidence_class: str,
    sample_count: int = 1,
    registration: Mapping[str, Any] | None = None,
) -> MeasurementRecord:
    shape = (sample_count, len(channel_names))
    return _record(
        operator_id=operator_id,
        family=family,
        channel_names=channel_names,
        units=units,
        values=np.full(shape, np.nan),
        mask=np.zeros(shape, dtype=bool),
        std=np.full(shape, np.nan),
        timestamp=timestamp,
        evidence_class=evidence_class,
        registration=registration,
        metadata={"missingness": "not_observed; null/NaN plus mask=false"},
    )


def adapt_registered_crack_observation(
    *,
    crack_probability: Any,
    mask: Any,
    std: Any,
    timestamp: str,
    evidence_class: str,
    registration: Mapping[str, Any],
    source_kind: str,
    target_node_index: Any | None = None,
) -> MeasurementRecord:
    if source_kind not in {"registered_image_segmentation", "declared_synthetic_visibility_operator"}:
        raise ValueError("crack observations require image segmentation or a declared synthetic visibility operator")
    if source_kind == "declared_synthetic_visibility_operator" and evidence_class != "synthetic_sensor_smoke":
        raise ValueError("synthetic visibility output must carry synthetic_sensor_smoke evidence")
    values = _as_float(crack_probability).reshape(-1, 1)
    metadata: dict[str, Any] = {
        "source_kind": source_kind,
        "direct_measurand": "surface-visible crack segmentation",
    }
    if target_node_index is not None:
        index = np.asarray(target_node_index, dtype=np.int64).reshape(-1)
        if index.shape[0] != values.shape[0] or np.any(index < 0):
            raise ValueError("target_node_index must be nonnegative with one entry per crack sample")
        metadata["target_node_index"] = index.tolist()
    return _record(
        operator_id="registered_crack_image_v1",
        family="registered_crack_geometry",
        channel_names=("registered_crack_probability",),
        units=("1",),
        values=values,
        mask=np.asarray(mask, dtype=bool).reshape(values.shape),
        std=_as_float(std).reshape(values.shape),
        timestamp=timestamp,
        evidence_class=evidence_class,
        registration=registration,
        metadata=metadata,
    )


def crack_geometry_record(
    *,
    width_m: float | None,
    length_m: float | None,
    tip_xy_m: Sequence[float] | None,
    std_m: Sequence[float | None],
    timestamp: str,
    evidence_class: str,
    registration: Mapping[str, Any],
) -> MeasurementRecord:
    raw = [width_m, length_m, None, None]
    if tip_xy_m is not None:
        if len(tip_xy_m) != 2:
            raise ValueError("tip_xy_m must contain x and y")
        raw[2:] = list(tip_xy_m)
    if len(std_m) != 4:
        raise ValueError("std_m must contain width, length, tip-x and tip-y uncertainty")
    values = np.asarray([[np.nan if value is None else value for value in raw]], dtype=np.float64)
    mask = np.isfinite(values)
    uncertainty = np.asarray([[np.nan if value is None else value for value in std_m]], dtype=np.float64)
    uncertainty[~mask] = np.nan
    return _record(
        operator_id="registered_crack_geometry_v1",
        family="registered_crack_geometry",
        channel_names=("crack_width", "crack_length", "crack_tip_x", "crack_tip_y"),
        units=("m", "m", "m", "m"),
        values=values,
        mask=mask,
        std=uncertainty,
        timestamp=timestamp,
        evidence_class=evidence_class,
        registration=registration,
        metadata={"direct_measurand": "registered surface crack geometry"},
    )


def adapt_dic_displacement(
    *,
    displacement_m: Any,
    mask: Any,
    std_m: Any,
    timestamp: str,
    evidence_class: str,
    registration: Mapping[str, Any],
) -> MeasurementRecord:
    values = _as_float(displacement_m)
    if values.ndim != 2 or values.shape[1] != 2:
        raise ValueError("DIC displacement must have shape [N,2]")
    return _record(
        operator_id="registered_dic_displacement_v1",
        family="dic_displacement",
        channel_names=("dic_u_x", "dic_u_y"),
        units=("m", "m"),
        values=values,
        mask=mask,
        std=std_m,
        timestamp=timestamp,
        evidence_class=evidence_class,
        registration=registration,
        metadata={"direct_measurand": "registered optical displacement", "laboratory_calibration_typical": True},
    )


def adapt_strain_sensor(
    *,
    strain: Any,
    mask: Any,
    std: Any,
    sensor_axis_xy: Any,
    timestamp: str,
    evidence_class: str,
    registration: Mapping[str, Any],
) -> MeasurementRecord:
    values = _as_float(strain).reshape(-1, 1)
    axes = _as_float(sensor_axis_xy)
    if axes.shape != (values.shape[0], 2):
        raise ValueError("sensor_axis_xy must have shape [N,2]")
    norm = np.linalg.norm(axes, axis=1)
    if np.any(~np.isfinite(norm)) or np.any(norm <= 0):
        raise ValueError("strain sensor axes must be finite and non-zero")
    return _record(
        operator_id="registered_strain_sensor_v1",
        family="strain_sensor",
        channel_names=("strain_axial",),
        units=("1",),
        values=values,
        mask=np.asarray(mask, dtype=bool).reshape(values.shape),
        std=_as_float(std).reshape(values.shape),
        timestamp=timestamp,
        evidence_class=evidence_class,
        registration=registration,
        metadata={"sensor_axis_xy": (axes / norm[:, None]).tolist(), "direct_measurand": "axial strain"},
    )


def estimate_small_strain_from_displacement(
    coordinates_m: Any,
    displacement_m: Any,
    edge_index: Any,
    observation_mask: Any,
) -> tuple[np.ndarray, np.ndarray]:
    """Estimate symmetric small strain by local affine least squares."""
    coordinates = _as_float(coordinates_m)
    displacement = _as_float(displacement_m)
    edges = np.asarray(edge_index, dtype=np.int64)
    observed = np.asarray(observation_mask, dtype=bool)
    if coordinates.ndim != 2 or coordinates.shape[1] != 2 or displacement.shape != coordinates.shape:
        raise ValueError("coordinates and displacement must both have shape [N,2]")
    if observed.shape == (coordinates.shape[0], 2):
        observed = np.all(observed, axis=1)
    if observed.shape != (coordinates.shape[0],):
        raise ValueError("observation_mask must have shape [N] or [N,2]")
    if edges.ndim != 2 or edges.shape[0] != 2:
        raise ValueError("edge_index must have shape [2,E]")
    neighbours: list[list[int]] = [[] for _ in range(coordinates.shape[0])]
    for source, target in edges.T:
        if 0 <= source < len(neighbours) and 0 <= target < len(neighbours):
            neighbours[int(source)].append(int(target))
            neighbours[int(target)].append(int(source))
    strain = np.full((coordinates.shape[0], 3), np.nan, dtype=np.float64)
    strain_mask = np.zeros_like(strain, dtype=bool)
    for node, local in enumerate(neighbours):
        valid = sorted({other for other in local if observed[other] and other != node})
        if not observed[node] or len(valid) < 2:
            continue
        dx = coordinates[valid] - coordinates[node]
        du = displacement[valid] - displacement[node]
        if np.linalg.matrix_rank(dx) < 2:
            continue
        gradient, *_ = np.linalg.lstsq(dx, du, rcond=None)
        # du = dx @ gradient; gradient[row coordinate, column displacement].
        eps_xx = gradient[0, 0]
        eps_yy = gradient[1, 1]
        eps_xy = 0.5 * (gradient[0, 1] + gradient[1, 0])
        strain[node] = (eps_xx, eps_yy, eps_xy)
        strain_mask[node] = True
    return strain, strain_mask


def derive_psi_raw_estimate_from_strain(
    *,
    strain: Any,
    mask: Any,
    youngs_modulus_pa: float,
    poisson_ratio: float,
    constitutive_model_id: str,
    tensile_split_id: str,
    kinematic_assumption: str,
) -> dict[str, Any]:
    """Derive a conditional tensile-energy estimate, never a sensor value."""
    if not constitutive_model_id or not tensile_split_id:
        raise ValueError("constitutive_model_id and tensile_split_id are required")
    if kinematic_assumption not in {"plane_stress", "plane_strain"}:
        raise ValueError("kinematic_assumption must be plane_stress or plane_strain")
    if not np.isfinite(youngs_modulus_pa) or youngs_modulus_pa <= 0:
        raise ValueError("Young's modulus must be finite and positive")
    if not np.isfinite(poisson_ratio) or not (-0.99 < poisson_ratio < 0.49):
        raise ValueError("Poisson ratio is outside the supported isotropic range")
    eps = _as_float(strain)
    observed = _as_mask(mask, eps.shape)
    if eps.ndim != 2 or eps.shape[1] != 3:
        raise ValueError("strain must have columns eps_xx, eps_yy, eps_xy")
    node_mask = np.all(observed, axis=1)
    values = np.full(eps.shape[0], np.nan, dtype=np.float64)
    mu = youngs_modulus_pa / (2.0 * (1.0 + poisson_ratio))
    if kinematic_assumption == "plane_stress":
        lam = youngs_modulus_pa * poisson_ratio / (1.0 - poisson_ratio**2)
    else:
        lam = youngs_modulus_pa * poisson_ratio / ((1.0 + poisson_ratio) * (1.0 - 2.0 * poisson_ratio))
    for index in np.flatnonzero(node_mask):
        tensor = np.asarray([[eps[index, 0], eps[index, 2]], [eps[index, 2], eps[index, 1]]])
        eigenvalues = np.linalg.eigvalsh(tensor)
        positive = np.maximum(eigenvalues, 0.0)
        values[index] = 0.5 * lam * max(float(np.trace(tensor)), 0.0) ** 2 + mu * float(np.sum(positive**2))
    return {
        "schema_version": DERIVED_ESTIMATE_VERSION,
        "estimate_name": "psi_raw_tensile_estimate",
        "units": "J/m^3",
        "values": values,
        "mask": node_mask,
        "direct_sensor_observation": False,
        "decision_eligible": False,
        "requires": {
            "constitutive_model_id": constitutive_model_id,
            "tensile_split_id": tensile_split_id,
            "kinematic_assumption": kinematic_assumption,
            "youngs_modulus_pa": float(youngs_modulus_pa),
            "poisson_ratio": float(poisson_ratio),
        },
        "claim_boundary": "conditional derived latent estimate; not directly measured psi_raw",
    }


def adapt_fwd_observation(
    *,
    load_n: float | None,
    offsets_m: Any,
    deflection_m: Any,
    mask: Any,
    std_m: Any,
    timestamp: str,
    evidence_class: str,
    registration: Mapping[str, Any],
) -> MeasurementRecord:
    offsets = _as_float(offsets_m).reshape(-1)
    deflection = _as_float(deflection_m).reshape(-1)
    available = np.asarray(mask, dtype=bool).reshape(-1)
    uncertainty = _as_float(std_m).reshape(-1)
    if offsets.shape != deflection.shape or available.shape != deflection.shape or uncertainty.shape != deflection.shape:
        raise ValueError("FWD offsets, deflections, mask and uncertainty must share shape")
    rows = np.column_stack((np.full_like(deflection, np.nan if load_n is None else load_n), offsets, deflection))
    row_mask = np.column_stack((np.full_like(available, load_n is not None), np.isfinite(offsets), available))
    row_std = np.column_stack((np.where(row_mask[:, 0], 0.0, np.nan), np.where(row_mask[:, 1], 0.0, np.nan), uncertainty))
    rows[~row_mask] = np.nan
    row_std[~row_mask] = np.nan
    observed_offsets = offsets[available & np.isfinite(offsets) & np.isfinite(deflection)]
    observed_deflection = deflection[available & np.isfinite(offsets) & np.isfinite(deflection)]
    basin = None
    if observed_offsets.size >= 2:
        order = np.argsort(observed_offsets)
        basin = float(np.trapezoid(observed_deflection[order], observed_offsets[order]))
    return _record(
        operator_id="fwd_load_deflection_basin_v1",
        family="fwd_load_deflection",
        channel_names=("fwd_load", "fwd_offset", "fwd_deflection"),
        units=("N", "m", "m"),
        values=rows,
        mask=row_mask,
        std=row_std,
        timestamp=timestamp,
        evidence_class=evidence_class,
        registration=registration,
        metadata={"basin_integral_m2": basin, "direct_measurand": "FWD load and deflection basin"},
    )


def adapt_wim_observation(
    *,
    axle_load_n: Any,
    speed_mps: Any,
    mask: Any,
    std: Any,
    timestamp: str,
    evidence_class: str,
    spectrum_edges_n: Any,
    equivalent_load_calibration_id: str | None = None,
) -> MeasurementRecord:
    load = _as_float(axle_load_n).reshape(-1)
    speed = _as_float(speed_mps).reshape(-1)
    available = np.asarray(mask, dtype=bool).reshape(-1)
    uncertainty = _as_float(std)
    if uncertainty.shape != (load.shape[0], 2):
        raise ValueError("WIM uncertainty must have shape [N,2]")
    if speed.shape != load.shape or available.shape != load.shape:
        raise ValueError("WIM load, speed and mask must share shape")
    values = np.column_stack((load, speed))
    pair_mask = np.repeat(available[:, None], 2, axis=1)
    values[~pair_mask] = np.nan
    uncertainty[~pair_mask] = np.nan
    edges = _as_float(spectrum_edges_n).reshape(-1)
    if edges.size < 2 or np.any(np.diff(edges) <= 0):
        raise ValueError("WIM spectrum edges must be strictly increasing")
    counts, _ = np.histogram(load[available & np.isfinite(load)], bins=edges)
    return _record(
        operator_id="wim_axle_load_speed_spectrum_v1",
        family="wim_traffic",
        channel_names=("wim_axle_load", "wim_speed"),
        units=("N", "m/s"),
        values=values,
        mask=pair_mask,
        std=uncertainty,
        timestamp=timestamp,
        evidence_class=evidence_class,
        metadata={
            "spectrum_edges_n": edges.tolist(),
            "spectrum_counts": counts.tolist(),
            "equivalent_load_calibration_id": equivalent_load_calibration_id,
            "equivalent_load_index": None,
            "equivalent_load_rule": "must remain null unless an explicit calibration is applied",
        },
    )


def adapt_temperature_time(
    *,
    air_temperature_c: float | None,
    pavement_temperature_c: float | None,
    elapsed_s: float | None,
    std: Sequence[float | None],
    timestamp: str,
    evidence_class: str,
) -> MeasurementRecord:
    values = np.asarray([[air_temperature_c, pavement_temperature_c, elapsed_s]], dtype=np.float64)
    mask = np.isfinite(values)
    uncertainty = np.asarray([[np.nan if value is None else value for value in std]], dtype=np.float64)
    if uncertainty.shape != values.shape:
        raise ValueError("temperature/time uncertainty must contain three entries")
    uncertainty[~mask] = np.nan
    return _record(
        operator_id="temperature_time_v1",
        family="temperature_time",
        channel_names=("air_temperature", "pavement_temperature", "elapsed_time"),
        units=("degC", "degC", "s"),
        values=values,
        mask=mask,
        std=uncertainty,
        timestamp=timestamp,
        evidence_class=evidence_class,
        metadata={"timestamp_is_observation": True},
    )


def adapt_maintenance_event(
    *,
    reset: bool,
    event_id: str | None,
    event_code: int | None,
    new_state_segment_id: str | None,
    timestamp: str,
    evidence_class: str,
) -> MeasurementRecord:
    if reset and (not event_id or not new_state_segment_id):
        raise ValueError("maintenance reset requires event_id and new_state_segment_id")
    value = np.asarray([[np.nan if event_code is None else event_code, float(reset)]], dtype=np.float64)
    mask = np.asarray([[event_code is not None, True]], dtype=bool)
    std = np.where(mask, 0.0, np.nan)
    return _record(
        operator_id="maintenance_reset_v1",
        family="maintenance_reset",
        channel_names=("maintenance_event_code", "maintenance_reset"),
        units=("category", "bool"),
        values=value,
        mask=mask,
        std=std,
        timestamp=timestamp,
        evidence_class=evidence_class,
        metadata={"event_id": event_id, "new_state_segment_id": new_state_segment_id},
    )


def measurement_operator_spec() -> dict[str, Any]:
    return {
        "schema_version": MEASUREMENT_SPEC_VERSION,
        "handoff_version": HANDOFF_VERSION,
        "purpose": "real-measurable observation to predictor-independent inverse/forecast handoff",
        "allowed_families": list(OBSERVATION_FAMILIES),
        "forbidden_direct_channels": sorted(FORBIDDEN_DIRECT_CHANNELS),
        "evidence_classes": {
            "real_measurement": "registered instrument/image observation with provenance",
            "synthetic_sensor_smoke": "explicit measurement rendering used only for contract validation",
        },
        "missingness": "NaN/null plus mask=false; never zero-fill before preserving the mask",
        "spatial_registration": {
            "required": [
                "coordinate_frame_id", "target_frame_id", "registration_id",
                "transform_3x3", "uncertainty_std_m", "source_sha256",
            ],
            "rule": "spatial channels cannot enter assimilation without registration provenance",
        },
        "derived_estimate_firewall": {
            "dic_or_strain_to_psi_raw": "requires constitutive model, material parameters, kinematic assumption, and tensile split",
            "storage": "derived_estimates only",
            "direct_sensor_observation": False,
            "decision_eligible": False,
        },
        "multi_trajectory_compatibility": {
            "stable_envelope": HANDOFF_VERSION,
            "identity_keys": ["asset_id", "trajectory_id", "inspection_id", "state_segment_id"],
            "rule": "future schemas require a versioned adapter; no inferred field names or shapes",
        },
    }


def measurement_handoff_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": HANDOFF_VERSION,
        "type": "object",
        "required": [
            "schema_version", "asset_id", "trajectory_id", "inspection_id",
            "state_segment_id", "target_schema_requested", "adapter_status",
            "records", "derived_estimates", "decision_eligible", "claim_boundary",
            "decision_eligibility_rule",
        ],
        "properties": {
            "schema_version": {"const": HANDOFF_VERSION},
            "asset_id": {"type": "string", "minLength": 1},
            "trajectory_id": {"type": "string", "minLength": 1},
            "inspection_id": {"type": "string", "minLength": 1},
            "state_segment_id": {"type": "string", "minLength": 1},
            "target_schema_requested": {"type": "string", "minLength": 1},
            "target_adapter": {"type": ["string", "null"]},
            "adapter_status": {
                "enum": ["available", "versioned_adapter_required_no_schema_guessing"]
            },
            "records": {"type": "array"},
            "derived_estimates": {"type": "array"},
            "decision_eligible": {"type": "boolean"},
            "decision_eligibility_rule": {"type": "string"},
            "claim_boundary": {"type": "string"},
        },
        "additionalProperties": False,
        "array_payload_rule": "record and derived arrays are stored in the companion NPZ by ordinal index",
    }


def identifiability_ladder_rows() -> list[dict[str, str]]:
    return [
        {"level": "L0", "observations": "time + temperature + WIM + maintenance", "hidden_state_assimilation": "not identified", "material_parameter_inversion": "not identified", "forecast_update": "forcing/reset update only", "minimum_evidence": "timestamped load/environment provenance"},
        {"level": "L1", "observations": "L0 + registered crack image/mask/width/length", "hidden_state_assimilation": "surface geometry partial", "material_parameter_inversion": "not identified", "forecast_update": "geometry-conditioned", "minimum_evidence": "repeatable registration and segmentation uncertainty"},
        {"level": "L2", "observations": "L1 + FWD load/deflection basin", "hidden_state_assimilation": "geometry + stiffness response partial", "material_parameter_inversion": "confounded", "forecast_update": "state correction candidate", "minimum_evidence": "known load, basin and temperature"},
        {"level": "L3", "observations": "L2 + registered DIC or strain", "hidden_state_assimilation": "mechanical state conditional", "material_parameter_inversion": "still conditional/non-unique", "forecast_update": "local mechanical correction candidate", "minimum_evidence": "constitutive assumptions declared for derived energy"},
        {"level": "L4", "observations": "repeated multimodal visits + WIM/environment/reset", "hidden_state_assimilation": "conditional candidate", "material_parameter_inversion": "not automatic", "forecast_update": "operational candidate after holdout calibration", "minimum_evidence": "multiple visits and calibrated uncertainty"},
        {"level": "L5", "observations": "L4 across independent loads/assets/material evidence", "hidden_state_assimilation": "testable", "material_parameter_inversion": "candidate only after rank/posterior checks", "forecast_update": "multi-asset validation candidate", "minimum_evidence": "independent excitation, sensitivity rank and physical holdout"},
    ]


def identifiability_matrix_rows() -> list[dict[str, str]]:
    return [
        {"channel": "registered crack image/mask/width/length", "direct_measurand": "surface crack geometry", "hidden_state": "alpha geometry proxy only", "material_parameters": "weak/non-unique", "forecast_update": "yes", "main_confounds": "visibility, segmentation, registration"},
        {"channel": "DIC displacement", "direct_measurand": "surface displacement", "hidden_state": "mechanical state partial", "material_parameters": "load/BC/model confounded", "forecast_update": "yes", "main_confounds": "registration, illumination, out-of-plane motion"},
        {"channel": "strain sensor", "direct_measurand": "directional strain", "hidden_state": "local mechanics partial", "material_parameters": "conditional", "forecast_update": "yes", "main_confounds": "orientation, drift, temperature"},
        {"channel": "FWD load + basin", "direct_measurand": "load-response stiffness", "hidden_state": "global/local stiffness partial", "material_parameters": "layer/thickness/damage confounded", "forecast_update": "yes", "main_confounds": "temperature, support, layer structure"},
        {"channel": "WIM axle/load/speed/spectrum", "direct_measurand": "traffic forcing", "hidden_state": "no", "material_parameters": "no", "forecast_update": "forcing", "main_confounds": "classification, calibration, missing vehicles"},
        {"channel": "temperature/time", "direct_measurand": "environment/time", "hidden_state": "no", "material_parameters": "temperature-dependence only", "forecast_update": "forcing", "main_confounds": "depth and spatial representativeness"},
        {"channel": "maintenance/reset", "direct_measurand": "intervention event", "hidden_state": "state segmentation", "material_parameters": "no", "forecast_update": "mandatory reset", "main_confounds": "incomplete work records"},
        {"channel": "derived psi_raw estimate", "direct_measurand": "none", "hidden_state": "conditional derived estimate", "material_parameters": "assumed, not identified", "forecast_update": "ineligible unless assimilated with calibration", "main_confounds": "constitutive model and tensile split"},
    ]


def assess_identifiability(
    *,
    families: Sequence[str],
    repeated_epochs: int,
    independent_load_cases: int,
    calibrated_uncertainty: bool,
    multiple_assets: bool,
) -> dict[str, Any]:
    observed = set(families)
    unknown = sorted(observed - set(OBSERVATION_FAMILIES))
    if unknown:
        raise ValueError(f"unknown observation families: {unknown}")
    geometry = "registered_crack_geometry" in observed
    response = bool({"fwd_load_deflection", "dic_displacement", "strain_sensor"} & observed)
    forcing = "wim_traffic" in observed and "temperature_time" in observed
    hidden_candidate = geometry and response and repeated_epochs >= 2
    material_candidate = hidden_candidate and independent_load_cases >= 2 and multiple_assets
    forecast_candidate = hidden_candidate and forcing and calibrated_uncertainty
    return {
        "hidden_state_assimilation": "conditional_candidate" if hidden_candidate else "not_identified",
        "material_parameter_inversion": "rank_and_posterior_gate_required" if material_candidate else "not_identified",
        "forecast_update": "holdout_gate_required" if forecast_candidate else "context_only_or_not_ready",
        "decision_eligible": False,
        "decision_rule": "assessment declares prerequisites only; empirical calibration and physical holdout remain required",
    }


def build_measurement_handoff(
    *,
    asset_id: str,
    trajectory_id: str,
    inspection_id: str,
    state_segment_id: str,
    records: Sequence[MeasurementRecord],
    derived_estimates: Sequence[Mapping[str, Any]] = (),
    target_schema_requested: str = "road_observation_state_bundle_v1",
) -> dict[str, Any]:
    if not all((asset_id, trajectory_id, inspection_id, state_segment_id)):
        raise ValueError("asset, trajectory, inspection and state-segment ids are required")
    descriptors = []
    for record in records:
        record.validate()
        descriptors.append(record.descriptor())
    derived_descriptors = []
    for estimate in derived_estimates:
        if estimate.get("direct_sensor_observation") is not False or estimate.get("decision_eligible") is not False:
            raise ValueError("derived latent estimates must remain outside direct observations and decision ineligible")
        derived_descriptors.append({key: value for key, value in estimate.items() if key not in {"values", "mask"}})
    adapter = STATE_BUNDLE_ADAPTER_VERSION if target_schema_requested == "road_observation_state_bundle_v1" else None
    return {
        "schema_version": HANDOFF_VERSION,
        "asset_id": asset_id,
        "trajectory_id": trajectory_id,
        "inspection_id": inspection_id,
        "state_segment_id": state_segment_id,
        "target_schema_requested": target_schema_requested,
        "target_adapter": adapter,
        "adapter_status": "available" if adapter else "versioned_adapter_required_no_schema_guessing",
        "records": descriptors,
        "derived_estimates": derived_descriptors,
        "decision_eligible": False,
        "decision_eligibility_rule": "a measurement handoff cannot self-authorize an inverse or forecast decision; calibration, identifiability, and quality gates must promote it",
        "claim_boundary": "measurement interface only; eligibility does not prove inverse identifiability or forecast validity",
    }


def adapt_handoff_to_state_bundle_v1_observations(
    *, handoff: Mapping[str, Any], records: Sequence[MeasurementRecord], node_count: int
) -> dict[str, Any]:
    """Map measurable records into the current bundle's observation arrays.

    This adapter does not create ``state_mean``. It only prepares measurement
    arrays for a separate assimilation step and leaves unavailable values masked.
    """
    if handoff.get("schema_version") != HANDOFF_VERSION:
        raise ValueError("unexpected measurement handoff version")
    if handoff.get("target_adapter") != STATE_BUNDLE_ADAPTER_VERSION:
        raise ValueError("handoff does not select the state-bundle-v1 adapter")
    if node_count <= 0:
        raise ValueError("node_count must be positive")
    node_channels = ("registered_crack_probability", "strain_axial", "log10_psi_raw_oracle")
    global_channels = (
        "crack_tip_x", "crack_width_mean", "fwd_deflection_center", "fwd_deflection_offset_300mm"
    )
    traffic_channels = ("equivalent_standard_axle_load_increment", "heavy_axle_count", "mean_axle_load")
    environment_channels = ("air_temperature", "pavement_temperature", "layer_moisture")
    node_values = np.full((1, node_count, len(node_channels)), np.nan, dtype=np.float64)
    node_mask = np.zeros_like(node_values, dtype=bool)
    global_values = np.full((1, len(global_channels)), np.nan, dtype=np.float64)
    global_mask = np.zeros_like(global_values, dtype=bool)
    traffic_values = np.full((1, len(traffic_channels)), np.nan, dtype=np.float64)
    traffic_mask = np.zeros_like(traffic_values, dtype=bool)
    environment_values = np.full((1, len(environment_channels)), np.nan, dtype=np.float64)
    environment_mask = np.zeros_like(environment_values, dtype=bool)
    timestamps: set[str] = set()
    mapped: list[str] = []
    unmapped: list[str] = []
    maintenance_reset = False
    maintenance_event_id = ""
    state_segment_id = str(handoff["state_segment_id"])

    for record in records:
        record.validate()
        timestamps.add(record.timestamp)
        channel_to_col = {name: index for index, name in enumerate(record.channel_names)}
        for channel in record.channel_names:
            if channel in node_channels:
                source_col = channel_to_col[channel]
                target_col = node_channels.index(channel)
                index_meta = record.metadata.get("target_node_index")
                if index_meta is None and record.values.shape[0] == node_count:
                    target_index = np.arange(node_count)
                elif index_meta is not None:
                    target_index = np.asarray(index_meta, dtype=np.int64)
                else:
                    unmapped.append(f"{record.operator_id}:{channel}:missing_target_node_index")
                    continue
                if target_index.shape != (record.values.shape[0],) or np.any(target_index >= node_count):
                    raise ValueError(f"invalid target_node_index for {record.operator_id}")
                observed = record.mask[:, source_col]
                node_values[0, target_index[observed], target_col] = record.values[observed, source_col]
                node_mask[0, target_index[observed], target_col] = True
                mapped.append(f"{record.operator_id}:{channel}")
            elif channel in {"crack_width", "crack_tip_x"}:
                source_col = channel_to_col[channel]
                target_name = "crack_width_mean" if channel == "crack_width" else channel
                target_col = global_channels.index(target_name)
                observed = np.flatnonzero(record.mask[:, source_col])
                if observed.size:
                    global_values[0, target_col] = float(record.values[observed[0], source_col])
                    global_mask[0, target_col] = True
                mapped.append(f"{record.operator_id}:{channel}")
            else:
                unmapped.append(f"{record.operator_id}:{channel}")

        if record.family == "fwd_load_deflection":
            offsets = record.values[:, channel_to_col["fwd_offset"]]
            deflection = record.values[:, channel_to_col["fwd_deflection"]]
            valid = record.mask[:, channel_to_col["fwd_offset"]] & record.mask[:, channel_to_col["fwd_deflection"]]
            for target_offset, target_name in ((0.0, "fwd_deflection_center"), (0.3, "fwd_deflection_offset_300mm")):
                if np.any(valid):
                    local = np.flatnonzero(valid)[np.argmin(np.abs(offsets[valid] - target_offset))]
                    if abs(float(offsets[local]) - target_offset) <= 0.05:
                        column = global_channels.index(target_name)
                        global_values[0, column] = float(deflection[local])
                        global_mask[0, column] = True
                        mapped.append(f"{record.operator_id}:{target_name}")
        elif record.family == "wim_traffic":
            load_col = channel_to_col["wim_axle_load"]
            valid = record.mask[:, load_col]
            if np.any(valid):
                traffic_values[0, traffic_channels.index("heavy_axle_count")] = int(np.count_nonzero(valid))
                traffic_values[0, traffic_channels.index("mean_axle_load")] = float(np.mean(record.values[valid, load_col]))
                traffic_mask[0, 1:] = True
                mapped.append(f"{record.operator_id}:traffic_summary")
        elif record.family == "temperature_time":
            for source_name, target_name in (("air_temperature", "air_temperature"), ("pavement_temperature", "pavement_temperature")):
                source_col = channel_to_col[source_name]
                if record.mask[0, source_col]:
                    target_col = environment_channels.index(target_name)
                    environment_values[0, target_col] = record.values[0, source_col]
                    environment_mask[0, target_col] = True
                    mapped.append(f"{record.operator_id}:{source_name}")
        elif record.family == "maintenance_reset":
            reset_col = channel_to_col["maintenance_reset"]
            if record.mask[0, reset_col]:
                maintenance_reset = bool(record.values[0, reset_col])
                maintenance_event_id = str(record.metadata.get("event_id") or "")
                if maintenance_reset:
                    state_segment_id = str(record.metadata["new_state_segment_id"])
                mapped.append(f"{record.operator_id}:maintenance_reset")

    if len(timestamps) > 1:
        raise ValueError("state-bundle adapter requires one timestamp per inspection packet")
    # The oracle audit channel is deliberately never populated by measurement records.
    assert not node_mask[:, :, node_channels.index("log10_psi_raw_oracle")].any()
    return {
        "adapter_version": STATE_BUNDLE_ADAPTER_VERSION,
        "node_observation_channels": node_channels,
        "node_observation_values": node_values,
        "node_observation_mask": node_mask,
        "global_observation_channels": global_channels,
        "global_observation_values": global_values,
        "global_observation_mask": global_mask,
        "traffic_channels": traffic_channels,
        "traffic_values": traffic_values,
        "traffic_mask": traffic_mask,
        "environment_channels": environment_channels,
        "environment_values": environment_values,
        "environment_mask": environment_mask,
        "timestamp": next(iter(timestamps), ""),
        "timestamp_mask": bool(timestamps),
        "maintenance_reset": maintenance_reset,
        "maintenance_event_id": maintenance_event_id,
        "state_segment_id": state_segment_id,
        "mapped": sorted(set(mapped)),
        "unmapped": sorted(set(unmapped)),
        "state_mean_created": False,
        "decision_eligible": False,
    }


def write_measurement_handoff_npz(
    path: Path,
    handoff: Mapping[str, Any],
    records: Sequence[MeasurementRecord],
    derived_estimates: Sequence[Mapping[str, Any]] = (),
) -> None:
    arrays: dict[str, np.ndarray] = {
        "schema_version": np.asarray(HANDOFF_VERSION),
        "handoff_json": np.asarray(json.dumps(handoff, sort_keys=True)),
    }
    for index, record in enumerate(records):
        prefix = f"record_{index:02d}"
        arrays[f"{prefix}_values"] = record.values
        arrays[f"{prefix}_mask"] = record.mask
        arrays[f"{prefix}_std"] = record.std
    for index, estimate in enumerate(derived_estimates):
        prefix = f"derived_{index:02d}"
        arrays[f"{prefix}_values"] = np.asarray(estimate["values"], dtype=np.float64)
        arrays[f"{prefix}_mask"] = np.asarray(estimate["mask"], dtype=bool)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)


def validate_measurement_handoff_npz(path: Path) -> list[str]:
    errors: list[str] = []
    with np.load(path, allow_pickle=False) as package:
        if "schema_version" not in package or str(package["schema_version"].item()) != HANDOFF_VERSION:
            return ["unexpected or missing handoff schema version"]
        try:
            handoff = json.loads(str(package["handoff_json"].item()))
        except (KeyError, json.JSONDecodeError):
            return ["missing or invalid handoff_json"]
        if handoff.get("schema_version") != HANDOFF_VERSION:
            errors.append("handoff JSON schema version differs")
        for record in handoff.get("records", []):
            for channel in record.get("channel_names", []):
                if str(channel).lower().removesuffix("_oracle") in FORBIDDEN_DIRECT_CHANNELS:
                    errors.append(f"latent direct observation escaped firewall: {channel}")
        for estimate in handoff.get("derived_estimates", []):
            if estimate.get("direct_sensor_observation") is not False or estimate.get("decision_eligible") is not False:
                errors.append("derived estimate escaped decision firewall")
        if handoff.get("adapter_status") == "versioned_adapter_required_no_schema_guessing" and handoff.get("target_adapter") is not None:
            errors.append("unknown target schema must not receive a guessed adapter")
    return errors
