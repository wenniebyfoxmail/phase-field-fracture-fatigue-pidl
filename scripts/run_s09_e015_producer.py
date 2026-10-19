#!/usr/bin/env python3
"""Execute the exact reviewed S09-E015 producer once."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
from s09_e015_producer import run_producer  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--base-config", type=Path, required=True)
    parser.add_argument("--initial-checkpoint", type=Path, required=True)
    parser.add_argument("--control-endpoint", type=Path, required=True)
    parser.add_argument("--candidate-endpoint", type=Path, required=True)
    parser.add_argument("--e014-run-dir", type=Path, required=True)
    parser.add_argument("--vector-archive", type=Path, required=True)
    parser.add_argument("--e014-completion", type=Path, required=True)
    parser.add_argument("--run-config", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--execute-reviewed-run", action="store_true")
    args = parser.parse_args()
    if not args.execute_reviewed_run:
        parser.error("--execute-reviewed-run is required")
    result = run_producer(
        packet_dir=args.packet_dir,
        base_config=args.base_config,
        initial_checkpoint=args.initial_checkpoint,
        control_endpoint=args.control_endpoint,
        candidate_endpoint=args.candidate_endpoint,
        e014_run_dir=args.e014_run_dir,
        vector_archive=args.vector_archive,
        e014_completion=args.e014_completion,
        output_dir=args.output_dir,
        archive_dir=args.archive_dir,
        repo_root=ROOT,
        expected_commit=args.expected_commit,
        run_config=args.run_config,
        protocol=args.protocol,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
