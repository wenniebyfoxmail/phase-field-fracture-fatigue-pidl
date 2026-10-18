#!/usr/bin/env python3
"""Focused no-training pair-contrast Jacobian audit for S09-E010 B25."""

from __future__ import annotations

from collections import OrderedDict
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from s09_e009_four_arm import (  # noqa: E402
    atomic_losses,
    flattened_objective_gradients,
    flattened_parameters,
    grouped_losses,
    parameter_state_sha256,
)
from s09_e010_support_amplitude import (  # noqa: E402
    ARM_B25,
    balanced_direction,
    support_amplitude_losses,
)
from s09_stage0a_p1_trainer import build_runtime  # noqa: E402


RUN_ID = "S09-E010-R001-support-amplitude-three-arm"
RUN_ROOT = ROOT / "local_archive/experiments/S09-E010/runs" / RUN_ID
PRODUCER = RUN_ROOT / "remote_run"
PACKET = (
    ROOT
    / "local_archive/experiments/S09-E008/runs/"
    "S09-E008-P1-R001-stage0a-memorisation/packet"
)
CONFIG = ROOT / "docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json"
CHECKPOINT = PRODUCER / ARM_B25 / "checkpoint_update500.pt"
OUTPUT = ROOT / "docs/research/S09/S09-E010/results/cycle_separability"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cosine(left: np.ndarray, right: np.ndarray) -> float | None:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    return None if denominator == 0 else float(np.dot(left, right) / denominator)


def effective_rank(matrix: np.ndarray) -> dict[str, Any]:
    singular = np.linalg.svd(matrix, compute_uv=False)
    energy = singular**2
    total = float(energy.sum())
    fractions = energy / total if total > 0 else np.zeros_like(energy)
    positive = fractions[fractions > 0]
    return {
        "effective_rank": (
            float(np.exp(-(positive * np.log(positive)).sum()))
            if positive.size
            else 0.0
        ),
        "first_mode_energy_fraction": float(fractions[0]) if fractions.size else 0.0,
        "singular_values": singular.tolist(),
    }


def runtime_and_initial() -> tuple[Any, np.ndarray, str]:
    config = json.loads(CONFIG.read_text())
    torch.manual_seed(int(config["model"]["seed"]))
    runtime = build_runtime(
        packet_dir=PACKET,
        config_path=CONFIG,
        device=torch.device("cpu"),
        executable=False,
    )
    initial, _ = flattened_parameters(runtime.model)
    return runtime, initial.cpu().numpy(), parameter_state_sha256(runtime.model)


def collect_jacobians(runtime: Any) -> dict[str, Any]:
    cycles = [int(value) for value in runtime.arrays["cycles"].tolist()]
    amplitudes: list[float] = []
    jacobians: list[np.ndarray] = []
    damage_gradients: list[np.ndarray] = []
    physics_gradients: list[np.ndarray] = []
    b25_directions: list[np.ndarray] = []
    projection_counts: list[dict[str, Any]] = []
    runtime.model.eval()
    before_hash = parameter_state_sha256(runtime.model)

    for index, cycle in enumerate(cycles):
        losses, context = atomic_losses(runtime, index)
        additions, addition_record = support_amplitude_losses(
            predicted_peak=context["output"]["d_peak"],
            target_peak=context["target"]["d_peak"],
            damage_pre=context["d_pre"],
            nodal_weight=context["output"]["nodal_weight"],
        )
        groups = grouped_losses(losses)
        pred_delta = context["output"]["d_peak"] - context["d_pre"]
        nodal = context["output"]["nodal_weight"]
        amplitude = (pred_delta.abs() * nodal).sum() / nodal.sum()
        objectives = OrderedDict(
            (
                ("amplitude", amplitude),
                ("L_D", groups["L_D"]),
                ("L_S", additions["L_S"]),
                ("L_A", additions["L_A"]),
                ("L_U", groups["L_U"]),
                ("L_H", groups["L_H"]),
                ("L_P", groups["L_P"]),
            )
        )
        vectors, _ = flattened_objective_gradients(runtime.model, objectives)
        balanced_inputs = OrderedDict(
            (name, vectors[name]) for name in ("L_D", "L_S", "L_A", "L_U", "L_H", "L_P")
        )
        direction, _ = balanced_direction(balanced_inputs, beta=0.25)
        amplitudes.append(float(amplitude.detach().cpu()))
        jacobians.append(vectors["amplitude"].detach().cpu().numpy().copy())
        damage_gradients.append(vectors["L_D"].detach().cpu().numpy().copy())
        physics_gradients.append(vectors["L_P"].detach().cpu().numpy().copy())
        b25_directions.append(direction.detach().cpu().numpy().copy())
        projection_counts.append(
            {
                "cycle": cycle,
                "predicted_amplitude": addition_record["predicted_amplitude"],
            }
        )
    if parameter_state_sha256(runtime.model) != before_hash:
        raise RuntimeError("read-only audit changed model parameters")
    return {
        "cycles": cycles,
        "amplitudes": np.asarray(amplitudes),
        "jacobians": np.stack(jacobians),
        "damage_gradients": np.stack(damage_gradients),
        "physics_gradients": np.stack(physics_gradients),
        "b25_directions": np.stack(b25_directions),
        "amplitude_records": projection_counts,
    }


def read_frozen_amplitudes() -> dict[int, float]:
    rows: dict[int, float] = {}
    with (PRODUCER / "per_cycle_metrics.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row["arm"] == ARM_B25 and int(row["update"]) == 500:
                rows[int(row["cycle"])] = float(row["predicted_damage_increment_abs_mean"])
    if len(rows) != 16:
        raise ValueError("frozen B25 update-500 amplitude support drift")
    return rows


def pair_audit(data: dict[str, Any], training_displacement: float) -> dict[str, Any]:
    cycles = data["cycles"]
    index = {cycle: i for i, cycle in enumerate(cycles)}
    config = json.loads(CONFIG.read_text())
    growth = [int(value) for value in config["data"]["growth_cycles"]]
    stagnant = [int(value) for value in config["data"]["near_stagnant_cycles"]]
    amplitudes = data["amplitudes"]
    jacobians = data["jacobians"]
    mean_damage_descent = -data["damage_gradients"].mean(axis=0)
    mean_physics_descent = -data["physics_gradients"].mean(axis=0)
    mean_b25_descent = -data["b25_directions"].mean(axis=0)

    pairs = []
    contrasts = []
    for growth_cycle in growth:
        for stagnant_cycle in stagnant:
            gi, si = index[growth_cycle], index[stagnant_cycle]
            margin = float(amplitudes[gi] - amplitudes[si])
            outcome = "WIN" if margin > 0 else "LOSS" if margin < 0 else "TIE"
            contrast = jacobians[gi] - jacobians[si]
            contrast_norm = float(np.linalg.norm(contrast))
            row_rms = math.sqrt(
                (float(np.linalg.norm(jacobians[gi])) ** 2
                 + float(np.linalg.norm(jacobians[si])) ** 2)
                / 2.0
            )
            required = None if contrast_norm == 0 else abs(margin) / contrast_norm
            record = {
                "growth_cycle": growth_cycle,
                "stagnant_cycle": stagnant_cycle,
                "outcome": outcome,
                "current_margin": margin,
                "growth_amplitude": float(amplitudes[gi]),
                "stagnant_amplitude": float(amplitudes[si]),
                "pair_contrast_jacobian_norm": contrast_norm,
                "contrast_to_row_rms": None if row_rms == 0 else contrast_norm / row_rms,
                "growth_stagnant_jacobian_cosine": cosine(jacobians[gi], jacobians[si]),
                "linear_min_parameter_l2_to_zero_margin": required,
                "linear_min_l2_relative_to_observed_training_displacement": (
                    None
                    if required is None or training_displacement == 0
                    else required / training_displacement
                ),
                "margin_derivative_along_mean_L_D_descent": float(
                    np.dot(contrast, mean_damage_descent)
                ),
                "margin_derivative_along_mean_L_P_descent": float(
                    np.dot(contrast, mean_physics_descent)
                ),
                "margin_derivative_along_mean_B25_descent": float(
                    np.dot(contrast, mean_b25_descent)
                ),
                "contrast_cosine_with_mean_L_D_descent": cosine(
                    contrast, mean_damage_descent
                ),
                "contrast_cosine_with_mean_L_P_descent": cosine(
                    contrast, mean_physics_descent
                ),
                "contrast_cosine_with_mean_B25_descent": cosine(
                    contrast, mean_b25_descent
                ),
            }
            pairs.append(record)
            contrasts.append(contrast)

    incorrect = [row for row in pairs if row["outcome"] == "LOSS"]
    correct = [row for row in pairs if row["outcome"] == "WIN"]

    def group_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
        norms = [row["pair_contrast_jacobian_norm"] for row in rows]
        relatives = [row["contrast_to_row_rms"] for row in rows]
        linear = [row["linear_min_l2_relative_to_observed_training_displacement"] for row in rows]
        b25_derivatives = [row["margin_derivative_along_mean_B25_descent"] for row in rows]
        return {
            "count": len(rows),
            "contrast_norm_median": float(np.median(norms)),
            "contrast_norm_minimum": float(np.min(norms)),
            "contrast_to_row_rms_median": float(np.median(relatives)),
            "linear_min_l2_relative_to_training_displacement_median": float(
                np.median(linear)
            ),
            "mean_B25_descent_increases_margin_count": int(
                sum(value > 0 for value in b25_derivatives)
            ),
            "mean_B25_descent_decreases_margin_count": int(
                sum(value < 0 for value in b25_derivatives)
            ),
        }

    contrast_matrix = np.stack(contrasts)
    incorrect_matrix = np.stack(
        [
            jacobians[index[row["growth_cycle"]]]
            - jacobians[index[row["stagnant_cycle"]]]
            for row in incorrect
        ]
    )
    return {
        "growth_cycles": growth,
        "near_stagnant_cycles": stagnant,
        "pairs": pairs,
        "all_pairs": {
            **group_summary(pairs),
            "contrast_matrix_rank": effective_rank(contrast_matrix),
        },
        "incorrect_pairs": {
            **group_summary(incorrect),
            "pairs": [
                [row["growth_cycle"], row["stagnant_cycle"]] for row in incorrect
            ],
            "contrast_matrix_rank": effective_rank(incorrect_matrix),
        },
        "correct_pairs": group_summary(correct),
        "mean_direction_norms": {
            "L_D_descent": float(np.linalg.norm(mean_damage_descent)),
            "L_P_descent": float(np.linalg.norm(mean_physics_descent)),
            "B25_descent": float(np.linalg.norm(mean_b25_descent)),
        },
    }


def write_csv(records: list[dict[str, Any]]) -> None:
    path = OUTPUT / "B25_update500_pair_contrast_jacobian.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def plot(records: list[dict[str, Any]]) -> None:
    labels = [f"{row['growth_cycle']}>{row['stagnant_cycle']}" for row in records]
    colors = ["#c44e52" if row["outcome"] == "LOSS" else "#4c72b0" for row in records]
    fig, axes = plt.subplots(2, 1, figsize=(13, 8.2), constrained_layout=True)
    axes[0].bar(labels, [row["current_margin"] for row in records], color=colors)
    axes[0].axhline(0, color="black", linewidth=0.8)
    axes[0].set_ylabel("B25 amplitude margin")
    axes[0].set_title("Current growth-minus-stagnant margins (red = misordered)")
    axes[1].bar(
        labels,
        [row["contrast_to_row_rms"] for row in records],
        color=colors,
    )
    axes[1].set_ylabel("||Jg - Js|| / RMS(||Jg||, ||Js||)")
    axes[1].set_title("Local pair-contrast sensitivity relative to row sensitivity")
    for axis in axes:
        axis.tick_params(axis="x", rotation=65, labelsize=8)
        axis.grid(axis="y", alpha=0.25)
    fig.suptitle("S09-E010 B25 update-500 pair-contrast Jacobian audit")
    fig.savefig(OUTPUT / "S09-E010-R001-B25-pair-contrast-jacobian.png", dpi=220, facecolor="white")
    fig.savefig(OUTPUT / "S09-E010-R001-B25-pair-contrast-jacobian.pdf", facecolor="white")
    plt.close(fig)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    runtime, initial_parameters, initial_hash = runtime_and_initial()
    payload = torch.load(CHECKPOINT, map_location="cpu", weights_only=True)
    if payload["update"] != 500 or payload["arm"] != ARM_B25:
        raise ValueError("B25 checkpoint identity mismatch")
    runtime.model.load_state_dict(payload["model"], strict=True)
    checkpoint_parameters, _ = flattened_parameters(runtime.model)
    training_displacement = float(
        np.linalg.norm(checkpoint_parameters.cpu().numpy() - initial_parameters)
    )
    data = collect_jacobians(runtime)
    frozen = read_frozen_amplitudes()
    replay_error = max(
        abs(float(value) - frozen[cycle])
        for cycle, value in zip(data["cycles"], data["amplitudes"])
    )
    if replay_error > 1e-12:
        raise ValueError("B25 amplitude replay mismatch")
    audit = pair_audit(data, training_displacement)
    write_csv(audit["pairs"])
    plot(audit["pairs"])
    receipt = {
        "schema_version": "s09-e010-pair-contrast-jacobian-v1",
        "run_id": RUN_ID,
        "state": "B25_update500",
        "purpose": "read-only local sensitivity audit of the 25 frozen amplitude-ranking pairs",
        "optimizer_constructed": False,
        "optimizer_steps_performed": 0,
        "fresh_holdout_accessed": False,
        "analysis_script": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "checkpoint": {
            "path": str(CHECKPOINT.relative_to(ROOT)),
            "sha256": sha256(CHECKPOINT),
            "parameter_state_sha256": parameter_state_sha256(runtime.model),
        },
        "common_initial_parameter_state_sha256": initial_hash,
        "observed_initial_to_B25_parameter_l2": training_displacement,
        "maximum_frozen_amplitude_replay_abs_difference": replay_error,
        "amplitude_jacobian_rank": effective_rank(data["jacobians"]),
        "audit": audit,
    }
    (OUTPUT / "B25_update500_pair_contrast_jacobian_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    print(json.dumps({
        "incorrect_pairs": audit["incorrect_pairs"],
        "optimizer_steps_performed": 0,
        "output": str(OUTPUT),
    }, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
