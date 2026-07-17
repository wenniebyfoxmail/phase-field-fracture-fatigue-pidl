#!/usr/bin/env python3
"""Forecast c89 after assimilating only the observed c87 raw driver.

The c87 damage, history, and degradation channels remain model-generated. The
raw tensile-energy channel is replaced by a full-field c87 observation before
the frozen operator forecasts c89. The c89 target is opened only after that
forecast has been produced.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.io import loadmat
import torch


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from evaluate_spatial_degradation_reconstruction_gate import (  # noqa: E402
    FIELD_GATES,
    gate_pass,
)
from run_damage_conditioned_equilibrium_gate import (  # noqa: E402
    metric_row,
    rollout,
)
from run_fem_mechanism_assimilation_gate import checkpoint_model  # noqa: E402
from train_fem_mechanism_mesh_operator import choose_device  # noqa: E402


OBSERVATION_CYCLE = 87
FORECAST_CYCLE = 89
RAW_CHANNEL = 3


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-manifest", type=Path, required=True)
    parser.add_argument("--upstream-predictions", type=Path, required=True)
    parser.add_argument("--c87-raw-observation-mat", type=Path, required=True)
    parser.add_argument("--operator-dataset", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--upstream-method", default="dic_selected_front_translation"
    )
    parser.add_argument("--device", default="auto")
    parser.add_argument("--allow-single-trajectory-diagnostic", action="store_true")
    args = parser.parse_args()
    if not args.allow_single_trajectory_diagnostic:
        parser.error("single-trajectory scope requires explicit acknowledgement")
    return args


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def graph_from_dataset(
    data: np.lib.npyio.NpzFile, device: torch.device
) -> dict[str, torch.Tensor]:
    names = (
        "coordinates",
        "log_area",
        "areas",
        "edge_index",
        "edge_attr",
        "cluster_index",
        "coarse_edge_index",
        "coarse_edge_attr",
    )
    graph = {
        name: torch.from_numpy(np.asarray(data[name])).to(device) for name in names
    }
    graph["edge_index"] = graph["edge_index"].long()
    graph["cluster_index"] = graph["cluster_index"].long()
    graph["coarse_edge_index"] = graph["coarse_edge_index"].long()
    return graph


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    upstream = json.loads(args.upstream_manifest.read_text(encoding="utf-8"))
    if upstream.get("primary_tag") != args.upstream_method:
        raise ValueError("upstream manifest primary method mismatch")
    if upstream.get("primary_full_gate_pass"):
        raise ValueError(
            "upstream already passed; sequential attribution is unnecessary"
        )

    c87_key = f"{args.upstream_method}_c87"
    c89_key = f"{args.upstream_method}_c89"
    with np.load(args.upstream_predictions, allow_pickle=False) as predictions:
        generated_c87 = np.asarray(predictions[c87_key], dtype=np.float32)
        upstream_c89 = np.asarray(predictions[c89_key], dtype=np.float32)

    observation_file = loadmat(
        args.c87_raw_observation_mat, variable_names=("psi_elem",)
    )
    if "psi_elem" not in observation_file:
        raise KeyError("c87 observation MAT lacks psi_elem")
    observed_raw = np.asarray(
        observation_file["psi_elem"], dtype=np.float64
    ).reshape(-1)
    if len(observed_raw) != len(generated_c87):
        raise ValueError("c87 raw observation shape mismatch")
    if np.any(observed_raw < 0.0) or not np.all(np.isfinite(observed_raw)):
        raise ValueError("c87 raw observation is invalid")

    device = choose_device(args.device)
    data = np.load(args.operator_dataset, allow_pickle=False)
    cycles = np.asarray(data["cycles"], dtype=int)
    if not np.array_equal(cycles, np.arange(1, FORECAST_CYCLE + 1)):
        raise ValueError("operator dataset cycle axis mismatch")
    if int(np.asarray(data["trajectory_count"]).item()) != 1:
        raise ValueError("this diagnostic requires exactly one trajectory")
    areas = np.asarray(data["areas"], dtype=np.float64)
    log_floor = float(np.asarray(data["log_floor"]).item())
    graph = graph_from_dataset(data, device)
    model, statistics, checkpoint = checkpoint_model(args.checkpoint, device)
    if checkpoint.get("args", {}).get("model") != "multiscale":
        raise ValueError("checkpoint is not the locked multiscale operator")

    analysis_c87 = generated_c87.copy()
    analysis_c87[:, RAW_CHANNEL] = np.log10(np.maximum(observed_raw, log_floor))
    # The c89 target has not been indexed at this point.
    sequential_c89 = rollout(
        model,
        statistics,
        analysis_c87,
        OBSERVATION_CYCLE,
        FORECAST_CYCLE,
        graph,
        device,
        torch.float32,
    )

    # Post-forecast truth opening for evaluation only.
    target_c89 = np.asarray(data["states"][FORECAST_CYCLE - 1], dtype=np.float32)
    target_c87_raw = np.asarray(
        data["states"][OBSERVATION_CYCLE - 1, :, RAW_CHANNEL], dtype=np.float32
    )
    observation_consistency = float(
        np.max(np.abs(analysis_c87[:, RAW_CHANNEL] - target_c87_raw))
    )
    if observation_consistency > 1.0e-5:
        raise ValueError("MAT and operator-dataset c87 raw fields differ")

    rows = []
    for method, prediction in (
        ("upstream_without_c87_raw_assimilation", upstream_c89),
        ("sequential_c87_raw_assimilation", sequential_c89),
    ):
        row = metric_row(method, FORECAST_CYCLE, prediction, target_c89, areas)
        passed = gate_pass(
            float(row["derived_active_log_mae"]),
            float(row["derived_active_correlation"]),
            float(row["absolute_p99_iou"]),
            float(row["absolute_support_area_ratio"]),
        )
        row.update(
            {
                "phase": "held_out_c89_forecast",
                "observation": (
                    "none"
                    if method == "upstream_without_c87_raw_assimilation"
                    else "full-field c87 raw tensile energy only"
                ),
                "gate_pass": passed,
            }
        )
        rows.append(row)

    result_path = args.out / "sequential_raw_assimilation_metrics.csv"
    write_rows(result_path, rows)
    prediction_path = args.out / "sequential_raw_assimilation_predictions.npz"
    np.savez_compressed(
        prediction_path,
        generated_c87=generated_c87,
        observed_c87_log10_raw=analysis_c87[:, RAW_CHANNEL],
        analysis_c87=analysis_c87,
        upstream_c89=upstream_c89,
        sequential_c89=sequential_c89,
        target_c89=target_c89,
    )
    sequential_row = rows[1]
    manifest = {
        "scope": "single_trajectory_full_field_c87_raw_sequential_assimilation",
        "fem_reference": "eta0 SENS FEM",
        "observation_cycle": OBSERVATION_CYCLE,
        "forecast_cycle": FORECAST_CYCLE,
        "assimilated_channels": ["log10_psi_raw"],
        "unassimilated_channels": ["damage", "alpha_bar", "fatigue_degradation"],
        "c89_target_opened_after_forecast": True,
        "c89_assimilated": False,
        "observation_semantics": (
            "full-field FEM raw tensile energy; in experiments this would require "
            "a DIC strain field plus the declared constitutive split"
        ),
        "observation_consistency_max_abs": observation_consistency,
        "field_gates": FIELD_GATES,
        "c89_gate_pass": bool(sequential_row["gate_pass"]),
        "c89_active_log_mae": float(sequential_row["derived_active_log_mae"]),
        "c89_active_correlation": float(
            sequential_row["derived_active_correlation"]
        ),
        "c89_absolute_p99_iou": float(sequential_row["absolute_p99_iou"]),
        "c89_support_area_ratio": float(
            sequential_row["absolute_support_area_ratio"]
        ),
        "c89_own_p99_iou": float(sequential_row["own_p99_iou"]),
        "trajectory_generalization": False,
        "quarantine": (
            "single FEM trajectory and noiseless full-field FEM observation; "
            "not evidence under sparse/noisy DIC or a new geometry"
        ),
        "input_sha256": {
            "upstream_manifest": sha256(args.upstream_manifest),
            "upstream_predictions": sha256(args.upstream_predictions),
            "c87_raw_observation_mat": sha256(args.c87_raw_observation_mat),
            "operator_dataset": sha256(args.operator_dataset),
            "checkpoint": sha256(args.checkpoint),
        },
        "output_sha256": {
            result_path.name: sha256(result_path),
            prediction_path.name: sha256(prediction_path),
        },
    }
    manifest_path = args.out / "RUN_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), **manifest}, indent=2))


if __name__ == "__main__":
    main()
