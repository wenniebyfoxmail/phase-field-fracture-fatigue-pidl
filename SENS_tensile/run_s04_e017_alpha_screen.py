#!/usr/bin/env python3
"""S04-E017 two-state unbiased damage-stratified supervised repair screen."""
from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import shutil
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

from run_s04_e013_stage1_supervised import (
    EXPECTED as ALL_EXPECTED,
    SAMPLE_SEED_OFFSET,
    US,
    apply_sens_bc,
    build_model,
    final_metrics,
    normalize_xy,
    predict_in_chunks,
    sha256,
    REQUIRED, boundary_masks, q4_strain, residual_metrics,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_REVISION = "20261012-r1-alpha-screen"
EXPECTED = {state: ALL_EXPECTED[state] for state in ("c20s4", "c60s4", "c83s4")}
EXPECTED["c40s4"] = "64c5fd2ff16cc2588d723854edff25c288bc0bfa708f7dc3f17f4e5374460e7c"
ALLOCATIONS = {"0.5": (8192, 8192), "0.7": (11469, 4915), "0.9": (14746, 1638)}
SEEDS = (7,)
STEPS = 10_000
BATCH_NODES = 16_384
DAMAGE_THRESHOLD = 0.1
MONITOR_STEPS = tuple(range(0, STEPS + 1, 1_000))


def validate_reference(state: str, path: Path) -> dict:
    digest = sha256(path)
    if digest != EXPECTED[state]:
        raise ValueError(f"{state}: reference SHA mismatch: {digest}")
    with np.load(path) as source:
        missing = set(REQUIRED) - set(source.files)
        if missing:
            raise ValueError(f"{state}: missing arrays {sorted(missing)}")
        data = {name: source[name].copy() for name in REQUIRED}
    for name, shape in REQUIRED.items():
        if data[name].shape != shape:
            raise ValueError(f"{state}: {name} shape {data[name].shape} != {shape}")
        if not np.isfinite(data[name]).all():
            raise ValueError(f"{state}: {name} contains nonfinite values")
    if not np.issubdtype(data["conn"].dtype, np.integer):
        raise ValueError(f"{state}: connectivity must be integer")
    if data["conn"].min() < 0 or data["conn"].max() >= len(data["xy"]):
        raise ValueError(f"{state}: connectivity out of range")
    np.testing.assert_array_equal(data["xy"].min(0), np.array([-0.5, -0.5]))
    np.testing.assert_array_equal(data["xy"].max(0), np.array([0.5, 0.5]))
    if np.any((data["damage"] < 0.0) | (data["damage"] > 1.0)):
        raise ValueError(f"{state}: damage outside [0,1]")
    bottom, top = boundary_masks(data["xy"])
    target = data["equilibrated_uv"]
    bc_error = max(float(np.abs(target[bottom]).max()),
                   float(np.abs(target[top, 0]).max()),
                   float(np.abs(target[top, 1] - US).max()))
    if bc_error > 1e-12:
        raise ValueError(f"{state}: target BC error {bc_error}")
    evaluator_strain = q4_strain(data["xy"], data["conn"], target)
    strain_lock_error = float(np.max(np.abs(evaluator_strain - data["strain_after"])))
    if strain_lock_error > 5e-10:
        raise ValueError(f"{state}: strain evaluator mismatch {strain_lock_error}")
    reference = residual_metrics(data["xy"], data["conn"], target, data["damage"])
    if np.any(reference["mass"] <= 0.0):
        raise ValueError(f"{state}: nonpositive nodal mass")
    if not np.all(data["gp_weights"] > 0.0):
        raise ValueError(f"{state}: nonpositive GP weights")
    data.update(reference_sha256=digest, target_bc_error=bc_error,
                strain_lock_error=strain_lock_error,
                reference_rho_u=reference["rho_u"], mass=reference["mass"],
                area=reference["area"], energy_scale=reference["energy_scale"])
    return data


def make_strata(damage: np.ndarray, mass: np.ndarray) -> dict:
    active = np.asarray(damage > DAMAGE_THRESHOLD)
    if not active.any() or active.all():
        raise ValueError("damage stratification requires two nonempty strata")
    mass = np.asarray(mass, dtype=np.float64)
    total = float(mass.sum())
    if not np.isfinite(total) or total <= 0.0 or np.any(mass <= 0.0):
        raise ValueError("invalid nodal mass")
    probability = mass / total
    p_active = float(probability[active].sum())
    return {
        "active_index": np.flatnonzero(active),
        "background_index": np.flatnonzero(~active),
        "active_probability": probability[active] / p_active,
        "background_probability": probability[~active] / (1.0 - p_active),
        "p_active": p_active,
        "p_background": 1.0 - p_active,
        "active_count": int(active.sum()),
        "background_count": int((~active).sum()),
    }


def draw_stratified(rng: np.random.Generator, strata: dict, alpha: str) -> tuple[np.ndarray, np.ndarray]:
    """Draw A then B without shuffling; this order is part of the protocol."""
    active = rng.choice(
        strata["active_index"], size=ALLOCATIONS[alpha][0], replace=True,
        p=strata["active_probability"],
    )
    background = rng.choice(
        strata["background_index"], size=ALLOCATIONS[alpha][1], replace=True,
        p=strata["background_probability"],
    )
    return active, background


def stratified_loss(active_error_sq: torch.Tensor, background_error_sq: torch.Tensor,
                    p_active: float, p_background: float) -> torch.Tensor:
    return (
        p_active * torch.mean(active_error_sq)
        + p_background * torch.mean(background_error_sq)
    ) / abs(US) ** 2


def monitor_full_field(model, xy: torch.Tensor, target: torch.Tensor,
                       mass: np.ndarray, damage: np.ndarray, step: int) -> dict:
    predicted = predict_in_chunks(model, xy)
    error_sq = torch.sum((predicted - target) ** 2, dim=1).detach().cpu().numpy()
    probability = mass / np.sum(mass)
    active = damage > DAMAGE_THRESHOLD
    active_loss = float(np.sum(probability[active] * error_sq[active]) / abs(US) ** 2)
    background_loss = float(np.sum(probability[~active] * error_sq[~active]) / abs(US) ** 2)
    total_loss = active_loss + background_loss
    return {
        "step": step,
        "full_field_loss": total_loss,
        "displacement_mass_rms_over_abs_Us": float(np.sqrt(total_loss)),
        "active_contribution": active_loss,
        "background_contribution": background_loss,
        "p_damage": float(probability[active].sum()),
        "p_background": float(probability[~active].sum()),
        "damage_conditional_rms_over_abs_Us": float(np.sqrt(active_loss / probability[active].sum())),
        "background_conditional_rms_over_abs_Us": float(np.sqrt(background_loss / probability[~active].sum())),
    }


def train(args: argparse.Namespace, data: dict) -> dict:
    if not torch.cuda.is_available() or args.device != "cuda":
        raise RuntimeError("formal S04-E017 training requires --device cuda on a CUDA producer")
    actual_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    dirty = bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip())
    if actual_commit != args.expected_commit or dirty:
        raise RuntimeError(
            f"code identity invalid: actual={actual_commit} expected={args.expected_commit} dirty={dirty}"
        )
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if not visible.isdigit():
        raise RuntimeError("formal S04-E017 requires one explicit numeric CUDA_VISIBLE_DEVICES value")
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") not in (":4096:8", ":16:8"):
        raise RuntimeError("CUBLAS_WORKSPACE_CONFIG must be set before Python starts")

    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.cuda.manual_seed_all(args.seed)
    device = torch.device("cuda")
    model = build_model(args.seed).to(device=device, dtype=torch.float64)
    xy = torch.tensor(data["xy"], dtype=torch.float64, device=device)
    target = torch.tensor(data["equilibrated_uv"], dtype=torch.float64, device=device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=1e-3, betas=(0.9, 0.999), eps=1e-8,
        weight_decay=1e-8, amsgrad=False, maximize=False,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=STEPS, eta_min=1e-5
    )
    rng = np.random.Generator(np.random.PCG64(args.seed + SAMPLE_SEED_OFFSET))
    n_damage, n_background = ALLOCATIONS[args.alpha]
    strata = make_strata(data["damage"], data["mass"])
    monitor = [monitor_full_field(model, xy, target, data["mass"], data["damage"], 0)]
    last_loss = None
    started = time.time()
    started_utc = datetime.now(timezone.utc).isoformat()
    for step in range(1, STEPS + 1):
        sampled_active, sampled_background = draw_stratified(rng, strata, args.alpha)
        sampled = np.concatenate((sampled_active, sampled_background))
        index = torch.tensor(sampled, dtype=torch.long, device=device)
        physical = xy[index]
        optimizer.zero_grad(set_to_none=True)
        predicted = apply_sens_bc(model(normalize_xy(physical)), physical)
        error_sq = torch.sum((predicted - target[index]) ** 2, dim=1)
        loss = stratified_loss(
            error_sq[:n_damage], error_sq[n_damage:],
            strata["p_active"], strata["p_background"],
        )
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError(f"nonfinite loss at step {step}")
        loss.backward()
        optimizer.step()
        scheduler.step()
        last_loss = float(loss.detach())
        if step in MONITOR_STEPS:
            entry = monitor_full_field(
                model, xy, target, data["mass"], data["damage"], step
            )
            monitor.append(entry)
            print(json.dumps({**entry, "sampled_loss": last_loss,
                              "lr": scheduler.get_last_lr()[0]}), flush=True)

    predicted = predict_in_chunks(model, xy).cpu().numpy()
    metrics = final_metrics(data, predicted)
    if not np.isclose(
        monitor[-1]["displacement_mass_rms_over_abs_Us"],
        metrics["displacement_mass_rms_over_abs_Us"], rtol=0.0, atol=1e-14,
    ):
        raise RuntimeError("final monitoring metric mismatch")
    reference_sha_after = sha256(args.reference)
    if reference_sha_after != data["reference_sha256"]:
        raise RuntimeError("reference file mutated during training")

    args.out.mkdir(parents=True, exist_ok=False)
    checkpoint = args.out / "final_step_10000.pt"
    torch.save({
        "protocol_revision": PROTOCOL_REVISION,
        "state": args.state,
        "seed": args.seed,
        "alpha": args.alpha,
        "step": STEPS,
        "sampler": {
            "damage_threshold": DAMAGE_THRESHOLD,
            "n_damage": n_damage,
            "n_background": n_background,
            "sample_seed": args.seed + SAMPLE_SEED_OFFSET,
            "order": "damage_then_background_no_shuffle",
        },
        "model_state_dict": {k: v.detach().cpu() for k, v in model.state_dict().items()},
    }, checkpoint)
    prediction = args.out / "prediction.npz"
    np.savez_compressed(prediction, uv=predicted)
    monitor_path = args.out / "monitoring.json"
    monitor_path.write_text(json.dumps(monitor, indent=2), encoding="utf-8")
    result = {
        "status": "COMPLETED",
        "protocol_revision": PROTOCOL_REVISION,
        "state": args.state,
        "seed": args.seed,
        "alpha": args.alpha,
        "reference_sha256": data["reference_sha256"],
        "reference_sha256_after": reference_sha_after,
        "checkpoint_sha256": sha256(checkpoint),
        "prediction_sha256": sha256(prediction),
        "monitoring_sha256": sha256(monitor_path),
        "steps": STEPS,
        "batch_nodes": BATCH_NODES,
        "n_damage": n_damage,
        "n_background": n_background,
        "damage_threshold": DAMAGE_THRESHOLD,
        "p_damage": strata["p_active"],
        "p_background": strata["p_background"],
        "damage_node_count": strata["active_count"],
        "background_node_count": strata["background_count"],
        "sample_seed": args.seed + SAMPLE_SEED_OFFSET,
        "sample_order": "damage_then_background_no_shuffle",
        "final_sampled_loss": last_loss,
        "final_scheduler_lr": scheduler.get_last_lr()[0],
        "elapsed_seconds": time.time() - started,
        "started_utc": started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "training": True,
        "damage_solves": 0,
        "history_commits": 0,
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "cuda_version": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(device),
        "platform": platform.platform(),
        "pid": os.getpid(),
        "metrics": metrics,
    }
    metrics_path = args.out / "metrics.json"
    metrics_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    archive_root = Path(args.archive_root)
    archive_root.mkdir(parents=True, exist_ok=False)
    archive_hashes = {}
    for asset in (checkpoint, prediction, monitor_path, metrics_path):
        copied = archive_root / asset.name
        shutil.copy2(asset, copied)
        source_hash = sha256(asset)
        if sha256(copied) != source_hash:
            raise RuntimeError(f"archive copy verification failed for {asset.name}")
        archive_hashes[asset.name] = source_hash
    receipt = {
        "status": "COMPLETED", "run_id": args.run_id,
        "protocol_revision": PROTOCOL_REVISION, "state": args.state, "seed": args.seed,
        "alpha": args.alpha,
        "producer_alias": "taobo", "hostname": socket.gethostname(),
        "code_commit": actual_commit, "dirty": dirty, "command": shlex.join(os.sys.argv),
        "pid": os.getpid(), "cuda_visible_devices": visible,
        "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        "gpu": torch.cuda.get_device_name(device), "output_root": str(args.out.resolve()),
        "archive_root": args.archive_root, "log_path": args.log_path,
        "started_utc": started_utc, "finished_utc": result["finished_utc"],
        "checkpoint_sha256": result["checkpoint_sha256"],
        "prediction_sha256": result["prediction_sha256"],
        "monitoring_sha256": result["monitoring_sha256"],
        "metrics_sha256": sha256(metrics_path),
        "reference_sha256": result["reference_sha256"],
        "archive_status": "VERIFIED_COPY", "archive_file_hashes": archive_hashes,
    }
    receipt_text = json.dumps(receipt, indent=2)
    (args.out / "RUN_RECEIPT.json").write_text(receipt_text, encoding="utf-8")
    (archive_root / "RUN_RECEIPT.json").write_text(receipt_text, encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--alpha", choices=tuple(ALLOCATIONS), required=True)
    parser.add_argument("--state", choices=tuple(EXPECTED), required=True)
    parser.add_argument("--seed", choices=SEEDS, type=int, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--expected-commit")
    parser.add_argument("--archive-root")
    parser.add_argument("--log-path")
    parser.add_argument("--device", choices=("cuda",), default="cuda")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if not args.validate_only:
        for name in ("out", "run_id", "expected_commit", "archive_root", "log_path"):
            if not getattr(args, name):
                parser.error(f"--{name.replace('_', '-')} is required for formal training")
        if len(args.expected_commit) != 40 or any(c not in "0123456789abcdef" for c in args.expected_commit):
            parser.error("--expected-commit must be a lowercase 40-character git SHA")
        for name, prefix in {
            "out": "/mnt/data2/drtao/wennie/",
            "archive_root": "/mnt/data2/drtao/pidl_archives/",
            "log_path": "/mnt/data2/drtao/wennie/",
        }.items():
            value = str(Path(getattr(args, name)).expanduser().resolve())
            if not value.startswith(prefix) or args.run_id not in value:
                parser.error(f"--{name.replace('_', '-')} must be under {prefix} and contain --run-id")
        if Path(args.archive_root).exists():
            parser.error("--archive-root must not already exist")
    if args.out is not None and args.out.exists():
        parser.error("--out must not already exist")
    return args


def main() -> None:
    args = parse_args()
    data = validate_reference(args.state, args.reference)
    if args.validate_only:
        n_damage, n_background = ALLOCATIONS[args.alpha]
        strata = make_strata(data["damage"], data["mass"])
        print(json.dumps({
            "status": "VALIDATION_ONLY_PASS", "training": False,
            "state": args.state, "seed": args.seed,
        "alpha": args.alpha,
            "reference_sha256": data["reference_sha256"],
            "reference_rho_u": data["reference_rho_u"],
            "p_damage": strata["p_active"],
            "damage_node_count": strata["active_count"],
            "n_damage": n_damage, "n_background": n_background,
        }, indent=2))
        return
    print(json.dumps(train(args, data), indent=2), flush=True)


if __name__ == "__main__":
    main()
