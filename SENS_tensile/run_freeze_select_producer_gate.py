from __future__ import annotations

import argparse
import json
from pathlib import Path

from freeze_select.producer_gate import run_producer_gate


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a manifest-declared factorial Stage B/C producer package after producer qualification"
    )
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_producer_gate(args.snapshot, args.manifest, args.output_dir)
    print(json.dumps(report.to_dict(), indent=2))
    raise SystemExit(0 if report.passed else 2)


if __name__ == "__main__":
    main()
