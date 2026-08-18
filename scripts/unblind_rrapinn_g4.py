#!/usr/bin/env python3
"""Verify a G4 seal, then apply an independently supplied two-arm map."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from rrapinn_g4_blind_contract import ContractError, unblind_metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", type=Path, required=True)
    parser.add_argument("--expected-seal-sha256", required=True)
    parser.add_argument("--metrics-csv", type=Path, required=True)
    parser.add_argument("--analysis-code", type=Path, required=True)
    parser.add_argument("--fem-artifact", type=Path, required=True)
    parser.add_argument("--projector-artifact", type=Path, required=True)
    parser.add_argument("--arm-map-csv", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    try:
        unblind_metrics(
            seal_path=args.seal,
            expected_seal_sha256=args.expected_seal_sha256,
            metrics_csv=args.metrics_csv,
            analysis_code=args.analysis_code,
            fem_artifact=args.fem_artifact,
            projector_artifact=args.projector_artifact,
            arm_map_csv=args.arm_map_csv,
            output_csv=args.output_csv,
        )
    except (ContractError, FileExistsError, OSError) as exc:
        parser.error(str(exc))
    print(f"unblinded_csv={args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

