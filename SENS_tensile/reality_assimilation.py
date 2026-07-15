#!/usr/bin/env python3
"""Reality-facing observation and sequential FEM-library assimilation tools.

The module deliberately separates three things that older M2S scripts mixed:

* observable channels (vision, known load/environment, measured response),
* synthetic sensor proxies (mechanical-energy and damage-activity proxies), and
* hidden FEM/phase-field state used only as an oracle ceiling.

No neural-network or PIDL training is performed here.  A collection of FEM
trajectories is treated as a discrete model library and sequential observations
update the posterior weight of each candidate trajectory.  The posterior is
then propagated to remaining life and future crack geometry.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import glob
import json
import os
from pathlib import Path
import re
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.io import loadmat

from run_m2s_synthetic_validation import (
    feature_row,
    load_fem_handoff,
    orient_conn,
    orient_points,
    polygon_areas,
    weighted_mean,
)


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    channel: str
    status: str
    physical_meaning: str
    deployment_source: str


FEATURE_CATALOG: tuple[FeatureSpec, ...] = (
    FeatureSpec(
        "crack_tip_x_d09",
        "vision_geometry",
        "observable",
        "surface crack-tip coordinate after calibrated segmentation/registration",
        "repeated calibrated RGB/line-scan/3D inspection",
    ),
    FeatureSpec(
        "damage_area_gt_0p5",
        "vision_geometry",
        "observable_proxy",
        "visible cracked-area fraction; FEM damage threshold is a synthetic rendering rule",
        "registered crack mask with physical pixel scale",
    ),
    FeatureSpec(
        "damage_area_gt_0p9",
        "vision_geometry",
        "observable_proxy",
        "high-confidence open-crack area fraction",
        "registered crack mask with calibrated severity threshold",
    ),
    FeatureSpec(
        "visible_crack_width_y",
        "vision_geometry",
        "observable_proxy",
        "transverse width of the visible damaged support",
        "calibrated image, stereo, structured light, or 3D line scan",
    ),
    FeatureSpec(
        "umax",
        "load_environment",
        "observable",
        "known loading amplitude for the synthetic benchmark",
        "traffic axle/load monitoring; replace with load-spectrum summaries in field data",
    ),
    FeatureSpec(
        "mechanical_energy_tip_proxy",
        "mechanical_response",
        "synthetic_proxy",
        "tip-local raw tensile-energy reduction; not a directly measured strain",
        "future replacement: DIC/strain/FBG features mapped through an observation model",
    ),
    FeatureSpec(
        "mechanical_energy_strip_proxy",
        "mechanical_response",
        "synthetic_proxy",
        "crack-strip raw tensile-energy reduction",
        "future replacement: sparse strain or full-field DIC response",
    ),
    FeatureSpec(
        "ae_damage_activity_proxy",
        "damage_activity",
        "synthetic_proxy",
        "positive damage increment per accumulated cycle",
        "future replacement: localized acoustic-emission event rate/energy",
    ),
    FeatureSpec(
        "ae_history_activity_proxy",
        "damage_activity",
        "synthetic_proxy",
        "positive fatigue-history increment per accumulated cycle",
        "future replacement: AE plus load-conditioned damage-activity likelihood",
    ),
    FeatureSpec(
        "dic_tip_response",
        "mechanical_response",
        "observable_modelled",
        "calibrated tip-local DIC or strain-sensor response feature",
        "registered peak-load DIC/FBG/strain measurement through a versioned calibration",
    ),
    FeatureSpec(
        "dic_strip_response",
        "mechanical_response",
        "observable_modelled",
        "calibrated crack-strip DIC or strain-sensor response feature",
        "registered full-field DIC or sparse strain array through a versioned calibration",
    ),
    FeatureSpec(
        "ae_log_event_rate",
        "damage_activity",
        "observable_modelled",
        "load-normalized localized acoustic-emission log event rate",
        "localized AE catalogue with a locked threshold and inspection exposure",
    ),
    FeatureSpec(
        "ae_log_energy_rate",
        "damage_activity",
        "observable_modelled",
        "load-normalized localized acoustic-emission log energy rate",
        "localized AE waveform energy with a locked threshold and inspection exposure",
    ),
    FeatureSpec(
        "alpha_bar_p99",
        "hidden_state",
        "oracle_only",
        "FEM fatigue-history upper-tail state",
        "not directly observable; posterior latent state only",
    ),
    FeatureSpec(
        "fatigue_f_tip_2l0_mean",
        "hidden_state",
        "oracle_only",
        "tip-local fatigue degradation",
        "not directly observable; posterior latent state only",
    ),
    FeatureSpec(
        "psi_active_tip_2l0_mean",
        "hidden_state",
        "oracle_only",
        "tip-local degraded active driver",
        "not directly observable; posterior latent state only",
    ),
)

FEATURE_BY_NAME = {spec.name: spec for spec in FEATURE_CATALOG}

OBSERVATION_TIERS: Mapping[str, tuple[str, ...]] = {
    "tip_only": ("crack_tip_x_d09",),
    "vision_only": (
        "crack_tip_x_d09",
        "damage_area_gt_0p5",
        "damage_area_gt_0p9",
        "visible_crack_width_y",
    ),
    "vision_plus_load": (
        "crack_tip_x_d09",
        "damage_area_gt_0p5",
        "damage_area_gt_0p9",
        "visible_crack_width_y",
        "umax",
    ),
    "vision_load_mechanical": (
        "crack_tip_x_d09",
        "damage_area_gt_0p5",
        "damage_area_gt_0p9",
        "visible_crack_width_y",
        "umax",
        "mechanical_energy_tip_proxy",
        "mechanical_energy_strip_proxy",
    ),
    "vision_load_mechanical_activity": (
        "crack_tip_x_d09",
        "damage_area_gt_0p5",
        "damage_area_gt_0p9",
        "visible_crack_width_y",
        "umax",
        "mechanical_energy_tip_proxy",
        "mechanical_energy_strip_proxy",
        "ae_damage_activity_proxy",
        "ae_history_activity_proxy",
    ),
    "vision_load_dic": (
        "crack_tip_x_d09",
        "damage_area_gt_0p5",
        "damage_area_gt_0p9",
        "visible_crack_width_y",
        "umax",
        "dic_tip_response",
        "dic_strip_response",
    ),
    "vision_load_dic_ae": (
        "crack_tip_x_d09",
        "damage_area_gt_0p5",
        "damage_area_gt_0p9",
        "visible_crack_width_y",
        "umax",
        "dic_tip_response",
        "dic_strip_response",
        "ae_log_event_rate",
        "ae_log_energy_rate",
    ),
    "oracle_hidden_state": tuple(
        spec.name for spec in FEATURE_CATALOG if spec.status != "observable_modelled"
    ),
}


@dataclass(frozen=True)
class SensorObservationModel:
    """Versioned linear sensor calibration from FEM proxies to measured features.

    The mapping is deliberately explicit. It is only a bridge until raw FEM
    strain fields and laboratory paired sensor data are available; calibration
    status is carried into every inference manifest.
    """

    model_id: str
    calibration_status: str
    channels: Mapping[str, Mapping[str, object]]
    approved_for_inference: bool = False
    calibration_metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        allowed = {"synthetic_only", "lab_calibrated", "field_calibrated"}
        if self.calibration_status not in allowed:
            raise ValueError(
                f"calibration_status must be one of {sorted(allowed)}, got {self.calibration_status!r}"
            )
        if not self.model_id:
            raise ValueError("Sensor observation model needs a non-empty model_id")
        for output_name, spec in self.channels.items():
            if output_name not in FEATURE_BY_NAME:
                raise ValueError(f"Sensor observation model has unknown output {output_name}")
            if FEATURE_BY_NAME[output_name].status != "observable_modelled":
                raise ValueError(f"Sensor output {output_name} is not a modelled observable channel")
            sources = spec.get("sources")
            if not isinstance(sources, Mapping) or not sources:
                raise ValueError(f"Sensor channel {output_name} needs a non-empty sources mapping")
            sigma = float(spec.get("sigma", 0.0))
            if sigma < 0.0:
                raise ValueError(f"Sensor channel {output_name} has negative sigma")
            for source_name, gain in sources.items():
                if source_name not in FEATURE_BY_NAME:
                    raise ValueError(f"Sensor channel {output_name} uses unknown source {source_name}")
                if not np.isfinite(float(gain)):
                    raise ValueError(f"Sensor channel {output_name} has non-finite gain")
        if self.calibration_status != "synthetic_only" and not any(
            float(spec.get("sigma", 0.0)) > 0.0 for spec in self.channels.values()
        ):
            raise ValueError("A calibrated sensor model must include non-zero residual uncertainty")

    @property
    def output_features(self) -> tuple[str, ...]:
        return tuple(self.channels)

    @property
    def noise_scales(self) -> dict[str, float]:
        return {name: float(spec.get("sigma", 0.0)) for name, spec in self.channels.items()}

    @classmethod
    def from_json(cls, path: Path) -> "SensorObservationModel":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            model_id=str(payload["model_id"]),
            calibration_status=str(payload["calibration_status"]),
            channels=payload["channels"],
            approved_for_inference=bool(payload.get("approved_for_inference", False)),
            calibration_metadata=payload.get("calibration_metadata", {}),
        )


DEFAULT_SYNTHETIC_SENSOR_MODEL = SensorObservationModel(
    model_id="synthetic_proxy_identity_v1",
    calibration_status="synthetic_only",
    approved_for_inference=False,
    channels={
        "dic_tip_response": {
            "sources": {"mechanical_energy_tip_proxy": 1.0},
            "offset": 0.0,
            "sigma": 0.0,
        },
        "dic_strip_response": {
            "sources": {"mechanical_energy_strip_proxy": 1.0},
            "offset": 0.0,
            "sigma": 0.0,
        },
        "ae_log_event_rate": {
            "sources": {"ae_damage_activity_proxy": 1.0},
            "offset": 0.0,
            "sigma": 0.0,
        },
        "ae_log_energy_rate": {
            "sources": {"ae_history_activity_proxy": 1.0},
            "offset": 0.0,
            "sigma": 0.0,
        },
    },
)


def validate_sensor_model_for_inference(
    model: SensorObservationModel,
    tier: str | None = None,
) -> None:
    if model.calibration_status == "synthetic_only":
        raise ValueError("Real/laboratory DIC/AE inference rejects synthetic_only calibration")
    if not model.approved_for_inference:
        raise ValueError(
            "Sensor calibration is not approved_for_inference; review its grouped validation package first"
        )
    if tier is not None:
        if tier not in OBSERVATION_TIERS:
            raise KeyError(f"Unknown observation tier {tier}")
        required = {
            name
            for name in OBSERVATION_TIERS[tier]
            if FEATURE_BY_NAME[name].status == "observable_modelled"
        }
        missing = sorted(required - set(model.output_features))
        if missing:
            raise ValueError(f"Sensor calibration lacks channels required by {tier}: {missing}")


def vision_features_from_probability_mask(
    probability: np.ndarray,
    *,
    pixel_size_x: float,
    pixel_size_y: float,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    flip_y: bool = False,
) -> dict[str, float]:
    """Map a registered crack-probability mask into `reality_obs_v1` geometry.

    Threshold 0.9 matches the FEM `d>=0.9` crack-tip convention. The 0.5
    support supplies the visible-area/width features and a simple threshold
    uncertainty band; raw RGB segmentation is intentionally out of scope.
    """
    mask = np.asarray(probability, dtype=float)
    if mask.ndim != 2 or mask.size == 0:
        raise ValueError("Crack probability mask must be a non-empty 2D array")
    if not (np.isfinite(mask).all() and 0.0 <= float(mask.min()) and float(mask.max()) <= 1.0):
        raise ValueError("Crack probability mask values must be finite and lie in [0, 1]")
    if pixel_size_x <= 0.0 or pixel_size_y <= 0.0:
        raise ValueError("Physical pixel sizes must be positive")
    row_index, col_index = np.indices(mask.shape)
    x = float(origin_x) + (col_index + 0.5) * float(pixel_size_x)
    if flip_y:
        y = float(origin_y) + (mask.shape[0] - row_index - 0.5) * float(pixel_size_y)
    else:
        y = float(origin_y) + (row_index + 0.5) * float(pixel_size_y)
    support_05 = mask >= 0.5
    support_09 = mask >= 0.9
    pixel_area = float(pixel_size_x) * float(pixel_size_y)

    def max_x(support: np.ndarray) -> float:
        return float(np.max(x[support])) if np.any(support) else float("nan")

    if np.any(support_05):
        visible_width = float(np.max(y[support_05]) - np.min(y[support_05]) + pixel_size_y)
    else:
        visible_width = 0.0
    area_05 = float(np.count_nonzero(support_05) * pixel_area)
    area_09 = float(np.count_nonzero(support_09) * pixel_area)
    tip_05 = max_x(support_05)
    tip_09 = max_x(support_09)
    return {
        "crack_tip_x_d09": tip_09,
        "damage_area_gt_0p5": area_05,
        "damage_area_gt_0p9": area_09,
        "visible_crack_width_y": visible_width,
        "vision_tip_x_threshold_lower": tip_09,
        "vision_tip_x_threshold_upper": tip_05,
        "vision_uncertain_area_0p5_to_0p9": max(0.0, area_05 - area_09),
    }


@dataclass
class Trajectory:
    trajectory_id: str
    source_path: Path
    failure_cycle: int | None
    umax: float
    rows: pd.DataFrame
    censored: bool = False
    censor_cycle: int | None = None
    parameters: Mapping[str, float] = field(default_factory=dict)
    physics_family: str = "unspecified"

    def __post_init__(self) -> None:
        if self.censored:
            if self.censor_cycle is None:
                raise ValueError(f"Censored trajectory {self.trajectory_id} needs censor_cycle")
        elif self.failure_cycle is None:
            raise ValueError(f"Uncensored trajectory {self.trajectory_id} needs failure_cycle")
        if any(not np.isfinite(float(value)) for value in self.parameters.values()):
            raise ValueError(f"Trajectory {self.trajectory_id} has a non-finite inverse parameter")
        if not str(self.physics_family).strip():
            raise ValueError(f"Trajectory {self.trajectory_id} needs a non-empty physics_family")

    @property
    def terminal_cycle(self) -> int:
        return int(self.censor_cycle if self.censored else self.failure_cycle)

    @property
    def inference_parameters(self) -> dict[str, float]:
        return {"umax": float(self.umax), **{str(k): float(v) for k, v in self.parameters.items()}}

    def row_at(self, cycle: float) -> pd.Series:
        cycles = self.rows["cycle"].to_numpy(dtype=float)
        target = float(cycle)
        if target <= cycles[0]:
            return self.rows.iloc[0].copy()
        if target >= cycles[-1]:
            return self.rows.iloc[-1].copy()
        upper = int(np.searchsorted(cycles, target, side="right"))
        lower = upper - 1
        if np.isclose(cycles[lower], target):
            return self.rows.iloc[lower].copy()
        fraction = (target - cycles[lower]) / (cycles[upper] - cycles[lower])
        left = self.rows.iloc[lower].copy()
        right = self.rows.iloc[upper]
        for name in self.rows.columns:
            if pd.api.types.is_numeric_dtype(self.rows[name]):
                left[name] = float(left[name]) + fraction * (float(right[name]) - float(left[name]))
        left["cycle"] = target
        if self.censored:
            left["remaining_life"] = float("nan")
            left["remaining_life_lower_bound"] = max(0.0, float(self.terminal_cycle) - target)
        else:
            left["remaining_life"] = max(0.0, float(self.failure_cycle) - target)
            left["remaining_life_lower_bound"] = left["remaining_life"]
        return left

    def future_row(self, cycle: float, horizon: int) -> pd.Series:
        return self.row_at(min(float(cycle) + int(horizon), float(self.terminal_cycle)))


def validate_physics_library(
    trajectories: Sequence[Trajectory],
    *,
    allow_mixed: bool = False,
) -> tuple[str, ...]:
    """Reject confounded model libraries unless explicitly used as tooling stress."""
    if not trajectories:
        raise ValueError("Trajectory library is empty")
    families = tuple(sorted({trajectory.physics_family for trajectory in trajectories}))
    if len(families) > 1 and not allow_mixed:
        raise ValueError(
            "Trajectory library mixes physics_family values: " + ", ".join(families)
        )
    return families


def project_trajectory_to_sensor_space(
    trajectory: Trajectory,
    model: SensorObservationModel,
) -> Trajectory:
    """Apply a noiseless sensor observation operator to one FEM trajectory."""
    rows = trajectory.rows.copy()
    for output_name, spec in model.channels.items():
        values = np.full(len(rows), float(spec.get("offset", 0.0)), dtype=float)
        sources = spec["sources"]
        assert isinstance(sources, Mapping)
        for source_name, gain in sources.items():
            if source_name not in rows.columns:
                raise ValueError(
                    f"Trajectory {trajectory.trajectory_id} lacks {source_name} required by {model.model_id}"
                )
            values += float(gain) * pd.to_numeric(rows[source_name], errors="coerce").to_numpy(float)
        rows[output_name] = values
    return Trajectory(
        trajectory_id=trajectory.trajectory_id,
        source_path=trajectory.source_path,
        failure_cycle=trajectory.failure_cycle,
        umax=trajectory.umax,
        rows=rows,
        censored=trajectory.censored,
        censor_cycle=trajectory.censor_cycle,
        parameters=trajectory.parameters,
        physics_family=trajectory.physics_family,
    )


def simulate_sensor_observations(
    trajectory: Trajectory,
    model: SensorObservationModel,
    *,
    noise_multiplier: float = 1.0,
    missing_probability: float = 0.0,
    random_seed: int = 0,
) -> Trajectory:
    """Render noisy/missing sensor observations while preserving truth columns."""
    if noise_multiplier < 0.0:
        raise ValueError("noise_multiplier must be non-negative")
    if not 0.0 <= missing_probability < 1.0:
        raise ValueError("missing_probability must be in [0, 1)")
    projected = project_trajectory_to_sensor_space(trajectory, model)
    rows = projected.rows.copy()
    rng = np.random.default_rng(int(random_seed))
    for name, sigma in model.noise_scales.items():
        values = rows[name].to_numpy(dtype=float)
        effective_sigma = float(sigma) * float(noise_multiplier)
        if effective_sigma > 0.0:
            values = values + rng.normal(0.0, effective_sigma, size=len(values))
        if missing_probability > 0.0:
            missing = rng.random(len(values)) < float(missing_probability)
            values[missing] = np.nan
        rows[name] = values
    return Trajectory(
        trajectory_id=projected.trajectory_id,
        source_path=projected.source_path,
        failure_cycle=projected.failure_cycle,
        umax=projected.umax,
        rows=rows,
        censored=projected.censored,
        censor_cycle=projected.censor_cycle,
        parameters=projected.parameters,
        physics_family=projected.physics_family,
    )


def _visible_width(damage: np.ndarray, y: np.ndarray, threshold: float = 0.5) -> float:
    mask = damage >= threshold
    if not bool(np.any(mask)):
        return 0.0
    return float(np.max(y[mask]) - np.min(y[mask]))


def _trajectory_from_arrays(
    *,
    source_path: Path,
    cycles: np.ndarray,
    centroids: np.ndarray,
    areas: np.ndarray,
    damage_by_cycle: np.ndarray,
    history_by_cycle: np.ndarray,
    fatigue_f_by_cycle: np.ndarray,
    psi_raw_by_cycle: np.ndarray,
    trajectory_id: str,
    umax: float,
    failure_cycle: int | None,
    censored: bool,
    censor_cycle: int | None,
    parameters: Mapping[str, float] | None,
    physics_family: str,
    l0: float,
    crack_strip_y: float,
    boundary_x: float,
) -> Trajectory:
    terminal_cycle = int(censor_cycle if censored else failure_cycle)
    cycles = np.asarray(cycles, dtype=int).reshape(-1)
    order = np.argsort(cycles)
    cycles = cycles[order]
    damage_by_cycle = np.asarray(damage_by_cycle, dtype=float)[order]
    history_by_cycle = np.asarray(history_by_cycle, dtype=float)[order]
    fatigue_f_by_cycle = np.asarray(fatigue_f_by_cycle, dtype=float)[order]
    psi_raw_by_cycle = np.asarray(psi_raw_by_cycle, dtype=float)[order]
    centroids = np.asarray(centroids, dtype=float)
    areas = np.asarray(areas, dtype=float).reshape(-1)
    n_elem = centroids.shape[0]
    for name, values in {
        "damage": damage_by_cycle,
        "alpha_bar": history_by_cycle,
        "fatigue_f": fatigue_f_by_cycle,
        "psi_raw": psi_raw_by_cycle,
    }.items():
        if values.shape != (len(cycles), n_elem):
            raise ValueError(
                f"{name} has shape {values.shape}; expected {(len(cycles), n_elem)}"
            )
    if areas.shape[0] != n_elem:
        raise ValueError(f"area count {areas.shape[0]} does not match {n_elem} elements")

    y = centroids[:, 1]
    rows: list[dict[str, float | str]] = []
    prev_damage = None
    prev_history = None
    prev_cycle = None
    for k, cycle in enumerate(cycles):
        if cycle > terminal_cycle:
            continue
        damage = damage_by_cycle[k]
        history = history_by_cycle[k]
        base = feature_row(
            int(cycle),
            terminal_cycle,
            centroids,
            areas,
            damage,
            history,
            fatigue_f_by_cycle[k],
            psi_raw_by_cycle[k],
            l0=l0,
            crack_strip_y=crack_strip_y,
            boundary_x=boundary_x,
        )
        dc = 1.0 if prev_cycle is None else max(1.0, float(cycle - prev_cycle))
        if prev_damage is None:
            damage_activity = 0.0
            history_activity = 0.0
        else:
            damage_activity = weighted_mean(np.maximum(damage - prev_damage, 0.0), areas) / dc
            history_activity = weighted_mean(np.maximum(history - prev_history, 0.0), areas) / dc
        rows.append(
            {
                "trajectory_id": trajectory_id,
                "cycle": float(cycle),
                "failure_cycle": float("nan") if censored else float(failure_cycle),
                "censored": float(censored),
                "censor_cycle": float(censor_cycle) if censored else float("nan"),
                "remaining_life": (
                    float("nan") if censored else float(max(0, int(failure_cycle) - int(cycle)))
                ),
                "remaining_life_lower_bound": float(max(0, terminal_cycle - int(cycle))),
                "umax": float(umax),
                "crack_tip_x_d09": float(base["crack_tip_x_d09"]),
                "damage_area_gt_0p5": float(base["damage_area_gt_0p5"]),
                "damage_area_gt_0p9": float(base["damage_area_gt_0p9"]),
                "visible_crack_width_y": _visible_width(damage, y),
                "mechanical_energy_tip_proxy": float(base["psi_raw_tip_2l0_mean"]),
                "mechanical_energy_strip_proxy": float(base["psi_raw_crack_strip_mean"]),
                "ae_damage_activity_proxy": float(np.log1p(max(damage_activity, 0.0))),
                "ae_history_activity_proxy": float(np.log1p(max(history_activity, 0.0))),
                "alpha_bar_p99": float(base["alpha_bar_p99"]),
                "fatigue_f_tip_2l0_mean": float(base["fatigue_f_tip_2l0_mean"]),
                "psi_active_tip_2l0_mean": float(base["psi_active_tip_2l0_mean"]),
            }
        )
        prev_damage = damage.copy()
        prev_history = history.copy()
        prev_cycle = int(cycle)
    if len(rows) < 3:
        raise ValueError(f"Need at least three states in {source_path}, got {len(rows)}")
    return Trajectory(
        trajectory_id,
        source_path,
        None if censored else int(failure_cycle),
        float(umax),
        pd.DataFrame(rows),
        censored=censored,
        censor_cycle=int(censor_cycle) if censored else None,
        parameters={} if parameters is None else parameters,
        physics_family=physics_family,
    )


def trajectory_from_handoff(
    path: Path,
    *,
    trajectory_id: str,
    umax: float,
    failure_cycle: int | None = None,
    censored: bool = False,
    censor_cycle: int | None = None,
    parameters: Mapping[str, float] | None = None,
    physics_family: str = "unspecified",
    l0: float = 0.01,
    crack_strip_y: float = 0.05,
    boundary_x: float = 0.45,
) -> Trajectory:
    """Convert a cycle-resolved FEM handoff into reality-facing observations."""
    fem = load_fem_handoff(path)
    cycles = fem["cycles"].astype(int)
    if censored:
        censor = int(cycles.max()) if censor_cycle is None else int(censor_cycle)
        nf = None
    else:
        nf = int(cycles.max()) if failure_cycle is None else int(failure_cycle)
        censor = None
    return _trajectory_from_arrays(
        source_path=path,
        cycles=cycles,
        centroids=fem["centroids"],
        areas=fem["areas"],
        damage_by_cycle=fem["damage"],
        history_by_cycle=fem["alpha_bar"],
        fatigue_f_by_cycle=fem["fatigue_f"],
        psi_raw_by_cycle=fem["psi_raw"],
        trajectory_id=trajectory_id,
        umax=umax,
        failure_cycle=nf,
        censored=censored,
        censor_cycle=censor,
        parameters=parameters,
        physics_family=physics_family,
        l0=l0,
        crack_strip_y=crack_strip_y,
        boundary_x=boundary_x,
    )


def trajectory_from_keyframes(
    keyframe_paths: Sequence[Path],
    *,
    mesh_path: Path,
    trajectory_id: str,
    umax: float,
    failure_cycle: int | None,
    censored: bool = False,
    censor_cycle: int | None = None,
    parameters: Mapping[str, float] | None = None,
    physics_family: str = "unspecified",
    l0: float = 0.01,
    crack_strip_y: float = 0.05,
    boundary_x: float = 0.45,
) -> Trajectory:
    """Load sparse FEM keyframes that share one declared mesh.

    This is the field-inspection analogue: latent FEM state may exist only at a
    few registered inspections.  Activity features are divided by the actual
    gap between keyframes and must be interpreted as interval averages.
    """
    if len(keyframe_paths) < 3:
        raise ValueError("Need at least three keyframes for a sparse trajectory")
    if censored and censor_cycle is None:
        raise ValueError("Sparse censored trajectory needs censor_cycle")
    if not censored and failure_cycle is None:
        raise ValueError("Sparse uncensored trajectory needs failure_cycle")
    mesh = loadmat(mesh_path)
    if "element_centroids" not in mesh or "connectivity" not in mesh or "node_coords" not in mesh:
        raise KeyError(f"Mesh {mesh_path} lacks geometry required for spatial observations")
    centroids = orient_points(np.asarray(mesh["element_centroids"], dtype=float), 2)
    nodes = orient_points(np.asarray(mesh["node_coords"], dtype=float), 2)
    conn = orient_conn(np.asarray(mesh["connectivity"], dtype=int))
    if np.nanmin(centroids[:, 0]) >= -1e-9 and np.nanmax(centroids[:, 0]) > 0.9:
        centroids = centroids.copy()
        centroids[:, :2] -= 0.5
        nodes = nodes.copy()
        nodes[:, :2] -= 0.5
    if "area_per_elem" in mesh:
        areas = np.asarray(mesh["area_per_elem"], dtype=float).reshape(-1)
    elif "element_area" in mesh:
        areas = np.asarray(mesh["element_area"], dtype=float).reshape(-1)
    else:
        areas = polygon_areas(nodes, conn)

    aliases = {
        "damage": ("d_elem", "alpha_elem"),
        "history": ("alpha_bar_elem",),
        "fatigue_f": ("f_alpha_elem", "f_fatigue_elem"),
        "psi_raw": ("psi_elem", "psi_plus_elem"),
    }
    cycles: list[int] = []
    fields = {name: [] for name in aliases}
    for path in keyframe_paths:
        payload = loadmat(path)
        if "cycle" in payload:
            cycle = int(np.asarray(payload["cycle"]).reshape(-1)[0])
        else:
            match = re.search(r"cycle_(\d+)", path.stem)
            if not match:
                raise ValueError(f"Cannot infer cycle from {path}")
            cycle = int(match.group(1))
        cycles.append(cycle)
        for out_name, candidates in aliases.items():
            found = next((name for name in candidates if name in payload), None)
            if found is None:
                raise KeyError(f"Keyframe {path} lacks {out_name}; tried {candidates}")
            fields[out_name].append(np.asarray(payload[found], dtype=float).reshape(-1))
    return _trajectory_from_arrays(
        source_path=Path(keyframe_paths[0]).parent,
        cycles=np.asarray(cycles, dtype=int),
        centroids=centroids,
        areas=areas,
        damage_by_cycle=np.vstack(fields["damage"]),
        history_by_cycle=np.vstack(fields["history"]),
        fatigue_f_by_cycle=np.vstack(fields["fatigue_f"]),
        psi_raw_by_cycle=np.vstack(fields["psi_raw"]),
        trajectory_id=trajectory_id,
        umax=umax,
        failure_cycle=failure_cycle,
        censored=censored,
        censor_cycle=censor_cycle,
        parameters=parameters,
        physics_family=physics_family,
        l0=l0,
        crack_strip_y=crack_strip_y,
        boundary_x=boundary_x,
    )


def trajectory_from_observation_csv(
    path: Path,
    *,
    trajectory_id: str,
    umax: float,
    failure_cycle: int | None,
    censored: bool = False,
    censor_cycle: int | None = None,
    parameters: Mapping[str, float] | None = None,
    physics_family: str = "field_observation_v1",
    observation_tier: str = "vision_only",
) -> Trajectory:
    """Load a completed laboratory/field history as an empirical trajectory."""
    observations = validate_observation_table(pd.read_csv(path), observation_tier)
    terminal_cycle = int(censor_cycle if censored else failure_cycle)
    if not np.isclose(float(observations["cycle"].iloc[-1]), float(terminal_cycle)):
        raise ValueError(
            f"Observation trajectory {trajectory_id} must include its declared terminal cycle "
            f"{terminal_cycle}, got {observations['cycle'].iloc[-1]}"
        )
    rows = observations.copy()
    rows["trajectory_id"] = trajectory_id
    rows["failure_cycle"] = float("nan") if censored else float(failure_cycle)
    rows["censored"] = float(censored)
    rows["censor_cycle"] = float(censor_cycle) if censored else float("nan")
    rows["remaining_life"] = (
        np.nan if censored else float(failure_cycle) - rows["cycle"].to_numpy(float)
    )
    rows["remaining_life_lower_bound"] = np.maximum(
        0.0, float(terminal_cycle) - rows["cycle"].to_numpy(float)
    )
    rows["umax"] = float(umax)
    return Trajectory(
        trajectory_id=trajectory_id,
        source_path=path,
        failure_cycle=None if censored else int(failure_cycle),
        umax=float(umax),
        rows=rows,
        censored=censored,
        censor_cycle=int(censor_cycle) if censored else None,
        parameters={} if parameters is None else parameters,
        physics_family=physics_family,
    )


def _manifest_path(value: object, manifest_dir: Path) -> Path:
    text = os.path.expandvars(os.path.expanduser(str(value)))
    path = Path(text)
    return path if path.is_absolute() else manifest_dir / path


def trajectories_from_manifest(manifest_path: Path) -> list[Trajectory]:
    """Load a mixed combined-handoff/sparse-keyframe trajectory library."""
    manifest = pd.read_csv(manifest_path)
    required = {
        "trajectory_id",
        "source_kind",
        "source_path",
        "umax",
        "failure_cycle",
        "censored",
        "censor_cycle",
        "physics_family",
    }
    missing = sorted(required - set(manifest.columns))
    if missing:
        raise ValueError(f"Trajectory manifest is missing columns: {missing}")
    if manifest["trajectory_id"].duplicated().any():
        raise ValueError("trajectory_id must be unique in a trajectory manifest")
    out: list[Trajectory] = []
    for _, row in manifest.iterrows():
        censored = str(row["censored"]).strip().lower() in {"1", "true", "yes"}
        source_kind = str(row["source_kind"]).strip()
        source_path = _manifest_path(row["source_path"], manifest_path.parent)
        if censored:
            if pd.isna(row["censor_cycle"]):
                raise ValueError(f"Censored trajectory {row['trajectory_id']} lacks censor_cycle")
            failure_cycle = None
            censor_cycle = int(row["censor_cycle"])
        else:
            if pd.isna(row["failure_cycle"]):
                raise ValueError(f"Uncensored trajectory {row['trajectory_id']} lacks failure_cycle")
            failure_cycle = int(row["failure_cycle"])
            censor_cycle = None
        common = {
            "trajectory_id": str(row["trajectory_id"]),
            "umax": float(row["umax"]),
            "failure_cycle": failure_cycle,
            "censored": censored,
            "censor_cycle": censor_cycle,
            "parameters": {
                column.removeprefix("parameter_"): float(row[column])
                for column in manifest.columns
                if column.startswith("parameter_") and not pd.isna(row[column])
            },
            "physics_family": str(row["physics_family"]).strip(),
        }
        if source_kind == "combined_handoff":
            out.append(trajectory_from_handoff(source_path, **common))
        elif source_kind == "keyframes":
            if "mesh_path" not in row or pd.isna(row["mesh_path"]):
                raise ValueError(f"Keyframe trajectory {row['trajectory_id']} lacks mesh_path")
            pattern = str(source_path)
            keyframes = [Path(path) for path in sorted(glob.glob(pattern))]
            if len(keyframes) < 3:
                raise ValueError(f"Keyframe pattern {pattern} matched only {len(keyframes)} files")
            out.append(
                trajectory_from_keyframes(
                    keyframes,
                    mesh_path=_manifest_path(row["mesh_path"], manifest_path.parent),
                    **common,
                )
            )
        elif source_kind == "observation_csv":
            if "observation_tier" not in row or pd.isna(row["observation_tier"]):
                raise ValueError(
                    f"Observation trajectory {row['trajectory_id']} lacks observation_tier"
                )
            out.append(
                trajectory_from_observation_csv(
                    source_path,
                    observation_tier=str(row["observation_tier"]),
                    **common,
                )
            )
        else:
            raise ValueError(f"Unknown source_kind {source_kind!r} for {row['trajectory_id']}")
    return out


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    values = np.asarray(values, dtype=float)[order]
    weights = np.asarray(weights, dtype=float)[order]
    total = float(np.sum(weights))
    if total <= 0.0:
        return float("nan")
    cdf = np.cumsum(weights) / total
    return float(values[min(int(np.searchsorted(cdf, q, side="left")), len(values) - 1)])


def empirical_crps(values: np.ndarray, weights: np.ndarray, truth: float) -> float:
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    weights = weights / np.sum(weights)
    first = float(np.sum(weights * np.abs(values - truth)))
    pair = np.abs(values[:, None] - values[None, :])
    second = 0.5 * float(np.sum(weights[:, None] * weights[None, :] * pair))
    return first - second


def _robust_scales(library: Sequence[Trajectory], feature_names: Sequence[str]) -> dict[str, float]:
    combined = pd.concat([t.rows[list(feature_names)] for t in library], ignore_index=True)
    scales: dict[str, float] = {}
    for name in feature_names:
        values = combined[name].to_numpy(dtype=float)
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            scales[name] = 1.0
            continue
        q25, q75 = np.quantile(finite, [0.25, 0.75])
        scale = float(q75 - q25)
        if scale < 1e-12:
            scale = float(np.std(finite))
        if scale < 1e-12:
            scale = max(float(np.max(np.abs(finite))), 1.0)
        scales[name] = scale
    return scales


class SequentialLibraryAssimilator:
    """Sequential Bayesian model averaging over complete FEM trajectories."""

    def __init__(
        self,
        library: Sequence[Trajectory],
        feature_names: Sequence[str],
        *,
        likelihood_sigma: float = 0.5,
        min_probability: float = 1e-12,
        censor_tail_scale: float = 50.0,
        censor_quadrature_points: int = 11,
        feature_noise: Mapping[str, float] | None = None,
    ) -> None:
        if len(library) < 2:
            raise ValueError("Sequential assimilation needs at least two candidate trajectories")
        if likelihood_sigma <= 0.0:
            raise ValueError("likelihood_sigma must be positive")
        if censor_tail_scale <= 0.0:
            raise ValueError("censor_tail_scale must be positive")
        if censor_quadrature_points < 3:
            raise ValueError("censor_quadrature_points must be at least 3")
        self.library = list(library)
        self.feature_names = tuple(feature_names)
        self.likelihood_sigma = float(likelihood_sigma)
        self.min_probability = float(min_probability)
        self.censor_tail_scale = float(censor_tail_scale)
        self.censor_quadrature_points = int(censor_quadrature_points)
        self.feature_noise = {
            name: float((feature_noise or {}).get(name, 0.0)) for name in self.feature_names
        }
        if any(value < 0.0 for value in self.feature_noise.values()):
            raise ValueError("feature_noise values must be non-negative")
        self.scales = _robust_scales(self.library, self.feature_names)
        self.log_weights = np.full(len(self.library), -np.log(len(self.library)), dtype=float)

    @property
    def weights(self) -> np.ndarray:
        shifted = self.log_weights - np.max(self.log_weights)
        weights = np.exp(shifted)
        return weights / np.sum(weights)

    def posterior_parameters(self) -> dict[str, dict[str, float]]:
        """Return marginal posterior summaries for declared FEM/model parameters."""
        weights = self.weights
        names = sorted({name for trajectory in self.library for name in trajectory.inference_parameters})
        output: dict[str, dict[str, float]] = {}
        for name in names:
            values = np.asarray(
                [trajectory.inference_parameters.get(name, np.nan) for trajectory in self.library],
                dtype=float,
            )
            valid = np.isfinite(values)
            if not np.any(valid):
                continue
            local_weights = weights[valid]
            local_weights /= np.sum(local_weights)
            local_values = values[valid]
            output[name] = {
                "mean": float(np.sum(local_weights * local_values)),
                "q05": weighted_quantile(local_values, local_weights, 0.05),
                "q50": weighted_quantile(local_values, local_weights, 0.50),
                "q95": weighted_quantile(local_values, local_weights, 0.95),
                "support_models": float(np.count_nonzero(valid)),
            }
        return output

    def update(self, cycle: float, observation: Mapping[str, float]) -> np.ndarray:
        log_like = np.zeros(len(self.library), dtype=float)
        used = np.zeros(len(self.library), dtype=int)
        for j, candidate in enumerate(self.library):
            row = candidate.row_at(cycle)
            for name in self.feature_names:
                observed = float(observation.get(name, np.nan))
                predicted = float(row.get(name, np.nan))
                if not (np.isfinite(observed) and np.isfinite(predicted)):
                    continue
                denominator = np.sqrt(
                    (self.likelihood_sigma * self.scales[name]) ** 2
                    + self.feature_noise[name] ** 2
                )
                z = (observed - predicted) / denominator
                log_like[j] += -0.5 * z**2
                used[j] += 1
        log_like = np.where(used > 0, log_like, np.log(self.min_probability))
        self.log_weights += log_like
        self.log_weights -= np.max(self.log_weights)
        self.log_weights = np.maximum(self.log_weights, np.log(self.min_probability))
        return self.weights.copy()

    def posterior_prediction(self, cycle: float, horizon: int) -> dict[str, float]:
        weights = self.weights
        rul_support: list[float] = []
        rul_weights: list[float] = []
        censored_mass = 0.0
        for trajectory, model_weight in zip(self.library, weights):
            current_cycle = float(trajectory.row_at(cycle)["cycle"])
            if trajectory.censored:
                lower_bound = max(0.0, float(trajectory.censor_cycle) - current_cycle)
                q = (np.arange(self.censor_quadrature_points, dtype=float) + 0.5) / self.censor_quadrature_points
                tail = -self.censor_tail_scale * np.log1p(-q)
                rul_support.extend((lower_bound + tail).tolist())
                rul_weights.extend(
                    np.full(self.censor_quadrature_points, model_weight / self.censor_quadrature_points).tolist()
                )
                censored_mass += float(model_weight)
            else:
                rul_support.append(max(0.0, float(trajectory.failure_cycle) - current_cycle))
                rul_weights.append(float(model_weight))
        rul = np.asarray(rul_support, dtype=float)
        rul_support_weights = np.asarray(rul_weights, dtype=float)
        rul_support_weights /= np.sum(rul_support_weights)
        future_tip = np.array(
            [float(t.future_row(cycle, horizon)["crack_tip_x_d09"]) for t in self.library],
            dtype=float,
        )
        entropy = -float(np.sum(weights * np.log(np.maximum(weights, 1e-300))))
        return {
            "rul_mean": float(np.sum(rul_support_weights * rul)),
            "rul_q05": weighted_quantile(rul, rul_support_weights, 0.05),
            "rul_q50": weighted_quantile(rul, rul_support_weights, 0.50),
            "rul_q95": weighted_quantile(rul, rul_support_weights, 0.95),
            "future_tip_mean": float(np.sum(weights * future_tip)),
            "future_tip_q05": weighted_quantile(future_tip, weights, 0.05),
            "future_tip_q95": weighted_quantile(future_tip, weights, 0.95),
            "posterior_entropy": entropy,
            "effective_models": float(np.exp(entropy)),
            "rul_crps_support": rul,
            "rul_crps_weights": rul_support_weights,
            "censored_posterior_mass": censored_mass,
            "censor_tail_scale": self.censor_tail_scale,
        }


def assimilate_holdout(
    holdout: Trajectory,
    library: Sequence[Trajectory],
    *,
    feature_names: Sequence[str],
    tier: str,
    inspection_stride: int = 5,
    forecast_horizon: int = 5,
    likelihood_sigma: float = 0.5,
    censor_tail_scale: float = 50.0,
    censor_quadrature_points: int = 11,
    feature_noise: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    if holdout.censored:
        raise ValueError("A censored holdout has no exact RUL truth; use it in the candidate library only")
    assimilator = SequentialLibraryAssimilator(
        library,
        feature_names,
        likelihood_sigma=likelihood_sigma,
        censor_tail_scale=censor_tail_scale,
        censor_quadrature_points=censor_quadrature_points,
        feature_noise=feature_noise,
    )
    source_rows = holdout.rows.iloc[:: max(1, int(inspection_stride))].copy()
    if source_rows.index[-1] != holdout.rows.index[-1]:
        source_rows = pd.concat([source_rows, holdout.rows.iloc[[-1]]])
    output: list[dict[str, float | str]] = []
    for _, row in source_rows.iterrows():
        cycle = float(row["cycle"])
        observation = {name: float(row.get(name, np.nan)) for name in feature_names}
        weights = assimilator.update(cycle, observation)
        pred = assimilator.posterior_prediction(cycle, forecast_horizon)
        parameter_posterior = assimilator.posterior_parameters()
        true_rul = float(row["remaining_life"])
        true_future_tip = float(holdout.future_row(cycle, forecast_horizon)["crack_tip_x_d09"])
        result: dict[str, float | str] = {
            "tier": tier,
            "heldout_trajectory": holdout.trajectory_id,
            "cycle": cycle,
            "true_rul": true_rul,
            "rul_mean": pred["rul_mean"],
            "rul_q05": pred["rul_q05"],
            "rul_q50": pred["rul_q50"],
            "rul_q95": pred["rul_q95"],
            "rul_crps": empirical_crps(
                np.asarray(pred["rul_crps_support"], dtype=float),
                np.asarray(pred["rul_crps_weights"], dtype=float),
                true_rul,
            ),
            "rul_interval_covers": float(pred["rul_q05"] <= true_rul <= pred["rul_q95"]),
            "true_future_tip": true_future_tip,
            "future_tip_mean": pred["future_tip_mean"],
            "future_tip_q05": pred["future_tip_q05"],
            "future_tip_q95": pred["future_tip_q95"],
            "posterior_entropy": pred["posterior_entropy"],
            "effective_models": pred["effective_models"],
            "max_model_weight": float(np.max(weights)),
            "censored_posterior_mass": pred["censored_posterior_mass"],
            "censor_tail_scale": pred["censor_tail_scale"],
        }
        for name, posterior in parameter_posterior.items():
            truth = holdout.inference_parameters.get(name, np.nan)
            result[f"parameter__{name}__true"] = float(truth)
            for statistic, value in posterior.items():
                result[f"parameter__{name}__{statistic}"] = float(value)
        output.append(result)
    return pd.DataFrame(output)


def summarize_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for (tier, heldout), df in predictions.groupby(["tier", "heldout_trajectory"], sort=False):
        rul_err = df["rul_mean"].to_numpy(float) - df["true_rul"].to_numpy(float)
        tip_err = df["future_tip_mean"].to_numpy(float) - df["true_future_tip"].to_numpy(float)
        rows.append(
            {
                "tier": tier,
                "heldout_trajectory": heldout,
                "n_updates": float(len(df)),
                "rul_mae": float(np.mean(np.abs(rul_err))),
                "rul_rmse": float(np.sqrt(np.mean(rul_err**2))),
                "rul_crps": float(df["rul_crps"].mean()),
                "rul_90_coverage": float(df["rul_interval_covers"].mean()),
                "rul_90_width": float((df["rul_q95"] - df["rul_q05"]).mean()),
                "future_tip_mae": float(np.mean(np.abs(tip_err))),
                "final_effective_models": float(df["effective_models"].iloc[-1]),
                "final_max_model_weight": float(df["max_model_weight"].iloc[-1]),
                "mean_censored_posterior_mass": float(df["censored_posterior_mass"].mean()),
                "final_censored_posterior_mass": float(df["censored_posterior_mass"].iloc[-1]),
            }
        )
    summary = pd.DataFrame(rows)
    aggregate: list[dict[str, float | str]] = []
    for tier, df in predictions.groupby("tier", sort=False):
        rul_err = df["rul_mean"].to_numpy(float) - df["true_rul"].to_numpy(float)
        tip_err = df["future_tip_mean"].to_numpy(float) - df["true_future_tip"].to_numpy(float)
        aggregate.append(
            {
                "tier": tier,
                "heldout_trajectory": "ALL",
                "n_updates": float(len(df)),
                "rul_mae": float(np.mean(np.abs(rul_err))),
                "rul_rmse": float(np.sqrt(np.mean(rul_err**2))),
                "rul_crps": float(df["rul_crps"].mean()),
                "rul_90_coverage": float(df["rul_interval_covers"].mean()),
                "rul_90_width": float((df["rul_q95"] - df["rul_q05"]).mean()),
                "future_tip_mae": float(np.mean(np.abs(tip_err))),
                "final_effective_models": float("nan"),
                "final_max_model_weight": float("nan"),
                "mean_censored_posterior_mass": float(df["censored_posterior_mass"].mean()),
                "final_censored_posterior_mass": float("nan"),
            }
        )
    return pd.concat([summary, pd.DataFrame(aggregate)], ignore_index=True)


def summarize_parameter_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """Summarize inverse-parameter recovery without mixing parameter units."""
    parameter_names = sorted(
        column.removeprefix("parameter__").removesuffix("__true")
        for column in predictions.columns
        if column.startswith("parameter__") and column.endswith("__true")
    )
    rows: list[dict[str, float | str]] = []
    for tier, tier_frame in predictions.groupby("tier", sort=False):
        for name in parameter_names:
            truth_column = f"parameter__{name}__true"
            mean_column = f"parameter__{name}__mean"
            q05_column = f"parameter__{name}__q05"
            q95_column = f"parameter__{name}__q95"
            available = tier_frame[[truth_column, mean_column, q05_column, q95_column]].dropna()
            if available.empty:
                continue
            error = available[mean_column].to_numpy(float) - available[truth_column].to_numpy(float)
            truth_values = available[truth_column].to_numpy(float)
            truth_range = float(np.max(truth_values) - np.min(truth_values))
            identifiable = bool(np.unique(truth_values).size >= 2 and truth_range > 1e-12)
            rows.append(
                {
                    "tier": tier,
                    "parameter": name,
                    "n_updates": float(len(available)),
                    "n_unique_truth": float(np.unique(truth_values).size),
                    "truth_range": truth_range,
                    "identifiable_from_holdout": identifiable,
                    "mae": float(np.mean(np.abs(error))) if identifiable else float("nan"),
                    "rmse": float(np.sqrt(np.mean(error**2))) if identifiable else float("nan"),
                    "90_coverage": (
                        float(
                            np.mean(
                                (available[q05_column] <= available[truth_column])
                                & (available[truth_column] <= available[q95_column])
                            )
                        )
                        if identifiable
                        else float("nan")
                    ),
                    "90_width": (
                        float((available[q95_column] - available[q05_column]).mean())
                        if identifiable
                        else float("nan")
                    ),
                }
            )
    return pd.DataFrame(rows)


def run_leave_one_trajectory_out(
    trajectories: Sequence[Trajectory],
    *,
    tiers: Iterable[str] = OBSERVATION_TIERS,
    inspection_stride: int = 5,
    forecast_horizon: int = 5,
    likelihood_sigma: float = 0.5,
    censor_tail_scale: float = 50.0,
    censor_quadrature_points: int = 11,
    sensor_model: SensorObservationModel | None = None,
    sensor_noise_multiplier: float = 0.0,
    sensor_missing_probability: float = 0.0,
    random_seed: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(trajectories) < 3:
        raise ValueError("Leave-one-trajectory-out assimilation needs at least three trajectories")
    tiers = tuple(tiers)
    if sensor_model is None:
        sensor_model = DEFAULT_SYNTHETIC_SENSOR_MODEL
    requested_features = {
        name
        for tier in tiers
        for name in OBSERVATION_TIERS.get(tier, ())
    }
    needs_sensor_projection = bool(requested_features & set(sensor_model.output_features))
    if needs_sensor_projection:
        projected_library = {
            trajectory.trajectory_id: project_trajectory_to_sensor_space(trajectory, sensor_model)
            for trajectory in trajectories
        }
        observed_holdouts = {
            trajectory.trajectory_id: simulate_sensor_observations(
                trajectory,
                sensor_model,
                noise_multiplier=sensor_noise_multiplier,
                missing_probability=sensor_missing_probability,
                random_seed=int(random_seed) + index,
            )
            for index, trajectory in enumerate(trajectories)
        }
        feature_noise = {
            name: sigma * float(sensor_noise_multiplier)
            for name, sigma in sensor_model.noise_scales.items()
        }
    else:
        projected_library = {trajectory.trajectory_id: trajectory for trajectory in trajectories}
        observed_holdouts = {trajectory.trajectory_id: trajectory for trajectory in trajectories}
        feature_noise = {}
    unavailable = []
    for tier in tiers:
        if tier not in OBSERVATION_TIERS:
            continue
        for trajectory in projected_library.values():
            missing = [name for name in OBSERVATION_TIERS[tier] if name not in trajectory.rows]
            if missing:
                unavailable.append(f"{trajectory.trajectory_id}/{tier}: {missing}")
    if unavailable:
        raise ValueError(
            "Selected observation tiers are unavailable in the trajectory library; "
            "choose compatible --tiers or provide a calibrated observation model: "
            + "; ".join(unavailable)
        )
    frames: list[pd.DataFrame] = []
    for tier in tiers:
        if tier not in OBSERVATION_TIERS:
            raise KeyError(f"Unknown observation tier {tier}")
        features = OBSERVATION_TIERS[tier]
        for original in (trajectory for trajectory in trajectories if not trajectory.censored):
            holdout = observed_holdouts[original.trajectory_id]
            library = [
                projected_library[t.trajectory_id]
                for t in trajectories
                if t.trajectory_id != original.trajectory_id
            ]
            frames.append(
                assimilate_holdout(
                    holdout,
                    library,
                    feature_names=features,
                    tier=tier,
                    inspection_stride=inspection_stride,
                    forecast_horizon=forecast_horizon,
                    likelihood_sigma=likelihood_sigma,
                    censor_tail_scale=censor_tail_scale,
                    censor_quadrature_points=censor_quadrature_points,
                    feature_noise=feature_noise,
                )
            )
    predictions = pd.concat(frames, ignore_index=True)
    return predictions, summarize_predictions(predictions)


def feature_catalog_frame() -> pd.DataFrame:
    tier_membership = {
        spec.name: ",".join(tier for tier, names in OBSERVATION_TIERS.items() if spec.name in names)
        for spec in FEATURE_CATALOG
    }
    return pd.DataFrame(
        [
            {
                "feature": spec.name,
                "channel": spec.channel,
                "status": spec.status,
                "physical_meaning": spec.physical_meaning,
                "deployment_source": spec.deployment_source,
                "tiers": tier_membership[spec.name],
            }
            for spec in FEATURE_CATALOG
        ]
    )


REQUIRED_OBSERVATION_METADATA = (
    "observation_space_version",
    "asset_id",
    "inspection_id",
    "timestamp",
    "cycle",
    "coordinate_frame",
    "registration_id",
)


def validate_observation_table(observations: pd.DataFrame, tier: str) -> pd.DataFrame:
    """Validate calibrated observations before they enter sequential inference.

    The table is already expected to be in the model observation space.  Raw
    pixels, DIC images, AE waveforms, or traffic records need a separately
    versioned observation model before this function is called.
    """
    if tier not in OBSERVATION_TIERS:
        raise KeyError(f"Unknown observation tier {tier}")
    required = set(REQUIRED_OBSERVATION_METADATA) | set(OBSERVATION_TIERS[tier])
    missing = sorted(required - set(observations.columns))
    if missing:
        raise ValueError(f"Observation table is missing columns: {missing}")
    if len(observations) < 2:
        raise ValueError("Sequential inference needs at least two registered inspections")
    out = observations.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="raise")
    if out["asset_id"].nunique() != 1:
        raise ValueError("One inference table must contain exactly one asset_id")
    if out["inspection_id"].duplicated().any():
        raise ValueError("inspection_id must be unique within an asset sequence")
    if out["coordinate_frame"].nunique() != 1 or out["registration_id"].nunique() != 1:
        raise ValueError("All inspections must share one coordinate frame and registration chain")
    versions = set(out["observation_space_version"].astype(str))
    if versions != {"reality_obs_v1"}:
        raise ValueError(f"Unsupported observation-space version(s): {sorted(versions)}")
    out = out.sort_values(["timestamp", "cycle"]).reset_index(drop=True)
    if np.any(np.diff(out["cycle"].to_numpy(dtype=float)) <= 0.0):
        raise ValueError("cycle/equivalent-load index must be strictly increasing")
    for name in OBSERVATION_TIERS[tier]:
        values = pd.to_numeric(out[name], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(values).any():
            raise ValueError(f"Feature {name} has no finite observation")
        out[name] = values
    if "maintenance_event" in out.columns:
        maintenance = out["maintenance_event"].astype(str).str.lower().isin({"1", "true", "yes"})
        if maintenance.any():
            raise NotImplementedError(
                "Maintenance/state-reset assimilation is not implemented; split the sequence at the event"
            )
    return out


def assimilate_observation_sequence(
    observations: pd.DataFrame,
    library: Sequence[Trajectory],
    *,
    tier: str,
    forecast_horizon: int = 5,
    likelihood_sigma: float = 0.5,
    censor_tail_scale: float = 50.0,
    censor_quadrature_points: int = 11,
    feature_noise: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Infer posterior forecasts for a calibrated real or laboratory sequence."""
    observations = validate_observation_table(observations, tier)
    features = OBSERVATION_TIERS[tier]
    assimilator = SequentialLibraryAssimilator(
        library,
        features,
        likelihood_sigma=likelihood_sigma,
        censor_tail_scale=censor_tail_scale,
        censor_quadrature_points=censor_quadrature_points,
        feature_noise=feature_noise,
    )
    output: list[dict[str, float | str]] = []
    for _, row in observations.iterrows():
        cycle = float(row["cycle"])
        weights = assimilator.update(cycle, {name: float(row[name]) for name in features})
        pred = assimilator.posterior_prediction(cycle, forecast_horizon)
        parameter_posterior = assimilator.posterior_parameters()
        result: dict[str, float | str] = {
            "observation_space_version": str(row["observation_space_version"]),
            "asset_id": str(row["asset_id"]),
            "inspection_id": str(row["inspection_id"]),
            "timestamp": row["timestamp"].isoformat(),
            "cycle": cycle,
            "tier": tier,
            "rul_mean": pred["rul_mean"],
            "rul_q05": pred["rul_q05"],
            "rul_q50": pred["rul_q50"],
            "rul_q95": pred["rul_q95"],
            "future_tip_mean": pred["future_tip_mean"],
            "future_tip_q05": pred["future_tip_q05"],
            "future_tip_q95": pred["future_tip_q95"],
            "posterior_entropy": pred["posterior_entropy"],
            "effective_models": pred["effective_models"],
            "max_model_weight": float(np.max(weights)),
            "censored_posterior_mass": pred["censored_posterior_mass"],
            "censor_tail_scale": pred["censor_tail_scale"],
        }
        for candidate, weight in zip(library, weights):
            result[f"model_weight__{candidate.trajectory_id}"] = float(weight)
        for name, posterior in parameter_posterior.items():
            for statistic, value in posterior.items():
                result[f"parameter__{name}__{statistic}"] = float(value)
        output.append(result)
    return pd.DataFrame(output)
