#!/usr/bin/env python3
"""S09-E006: frozen gradient-balanced Pareto-rescue comparison on Taobo."""
from __future__ import annotations

import argparse
import copy
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
sys.path.insert(0, str(ROOT / "SENS_tensile"))
from run_s09_equilibrium_operator import (  # noqa: E402
    evaluate, load_packet, make_optimizer, packet_audit, train_update,
)
from s09_equilibrium_operator import (  # noqa: E402
    EquilibriumOperator, affine_displacement, area_mse, graph_to_torch,
)
from s09_fem_physics import boundary, equilibrium  # noqa: E402
from s09_multiobjective import strict_balanced_projected_direction  # noqa: E402
from s09_q4_quadrature import q4_shape_data  # noqa: E402


PACKET_SHA256 = "b37a63ccb0e7129ecc3fbe01fc356c93fccc1877b5f34e68fe93265f335109ed"
CHECKPOINT_SHA256 = "1fc1695a87c41cd4a373fa31535dc99be7d91ad01af9a1e11a2986d83af8029e"
SEQUENCE_SHA256 = "ee1884ae1a81813334641faaacc0e44151d23cb4f36e35948ec656fd20c976f5"
REFERENCE_SHA256 = "202be98d2be46c702196a7f05d4571789097a297aea3f99870dd66379ae6e62f"
E004_COMMIT = "11fd75d70b18165d6214d50c90adc9c9c9b522a5"
E004_UNCHANGED_PATHS = (
    "SENS_tensile/run_s09_equilibrium_operator.py",
    "source/s09_equilibrium_operator.py",
    "source/s09_fem_physics.py",
    "source/s09_q4_quadrature.py",
)
ARMS = {"balanced_beta_0p25": 0.25, "balanced_beta_1p0": 1.0}
MATCHED_UPDATES = 700
ASSESS_EVERY = 50
OUTPUT_ROOT = Path("/mnt/data2/drtao/wennie")


class ArmInvalid(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def validate_output_path(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(OUTPUT_ROOT):
        raise RuntimeError("output must be contained by /mnt/data2/drtao/wennie")
    if not re.fullmatch(r"S09-E006-R\d{3}_[A-Za-z0-9._-]+", resolved.name):
        raise RuntimeError("output directory must carry a unique S09-E006 Run ID")
    return resolved


def assert_e004_semantics_unchanged() -> None:
    subprocess.check_call(
        ["git", "diff", "--quiet", E004_COMMIT, "--", *E004_UNCHANGED_PATHS], cwd=ROOT
    )


def optimizer_steps(optimizer_state: dict) -> set[int]:
    steps = set()
    for state in optimizer_state["state"].values():
        if "step" in state:
            steps.add(int(state["step"]))
    if not steps:
        raise RuntimeError("optimizer state has no step counters")
    return steps


def state_sha256(value) -> str:
    digest = hashlib.sha256()

    def update(item) -> None:
        if torch.is_tensor(item):
            array = item.detach().cpu().contiguous().numpy()
            digest.update(b"tensor")
            digest.update(str(array.dtype).encode())
            digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
            digest.update(array.tobytes())
        elif isinstance(item, dict):
            digest.update(b"dict")
            for key in sorted(item, key=lambda entry: str(entry)):
                update(str(key)); update(item[key])
        elif isinstance(item, (list, tuple)):
            digest.update(b"sequence")
            for entry in item:
                update(entry)
        else:
            digest.update(repr(item).encode())

    update(value)
    return digest.hexdigest()


def validate_sequence(path: Path) -> np.ndarray:
    sequence = np.load(path, allow_pickle=False)
    if sequence.shape != (1000,) or sequence.dtype.kind not in "iu":
        raise RuntimeError("E004 training sequence identity/shape mismatch")
    if int(sequence.min()) < 0 or int(sequence.max()) >= 16:
        raise RuntimeError("training sequence contains an invalid state index")
    return sequence[300:].astype(np.int64, copy=False)


def compute_affine_normalizers(packet, graph, physics, free):
    train_d = torch.as_tensor(packet["train_d"], dtype=torch.float32, device=graph["xy"].device)
    values = []
    with torch.no_grad():
        for index, load in enumerate(packet["train_load"]):
            affine = affine_displacement(graph["xy"], float(load))
            force, _ = equilibrium(affine, train_d[index], *physics)
            denominator = force[free].square().mean()
            if not torch.isfinite(denominator) or float(denominator) <= 0.0:
                raise RuntimeError(f"invalid affine normalizer for training state {index}")
            values.append(denominator)
    return torch.stack(values)


def seven_metrics(metrics: dict) -> dict[str, float]:
    result = {"aggregate_R": float(metrics["R"])}
    for state in metrics["states"]:
        cycle = int(state["cycle"])
        result[f"c{cycle}_R_u"] = float(state["relative_to_affine"])
        result[f"c{cycle}_R_f"] = float(state["free_force_rms_ratio_to_affine"])
    if set(result) != {
        "aggregate_R", "c76_R_u", "c76_R_f", "c82_R_u", "c82_R_f",
        "c83_R_u", "c83_R_f",
    }:
        raise RuntimeError("development metric identity mismatch")
    if not np.isfinite(list(result.values())).all():
        raise RuntimeError("non-finite development metric")
    return result


def validate_replay(replay: dict, reference_file: Path) -> dict:
    reference_payload = json.loads(reference_file.read_text())
    reference = seven_metrics(reference_payload["final"]["data_only"])
    observed = seven_metrics(replay)
    checks = {}
    for key, expected in reference.items():
        actual = observed[key]
        tolerance = 1e-6 + 1e-5 * abs(expected)
        difference = abs(actual - expected)
        checks[key] = {
            "reference": expected, "replay": actual, "absolute_difference": difference,
            "tolerance": tolerance, "pass": bool(difference <= tolerance),
        }
    if not all(item["pass"] for item in checks.values()):
        raise RuntimeError("data-only replay failed the seven-value identity gate")
    return checks


def balanced_update(model, optimizer, index, packet, graph, physics, free,
                    affine_normalizer, beta):
    device = graph["xy"].device
    damage = torch.as_tensor(packet["train_d"][index], device=device, dtype=torch.float32)
    target = torch.as_tensor(packet["train_u"][index], device=device, dtype=torch.float32)
    load = float(packet["train_load"][index])
    optimizer.zero_grad(set_to_none=True)
    prediction = model(damage, load, graph)
    data_loss = area_mse(
        prediction / load, target / load, model.correction_scale, graph["area"]
    )
    force, _ = equilibrium(prediction, damage, *physics)
    physics_loss = force[free].square().mean() / affine_normalizer[index]
    if not torch.isfinite(data_loss) or not torch.isfinite(physics_loss):
        raise ArmInvalid("non-finite objective")
    parameters = tuple(model.parameters())
    data_gradients = torch.autograd.grad(data_loss, parameters, retain_graph=True)
    physics_gradients = torch.autograd.grad(physics_loss, parameters)
    try:
        direction, metadata = strict_balanced_projected_direction(
            data_gradients, physics_gradients, beta
        )
    except ValueError as error:
        raise ArmInvalid(str(error)) from error
    assigned = []
    for parameter, gradient in zip(parameters, direction):
        converted = gradient.to(device=parameter.device, dtype=parameter.dtype).clone()
        if not torch.isfinite(converted).all():
            raise ArmInvalid("direction became non-finite after dtype conversion")
        parameter.grad = converted
        assigned.append(converted)
    assigned_norm = torch.sqrt(sum(item.detach().double().square().sum()
                                   for item in assigned))
    if not torch.isfinite(assigned_norm):
        raise ArmInvalid("assigned direction norm is non-finite")
    try:
        clipped_from = torch.nn.utils.clip_grad_norm_(
            parameters, 10.0, error_if_nonfinite=True
        )
    except RuntimeError as error:
        message = str(error).lower()
        if "total norm" in message and "non-finite" in message:
            raise ArmInvalid("combined clipped norm is non-finite") from error
        raise
    if not torch.isfinite(clipped_from):
        raise ArmInvalid("combined clipped norm is non-finite")
    metadata["clip_max_norm"] = 10.0
    metadata["assigned_direction_norm_before_clip"] = float(assigned_norm)
    metadata["clip_reported_preclip_norm"] = float(clipped_from)
    metadata["clip_applied"] = bool(float(clipped_from) > 10.0)
    optimizer.step()
    return float(data_loss.detach()), float(physics_loss.detach()), metadata


def make_arm(common_checkpoint, scale, device):
    model = EquilibriumOperator(scale, width=32, rank=8).to(device)
    model.load_state_dict(copy.deepcopy(common_checkpoint["model"]))
    optimizer = make_optimizer(model)
    optimizer.load_state_dict(copy.deepcopy(common_checkpoint["optimizer"]))
    if optimizer_steps(optimizer.state_dict()) != {300}:
        raise RuntimeError("common optimizer is not at exact step 300")
    stochastic = [module.__class__.__name__ for module in model.modules()
                  if isinstance(module, (torch.nn.Dropout, torch.nn.modules.batchnorm._BatchNorm))]
    if stochastic:
        raise RuntimeError(f"unexpected stochastic/stateful layers: {stochastic}")
    model.train()
    return model, optimizer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--sequence", type=Path, required=True)
    parser.add_argument("--reference-metrics", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--expected-commit")
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()

    identities = {
        "packet": (args.packet, PACKET_SHA256),
        "checkpoint": (args.checkpoint, CHECKPOINT_SHA256),
        "sequence": (args.sequence, SEQUENCE_SHA256),
        "reference_metrics": (args.reference_metrics, REFERENCE_SHA256),
    }
    for label, (path, expected) in identities.items():
        if sha256(path) != expected:
            raise RuntimeError(f"{label} identity mismatch")
    assert_e004_semantics_unchanged()
    packet = load_packet(args.packet)
    scale, graph_np = packet_audit(packet)
    sequence = validate_sequence(args.sequence)
    if args.audit_only:
        print(json.dumps({"identity_pass": True, "matched_updates": len(sequence),
                          "betas": list(ARMS.values())}))
        return

    if platform.system() != "Linux" or platform.node() != "GPUServer8":
        raise RuntimeError("Taobo GPUServer8 only; no Mac training")
    if not args.expected_commit or git("rev-parse", "HEAD") != args.expected_commit:
        raise RuntimeError("exact reviewed commit required")
    if git("status", "--porcelain"):
        raise RuntimeError("clean producer checkout required")
    if not os.getenv("CUDA_VISIBLE_DEVICES") or not torch.cuda.is_available():
        raise RuntimeError("explicit healthy CUDA device required")
    if args.out is None:
        raise RuntimeError("output path is required")
    args.out = validate_output_path(args.out)
    args.out.mkdir(parents=True, exist_ok=False)

    device = torch.device("cuda")
    torch.manual_seed(1)
    np.random.seed(1)
    graph = graph_to_torch(graph_np, device)
    conn = torch.as_tensor(packet["conn"], dtype=torch.long, device=device)
    shape, dshape, det = q4_shape_data(graph["xy"], conn)
    physics = (conn, shape, dshape, det)
    free = boundary(graph["xy"])
    affine_normalizer = compute_affine_normalizers(packet, graph, physics, free)
    common_checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=True)
    if optimizer_steps(common_checkpoint["optimizer"]) != {300}:
        raise RuntimeError("checkpoint optimizer is not at exact step 300")

    started = time.time()
    receipt = {
        "experiment_id": "S09-E006", "run_id": args.out.name,
        "protocol_revision": "v2-gradient-balanced-pareto-rescue",
        "commit": args.expected_commit, "dirty": "", "hostname": platform.node(),
        "gpu": os.getenv("CUDA_VISIBLE_DEVICES"), "pid": os.getpid(),
        "command": sys.argv, "started_unix": started, "seed": 1,
        "matched_updates_per_arm": MATCHED_UPDATES, "betas": ARMS,
        "identity_sha256": {key: expected for key, (_, expected) in identities.items()},
        "e004_commit": E004_COMMIT, "e004_paths_unchanged": True,
        "torch_version": torch.__version__, "cuda_version": torch.version.cuda,
        "cuda_device": torch.cuda.get_device_name(0),
        "execution_status": "running", "scientific_status": "pending",
    }
    dump(args.out / "receipt.json", receipt)
    updates, assessments, final_metrics, final_fields = [], [], {}, {}
    arm_status = {}
    try:
        arm_order = ["data_only_replay", *ARMS]
        for arm in arm_order:
            model, optimizer = make_arm(common_checkpoint, scale, device)
            start_model_hash = state_sha256(model.state_dict())
            start_optimizer_hash = state_sha256(optimizer.state_dict())
            valid, failure = True, None
            for matched_step, index_value in enumerate(sequence, start=1):
                index = int(index_value)
                cycle = int(packet["train_cycle"][index])
                before_steps = optimizer_steps(optimizer.state_dict())
                expected_before = 299 + matched_step
                if before_steps != {expected_before}:
                    raise RuntimeError(f"optimizer pre-step mismatch for {arm}: {before_steps}")
                row = {"arm": arm, "matched_step": matched_step,
                       "state_index": index, "cycle": cycle}
                try:
                    if arm == "data_only_replay":
                        data_loss, physics_loss, _ = train_update(
                            model, optimizer, index, packet, graph, physics, free,
                            affine_normalizer, 0.0,
                        )
                    else:
                        data_loss, physics_loss, metadata = balanced_update(
                            model, optimizer, index, packet, graph, physics, free,
                            affine_normalizer, ARMS[arm],
                        )
                        row.update(metadata)
                except ArmInvalid as error:
                    valid, failure = False, {
                        "matched_step": matched_step, "state_index": index,
                        "cycle": cycle, "reason": str(error),
                    }
                    row.update(valid=False, failure_reason=str(error))
                    updates.append(row)
                    break
                after_steps = optimizer_steps(optimizer.state_dict())
                if after_steps != {expected_before + 1}:
                    raise RuntimeError(f"optimizer post-step mismatch for {arm}: {after_steps}")
                row.update(valid=True, data_loss=data_loss, physics_loss=physics_loss,
                           optimizer_step_before=expected_before,
                           optimizer_step_after=expected_before + 1)
                updates.append(row)
                if matched_step % ASSESS_EVERY == 0:
                    metrics, _ = evaluate(model, packet, graph, physics, device)
                    assessments.append({
                        "arm": arm, "matched_step": matched_step,
                        "development_R": metrics["R"],
                        "mean_development_R_f": float(np.mean([
                            state["free_force_rms_ratio_to_affine"]
                            for state in metrics["states"]
                        ])),
                    })
            completed = valid and len([row for row in updates if row["arm"] == arm
                                       and row.get("valid")]) == MATCHED_UPDATES
            arm_status[arm] = {
                "valid": bool(completed), "failure": failure,
                "start_model_sha256": start_model_hash,
                "start_optimizer_sha256": start_optimizer_hash,
                "updates_completed": sum(row.get("valid", False) for row in updates
                                         if row["arm"] == arm),
            }
            suffix = "final" if completed else "invalid_partial"
            torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict()},
                       args.out / f"{arm}_{suffix}.pt")
            arm_status[arm]["final_model_sha256"] = state_sha256(model.state_dict())
            arm_status[arm]["final_optimizer_sha256"] = state_sha256(optimizer.state_dict())
            if completed:
                metrics, fields = evaluate(model, packet, graph, physics, device)
                final_metrics[arm] = metrics
                final_fields[arm] = fields
            if arm == "data_only_replay":
                if not completed:
                    raise RuntimeError("data-only replay did not complete")
                replay_checks = validate_replay(metrics, args.reference_metrics)
                dump(args.out / "replay_checks.json", replay_checks)

        replay = final_metrics["data_only_replay"]
        if any(state["relative_to_affine"] <= 0.0 for state in replay["states"]):
            raise RuntimeError("data-only displacement comparator is non-positive")
        replay_force_mean = float(np.mean([
            state["free_force_rms_ratio_to_affine"] for state in replay["states"]
        ]))
        if not np.isfinite(replay_force_mean) or replay_force_mean <= 0.0:
            raise RuntimeError("data-only residual comparator is non-positive or non-finite")
        feasibility = {}
        for arm in ARMS:
            if not arm_status[arm]["valid"]:
                feasibility[arm] = {"valid": False, "votes": False, "pass": None}
                continue
            metrics = final_metrics[arm]
            force_mean = float(np.mean([
                state["free_force_rms_ratio_to_affine"] for state in metrics["states"]
            ]))
            displacement_ratios = [
                candidate["relative_to_affine"] / comparator["relative_to_affine"]
                for candidate, comparator in zip(metrics["states"], replay["states"])
            ]
            residual_pass = force_mean <= 0.50 * replay_force_mean
            displacement_pass = all(value <= 1.10 for value in displacement_ratios)
            feasibility[arm] = {
                "valid": True, "votes": True,
                "mean_R_f": force_mean, "data_only_mean_R_f": replay_force_mean,
                "residual_ratio_to_data_only": force_mean / replay_force_mean,
                "residual_clause_pass": bool(residual_pass),
                "per_state_R_u_ratio_to_data_only": displacement_ratios,
                "displacement_clause_pass": bool(displacement_pass),
                "pass": bool(residual_pass and displacement_pass),
            }
        valid_balanced = [arm for arm in ARMS if feasibility[arm]["valid"]]
        passing = [arm for arm in valid_balanced if feasibility[arm]["pass"]]
        if passing:
            verdict = "supports"
            selected = min(
                passing,
                key=lambda arm: (final_metrics[arm]["R"], feasibility[arm]["mean_R_f"]),
            )
        elif valid_balanced:
            verdict, selected = "negative", None
        else:
            verdict, selected = "inconclusive", None
        result = {
            "primary": {
                "criterion": (
                    "exists valid frozen balanced arm with mean R_f <= 0.50*data-only "
                    "and every state R_u <= 1.10*data-only"
                ),
                "verdict": verdict, "pass": bool(passing),
                "passing_arms": passing, "selected_arm": selected,
            },
            "validity": {"data_only_replay_pass": True, "arm_status": arm_status},
            "feasibility": feasibility, "final": final_metrics,
            "claim_boundary": (
                "Fixed-damage development optimization capability only; no exact equilibrium, "
                "damage evolution, independent generalization or real-road validity."
            ),
        }
        dump(args.out / "metrics.json", result)
        arrays = {"xy": packet["xy"], "area": packet["lumped_area"],
                  "cycle": packet["dev_cycle"], "damage": packet["dev_d"]}
        for arm, fields in final_fields.items():
            arrays[f"{arm}_prediction"] = np.stack([item[0] for item in fields])
        data_fields = final_fields["data_only_replay"]
        arrays["target"] = np.stack([item[1] for item in data_fields])
        arrays["affine"] = np.stack([item[2] for item in data_fields])
        np.savez_compressed(args.out / "final_fields.npz", **arrays)
        receipt.update(execution_status="succeeded", scientific_status=verdict,
                       selected_arm=selected)
    except Exception as error:
        receipt.update(execution_status="failed", scientific_status="inadmissible",
                       error=repr(error))
        raise
    finally:
        if updates:
            with (args.out / "updates.csv").open("w", newline="") as stream:
                columns = sorted({key for row in updates for key in row})
                writer = csv.DictWriter(stream, fieldnames=columns)
                writer.writeheader(); writer.writerows(updates)
        if assessments:
            with (args.out / "assessments.csv").open("w", newline="") as stream:
                columns = sorted({key for row in assessments for key in row})
                writer = csv.DictWriter(stream, fieldnames=columns)
                writer.writeheader(); writer.writerows(assessments)
        if arm_status:
            dump(args.out / "arm_status.json", arm_status)
        receipt.update(elapsed_s=time.time() - started,
                       cuda_peak_memory_bytes=torch.cuda.max_memory_allocated())
        dump(args.out / "receipt.json", receipt)


if __name__ == "__main__":
    main()
