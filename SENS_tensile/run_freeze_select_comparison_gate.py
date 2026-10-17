from __future__ import annotations

import argparse
import json
from pathlib import Path

from freeze_select.comparison_gate import METHODS, run_comparison_gate


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and compare three Freeze-Then-Select method packages")
    parser.add_argument("--freeze-then-select", type=Path, required=True)
    parser.add_argument("--single-shot", type=Path, required=True)
    parser.add_argument("--joint-training", type=Path, required=True)
    parser.add_argument("--sealed-truth", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_comparison_gate(
        {
            METHODS[0]: args.freeze_then_select,
            METHODS[1]: args.single_shot,
            METHODS[2]: args.joint_training,
        },
        args.sealed_truth,
        args.output_dir,
    )
    print(json.dumps(report.to_dict(), indent=2))
    raise SystemExit(0 if report.package_valid else 2)


if __name__ == "__main__":
    main()
