#!/usr/bin/env python3
"""Explicit producer-only entry point for the reviewed S09-E009 run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e009_producer import run_producer  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--resolved-config", type=Path, required=True)
    parser.add_argument("--base-config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execute-reviewed-run", action="store_true")
    args = parser.parse_args()
    if not args.execute_reviewed_run:
        parser.error("--execute-reviewed-run is required")
    receipt = run_producer(
        packet_dir=args.packet_dir,
        resolved_config_path=args.resolved_config,
        base_runtime_config_path=args.base_config,
        output_dir=args.output_dir,
        repo_root=ROOT,
    )
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
