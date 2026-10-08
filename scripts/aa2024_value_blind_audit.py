#!/usr/bin/env python3
"""Outcome-blind manifest gate for Zenodo record 11945905.

This v4 runner deliberately stops before reading any archive member content.  It
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


PROTOCOL_REVISION = "v4"
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


class DuplicateKeyError(ValueError):
    """Raised when untrusted JSON contains an ambiguous duplicate key."""


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_member(name: str) -> str | None:
    if not isinstance(name, str) or "\x00" in name or "\\" in name:
        return None
    if any(ord(character) < 32 for character in name):
        return None
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or (
        path.parts and path.parts[0].endswith(":")
    ):
        return None
    parts = [part for part in path.parts if part not in ("", ".")]
    if not parts:
        return None
    return "/".join(parts)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF)


def _is_supported_file_type(info: zipfile.ZipInfo) -> bool:
    """Accept ordinary files/directories and unspecified legacy ZIP modes."""
    if info.create_system != 3:
        return True
    mode = (info.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(mode)
    return file_type in (0, stat.S_IFREG, stat.S_IFDIR)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(key)
        result[key] = value
    return result


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
            type(payload.get("id")) is int
            and payload.get("id") == lock.record_id
            and isinstance(payload.get("conceptrecid"), (str, int))
            and not isinstance(payload.get("conceptrecid"), bool)
            and str(payload.get("conceptrecid")) == lock.concept_id
        ),
        "doi_identity": metadata.get("doi") == lock.doi,
        "license_identity": license_id == "cc-by-4.0",
        "archive_entry_identity": (
            len(archive_entries) == 1
            and type(archive_entry.get("size")) is int
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
    except (OSError, UnicodeError, zipfile.BadZipFile, NotImplementedError):
        return result, ["ZIP_CENTRAL_DIRECTORY_INVALID"]

    result["central_directory_readable"] = True
    canonical_infos: list[tuple[str, zipfile.ZipInfo, bool]] = []
    path_invalid = False
    member_invalid = False
    for info in infos:
        original_name = info.orig_filename
        normalized = _canonical_member(original_name)
        if normalized is None:
            path_invalid = True
            continue
        is_directory = original_name.endswith("/") or (
            info.create_system == 3
            and stat.S_ISDIR((info.external_attr >> 16) & 0xFFFF)
        )
        canonical_infos.append((normalized, info, is_directory))
        if (
            (info.flag_bits & 0x1)
            or _is_symlink(info)
            or not _is_supported_file_type(info)
            or info.compress_type not in SUPPORTED_COMPRESSION
        ):
            member_invalid = True
    canonical = [name for name, _info, _is_directory in canonical_infos]
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
        name for name, _info, is_directory in canonical_infos if not is_directory
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
    basenames = Counter(PurePosixPath(name).name for name in files)
    result["expected_mapping_file_count"] = basenames[lock.expected_mapping_basename]
    result["expected_dictionary_counts"] = {
        name: basenames[name] for name in lock.expected_dictionaries
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
    manifest_failure_codes = {
        "UNSAFE_OR_AMBIGUOUS_MEMBER_PATH",
        "UNSUPPORTED_OR_ENCRYPTED_MEMBER",
        "GLOBAL_NODEMAP_COUNT_MISMATCH",
        "GLOBAL_CONNECTION_COUNT_MISMATCH",
        "MAPPING_FILE_IDENTITY_MISMATCH",
        "METADATA_DICTIONARY_IDENTITY_MISMATCH",
    }
    if not reasons:
        allowed_conclusion = "header_audit_may_be_designed"
    elif manifest["central_directory_readable"] and any(
        reason in manifest_failure_codes for reason in reasons
    ):
        allowed_conclusion = "locked_archive_does_not_meet_declared_manifest_contract"
    else:
        allowed_conclusion = "qualification_not_established"
    output = {
        "schema_version": 4,
        "experiment_id": "S03-E003",
        "protocol_revision": PROTOCOL_REVISION,
        "value_blinded": True,
        "scope": "archive_identity_and_central_directory_only",
        "official_metadata_checks": official,
        "local_archive_checks": identity,
        "manifest_counts": manifest,
        "decision": decision,
        "stop_reason_codes": reasons,
        "allowed_conclusion": allowed_conclusion,
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
    if output["schema_version"] != 4:
        raise AuditError("schema version mismatch")
    if output["experiment_id"] != "S03-E003":
        raise AuditError("experiment identity mismatch")
    if output["protocol_revision"] != PROTOCOL_REVISION:
        raise AuditError("protocol identity mismatch")
    if not isinstance(output["value_blinded"], bool) or output["value_blinded"] is not True:
        raise AuditError("value-blind marker mismatch")
    if output["decision"] not in {"QUALIFIED_FOR_HEADER_AUDIT", "BLOCKED_DATASET_CAPABILITY"}:
        raise AuditError("decision enum mismatch")
    if output["allowed_conclusion"] not in {
        "header_audit_may_be_designed",
        "locked_archive_does_not_meet_declared_manifest_contract",
        "qualification_not_established",
    }:
        raise AuditError("allowed conclusion enum mismatch")
    if not set(output["stop_reason_codes"]).issubset(FIXED_REASON_CODES):
        raise AuditError("stop reason enum mismatch")
    if output["stop_reason_codes"] != sorted(set(output["stop_reason_codes"])):
        raise AuditError("stop reasons must be sorted and unique")
    expected_official = {
        "record_identity", "doi_identity", "license_identity", "archive_entry_identity",
    }
    expected_identity = {
        "archive_name_matches", "archive_size_matches", "archive_md5_matches",
    }
    expected_manifest = {
        "central_directory_readable", "safe_unique_paths",
        "supported_unencrypted_regular_files", "total_file_count",
        "global_nodemap_count", "global_connection_count", "local_nodemap_count",
        "expected_mapping_file_count", "expected_dictionary_counts",
    }
    if set(output["official_metadata_checks"]) != expected_official:
        raise AuditError("official metadata schema mismatch")
    if set(output["local_archive_checks"]) != expected_identity:
        raise AuditError("archive identity schema mismatch")
    if set(output["manifest_counts"]) != expected_manifest:
        raise AuditError("manifest schema mismatch")
    if not all(isinstance(value, bool) for value in output["official_metadata_checks"].values()):
        raise AuditError("official metadata output must be boolean-only")
    if not all(isinstance(value, bool) for value in output["local_archive_checks"].values()):
        raise AuditError("archive identity output must be boolean-only")
    manifest = output["manifest_counts"]
    for key in (
        "central_directory_readable", "safe_unique_paths",
        "supported_unencrypted_regular_files",
    ):
        if type(manifest[key]) is not bool:
            raise AuditError("manifest flags must be boolean")
    for key in (
        "total_file_count", "global_nodemap_count", "global_connection_count",
        "local_nodemap_count", "expected_mapping_file_count",
    ):
        if type(manifest[key]) is not int or manifest[key] < 0:
            raise AuditError("manifest counts must be nonnegative integers")
    dictionary_counts = manifest["expected_dictionary_counts"]
    if not isinstance(dictionary_counts, dict) or set(dictionary_counts) != set(EXPECTED_DICTIONARIES):
        raise AuditError("dictionary count schema mismatch")
    if any(type(value) is not int or value < 0 for value in dictionary_counts.values()):
        raise AuditError("dictionary counts must be nonnegative integers")
    has_reasons = bool(output["stop_reason_codes"])
    if (output["decision"] == "QUALIFIED_FOR_HEADER_AUDIT") == has_reasons:
        raise AuditError("decision and stop reasons disagree")
    if output["decision"] == "QUALIFIED_FOR_HEADER_AUDIT" and (
        output["allowed_conclusion"] != "header_audit_may_be_designed"
    ):
        raise AuditError("qualified decision has inconsistent conclusion")
    if not isinstance(output["blocked_conclusions"], list) or not all(
        isinstance(value, str) for value in output["blocked_conclusions"]
    ):
        raise AuditError("blocked conclusions schema mismatch")
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
        payload = json.loads(
            api_metadata.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, DuplicateKeyError):
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
