#!/usr/bin/env python3
"""Build the immutable S04-E042 producer package outside the worktree.

The generated sidecars distinguish the committed operational wrapper from the
reviewed numerical closure.  ``package_commit`` may contain newer launch
material, but every file that can enter the projected-damage calculation must
remain byte-identical to ``REVIEWED_RUNTIME_COMMIT``.

The bootstrap is emitted outside the archive.  A future launch card pins its
receipt digest before any remote materialisation occurs.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path


REVIEWED_RUNTIME_COMMIT = "521c611fb2b24622df50ef5c2f4624b4abfed72d"
RECEIPT_SCHEMA = "S04-E042-producer-package-receipt-v2"
RUNTIME_MANIFEST_SCHEMA = "S04-E042-reviewed-runtime-manifest-v2"
ENTRYPOINT = "docs/research/S04/S04-E042/producer_launch.sh"
BOOTSTRAP = "docs/research/S04/S04-E042/producer_bootstrap.sh"
RUNNER = "scripts/run_s04_e042_projected_damage.py"
PROJECTED_DAMAGE_MODULE = "source/projected_damage.py"
RUNTIME_EXTRA_PATHS = (
    RUNNER,
    "SENS_tensile/field_computation.py",
    "SENS_tensile/meshed_geom_fem_soft_hist0.msh",
)
PACKAGE_PATHS = (
    "source",
    *RUNTIME_EXTRA_PATHS,
    ENTRYPOINT,
    "docs/research/S04/S04-E042/experiment.md",
    "docs/research/S04/S04-E042/chatgpt_method_review.md",
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
    if PROJECTED_DAMAGE_MODULE not in paths:
        raise RuntimeError("reviewed runtime closure omits source/projected_damage.py")
    return paths


def projected_damage_import_proof(runner_bytes: bytes) -> dict[str, str]:
    """Require the real E042 runner to import its explicit direct carrier."""
    try:
        tree = ast.parse(runner_bytes.decode("utf-8"), filename=RUNNER)
    except (SyntaxError, UnicodeDecodeError) as error:
        raise RuntimeError(f"cannot parse reviewed E042 runner: {error}") from error
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "projected_damage":
            if any(alias.name == "ReferenceBaseProjectedDamage" for alias in node.names):
                return {
                    "module": "projected_damage",
                    "symbol": "ReferenceBaseProjectedDamage",
                    "module_path": PROJECTED_DAMAGE_MODULE,
                    "runner_path": RUNNER,
                }
    raise RuntimeError("reviewed E042 runner does not import ReferenceBaseProjectedDamage")


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
    import_proof = projected_damage_import_proof(blob(repo, reviewed_commit, RUNNER))
    manifest_files: list[dict[str, object]] = []
    for relative in paths:
        reviewed_bytes = blob(repo, reviewed_commit, relative)
        package_bytes = blob(repo, package_commit, relative)
        if package_bytes != reviewed_bytes:
            raise RuntimeError(f"runtime file differs from reviewed snapshot: {relative}")
        manifest_files.append(
            {"path": relative, "bytes": len(reviewed_bytes), "sha256": sha256_bytes(reviewed_bytes)}
        )
    projected_item = next(item for item in manifest_files if item["path"] == PROJECTED_DAMAGE_MODULE)
    import_proof["module_sha256"] = str(projected_item["sha256"])
    manifest = {
        "schema": RUNTIME_MANIFEST_SCHEMA,
        "reviewed_runtime_commit": reviewed_commit,
        "files": manifest_files,
        "e042_import_proof": import_proof,
    }
    manifest_path = output / "reviewed_runtime_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    archive_path = output / "s04-e042-code.tar"
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
        "schema": "S04-E042-producer-package-summary-v1",
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
