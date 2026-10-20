#!/usr/bin/env python3
"""Disabled-by-default launch boundary for S09-E017."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e017_producer_package import (  # noqa: E402
    assert_launch_enabled,
    resolve_real_bindings,
)
from s09_e017_execution_control import (  # noqa: E402
    canonical_json,
    control_admission,
    process_identity,
    resource_snapshot,
    sha256_bytes,
    sha256_path,
    validate_execution_candidate,
    validate_runtime_control,
)


def _strict_json(path: Path):
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolved-config", type=Path, required=True)
    parser.add_argument("--packet-dir", type=Path)
    parser.add_argument("--base-runtime-config", type=Path)
    parser.add_argument("--initial-checkpoint", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--execution-candidate", type=Path)
    parser.add_argument("--execution-authority", type=Path)
    parser.add_argument("--code-archive", type=Path)
    parser.add_argument("--control-dir", type=Path)
    parser.add_argument("--execute-reviewed-run", action="store_true")
    args = parser.parse_args()
    config = _strict_json(args.resolved_config)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    # The tracked candidate always stops here.  Only a later exact reviewed,
    # resolved config may pass this gate and import scientific dependencies.
    assert_launch_enabled(
        config, cli_flag=args.execute_reviewed_run, observed_commit=commit
    )
    for name in (
        "packet_dir",
        "base_runtime_config",
        "initial_checkpoint",
        "output_dir",
        "execution_candidate",
        "execution_authority",
        "code_archive",
        "control_dir",
    ):
        if getattr(args, name) is None:
            parser.error(f"--{name.replace('_', '-')} is required after authority")
    candidate_bytes = args.execution_candidate.read_bytes()
    candidate = _strict_json(args.execution_candidate)
    authority = _strict_json(args.execution_authority)
    validate_execution_candidate(candidate)
    archive_cap = candidate["resources"]["code_archive_cap_bytes"]
    if args.code_archive.stat().st_size > archive_cap:
        raise ValueError("code archive cap exceeded")
    archive_sha256 = sha256_path(args.code_archive)
    candidate_sha256 = sha256_bytes(candidate_bytes)
    validate_runtime_control(
        config,
        candidate,
        authority,
        observed_commit=commit,
        candidate_sha256=candidate_sha256,
        code_archive_sha256=archive_sha256,
    )
    expected_paths = candidate["paths"]
    actual_paths = {
        "packet_dir": args.packet_dir,
        "base_runtime_config": args.base_runtime_config,
        "initial_checkpoint": args.initial_checkpoint,
        "output_root": args.output_dir,
        "code_archive": args.code_archive,
        "control_root": args.control_dir,
    }
    for name, value in actual_paths.items():
        if value != Path(expected_paths[name]):
            parser.error(f"--{name.replace('_', '-')} differs from frozen candidate")
    try:
        admission = control_admission(
            candidate,
            config,
            code_archive=args.code_archive,
        )
        receipt_path = args.control_dir / "admission_receipt.json"
        if receipt_path.exists():
            raise FileExistsError("admission receipt already exists")
        receipt_path.write_bytes(canonical_json(admission))
    except Exception as error:
        failure = {
            "terminal_state": "ADMISSION_STOPPED",
            "first_reason": f"{type(error).__name__}: {error}",
            "arm": None,
            "attempted_update": 0,
            "counters": {
                "model_forwards": 0,
                "autograd_collections": 0,
                "optimizer_constructions": 0,
                "optimizer_steps": 0,
            },
            "last_complete_update": 0,
            "missing_or_unreadable": [],
            "process_identity": process_identity(),
            "resource_snapshot": None,
            "retry": False,
            "alternate_gpu": False,
        }
        try:
            if args.control_dir.is_dir():
                failure["resource_snapshot"] = resource_snapshot(
                    config["_execution_control"], args.output_dir
                )
                failure_path = args.control_dir / "admission_failure_receipt.json"
                with failure_path.open("xb") as stream:
                    stream.write(canonical_json(failure))
        except Exception:
            pass
        raise
    bindings = resolve_real_bindings(
        config, cli_flag=args.execute_reviewed_run, observed_commit=commit
    )
    bindings["real_adapter_entrypoint"](
        config=config,
        packet_dir=args.packet_dir,
        base_runtime_config=args.base_runtime_config,
        initial_checkpoint=args.initial_checkpoint,
        output_dir=args.output_dir,
        bindings=bindings,
    )


if __name__ == "__main__":
    main()
