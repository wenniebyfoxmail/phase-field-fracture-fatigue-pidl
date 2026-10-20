#!/usr/bin/env python3
"""Run one write-once E017 metadata admission and stop before science."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e017_admission_only import (  # noqa: E402
    begin_attempt,
    canonical_json,
    failure_receipt,
    run_metadata_admission,
    strict_json,
)
from resolve_s09_e017_admission_only import resolve_from_paths  # noqa: E402


def _write_once(path: Path, value: object) -> None:
    with path.open("xb") as stream:
        stream.write(canonical_json(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission-candidate", type=Path, required=True)
    parser.add_argument("--admission-candidate-sha256", required=True)
    parser.add_argument("--final-execution-candidate", type=Path, required=True)
    parser.add_argument("--base-package-config", type=Path, required=True)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--code-archive", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--attempt-root", type=Path, required=True)
    parser.add_argument("--execute-authorised-admission-only", action="store_true")
    args = parser.parse_args()
    if not args.execute_authorised_admission_only:
        parser.error("--execute-authorised-admission-only is required")
    authority, _ = strict_json(args.authority)
    attempt_started = False
    try:
        begin_attempt(args.attempt_root, authority)
        attempt_started = True
        resolved, resolution = resolve_from_paths(
            candidate_path=args.admission_candidate,
            candidate_sha256=args.admission_candidate_sha256,
            final_candidate_path=args.final_execution_candidate,
            package_config_path=args.base_package_config,
            authority_path=args.authority,
            code_archive=args.code_archive,
            code_root=args.code_root,
        )
        _write_once(args.attempt_root / "config_resolved_admission_only.json", resolved)
        _write_once(args.attempt_root / "resolution_receipt.json", resolution)
        candidate, _ = strict_json(args.admission_candidate)
        receipt = run_metadata_admission(
            candidate=candidate,
            resolved=resolved,
            authority=authority,
            attempt_root=args.attempt_root,
        )
        _write_once(args.attempt_root / "admission_only_receipt.json", receipt)
        print(canonical_json(receipt).decode("utf-8"), end="")
    except Exception as error:
        if attempt_started:
            try:
                _write_once(
                    args.attempt_root / "admission_only_failure_receipt.json",
                    failure_receipt(authority=authority, error=error),
                )
            except Exception:
                pass
        raise


if __name__ == "__main__":
    main()
