#!/usr/bin/env python3
"""Outcome-blind manifest gate for Zenodo record 11945905.

This v3 runner deliberately stops before reading any archive member content.  It
verifies the immutable archive and compares its central-directory structure to
the official record description.  Header or field inspection requires a later
reviewed revision only if this cheaper gate passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


PROTOCOL_REVISION = "v3"
EXPECTED_RECORD_ID = 11945905
EXPECTED_CONCEPT_ID = "11945904"
EXPECTED_DOI = "10.5281/zenodo.11945905"
EXPECTED_ARCHIVE_NAME = "multiscale_digital_image_correlation.zip"
EXPECTED_SIZE = 1_248_078_255
EXPECTED_MD5 = "e671b804e29401e70043bc1e17f66dd1"
EXPECTED_GLOBAL_NODEMAPS = 797
EXPECTED_GLOBAL_CONNECTIONS = 797
EXPECTED_MAPPING_BASENAME = "local_2d_microscopic_coordinates_by_nodemaps.csv"
EXPECTED_DICTIONARIES = (
    "higher_level_metadata_dictionary.json",
    "timestep_level_metadata_dictionary.json",
)
EXPECTED_AUDIT_ROOT = Path(
    "/Users/wenxiaofang/phase-field-fracture-with-pidl/"
    "local_archive/experiments/S03-E003/runs/S03-E003-R001"
)
EXPECTED_RAW_ROOT = Path(
    "/Users/wenxiaofang/phase-field-fracture-with-pidl/"
    "local_archive/open_data/aa2024_dic_zenodo_11945905_20261008/raw"
)
SUPPORTED_COMPRESSION = {
    zipfile.ZIP_STORED,
    zipfile.ZIP_DEFLATED,
    zipfile.ZIP_BZIP2,
    zipfile.ZIP_LZMA,
}
FIXED_REASON_CODES = {
    "OFFICIAL_METADATA_INVALID",
    "ARCHIVE_IDENTITY_MISMATCH",
    "ZIP_CENTRAL_DIRECTORY_INVALID",
    "UNSAFE_OR_AMBIGUOUS_MEMBER_PATH",
    "UNSUPPORTED_OR_ENCRYPTED_MEMBER",
    "GLOBAL_NODEMAP_COUNT_MISMATCH",
    "GLOBAL_CONNECTION_COUNT_MISMATCH",
    "MAPPING_FILE_IDENTITY_MISMATCH",
    "METADATA_DICTIONARY_IDENTITY_MISMATCH",
}


@dataclass(frozen=True)
class IdentityLock:
    record_id: int = EXPECTED_RECORD_ID
    concept_id: str = EXPECTED_CONCEPT_ID
    doi: str = EXPECTED_DOI
    archive_name: str = EXPECTED_ARCHIVE_NAME
    archive_size: int = EXPECTED_SIZE
    archive_md5: str = EXPECTED_MD5
    expected_global_nodemaps: int = EXPECTED_GLOBAL_NODEMAPS
    expected_global_connections: int = EXPECTED_GLOBAL_CONNECTIONS
    expected_mapping_basename: str = EXPECTED_MAPPING_BASENAME
    expected_dictionaries: tuple[str, ...] = EXPECTED_DICTIONARIES


class AuditError(ValueError):
    """Controlled local configuration or output error."""


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_member(name: str) -> str | None:
    if "\\" in name:
        return None
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        return None
    parts = [part for part in path.parts if part not in ("", ".")]
    if not parts:
        return None
    return "/".join(parts)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF)


def _official_metadata(payload: Any, lock: IdentityLock) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "record_identity": False,
            "doi_identity": False,
            "license_identity": False,
            "archive_entry_identity": False,
        }
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    files = payload.get("files") if isinstance(payload.get("files"), list) else []
    archive_entries = [
        entry for entry in files
        if isinstance(entry, dict) and entry.get("key") == lock.archive_name
    ]
    archive_entry = archive_entries[0] if len(archive_entries) == 1 else {}
    license_field = metadata.get("license")
    license_id = license_field.get("id") if isinstance(license_field, dict) else None
    return {
        "record_identity": (
            payload.get("id") == lock.record_id
            and str(payload.get("conceptrecid")) == lock.concept_id
        ),
        "doi_identity": metadata.get("doi") == lock.doi,
        "license_identity": license_id == "cc-by-4.0",
        "archive_entry_identity": (
            len(archive_entries) == 1
            and archive_entry.get("size") == lock.archive_size
            and archive_entry.get("checksum") == f"md5:{lock.archive_md5}"
        ),
    }


def _empty_manifest(lock: IdentityLock = IdentityLock()) -> dict[str, Any]:
    return {
        "central_directory_readable": False,
        "safe_unique_paths": False,
        "supported_unencrypted_regular_files": False,
        "total_file_count": 0,
        "global_nodemap_count": 0,
        "global_connection_count": 0,
        "local_nodemap_count": 0,
        "expected_mapping_file_count": 0,
        "expected_dictionary_counts": {
            name: 0 for name in lock.expected_dictionaries
        },
    }


def _manifest(archive_path: Path, lock: IdentityLock) -> tuple[dict[str, Any], list[str]]:
    result = _empty_manifest(lock)
    reasons: list[str] = []
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            infos = archive.infolist()
    except (OSError, zipfile.BadZipFile, NotImplementedError):
        return result, ["ZIP_CENTRAL_DIRECTORY_INVALID"]

    result["central_directory_readable"] = True
    canonical_infos: list[tuple[str, zipfile.ZipInfo]] = []
    path_invalid = False
    member_invalid = False
    for info in infos:
        normalized = _canonical_member(info.filename)
        if normalized is None:
            path_invalid = True
            continue
        canonical_infos.append((normalized, info))
        if (info.flag_bits & 0x1) or _is_symlink(info) or info.compress_type not in SUPPORTED_COMPRESSION:
            member_invalid = True
    canonical = [name for name, _info in canonical_infos]
    folded = [name.casefold() for name in canonical]
    if len(canonical) != len(set(canonical)) or len(folded) != len(set(folded)):
        path_invalid = True
    result["safe_unique_paths"] = not path_invalid
    result["supported_unencrypted_regular_files"] = not member_invalid
    if path_invalid:
        reasons.append("UNSAFE_OR_AMBIGUOUS_MEMBER_PATH")
    if member_invalid:
        reasons.append("UNSUPPORTED_OR_ENCRYPTED_MEMBER")

    files = [
        name for name, info in canonical_infos if not info.is_dir()
    ]
    result["total_file_count"] = len(files)
    result["global_nodemap_count"] = sum(
        1 for name in files
        if "/global_3d_dic/nodemaps/" in f"/{name.casefold()}"
        and name.casefold().endswith(".txt")
    )
    result["global_connection_count"] = sum(
        1 for name in files
        if "/global_3d_dic/connections/" in f"/{name.casefold()}"
        and name.casefold().endswith(".txt")
    )
    result["local_nodemap_count"] = sum(
        1 for name in files
        if "/local_2d_dic/" in f"/{name.casefold()}"
        and "/nodemaps/" in f"/{name.casefold()}"
        and name.casefold().endswith(".txt")
    )
    basenames = Counter(PurePosixPath(name).name.casefold() for name in files)
    result["expected_mapping_file_count"] = basenames[lock.expected_mapping_basename.casefold()]
    result["expected_dictionary_counts"] = {
        name: basenames[name.casefold()] for name in lock.expected_dictionaries
    }
    return result, reasons


def _result(
    official: dict[str, Any],
    identity: dict[str, Any],
    manifest: dict[str, Any],
    reasons: list[str],
    lock: IdentityLock,
) -> dict[str, Any]:
    if not all(official.values()):
        reasons.append("OFFICIAL_METADATA_INVALID")
    if not all(identity.values()):
        reasons.append("ARCHIVE_IDENTITY_MISMATCH")
    if all(official.values()) and all(identity.values()) and not reasons:
        if manifest["global_nodemap_count"] != lock.expected_global_nodemaps:
            reasons.append("GLOBAL_NODEMAP_COUNT_MISMATCH")
        if manifest["global_connection_count"] != lock.expected_global_connections:
            reasons.append("GLOBAL_CONNECTION_COUNT_MISMATCH")
        if manifest["expected_mapping_file_count"] != 1:
            reasons.append("MAPPING_FILE_IDENTITY_MISMATCH")
        if any(count != 1 for count in manifest["expected_dictionary_counts"].values()):
            reasons.append("METADATA_DICTIONARY_IDENTITY_MISMATCH")
    reasons = sorted(set(reasons))
    if not set(reasons).issubset(FIXED_REASON_CODES):
        raise AuditError("noncanonical stop reason")
    decision = "QUALIFIED_FOR_HEADER_AUDIT" if not reasons else "BLOCKED_DATASET_CAPABILITY"
    output = {
        "schema_version": 3,
        "experiment_id": "S03-E003",
        "protocol_revision": PROTOCOL_REVISION,
        "value_blinded": True,
        "scope": "archive_identity_and_central_directory_only",
        "official_metadata_checks": official,
        "local_archive_checks": identity,
        "manifest_counts": manifest,
        "decision": decision,
        "stop_reason_codes": reasons,
        "allowed_conclusion": (
            "header_audit_may_be_designed" if not reasons
            else "locked_archive_does_not_meet_declared_manifest_contract"
        ),
        "blocked_conclusions": [
            "header semantics", "chronology", "target support", "forecast performance",
            "phase-field recovery", "material-property identification", "road transfer",
        ],
    }
    _validate_output_schema(output)
    return output


def _validate_output_schema(output: dict[str, Any]) -> None:
    expected_top = {
        "schema_version", "experiment_id", "protocol_revision", "value_blinded",
        "scope", "official_metadata_checks", "local_archive_checks", "manifest_counts",
        "decision", "stop_reason_codes", "allowed_conclusion", "blocked_conclusions",
    }
    if set(output) != expected_top:
        raise AuditError("output schema mismatch")
    if output["protocol_revision"] != PROTOCOL_REVISION:
        raise AuditError("protocol identity mismatch")
    if not isinstance(output["value_blinded"], bool) or output["value_blinded"] is not True:
        raise AuditError("value-blind marker mismatch")
    if output["decision"] not in {"QUALIFIED_FOR_HEADER_AUDIT", "BLOCKED_DATASET_CAPABILITY"}:
        raise AuditError("decision enum mismatch")
    if not set(output["stop_reason_codes"]).issubset(FIXED_REASON_CODES):
        raise AuditError("stop reason enum mismatch")
    if not all(isinstance(value, bool) for value in output["official_metadata_checks"].values()):
        raise AuditError("official metadata output must be boolean-only")
    if not all(isinstance(value, bool) for value in output["local_archive_checks"].values()):
        raise AuditError("archive identity output must be boolean-only")
    rendered = json.dumps(output, sort_keys=True)
    for forbidden in (
        "cracklength_values", "per_episode", "field_array", "source_description",
        "member_name", "filename",
    ):
        if forbidden in rendered.lower():
            raise AuditError("output contains a forbidden key or source")


def audit(
    api_metadata: Path,
    archive_path: Path,
    lock: IdentityLock = IdentityLock(),
) -> dict[str, Any]:
    try:
        payload = json.loads(api_metadata.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        payload = None
    official = _official_metadata(payload, lock)
    try:
        size_matches = archive_path.stat().st_size == lock.archive_size
        name_matches = archive_path.name == lock.archive_name
        md5_matches = _md5(archive_path) == lock.archive_md5
    except OSError:
        size_matches = name_matches = md5_matches = False
    identity = {
        "archive_name_matches": name_matches,
        "archive_size_matches": size_matches,
        "archive_md5_matches": md5_matches,
    }
    if not all(official.values()) or not all(identity.values()):
        manifest, reasons = _empty_manifest(lock), []
    else:
        manifest, reasons = _manifest(archive_path, lock)
    return _result(official, identity, manifest, reasons, lock)


def _validated_output_path(
    output: Path,
    inputs: tuple[Path, ...],
    allowed_root: Path = EXPECTED_AUDIT_ROOT,
    raw_root: Path = EXPECTED_RAW_ROOT,
) -> Path:
    root = allowed_root.resolve()
    raw = raw_root.resolve()
    target = output.resolve(strict=False)
    if target != root and root not in target.parents:
        raise AuditError("output must be inside the frozen audit root")
    if target == raw or raw in target.parents:
        raise AuditError("output cannot be placed in the immutable raw tree")
    for source in inputs:
        if target == source.resolve():
            raise AuditError("output collides with immutable input")
        if output.exists() and source.exists() and os.path.samefile(output, source):
            raise AuditError("output aliases immutable input")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.parent.resolve() != target.parent:
        raise AuditError("output parent contains a symlink alias")
    return target


def _atomic_write(path: Path, output: dict[str, Any]) -> None:
    _validate_output_schema(output)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        json.dump(output, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-metadata", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output_path = _validated_output_path(
        args.output, (args.api_metadata, args.archive)
    )
    result = audit(args.api_metadata, args.archive)
    _atomic_write(output_path, result)
    print(json.dumps({
        "decision": result["decision"],
        "stop_reason_codes": result["stop_reason_codes"],
        "output": str(output_path),
        "protocol_revision": PROTOCOL_REVISION,
    }, sort_keys=True))
    return 0 if result["decision"] == "QUALIFIED_FOR_HEADER_AUDIT" else 2


if __name__ == "__main__":
    sys.exit(main())
