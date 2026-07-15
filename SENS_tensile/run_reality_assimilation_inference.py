#!/usr/bin/env python3
"""Assimilate a calibrated laboratory/field observation sequence.

Raw images, DIC frames, AE waveforms, and traffic records must first be mapped
to the versioned `reality_obs_v1` observation table.  This command performs no
training; it updates a direct-FEM trajectory-library posterior and writes the
forecast after every inspection.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from reality_assimilation import (
    OBSERVATION_TIERS,
    SensorObservationModel,
    assimilate_observation_sequence,
    project_trajectory_to_sensor_space,
    trajectory_from_handoff,
    trajectories_from_manifest,
    validate_physics_library,
    validate_sensor_model_for_inference,
)
from run_m2s_next_stage_feasibility import DEFAULT_FIELD_ROOT, discover_field_handoffs
from run_reality_assimilation_benchmark import infer_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations-csv", required=True, type=Path)
    parser.add_argument("--tier", required=True, choices=list(OBSERVATION_TIERS))
    parser.add_argument("--field-root", type=Path, default=DEFAULT_FIELD_ROOT)
    parser.add_argument(
        "--trajectory-manifest",
        type=Path,
        default=None,
        help="Mixed combined/keyframe library, including optional right-censored trajectories.",
    )
    parser.add_argument("--umax", type=float, default=0.12)
    parser.add_argument("--forecast-horizon", type=int, default=5)
    parser.add_argument("--likelihood-sigma", type=float, default=0.5)
    parser.add_argument("--censor-tail-scale", type=float, default=50.0)
    parser.add_argument("--censor-quadrature-points", type=int, default=11)
    parser.add_argument(
        "--sensor-model-json",
        type=Path,
        default=None,
        help="Required for DIC/AE tiers; must be lab- or field-calibrated.",
    )
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    if args.trajectory_manifest is not None:
        library = trajectories_from_manifest(args.trajectory_manifest)
        field_paths = [trajectory.source_path for trajectory in library]
    else:
        field_paths = discover_field_handoffs(args.field_root)
        if len(field_paths) < 2:
            raise RuntimeError(f"Need at least two FEM library trajectories in {args.field_root}")
        library = [
            trajectory_from_handoff(
                path,
                trajectory_id=infer_id(path),
                umax=args.umax,
                physics_family="strict_reverseBC_softHist0",
            )
            for path in field_paths
        ]
    try:
        physics_families = list(validate_physics_library(library))
    except ValueError as error:
        raise RuntimeError(f"Real inference requires one compatible physics_family: {error}") from error
    if len(library) < 2:
        raise RuntimeError("Sequential inference needs at least two FEM library trajectories")
    sensor_model = None
    if args.tier in {"vision_load_dic", "vision_load_dic_ae"}:
        if args.sensor_model_json is None:
            raise RuntimeError("A calibrated --sensor-model-json is required for DIC/AE inference")
        sensor_model = SensorObservationModel.from_json(args.sensor_model_json)
        try:
            validate_sensor_model_for_inference(sensor_model, args.tier)
        except ValueError as error:
            raise RuntimeError(str(error)) from error
        library = [project_trajectory_to_sensor_space(trajectory, sensor_model) for trajectory in library]
    observations = pd.read_csv(args.observations_csv)
    posterior = assimilate_observation_sequence(
        observations,
        library,
        tier=args.tier,
        forecast_horizon=args.forecast_horizon,
        likelihood_sigma=args.likelihood_sigma,
        censor_tail_scale=args.censor_tail_scale,
        censor_quadrature_points=args.censor_quadrature_points,
        feature_noise=None if sensor_model is None else sensor_model.noise_scales,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    posterior.to_csv(args.out_dir / "posterior_forecast.csv", index=False)
    manifest = {
        "observation_source": str(args.observations_csv),
        "observation_tier": args.tier,
        "observation_space_version": "reality_obs_v1",
        "field_library": [str(path) for path in field_paths],
        "trajectory_manifest": str(args.trajectory_manifest) if args.trajectory_manifest else None,
        "forecast_horizon": args.forecast_horizon,
        "likelihood_sigma": args.likelihood_sigma,
        "censor_tail_scale": args.censor_tail_scale,
        "censor_quadrature_points": args.censor_quadrature_points,
        "sensor_observation_model_id": None if sensor_model is None else sensor_model.model_id,
        "sensor_calibration_status": None if sensor_model is None else sensor_model.calibration_status,
        "sensor_approved_for_inference": (
            None if sensor_model is None else sensor_model.approved_for_inference
        ),
        "sensor_model_json": str(args.sensor_model_json) if args.sensor_model_json else None,
        "training_launched": False,
        "physics_family": physics_families[0],
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(posterior)} sequential forecasts to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
