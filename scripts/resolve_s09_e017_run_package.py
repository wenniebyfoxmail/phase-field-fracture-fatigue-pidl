#!/usr/bin/env python3
"""Validate the disabled S09-E017 package candidate without scientific I/O."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e017_producer_package import canonical_json, validate_package_config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-config", type=Path, required=True)
    parser.add_argument("--check-disabled-candidate", action="store_true")
    args = parser.parse_args()
    if not args.check_disabled_candidate:
        parser.error("--check-disabled-candidate is required")
    raw = args.package_config.read_bytes()
    config = json.loads(
        raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value))
    )
    validate_package_config(config)
    if raw != canonical_json(config):
        raise ValueError("package config is not canonical JSON")
    print(
        json.dumps(
            {
                "status": config["status"],
                "execution_authorized": False,
                "scientific_assets_read": False,
                "bindings_resolved": False,
                "model_forward": 0,
                "autograd_collections": 0,
                "optimizer_constructions": 0,
                "optimizer_steps": 0,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
