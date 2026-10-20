#!/usr/bin/env python3
"""CLI for the separately versioned S09-E017 deployment helper."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e017_chunked_deployment import (  # noqa: E402
    DeploymentStop,
    assemble_with_receipt,
    audit_legacy_partial,
    build_chunk_store,
    canonical_json,
    import_verified_legacy_chunks,
    inspect_chunk_store,
    load_manifest,
    manifest_sha256,
    _publish_bytes_no_replace,
)


def _manifest_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)


def _report_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--report", type=Path)


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build")
    build.add_argument("--archive", type=Path, required=True)
    build.add_argument("--chunk-dir", type=Path, required=True)
    build.add_argument("--manifest", type=Path, required=True)
    build.add_argument("--chunk-size-bytes", type=int, required=True)
    build.add_argument("--expected-archive-bytes", type=int, required=True)
    build.add_argument("--expected-archive-sha256", required=True)
    build.add_argument("--reviewed-control-commit", required=True)

    inspect = subparsers.add_parser("inspect-store")
    _manifest_args(inspect)
    _report_arg(inspect)
    inspect.add_argument("--chunk-dir", type=Path, required=True)

    audit = subparsers.add_parser("audit-legacy")
    _manifest_args(audit)
    _report_arg(audit)
    audit.add_argument("--legacy-partial", type=Path, required=True)

    import_legacy = subparsers.add_parser("import-legacy")
    _manifest_args(import_legacy)
    _report_arg(import_legacy)
    import_legacy.add_argument("--legacy-partial", type=Path, required=True)
    import_legacy.add_argument("--chunk-dir", type=Path, required=True)

    assemble = subparsers.add_parser("assemble")
    _manifest_args(assemble)
    assemble.add_argument("--chunk-dir", type=Path, required=True)
    assemble.add_argument("--output", type=Path, required=True)
    assemble.add_argument("--receipt", type=Path, required=True)
    assemble.add_argument("--max-wall-seconds", type=float, required=True)

    args = parser.parse_args()
    if args.command == "build":
        manifest = build_chunk_store(
            args.archive,
            args.chunk_dir,
            chunk_size_bytes=args.chunk_size_bytes,
            expected_archive_bytes=args.expected_archive_bytes,
            expected_archive_sha256=args.expected_archive_sha256,
            reviewed_control_commit=args.reviewed_control_commit,
        )
        _publish_bytes_no_replace(args.manifest, canonical_json(manifest))
        output = {
            "terminal_state": "CHUNK_STORE_BUILT",
            "manifest_sha256": manifest_sha256(manifest),
            "chunk_count": len(manifest["chunks"]),
            "archive_bytes": manifest["source"]["bytes"],
        }
    else:
        manifest = load_manifest(args.manifest, expected_sha256=args.manifest_sha256)
        if args.command == "inspect-store":
            output = inspect_chunk_store(manifest, args.chunk_dir)
        elif args.command == "audit-legacy":
            output = audit_legacy_partial(manifest, args.legacy_partial)
        elif args.command == "import-legacy":
            output = import_verified_legacy_chunks(
                manifest, args.legacy_partial, args.chunk_dir
            )
        else:
            output = assemble_with_receipt(
                manifest,
                args.chunk_dir,
                args.output,
                args.receipt,
                max_wall_seconds=args.max_wall_seconds,
            )
        if getattr(args, "report", None) is not None:
            _publish_bytes_no_replace(args.report, canonical_json(output))
    print(canonical_json(output).decode("utf-8"), end="")


if __name__ == "__main__":
    try:
        main()
    except DeploymentStop as error:
        failure = {
            "terminal_state": "DEPLOYMENT_HELPER_STOPPED",
            "first_reason": error.first_reason,
            "message": str(error),
        }
        print(canonical_json(failure).decode("utf-8"), end="", file=sys.stderr)
        raise SystemExit(1) from error
