#!/usr/bin/env python3
"""Run the frozen single-trajectory observation-innovation diagnostic.

FEM is used twice but never inside the runtime decision function: first through
explicitly labelled synthetic/oracle-derived observation operators, and later
as an ``audit_only_*`` mechanism reference. No training is launched.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from road_forecast_trigger import normalized_weights, weighted_quantile  # noqa: E402
from road_observation_innovation import (  # noqa: E402
    CHANNELS,
    apply_innovation_aware_rule,
    fit_innovation_envelopes,
    observation_innovation_packet_spec,
    runtime_input_from_model_and_packet,
    score_observation_packet,
    validate_observation_innovation_packet,
)

from analyze_road_forecast_triggers import FAMILY_LAYOUT, load_family  # noqa: E402


CALIBRATION_STEPS = (77, 78, 79)
IMAGE_FEATURES = (
    "visible_area_fraction",
    "tip_x_p99",
    "centroid_x",
    "centroid_y",
    "transverse_width",
)
STRAIN_PROXY_FEATURES = (
    "top1_centroid_x",
    "top1_centroid_y",
    "top1_width_x",
    "top1_width_y",
)
FWD_FEATURES = ("central_deflection", "basin_curvature", "basin_area")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("cannot write empty CSV")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_committee(temporal_package: Path) -> tuple[np.ndarray, np.ndarray, list[Path]]:
    all_predictions: list[np.ndarray] = []
    paths: list[Path] = []
    cycles: np.ndarray | None = None
    for family in FAMILY_LAYOUT:
        current_cycles, predictions, family_paths = load_family(temporal_package, family)
        if cycles is None:
            cycles = current_cycles
        elif not np.array_equal(cycles, current_cycles):
            raise ValueError("prediction families do not share one cycle grid")
        all_predictions.append(predictions)
        paths.extend(family_paths)
    assert cycles is not None
    return cycles, np.concatenate(all_predictions, axis=0), paths


def load_fem_states(dataset: Path, cycles: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with np.load(dataset, allow_pickle=False) as data:
        dataset_cycles = np.asarray(data["cycles"], dtype=int)
        states = np.asarray(data["states"], dtype=np.float64)
        coordinates = np.asarray(data["coordinates"], dtype=np.float64)
        areas = np.asarray(data["areas"], dtype=np.float64)
        trajectory_count = int(np.asarray(data["trajectory_count"]).item())
    if trajectory_count != 1:
        raise ValueError("diagnostic is frozen to the declared single trajectory")
    index = {int(cycle): position for position, cycle in enumerate(dataset_cycles)}
    return np.stack([states[index[int(cycle)]] for cycle in cycles]), coordinates, areas


def synthetic_image_geometry(state: np.ndarray, coordinates: np.ndarray, areas: np.ndarray) -> np.ndarray:
    weights = normalized_weights(areas)
    damage = np.clip(np.asarray(state[:, 0], dtype=np.float64), 0.0, 1.0)
    visibility = np.clip((damage - 0.2) / 0.6, 0.0, 1.0)
    visible_weights = visibility * weights
    visible_mass = float(visible_weights.sum())
    if visible_mass <= 0:
        return np.zeros(len(IMAGE_FEATURES), dtype=np.float64)
    centroid_x = float(np.sum(coordinates[:, 0] * visible_weights) / visible_mass)
    centroid_y = float(np.sum(coordinates[:, 1] * visible_weights) / visible_mass)
    width = float(np.sqrt(np.sum((coordinates[:, 1] - centroid_y) ** 2 * visible_weights) / visible_mass))
    tip_x = weighted_quantile(coordinates[:, 0], visibility * areas, 0.99)
    return np.asarray([visible_mass, tip_x, centroid_x, centroid_y, width])


def oracle_strain_localization_proxy(state: np.ndarray, coordinates: np.ndarray, areas: np.ndarray) -> np.ndarray:
    log_raw = np.asarray(state[:, 3], dtype=np.float64)
    threshold = weighted_quantile(log_raw, areas, 0.99)
    mask = log_raw >= threshold
    weights = np.asarray(areas[mask], dtype=np.float64)
    weights = weights / weights.sum()
    points = coordinates[mask]
    centroid = np.sum(points * weights[:, None], axis=0)
    width = np.sqrt(np.sum((points - centroid) ** 2 * weights[:, None], axis=0))
    return np.concatenate([centroid, width])


def channel_payload(
    *,
    feature_names: tuple[str, ...],
    observed: np.ndarray,
    predicted_ensemble: np.ndarray,
    mask: np.ndarray,
    observation_std: np.ndarray,
    step: int,
    evidence_class: str,
    operator_id: str,
    source_hash: str,
    uncertainty_semantics: str,
) -> dict[str, object]:
    predicted_ensemble = np.asarray(predicted_ensemble, dtype=np.float64)
    mask_array = np.asarray(mask, dtype=bool)
    observed_array = np.asarray(observed, dtype=np.float64)
    predicted_mean = predicted_ensemble.mean(axis=0)
    predicted_std = predicted_ensemble.std(axis=0, ddof=0)
    observation_std_array = np.asarray(observation_std, dtype=np.float64)

    def nullable(values: np.ndarray) -> list[float | None]:
        return [float(value) if bool(mask_array[index]) else None for index, value in enumerate(values)]

    return {
        "feature_names": list(feature_names),
        "values": nullable(observed_array),
        "predicted_values": nullable(predicted_mean),
        "mask": mask_array.tolist(),
        "uncertainty": {
            "observation_std": nullable(observation_std_array),
            "prediction_std": nullable(predicted_std),
            "semantics": uncertainty_semantics,
        },
        "provenance": {
            "evidence_class": evidence_class,
            "source_id": f"single_eta0_fem_trajectory:{source_hash}",
            "observation_operator_id": operator_id,
            "source_hashes": {"operator_dataset": source_hash},
            "real_road_compatible": False,
        },
        "registration": {
            "coordinate_frame_id": "normalized_common_fem_mesh",
            "registration_id": "identity_single_trajectory_diagnostic",
            "quality_score": 1.0,
            "uncertainty": "not calibrated for image/FWD/strain deployment",
        },
        "time": {
            "timestamp": None,
            "equivalent_load_index": None,
            "inspection_epoch_id": f"synthetic_step_{step}",
            "integration_step_index": int(step),
        },
    }


def build_packet(
    step: int,
    fem_state: np.ndarray,
    predicted_states: np.ndarray,
    coordinates: np.ndarray,
    areas: np.ndarray,
    dataset_hash: str,
) -> dict[str, object]:
    image_observed = synthetic_image_geometry(fem_state, coordinates, areas)
    image_predictions = np.stack([
        synthetic_image_geometry(state, coordinates, areas) for state in predicted_states
    ])
    strain_observed = oracle_strain_localization_proxy(fem_state, coordinates, areas)
    strain_predictions = np.stack([
        oracle_strain_localization_proxy(state, coordinates, areas) for state in predicted_states
    ])
    fwd_values = np.zeros(len(FWD_FEATURES), dtype=np.float64)
    packet = {
        "schema_version": "observation_innovation_packet_v1",
        "packet_id": f"single-trajectory-synthetic-{step}",
        "time": {
            "timestamp": None,
            "equivalent_load_index": None,
            "inspection_epoch_id": f"synthetic_step_{step}",
            "integration_step_index": int(step),
        },
        "channels": {
            CHANNELS[0]: channel_payload(
                feature_names=IMAGE_FEATURES,
                observed=image_observed,
                predicted_ensemble=image_predictions,
                mask=np.ones(len(IMAGE_FEATURES), dtype=bool),
                observation_std=np.asarray([1.0e-4, 0.01, 0.01, 0.01, 0.01]),
                step=step,
                evidence_class="synthetic_sensor",
                operator_id="latent_damage_visibility_geometry_v1",
                source_hash=dataset_hash,
                uncertainty_semantics="fixed diagnostic resolution floor; not road calibrated",
            ),
            CHANNELS[1]: channel_payload(
                feature_names=FWD_FEATURES,
                observed=fwd_values,
                predicted_ensemble=np.zeros((len(predicted_states), len(FWD_FEATURES))),
                mask=np.zeros(len(FWD_FEATURES), dtype=bool),
                observation_std=np.ones(len(FWD_FEATURES)),
                step=step,
                evidence_class="oracle_derived_proxy",
                operator_id="unavailable_no_displacement_or_fwd_response",
                source_hash=dataset_hash,
                uncertainty_semantics="unavailable and fully masked; zeros are placeholders only",
            ),
            CHANNELS[2]: channel_payload(
                feature_names=STRAIN_PROXY_FEATURES,
                observed=strain_observed,
                predicted_ensemble=strain_predictions,
                mask=np.ones(len(STRAIN_PROXY_FEATURES), dtype=bool),
                observation_std=np.full(len(STRAIN_PROXY_FEATURES), 0.01),
                step=step,
                evidence_class="oracle_derived_proxy",
                operator_id="raw_energy_top1_localization_proxy_v1",
                source_hash=dataset_hash,
                uncertainty_semantics="fixed coordinate floor; no calibrated strain observation operator",
            ),
        },
        "operational_context": {
            "traffic_environment_ood": {
                "warning": False,
                "hard": False,
                "score": None,
                "provenance": "unavailable in the single FEM trajectory",
            },
            "data_quality": {
                "warning": False,
                "hard": False,
                "missing_fraction": None,
                "sensor_drift": None,
                "registration_failure": False,
            },
            "inspection_overdue": False,
            "maintenance_event": False,
        },
    }
    validate_observation_innovation_packet(packet)
    return packet


def first_true(rows: list[dict[str, object]], key: str, step_key: str = "integration_step_index") -> int | None:
    values = [int(row[step_key]) for row in rows if bool(row[key])]
    return min(values) if values else None


def relation_to_audit(request: int | None, audit_failure: int) -> tuple[int | None, str]:
    if request is None:
        return None, "no_request"
    lead = audit_failure - request
    if lead > 0:
        return lead, "positive_lead"
    if lead == 0:
        return 0, "same_step"
    return lead, "lag"


def policy_summary(
    policy: str,
    request: int | None,
    stop: int | None,
    audit_failure: int,
    association_horizon: int = 3,
) -> dict[str, object]:
    request_lead, request_relation = relation_to_audit(request, audit_failure)
    stop_lead, stop_relation = relation_to_audit(stop, audit_failure)
    false_alarm = int(
        request is not None
        and request < audit_failure
        and audit_failure - request > association_horizon
    )
    return {
        "policy": policy,
        "first_request_step": request,
        "first_stop_step": stop,
        "audit_only_hidden_support_failure_step": audit_failure,
        "request_lead_steps_positive_is_early": request_lead,
        "request_relation": request_relation,
        "stop_lead_steps_positive_is_early": stop_lead,
        "stop_relation": stop_relation,
        "false_alarm_count_descriptive_single_trajectory": false_alarm,
        "false_alarm_association_horizon_steps": association_horizon,
        "false_alarm_rate_estimable": False,
    }


def plot_results(rows: list[dict[str, object]], summary: list[dict[str, object]], out: Path) -> None:
    steps = np.asarray([int(row["integration_step_index"]) for row in rows])
    fig, axes = plt.subplots(3, 1, figsize=(9.0, 8.6), sharex=True, constrained_layout=True)
    axes[0].plot(steps, [float(row["model_trigger_risk_score"]) for row in rows], color="#555555", lw=2.0)
    axes[0].axhline(3.0, color="#999999", ls="--", lw=1.0)
    axes[0].axhline(5.0, color="#222222", ls=":", lw=1.0)
    axes[0].set_ylabel("model-only risk z")
    axes[1].plot(steps, [float(row["image_channel_z"]) for row in rows], color="#0072B2", lw=2.0, label="synthetic image geometry")
    axes[1].plot(steps, [float(row["strain_proxy_channel_z"]) for row in rows], color="#D55E00", lw=2.0, label="oracle-derived localization proxy")
    axes[1].plot(steps, [float(row["fwd_channel_z"]) for row in rows], color="#999999", lw=1.5, label="FWD unavailable/masked")
    axes[1].axhline(3.0, color="#999999", ls="--", lw=1.0)
    axes[1].axhline(5.0, color="#222222", ls=":", lw=1.0)
    axes[1].set_yscale("symlog", linthresh=5.0, linscale=1.0)
    axes[1].set_ylim(bottom=0.0)
    axes[1].set_ylabel("observation innovation z")
    axes[1].legend(fontsize=8, loc="upper left")
    axes[2].plot(steps, [float(row["audit_only_fem_absolute_p99_iou"]) for row in rows], color="#7B3294", lw=2.2)
    axes[2].axhline(0.5, color="#B2182B", ls="-.", lw=1.0)
    axes[2].set_ylabel("FEM-p99 IoU\n(audit only)")
    axes[2].set_xlabel("simulation integration step (no road-time conversion)")
    for axis in axes:
        axis.axvspan(77, 79, color="#E6E6E6", alpha=0.65)
        axis.grid(color="#D9D9D9", lw=0.6, alpha=0.7)
    colours = {
        "model_only": "#555555",
        "image_only_innovation": "#0072B2",
        "image_plus_oracle_proxy": "#009E73",
    }
    for item in summary:
        request = item["first_request_step"]
        if request is not None:
            axes[0].axvline(int(request), color=colours[str(item["policy"])], ls="--", lw=1.4, label=f"{item['policy']} request")
    axes[0].legend(fontsize=8, loc="upper left")
    fig.suptitle(
        "Model-only versus observation-innovation trigger\n"
        "single eta0 synthetic/oracle-derived diagnostic; FEM mechanism is audit-only",
        fontsize=11,
    )
    fig.savefig(out.with_suffix(".png"), dpi=220)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def write_trigger_spec(path: Path, envelopes: dict[str, object]) -> None:
    write_json(path, {
        "schema_version": "observation_innovation_trigger_v1",
        "status": "quarantined_single_synthetic_trajectory",
        "runtime_allowlist": sorted({
            "model uncertainty and self-state/support drift",
            "declared observation innovation",
            "traffic/environment OOD",
            "data quality, overdue inspection, and maintenance",
        }),
        "runtime_prohibited": [
            "FEM IoU or FEM field error",
            "known transition/failure cycle",
            "cycle-to-failure or target-cycle phase",
            "future traffic, environment, observation, or maintenance",
        ],
        "calibration_steps": list(CALIBRATION_STEPS),
        "calibration_rule": "median/MAD envelope frozen on c77-c79 only; z=3 warning and z=5 hard thresholds inherited from stage 1 without sweep",
        "request_rule": "one hard declared innovation/OOD/data-quality/overdue/maintenance gate, or model warning corroborated by observation/OOD/data-quality warning",
        "stop_rule": "hard gate, model stop, or two consecutive soft warnings",
        "feature_envelopes": {
            name: {"centre": value.centre, "scale": value.scale, "warn_z": value.warn_z, "hard_z": value.hard_z}
            for name, value in envelopes.items()
        },
        "offline_channel_status": {
            CHANNELS[0]: "synthetic_sensor derived from FEM damage through a declared visibility/geometry operator",
            CHANNELS[1]: "unavailable and masked; no displacement/FWD response exists in the archive",
            CHANNELS[2]: "oracle_derived_proxy from raw-energy localization; not a strain measurement",
        },
        "audit_join": "audit_only_* columns are joined after runtime decisions and can be permuted without changing them",
    })


def write_decision(path: Path, summary: list[dict[str, object]]) -> None:
    by_policy = {str(row["policy"]): row for row in summary}
    model = by_policy["model_only"]
    image = by_policy["image_only_innovation"]
    innovation = by_policy["image_plus_oracle_proxy"]
    text = f"""# Observation-Innovation Trigger: Stage-2 Decision

## Verdict

**Road-like image innovation remains late; positive lead appears only with an oracle-derived localization proxy.**

The stage-1 model-only policy first requests an inspection at step `{model['first_request_step']}` and stops recursion at `{model['first_stop_step']}`. With only the synthetic crack-image geometry channel, the same frozen policy first requests and stops at step `{image['first_request_step']}`. With image plus the oracle-derived raw-energy localization proxy, it first requests and stops at step `{innovation['first_request_step']}`. The independently joined FEM audit first falls below the absolute-p99 support gate at step `{innovation['audit_only_hidden_support_failure_step']}`.

Therefore the model-only request has lead `{model['request_lead_steps_positive_is_early']}` (a lag when negative), and image-only has lead `{image['request_lead_steps_positive_is_early']}`. The `+{innovation['request_lead_steps_positive_is_early']}` lead appears only after adding the hidden raw-energy localization proxy. The reality-facing result is therefore **negative**: the available road-like image proxy does not provide positive lead. The oracle-assisted result is an upper-bound diagnostic, not evidence of road early warning, and it has no road-time/ESAL/calendar conversion.

## What the trigger actually consumed

- model ensemble/self-state diagnostics from the matched model committee;
- a declared synthetic crack-image geometry innovation;
- an explicitly labelled oracle-derived raw-energy localization proxy;
- no FWD innovation, because the archive contains no displacement or FWD basin response;
- no traffic/environment OOD, overdue, maintenance, or sensor-quality event, because those streams are absent.

The runtime decision function receives none of the FEM IoU/error columns. FEM support is joined afterwards under `audit_only_*`. Automated tests reject extra FEM/audit/failure keys and show that changing audit values cannot change decisions.

## Frozen rule and false alarms

The feature envelopes were frozen from c77-c79, using the inherited robust warning/hard thresholds `z=3/5`. c80-c89 were not used to fit thresholds, and no threshold sweep was performed. Under the predeclared three-step association rule, the descriptive false-alarm counts are `{model['false_alarm_count_descriptive_single_trajectory']}`, `{image['false_alarm_count_descriptive_single_trajectory']}`, and `{innovation['false_alarm_count_descriptive_single_trajectory']}` for model-only, image-only, and oracle-assisted policies. A false-alarm **rate cannot be estimated** from one trajectory and one hidden support transition.

## Reality gap

1. The image channel needs registered repeated road imagery, segmentation calibration, visibility/missingness, and registration uncertainty.
2. FWD requires measured basins plus a calibrated structural response operator, layer/support conditions, load, and temperature.
3. Strain localization requires synchronized sensors or DIC and a calibrated projection/error model. The present raw-energy proxy is not strain.
4. WIM/load spectra, timestamps, temperature, moisture, maintenance, inspection policy, and sensor drift are absent.
5. Thresholds require physically independent calibration trajectories and leave-one-road-section/asset-out validation.

## Decision

Accept `observation_innovation_packet_v1` and the leakage firewall as an interface/framework diagnostic. Record image-only triggering as a negative result and quarantine the oracle-assisted positive one-step lead. Do not claim real-road detection performance, false-alarm rate, or RUL improvement from this package.
"""
    path.write_text(text, encoding="utf-8")


def validate_outputs(out: Path) -> None:
    required = [
        "observation_innovation_packet_v1.json",
        "observation_innovation_trigger_spec_v1.json",
        "synthetic_innovation_packets.jsonl",
        "innovation_trigger_trajectory.csv",
        "trigger_policy_comparison.csv",
        "decision.md",
        "RUN_MANIFEST.json",
        "HASHES.sha256",
    ]
    missing = [name for name in required if not (out / name).is_file()]
    if missing:
        raise FileNotFoundError(f"missing outputs: {missing}")
    packets = [json.loads(line) for line in (out / "synthetic_innovation_packets.jsonl").read_text().splitlines()]
    for packet in packets:
        validate_observation_innovation_packet(packet)
    rows = list(csv.DictReader((out / "innovation_trigger_trajectory.csv").open()))
    if not rows or not all("audit_only_fem_absolute_p99_iou" in row for row in rows):
        raise ValueError("audit join is absent")
    runtime_columns = {
        key for key in rows[0]
        if not key.startswith("audit_only_")
    }
    if any("fem" in key.lower() or "failure" in key.lower() for key in runtime_columns):
        raise ValueError("runtime trajectory leaked a FEM/failure key")


def run(args: argparse.Namespace) -> None:
    args.out.mkdir(parents=True, exist_ok=True)
    cycles, predictions, prediction_paths = load_committee(args.temporal_package)
    fem_states, coordinates, areas = load_fem_states(args.dataset, cycles)
    dataset_hash = sha256(args.dataset)
    packets = [
        build_packet(int(cycle), fem_states[index], predictions[:, index], coordinates, areas, dataset_hash)
        for index, cycle in enumerate(cycles)
    ]
    envelopes = fit_innovation_envelopes(packets, CALIBRATION_STEPS)
    scores = [score_observation_packet(packet, envelopes) for packet in packets]

    with args.stage1_csv.open(newline="", encoding="utf-8") as handle:
        stage1_rows = [
            row for row in csv.DictReader(handle)
            if row["family"] == "matched_model_committee"
        ]
    stage1_by_step = {int(row["cycle"]): row for row in stage1_rows}
    runtime_inputs = [
        runtime_input_from_model_and_packet(
            stage1_by_step[int(cycle)], score, packet["operational_context"]
        )
        for cycle, score, packet in zip(cycles, scores, packets)
    ]
    decisions = apply_innovation_aware_rule(runtime_inputs, CALIBRATION_STEPS)
    image_scores = [{
        "observation_warning_count": int(score["channel_z"][CHANNELS[0]] >= 3.0),
        "observation_hard_count": int(score["channel_z"][CHANNELS[0]] >= 5.0),
        "max_observation_z": float(score["channel_z"][CHANNELS[0]]),
    } for score in scores]
    image_runtime_inputs = [
        runtime_input_from_model_and_packet(
            stage1_by_step[int(cycle)], score, packet["operational_context"]
        )
        for cycle, score, packet in zip(cycles, image_scores, packets)
    ]
    image_decisions = apply_innovation_aware_rule(
        image_runtime_inputs, CALIBRATION_STEPS
    )

    detailed_rows: list[dict[str, object]] = []
    for cycle, score, decision, image_decision in zip(
        cycles, scores, decisions, image_decisions
    ):
        stage1 = stage1_by_step[int(cycle)]
        detailed_rows.append({
            "integration_step_index": int(cycle),
            "model_trigger_risk_score": float(stage1["trigger_risk_score"]),
            "model_only_request_inspection": stage1["candidate_request_inspection"],
            "model_only_stop_recursive": stage1["candidate_stop_recursive"],
            "image_channel_z": float(score["channel_z"][CHANNELS[0]]),
            "fwd_channel_z": float(score["channel_z"][CHANNELS[1]]),
            "strain_proxy_channel_z": float(score["channel_z"][CHANNELS[2]]),
            "observation_warning_count": int(score["observation_warning_count"]),
            "observation_hard_count": int(score["observation_hard_count"]),
            "image_only_request_inspection": bool(image_decision["innovation_aware_request_inspection"]),
            "image_only_stop_recursive": bool(image_decision["innovation_aware_stop_recursive"]),
            "innovation_aware_request_inspection": bool(decision["innovation_aware_request_inspection"]),
            "innovation_aware_stop_recursive": bool(decision["innovation_aware_stop_recursive"]),
            "runtime_decision_status": decision["runtime_decision_status"],
            "audit_only_fem_absolute_p99_iou": float(stage1["audit_only_fem_absolute_p99_iou"]),
            "audit_only_fem_support_area_ratio": float(stage1["audit_only_fem_support_area_ratio"]),
            "audit_only_fem_active_log_mae": float(stage1["audit_only_fem_active_log_mae"]),
            "audit_only_hidden_support_gate_failed": stage1["audit_only_support_gate_failed"],
        })

    audit_failure = min(
        int(row["integration_step_index"])
        for row in detailed_rows
        if str(row["audit_only_hidden_support_gate_failed"]).lower() == "true"
    )
    model_request = min(int(row["integration_step_index"]) for row in detailed_rows if str(row["model_only_request_inspection"]).lower() == "true")
    model_stop = min(int(row["integration_step_index"]) for row in detailed_rows if str(row["model_only_stop_recursive"]).lower() == "true")
    innovation_request = first_true(detailed_rows, "innovation_aware_request_inspection")
    innovation_stop = first_true(detailed_rows, "innovation_aware_stop_recursive")
    image_request = first_true(detailed_rows, "image_only_request_inspection")
    image_stop = first_true(detailed_rows, "image_only_stop_recursive")
    summary = [
        policy_summary("model_only", model_request, model_stop, audit_failure),
        policy_summary("image_only_innovation", image_request, image_stop, audit_failure),
        policy_summary("image_plus_oracle_proxy", innovation_request, innovation_stop, audit_failure),
    ]

    write_json(args.out / "observation_innovation_packet_v1.json", observation_innovation_packet_spec())
    write_trigger_spec(args.out / "observation_innovation_trigger_spec_v1.json", envelopes)
    with (args.out / "synthetic_innovation_packets.jsonl").open("w", encoding="utf-8") as handle:
        for packet in packets:
            handle.write(json.dumps(packet, sort_keys=True) + "\n")
    write_csv(args.out / "innovation_trigger_trajectory.csv", detailed_rows)
    write_csv(args.out / "trigger_policy_comparison.csv", summary)
    plot_results(detailed_rows, summary, args.out / "innovation_trigger_comparison")
    write_decision(args.out / "decision.md", summary)

    primary_names = [
        "observation_innovation_packet_v1.json",
        "observation_innovation_trigger_spec_v1.json",
        "synthetic_innovation_packets.jsonl",
        "innovation_trigger_trajectory.csv",
        "trigger_policy_comparison.csv",
        "innovation_trigger_comparison.png",
        "innovation_trigger_comparison.pdf",
        "decision.md",
        "00_task_brief.md",
        "attempt.md",
        "attempts.jsonl",
    ]
    primary_assets = [args.out / name for name in primary_names if (args.out / name).is_file()]
    manifest = {
        "schema_version": "observation_innovation_trigger_package_v1",
        "status": "quarantined_single_synthetic_trajectory",
        "claim_class": "framework-validation",
        "training_launched": False,
        "trajectory_count": 1,
        "calibration_steps": list(CALIBRATION_STEPS),
        "threshold_sweep": False,
        "runtime_uses_fem_audit": False,
        "offline_observations": {
            "image": "synthetic_sensor",
            "fwd": "unavailable_masked",
            "strain": "oracle_derived_proxy",
        },
        "agent1_package": {"path": str(args.agent1_package), "manifest_sha256": sha256(args.agent1_package / "RUN_MANIFEST.json")},
        "agent3_contract": {"path": str(args.agent3_contract), "sha256": sha256(args.agent3_contract)},
        "source_dataset": {"path": str(args.dataset), "sha256": dataset_hash},
        "stage1_csv": {"path": str(args.stage1_csv), "sha256": sha256(args.stage1_csv)},
        "implementation_assets": [
            {"path": "source/road_observation_innovation.py", "sha256": sha256(ROOT / "source" / "road_observation_innovation.py")},
            {"path": "SENS_tensile/analyze_observation_innovation_trigger.py", "sha256": sha256(Path(__file__).resolve())},
            {"path": "tests/test_road_observation_innovation.py", "sha256": sha256(ROOT / "tests" / "test_road_observation_innovation.py")},
        ],
        "prediction_assets": [{"path": str(path), "sha256": sha256(path)} for path in prediction_paths],
        "primary_assets": [{"path": path.name, "sha256": sha256(path)} for path in primary_assets],
        "hash_index": "HASHES.sha256",
        "limitations": [
            "one eta0 FEM trajectory",
            "no road-time mapping",
            "image observation is synthetic",
            "strain localization is oracle-derived rather than measured",
            "FWD, traffic, environment, maintenance, and real data quality are absent",
            "three calibration steps cannot establish operational false-alarm rate",
        ],
    }
    write_json(args.out / "RUN_MANIFEST.json", manifest)
    hash_paths = primary_assets + [args.out / "RUN_MANIFEST.json"]
    (args.out / "HASHES.sha256").write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in hash_paths),
        encoding="utf-8",
    )
    validate_outputs(args.out)
    print(json.dumps({"status": "PASS", "summary": summary, "out": str(args.out)}, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--temporal-package", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--stage1-csv", type=Path, required=True)
    parser.add_argument("--agent1-package", type=Path, required=True)
    parser.add_argument("--agent3-contract", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
