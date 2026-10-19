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

from s09_e017_producer_package import assert_launch_enabled  # noqa: E402


def _strict_json(path: Path):
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolved-config", type=Path, required=True)
    parser.add_argument("--execute-reviewed-run", action="store_true")
    args = parser.parse_args()
    config = _strict_json(args.resolved_config)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    # The tracked candidate always stops here.  A later exact reviewed commit
    # must add and bind the real adapter entry point before enabling launch.
    assert_launch_enabled(
        config, cli_flag=args.execute_reviewed_run, observed_commit=commit
    )
    raise PermissionError("real E017 adapter entry point is not enabled in this package")


if __name__ == "__main__":
    main()
