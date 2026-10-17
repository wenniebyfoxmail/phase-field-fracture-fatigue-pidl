#!/usr/bin/env python3
"""Genuine joint field-and-equation optimization sentinel with provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from freeze_select.library import DYNAMIC_TERM_NAMES, build_candidate_library
from freeze_select.schema import validate_frozen_snapshots
from freeze_select.structured_adapter import AdapterConfig, StructuredFieldAdapter
from run_freeze_select_ferrite_adapter_sentinel import sample_observations


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checkpoint_hash(path: Path) -> str:
    return sha256(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cutoff-time", type=float, default=15.0)
    parser.add_argument("--observation-rate", type=float, default=0.20)
    parser.add_argument("--noise-sigma", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--batch-size", type=int, default=8192)
    parser.add_argument("--observation-batch-size", type=int, default=4096)
    parser.add_argument("--field-lr", type=float, default=1e-4)
    parser.add_argument("--beta-lr", type=float, default=5e-3)
    parser.add_argument("--l1", type=float, default=1e-4)
    parser.add_argument("--relative-threshold", type=float, default=0.08)
    parser.add_argument("--device", default="cuda:3")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if args.device.startswith("cuda"):
        torch.cuda.manual_seed_all(args.seed)
    device = torch.device(args.device)

    frame = pd.read_csv(args.input_csv)
    validate_frozen_snapshots(frame, claim_class="tooling-only")
    cutoff = frame[frame["time"] <= args.cutoff_time].copy().reset_index(drop=True)
    future_rows_excluded = int((frame["time"] > args.cutoff_time).sum())
    observations, observation_hash = sample_observations(
        cutoff, args.observation_rate, args.seed
    )

    query_designs: list[np.ndarray] = []
    query_frames: list[pd.DataFrame] = []
    query_trajectory: list[np.ndarray] = []
    observation_designs: list[np.ndarray] = []
    observation_targets: list[np.ndarray] = []
    observation_trajectory: list[np.ndarray] = []
    coefficients: list[np.ndarray] = []
    adapter_manifests: list[dict[str, object]] = []

    for trajectory_index, (trajectory_id, block) in enumerate(
        cutoff.groupby("trajectory_id", sort=True)
    ):
        block = block.copy().sort_values(["time", "cell_id"]).reset_index(drop=True)
        observed_source = observations[observations["trajectory_id"] == trajectory_id]
        observed = observed_source[["x", "y", "time", "d"]].copy()
        scale = max(float(np.quantile(np.abs(block["d"].to_numpy(float)), 0.95)), 1e-8)
        rng = np.random.default_rng(args.seed + 101 * trajectory_index)
        noisy = np.clip(
            observed["d"].to_numpy(float)
            + rng.normal(0.0, args.noise_sigma * scale, len(observed)),
            0.0,
            1.0,
        )
        observed["value"] = noisy
        localized = observed_source[observed_source["d"] >= 0.5]
        if localized.empty:
            center_x = float(observed_source["x"].mean())
            center_y = float(observed_source["y"].mean())
        else:
            center_x = float(localized["x"].mean())
            center_y = float(localized["y"].mean())
        temporal_basis = max(4, min(7, int(block["time"].nunique())))
        config = AdapterConfig(
            x_modes=8,
            y_modes=6,
            temporal_basis=temporal_basis,
            spline_degree=min(3, temporal_basis - 1),
            ridge=1e-7,
            defect_center_x=center_x,
            defect_center_y=center_y,
            defect_scales=(0.02, 0.05, 0.10, 0.20),
            wheelpath_scales=(0.08, 0.20),
        )
        adapter = StructuredFieldAdapter(config, cutoff_time=args.cutoff_time)
        adapter.fit(observed, value_column="value")
        query_designs.append(adapter._design(block).astype(np.float32))
        observation_designs.append(adapter._design(observed).astype(np.float32))
        observation_targets.append(noisy.astype(np.float32))
        query_frames.append(block)
        query_trajectory.append(np.full(len(block), trajectory_index, dtype=np.int64))
        observation_trajectory.append(np.full(len(observed), trajectory_index, dtype=np.int64))
        coefficients.append(np.asarray(adapter._coefficient, dtype=np.float32))
        adapter_manifests.append({"trajectory_id": str(trajectory_id), **adapter.manifest()})

    joint_frame = pd.concat(query_frames, ignore_index=True)
    zero_damage_frame = joint_frame.copy()
    zero_damage_frame["d"] = 0.0
    independent_library = build_candidate_library(
        zero_damage_frame, term_names=DYNAMIC_TERM_NAMES
    ).to_numpy(np.float32)
    library_scale = np.sqrt(np.mean(np.square(independent_library), axis=0))
    library_scale[library_scale <= np.finfo(np.float32).eps] = 1.0
    independent_library /= library_scale
    residual_target = -joint_frame["known_residual"].to_numpy(np.float32)

    query_design = torch.as_tensor(np.concatenate(query_designs), device=device)
    query_trajectory_tensor = torch.as_tensor(np.concatenate(query_trajectory), device=device)
    observation_design = torch.as_tensor(np.concatenate(observation_designs), device=device)
    observation_trajectory_tensor = torch.as_tensor(
        np.concatenate(observation_trajectory), device=device
    )
    observation_target = torch.as_tensor(np.concatenate(observation_targets), device=device)
    library = torch.as_tensor(independent_library, device=device)
    residual = torch.as_tensor(residual_target, device=device)

    initial_coefficient = np.stack(coefficients)
    field_coefficient = torch.nn.Parameter(torch.as_tensor(initial_coefficient, device=device))
    beta_scaled = torch.nn.Parameter(torch.zeros(len(DYNAMIC_TERM_NAMES), device=device))
    optimizer = torch.optim.Adam(
        [
            {"params": [field_coefficient], "lr": args.field_lr},
            {"params": [beta_scaled], "lr": args.beta_lr},
        ]
    )
    observation_scale = max(float(np.quantile(np.abs(np.concatenate(observation_targets)), 0.95)), 0.05)
    residual_scale = max(float(np.sqrt(np.mean(np.square(residual_target)))), 1e-6)

    init_path = args.output_dir / "checkpoint_init.pt"
    torch.save(
        {
            "field_coefficient": field_coefficient.detach().cpu(),
            "beta_scaled": beta_scaled.detach().cpu(),
            "seed": args.seed,
            "observation_ids_sha256": observation_hash,
        },
        init_path,
    )

    rng = np.random.default_rng(args.seed + 9001)
    history: list[dict[str, object]] = []
    for step in range(args.steps + 1):
        query_index = torch.as_tensor(
            rng.integers(0, len(query_design), size=min(args.batch_size, len(query_design))),
            device=device,
        )
        observation_index = torch.as_tensor(
            rng.integers(
                0,
                len(observation_design),
                size=min(args.observation_batch_size, len(observation_design)),
            ),
            device=device,
        )
        query_coefficient = field_coefficient[query_trajectory_tensor[query_index]]
        d_query = torch.sum(query_design[query_index] * query_coefficient, dim=1)
        observation_coefficient = field_coefficient[
            observation_trajectory_tensor[observation_index]
        ]
        d_observation = torch.sum(
            observation_design[observation_index] * observation_coefficient, dim=1
        )
        theta = (1.0 - d_query).unsqueeze(1) * library[query_index]
        residual_prediction = theta @ beta_scaled
        observation_loss = torch.mean(
            torch.square((d_observation - observation_target[observation_index]) / observation_scale)
        )
        equation_loss = torch.mean(
            torch.square((residual_prediction - residual[query_index]) / residual_scale)
        )
        bound_loss = torch.mean(torch.relu(-d_query) ** 2 + torch.relu(d_query - 1.0) ** 2)
        sparsity_loss = args.l1 * torch.sum(torch.abs(beta_scaled)) / residual_scale
        loss = observation_loss + equation_loss + 0.1 * bound_loss + sparsity_loss
        if not torch.isfinite(loss):
            raise FloatingPointError(f"Non-finite loss at step {step}")
        if step < args.steps:
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
        if step % 25 == 0 or step == args.steps:
            beta_now = beta_scaled.detach().cpu().numpy()
            peak = float(np.max(np.abs(beta_now)))
            support = [
                name
                for name, value in zip(DYNAMIC_TERM_NAMES, beta_now)
                if peak > 0.0 and abs(float(value)) >= args.relative_threshold * peak
            ]
            history.append(
                {
                    "step": step,
                    "loss": float(loss.detach().cpu()),
                    "observation_loss": float(observation_loss.detach().cpu()),
                    "equation_loss": float(equation_loss.detach().cpu()),
                    "bound_loss": float(bound_loss.detach().cpu()),
                    "sparsity_loss": float(sparsity_loss.detach().cpu()),
                    "support": "|".join(support),
                }
            )

    final_path = args.output_dir / "checkpoint_final.pt"
    torch.save(
        {
            "field_coefficient": field_coefficient.detach().cpu(),
            "beta_scaled": beta_scaled.detach().cpu(),
            "seed": args.seed,
            "observation_ids_sha256": observation_hash,
        },
        final_path,
    )
    pd.DataFrame(history).to_csv(args.output_dir / "training_history.csv", index=False)

    with torch.no_grad():
        final_d = torch.sum(
            query_design * field_coefficient[query_trajectory_tensor], dim=1
        ).clamp(0.0, 1.0).cpu().numpy()
    field_change = float(
        torch.linalg.vector_norm(
            field_coefficient.detach().cpu() - torch.as_tensor(initial_coefficient)
        )
    )
    beta_final_scaled = beta_scaled.detach().cpu().numpy()
    beta_physical = beta_final_scaled / library_scale
    peak = float(np.max(np.abs(beta_final_scaled)))
    support = [
        name
        for name, value in zip(DYNAMIC_TERM_NAMES, beta_final_scaled)
        if peak > 0.0 and abs(float(value)) >= args.relative_threshold * peak
    ]
    final_field_path = args.output_dir / "joint_final_field.npz"
    np.savez_compressed(final_field_path, d=final_d)
    metrics = {
        "protocol_id": "genuine_joint_structured_field_point_residual_v1",
        "claim_class": "tooling-only_semisynthetic_joint_baseline",
        "input_sha256": sha256(args.input_csv),
        "code_sha256": sha256(Path(__file__)),
        "observation_ids_sha256": observation_hash,
        "observation_rate": args.observation_rate,
        "noise_sigma": args.noise_sigma,
        "cutoff_time": args.cutoff_time,
        "future_rows_excluded": future_rows_excluded,
        "future_damage_access": False,
        "field_frozen_during_optimization": False,
        "field_and_beta_same_optimizer": True,
        "steps": args.steps,
        "field_lr": args.field_lr,
        "beta_lr": args.beta_lr,
        "l1": args.l1,
        "relative_threshold": args.relative_threshold,
        "field_parameter_change_l2": field_change,
        "beta_parameter_change_l2": float(np.linalg.norm(beta_final_scaled)),
        "stable_support_not_applicable": True,
        "final_support": support,
        "final_beta_physical": dict(zip(DYNAMIC_TERM_NAMES, map(float, beta_physical))),
        "median_d_rmse": float(
            np.median(
                [
                    np.sqrt(np.mean(np.square(final_d[index] - joint_frame.loc[index, "d"].to_numpy(float))))
                    for _, index in joint_frame.groupby("snapshot_id", sort=False).groups.items()
                ]
            )
        ),
        "checkpoint_init_sha256": checkpoint_hash(init_path),
        "checkpoint_final_sha256": checkpoint_hash(final_path),
        "training_history_sha256": sha256(args.output_dir / "training_history.csv"),
        "joint_final_field_sha256": sha256(final_field_path),
        "adapter_manifests": adapter_manifests,
        "final_losses": history[-1],
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
