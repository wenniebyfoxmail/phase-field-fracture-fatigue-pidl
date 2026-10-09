#!/usr/bin/env python3
"""Run the frozen S09-E004 matched operator comparison on Taobo."""
from __future__ import annotations

import argparse
import copy
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
    correction_scale, graph_to_torch, weighted_l2,
)
from s09_fem_physics import boundary, equilibrium
from s09_q4_quadrature import q4_shape_data


SEED = 1
WARMUP_UPDATES = 300
MATCHED_UPDATES = 700
ASSESS_EVERY = 50


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump(path: Path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def git(root: Path, *args) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def load_packet(path: Path):
    with np.load(path, allow_pickle=False) as packet:
        return {key: packet[key] for key in packet.files}


def packet_audit(packet: dict):
    required = {
        "xy": (86756, 2), "conn": (86408, 4), "lumped_area": (86756,),
        "train_d": (16, 86756), "train_u": (16, 86756, 2),
        "train_load": (16,), "train_cycle": (16,),
        "dev_d": (3, 86756), "dev_u": (3, 86756, 2),
        "dev_load": (3,), "dev_cycle": (3,),
    }
    for key, shape in required.items():
        if key not in packet or packet[key].shape != shape:
            raise ValueError(f"packet shape mismatch: {key} expected {shape}")
        if not np.isfinite(packet[key]).all():
            raise ValueError(f"non-finite packet array: {key}")
    if tuple(packet["train_cycle"].tolist()) != (1, 7, 14, 21, 28, 35, 41, 48, 55, 62, 69, 75, 82, 89, 96, 103):
        raise ValueError("training cycle identity mismatch")
    if tuple(packet["dev_cycle"].tolist()) != (76, 82, 83):
        raise ValueError("development cycle identity mismatch")
    if np.any(packet["lumped_area"] <= 0) or not np.isclose(packet["lumped_area"].sum(), 1.0, atol=1e-10):
        raise ValueError("native area identity mismatch")
    scale = correction_scale(
        packet["train_u"], packet["train_load"], packet["xy"], packet["lumped_area"]
    )
    graph = build_graph(packet["xy"], packet["conn"], packet["lumped_area"])
    return scale, graph


def physics_loss(model, damage, load, graph, conn, shape, dshape, det, free, normalizer):
    prediction = model(damage, load, graph)
    force, _ = equilibrium(prediction, damage, conn, shape, dshape, det)
    loss = force[free].square().mean() / normalizer
    return prediction, loss


@torch.no_grad()
def evaluate(model, packet, graph, physics, device):
    area = graph["area"]
    numerators, denominators, states = [], [], []
    fields = []
    for index, cycle in enumerate(packet["dev_cycle"]):
        damage = torch.as_tensor(packet["dev_d"][index], device=device, dtype=torch.float32)
        target = torch.as_tensor(packet["dev_u"][index], device=device, dtype=torch.float32)
        load = float(packet["dev_load"][index])
        prediction = model(damage, load, graph)
        affine = affine_displacement(graph["xy"], load)
        numerator = weighted_l2(prediction, target, area)
        denominator = weighted_l2(affine, target, area)
        force, _ = equilibrium(prediction, damage, *physics)
        affine_force, _ = equilibrium(affine, damage, *physics)
        free = boundary(graph["xy"])
        residual_ratio = torch.sqrt(
            force[free].square().mean() / affine_force[free].square().mean().clamp_min(1e-30)
        )
        numerators.append(numerator)
        denominators.append(denominator)
        states.append({
            "cycle": int(cycle),
            "relative_to_affine": float(numerator / denominator),
            "weighted_error": float(numerator),
            "affine_weighted_error": float(denominator),
            "free_force_rms_ratio_to_affine": float(residual_ratio),
        })
        fields.append((prediction.cpu().numpy(), target.cpu().numpy(), affine.cpu().numpy()))
    aggregate = float(torch.stack(numerators).sum() / torch.stack(denominators).sum())
    return {"R": aggregate, "states": states}, fields


def make_optimizer(model):
    return torch.optim.AdamW(model.parameters(), lr=3e-4)


def train_update(model, optimizer, index, packet, graph, physics, free, affine_normalizer, weight):
    damage = torch.as_tensor(packet["train_d"][index], device=graph["xy"].device, dtype=torch.float32)
    target = torch.as_tensor(packet["train_u"][index], device=graph["xy"].device, dtype=torch.float32)
    load = float(packet["train_load"][index])
    optimizer.zero_grad(set_to_none=True)
    prediction = model(damage, load, graph)
    data_loss = area_mse(prediction / load, target / load, model.correction_scale, graph["area"])
    residual_loss = prediction.new_zeros(())
    if weight:
        force, _ = equilibrium(prediction, damage, *physics)
        residual_loss = force[free].square().mean() / affine_normalizer[index]
    loss = data_loss + weight * residual_loss
    if not torch.isfinite(loss):
        raise FloatingPointError("non-finite training loss")
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 10.0, error_if_nonfinite=True)
    optimizer.step()
    return float(data_loss.detach()), float(residual_loss.detach()), float(loss.detach())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--expected-packet-sha256", required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--expected-commit")
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    if sha256(args.packet) != args.expected_packet_sha256:
        raise RuntimeError("frozen packet identity mismatch")
    packet = load_packet(args.packet)
    scale, graph_np = packet_audit(packet)
    audit = {
        "packet_sha256": args.expected_packet_sha256,
        "correction_scale": scale.tolist(),
        "node_edges": int(graph_np["edges"].shape[1]),
        "coarse_nodes": int(len(graph_np["coarse_area"])),
        "coarse_edges": int(graph_np["coarse_edges"].shape[1]),
        "audit_pass": True,
    }
    if args.audit_only:
        print(json.dumps(audit))
        return

    root = Path(__file__).resolve().parents[1]
    if platform.system() != "Linux" or platform.node() != "GPUServer8":
        raise RuntimeError("Taobo GPUServer8 only; no Mac training")
    if not args.expected_commit or git(root, "rev-parse", "HEAD") != args.expected_commit:
        raise RuntimeError("exact reviewed commit required")
    if git(root, "status", "--porcelain"):
        raise RuntimeError("clean producer checkout required")
    if not os.getenv("CUDA_VISIBLE_DEVICES") or not torch.cuda.is_available():
        raise RuntimeError("explicit healthy CUDA device required")
    if args.out is None or not str(args.out.resolve()).startswith("/mnt/data2/drtao/wennie/"):
        raise RuntimeError("fresh /mnt/data2/drtao/wennie output required")
    args.out.mkdir(parents=True, exist_ok=False)

    device = torch.device("cuda")
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    graph = graph_to_torch(graph_np, device)
    conn = torch.as_tensor(packet["conn"], dtype=torch.long, device=device)
    shape, dshape, det = q4_shape_data(graph["xy"], conn)
    physics = (conn, shape, dshape, det)
    free = boundary(graph["xy"])
    train_d = torch.as_tensor(packet["train_d"], dtype=torch.float32, device=device)
    affine_normalizer = []
    with torch.no_grad():
        for index, load in enumerate(packet["train_load"]):
            affine = affine_displacement(graph["xy"], float(load))
            force, _ = equilibrium(affine, train_d[index], *physics)
            affine_normalizer.append(force[free].square().mean().clamp_min(1e-30))
    affine_normalizer = torch.stack(affine_normalizer)

    started = time.time()
    receipt = {
        "experiment_id": "S09-E004", "run_id": args.out.name,
        "protocol_revision": "v1-equilibrium-operator-prototype",
        "commit": args.expected_commit, "dirty": git(root, "status", "--porcelain"),
        "packet_sha256": args.expected_packet_sha256, "hostname": platform.node(),
        "gpu": os.getenv("CUDA_VISIBLE_DEVICES"), "pid": os.getpid(),
        "command": sys.argv, "started_unix": started, "seed": SEED,
        "warmup_updates": WARMUP_UPDATES, "matched_updates": MATCHED_UPDATES,
        "execution_status": "running", "retrieval": "pending",
    }
    dump(args.out / "receipt.json", receipt)
    dump(args.out / "packet_audit.json", audit)

    sequence = np.random.default_rng(SEED).integers(0, len(packet["train_d"]), size=WARMUP_UPDATES+MATCHED_UPDATES)
    np.save(args.out / "training_sequence.npy", sequence)
    common = EquilibriumOperator(scale, width=32, rank=8).to(device)
    common_optimizer = make_optimizer(common)
    history = []
    try:
        for step, index in enumerate(sequence[:WARMUP_UPDATES], start=1):
            data, residual, total = train_update(
                common, common_optimizer, int(index), packet, graph, physics, free,
                affine_normalizer, 0.0,
            )
            if step % ASSESS_EVERY == 0:
                history.append({"phase": "warmup", "arm": "common", "step": step,
                                "data_loss": data, "physics_loss": residual, "total_loss": total})
        torch.save({"model": common.state_dict(), "optimizer": common_optimizer.state_dict()},
                   args.out / "common_warmup.pt")

        models, optimizers = {}, {}
        for arm in ("data_only", "equilibrium_informed"):
            model = EquilibriumOperator(scale, width=32, rank=8).to(device)
            model.load_state_dict(copy.deepcopy(common.state_dict()))
            optimizer = make_optimizer(model)
            optimizer.load_state_dict(copy.deepcopy(common_optimizer.state_dict()))
            models[arm], optimizers[arm] = model, optimizer

        best = {arm: float("inf") for arm in models}
        for arm in ("data_only", "equilibrium_informed"):
            model, optimizer = models[arm], optimizers[arm]
            for matched_step, index in enumerate(sequence[WARMUP_UPDATES:], start=1):
                weight = 0.0
                if arm == "equilibrium_informed":
                    weight = 0.01 + (0.1-0.01) * (matched_step-1) / (MATCHED_UPDATES-1)
                data, residual, total = train_update(
                    model, optimizer, int(index), packet, graph, physics, free,
                    affine_normalizer, weight,
                )
                if matched_step % ASSESS_EVERY == 0:
                    metrics, _ = evaluate(model, packet, graph, physics, device)
                    row = {"phase": "matched", "arm": arm, "step": matched_step,
                           "data_loss": data, "physics_loss": residual,
                           "physics_weight": weight, "total_loss": total, "development_R": metrics["R"]}
                    history.append(row)
                    print(json.dumps(row), flush=True)
                    if metrics["R"] < best[arm]:
                        best[arm] = metrics["R"]
                        torch.save(model.state_dict(), args.out / f"{arm}_best_diagnostic.pt")
            torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict()},
                       args.out / f"{arm}_final.pt")

        final_metrics, final_fields = {}, {}
        for arm, model in models.items():
            metrics, fields = evaluate(model, packet, graph, physics, device)
            final_metrics[arm] = metrics
            final_fields[arm] = fields
        ratio = final_metrics["equilibrium_informed"]["R"] / final_metrics["data_only"]["R"]
        result = {
            "primary": {
                "criterion": "final R_equilibrium / R_data <= 0.95",
                "ratio": ratio, "threshold": 0.95, "pass": bool(ratio <= 0.95),
            },
            "final": final_metrics,
            "best_diagnostic_R": best,
            "claim_boundary": (
                "Fixed-damage development mapping only; no damage evolution, autonomous rollout, "
                "independent generalization, FEM truth, or real-road validity."
            ),
        }
        dump(args.out / "metrics.json", result)
        arrays = {"xy": packet["xy"], "area": packet["lumped_area"],
                  "cycle": packet["dev_cycle"], "damage": packet["dev_d"]}
        for arm, fields in final_fields.items():
            arrays[f"{arm}_prediction"] = np.stack([item[0] for item in fields])
        arrays["target"] = np.stack([item[1] for item in final_fields["data_only"]])
        arrays["affine"] = np.stack([item[2] for item in final_fields["data_only"]])
        np.savez_compressed(args.out / "final_fields.npz", **arrays)
        receipt.update(execution_status="succeeded", scientific_status=("pass" if ratio <= .95 else "fail"))
    except Exception as error:
        receipt.update(execution_status="failed", error=repr(error))
        raise
    finally:
        if history:
            with (args.out / "history.csv").open("w", newline="") as stream:
                columns = sorted({key for row in history for key in row})
                writer = csv.DictWriter(stream, fieldnames=columns)
                writer.writeheader(); writer.writerows(history)
        receipt.update(elapsed_s=time.time()-started,
                       cuda_peak_memory_bytes=torch.cuda.max_memory_allocated())
        dump(args.out / "receipt.json", receipt)


if __name__ == "__main__":
    main()
