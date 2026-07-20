#!/usr/bin/env python3
"""Safely dispatch checkpoint-only multi-origin evaluations over allowed GPUs."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
CORE_STAGES = {"core_1", "core_2"}


def gpu_memory_mib(gpu: int) -> int:
    completed = subprocess.run(
        [
            "nvidia-smi",
            f"--id={gpu}",
            "--query-gpu=memory.used",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(completed.stdout.strip().splitlines()[0])


def parse_gpu_list(text: str) -> tuple[int, ...]:
    values = tuple(dict.fromkeys(int(value.strip()) for value in text.split(",") if value.strip()))
    if not values or min(values) < 0:
        raise argparse.ArgumentTypeError("provide non-negative GPU indices")
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--sparse-c87", type=Path, required=True)
    parser.add_argument("--sparse-c87-sha256", required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--gpus", type=parse_gpu_list, required=True)
    parser.add_argument("--tmp-root", type=Path, required=True)
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--free-memory-threshold-mib", type=int, default=256)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def discover_jobs(root: Path) -> list[dict]:
    jobs = []
    for manifest_path in sorted(root.rglob("RUN_MANIFEST.json")):
        if manifest_path.parent.parent.name not in CORE_STAGES:
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        jobs.append(
            {
                "family": manifest["temporal_model"],
                "seed": int(manifest["seed"]),
                "checkpoint_run_dir": str(manifest_path.parent),
                "state": "PENDING",
            }
        )
    if len(jobs) != 18:
        raise ValueError(f"expected 18 frozen core runs, found {len(jobs)}")
    return jobs


def write_status(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    args = parse_args()
    jobs = discover_jobs(args.runs_root)
    for job in jobs:
        output = args.out_root / f"{job['family']}_seed{job['seed']}"
        job["output"] = str(output)
        if (output / "MULTI_ORIGIN_MANIFEST.json").exists():
            job["state"] = "DONE"
            job["resume_reason"] = "existing MULTI_ORIGIN_MANIFEST.json"
    if args.dry_run:
        print(json.dumps({"gpus": args.gpus, "jobs": jobs}, indent=2))
        return
    if sys.platform == "darwin":
        raise RuntimeError("producer dispatcher is disabled on Mac")
    if args.poll_seconds < 1:
        raise ValueError("poll-seconds must be positive")

    args.out_root.mkdir(parents=True, exist_ok=True)
    args.tmp_root.mkdir(parents=True, exist_ok=True)
    log_root = args.out_root / "logs"
    log_root.mkdir(parents=True, exist_ok=True)
    status_path = args.out_root / "dispatcher_status.json"
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
                    job["blocked_reason"] = "an earlier evaluation failed"
        pending = [job for job in jobs if job["state"] == "PENDING"]
        for gpu in (() if failed else args.gpus):
            if not pending or gpu in running:
                continue
            used = gpu_memory_mib(gpu)
            if used > args.free_memory_threshold_mib:
                continue
            job = pending.pop(0)
            output = Path(job["output"])
            output.mkdir(parents=True, exist_ok=True)
            log_path = log_root / f"{job['family']}_seed{job['seed']}_gpu{gpu}.log"
            handle = log_path.open("a", encoding="utf-8")
            environment = os.environ.copy()
            environment["CUDA_VISIBLE_DEVICES"] = str(gpu)
            environment["TMPDIR"] = str(args.tmp_root / f"gpu{gpu}")
            Path(environment["TMPDIR"]).mkdir(parents=True, exist_ok=True)
            command = [
                sys.executable,
                "-u",
                str(HERE / "evaluate_temporal_multi_origin_checkpoint.py"),
                "--dataset",
                str(args.dataset.resolve()),
                "--checkpoint-run-dir",
                job["checkpoint_run_dir"],
                "--sparse-c87",
                str(args.sparse_c87.resolve()),
                "--sparse-c87-sha256",
                args.sparse_c87_sha256,
                "--out",
                str(output),
                "--device",
                "cuda",
            ]
            process = subprocess.Popen(
                command,
                cwd=HERE.parent,
                env=environment,
                stdout=handle,
                stderr=subprocess.STDOUT,
            )
            job.update(
                {
                    "state": "RUNNING",
                    "gpu": gpu,
                    "pid": process.pid,
                    "log": str(log_path),
                    "started_unix": time.time(),
                    "gpu_memory_before_mib": used,
                    "command": command,
                }
            )
            running[gpu] = (process, job, handle)

        status = {
            "protocol_id": "temporal_multi_origin_reanalysis_v1_20260720",
            "manager_pid": os.getpid(),
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
        raise RuntimeError("a multi-origin evaluation failed; inspect dispatcher status")


if __name__ == "__main__":
    main()
