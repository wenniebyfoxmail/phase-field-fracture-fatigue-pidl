#!/usr/bin/env python3
"""S09-E005: audit data/physics gradients at the frozen E004 checkpoint."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_equilibrium_operator import (
    EquilibriumOperator, affine_displacement, area_mse, build_graph,
    correction_scale, graph_to_torch,
)
from s09_fem_physics import boundary, equilibrium
from s09_multiobjective import (
    data_anchored_projected_direction, gradient_statistics,
    linearized_changes, normalized_sum_direction, weighted_sum_direction,
)
from s09_q4_quadrature import q4_shape_data


PACKET_SHA256 = "b37a63ccb0e7129ecc3fbe01fc356c93fccc1877b5f34e68fe93265f335109ed"
CHECKPOINT_SHA256 = "1fc1695a87c41cd4a373fa31535dc99be7d91ad01af9a1e11a2986d83af8029e"
E004_INITIAL_WEIGHT = 0.01
E004_FIRST_ASSESSMENT_WEIGHT = 0.01 + (0.1 - 0.01) * 49 / 699
E004_COMMIT = "11fd75d70b18165d6214d50c90adc9c9c9b522a5"
E004_UNCHANGED_PATHS = (
    "SENS_tensile/run_s09_equilibrium_operator.py",
    "source/s09_equilibrium_operator.py",
    "source/s09_fem_physics.py",
    "source/s09_q4_quadrature.py",
)
OUTPUT_ROOT = Path("/mnt/data2/drtao/wennie")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tensor_state_sha256(state) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(state.items()):
        digest.update(name.encode())
        array = value.detach().cpu().contiguous().numpy()
        digest.update(str(array.dtype).encode())
        digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
        digest.update(array.tobytes())
    return digest.hexdigest()


def git(root: Path, *args) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def dump(path: Path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def load_packet(path: Path):
    with np.load(path, allow_pickle=False) as packet:
        return {key: packet[key] for key in packet.files}


def validate_output_path(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(OUTPUT_ROOT):
        raise RuntimeError("output must be contained by /mnt/data2/drtao/wennie")
    if not re.fullmatch(r"S09-E005-R\d{3}_[A-Za-z0-9._-]+", resolved.name):
        raise RuntimeError("output directory must carry a unique S09-E005 Run ID")
    return resolved


def assert_e004_semantics_unchanged(root: Path):
    subprocess.check_call(
        ["git", "diff", "--quiet", E004_COMMIT, "--", *E004_UNCHANGED_PATHS], cwd=root
    )


def checkpoint_step_count(checkpoint) -> int:
    steps = []
    for state in checkpoint["optimizer"]["state"].values():
        if "step" in state:
            steps.append(int(state["step"]))
    if not steps or set(steps) != {300}:
        raise RuntimeError(f"checkpoint is not the exact step-300 optimizer state: {set(steps)}")
    return 300


def audit_losses(model, damage, target, load, graph, physics, free, normalizer):
    """Exact E004 data and physics objectives, exposed for equivalence tests."""
    prediction = model(damage, load, graph)
    data_loss = area_mse(prediction / load, target / load,
                         model.correction_scale, graph["area"])
    force, _ = equilibrium(prediction, damage, *physics)
    physics_loss = force[free].square().mean() / normalizer
    return prediction, force, data_loss, physics_loss


def validate_packet(packet):
    required = {
        "xy": (86756, 2), "conn": (86408, 4), "lumped_area": (86756,),
        "train_d": (16, 86756), "train_u": (16, 86756, 2),
        "train_load": (16,), "train_cycle": (16,),
    }
    for key, shape in required.items():
        if key not in packet or packet[key].shape != shape:
            raise ValueError(f"packet shape mismatch: {key}")
        if not np.isfinite(packet[key]).all():
            raise ValueError(f"non-finite packet array: {key}")
    expected = (1, 7, 14, 21, 28, 35, 41, 48, 55, 62, 69, 75, 82, 89, 96, 103)
    if tuple(packet["train_cycle"].tolist()) != expected:
        raise ValueError("training cycle identity mismatch")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    if platform.system() != "Linux" or platform.node() != "GPUServer8":
        raise RuntimeError("Taobo GPUServer8 only; native audit uses GPU backward passes")
    if git(root, "rev-parse", "HEAD") != args.expected_commit:
        raise RuntimeError("exact reviewed commit required")
    if git(root, "status", "--porcelain"):
        raise RuntimeError("clean producer checkout required")
    if not os.getenv("CUDA_VISIBLE_DEVICES") or not torch.cuda.is_available():
        raise RuntimeError("explicit healthy CUDA device required")
    args.out = validate_output_path(args.out)
    assert_e004_semantics_unchanged(root)
    if sha256(args.packet) != PACKET_SHA256:
        raise RuntimeError("frozen packet identity mismatch")
    checkpoint_file_hash_before = sha256(args.checkpoint)
    if checkpoint_file_hash_before != CHECKPOINT_SHA256:
        raise RuntimeError("frozen checkpoint identity mismatch")
    args.out.mkdir(parents=True, exist_ok=False)

    packet = load_packet(args.packet)
    validate_packet(packet)
    device = torch.device("cuda")
    graph_np = build_graph(packet["xy"], packet["conn"], packet["lumped_area"])
    graph = graph_to_torch(graph_np, device)
    conn = torch.as_tensor(packet["conn"], dtype=torch.long, device=device)
    shape, dshape, det = q4_shape_data(graph["xy"], conn)
    physics = (conn, shape, dshape, det)
    free = boundary(graph["xy"])
    scale = correction_scale(packet["train_u"], packet["train_load"],
                             packet["xy"], packet["lumped_area"])
    model = EquilibriumOperator(scale, width=32, rank=8).to(device)
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=True)
    step = checkpoint_step_count(checkpoint)
    model.load_state_dict(checkpoint["model"])
    model.train()
    stochastic_or_stateful = [module.__class__.__name__ for module in model.modules()
                              if isinstance(module, (torch.nn.Dropout, torch.nn.modules.batchnorm._BatchNorm))]
    if stochastic_or_stateful:
        raise RuntimeError(f"unexpected stochastic/stateful layers: {stochastic_or_stateful}")
    state_hash_before = tensor_state_sha256(model.state_dict())
    named_parameters = list(model.named_parameters())
    parameters = [parameter for _, parameter in named_parameters]

    started = time.time()
    receipt = {
        "experiment_id": "S09-E005", "run_id": args.out.name,
        "protocol_revision": "v1-no-update-gradient-audit",
        "commit": args.expected_commit, "packet_sha256": PACKET_SHA256,
        "checkpoint_sha256": CHECKPOINT_SHA256, "hostname": platform.node(),
        "gpu": os.getenv("CUDA_VISIBLE_DEVICES"), "pid": os.getpid(),
        "command": sys.argv, "started_unix": started,
        "optimizer_updates": 0, "checkpoint_optimizer_step": step,
        "e004_commit": E004_COMMIT, "e004_paths_unchanged": True,
        "training_mode": model.training, "stochastic_or_stateful_layers": [],
        "torch_version": torch.__version__, "cuda_version": torch.version.cuda,
        "cuda_device": torch.cuda.get_device_name(0),
        "optimizer_updates_instrumentation": "no optimizer is constructed; guarded by code review and final state identity",
        "execution_status": "running",
    }
    dump(args.out / "receipt.json", receipt)
    rows = []
    try:
        for index, cycle in enumerate(packet["train_cycle"]):
            damage = torch.as_tensor(packet["train_d"][index], dtype=torch.float32, device=device)
            target = torch.as_tensor(packet["train_u"][index], dtype=torch.float32, device=device)
            load = float(packet["train_load"][index])
            affine = affine_displacement(graph["xy"], load)
            affine_force, _ = equilibrium(affine, damage, *physics)
            affine_force_mse = affine_force[free].square().mean()
            if not torch.isfinite(affine_force_mse) or float(affine_force_mse) <= 0.0:
                raise RuntimeError(f"invalid affine force normalizer for cycle {cycle}")
            normalizer = affine_force_mse
            target_force, _ = equilibrium(target, damage, *physics)
            prediction, force, data_loss, physics_loss = audit_losses(
                model, damage, target, load, graph, physics, free, normalizer)
            data_gradients = torch.autograd.grad(data_loss, parameters, retain_graph=True)
            physics_gradients = torch.autograd.grad(physics_loss, parameters)
            stats = gradient_statistics(named_parameters, data_gradients, physics_gradients)
            projected, projected_metadata = data_anchored_projected_direction(
                data_gradients, physics_gradients)
            directions = {
                "e004_weight_0p01": weighted_sum_direction(
                    data_gradients, physics_gradients, E004_INITIAL_WEIGHT),
                "e004_weight_first_assessment": weighted_sum_direction(
                    data_gradients, physics_gradients, E004_FIRST_ASSESSMENT_WEIGHT),
                "gradient_normalized": normalized_sum_direction(data_gradients, physics_gradients),
                "data_anchored_projected": projected,
            }
            row = {
                "state_index": index, "cycle": int(cycle), "load": load,
                "data_loss": float(data_loss.detach()),
                "physics_loss": float(physics_loss.detach()),
                "affine_force_mse_unclamped": float(affine_force_mse),
                "prediction_force_rms_ratio_to_affine": float(torch.sqrt(physics_loss.detach())),
                "target_force_rms_ratio_to_affine": float(torch.sqrt(
                    target_force[free].square().mean() / normalizer)),
                "gradient": stats,
                "linearized": {name: linearized_changes(data_gradients, physics_gradients, direction)
                               for name, direction in directions.items()},
                "data_anchored_projected_metadata": projected_metadata,
            }
            rows.append(row)
            print(json.dumps({"cycle": int(cycle), "global": stats["global"]}), flush=True)

        required_groups = {"global", "encoder", "local", "coarse", "decoder"}
        complete = len(rows) == 16 and all(set(row["gradient"]) == required_groups for row in rows)
        finite = all(np.isfinite([
            row["data_loss"], row["physics_loss"], row["affine_force_mse_unclamped"],
            row["prediction_force_rms_ratio_to_affine"], row["target_force_rms_ratio_to_affine"],
            *[value for group in row["gradient"].values()
              for key, value in group.items() if key not in {"parameter_tensors", "parameter_coordinates"}],
            *[value for direction in row["linearized"].values() for value in direction.values()],
        ]).all() for row in rows)
        if not complete or not finite:
            raise RuntimeError(f"audit completeness/finite validation failed: complete={complete}, finite={finite}")
        dump(args.out / "gradient_audit.json", {
            "weights": {"initial": E004_INITIAL_WEIGHT,
                        "first_assessment": E004_FIRST_ASSESSMENT_WEIGHT},
            "linearized_change_definition": "first-order change for theta <- theta - lr*direction, per unit lr",
            "states": rows,
        })
        with (args.out / "gradient_audit.csv").open("w", newline="") as stream:
            columns = ["state_index", "cycle", "load", "data_loss", "physics_loss",
                       "affine_force_mse_unclamped",
                       "prediction_force_rms_ratio_to_affine", "target_force_rms_ratio_to_affine",
                       "data_grad_norm", "physics_grad_norm", "physics_to_data_norm", "cosine"]
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                glob = row["gradient"]["global"]
                writer.writerow({
                    **{key: row[key] for key in columns[:8]},
                    "data_grad_norm": glob["data_norm"],
                    "physics_grad_norm": glob["physics_norm"],
                    "physics_to_data_norm": glob["physics_to_data_norm"],
                    "cosine": glob["cosine"],
                })
        state_hash_after = tensor_state_sha256(model.state_dict())
        checkpoint_file_hash_after = sha256(args.checkpoint)
        if state_hash_after != state_hash_before or checkpoint_file_hash_after != checkpoint_file_hash_before:
            raise RuntimeError("no-update identity failed")
        receipt.update(execution_status="succeeded", audited_states=len(rows),
                       model_state_sha256_before=state_hash_before,
                       model_state_sha256_after=state_hash_after,
                       checkpoint_file_sha256_after=checkpoint_file_hash_after,
                       no_update_identity_pass=True, finite_output_pass=bool(finite),
                       completeness_pass=bool(complete), declared_blocks=sorted(required_groups))
    except Exception as error:
        receipt.update(execution_status="failed", error=repr(error))
        raise
    finally:
        receipt.update(elapsed_s=time.time() - started,
                       cuda_peak_memory_bytes=torch.cuda.max_memory_allocated())
        dump(args.out / "receipt.json", receipt)


if __name__ == "__main__":
    main()

