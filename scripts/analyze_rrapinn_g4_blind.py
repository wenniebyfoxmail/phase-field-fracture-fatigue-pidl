#!/usr/bin/env python3
"""Calculate and exclusively write the frozen RRaPINN G4 blind metrics CSV."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from rrapinn_g4_field_analysis import analyze_blind_pair  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--arm-manifest", action="append", type=Path,
        help="Opaque analysis manifest; pass exactly twice.",
    )
    parser.add_argument("--arm-1", type=Path, help="First opaque analysis manifest.")
    parser.add_argument("--arm-2", type=Path, help="Second opaque analysis manifest.")
    parser.add_argument("--fem-c76", type=Path, required=True)
    parser.add_argument("--fem-c82", type=Path, required=True)
    parser.add_argument(
        "--projector-manifest", "--projector", dest="projector_manifest",
        type=Path, required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repeated = args.arm_manifest or []
    paired = [value for value in (args.arm_1, args.arm_2) if value is not None]
    if repeated and paired:
        parser.error("use either two --arm-manifest values or --arm-1/--arm-2")
    arm_manifests = repeated if repeated else paired
    if len(arm_manifests) != 2:
        parser.error("exactly two opaque-arm analysis manifests are required")
    rows = analyze_blind_pair(
        arm_manifests=arm_manifests,
        fem_c76=args.fem_c76,
        fem_c82=args.fem_c82,
        projector_manifest=args.projector_manifest,
        output_csv=args.output,
    )
    print(json.dumps({
        "status": "PASS_BLIND_ANALYSIS",
        "output": str(args.output.resolve()),
        "row_count": len(rows),
        "opaque_arms": sorted({row["opaque_arm"] for row in rows}),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
