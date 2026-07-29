#!/usr/bin/env python3
"""Dispatch the frozen 36-job factorial LOCO matrix across explicit GPUs."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--gpus", default="0,1,2,3,4,5,6,7")
    parser.add_argument("--poll-seconds", type=float, default=15.0)
    return parser.parse_args()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_state(path: Path, state: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def main() -> None:
    args = parse_args()
    if sys.platform == "darwin":
        raise RuntimeError("producer dispatcher cannot run on Mac")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("job_count") != 36 or set(manifest.get("models", {})) != {
        "markov", "tcn", "transformer"
    }:
        raise ValueError("producer manifest is not the sealed 36-job matrix")
    data_manifest = json.loads((args.data_root / "RUN_MANIFEST.json").read_text())
    if data_manifest.get("trajectory_count") != 4 or data_manifest.get("state_count") != 348:
        raise ValueError("materialised data inventory differs from the sealed contract")
    gpus = [int(value) for value in args.gpus.split(",") if value.strip()]
    if not gpus or len(set(gpus)) != len(gpus):
        raise ValueError("GPU list must be non-empty and unique")
    args.out_root.mkdir(parents=True, exist_ok=True)
    (args.out_root / "logs").mkdir(exist_ok=True)
    state_path = args.out_root / "dispatcher_state.json"
    state = {
        "status": "running",
        "started_at": now(),
        "manifest": str(args.manifest.resolve()),
        "data_root": str(args.data_root.resolve()),
        "jobs": {},
    }
    pending = list(manifest["jobs"])
    running: dict[int, tuple[subprocess.Popen, object, dict]] = {}
    failures = 0

    while pending or running:
        for gpu in gpus:
            if not pending or gpu in running:
                continue
            job = pending.pop(0)
            family = job["family"]
            spec = manifest["models"][family]
            out = args.out_root / "runs" / job["job_id"]
            out.mkdir(parents=True, exist_ok=True)
            log_path = args.out_root / "logs" / f"{job['job_id']}.log"
            command = [
                sys.executable,
                "-u",
                str(HERE / "train_factorial_loco_temporal_operator.py"),
                "--data-root", str(args.data_root),
                "--heldout", job["held_out_trajectory_id"],
                "--family", family,
                "--seed", str(job["seed"]),
                "--context", str(job["context"]),
                "--temporal-width", str(spec["temporal_width"]),
                "--local-dim", str(spec["local_dim"]),
                "--token-dim", str(spec["token_dim"]),
                "--steps", str(job["steps"]),
                "--out", str(out),
                "--device", "cuda",
            ]
            env = dict(os.environ)
            env["CUDA_VISIBLE_DEVICES"] = str(gpu)
            env.setdefault("TMPDIR", str(args.out_root / "tmp"))
            Path(env["TMPDIR"]).mkdir(parents=True, exist_ok=True)
            log_handle = log_path.open("w", encoding="utf-8")
            process = subprocess.Popen(
                command,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                cwd=HERE.parent,
                env=env,
            )
            running[gpu] = (process, log_handle, job)
            state["jobs"][job["job_id"]] = {
                "status": "running",
                "gpu": gpu,
                "pid": process.pid,
                "started_at": now(),
                "log": str(log_path),
                "out": str(out),
                "command": command,
            }
            write_state(state_path, state)

        time.sleep(args.poll_seconds)
        for gpu, (process, log_handle, job) in list(running.items()):
            returncode = process.poll()
            if returncode is None:
                continue
            log_handle.close()
            entry = state["jobs"][job["job_id"]]
            entry.update(
                {
                    "status": "complete" if returncode == 0 else "failed",
                    "returncode": returncode,
                    "finished_at": now(),
                }
            )
            if returncode != 0:
                failures += 1
            del running[gpu]
            write_state(state_path, state)

    state["status"] = "complete" if failures == 0 else "complete_with_failures"
    state["finished_at"] = now()
    state["failure_count"] = failures
    write_state(state_path, state)
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()

