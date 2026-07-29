#!/usr/bin/env python3
"""Validate one or more FEM trajectory manifests and an optional LOTO lock."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from fem_trajectory_bundle import (
    load_bundles,
    validate_bundle,
    validate_loto_split,
    write_json,
)  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, action="append", required=True)
    parser.add_argument("--split", type=Path)
    parser.add_argument("--deep", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    bundles = load_bundles(args.bundle)
    result = {
        "bundle_reports": [
            validate_bundle(bundle, deep=args.deep).as_dict() for bundle in bundles
        ]
    }
    if args.split:
        split = json.loads(args.split.read_text(encoding="utf-8"))
        result["split_report"] = validate_loto_split(split, bundles).as_dict()
    valid = all(report["valid"] for report in result["bundle_reports"])
    valid = valid and result.get("split_report", {"valid": True})["valid"]
    result["valid"] = valid

    if args.report:
        write_json(args.report, result)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if valid else 1)


if __name__ == "__main__":
    main()
