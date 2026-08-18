#!/usr/bin/env python3
"""Fail-closed static validator for the preregistered G3 three-arm packet."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_ARMS = {
    "A_absent": ["--mechanical-risk-mode", "absent"],
    "B_off": ["--mechanical-risk-mode", "off"],
    "C_on": [
        "--mechanical-risk-mode", "on",
        "--mechanical-risk-alpha", "0.85",
        "--mechanical-risk-lambda", "0.000549728557462236",
        "--mechanical-risk-e-ref", "1",
        "--mechanical-risk-l-ref", "1",
    ],
}


def validate(payload: dict) -> dict:
    checks = {
        "schema": payload.get("schema") == "rrapinn-g3-smoke-packet-v1",
        "not_authorized": payload.get("training_authorized") is False,
        "first_detect": payload.get("comparison_cycle") == 82
        and payload.get("comparison_semantics") == "last_common_pre_first_detect"
        and payload.get("fem_first_detect_cycle") == 83
        and payload.get("fem_confirmation_cycle") == 86
        and payload.get("confirmation_cycle_used") is False,
        "base_commit": payload.get("producer_parent_commit")
        == "27b634cd9160038f3c3513ed99545296a025e039",
        "head_frozen_at_launch": payload.get("required_head_commit")
        == "${G3_PRODUCER_COMMIT}",
        "frozen_lambda": payload.get("frozen_smoke_lambda") == 0.000549728557462236,
        "init_sha": payload.get("init_checkpoint_sha256")
        == "1044740e0004fe11688ec4930a4c3ea25cf0bd252bb66b29e6ddca6bbeb07a9e",
        "common_has_one_cycle": ["--n-cycles-physical", "1"]
        == payload.get("command_common", [])[3:5],
    }
    arms = payload.get("arms", [])
    actual = {arm.get("name"): arm.get("extra_args") for arm in arms}
    checks["exact_three_arms"] = actual == EXPECTED_ARMS
    common = payload.get("command_common", [])
    forbidden = {"--graph-pidl", "--compile"}
    checks["no_extra_representation"] = forbidden.isdisjoint(common)
    checks["fresh_fail_closed"] = "--fresh-output-required" in common
    checks["clean_git_required"] = "--require-clean-git" in common
    checks["single_intervention"] = all(
        not forbidden.intersection(extra) for extra in actual.values()
    )
    return {"status": "pass_schema_only" if all(checks.values()) else "fail", "checks": checks}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("packet", type=Path)
    args = ap.parse_args()
    payload = json.loads(args.packet.read_text(encoding="utf-8"))
    result = validate(payload)
    print(json.dumps(result, indent=2))
    if result["status"] != "pass_schema_only":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
