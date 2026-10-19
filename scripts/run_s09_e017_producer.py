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
    ):
        if getattr(args, name) is None:
            parser.error(f"--{name.replace('_', '-')} is required after authority")
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
