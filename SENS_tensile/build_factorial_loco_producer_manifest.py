#!/usr/bin/env python3
"""Build the sealed 1%-matched 4-fold factorial LOCO producer matrix."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from fem_multitrajectory_contract_adapter import (  # noqa: E402
    ADAPTER_ID,
    AGENT2_COMMIT,
    EXPECTED_LOCO_LOCK_SHA256,
    SCHEMA_ID,
    load_agent2_factorial_loco_contract,
)
from temporal_mesh_operator import (  # noqa: E402
    TemporalMeshOperator,
    count_parameters,
    parameter_breakdown,
)


MODEL_CONFIGS = {
    "markov": {"context": 1, "temporal_width": 463},
    "tcn": {"context": 3, "temporal_width": 334},
    "transformer": {"context": 3, "temporal_width": 124},
}
LOCAL_DIM = 49
TOKEN_DIM = 50
METADATA_DIM = 2
TARGET = 329_000
TOLERANCE = 0.01
SEEDS = (1, 2, 3)
STEPS = 3000


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_agent2_factorial_loco_contract(args.contract)
    split = json.loads(args.split.read_text(encoding="utf-8"))
    if split.get("lock_sha256") != EXPECTED_LOCO_LOCK_SHA256:
        raise ValueError("LOCO split lock differs from frozen Agent2 contract")
    trajectory_ids = {record.trajectory_id for record in records}

    capacity_rows = []
    model_specs = {}
    for family, config in MODEL_CONFIGS.items():
        model = TemporalMeshOperator(
            temporal_family=family,
            metadata_dim=METADATA_DIM,
            local_dim=LOCAL_DIM,
            token_dim=TOKEN_DIM,
            temporal_width=config["temporal_width"],
            max_context=config["context"],
            transformer_heads=4,
        )
        parameters = count_parameters(model)
        relative_error = abs(parameters - TARGET) / TARGET
        if relative_error > TOLERANCE:
            raise ValueError(f"{family} fails 1% parameter gate")
        model_specs[family] = {
            **config,
            "local_dim": LOCAL_DIM,
            "token_dim": TOKEN_DIM,
            "metadata_dim": METADATA_DIM,
            "transformer_heads": 4,
            "parameter_count": parameters,
            "parameter_breakdown": parameter_breakdown(model),
            "relative_error": relative_error,
        }
        capacity_rows.append(
            {
                "family": family,
                "ranking_role": "formal_control" if family == "markov" else "finite_candidate",
                "context": config["context"],
                "local_dim": LOCAL_DIM,
                "token_dim": TOKEN_DIM,
                "temporal_width": config["temporal_width"],
                "transformer_heads": 4 if family == "transformer" else "not_applicable",
                "metadata_dim": METADATA_DIM,
                "parameter_count": parameters,
                "target": TARGET,
                "relative_error": f"{relative_error:.12g}",
                "within_one_percent": "true",
            }
        )

    jobs = []
    for fold in split["folds"]:
        train = tuple(fold["train_trajectory_ids"])
        test = tuple(fold["test_trajectory_ids"])
        if set(train) | set(test) != trajectory_ids or set(train) & set(test):
            raise ValueError("producer fold crosses the frozen trajectory inventory")
        for family, spec in model_specs.items():
            for seed in SEEDS:
                job_id = f"{fold['fold_id'].split('::')[-1]}__{family}__seed{seed}"
                jobs.append(
                    {
                        "job_id": job_id,
                        "fold_id": fold["fold_id"],
                        "train_trajectory_ids": list(train),
                        "held_out_trajectory_id": test[0],
                        "family": family,
                        "seed": seed,
                        "context": spec["context"],
                        "steps": STEPS,
                        "parameter_count": spec["parameter_count"],
                        "status": "producer_ready_not_launched",
                    }
                )

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "parameter_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(capacity_rows[0]))
        writer.writeheader()
        writer.writerows(capacity_rows)
    manifest = {
        "manifest_id": "factorial_loco_graph_temporal_v1",
        "status": "producer_ready_not_launched",
        "agent2_commit": AGENT2_COMMIT,
        "contract_path": str(args.contract.resolve()),
        "contract_file_sha256": sha256_file(args.contract),
        "producer_schema_id": SCHEMA_ID,
        "producer_adapter_id": ADAPTER_ID,
        "loco_split_path": str(args.split.resolve()),
        "loco_split_file_sha256": sha256_file(args.split),
        "loco_internal_lock_sha256": EXPECTED_LOCO_LOCK_SHA256,
        "claim_scope": "within-Hard5 shared-geometry numerical factorial only",
        "claim_blocks": [
            "independent roads",
            "road-like LOTO",
            "real-road validation",
            "geometry generalization",
            "material generalization",
            "calibrated hazard/RUL",
        ],
        "models": model_specs,
        "optimizer": {"name": "AdamW", "lr": 0.0003, "weight_decay": 1e-6},
        "loss": "shared temporal_mechanism_loss, 3-step autoregressive exposure",
        "steps": STEPS,
        "seeds": list(SEEDS),
        "job_count": len(jobs),
        "jobs": jobs,
        "risk_heads": "absent; calibrated hazard/RUL unavailable",
    }
    (args.out / "producer_experiment_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"jobs": len(jobs), "parameter_gate": "PASS"}))


if __name__ == "__main__":
    main()

