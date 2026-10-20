"""Content-addressed, fail-closed deployment of the frozen S09-E017 archive.

This module has no SSH, network, authority, admission, model, or training path.
It prepares and verifies immutable chunks and atomically publishes the original
archive bytes only after every chunk and the assembled archive pass SHA-256.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Callable, Mapping


MANIFEST_SCHEMA = "s09-e017-content-addressed-archive-v1"
RECEIPT_SCHEMA = "s09-e017-content-addressed-deployment-receipt-v1"
CHUNK_NAME = re.compile(r"^(?P<index>[0-9]{5})-(?P<sha>[0-9a-f]{64})\.chunk$")
READ_SIZE = 1024 * 1024


class DeploymentStop(RuntimeError):
    """A first-stop condition with a stable machine-readable reason."""

    def __init__(
        self, first_reason: str, message: str, *, published: bool = False
    ) -> None:
        super().__init__(message)
        self.first_reason = first_reason
        self.published = published


@dataclass(frozen=True)
class AssemblyResult:
    output: Path
    bytes_written: int
    sha256: str
    verified_chunks: int
    elapsed_seconds: float


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(READ_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def _require(condition: bool, reason: str, message: str) -> None:
    if not condition:
        raise DeploymentStop(reason, message)


def _strict_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _regular_file(path: Path, *, reason: str) -> None:
    _require(path.exists(), reason, f"missing file: {path}")
    _require(path.is_file(), reason, f"not a regular file: {path}")
    _require(not path.is_symlink(), reason, f"symlink is forbidden: {path}")


def _directory(path: Path, *, create: bool = False) -> None:
    if create:
        path.mkdir(parents=True, exist_ok=True)
    _require(path.exists(), "PATH_CONFLICT", f"missing directory: {path}")
    _require(path.is_dir(), "PATH_CONFLICT", f"not a directory: {path}")
    _require(not path.is_symlink(), "PATH_CONFLICT", f"symlink is forbidden: {path}")


def _publish_bytes_no_replace(path: Path, payload: bytes) -> None:
    """Publish bytes without replacing an existing path."""
    _directory(path.parent, create=True)
    temp = path.parent / f".{path.name}.tmp-{os.getpid()}"
    _require(not temp.exists(), "PATH_CONFLICT", f"temporary path exists: {temp}")
    try:
        with temp.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp, path)
        except FileExistsError as error:
            raise DeploymentStop(
                "PATH_CONFLICT", f"refusing to replace {path}"
            ) from error
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temp.exists():
            temp.unlink()


def require_new_path(path: Path, *, reason: str = "PATH_CONFLICT") -> None:
    _require(not path.exists(), reason, f"refusing to replace {path}")


def manifest_sha256(manifest: Mapping[str, Any]) -> str:
    validate_manifest(manifest)
    return sha256_bytes(canonical_json(manifest))


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    required = {"schema_version", "deployment_scope", "source", "chunking", "chunks"}
    _require(set(manifest) == required, "MANIFEST_INVALID", "manifest keys drift")
    _require(
        manifest["schema_version"] == MANIFEST_SCHEMA,
        "MANIFEST_INVALID",
        "manifest schema drift",
    )
    _require(
        manifest["deployment_scope"] == "DEPLOYMENT_HELPER_ONLY_NO_EXECUTION",
        "MANIFEST_INVALID",
        "deployment scope drift",
    )
    source = manifest["source"]
    _require(
        isinstance(source, dict)
        and set(source) == {"basename", "bytes", "sha256", "reviewed_control_commit"},
        "MANIFEST_INVALID",
        "source schema drift",
    )
    _require(
        isinstance(source["basename"], str)
        and source["basename"]
        and Path(source["basename"]).name == source["basename"],
        "MANIFEST_INVALID",
        "source basename invalid",
    )
    _require(
        _strict_int(source["bytes"]) and source["bytes"] > 0,
        "MANIFEST_INVALID",
        "source byte count invalid",
    )
    _require(
        isinstance(source["sha256"], str)
        and re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) is not None,
        "MANIFEST_INVALID",
        "source SHA-256 invalid",
    )
    _require(
        isinstance(source["reviewed_control_commit"], str)
        and re.fullmatch(r"[0-9a-f]{40}", source["reviewed_control_commit"])
        is not None,
        "MANIFEST_INVALID",
        "reviewed commit invalid",
    )
    chunking = manifest["chunking"]
    _require(
        isinstance(chunking, dict)
        and set(chunking) == {"algorithm", "chunk_count", "chunk_size_bytes"},
        "MANIFEST_INVALID",
        "chunking schema drift",
    )
    _require(
        chunking["algorithm"] == "fixed-size-sha256",
        "MANIFEST_INVALID",
        "chunking algorithm drift",
    )
    _require(
        _strict_int(chunking["chunk_size_bytes"]) and chunking["chunk_size_bytes"] > 0,
        "MANIFEST_INVALID",
        "chunk size invalid",
    )
    chunks = manifest["chunks"]
    _require(isinstance(chunks, list) and chunks, "MANIFEST_INVALID", "chunks missing")
    _require(
        _strict_int(chunking["chunk_count"]) and chunking["chunk_count"] == len(chunks),
        "MANIFEST_INVALID",
        "chunk count drift",
    )
    offset = 0
    for expected_index, chunk in enumerate(chunks):
        _require(
            isinstance(chunk, dict)
            and set(chunk) == {"index", "name", "offset", "sha256", "size"},
            "MANIFEST_INVALID",
            f"chunk {expected_index} schema drift",
        )
        _require(
            _strict_int(chunk["index"]) and chunk["index"] == expected_index,
            "MANIFEST_INVALID",
            f"chunk {expected_index} index drift",
        )
        _require(
            _strict_int(chunk["offset"]) and chunk["offset"] == offset,
            "MANIFEST_INVALID",
            f"chunk {expected_index} offset drift",
        )
        _require(
            _strict_int(chunk["size"])
            and 0 < chunk["size"] <= chunking["chunk_size_bytes"],
            "MANIFEST_INVALID",
            f"chunk {expected_index} size invalid",
        )
        _require(
            isinstance(chunk["sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", chunk["sha256"]) is not None,
            "MANIFEST_INVALID",
            f"chunk {expected_index} SHA-256 invalid",
        )
        expected_name = f"{expected_index:05d}-{chunk['sha256']}.chunk"
        _require(
            chunk["name"] == expected_name
            and CHUNK_NAME.fullmatch(chunk["name"]) is not None,
            "MANIFEST_INVALID",
            f"chunk {expected_index} name invalid",
        )
        offset += chunk["size"]
    _require(
        offset == source["bytes"],
        "MANIFEST_INVALID",
        "chunk bytes do not cover source exactly",
    )
    _require(
        chunks[-1]["size"] <= chunking["chunk_size_bytes"],
        "MANIFEST_INVALID",
        "final chunk too large",
    )
    for chunk in chunks[:-1]:
        _require(
            chunk["size"] == chunking["chunk_size_bytes"],
            "MANIFEST_INVALID",
            "non-final chunk is not full sized",
        )


def load_manifest(path: Path, *, expected_sha256: str) -> dict[str, Any]:
    _regular_file(path, reason="MANIFEST_MISSING")
    payload = path.read_bytes()
    _require(
        sha256_bytes(payload) == expected_sha256,
        "MANIFEST_HASH_MISMATCH",
        "manifest SHA-256 mismatch",
    )
    try:
        manifest = json.loads(
            payload,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise DeploymentStop(
            "MANIFEST_INVALID", "manifest is not strict JSON"
        ) from error
    _require(
        isinstance(manifest, dict), "MANIFEST_INVALID", "manifest is not an object"
    )
    validate_manifest(manifest)
    _require(
        payload == canonical_json(manifest),
        "MANIFEST_INVALID",
        "manifest is not canonical JSON",
    )
    return manifest


def build_chunk_store(
    archive: Path,
    chunk_dir: Path,
    *,
    chunk_size_bytes: int,
    expected_archive_bytes: int,
    expected_archive_sha256: str,
    reviewed_control_commit: str,
) -> dict[str, Any]:
    _regular_file(archive, reason="SOURCE_ARCHIVE_MISSING")
    _require(
        archive.stat().st_size == expected_archive_bytes,
        "SOURCE_ARCHIVE_SIZE_MISMATCH",
        "source archive size mismatch",
    )
    _require(
        sha256_path(archive) == expected_archive_sha256,
        "SOURCE_ARCHIVE_HASH_MISMATCH",
        "source archive SHA-256 mismatch",
    )
    _require(
        _strict_int(chunk_size_bytes) and chunk_size_bytes > 0,
        "MANIFEST_INVALID",
        "chunk size invalid",
    )
    _directory(chunk_dir, create=True)
    chunks: list[dict[str, Any]] = []
    offset = 0
    with archive.open("rb") as stream:
        index = 0
        while True:
            payload = stream.read(chunk_size_bytes)
            if not payload:
                break
            digest = sha256_bytes(payload)
            name = f"{index:05d}-{digest}.chunk"
            path = chunk_dir / name
            if path.exists():
                _regular_file(path, reason="CHUNK_PATH_CONFLICT")
                _require(
                    path.stat().st_size == len(payload) and sha256_path(path) == digest,
                    "CHUNK_PATH_CONFLICT",
                    f"existing chunk differs: {path}",
                )
            else:
                _publish_bytes_no_replace(path, payload)
            chunks.append(
                {
                    "index": index,
                    "name": name,
                    "offset": offset,
                    "sha256": digest,
                    "size": len(payload),
                }
            )
            offset += len(payload)
            index += 1
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "deployment_scope": "DEPLOYMENT_HELPER_ONLY_NO_EXECUTION",
        "source": {
            "basename": archive.name,
            "bytes": expected_archive_bytes,
            "sha256": expected_archive_sha256,
            "reviewed_control_commit": reviewed_control_commit,
        },
        "chunking": {
            "algorithm": "fixed-size-sha256",
            "chunk_count": len(chunks),
            "chunk_size_bytes": chunk_size_bytes,
        },
        "chunks": chunks,
    }
    validate_manifest(manifest)
    return manifest


def inspect_chunk_store(manifest: Mapping[str, Any], chunk_dir: Path) -> dict[str, Any]:
    validate_manifest(manifest)
    _directory(chunk_dir)
    expected_names = {chunk["name"] for chunk in manifest["chunks"]}
    present_valid: list[int] = []
    missing: list[int] = []
    corrupt: list[int] = []
    for chunk in manifest["chunks"]:
        path = chunk_dir / chunk["name"]
        if not path.exists():
            missing.append(chunk["index"])
            continue
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != chunk["size"]
            or sha256_path(path) != chunk["sha256"]
        ):
            corrupt.append(chunk["index"])
            continue
        present_valid.append(chunk["index"])
    unexpected = sorted(
        path.name for path in chunk_dir.iterdir() if path.name not in expected_names
    )
    return {
        "schema_version": "s09-e017-chunk-store-inspection-v1",
        "manifest_sha256": manifest_sha256(manifest),
        "present_valid": present_valid,
        "missing": missing,
        "missing_names": [manifest["chunks"][index]["name"] for index in missing],
        "corrupt": corrupt,
        "corrupt_names": [manifest["chunks"][index]["name"] for index in corrupt],
        "unexpected": unexpected,
        "complete": not missing and not corrupt,
        "verified_bytes": sum(
            manifest["chunks"][index]["size"] for index in present_valid
        ),
    }


def audit_legacy_partial(
    manifest: Mapping[str, Any], legacy_partial: Path
) -> dict[str, Any]:
    """Read-only audit; no prefix or percentage claim is trusted."""
    validate_manifest(manifest)
    _regular_file(legacy_partial, reason="LEGACY_PARTIAL_MISSING")
    file_size = legacy_partial.stat().st_size
    verified: list[int] = []
    mismatched: list[int] = []
    incomplete: list[int] = []
    absent: list[int] = []
    with legacy_partial.open("rb") as stream:
        for chunk in manifest["chunks"]:
            if file_size <= chunk["offset"]:
                absent.append(chunk["index"])
                continue
            if file_size < chunk["offset"] + chunk["size"]:
                incomplete.append(chunk["index"])
                continue
            stream.seek(chunk["offset"])
            payload = stream.read(chunk["size"])
            if (
                len(payload) == chunk["size"]
                and sha256_bytes(payload) == chunk["sha256"]
            ):
                verified.append(chunk["index"])
            else:
                mismatched.append(chunk["index"])
    return {
        "schema_version": "s09-e017-legacy-partial-audit-v1",
        "manifest_sha256": manifest_sha256(manifest),
        "legacy_path": str(legacy_partial),
        "legacy_bytes": file_size,
        "legacy_sha256": sha256_path(legacy_partial),
        "verified_complete_chunks": verified,
        "mismatched_complete_chunks": mismatched,
        "incomplete_chunks": incomplete,
        "absent_chunks": absent,
        "verified_reusable_bytes": sum(
            manifest["chunks"][index]["size"] for index in verified
        ),
        "read_only": True,
    }


def import_verified_legacy_chunks(
    manifest: Mapping[str, Any], legacy_partial: Path, chunk_dir: Path
) -> dict[str, Any]:
    """Reverify and atomically copy only matching complete legacy ranges."""
    report = audit_legacy_partial(manifest, legacy_partial)
    _directory(chunk_dir, create=True)
    imported: list[int] = []
    with legacy_partial.open("rb") as stream:
        for index in report["verified_complete_chunks"]:
            chunk = manifest["chunks"][index]
            stream.seek(chunk["offset"])
            payload = stream.read(chunk["size"])
            _require(
                len(payload) == chunk["size"]
                and sha256_bytes(payload) == chunk["sha256"],
                "LEGACY_CHANGED_DURING_IMPORT",
                f"legacy bytes changed for chunk {index}",
            )
            destination = chunk_dir / chunk["name"]
            if destination.exists():
                _regular_file(destination, reason="CHUNK_PATH_CONFLICT")
                _require(
                    destination.stat().st_size == chunk["size"]
                    and sha256_path(destination) == chunk["sha256"],
                    "CHUNK_PATH_CONFLICT",
                    f"existing imported chunk differs: {destination}",
                )
            else:
                _publish_bytes_no_replace(destination, payload)
            imported.append(index)
    return {
        "schema_version": "s09-e017-legacy-import-v1",
        "manifest_sha256": manifest_sha256(manifest),
        "legacy_sha256": report["legacy_sha256"],
        "imported_chunks": imported,
        "imported_bytes": sum(manifest["chunks"][index]["size"] for index in imported),
        "reverified_during_import": True,
    }


def assemble_archive(
    manifest: Mapping[str, Any],
    chunk_dir: Path,
    output: Path,
    *,
    max_wall_seconds: float,
    monotonic: Callable[[], float] = time.monotonic,
    before_publish: Callable[[Mapping[str, Any]], None] | None = None,
) -> AssemblyResult:
    validate_manifest(manifest)
    _require(max_wall_seconds > 0, "BUDGET_INVALID", "wall cap must be positive")
    _directory(chunk_dir)
    _directory(output.parent)
    _require(not output.exists(), "PUBLISH_PATH_CONFLICT", f"output exists: {output}")
    manifest_hash = manifest_sha256(manifest)
    temp = output.parent / f".{output.name}.assembly-{manifest_hash[:16]}.tmp"
    _require(not temp.exists(), "PATH_CONFLICT", f"assembly temp exists: {temp}")
    start = monotonic()
    verified_chunks = 0
    bytes_written = 0
    digest = hashlib.sha256()
    try:
        with temp.open("xb") as stream:
            for chunk in manifest["chunks"]:
                _require(
                    monotonic() - start <= max_wall_seconds,
                    "DEPLOYMENT_WALL_CAP_EXCEEDED",
                    "wall cap reached before chunk verification",
                )
                path = chunk_dir / chunk["name"]
                _regular_file(path, reason="CHUNK_MISSING")
                _require(
                    path.stat().st_size == chunk["size"]
                    and sha256_path(path) == chunk["sha256"],
                    "CHUNK_HASH_MISMATCH",
                    f"chunk verification failed: {path}",
                )
                payload = path.read_bytes()
                stream.write(payload)
                digest.update(payload)
                verified_chunks += 1
                bytes_written += len(payload)
            stream.flush()
            os.fsync(stream.fileno())
        _require(
            monotonic() - start <= max_wall_seconds,
            "DEPLOYMENT_WALL_CAP_EXCEEDED",
            "wall cap reached before final publication",
        )
        _require(
            bytes_written == manifest["source"]["bytes"],
            "ASSEMBLED_SIZE_MISMATCH",
            "assembled byte count mismatch",
        )
        archive_sha = digest.hexdigest()
        _require(
            archive_sha == manifest["source"]["sha256"],
            "ASSEMBLED_HASH_MISMATCH",
            "assembled archive SHA-256 mismatch",
        )
        if before_publish is not None:
            before_publish(
                {
                    "archive_bytes": bytes_written,
                    "archive_sha256": archive_sha,
                    "manifest_sha256": manifest_hash,
                    "output": str(output),
                    "verified_chunks": verified_chunks,
                }
            )
        try:
            os.link(temp, output)
        except FileExistsError as error:
            raise DeploymentStop(
                "PUBLISH_PATH_CONFLICT",
                f"refusing to replace {output}",
                published=False,
            ) from error
        try:
            directory_fd = os.open(output.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError as error:
            raise DeploymentStop(
                "PUBLISH_DURABILITY_UNCONFIRMED",
                f"archive linked but directory fsync failed: {error}",
                published=True,
            ) from error
        elapsed = monotonic() - start
        return AssemblyResult(
            output=output,
            bytes_written=bytes_written,
            sha256=archive_sha,
            verified_chunks=verified_chunks,
            elapsed_seconds=elapsed,
        )
    finally:
        if temp.exists():
            try:
                temp.unlink()
            except OSError:
                # The original stop remains authoritative. A stale hidden temp
                # cannot be mistaken for the expected archive path.
                pass


def assemble_with_receipt(
    manifest: Mapping[str, Any],
    chunk_dir: Path,
    output: Path,
    receipt: Path,
    *,
    max_wall_seconds: float,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    attempt_receipt = receipt.with_name(f"{receipt.name}.attempt")
    prepared_receipt = receipt.with_name(f"{receipt.name}.prepared")
    fallback_receipt = receipt.with_name(f"{receipt.name}.failure")
    for path in (receipt, attempt_receipt, prepared_receipt, fallback_receipt):
        require_new_path(path, reason="RECEIPT_PATH_CONFLICT")
    start = monotonic()
    attempt = {
        "schema_version": RECEIPT_SCHEMA,
        "terminal_state": "DEPLOYMENT_ASSEMBLY_STARTED",
        "manifest_sha256": manifest_sha256(manifest),
        "output": str(output),
        "published": False,
    }
    _publish_bytes_no_replace(attempt_receipt, canonical_json(attempt))

    def record_prepared(details: Mapping[str, Any]) -> None:
        prepared = {
            "schema_version": RECEIPT_SCHEMA,
            "terminal_state": "DEPLOYMENT_ARCHIVE_PREPARED",
            "manifest_sha256": details["manifest_sha256"],
            "output": details["output"],
            "archive_bytes": details["archive_bytes"],
            "archive_sha256": details["archive_sha256"],
            "verified_chunks": details["verified_chunks"],
            "published": False,
        }
        _publish_bytes_no_replace(prepared_receipt, canonical_json(prepared))

    try:
        result = assemble_archive(
            manifest,
            chunk_dir,
            output,
            max_wall_seconds=max_wall_seconds,
            monotonic=monotonic,
            before_publish=record_prepared,
        )
    except (DeploymentStop, OSError) as error:
        if isinstance(error, DeploymentStop):
            first_reason = error.first_reason
            published = error.published
        else:
            first_reason = "DEPLOYMENT_IO_ERROR"
            published = False
        payload = {
            "schema_version": RECEIPT_SCHEMA,
            "terminal_state": (
                "DEPLOYMENT_STOPPED_AFTER_PUBLICATION"
                if published
                else "DEPLOYMENT_STOPPED_BEFORE_PUBLICATION"
            ),
            "first_reason": first_reason,
            "message": str(error),
            "manifest_sha256": manifest_sha256(manifest),
            "published": published,
            "output_exists": output.exists(),
            "elapsed_seconds": monotonic() - start,
        }
        try:
            _publish_bytes_no_replace(receipt, canonical_json(payload))
        except (DeploymentStop, OSError) as receipt_error:
            fallback = dict(payload)
            fallback["terminal_state"] = "DEPLOYMENT_TERMINAL_RECEIPT_WRITE_FAILED"
            fallback["terminal_receipt_error"] = str(receipt_error)
            _publish_bytes_no_replace(fallback_receipt, canonical_json(fallback))
        return payload
    payload = {
        "schema_version": RECEIPT_SCHEMA,
        "terminal_state": "DEPLOYMENT_ARCHIVE_PUBLISHED",
        "first_reason": None,
        "manifest_sha256": manifest_sha256(manifest),
        "published": True,
        "output": str(result.output),
        "archive_bytes": result.bytes_written,
        "archive_sha256": result.sha256,
        "verified_chunks": result.verified_chunks,
        "elapsed_seconds": result.elapsed_seconds,
    }
    try:
        _publish_bytes_no_replace(receipt, canonical_json(payload))
    except (DeploymentStop, OSError) as error:
        fallback = {
            "schema_version": RECEIPT_SCHEMA,
            "terminal_state": "DEPLOYMENT_TERMINAL_RECEIPT_WRITE_FAILED",
            "first_reason": "TERMINAL_RECEIPT_WRITE_FAILED",
            "message": str(error),
            "manifest_sha256": manifest_sha256(manifest),
            "published": True,
            "output_exists": output.exists(),
            "archive_bytes": result.bytes_written,
            "archive_sha256": result.sha256,
            "elapsed_seconds": monotonic() - start,
        }
        _publish_bytes_no_replace(fallback_receipt, canonical_json(fallback))
        return fallback
    return payload
