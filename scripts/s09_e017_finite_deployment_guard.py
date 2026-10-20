#!/usr/bin/env python3
"""Run the exact reviewed deployment plan under one finite outer guard."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e017_chunked_deployment import DeploymentStop, canonical_json  # noqa: E402
from s09_e017_finite_deployment_guard import run_guarded_plan  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--execute-authorised-deployment", action="store_true")
    args = parser.parse_args()
    receipt = run_guarded_plan(
        candidate_path=args.candidate,
        candidate_sha256=args.candidate_sha256,
        authority_path=args.authority,
        plan_path=args.plan,
        plan_sha256=args.plan_sha256,
        receipt_path=args.receipt,
        execute_authorised_deployment=args.execute_authorised_deployment,
    )
    print(canonical_json(receipt).decode("utf-8"), end="")
    if receipt["terminal_state"] != "DEPLOYMENT_PLAN_COMPLETED":
        raise SystemExit(2)


if __name__ == "__main__":
    try:
        main()
    except DeploymentStop as error:
        failure = {
            "terminal_state": "DEPLOYMENT_GUARD_REJECTED",
            "first_reason": error.first_reason,
            "message": str(error),
        }
        print(canonical_json(failure).decode("utf-8"), end="", file=sys.stderr)
        raise SystemExit(1) from error
