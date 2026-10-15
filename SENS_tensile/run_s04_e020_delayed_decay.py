#!/usr/bin/env python3
"""E020 schedule-only continuation; E019 scientific source is immutable."""
from __future__ import annotations
import argparse, hashlib, json, os, platform, shlex, shutil, socket, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import torch
from run_s04_e019_frozen_residual_screen import (
    EXPECTED,
    ALLOCATIONS,
    SEEDS,
    STEPS,
    BATCH_NODES,
    DAMAGE_THRESHOLD,
    MONITOR_STEPS,
    SAMPLE_SEED_OFFSET,
    US,
    BACKBONE_LOCKS,
    validate_reference,
    admit_backbone,
    build_model,
    state_digest,
    make_strata,
    draw_stratified,
    stratified_loss,
    monitor_full_field,
    support_diagnostics,
    predict_in_chunks,
    final_metrics,
    sha256,
    anchor_component_geometry,
    PARAMETER_COUNT,
    RESIDUAL_PARAMETER_COUNT,
)
from s04_e020_delayed_decay import (
    PROTOCOL_REVISION,
    CONTROL_LOCKS,
    DelayedDecaySchedule,
    admit_control,
    check_pair_identity,
    schedule_identity,
    check_schedule_identity,
    check_runtime_identity,
    update_lr,
)

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("localized",)


def train(args: argparse.Namespace, data: dict) -> dict:
    if not torch.cuda.is_available() or args.device != "cuda":
        raise RuntimeError(
            "formal S04-E020 training requires --device cuda on a CUDA producer"
        )
    actual_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    if actual_commit != args.expected_commit or dirty:
        raise RuntimeError(
            f"code identity invalid: actual={actual_commit} expected={args.expected_commit} dirty={dirty}"
        )
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if not visible.isdigit():
        raise RuntimeError(
            "formal S04-E020 requires one explicit numeric CUDA_VISIBLE_DEVICES value"
        )
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") not in (":4096:8", ":16:8"):
        raise RuntimeError("CUBLAS_WORKSPACE_CONFIG must be set before Python starts")

    check_runtime_identity(
        args.state,
        dict(
            torch_version=str(torch.__version__),
            numpy_version=np.__version__,
            cuda_version=torch.version.cuda,
            gpu=torch.cuda.get_device_name(0),
            hostname=socket.gethostname(),
            cuda_visible_devices=visible,
            cublas_workspace_config=os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        ),
    )
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.cuda.manual_seed_all(args.seed)
    device = torch.device("cuda")
    geometry = anchor_component_geometry(
        data["xy"], data["damage"], data["conn"], data["mass"]
    )
    backbone, saved_base_uv, backbone_lock = admit_backbone(
        args.state, args.backbone_dir, data
    )
    paired = admit_control(args.state, args.control_dir, data, backbone)
    model = build_model(args.seed, args.arm, geometry, backbone).to(
        device=device, dtype=torch.float64
    )
    backbone_digest = state_digest(model.backbone)
    initial_residual_digest = state_digest(model.residual)
    check_pair_identity(args.state, geometry, backbone_digest, initial_residual_digest)
    base_xy = torch.tensor(data["xy"], dtype=torch.float64, device=device)
    evaluated_base = predict_in_chunks(model.backbone, base_xy).cpu().numpy()
    np.testing.assert_allclose(evaluated_base, saved_base_uv, rtol=0, atol=1e-12)
    baseline_metrics = final_metrics(data, evaluated_base)
    saved_metrics = final_metrics(data, saved_base_uv)
    np.testing.assert_allclose(
        baseline_metrics["displacement_mass_rms_over_abs_Us"],
        saved_metrics["displacement_mass_rms_over_abs_Us"],
        rtol=0,
        atol=1e-14,
    )
    baseline_uv = torch.tensor(evaluated_base, dtype=torch.float64, device=device)
    sampler_digest = hashlib.sha256()
    xy = torch.tensor(data["xy"], dtype=torch.float64, device=device)
    target = torch.tensor(data["equilibrated_uv"], dtype=torch.float64, device=device)
    optimizer = torch.optim.AdamW(
        model.residual.parameters(),
        lr=1e-3,
        betas=(0.9, 0.999),
        eps=1e-8,
        weight_decay=1e-8,
        amsgrad=False,
        maximize=False,
    )
    scheduler = DelayedDecaySchedule(optimizer)
    rng = np.random.Generator(np.random.PCG64(args.seed + SAMPLE_SEED_OFFSET))
    n_damage, n_background = ALLOCATIONS[args.alpha]
    strata = make_strata(data["damage"], data["mass"])
    monitor = [monitor_full_field(model, xy, target, data["mass"], data["damage"], 0)]
    initial_uv = predict_in_chunks(model, xy).cpu().numpy()
    np.testing.assert_allclose(initial_uv, evaluated_base, rtol=0, atol=0)
    monitor[0].update(support_diagnostics(initial_uv, evaluated_base, data, geometry))
    last_loss = None
    started = time.time()
    started_utc = datetime.now(timezone.utc).isoformat()
    for step in range(1, STEPS + 1):
        sampled_active, sampled_background = draw_stratified(rng, strata, args.alpha)
        sampled = np.concatenate((sampled_active, sampled_background))
        index = torch.tensor(sampled, dtype=torch.long, device=device)
        physical = xy[index]
        sampler_digest.update(np.asarray(sampled, dtype="<i8").tobytes())
        optimizer.zero_grad(set_to_none=True)
        predicted = baseline_uv[index] + model.correction_physical(physical)
        error_sq = torch.sum((predicted - target[index]) ** 2, dim=1)
        loss = stratified_loss(
            error_sq[:n_damage],
            error_sq[n_damage:],
            strata["p_active"],
            strata["p_background"],
        )
        if not bool(torch.isfinite(loss)):
            raise FloatingPointError(f"nonfinite loss at step {step}")
        scheduler.before_update(step)
        loss.backward()
        if any(
            p.grad is not None and not bool(torch.isfinite(p.grad).all())
            for p in model.residual.parameters()
        ):
            raise FloatingPointError(f"nonfinite gradient at step {step}")
        optimizer.step()
        scheduler.step()
        last_loss = float(loss.detach())
        if step in MONITOR_STEPS:
            entry = monitor_full_field(
                model, xy, target, data["mass"], data["damage"], step
            )
            snapshot_uv = predict_in_chunks(model, xy).cpu().numpy()
            entry.update(
                support_diagnostics(snapshot_uv, evaluated_base, data, geometry)
            )
            if (
                args.arm == "localized"
                and entry["outside_support_max_abs_delta"] > 1e-12
            ):
                raise RuntimeError("outside-support preservation failed")
            monitor.append(entry)
            print(
                json.dumps(
                    {
                        **entry,
                        "sampled_loss": last_loss,
                        "lr_used": scheduler.used[-1],
                        "lr_next": scheduler.next_lr,
                    }
                ),
                flush=True,
            )

    if sampler_digest.hexdigest() != CONTROL_LOCKS[args.state]["sampler_index_sha256"]:
        raise RuntimeError("historical paired sampling stream mismatch")
    lr_values = np.asarray(scheduler.used, dtype="<f8")
    schedule = schedule_identity(lr_values)
    check_schedule_identity(schedule, lr_values)
    predicted = predict_in_chunks(model, xy).cpu().numpy()
    if state_digest(model.backbone) != backbone_digest or any(
        p.requires_grad for p in model.backbone.parameters()
    ):
        raise RuntimeError("backbone mutated")
    if (
        sha256(args.backbone_dir / "final_step_10000.pt")
        != backbone_lock["checkpoint_sha256"]
    ):
        raise RuntimeError("inherited checkpoint mutated")
    diagnostics = support_diagnostics(predicted, evaluated_base, data, geometry)
    if args.arm == "localized" and diagnostics["outside_support_max_abs_delta"] > 1e-12:
        raise RuntimeError("outside support drift")
    metrics = final_metrics(data, predicted)
    if not np.isclose(
        monitor[-1]["displacement_mass_rms_over_abs_Us"],
        metrics["displacement_mass_rms_over_abs_Us"],
        rtol=0.0,
        atol=1e-14,
    ):
        raise RuntimeError("final monitoring metric mismatch")
    reference_sha_after = sha256(args.reference)
    if reference_sha_after != data["reference_sha256"]:
        raise RuntimeError("reference file mutated during training")

    args.out.mkdir(parents=True, exist_ok=False)
    lr_path = args.out / "learning_rates.npy"
    np.save(lr_path, lr_values, allow_pickle=False)
    lr_sha = sha256(lr_path)
    checkpoint = args.out / "final_step_10000.pt"
    torch.save(
        {
            "protocol_revision": PROTOCOL_REVISION,
            "paired_control_lock": CONTROL_LOCKS[args.state],
            "lr_schedule": schedule,
            "learning_rates_sha256": lr_sha,
            "state": args.state,
            "seed": args.seed,
            "alpha": args.alpha,
            "arm": args.arm,
            "step": STEPS,
            "sampler": {
                "damage_threshold": DAMAGE_THRESHOLD,
                "n_damage": n_damage,
                "n_background": n_background,
                "sample_seed": args.seed + SAMPLE_SEED_OFFSET,
                "order": "damage_then_background_no_shuffle",
            },
            "geometry": geometry,
            "parameter_count": PARAMETER_COUNT,
            "residual_parameter_count": RESIDUAL_PARAMETER_COUNT,
            "backbone_lock": backbone_lock,
            "backbone_digest": backbone_digest,
            "initial_residual_digest": initial_residual_digest,
            "sampler_index_sha256": sampler_digest.hexdigest(),
            "model_state_dict": {
                k: v.detach().cpu() for k, v in model.state_dict().items()
            },
        },
        checkpoint,
    )
    prediction = args.out / "prediction.npz"
    np.savez_compressed(prediction, uv=predicted)
    monitor_path = args.out / "monitoring.json"
    monitor_path.write_text(json.dumps(monitor, indent=2), encoding="utf-8")
    result = {
        "status": "COMPLETED",
        "protocol_revision": PROTOCOL_REVISION,
        "paired_control_lock": CONTROL_LOCKS[args.state],
        "lr_schedule": schedule,
        "learning_rates_sha256": lr_sha,
        "state": args.state,
        "seed": args.seed,
        "alpha": args.alpha,
        "arm": args.arm,
        "reference_sha256": data["reference_sha256"],
        "reference_sha256_after": reference_sha_after,
        "checkpoint_sha256": sha256(checkpoint),
        "prediction_sha256": sha256(prediction),
        "monitoring_sha256": sha256(monitor_path),
        "steps": STEPS,
        "batch_nodes": BATCH_NODES,
        "geometry": geometry,
        "parameter_count": PARAMETER_COUNT,
        "residual_parameter_count": RESIDUAL_PARAMETER_COUNT,
        "backbone_lock": backbone_lock,
        "backbone_digest": backbone_digest,
        "initial_residual_digest": initial_residual_digest,
        "sampler_index_sha256": sampler_digest.hexdigest(),
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
        "historical_control_admission": paired,
        "baseline_metrics": baseline_metrics,
        "baseline_regions": monitor[0],
        "support_diagnostics": diagnostics,
        "backbone_frozen": True,
        "new_optimizer_steps": STEPS,
        "inherited_optimizer_steps": 10000,
        "metrics": metrics,
    }
    metrics_path = args.out / "metrics.json"
    metrics_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    archive_root = Path(args.archive_root)
    archive_root.mkdir(parents=True, exist_ok=False)
    archive_hashes = {}
    for asset in (checkpoint, prediction, monitor_path, metrics_path, lr_path):
        copied = archive_root / asset.name
        shutil.copy2(asset, copied)
        source_hash = sha256(asset)
        if sha256(copied) != source_hash:
            raise RuntimeError(f"archive copy verification failed for {asset.name}")
        archive_hashes[asset.name] = source_hash
    receipt = {
        "status": "COMPLETED",
        "run_id": args.run_id,
        "protocol_revision": PROTOCOL_REVISION,
        "paired_control_lock": CONTROL_LOCKS[args.state],
        "lr_schedule": schedule,
        "learning_rates_sha256": lr_sha,
        "state": args.state,
        "seed": args.seed,
        "alpha": args.alpha,
        "arm": args.arm,
        "producer_alias": "taobo",
        "hostname": socket.gethostname(),
        "code_commit": actual_commit,
        "dirty": dirty,
        "command": shlex.join(os.sys.argv),
        "pid": os.getpid(),
        "cuda_visible_devices": visible,
        "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        "gpu": torch.cuda.get_device_name(device),
        "output_root": str(args.out.resolve()),
        "archive_root": args.archive_root,
        "log_path": args.log_path,
        "started_utc": started_utc,
        "finished_utc": result["finished_utc"],
        "checkpoint_sha256": result["checkpoint_sha256"],
        "prediction_sha256": result["prediction_sha256"],
        "monitoring_sha256": result["monitoring_sha256"],
        "metrics_sha256": sha256(metrics_path),
        "reference_sha256": result["reference_sha256"],
        "archive_status": "VERIFIED_COPY",
        "archive_file_hashes": archive_hashes,
        "backbone_lock": backbone_lock,
        "backbone_digest": backbone_digest,
        "initial_residual_digest": initial_residual_digest,
        "sampler_index_sha256": sampler_digest.hexdigest(),
    }
    receipt_text = json.dumps(receipt, indent=2)
    (args.out / "RUN_RECEIPT.json").write_text(receipt_text, encoding="utf-8")
    (archive_root / "RUN_RECEIPT.json").write_text(receipt_text, encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--alpha", choices=tuple(ALLOCATIONS), default="0.7")
    parser.add_argument("--state", choices=tuple(EXPECTED), required=True)
    parser.add_argument("--seed", choices=SEEDS, type=int, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--backbone-dir", type=Path, required=True)
    parser.add_argument("--control-dir", type=Path, required=True)
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
                parser.error(
                    f"--{name.replace('_', '-')} is required for formal training"
                )
        if len(args.expected_commit) != 40 or any(
            c not in "0123456789abcdef" for c in args.expected_commit
        ):
            parser.error("--expected-commit must be a lowercase 40-character git SHA")
        for name, prefix in {
            "out": "/mnt/data2/drtao/wennie/",
            "archive_root": "/mnt/data2/drtao/pidl_archives/",
            "log_path": "/mnt/data2/drtao/wennie/",
        }.items():
            value = str(Path(getattr(args, name)).expanduser().resolve())
            if not value.startswith(prefix) or args.run_id not in value:
                parser.error(
                    f"--{name.replace('_', '-')} must be under {prefix} and contain --run-id"
                )
        if Path(args.archive_root).exists():
            parser.error("--archive-root must not already exist")
    if args.out is not None and args.out.exists():
        parser.error("--out must not already exist")
    return args


def main() -> None:
    args = parse_args()
    data = validate_reference(args.state, args.reference)
    if args.validate_only:
        backbone, base, lock = admit_backbone(args.state, args.backbone_dir, data)
        control = admit_control(args.state, args.control_dir, data, backbone)
        n_damage, n_background = ALLOCATIONS[args.alpha]
        strata = make_strata(data["damage"], data["mass"])
        print(
            json.dumps(
                {
                    "status": "VALIDATION_ONLY_PASS",
                    "paired_control_run_id": control["lock"]["run_id"],
                    "control_regions": control["regions"],
                    "historical_reference_rho": {
                        "recorded": control["reference_rho_u_recorded"],
                        "current": control["reference_rho_u_current"],
                        "policy": control["rho_portability_policy"],
                    },
                    "actual_update_lr": {
                        str(k): update_lr(k) for k in (1, 8000, 8001, 9000, 9999, 10000)
                    },
                    "training": False,
                    "state": args.state,
                    "seed": args.seed,
                    "alpha": args.alpha,
                    "arm": args.arm,
                    "reference_sha256": data["reference_sha256"],
                    "reference_rho_u": data["reference_rho_u"],
                    "p_damage": strata["p_active"],
                    "damage_node_count": strata["active_count"],
                    "n_damage": n_damage,
                    "n_background": n_background,
                },
                indent=2,
            )
        )
        return
    print(json.dumps(train(args, data), indent=2), flush=True)


if __name__ == "__main__":
    main()
