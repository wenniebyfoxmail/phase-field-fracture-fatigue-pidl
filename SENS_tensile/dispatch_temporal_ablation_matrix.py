#!/usr/bin/env python3
"""Dispatch explicit validation-selected temporal ablations on producer GPUs."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "source"))

from dispatch_temporal_architecture_matrix import gpu_memory_mib, parse_gpu_list, write_status  # noqa: E402
from run_temporal_architecture_matrix import command_for, load_and_validate_protocol  # noqa: E402
from temporal_mesh_operator import match_temporal_width  # noqa: E402


VALID_ABLATIONS = (
    "context_1",
    "context_3",
    "context_5",
    "context_10",
    "context_20",
    "pointwise",
    "teacher_forcing",
    "one_step",
)


def parse_csv(text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip() for value in text.split(",") if value.strip()))


def parse_seeds(text: str) -> tuple[int, ...]:
    values = tuple(int(value) for value in parse_csv(text))
    if not values or min(values) < 1:
        raise argparse.ArgumentTypeError("seeds must be positive integers")
    return values


def replace_argument(command: list[str], name: str, value: str) -> None:
    command[command.index(name) + 1] = value


def pointwise_width(protocol: dict, family: str) -> int:
    architecture = protocol["shared_architecture"]
    match = match_temporal_width(
        family,
        target_parameters=protocol["capacity_gate"]["target_parameters"],
        tolerance=protocol["capacity_gate"]["relative_tolerance"],
        model_kwargs={
            "metadata_dim": 0,
            "local_dim": architecture["local_dim"],
            "token_dim": architecture["token_dim"],
            "local_layers": architecture["local_layers"],
            "coarse_layers": architecture["coarse_layers"],
            "graph_enabled": False,
            "max_context": max(architecture["context_candidates"]),
            "transformer_heads": architecture["transformer_heads"],
        },
        candidate_widths=range(8, 601, 4),
    )
    return match.width


def ablation_command(
    protocol: dict,
    dataset: Path,
    output: Path,
    family: str,
    seed: int,
    ablation: str,
) -> list[str]:
    command = command_for(
        protocol,
        dataset,
        output,
        family,
        seed,
        int(protocol["optimization"]["steps"]),
    )
    if ablation.startswith("context_"):
        replace_argument(command, "--context-lengths", ablation.split("_", 1)[1])
    elif ablation == "pointwise":
        command.extend(["--spatial-encoder", "pointwise"])
        replace_argument(command, "--temporal-width", str(pointwise_width(protocol, family)))
    elif ablation == "teacher_forcing":
        replace_argument(command, "--teacher-forcing-ratio", "1.0")
    elif ablation == "one_step":
        replace_argument(command, "--rollout-steps", "1")
    else:
        raise ValueError(f"unknown ablation {ablation}")
    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--family", required=True)
    parser.add_argument("--ablations", type=parse_csv, required=True)
    parser.add_argument("--seeds", type=parse_seeds, default=(1,))
    parser.add_argument("--gpus", type=parse_gpu_list, required=True)
    parser.add_argument("--tmp-root", type=Path, required=True)
    parser.add_argument("--poll-seconds", type=int, default=20)
    parser.add_argument("--free-memory-threshold-mib", type=int, default=256)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    invalid = sorted(set(args.ablations) - set(VALID_ABLATIONS))
    if invalid:
        raise ValueError(f"unknown ablations: {invalid}")
    protocol = load_and_validate_protocol(args.dataset.resolve())
    if args.family not in protocol["capacity_gate"]["matched_widths"]:
        raise ValueError(f"family {args.family!r} is not in the sealed core matrix")
    jobs = [
        {
            "family": args.family,
            "ablation": ablation,
            "seed": seed,
            "state": "PENDING",
            "tag": f"{args.family}_{ablation}_seed{seed}",
        }
        for ablation in args.ablations
        for seed in args.seeds
    ]
    for job in jobs:
        output = args.out_root / "ablations" / str(job["tag"])
        job["output"] = str(output)
        job["command"] = ablation_command(
            protocol,
            args.dataset.resolve(),
            output,
            args.family,
            int(job["seed"]),
            str(job["ablation"]),
        )
        if (output / "RUN_MANIFEST.json").exists():
            job["state"] = "DONE"
            job["resume_reason"] = "existing RUN_MANIFEST.json"
    if args.dry_run:
        print(json.dumps({"family": args.family, "gpus": args.gpus, "jobs": jobs}, indent=2))
        return
    if sys.platform == "darwin":
        raise RuntimeError("ablation execution is disabled on Mac")

    args.tmp_root.mkdir(parents=True, exist_ok=True)
    log_root = args.out_root / "ablation_logs"
    log_root.mkdir(parents=True, exist_ok=True)
    tag = f"{args.family}_{int(time.time())}"
    status_path = args.out_root / f"ablation_dispatcher_{tag}.json"
    running: dict[int, tuple[subprocess.Popen, dict, object]] = {}
    started = time.time()
    status: dict = {}
    while any(job["state"] in {"PENDING", "RUNNING"} for job in jobs):
        for gpu, (process, job, handle) in list(running.items()):
            returncode = process.poll()
            if returncode is None:
                continue
            handle.close()
            job["returncode"] = returncode
            job["finished_unix"] = time.time()
            job["state"] = "DONE" if returncode == 0 else "FAILED"
            del running[gpu]

        failed = any(job["state"] == "FAILED" for job in jobs)
        if failed:
            for job in jobs:
                if job["state"] == "PENDING":
                    job["state"] = "BLOCKED"
                    job["blocked_reason"] = "an earlier ablation failed"
        pending = [job for job in jobs if job["state"] == "PENDING"]
        for gpu in (() if failed else args.gpus):
            if not pending or gpu in running:
                continue
            used = gpu_memory_mib(gpu)
            if used > args.free_memory_threshold_mib:
                continue
            job = pending.pop(0)
            log_path = log_root / f"{job['tag']}_gpu{gpu}.log"
            handle = log_path.open("a", encoding="utf-8")
            environment = os.environ.copy()
            environment["CUDA_VISIBLE_DEVICES"] = str(gpu)
            environment["TMPDIR"] = str(args.tmp_root / f"gpu{gpu}")
            Path(environment["TMPDIR"]).mkdir(parents=True, exist_ok=True)
            process = subprocess.Popen(
                job["command"], cwd=ROOT, env=environment,
                stdout=handle, stderr=subprocess.STDOUT,
            )
            job.update(
                {
                    "state": "RUNNING",
                    "gpu": gpu,
                    "pid": process.pid,
                    "log": str(log_path),
                    "started_unix": time.time(),
                    "gpu_memory_before_mib": used,
                }
            )
            running[gpu] = (process, job, handle)

        status = {
            "protocol_id": protocol["protocol_id"],
            "manager_pid": os.getpid(),
            "family": args.family,
            "started_unix": started,
            "updated_unix": time.time(),
            "allowed_gpus": args.gpus,
            "jobs": jobs,
        }
        write_status(status_path, status)
        if any(job["state"] in {"PENDING", "RUNNING"} for job in jobs):
            time.sleep(args.poll_seconds)
    status["completed_unix"] = time.time()
    write_status(status_path, status)
    if any(job["state"] == "FAILED" for job in jobs):
        raise RuntimeError("an ablation failed; inspect status and logs")


if __name__ == "__main__":
    main()
