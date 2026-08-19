#!/usr/bin/env python3
"""Run the approved Taobo-only S4/S8/S16 seed-1 c60 producer stage."""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

from loading_cadence_smoke import (
    SCHEDULES,
    semantic_torch_hash,
    sha256,
    validate_archive,
    validate_nested_schedules,
    write_json,
)


N_CYCLES = 60
SEED = 1


def cycle_csv() -> str:
    return ",".join(str(cycle) for cycle in range(1, N_CYCLES + 1))


def run(command: list[str], log_path: Path, cwd: Path) -> dict[str, object]:
    started = time.time()
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"[command] {shlex.join(command)}\n")
        log.write(f"[started_unix] {started:.6f}\n")
        proc = subprocess.run(
            command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, check=False
        )
    ended = time.time()
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"[ended_unix] {ended:.6f}\n")
        log.write(f"\n[wall_seconds] {ended - started:.6f}\n")
    if proc.returncode:
        raise RuntimeError(f"command failed rc={proc.returncode}; see {log_path}")
    return {
        "command": shlex.join(command),
        "log": str(log_path),
        "started_unix": started,
        "ended_unix": ended,
        "wall_seconds": ended - started,
        "returncode": proc.returncode,
    }


def common_command(runner: Path, archive_name: str) -> list[str]:
    diagnostics = cycle_csv()
    return [
        sys.executable,
        "-u",
        str(runner),
        "0.12",
        "--n-cycles-physical",
        str(N_CYCLES),
        "--seed",
        str(SEED),
        "--hidden-layers",
        "8",
        "--neurons",
        "400",
        "--init-coeff",
        "1.0",
        "--history-driver-reduction-mode",
        "fem_gp_tri3_g_mean",
        "--fem-irr-penalty",
        "--hard-alpha-recovery-step",
        "--hard-alpha-target",
        "1.0",
        "--diag-physical-cycles",
        diagnostics,
        "--diag-full-physical-cycles",
        diagnostics,
        "--plot-every",
        "1000000",
        "--fixed-horizon",
        "--archive-name",
        archive_name,
        "--tag",
        "cadenceC60Seed1Production",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--approval-reference", required=True)
    args = parser.parse_args()
    archive_root_raw = os.environ.get("PIDL_ARCHIVE_DIR")
    if not archive_root_raw:
        parser.error("PIDL_ARCHIVE_DIR is required")
    archive_root = Path(archive_root_raw).resolve()
    here = Path(__file__).resolve().parent
    runner = here / "run_fem_mesh_probe_driver_umax.py"
    helper = here / "loading_cadence_smoke.py"
    mesh = here / "meshed_geom_fem_soft_hist0.msh"
    logs = archive_root / "production_logs"
    manifest_path = archive_root / "cadence_c60_seed1_manifest.json"
    receipt_path = archive_root / "cadence_c60_seed1_producer_receipt.json"

    if socket.gethostname() != "GPUServer8" or not torch.cuda.is_available():
        raise RuntimeError("c60 production is guarded to Taobo GPUServer8 with CUDA")
    visible_gpu = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if not visible_gpu.isdigit():
        raise RuntimeError("CUDA_VISIBLE_DEVICES must name exactly one physical GPU index")
    if manifest_path.exists() or receipt_path.exists() or any(
        archive_root.glob(f"{args.run_id}_*")
    ):
        raise FileExistsError("fresh archive-root contract violated")
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=here.parent, text=True
    ).strip()
    if dirty:
        raise RuntimeError(f"producer checkout must be clean before launch: {dirty[:500]}")

    logs.mkdir(parents=True, exist_ok=True)
    validate_nested_schedules()
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=here.parent, text=True
    ).strip()
    git_branch = subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=here.parent, text=True
    ).strip()
    manifest = {
        "run_id": args.run_id,
        "scope": "approved Taobo-only S4/S8/S16 seed1 fixed-horizon c60 producer stage",
        "claim_boundary": "producer completion is not cadence-convergence acceptance",
        "approval_reference": args.approval_reference,
        "commit": commit,
        "branch": git_branch,
        "runner_sha256": sha256(runner),
        "helper_sha256": sha256(helper),
        "wrapper_sha256": sha256(Path(__file__).resolve()),
        "model_train_sha256": sha256(here.parent / "source" / "model_train.py"),
        "mesh_sha256": sha256(mesh),
        "python": sys.version,
        "numpy": np.__version__,
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_visible_devices": visible_gpu,
        "hostname": socket.gethostname(),
        "gpu_name": torch.cuda.get_device_name(0),
        "gpu_uuid": subprocess.check_output(
            [
                "nvidia-smi",
                "-i",
                visible_gpu,
                "--query-gpu=uuid",
                "--format=csv,noheader",
            ],
            text=True,
        ).strip(),
        "pidl_archive_dir": str(archive_root),
        "schedules": SCHEDULES,
        "umax": 0.12,
        "physical_cycles": N_CYCLES,
        "seed": SEED,
        "diagnostic_cycles": list(range(1, N_CYCLES + 1)),
        "bc": "exact_bc=False; bottom u=v=0; top u=0,v=U on full edges",
        "optimizer_state_contract": (
            "no cross-step optimizer state: model_train.py recreates RPROP/LBFGS "
            "inside each retained-state solve and checkpoints no optimizer"
        ),
    }
    write_json(manifest_path, manifest)

    producer_name = f"{args.run_id}_state0_seed{SEED}"
    producer = archive_root / producer_name
    recovery_cmd = common_command(runner, producer_name) + [
        "--displacement-steps",
        "0.06,0.12,0.06,0",
        "--recovery-only",
    ]
    runtimes: dict[str, dict[str, object]] = {}
    runtimes["state0_producer"] = run(
        recovery_cmd, logs / "state0_producer.log", here
    )
    producer_model = producer / "best_models" / "trained_1NN_0.pt"
    producer_history = producer / "best_models" / "checkpoint_step_0.pt"
    producer_hashes = {
        "model_file": sha256(producer_model),
        "history_file": sha256(producer_history),
        "model_semantic": semantic_torch_hash(producer_model),
        "history_semantic": semantic_torch_hash(producer_history),
    }

    results = []
    for level, factors in SCHEDULES.items():
        branch_name = f"{args.run_id}_{level}_seed{SEED}_c{N_CYCLES}"
        branch_archive = archive_root / branch_name
        if branch_archive.exists():
            raise FileExistsError(f"fresh-run contract violated: {branch_archive}")
        shutil.copytree(producer, branch_archive, copy_function=shutil.copy2)
        displacement = ",".join(f"{0.12 * value:.8g}" for value in factors)
        command = common_command(runner, branch_name) + [
            "--displacement-steps",
            displacement,
        ]
        runtimes[level] = run(command, logs / f"{level}.log", here)
        branch_log = (logs / f"{level}.log").read_text(
            encoding="utf-8", errors="replace"
        )
        if "从 step 0 恢复，继续 step 1/" not in branch_log:
            raise RuntimeError(f"{level} did not prove resume from shared step0")
        results.append(validate_archive(branch_archive, level, mesh, N_CYCLES))

    model_hashes = {item["state0_model_sha256"] for item in results}
    history_hashes = {item["state0_history_sha256"] for item in results}
    model_semantic = {item["state0_model_semantic_sha256"] for item in results}
    history_semantic = {item["state0_history_semantic_sha256"] for item in results}
    if (
        len(model_hashes) != 1
        or len(history_hashes) != 1
        or len(model_semantic) != 1
        or len(history_semantic) != 1
        or next(iter(model_hashes)) != producer_hashes["model_file"]
        or next(iter(history_hashes)) != producer_hashes["history_file"]
        or next(iter(model_semantic)) != producer_hashes["model_semantic"]
        or next(iter(history_semantic)) != producer_hashes["history_semantic"]
    ):
        raise RuntimeError("forked state0 files are not identical across levels")

    receipt = {
        "run_id": args.run_id,
        "status": "PASS_C60_PRODUCER_COMPLETE",
        "claim_boundary": "requires locked post-processing before any convergence verdict",
        "commit": commit,
        "branch": git_branch,
        "manifest": str(manifest_path),
        "levels": results,
        "runtime": runtimes,
        "shared_state0": {
            "model_sha256": next(iter(model_hashes)),
            "history_sha256": next(iter(history_hashes)),
            "model_semantic_sha256": next(iter(model_semantic)),
            "history_semantic_sha256": next(iter(history_semantic)),
            "producer_hashes": producer_hashes,
            "fork_method": "copy2 from one recovery-only producer before step1",
            "optimizer_state": "not_applicable_ephemeral_per_retained_state",
        },
        "scope": "S4/S8/S16 seed1 c60 producer only; no convergence claim",
    }
    write_json(receipt_path, receipt)
    print(f"PASS_C60_PRODUCER_COMPLETE receipt={receipt_path}")


if __name__ == "__main__":
    main()
