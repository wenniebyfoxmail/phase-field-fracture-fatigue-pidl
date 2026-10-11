#!/usr/bin/env python3
"""S09-E005: audit data/physics gradients at the frozen E004 checkpoint."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
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
    if not str(args.out.resolve()).startswith("/mnt/data2/drtao/wennie/"):
        raise RuntimeError("fresh /mnt/data2/drtao/wennie output required")
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
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model"])
    model.train()
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
        "optimizer_updates": 0, "execution_status": "running",
    }
    dump(args.out / "receipt.json", receipt)
    rows = []
    try:
        for index, cycle in enumerate(packet["train_cycle"]):
            damage = torch.as_tensor(packet["train_d"][index], dtype=torch.float32, device=device)
            target = torch.as_tensor(packet["train_u"][index], dtype=torch.float32, device=device)
            load = float(packet["train_load"][index])
            prediction = model(damage, load, graph)
            affine = affine_displacement(graph["xy"], load)
            affine_force, _ = equilibrium(affine, damage, *physics)
            normalizer = affine_force[free].square().mean().clamp_min(1e-30)
            force, _ = equilibrium(prediction, damage, *physics)
            target_force, _ = equilibrium(target, damage, *physics)
            data_loss = area_mse(prediction / load, target / load,
                                 model.correction_scale, graph["area"])
            physics_loss = force[free].square().mean() / normalizer
            data_gradients = torch.autograd.grad(data_loss, parameters, retain_graph=True)
            physics_gradients = torch.autograd.grad(physics_loss, parameters)
            stats = gradient_statistics(named_parameters, data_gradients, physics_gradients)
            directions = {
                "e004_weight_0p01": weighted_sum_direction(
                    data_gradients, physics_gradients, E004_INITIAL_WEIGHT),
                "e004_weight_first_assessment": weighted_sum_direction(
                    data_gradients, physics_gradients, E004_FIRST_ASSESSMENT_WEIGHT),
                "gradient_normalized": normalized_sum_direction(data_gradients, physics_gradients),
                "data_anchored_projected": data_anchored_projected_direction(
                    data_gradients, physics_gradients),
            }
            row = {
                "state_index": index, "cycle": int(cycle), "load": load,
                "data_loss": float(data_loss.detach()),
                "physics_loss": float(physics_loss.detach()),
                "prediction_force_rms_ratio_to_affine": float(torch.sqrt(physics_loss.detach())),
                "target_force_rms_ratio_to_affine": float(torch.sqrt(
                    target_force[free].square().mean() / normalizer)),
                "gradient": stats,
                "linearized": {name: linearized_changes(data_gradients, physics_gradients, direction)
                               for name, direction in directions.items()},
            }
            rows.append(row)
            print(json.dumps({"cycle": int(cycle), "global": stats["global"]}), flush=True)

        dump(args.out / "gradient_audit.json", {
            "weights": {"initial": E004_INITIAL_WEIGHT,
                        "first_assessment": E004_FIRST_ASSESSMENT_WEIGHT},
            "linearized_change_definition": "first-order change for theta <- theta - lr*direction, per unit lr",
            "states": rows,
        })
        with (args.out / "gradient_audit.csv").open("w", newline="") as stream:
            columns = ["state_index", "cycle", "load", "data_loss", "physics_loss",
                       "prediction_force_rms_ratio_to_affine", "target_force_rms_ratio_to_affine",
                       "data_grad_norm", "physics_grad_norm", "physics_to_data_norm", "cosine"]
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                glob = row["gradient"]["global"]
                writer.writerow({
                    **{key: row[key] for key in columns[:7]},
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
                       no_update_identity_pass=True)
    except Exception as error:
        receipt.update(execution_status="failed", error=repr(error))
        raise
    finally:
        receipt.update(elapsed_s=time.time() - started,
                       cuda_peak_memory_bytes=torch.cuda.max_memory_allocated())
        dump(args.out / "receipt.json", receipt)


if __name__ == "__main__":
    main()

