#!/usr/bin/env python3
"""Seal already-produced blind G4 metrics; this script does not analyze data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from rrapinn_g4_blind_contract import ContractError, seal_metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-csv", type=Path, required=True)
    parser.add_argument("--prelaunch-lock", type=Path, required=True)
    parser.add_argument("--fem-artifact", type=Path, required=True)
    parser.add_argument("--projector-artifact", type=Path, required=True)
    parser.add_argument(
        "--arm-manifest", type=Path, action="append", required=True,
        help="Pass exactly twice; both manifests and all referenced inputs are sealed.",
    )
    parser.add_argument("--output-seal", type=Path, required=True)
    args = parser.parse_args()
    try:
        seal_sha256 = seal_metrics(
            metrics_csv=args.metrics_csv,
            prelaunch_lock=args.prelaunch_lock,
            fem_artifact=args.fem_artifact,
            projector_artifact=args.projector_artifact,
            arm_manifests=args.arm_manifest,
            output_seal=args.output_seal,
        )
    except (ContractError, FileExistsError, OSError) as exc:
        parser.error(str(exc))
    print(f"seal_sha256={seal_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
