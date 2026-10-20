#!/usr/bin/env python3
"""Resolve an authorised E017 admission-only control without scientific I/O."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e017_admission_only import (  # noqa: E402
    ARCHIVE_BYTES,
    canonical_json,
    resolve_admission_only,
    sha256_bytes,
    sha256_path,
    strict_json,
    validate_candidate,
)


def _write_once(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical_json(value))


def resolve_from_paths(
    *,
    candidate_path: Path,
    candidate_sha256: str,
    final_candidate_path: Path,
    package_config_path: Path,
    authority_path: Path,
    code_archive: Path,
    code_root: Path,
) -> tuple[dict, dict]:
    candidate, candidate_bytes = strict_json(candidate_path)
    authority, _ = strict_json(authority_path)
    validate_candidate(candidate)
    if sha256_bytes(candidate_bytes) != candidate_sha256:
        raise ValueError("admission-only candidate SHA256 mismatch")
    final_candidate, final_bytes = strict_json(final_candidate_path)
    package, package_bytes = strict_json(package_config_path)
    if final_candidate.get("schema_version") != "s09-e017-final-execution-candidate-v1":
        raise ValueError("final candidate schema drift")
    if package.get("schema_version") != "s09-e017-final-run-package-v1":
        raise ValueError("package schema drift")
    archive_stat_before = code_archive.lstat()
    archive_sha256 = sha256_path(code_archive, expected_bytes=ARCHIVE_BYTES)
    archive_stat_after = code_archive.lstat()
    stat_before = {
        "device": archive_stat_before.st_dev,
        "inode": archive_stat_before.st_ino,
        "mode": archive_stat_before.st_mode,
        "mtime_ns": archive_stat_before.st_mtime_ns,
        "size_bytes": archive_stat_before.st_size,
    }
    stat_after = {
        "device": archive_stat_after.st_dev,
        "inode": archive_stat_after.st_ino,
        "mode": archive_stat_after.st_mode,
        "mtime_ns": archive_stat_after.st_mtime_ns,
        "size_bytes": archive_stat_after.st_size,
    }
    if stat_before != stat_after or stat_after["size_bytes"] != ARCHIVE_BYTES:
        raise ValueError("code archive changed during single bounded read")
    archive_verification = {
        "path": str(code_archive),
        "bytes": ARCHIVE_BYTES,
        "bytes_read": ARCHIVE_BYTES,
        "sha256": archive_sha256,
        "stat": stat_after,
    }
    observed_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=code_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()
    resolved = resolve_admission_only(
        candidate=candidate,
        authority=authority,
        candidate_sha256=candidate_sha256,
        plan_sha256=candidate["plan_sha256"],
        package_config_sha256=sha256_bytes(package_bytes),
        final_candidate_sha256=sha256_bytes(final_bytes),
        archive_sha256=archive_sha256,
        archive_verification=archive_verification,
        observed_commit=observed_commit,
    )
    receipt = {
        "schema_version": "s09-e017-admission-only-resolution-receipt-v1",
        "terminal_state": "RESOLVED_FOR_ADMISSION_ONLY",
        "run_id": candidate["run_id"],
        "admission_only_attempt_id": authority["admission_only_attempt_id"],
        "candidate_sha256": candidate_sha256,
        "authority_sha256": sha256_bytes(canonical_json(authority)),
        "package_config_sha256": sha256_bytes(package_bytes),
        "final_candidate_sha256": sha256_bytes(final_bytes),
        "archive_sha256": archive_sha256,
        "archive_bytes_read": ARCHIVE_BYTES,
        "archive_stat": stat_after,
        "observed_control_commit": observed_commit,
        "resolved_config_sha256": sha256_bytes(canonical_json(resolved)),
        "scientific_asset_content_reads": False,
        "execution_authorized": False,
        "producer_authorized": False,
        "counters": dict(resolved["counters"]),
    }
    return resolved, receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission-candidate", type=Path, required=True)
    parser.add_argument("--admission-candidate-sha256", required=True)
    parser.add_argument("--final-execution-candidate", type=Path, required=True)
    parser.add_argument("--base-package-config", type=Path, required=True)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--code-archive", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--output-config", type=Path, required=True)
    parser.add_argument("--output-receipt", type=Path, required=True)
    parser.add_argument("--resolve-authorised-admission-only", action="store_true")
    args = parser.parse_args()
    if not args.resolve_authorised_admission_only:
        parser.error("--resolve-authorised-admission-only is required")
    resolved, receipt = resolve_from_paths(
        candidate_path=args.admission_candidate,
        candidate_sha256=args.admission_candidate_sha256,
        final_candidate_path=args.final_execution_candidate,
        package_config_path=args.base_package_config,
        authority_path=args.authority,
        code_archive=args.code_archive,
        code_root=args.code_root,
    )
    _write_once(args.output_config, resolved)
    _write_once(args.output_receipt, receipt)
    print(canonical_json(receipt).decode("utf-8"), end="")


if __name__ == "__main__":
    main()
