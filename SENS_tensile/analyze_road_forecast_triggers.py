#!/usr/bin/env python3
"""Build the first road-time/inspection-trigger diagnostic from frozen forecasts.

This script is analysis-only.  It reads the matched three-seed temporal study,
freezes signal envelopes on c77-c79, and only then audits c80-c89.  FEM fields
are used in explicitly named ``audit_only_*`` columns and never in the trigger
decision.
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

from road_forecast_trigger import (  # noqa: E402
    apply_trigger_rule,
    compute_trigger_trajectory,
    fit_signal_envelopes,
    observation_trigger_spec,
    road_forecast_horizon_spec,
    road_time_mapping_spec,
)


FAMILY_LAYOUT = {
    "markov": "core_1",
    "gru": "core_1",
    "diagonal_ssm": "core_1",
    "lstm": "core_2",
    "tcn": "core_2",
    "transformer": "core_2",
}
CALIBRATION_CYCLES = (77, 78, 79)


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
        raise ValueError("cannot write an empty CSV")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_family(temporal_package: Path, family: str) -> tuple[np.ndarray, np.ndarray, list[Path]]:
    stage = FAMILY_LAYOUT[family]
    paths = [
        temporal_package / "raw" / stage / f"{family}_seed{seed}" / "reused_evaluation_predictions.npz"
        for seed in (1, 2, 3)
    ]
    if not all(path.is_file() for path in paths):
        missing = [str(path) for path in paths if not path.is_file()]
        raise FileNotFoundError(f"missing matched prediction assets: {missing}")
    cycles: np.ndarray | None = None
    states: list[np.ndarray] = []
    for path in paths:
        with np.load(path, allow_pickle=False) as data:
            current_cycles = np.asarray(data["cycles"], dtype=int)
            current_states = np.asarray(data["predicted_states"], dtype=np.float32)
        if cycles is None:
            cycles = current_cycles
        elif not np.array_equal(cycles, current_cycles):
            raise ValueError(f"cycle mismatch in {path}")
        states.append(current_states)
    assert cycles is not None
    return cycles, np.stack(states), paths


def validate_dataset(dataset: Path, cycles: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with np.load(dataset, allow_pickle=False) as data:
        dataset_cycles = np.asarray(data["cycles"], dtype=int)
        states = np.asarray(data["states"], dtype=np.float32)
        coordinates = np.asarray(data["coordinates"], dtype=np.float64)
        areas = np.asarray(data["areas"], dtype=np.float64)
        trajectory_count = int(np.asarray(data["trajectory_count"]).item())
    if trajectory_count != 1:
        raise ValueError("this diagnostic is locked to the declared one-trajectory package")
    index = {int(cycle): position for position, cycle in enumerate(dataset_cycles)}
    if any(int(cycle) not in index for cycle in cycles):
        raise ValueError("prediction cycle absent from FEM audit dataset")
    selected = np.stack([states[index[int(cycle)]] for cycle in cycles])
    return selected, coordinates, areas


def _family_rows(
    temporal_package: Path,
    fem_states: np.ndarray,
    coordinates: np.ndarray,
    areas: np.ndarray,
) -> tuple[list[dict[str, object]], dict[str, object], list[Path]]:
    rows: list[dict[str, object]] = []
    all_predictions: list[np.ndarray] = []
    all_paths: list[Path] = []
    reference_cycles: np.ndarray | None = None
    envelope_summary: dict[str, object] = {}

    for family in FAMILY_LAYOUT:
        cycles, predictions, paths = load_family(temporal_package, family)
        if reference_cycles is None:
            reference_cycles = cycles
        elif not np.array_equal(reference_cycles, cycles):
            raise ValueError("families do not share one cycle grid")
        family_rows = compute_trigger_trajectory(
            cycles, predictions, fem_states, coordinates, areas, family=family
        )
        envelopes = fit_signal_envelopes(family_rows, CALIBRATION_CYCLES)
        apply_trigger_rule(family_rows, envelopes, CALIBRATION_CYCLES)
        rows.extend(family_rows)
        all_predictions.append(predictions)
        all_paths.extend(paths)
        envelope_summary[family] = envelopes

    assert reference_cycles is not None
    committee_predictions = np.concatenate(all_predictions, axis=0)
    committee_rows = compute_trigger_trajectory(
        reference_cycles,
        committee_predictions,
        fem_states,
        coordinates,
        areas,
        family="matched_model_committee",
    )
    committee_envelopes = fit_signal_envelopes(committee_rows, CALIBRATION_CYCLES)
    apply_trigger_rule(committee_rows, committee_envelopes, CALIBRATION_CYCLES)
    rows.extend(committee_rows)
    envelope_summary["matched_model_committee"] = committee_envelopes
    return rows, envelope_summary, all_paths


def first_trigger(rows: list[dict[str, object]], family: str, key: str) -> int | None:
    cycles = [int(row["cycle"]) for row in rows if row["family"] == family and bool(row[key])]
    return min(cycles) if cycles else None


def plot_trigger_trajectory(rows: list[dict[str, object]], out: Path) -> None:
    families = list(FAMILY_LAYOUT) + ["matched_model_committee"]
    colours = {
        "markov": "#666666",
        "gru": "#56B4E9",
        "lstm": "#009E73",
        "tcn": "#E69F00",
        "transformer": "#0072B2",
        "diagonal_ssm": "#CC79A7",
        "matched_model_committee": "#D55E00",
    }
    fig, axes = plt.subplots(3, 1, figsize=(8.2, 8.4), sharex=True, constrained_layout=True)
    for family in families:
        selected = sorted((row for row in rows if row["family"] == family), key=lambda row: int(row["cycle"]))
        cycles = np.asarray([int(row["cycle"]) for row in selected])
        width = 2.2 if family == "matched_model_committee" else 1.1
        alpha = 1.0 if family == "matched_model_committee" else 0.7
        axes[0].plot(cycles, [float(row["trigger_risk_score"]) for row in selected], color=colours[family], lw=width, alpha=alpha, label=family)
        axes[1].plot(cycles, [float(row["active_log_ensemble_std"]) for row in selected], color=colours[family], lw=width, alpha=alpha)
        axes[2].plot(cycles, [float(row["audit_only_fem_absolute_p99_iou"]) for row in selected], color=colours[family], lw=width, alpha=alpha)
    axes[0].axhline(3.0, color="#999999", ls="--", lw=1.0, label="candidate warning z=3")
    axes[0].axhline(5.0, color="#222222", ls=":", lw=1.0, label="candidate hard z=5")
    axes[0].set_ylabel("model-only risk score")
    axes[1].set_ylabel("active ensemble std\n(area-weighted log10)")
    axes[2].set_ylabel("FEM-p99 IoU\n(audit only)")
    axes[2].set_xlabel("FEM cycle index (simulation audit axis only)")
    axes[2].set_ylim(-0.03, 1.03)
    request_cycle = first_trigger(
        rows, "matched_model_committee", "candidate_request_inspection"
    )
    stop_cycle = first_trigger(
        rows, "matched_model_committee", "candidate_stop_recursive"
    )
    for axis in axes:
        axis.axvspan(77, 79, color="#E6E6E6", alpha=0.65, label="frozen envelope c77-c79" if axis is axes[0] else None)
        axis.axvline(81, color="#B2182B", ls="-.", lw=1.0, label="first audit-only IoU<0.5" if axis is axes[0] else None)
        if request_cycle is not None:
            axis.axvline(
                request_cycle,
                color="#D55E00",
                ls="--",
                lw=1.0,
                label="committee inspection request" if axis is axes[0] else None,
            )
        if stop_cycle is not None:
            axis.axvline(
                stop_cycle,
                color="#000000",
                ls=":",
                lw=1.0,
                label="committee stop recursion" if axis is axes[0] else None,
            )
        axis.grid(color="#D9D9D9", lw=0.6, alpha=0.7)
    handles, labels = axes[0].get_legend_handles_labels()
    axes[0].legend(handles, labels, ncol=3, fontsize=7.4, loc="upper left")
    fig.suptitle("Candidate observation trigger versus FEM-only mechanism audit\n(single eta0 trajectory; thresholds are not road-calibrated)", fontsize=11)
    fig.savefig(out.with_suffix(".png"), dpi=220)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def plot_short_to_long_schematic(out: Path) -> None:
    fig, axis = plt.subplots(figsize=(10.5, 4.5), constrained_layout=True)
    axis.set_axis_off()
    boxes = [
        (0.02, 0.57, 0.17, 0.25, "Road observations\nimage / FWD / strain\nWIM + environment", "#DDEBF7"),
        (0.23, 0.57, 0.17, 0.25, "Agent1 assimilation\nlatent-state posterior\nwith uncertainty", "#E2F0D9"),
        (0.44, 0.57, 0.17, 0.25, "Short horizon\nnext 1-3 calibrated\nload blocks", "#FFF2CC"),
        (0.65, 0.57, 0.15, 0.25, "Inspection trigger\ninnovation / OOD\nuncertainty", "#FCE4D6"),
        (0.83, 0.57, 0.15, 0.25, "New inspection\nor stop recursive\nfield rollout", "#F4CCCC"),
        (0.44, 0.12, 0.36, 0.25, "Long horizon is a scenario distribution\ntraffic + climate + maintenance -> hazard,\nthreshold probability, and RUL", "#E4DFEC"),
    ]
    for x, y, w, h, label, colour in boxes:
        patch = plt.Rectangle((x, y), w, h, facecolor=colour, edgecolor="#555555", lw=1.0)
        axis.add_patch(patch)
        axis.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=9)
    arrow = dict(arrowstyle="->", color="#555555", lw=1.4)
    for start, end in [((0.19, 0.695), (0.23, 0.695)), ((0.40, 0.695), (0.44, 0.695)), ((0.61, 0.695), (0.65, 0.695)), ((0.80, 0.695), (0.83, 0.695))]:
        axis.annotate("", xy=end, xytext=start, arrowprops=arrow)
    axis.annotate("", xy=(0.44, 0.245), xytext=(0.525, 0.57), arrowprops=arrow)
    axis.annotate("rolling update", xy=(0.315, 0.57), xytext=(0.90, 0.52), ha="center", fontsize=8, arrowprops=dict(arrowstyle="->", color="#777777", lw=1.1, connectionstyle="arc3,rad=-0.35"))
    axis.text(0.02, 0.93, "A model step is a calibrated load block, not one FEM cycle or one axle passage.", fontsize=11, weight="bold")
    axis.text(0.02, 0.03, "Current evidence supports only within-trajectory conditional propagation; road-time mapping and trigger thresholds remain uncalibrated.", fontsize=8.5, color="#555555")
    fig.savefig(out.with_suffix(".png"), dpi=220)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def write_decision(path: Path, rows: list[dict[str, object]]) -> None:
    committee = [row for row in rows if row["family"] == "matched_model_committee"]
    first_request = first_trigger(rows, "matched_model_committee", "candidate_request_inspection")
    first_stop = first_trigger(rows, "matched_model_committee", "candidate_stop_recursive")
    first_audit_failure = min(
        int(row["cycle"])
        for row in committee
        if bool(row["audit_only_support_gate_failed"])
    )
    request_lag = None if first_request is None else first_request - first_audit_failure
    audit_c80 = next(row for row in committee if int(row["cycle"]) == 80)
    audit_c87 = next(row for row in committee if int(row["cycle"]) == 87)
    text = f"""# Road time and observation-trigger formulation decision

## Verdict

The current FEM evidence supports a **rolling conditional forecast**: assimilate a recent state, forecast the next one to three calibrated load blocks, and request a new inspection when uncertainty, observation innovation, or traffic/environment shift exceeds a frozen envelope. It does not support mapping one FEM cycle to one axle, ESAL, day, or inspection interval, and it does not support deterministic field rollout to road failure.

One road forecast step should provisionally be a **calibrated equivalent-load block with calendar/environment caps**. The block closes at a calibrated exposure increment, maximum calendar duration, material environment shift, inspection, or maintenance event. Without WIM/load-spectrum data, the only defensible fallback is inspection-to-inspection state propagation.

Longer-horizon road output must be scenario-conditioned threshold probability, event hazard, and RUL distribution. It must not be presented as unlimited recursion of the h1-h3 field operator.

## Offline trigger diagnostic

The matched Markov/GRU/LSTM/TCN/Transformer/diagonal-SSM prediction ensemble was analysed without retraining. Signal envelopes were frozen from c77-c79 before c80-c89 was audited. Trigger decisions use only model ensemble disagreement and self-state/support drift. FEM IoU and error appear only in columns prefixed `audit_only_` and do not enter the rule.

- First committee candidate inspection request: `{first_request}`.
- First committee candidate stop-recursive decision: `{first_stop}`.
- First audit-only FEM-p99 IoU failure (<0.5): `c{first_audit_failure}`.
- Candidate request lag relative to that hidden failure: `{request_lag}` simulation steps; this is not positive early-warning lead time.
- Audit-only committee FEM-p99 IoU at c80: `{float(audit_c80['audit_only_fem_absolute_p99_iou']):.3f}`.
- Audit-only committee FEM-p99 IoU at c87: `{float(audit_c87['audit_only_fem_absolute_p99_iou']):.3f}`.

The model-only committee warning **lags** the first hidden support-gate failure and therefore does not provide useful early warning in this trajectory. These cycle values are a one-trajectory diagnostic, not an operational threshold. Three calibration states are too few to estimate false-alarm rate, missed-transition rate, or lead-time generalisation. The trigger is therefore `diagnostic_only_single_trajectory`, and observation innovation is a required next input rather than an optional enhancement.

## Reality-facing trigger hierarchy

1. Use model ensemble/latent uncertainty as a warning, never as the only proof of physical change.
2. Compare predicted and measured crack geometry, FWD deflection basin, and strain localization through Agent1's observation operator.
3. Treat WIM/load-spectrum, temperature, moisture, sensor drift, and maintenance as OOD/data-quality gates.
4. Request image/FWD/strain when one model warning is corroborated by one observation/OOD warning, or when a hard safety/data-quality gate fires.
5. Stop recursive field rollout after two consecutive model warnings, a hard innovation, an OOD exposure, an overdue inspection, or maintenance-induced state reset.

## Scope and blockers

- Exactly one eta0 FEM trajectory is available; no road early-warning generalisation is claimed.
- Current data contain no WIM/ESAL calibration, timestamps, temperature, moisture, FWD, strain, or maintenance records.
- The historical data-efficiency runner contains privileged cycle-phase inputs and is excluded from the operational trigger.
- c89 remains an autonomous-transition stress test, not a normal road forecast target.
- Promotion requires physically diverse trajectories, synchronized road/laboratory observations, calibrated likelihoods, and leave-one-trajectory/load/road-section-out validation.

## Decision

Accept the time/horizon and interface formulation as a **framework-validation diagnostic**. Quarantine the numerical trigger thresholds. Do not launch new training until Agent1 supplies a frozen observation-operator contract and the project has physically diverse traffic/environment trajectories.
"""
    path.write_text(text, encoding="utf-8")


def write_manifest(
    path: Path,
    args: argparse.Namespace,
    prediction_paths: list[Path],
    primary_assets: list[Path],
) -> None:
    payload = {
        "schema": "road_time_trigger_formulation_v1",
        "claim_class": "framework-validation",
        "status": "quarantined_trigger_thresholds",
        "training_launched": False,
        "trajectory_count": 1,
        "fem_is_audit_reference": True,
        "trigger_uses_fem_truth": False,
        "calibration_cycles": list(CALIBRATION_CYCLES),
        "locked_stress_cycles": [87, 89],
        "source_dataset": {"path": str(args.dataset), "sha256": sha256(args.dataset)},
        "temporal_package": str(args.temporal_package),
        "prediction_assets": [{"path": str(p), "sha256": sha256(p)} for p in prediction_paths],
        "primary_assets": [{"path": str(p.relative_to(args.out)), "sha256": sha256(p)} for p in primary_assets],
        "limitations": [
            "single FEM trajectory",
            "no road-time calibration",
            "no observed FWD/DIC/image innovation channels",
            "three-cycle diagnostic envelope is not operational",
        ],
    }
    write_json(path, payload)


def validate_package(out: Path) -> None:
    required = [
        "road_time_mapping_spec.json",
        "road_forecast_horizon_spec.json",
        "observation_trigger_spec.json",
        "trigger_trajectory.csv",
        "trigger_trajectory.png",
        "short_to_long_rul_schematic.png",
        "decision.md",
        "RUN_MANIFEST.json",
    ]
    missing = [name for name in required if not (out / name).is_file()]
    if missing:
        raise FileNotFoundError(f"missing package assets: {missing}")
    trigger = json.loads((out / "observation_trigger_spec.json").read_text())
    if trigger["status"] != "candidate_diagnostic_not_road_validated":
        raise ValueError("trigger status must remain diagnostic")
    rows = list(csv.DictReader((out / "trigger_trajectory.csv").open()))
    if not rows or any("audit_only_fem_absolute_p99_iou" not in row for row in rows):
        raise ValueError("trigger trajectory lacks separated FEM audit columns")
    if any(row["trigger_status"] != "diagnostic_only_single_trajectory" for row in rows):
        raise ValueError("trajectory trigger status was promoted")


def run(args: argparse.Namespace) -> None:
    args.out.mkdir(parents=True, exist_ok=True)
    reference_cycles, _, _ = load_family(args.temporal_package, "markov")
    fem_states, coordinates, areas = validate_dataset(args.dataset, reference_cycles)
    rows, envelopes, prediction_paths = _family_rows(
        args.temporal_package, fem_states, coordinates, areas
    )
    rows.sort(key=lambda row: (str(row["family"]), int(row["cycle"])))
    write_csv(args.out / "trigger_trajectory.csv", rows)

    write_json(args.out / "road_time_mapping_spec.json", road_time_mapping_spec())
    write_json(args.out / "road_forecast_horizon_spec.json", road_forecast_horizon_spec())
    committee_envelopes = envelopes["matched_model_committee"]
    write_json(
        args.out / "observation_trigger_spec.json",
        observation_trigger_spec(CALIBRATION_CYCLES, committee_envelopes),
    )
    plot_trigger_trajectory(rows, args.out / "trigger_trajectory")
    plot_short_to_long_schematic(args.out / "short_to_long_rul_schematic")
    write_decision(args.out / "decision.md", rows)

    assets = [
        args.out / "road_time_mapping_spec.json",
        args.out / "road_forecast_horizon_spec.json",
        args.out / "observation_trigger_spec.json",
        args.out / "trigger_trajectory.csv",
        args.out / "trigger_trajectory.png",
        args.out / "trigger_trajectory.pdf",
        args.out / "short_to_long_rul_schematic.png",
        args.out / "short_to_long_rul_schematic.pdf",
        args.out / "decision.md",
    ]
    assets.extend(
        path
        for path in (
            args.out / "00_task_brief.md",
            args.out / "attempt.md",
            args.out / "attempts.jsonl",
        )
        if path.is_file()
    )
    write_manifest(args.out / "RUN_MANIFEST.json", args, prediction_paths, assets)
    validate_package(args.out)
    print(json.dumps({"status": "PASS", "out": str(args.out), "rows": len(rows)}, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--temporal-package", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
