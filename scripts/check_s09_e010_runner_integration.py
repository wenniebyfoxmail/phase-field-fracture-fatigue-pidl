#!/usr/bin/env python3
"""Build S09-E010 runner integration and emit its no-training receipt."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e010_runner_integration import (  # noqa: E402
    build_no_training_integration,
    write_no_training_receipt,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--base-config", type=Path, required=True)
    parser.add_argument("--integration-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bundle = build_no_training_integration(
        packet_dir=args.packet_dir,
        base_config_path=args.base_config,
        integration_config_path=args.integration_config,
        device=torch.device("cpu"),
    )
    write_no_training_receipt(bundle, args.output)
    print(f"NO_TRAINING_INTEGRATION_PASS {args.output}")


if __name__ == "__main__":
    main()
