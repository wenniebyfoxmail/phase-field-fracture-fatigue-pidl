#!/usr/bin/env python3
"""Read-only cycle-separability audit for the completed S09-E010 run.

The audit performs forward and autograd evaluations at the common initial
state and the three update-500 checkpoints.  It never constructs an optimizer
and never calls ``backward`` or ``step``.  Its purpose is to distinguish an
output-representation bottleneck from loss-gradient conflict/compression.
"""

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
    grouped_losses,
    parameter_state_sha256,
)
from s09_e010_support_amplitude import support_amplitude_losses  # noqa: E402
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
OUTPUT = ROOT / "docs/research/S09/S09-E010/results/cycle_separability"

ARMS = OrderedDict(
    (
        ("initial_common", None),
        ("A25_update500", "A25_exact_e009_replay"),
        ("B25_update500", "B25_support_amplitude_beta0p25"),
        ("B0_update500", "B0_support_amplitude_beta0"),
    )
)
OBJECTIVES = ("L_D", "L_S", "L_A", "L_P")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def matrix_metrics(matrix: np.ndarray) -> dict[str, Any]:
    """Return rank diagnostics for rows interpreted as per-cycle vectors."""
    if matrix.ndim != 2 or not np.isfinite(matrix).all():
        raise ValueError("matrix must be finite and two-dimensional")
    row_norm = np.linalg.norm(matrix, axis=1)
    valid = row_norm > 0
    gram = np.zeros((matrix.shape[0], matrix.shape[0]), dtype=np.float64)
    if np.any(valid):
        normalized = np.zeros_like(matrix)
        normalized[valid] = matrix[valid] / row_norm[valid, None]
        gram = normalized @ normalized.T
    singular = np.linalg.svd(matrix, compute_uv=False)
    energy = singular**2
    total = float(energy.sum())
    fractions = energy / total if total > 0 else np.zeros_like(energy)
    positive = fractions[fractions > 0]
    effective_rank = (
        float(np.exp(-(positive * np.log(positive)).sum())) if positive.size else 0.0
    )
    stable_rank = float(total / energy[0]) if energy.size and energy[0] > 0 else 0.0
    return {
        "effective_rank": effective_rank,
        "stable_rank": stable_rank,
        "first_mode_energy_fraction": float(fractions[0]) if fractions.size else 0.0,
        "singular_values": singular.tolist(),
        "row_norms": row_norm.tolist(),
        "cosine_gram": gram.tolist(),
        "zero_row_count": int((~valid).sum()),
    }


def state_metrics(
    matrix: np.ndarray,
    growth_indices: list[int],
    stagnant_indices: list[int],
) -> dict[str, Any]:
    raw = matrix_metrics(matrix)
    centered_matrix = matrix - matrix.mean(axis=0, keepdims=True)
    centered = matrix_metrics(centered_matrix)
    growth = matrix[growth_indices]
    stagnant = matrix[stagnant_indices]
    growth_mean = growth.mean(axis=0)
    stagnant_mean = stagnant.mean(axis=0)
    contrast = growth_mean - stagnant_mean
    growth_scatter = np.sqrt(np.mean(np.sum((growth - growth_mean) ** 2, axis=1)))
    stagnant_scatter = np.sqrt(
        np.mean(np.sum((stagnant - stagnant_mean) ** 2, axis=1))
    )
    pooled_scatter = math.sqrt((growth_scatter**2 + stagnant_scatter**2) / 2.0)
    contrast_norm = float(np.linalg.norm(contrast))
    mean_denominator = float(np.linalg.norm(growth_mean) * np.linalg.norm(stagnant_mean))
    mean_cosine = (
        None
        if mean_denominator == 0
        else float(np.dot(growth_mean, stagnant_mean) / mean_denominator)
    )
    return {
        "raw": raw,
        "cycle_centered": centered,
        "growth_stagnant": {
            "contrast_norm": contrast_norm,
            "pooled_within_group_rms": float(pooled_scatter),
            "contrast_to_within_ratio": (
                None if pooled_scatter == 0 else contrast_norm / pooled_scatter
            ),
            "mean_vector_cosine": mean_cosine,
        },
    }


def cosine(left: np.ndarray, right: np.ndarray) -> float | None:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator == 0:
        return None
    return float(np.dot(left, right) / denominator)


def load_runtime() -> Any:
    config = json.loads(CONFIG.read_text())
    torch.manual_seed(int(config["model"]["seed"]))
    return build_runtime(
        packet_dir=PACKET,
        config_path=CONFIG,
        device=torch.device("cpu"),
        executable=False,
    )


def read_expected_initial_identity() -> str:
    values = set()
    for arm in tuple(value for value in ARMS.values() if value is not None):
        record = json.loads((PRODUCER / arm / "start_identity.json").read_text())
        values.add(record["initial_state_sha256"])
    if len(values) != 1:
        raise ValueError("arm start identities disagree")
    return values.pop()


def collect_state(runtime: Any) -> dict[str, Any]:
    cycles = [int(value) for value in runtime.arrays["cycles"].tolist()]
    growth_cycles = set(int(value) for value in runtime.config["data"]["growth_cycles"])
    stagnant_cycles = set(
        int(value) for value in runtime.config["data"]["near_stagnant_cycles"]
    )
    growth_indices = [i for i, cycle in enumerate(cycles) if cycle in growth_cycles]
    stagnant_indices = [i for i, cycle in enumerate(cycles) if cycle in stagnant_cycles]
    if len(cycles) != 16 or len(growth_indices) != 5 or len(stagnant_indices) != 5:
        raise ValueError("frozen support drift")

    runtime.model.eval()
    initial_hash = parameter_state_sha256(runtime.model)
    increment_fields: list[np.ndarray] = []
    gradients: dict[str, list[np.ndarray]] = {name: [] for name in OBJECTIVES}
    cross_objective: list[dict[str, Any]] = []
    nodal_weight = np.asarray(runtime.arrays["nodal_weight"], dtype=np.float64)
    sqrt_weight = np.sqrt(nodal_weight / nodal_weight.sum())

    for index, cycle in enumerate(cycles):
        losses, context = atomic_losses(runtime, index)
        additions, _ = support_amplitude_losses(
            predicted_peak=context["output"]["d_peak"],
            target_peak=context["target"]["d_peak"],
            damage_pre=context["d_pre"],
            nodal_weight=context["output"]["nodal_weight"],
        )
        groups = grouped_losses(losses)
        objectives = OrderedDict(
            (
                ("L_D", groups["L_D"]),
                ("L_S", additions["L_S"]),
                ("L_A", additions["L_A"]),
                ("L_P", groups["L_P"]),
            )
        )
        vectors, _ = flattened_objective_gradients(runtime.model, objectives)
        arrays = {
            name: vectors[name].detach().cpu().numpy().astype(np.float64, copy=True)
            for name in OBJECTIVES
        }
        for name in OBJECTIVES:
            gradients[name].append(arrays[name])
        cross_objective.append(
            {
                "cycle": cycle,
                "L_D_vs_L_S": cosine(arrays["L_D"], arrays["L_S"]),
                "L_D_vs_L_A": cosine(arrays["L_D"], arrays["L_A"]),
                "L_D_vs_L_P": cosine(arrays["L_D"], arrays["L_P"]),
                "L_A_vs_L_P": cosine(arrays["L_A"], arrays["L_P"]),
            }
        )
        delta = (
            context["output"]["d_peak"].detach().cpu().numpy()
            - runtime.arrays["d_pre"][index]
        )
        increment_fields.append(delta * sqrt_weight)

    if parameter_state_sha256(runtime.model) != initial_hash:
        raise RuntimeError("read-only audit changed model parameters")

    output_matrix = np.stack(increment_fields)
    gradient_matrices = {name: np.stack(rows) for name, rows in gradients.items()}
    objective_metrics = {
        name: state_metrics(matrix, growth_indices, stagnant_indices)
        for name, matrix in gradient_matrices.items()
    }

    contrast_vectors = {
        name: matrix[growth_indices].mean(axis=0)
        - matrix[stagnant_indices].mean(axis=0)
        for name, matrix in gradient_matrices.items()
    }
    contrast_cosines = {
        "L_D_vs_L_S": cosine(contrast_vectors["L_D"], contrast_vectors["L_S"]),
        "L_D_vs_L_A": cosine(contrast_vectors["L_D"], contrast_vectors["L_A"]),
        "L_D_vs_L_P": cosine(contrast_vectors["L_D"], contrast_vectors["L_P"]),
        "L_A_vs_L_P": cosine(contrast_vectors["L_A"], contrast_vectors["L_P"]),
    }
    return {
        "parameter_state_sha256": initial_hash,
        "cycles": cycles,
        "growth_cycles": sorted(growth_cycles),
        "near_stagnant_cycles": sorted(stagnant_cycles),
        "output_increment": state_metrics(
            output_matrix, growth_indices, stagnant_indices
        ),
        "objective_gradients": objective_metrics,
        "per_cycle_cross_objective_cosines": cross_objective,
        "growth_stagnant_contrast_cosines": contrast_cosines,
    }


def plot_heatmaps(records: dict[str, Any], cycles: list[int]) -> None:
    columns = ("output_increment", *OBJECTIVES)
    labels = ("predicted Δd", *OBJECTIVES)
    fig, axes = plt.subplots(
        len(records), len(columns), figsize=(18, 13.5), constrained_layout=True
    )
    image = None
    for row, (state, record) in enumerate(records.items()):
        for column, (key, label) in enumerate(zip(columns, labels)):
            metrics = (
                record["output_increment"]
                if key == "output_increment"
                else record["objective_gradients"][key]
            )
            gram = np.asarray(metrics["raw"]["cosine_gram"])
            image = axes[row, column].imshow(
                gram, vmin=-1, vmax=1, cmap="coolwarm", interpolation="nearest"
            )
            axes[row, column].set_title(
                f"{state}\n{label}: r_eff={metrics['cycle_centered']['effective_rank']:.2f}"
            )
            axes[row, column].set_xticks(range(len(cycles)), cycles, rotation=90, fontsize=6)
            axes[row, column].set_yticks(range(len(cycles)), cycles, fontsize=6)
            if column == 0:
                axes[row, column].set_ylabel("cycle")
    assert image is not None
    fig.colorbar(image, ax=axes.ravel().tolist(), shrink=0.65, label="row cosine")
    fig.suptitle(
        "S09-E010 cycle separability: output and per-objective parameter-gradient geometry",
        fontsize=15,
    )
    fig.savefig(OUTPUT / "S09-E010-R001-cycle-gradient-gram.png", dpi=210, facecolor="white")
    fig.savefig(OUTPUT / "S09-E010-R001-cycle-gradient-gram.pdf", facecolor="white")
    plt.close(fig)


def plot_summary(records: dict[str, Any]) -> None:
    states = list(records)
    components = ("output_increment", *OBJECTIVES)
    labels = ("predicted Δd", *OBJECTIVES)
    x = np.arange(len(states))
    width = 0.15
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.2), constrained_layout=True)
    for i, (component, label) in enumerate(zip(components, labels)):
        metrics = [
            record["output_increment"]
            if component == "output_increment"
            else record["objective_gradients"][component]
            for record in records.values()
        ]
        axes[0].bar(
            x + (i - 2) * width,
            [m["cycle_centered"]["effective_rank"] for m in metrics],
            width,
            label=label,
        )
        axes[1].bar(
            x + (i - 2) * width,
            [
                m["growth_stagnant"]["contrast_to_within_ratio"] or 0.0
                for m in metrics
            ],
            width,
            label=label,
        )
    for axis in axes:
        axis.set_xticks(x, states, rotation=18, ha="right")
        axis.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("entropy effective rank after cycle centering")
    axes[0].set_title("How many cycle-varying directions are present?")
    axes[1].set_ylabel("growth–stagnant contrast / within-group RMS")
    axes[1].set_title("Does each signal separate the frozen groups?")
    axes[1].legend(ncol=3, fontsize=8)
    fig.suptitle("S09-E010 no-training cycle-separability audit")
    fig.savefig(OUTPUT / "S09-E010-R001-cycle-separability-summary.png", dpi=220, facecolor="white")
    fig.savefig(OUTPUT / "S09-E010-R001-cycle-separability-summary.pdf", facecolor="white")
    plt.close(fig)


def write_summary_csv(records: dict[str, Any]) -> None:
    rows = []
    for state, record in records.items():
        for component in ("output_increment", *OBJECTIVES):
            metrics = (
                record["output_increment"]
                if component == "output_increment"
                else record["objective_gradients"][component]
            )
            rows.append(
                {
                    "state": state,
                    "component": component,
                    "centered_effective_rank": metrics["cycle_centered"]["effective_rank"],
                    "centered_first_mode_energy_fraction": metrics["cycle_centered"][
                        "first_mode_energy_fraction"
                    ],
                    "raw_effective_rank": metrics["raw"]["effective_rank"],
                    "growth_stagnant_contrast_norm": metrics["growth_stagnant"][
                        "contrast_norm"
                    ],
                    "growth_stagnant_pooled_within_rms": metrics["growth_stagnant"][
                        "pooled_within_group_rms"
                    ],
                    "growth_stagnant_contrast_to_within_ratio": metrics[
                        "growth_stagnant"
                    ]["contrast_to_within_ratio"],
                    "growth_stagnant_mean_vector_cosine": metrics["growth_stagnant"][
                        "mean_vector_cosine"
                    ],
                }
            )
    path = OUTPUT / "cycle_separability_summary.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    runtime = load_runtime()
    expected_initial = read_expected_initial_identity()
    observed_initial = parameter_state_sha256(runtime.model)
    if observed_initial != expected_initial:
        raise ValueError("common initial model identity mismatch")

    records: OrderedDict[str, Any] = OrderedDict()
    checkpoint_records: dict[str, Any] = {}
    for state, arm in ARMS.items():
        if arm is None:
            checkpoint_records[state] = {
                "kind": "common_initial_state",
                "parameter_state_sha256": observed_initial,
            }
        else:
            checkpoint = PRODUCER / arm / "checkpoint_update500.pt"
            payload = torch.load(checkpoint, map_location="cpu", weights_only=True)
            if payload["update"] != 500 or payload["arm"] != arm:
                raise ValueError(f"checkpoint identity mismatch: {arm}")
            runtime.model.load_state_dict(payload["model"], strict=True)
            checkpoint_records[state] = {
                "kind": "update500_checkpoint",
                "arm": arm,
                "path": str(checkpoint.relative_to(ROOT)),
                "sha256": sha256(checkpoint),
            }
        records[state] = collect_state(runtime)

    cycles = records["initial_common"]["cycles"]
    plot_heatmaps(records, cycles)
    plot_summary(records)
    write_summary_csv(records)
    receipt = {
        "schema_version": "s09-e010-cycle-separability-audit-v1",
        "run_id": RUN_ID,
        "purpose": (
            "read-only discrimination between cycle-representation compression "
            "and multiobjective gradient geometry"
        ),
        "optimizer_constructed": False,
        "optimizer_steps_performed": 0,
        "fresh_holdout_accessed": False,
        "analysis_script": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "runtime": {
            "device": "cpu",
            "torch_version": torch.__version__,
            "model_dtype": "float64",
        },
        "packet_path": str(PACKET.relative_to(ROOT)),
        "packet_manifest_sha256": json.loads((PACKET / "packet_identity.json").read_text())[
            "manifest_sha256"
        ],
        "checkpoints": checkpoint_records,
        "records": records,
    }
    (OUTPUT / "cycle_separability_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    print(canonical_json({
        "output": str(OUTPUT),
        "states": list(records),
        "optimizer_steps_performed": 0,
    }))


if __name__ == "__main__":
    main()
