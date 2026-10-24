#!/usr/bin/env python3
"""Build the immutable S04-E040 producer package outside the worktree.

The generated sidecars separate two identities:

* ``package_commit`` is the committed tree containing the operational launcher.
* ``reviewed_runtime_commit`` is the exact 5aaa snapshot that supplied every
  Python/module/mesh byte which can enter the calculation.

The bootstrap is deliberately emitted outside the tar.  Its caller receives
the receipt SHA-256 as an explicit, user-approved value before any remote
extraction happens.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


REVIEWED_RUNTIME_COMMIT = "5aaa317ed55175e80acb581d922eb6a1a4cb6d49"
RECEIPT_SCHEMA = "S04-E040-producer-package-receipt-v2"
RUNTIME_MANIFEST_SCHEMA = "S04-E040-reviewed-runtime-manifest-v1"
ENTRYPOINT = "docs/research/S04/S04-E040/producer_launch.sh"
BOOTSTRAP = "docs/research/S04/S04-E040/producer_bootstrap.sh"
RUNTIME_EXTRA_PATHS = (
    "scripts/run_s04_e040_feasible_damage.py",
    "scripts/analyze_s04_e040_feasible_damage.py",
    "SENS_tensile/field_computation.py",
    "SENS_tensile/meshed_geom_fem_soft_hist0.msh",
)
PACKAGE_PATHS = (
    "source",
    *RUNTIME_EXTRA_PATHS,
    ENTRYPOINT,
    "docs/research/S04/S04-E040/experiment.md",
    "docs/research/S04/S04-E040/chatgpt_exact_source_review.md",
    "docs/research/S04/S04-E040/chatgpt_exact_source_review_packet.md",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(repo: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        message = completed.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"git {' '.join(arguments)} failed: {message}")
    return completed.stdout


def commit(repo: Path, value: str) -> str:
    return git(repo, "rev-parse", f"{value}^{{commit}}").decode().strip()


def blob(repo: Path, revision: str, relative: str) -> bytes:
    return git(repo, "show", f"{revision}:{relative}")


def runtime_paths(repo: Path, revision: str) -> list[str]:
    source_paths = git(repo, "ls-tree", "-r", "--name-only", revision, "--", "source").decode().splitlines()
    paths = sorted({*source_paths, *RUNTIME_EXTRA_PATHS})
    if not paths or any(not path for path in paths):
        raise RuntimeError("could not collect reviewed runtime closure")
    return paths


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--package-commit", default="HEAD")
    parser.add_argument("--allow-dirty", action="store_true")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo = arguments.repo.resolve()
    output = arguments.output.resolve()
    package_commit = commit(repo, arguments.package_commit)
    reviewed_commit = commit(repo, REVIEWED_RUNTIME_COMMIT)
    if package_commit != reviewed_commit:
        git(repo, "merge-base", "--is-ancestor", reviewed_commit, package_commit)
    if not arguments.allow_dirty and git(repo, "status", "--porcelain"):
        raise RuntimeError("refusing to package a dirty worktree")
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    paths = runtime_paths(repo, reviewed_commit)
    manifest_files: list[dict[str, object]] = []
    for relative in paths:
        reviewed_bytes = blob(repo, reviewed_commit, relative)
        package_bytes = blob(repo, package_commit, relative)
        if package_bytes != reviewed_bytes:
            raise RuntimeError(f"runtime file differs from reviewed snapshot: {relative}")
        manifest_files.append(
            {"path": relative, "bytes": len(reviewed_bytes), "sha256": sha256_bytes(reviewed_bytes)}
        )
    manifest = {
        "schema": RUNTIME_MANIFEST_SCHEMA,
        "reviewed_runtime_commit": reviewed_commit,
        "files": manifest_files,
    }
    manifest_path = output / "reviewed_runtime_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    archive_path = output / "s04-e040-code.tar"
    with archive_path.open("wb") as handle:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "archive",
                "--format=tar",
                "--prefix=code/",
                package_commit,
                "--",
                *PACKAGE_PATHS,
            ],
            stdout=handle,
            stderr=subprocess.PIPE,
            check=False,
        )
    if completed.returncode:
        raise RuntimeError(completed.stderr.decode(errors="replace").strip())
    archive_commit = git(repo, "get-tar-commit-id", input_bytes=archive_path.read_bytes()).decode().strip()
    if archive_commit != package_commit:
        raise RuntimeError(f"git archive embedded {archive_commit}, expected {package_commit}")

    bootstrap_path = output / "producer_bootstrap.sh"
    bootstrap_path.write_bytes(blob(repo, package_commit, BOOTSTRAP))
    bootstrap_path.chmod(0o755)
    entrypoint_bytes = blob(repo, package_commit, ENTRYPOINT)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "package_commit": package_commit,
        "reviewed_runtime_commit": reviewed_commit,
        "archive_file": archive_path.name,
        "archive_sha256": sha256_file(archive_path),
        "archive_bytes": archive_path.stat().st_size,
        "runtime_manifest_file": manifest_path.name,
        "runtime_manifest_sha256": sha256_file(manifest_path),
        "entrypoint": ENTRYPOINT,
        "entrypoint_sha256": sha256_bytes(entrypoint_bytes),
        "bootstrap_file": bootstrap_path.name,
        "bootstrap_sha256": sha256_file(bootstrap_path),
    }
    receipt_path = output / "package_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    summary = {
        "schema": "S04-E040-producer-package-summary-v1",
        "receipt_file": receipt_path.name,
        "receipt_sha256": sha256_file(receipt_path),
        "tar_commit": archive_commit,
        **receipt,
    }
    (output / "package_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError) as error:
        print(f"prepare producer package: {error}", file=sys.stderr)
        raise SystemExit(2)
