#!/usr/bin/env python3
"""Resolve one authorised S09-E017 runtime config without scientific I/O."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e017_execution_control import (  # noqa: E402
    canonical_json,
    resolve_runtime_config,
    sha256_bytes,
    sha256_path,
    validate_execution_candidate,
)
from s09_e017_producer_package import validate_package_config  # noqa: E402


def _strict_json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-package-config", type=Path, required=True)
    parser.add_argument("--execution-candidate", type=Path, required=True)
    parser.add_argument("--execution-authority", type=Path, required=True)
    parser.add_argument("--code-archive", type=Path, required=True)
    parser.add_argument("--output-config", type=Path, required=True)
    parser.add_argument("--output-receipt", type=Path, required=True)
    parser.add_argument("--resolve-authorised-config", action="store_true")
    args = parser.parse_args()
    if not args.resolve_authorised_config:
        parser.error("--resolve-authorised-config is required")
    base_bytes = args.base_package_config.read_bytes()
    base = _strict_json(args.base_package_config)
    candidate_bytes = args.execution_candidate.read_bytes()
    candidate = _strict_json(args.execution_candidate)
    authority = _strict_json(args.execution_authority)
    observed_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    validate_package_config(base)
    validate_execution_candidate(candidate)
    expected_base = ROOT / (
        "docs/research/S09/S09-E017/final_run_package_config_20261019.json"
    )
    if args.base_package_config.resolve() != expected_base.resolve():
        raise ValueError("base package config path drift")
    base_sha256 = sha256_bytes(base_bytes)
    archive_cap = candidate["resources"]["code_archive_cap_bytes"]
    if args.code_archive.stat().st_size > archive_cap:
        raise ValueError("code archive cap exceeded")
    candidate_sha256 = sha256_bytes(candidate_bytes)
    archive_sha256 = sha256_path(args.code_archive)
    resolved = resolve_runtime_config(
        base,
        candidate,
        authority,
        observed_commit=observed_commit,
        base_package_config_sha256=base_sha256,
        candidate_sha256=candidate_sha256,
        code_archive_sha256=archive_sha256,
    )
    receipt = {
        "terminal_state": "RESOLVED_FOR_AUTHORISED_EXECUTION",
        "run_id": candidate["run_id"],
        "reviewed_control_commit": observed_commit,
        "reviewed_adapter_commit": candidate["source"]["reviewed_adapter_commit"],
        "base_package_config_sha256": base_sha256,
        "candidate_config_sha256": candidate_sha256,
        "execution_authority_sha256": sha256_bytes(canonical_json(authority)),
        "code_archive_sha256": archive_sha256,
        "resolved_config_sha256": sha256_bytes(canonical_json(resolved)),
        "scientific_assets_read": False,
        "binding_resolutions": 0,
        "model_forwards": 0,
        "autograd_collections": 0,
        "optimizer_constructions": 0,
        "optimizer_steps": 0,
    }
    for path in (args.output_config, args.output_receipt):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output_config.write_bytes(canonical_json(resolved))
    args.output_receipt.write_bytes(canonical_json(receipt))
    print(canonical_json(receipt).decode("utf-8"), end="")


if __name__ == "__main__":
    main()
