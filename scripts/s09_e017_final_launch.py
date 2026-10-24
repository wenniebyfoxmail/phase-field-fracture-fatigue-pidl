#!/usr/bin/env python3
"""Detached remote resolver-to-producer boundary for the frozen E017 run."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys


RUN_ID = "S09-E017-R001-factorised-head-p0"


def _write_once(path: Path, value: dict) -> None:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _redirect(log_path: Path) -> None:
    descriptor = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.dup2(descriptor, 1)
    os.dup2(descriptor, 2)
    os.close(descriptor)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--session-name", required=True)
    parser.add_argument("--log-path", type=Path, required=True)
    args = parser.parse_args()
    control = args.control_root
    started_path = control / "final_launch_started.json"
    failure_path = control / "final_launch_failure.json"
    _redirect(args.log_path)
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--code-root",
        str(args.code_root),
        "--control-root",
        str(control),
        "--session-name",
        args.session_name,
        "--log-path",
        str(args.log_path),
    ]
    started = {
        "schema_version": "s09-e017-final-launch-started-v1",
        "terminal_state": "FINAL_LAUNCH_PROCESS_STARTED",
        "run_id": RUN_ID,
        "started_at": datetime.now().astimezone().isoformat(),
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "uid": os.getuid(),
        "cwd": str(args.code_root),
        "session_name": args.session_name,
        "log_path": str(args.log_path),
        "command": command,
        "retry": False,
        "resume": False,
    }
    _write_once(started_path, started)
    resolver = [
        "python3",
        "scripts/resolve_s09_e017_execution.py",
        "--base-package-config",
        "docs/research/S09/S09-E017/final_run_package_config_20261019.json",
        "--execution-candidate",
        "docs/research/S09/S09-E017/final_execution_candidate_20261020.json",
        "--execution-authority",
        str(control / "execution_authority.json"),
        "--code-archive",
        str(control / "code.tar.gz"),
        "--output-config",
        str(control / "config_resolved.json"),
        "--output-receipt",
        str(control / "resolution_receipt.json"),
        "--resolve-authorised-config",
    ]
    producer = [
        "python3",
        "scripts/run_s09_e017_producer.py",
        "--resolved-config",
        str(control / "config_resolved.json"),
        "--base-package-config",
        str(
            args.code_root
            / "docs/research/S09/S09-E017/final_run_package_config_20261019.json"
        ),
        "--execution-candidate",
        str(
            args.code_root
            / "docs/research/S09/S09-E017/final_execution_candidate_20261020.json"
        ),
        "--execution-authority",
        str(control / "execution_authority.json"),
        "--code-archive",
        str(control / "code.tar.gz"),
        "--control-dir",
        str(control),
        "--packet-dir",
        "/mnt/data2/drtao/wennie/S09-E008-P1-STAGING-20261016/packet",
        "--base-runtime-config",
        str(
            args.code_root
            / "docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json"
        ),
        "--initial-checkpoint",
        "/mnt/data2/drtao/wennie/S09-E010-R001-support-amplitude-three-arm/B25_support_amplitude_beta0p25/checkpoint_update500.pt",
        "--output-dir",
        "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/run",
        "--execute-reviewed-run",
    ]
    environment = os.environ.copy()
    environment.update(
        {
            "CUDA_VISIBLE_DEVICES": "5",
            "TMPDIR": "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/tmp",
            "XDG_CACHE_HOME": (
                "/mnt/data2/drtao/wennie/S09-E017-R001-factorised-head-p0/cache"
            ),
        }
    )
    try:
        subprocess.run(resolver, cwd=args.code_root, env=environment, check=True)
    except Exception as error:
        _write_once(
            failure_path,
            {
                "schema_version": "s09-e017-final-launch-failure-v1",
                "terminal_state": "FINAL_LAUNCH_STOPPED_BEFORE_PRODUCER",
                "run_id": RUN_ID,
                "first_reason": f"{type(error).__name__}: {error}",
                "producer_invoked": False,
                "retry": False,
                "resume": False,
            },
        )
        raise
    os.chdir(args.code_root)
    os.execvpe(producer[0], producer, environment)


if __name__ == "__main__":
    main()
