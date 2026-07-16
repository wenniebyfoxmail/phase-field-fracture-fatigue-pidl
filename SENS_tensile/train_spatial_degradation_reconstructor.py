#!/usr/bin/env python3
"""Train a sealed pointwise or one-ring c86 degradation reconstructor.

Model selection uses only c76-c80.  c81-c85 are opened after checkpoint
selection as chronological audits.  The output c86 reconstruction is written
and hashed without any c86 diffuse target in the input dataset.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import sys
import time

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "source"))

from spatial_degradation_reconstruction import (  # noqa: E402
    OneRingDegradationReconstructor,
    PointwiseDegradationReconstructor,
    Z_MAX,
    damage_to_z,
    matched_pointwise_width,
    parameter_count,
    reconstruct_damage,
    reconstruction_loss,
)


TRAIN_END = 75
VALIDATION_CYCLES = (76, 77, 78, 79, 80)
AUDIT_CYCLES = (81, 82, 83, 84, 85)
SEALED_CYCLE = 86


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def choose_device(name: str) -> torch.device:
    if name != "auto":
        return torch.device(name)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", choices=("pointwise", "one_ring"), required=True)
    parser.add_argument("--graph-hidden", type=int, default=64)
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--eval-every", type=int, default=100)
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--lr", type=float, default=3.0e-4)
    parser.add_argument("--weight-decay", type=float, default=1.0e-6)
    parser.add_argument("--grad-clip", type=float, default=5.0)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--allow-single-trajectory-diagnostic", action="store_true")
    args = parser.parse_args()
    if not args.allow_single_trajectory_diagnostic:
        parser.error(
            "pass --allow-single-trajectory-diagnostic for this sealed diagnostic"
        )
    if args.steps < 1 or args.eval_every < 1 or args.patience < 1:
        parser.error("steps, eval-every, and patience must be positive")
    return args


def cycle_indices(
    cycles: np.ndarray, selected: tuple[int, ...] | list[int]
) -> list[int]:
    lookup = {int(cycle): index for index, cycle in enumerate(cycles)}
    missing = sorted(set(selected) - set(lookup))
    if missing:
        raise ValueError(f"dataset lacks cycles: {missing}")
    return [lookup[int(cycle)] for cycle in selected]


def weighted_metrics(
    prediction_damage: np.ndarray,
    prediction_z: np.ndarray,
    target_damage: np.ndarray,
    prior_damage: np.ndarray,
    core: np.ndarray,
    areas: np.ndarray,
) -> dict[str, float]:
    weights = np.asarray(areas, dtype=np.float64)
    weights /= weights.sum()
    target_z = np.asarray(damage_to_z(target_damage), dtype=np.float64)
    prior_z = np.asarray(damage_to_z(prior_damage), dtype=np.float64)
    increment = target_z - prior_z
    noncore = ~np.asarray(core, bool)
    process = (increment > 1.0e-4) & noncore
    noncore_weights = weights[noncore]
    noncore_weights /= noncore_weights.sum()
    result = {
        "z_mae": float(
            np.sum(noncore_weights * np.abs(prediction_z[noncore] - target_z[noncore]))
        ),
        "z_rmse": float(
            np.sqrt(
                np.sum(
                    noncore_weights * (prediction_z[noncore] - target_z[noncore]) ** 2
                )
            )
        ),
        "damage_mae": float(
            np.sum(
                noncore_weights
                * np.abs(prediction_damage[noncore] - target_damage[noncore])
            )
        ),
        "damage_rmse": float(
            np.sqrt(
                np.sum(
                    noncore_weights
                    * (prediction_damage[noncore] - target_damage[noncore]) ** 2
                )
            )
        ),
        "core_recall_d095": float(
            np.mean(prediction_damage[np.asarray(core, bool)] >= 0.95)
        ),
    }
    if np.any(process):
        process_weights = weights[process]
        process_weights /= process_weights.sum()
        result["process_z_mae"] = float(
            np.sum(process_weights * np.abs(prediction_z[process] - target_z[process]))
        )
    else:
        result["process_z_mae"] = 0.0
    result["selection_score"] = (
        result["z_mae"] + 2.0 * result["damage_rmse"] + result["process_z_mae"]
    )
    return result


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("cannot write an empty metric table")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    device = choose_device(args.device)
    data = np.load(args.dataset, allow_pickle=False)
    if int(np.asarray(data["hidden_target_max_cycle"]).item()) != 85:
        raise ValueError("training dataset must contain no hidden target after c85")
    if int(np.asarray(data["sealed_prediction_cycle"]).item()) != SEALED_CYCLE:
        raise ValueError("training dataset must contain a sealed c86 feature row")

    cycles = np.asarray(data["target_cycles"], dtype=int)
    features_np = np.asarray(data["features"], dtype=np.float32)
    targets_np = np.asarray(data["target_capacity_fraction"], dtype=np.float32)
    damage_np = np.asarray(data["target_damage"], dtype=np.float32)
    cores_np = np.asarray(data["visible_core"], dtype=bool)
    areas_np = np.asarray(data["areas"], dtype=np.float32)
    train_indices = np.flatnonzero(cycles <= TRAIN_END)
    validation_indices = cycle_indices(cycles, VALIDATION_CYCLES)
    audit_indices = cycle_indices(cycles, AUDIT_CYCLES)
    if int(cycles[train_indices].max()) != TRAIN_END:
        raise ValueError("training split does not end at c75")

    # Statistics are computed from c5-c75 only.  No validation, audit, or c86
    # feature participates in normalization.
    train_features = features_np[train_indices]
    feature_mean = train_features.mean(axis=(0, 1), dtype=np.float64).astype(np.float32)
    feature_std = train_features.std(axis=(0, 1), dtype=np.float64).astype(np.float32)
    feature_std = np.maximum(feature_std, 1.0e-6)
    del train_features

    features = torch.from_numpy((features_np - feature_mean) / feature_std).to(device)
    targets = torch.from_numpy(targets_np).to(device)
    target_damage = torch.from_numpy(damage_np).to(device)
    cores = torch.from_numpy(cores_np).to(device)
    areas = torch.from_numpy(areas_np).to(device)
    edge_index = torch.from_numpy(np.asarray(data["edge_index"], dtype=np.int64)).to(
        device
    )
    edge_attr = torch.from_numpy(np.asarray(data["edge_attr"], dtype=np.float32)).to(
        device
    )
    input_dim = int(features.shape[-1])

    pointwise_width, pointwise_count, graph_count = matched_pointwise_width(
        input_dim, args.graph_hidden
    )
    if args.model == "pointwise":
        model = PointwiseDegradationReconstructor(input_dim, pointwise_width)
    else:
        model = OneRingDegradationReconstructor(input_dim, args.graph_hidden)
    model = model.to(device)
    actual_count = parameter_count(model)
    mismatch = abs(pointwise_count - graph_count) / graph_count
    if mismatch > 0.02:
        raise RuntimeError(
            f"pointwise/graph parameter mismatch is too large: {mismatch:.3%}"
        )

    def predict(index: int) -> tuple[torch.Tensor, torch.Tensor]:
        raw = model(features[index], edge_index, edge_attr)
        prior = torch.from_numpy(features_np[index, :, 0]).to(device)
        return reconstruct_damage(prior, raw, core_mask=cores[index])

    def validation_score() -> tuple[float, list[dict[str, float]]]:
        model.eval()
        rows = []
        with torch.no_grad():
            for index in validation_indices:
                pred_damage, pred_z = predict(index)
                row = weighted_metrics(
                    pred_damage.cpu().numpy(),
                    pred_z.cpu().numpy(),
                    damage_np[index],
                    features_np[index, :, 0],
                    cores_np[index],
                    areas_np,
                )
                rows.append(row)
        return float(np.mean([row["selection_score"] for row in rows])), rows

    args.out.mkdir(parents=True, exist_ok=True)
    best_path = args.out / "best_model.pt"
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.lr, weight_decay=args.weight_decay
    )
    generator = random.Random(args.seed)
    history = []
    best_score = float("inf")
    stale = 0
    started = time.time()
    for step in range(1, args.steps + 1):
        model.train()
        index = int(generator.choice(train_indices.tolist()))
        optimizer.zero_grad(set_to_none=True)
        pred_damage, pred_z = predict(index)
        prior_z = damage_to_z(torch.from_numpy(features_np[index, :, 0]).to(device))
        target_z = prior_z + (Z_MAX - prior_z) * targets[index]
        loss = reconstruction_loss(
            pred_damage,
            pred_z,
            target_damage[index],
            target_z,
            prior_z,
            cores[index],
            areas,
            edge_index,
        )
        loss.total.backward()
        gradient_norm = float(
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
            .detach()
            .cpu()
        )
        optimizer.step()
        if not torch.isfinite(loss.total):
            raise FloatingPointError(f"non-finite loss at step {step}")

        if step == 1 or step % args.eval_every == 0 or step == args.steps:
            score, validation_rows = validation_score()
            row = {
                "step": step,
                "train_cycle": int(cycles[index]),
                "train_total": float(loss.total.detach().cpu()),
                "train_degradation": float(loss.degradation.detach().cpu()),
                "train_damage": float(loss.damage.detach().cpu()),
                "train_core": float(loss.core.detach().cpu()),
                "train_gradient": float(loss.gradient.detach().cpu()),
                "gradient_norm": gradient_norm,
                "validation_score": score,
                "elapsed_seconds": time.time() - started,
            }
            history.append(row)
            print(json.dumps(row), flush=True)
            if score < best_score:
                best_score = score
                stale = 0
                torch.save(
                    {
                        "model": model.state_dict(),
                        "model_type": args.model,
                        "input_dim": input_dim,
                        "graph_hidden": args.graph_hidden,
                        "pointwise_width": pointwise_width,
                        "feature_mean": torch.from_numpy(feature_mean),
                        "feature_std": torch.from_numpy(feature_std),
                        "best_validation_score": best_score,
                        "validation_rows": validation_rows,
                        "split": {
                            "train": "c5-c75",
                            "validation": list(VALIDATION_CYCLES),
                            "audit": list(AUDIT_CYCLES),
                            "sealed_prediction": SEALED_CYCLE,
                        },
                    },
                    best_path,
                )
            else:
                stale += 1
                if stale >= args.patience:
                    print(
                        f"early stop after {stale} stale validation checks", flush=True
                    )
                    break

    write_rows(args.out / "training_history.csv", history)
    checkpoint = torch.load(best_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model"])
    model.eval()

    audit_rows: list[dict[str, object]] = []
    with torch.no_grad():
        for split, indices in (
            ("validation", validation_indices),
            ("audit", audit_indices),
        ):
            for index in indices:
                pred_damage, pred_z = predict(index)
                metrics = weighted_metrics(
                    pred_damage.cpu().numpy(),
                    pred_z.cpu().numpy(),
                    damage_np[index],
                    features_np[index, :, 0],
                    cores_np[index],
                    areas_np,
                )
                audit_rows.append(
                    {"split": split, "cycle": int(cycles[index]), **metrics}
                )
    write_rows(args.out / "prelock_metrics.csv", audit_rows)

    sealed_features_np = np.asarray(data["sealed_c86_features"], dtype=np.float32)
    sealed_features = torch.from_numpy(
        (sealed_features_np - feature_mean) / feature_std
    ).to(device)
    sealed_prior_np = np.asarray(data["sealed_c86_prior_damage"], dtype=np.float32)
    sealed_prior = torch.from_numpy(sealed_prior_np).to(device)
    with torch.no_grad():
        sealed_raw = model(sealed_features, edge_index, edge_attr)
        sealed_core = torch.from_numpy(
            np.asarray(data["sealed_c86_visible_core"], dtype=bool)
        ).to(device)
        sealed_damage, sealed_z = reconstruct_damage(
            sealed_prior, sealed_raw, core_mask=sealed_core
        )
    reconstruction_path = args.out / "sealed_c86_reconstruction.npz"
    np.savez_compressed(
        reconstruction_path,
        cycle=np.asarray(SEALED_CYCLE, dtype=np.int16),
        element_damage=sealed_damage.cpu().numpy().astype(np.float32),
        element_z=sealed_z.cpu().numpy().astype(np.float32),
        prior_element_damage=sealed_prior_np,
        visible_core=np.asarray(data["sealed_c86_visible_core"], dtype=np.uint8),
        model=np.asarray(args.model),
        feature_names=np.asarray(data["feature_names"]),
    )
    lock = {
        "model": args.model,
        "dataset_sha256": sha256(args.dataset),
        "checkpoint_sha256": sha256(best_path),
        "reconstruction_sha256": sha256(reconstruction_path),
        "training_targets": "c5-c75",
        "selection_targets": "c76-c80",
        "post_selection_audit_targets": "c81-c85",
        "sealed_prediction_cycle": SEALED_CYCLE,
        "c86_hidden_damage_opened": False,
        "c87_c89_targets_opened": False,
        "parameter_count": actual_count,
        "matched_pointwise_parameter_count": pointwise_count,
        "one_ring_parameter_count": graph_count,
        "parameter_mismatch_fraction": mismatch,
        "best_validation_score": best_score,
    }
    lock_path = args.out / "SEALED_C86_RECONSTRUCTION.json"
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    manifest = {
        **lock,
        "claim_class": "observable-conditioned hidden-state identification",
        "trajectory_generalization": False,
        "device": str(device),
        "seed": args.seed,
        "feature_normalization": "c5-c75 only",
        "target": "bounded irreversible z=-log10((1-d)^2) increment",
        "primary_assets": [
            best_path.name,
            "training_history.csv",
            "prelock_metrics.csv",
            reconstruction_path.name,
            lock_path.name,
        ],
    }
    (args.out / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
