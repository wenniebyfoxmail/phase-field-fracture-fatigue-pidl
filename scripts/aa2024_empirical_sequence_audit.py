#!/usr/bin/env python3
"""Bounded header audit of the actual AA2024 global-DIC sequence."""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import os
import re
import stat
import tempfile
import unicodedata
import zipfile
import zlib
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any


EXPERIMENT_ID = "S03-E004"
PROTOCOL_REVISION = "v1"
EXPECTED_SIZE = 1_248_078_255
EXPECTED_MD5 = "e671b804e29401e70043bc1e17f66dd1"
HEADER_BYTE_CAP = 131_072
EXPECTED_RUN_ROOT = Path(
    "/Users/wenxiaofang/phase-field-fracture-with-pidl/"
    "local_archive/experiments/S03-E004/runs/S03-E004-R001"
)
NODEMAP_RE = re.compile(
    r"^global_3d_dic/nodemaps/global_3d_dic_results_1_(\d+)\.txt$", re.I
)
CONNECTION_RE = re.compile(
    r"^global_3d_dic/connections/"
    r"global_3d_dic_results_1_(\d+)_connections\.txt$", re.I
)
REQUIRED_HEADER_FIELDS = (
    "current_stage_index",
    "current_stage_relative_date",
    "reference_stage_index",
    "force",
    "displacement",
    "cycles",
    "time",
    "cracklength",
)
REQUIRED_COLUMN_TOKENS = (
    "id", "x_undef", "y_undef", "z_undef", "u", "v", "w",
    "epsx", "epsy", "epsxy", "epseqv",
)
SUPPORTED_COMPRESSION = {
    zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED,
    zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA,
}
REASON_CODES = {
    "ARCHIVE_IDENTITY_MISMATCH",
    "ZIP_CENTRAL_DIRECTORY_INVALID",
    "UNSAFE_OR_AMBIGUOUS_MEMBER_PATH",
    "UNSUPPORTED_OR_ENCRYPTED_MEMBER",
    "GLOBAL_STAGE_PAIRING_INVALID",
    "GLOBAL_STAGE_COUNT_INSUFFICIENT",
    "NODEMAP_HEADER_INVALID",
    "REQUIRED_HEADER_FIELD_INVALID",
    "STAGE_IDENTITY_INVALID",
    "CHRONOLOGY_INVALID",
    "STATE_VARIATION_INSUFFICIENT",
    "NODEMAP_SCHEMA_INVALID",
    "STAGE_ID_PARSE_INVALID",
}

PARSER_FAILURE_REASONS = {
    "NODEMAP_HEADER_INVALID",
    "REQUIRED_HEADER_FIELD_INVALID",
    "STAGE_ID_PARSE_INVALID",
}


class AuditError(ValueError):
    """Controlled audit/configuration failure."""


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_member(name: str) -> str | None:
    if not isinstance(name, str) or "\\" in name:
        return None
    if any(unicodedata.category(char) == "Cc" for char in name):
        return None
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or (
        path.parts and path.parts[0].endswith(":")
    ):
        return None
    parts = [part for part in path.parts if part not in ("", ".")]
    return "/".join(parts) if parts else None


def _ordinary_supported(info: zipfile.ZipInfo) -> bool:
    if info.flag_bits & 0x1 or info.compress_type not in SUPPORTED_COMPRESSION:
        return False
    if info.create_system != 3:
        return True
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR)


def _is_directory(info: zipfile.ZipInfo) -> bool:
    if info.is_dir():
        return True
    # The MS-DOS directory attribute is independent of the trailing-slash
    # convention used by ZipInfo.is_dir().  A forged role-looking name must
    # not qualify merely because it was created on a non-Unix system.
    if info.external_attr & 0x10:
        return True
    if info.create_system != 3:
        return False
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_IFMT(mode) == stat.S_IFDIR


def _parse_numeric(text: str) -> Decimal:
    try:
        value = Decimal(text.strip())
    except InvalidOperation as exc:
        raise ValueError("invalid header value") from exc
    if not value.is_finite():
        raise ValueError("non-finite header value")
    return value


def _normalise_columns(line: str) -> tuple[str, ...]:
    columns = []
    for part in line.lstrip("#").split(";"):
        token = re.sub(r"\s*\[[^]]*\]\s*$", "", part.strip()).casefold()
        columns.append(token)
    return tuple(columns)


def _read_bounded_line(handle: Any, consumed: int) -> tuple[bytes, int]:
    """Read one logical header line without crossing the cap or a data row."""
    raw = bytearray()
    first_nonspace_seen = False
    while True:
        if consumed >= HEADER_BYTE_CAP:
            raise AuditError("header byte cap exceeded")
        byte = handle.read(1)
        if not byte:
            return bytes(raw), consumed
        consumed += 1
        raw.extend(byte)
        if not first_nonspace_seen:
            if byte == b"\n":
                return bytes(raw), consumed
            if byte in b" \t\r\v\f":
                continue
            # Header-control syntax is ASCII.  Reject any other leading
            # control or a non-ASCII prefix immediately, rather than reading
            # the rest of a potentially numerical body row before failing.
            if byte[0] < 0x20 or byte[0] == 0x7F or byte[0] >= 0x80:
                raise AuditError("unsupported leading header byte")
            first_nonspace_seen = True
            # A nodemap body row begins with a numeric node ID. Stop at its
            # first byte so a missing/malformed column header cannot consume it.
            if byte in b"+-0123456789.":
                raise AuditError("numerical body reached before column schema")
        if byte == b"\n":
            return bytes(raw), consumed


def _read_header(
    archive: zipfile.ZipFile, info: zipfile.ZipInfo
) -> tuple[dict[str, Decimal], tuple[str, ...]]:
    consumed = 0
    fields: dict[str, Decimal] = {}
    column_schema: tuple[str, ...] | None = None
    with archive.open(info, "r") as handle:
        while consumed < HEADER_BYTE_CAP:
            raw, consumed = _read_bounded_line(handle, consumed)
            if not raw:
                break
            try:
                line = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise AuditError("header is not UTF-8") from exc
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                content = stripped.lstrip("#").strip()
                if ":" in content:
                    try:
                        key, value = content.split(":", 1)
                        key = key.strip().casefold()
                        if key not in REQUIRED_HEADER_FIELDS:
                            continue
                        if key in fields:
                            raise AuditError(f"duplicate required field: {key}")
                        if "value_element" in value:
                            _label, value = value.split(":", 1)
                            fields[key] = _parse_numeric(value)
                        else:
                            fields[key] = _parse_numeric(value)
                    except (ValueError, IndexError) as exc:
                        raise AuditError(f"invalid required field: {key}") from exc
                continue
            column_schema = _normalise_columns(stripped)
            break
    if column_schema is None:
        raise AuditError("column schema not found within bounded header")
    return fields, column_schema


def _nondecreasing(values: list[Decimal]) -> bool:
    return all(right >= left for left, right in zip(values, values[1:]))


def audit(archive_path: Path, *, expected_size: int = EXPECTED_SIZE,
          expected_md5: str = EXPECTED_MD5) -> dict[str, Any]:
    reasons: set[str] = set()
    identity = {
        "size_matches": archive_path.is_file() and archive_path.stat().st_size == expected_size,
        "md5_matches": False,
    }
    if identity["size_matches"]:
        identity["md5_matches"] = _md5(archive_path) == expected_md5
    if not all(identity.values()):
        reasons.add("ARCHIVE_IDENTITY_MISMATCH")
        return _result(identity, {}, reasons)

    try:
        archive = zipfile.ZipFile(archive_path, "r")
        infos = archive.infolist()
    except (OSError, UnicodeError, zipfile.BadZipFile, NotImplementedError):
        reasons.add("ZIP_CENTRAL_DIRECTORY_INVALID")
        return _result(identity, {}, reasons)

    try:
        canonical: dict[str, zipfile.ZipInfo] = {}
        folded: set[str] = set()
        for info in infos:
            name = _canonical_member(info.orig_filename)
            if name is None or name in canonical or name.casefold() in folded:
                reasons.add("UNSAFE_OR_AMBIGUOUS_MEMBER_PATH")
                continue
            canonical[name] = info
            folded.add(name.casefold())
            if not _ordinary_supported(info):
                reasons.add("UNSUPPORTED_OR_ENCRYPTED_MEMBER")

        nodemaps: dict[int, tuple[str, zipfile.ZipInfo]] = {}
        connections: dict[int, tuple[str, zipfile.ZipInfo]] = {}
        for name, info in canonical.items():
            for regex, target in ((NODEMAP_RE, nodemaps),
                                  (CONNECTION_RE, connections)):
                match = regex.fullmatch(name)
                if match:
                    if _is_directory(info):
                        continue
                    try:
                        stage = int(match.group(1))
                    except (ValueError, OverflowError):
                        reasons.add("STAGE_ID_PARSE_INVALID")
                        continue
                    if stage in target:
                        reasons.add("GLOBAL_STAGE_PAIRING_INVALID")
                    target[stage] = (name, info)

        stages = sorted(nodemaps)
        if len(stages) < 2:
            reasons.add("GLOBAL_STAGE_COUNT_INSUFFICIENT")
        if set(nodemaps) != set(connections):
            reasons.add("GLOBAL_STAGE_PAIRING_INVALID")

        rows: list[dict[str, Decimal]] = []
        schemas: list[tuple[str, ...]] = []
        if not reasons.intersection({
            "UNSAFE_OR_AMBIGUOUS_MEMBER_PATH",
            "UNSUPPORTED_OR_ENCRYPTED_MEMBER",
            "GLOBAL_STAGE_PAIRING_INVALID",
            "GLOBAL_STAGE_COUNT_INSUFFICIENT",
            "STAGE_ID_PARSE_INVALID",
        }):
            for stage in stages:
                try:
                    fields, schema = _read_header(archive, nodemaps[stage][1])
                except (
                    AuditError, OSError, RuntimeError, UnicodeError,
                    EOFError, zlib.error, lzma.LZMAError, zipfile.BadZipFile,
                ):
                    reasons.add("NODEMAP_HEADER_INVALID")
                    break
                if set(REQUIRED_HEADER_FIELDS) - set(fields):
                    reasons.add("REQUIRED_HEADER_FIELD_INVALID")
                    break
                if fields["current_stage_index"] != Decimal(stage):
                    reasons.add("STAGE_IDENTITY_INVALID")
                    break
                if not all(token in schema for token in REQUIRED_COLUMN_TOKENS):
                    reasons.add("NODEMAP_SCHEMA_INVALID")
                    break
                if schemas and schema != schemas[0]:
                    reasons.add("NODEMAP_SCHEMA_INVALID")
                    break
                if rows and any(
                    fields[field] < rows[-1][field]
                    for field in ("current_stage_relative_date", "cycles", "time")
                ):
                    reasons.add("CHRONOLOGY_INVALID")
                    break
                rows.append(fields)
                schemas.append(schema)

        if rows and len(rows) == len(stages):
            if len({row["cycles"] for row in rows}) < 2 or len({
                row["cracklength"] for row in rows
            }) < 2:
                reasons.add("STATE_VARIATION_INSUFFICIENT")

        sequence = {
            "central_directory_readable": True,
            "global_nodemap_count": len(nodemaps),
            "global_connection_count": len(connections),
            "paired_stage_count": len(set(nodemaps) & set(connections)),
            "stage_id_sets_equal": set(nodemaps) == set(connections),
            "all_headers_parsed": len(rows) == len(stages) and bool(stages),
            "required_fields_complete": len(rows) == len(stages) and bool(stages),
            "stage_identity_matches": (
                bool(stages) and
                len(rows) == len(stages) and
                all(row["current_stage_index"] == stage for row, stage in zip(rows, stages))
            ),
            "chronology_nondecreasing": (
                bool(stages) and len(rows) == len(stages) and all(
                    _nondecreasing([row[field] for row in rows])
                    for field in ("current_stage_relative_date", "cycles", "time")
                )
            ),
            "distinct_cycle_count": len({row["cycles"] for row in rows}),
            "distinct_cracklength_count": len({row["cracklength"] for row in rows}),
            "stable_required_nodemap_schema": (
                len(schemas) == len(stages) and bool(stages) and
                all(schema == schemas[0] for schema in schemas) and
                all(token in schemas[0] for token in REQUIRED_COLUMN_TOKENS)
            ),
            "header_byte_cap": HEADER_BYTE_CAP,
            "nodemap_body_rows_read": 0,
            "connection_body_rows_read": 0,
        }
        return _result(identity, sequence, reasons)
    finally:
        archive.close()


def _result(identity: dict[str, Any], sequence: dict[str, Any],
            reasons: set[str]) -> dict[str, Any]:
    if not reasons.issubset(REASON_CODES):
        raise AuditError("noncanonical reason code")
    decision = (
        "QUALIFIED_EMPIRICAL_GLOBAL_SEQUENCE" if not reasons
        else "BLOCKED_EMPIRICAL_SEQUENCE"
    )
    if not reasons:
        conclusion = "empirical_global_sequence_may_enter_forecast_design"
    elif (
        reasons == {"ARCHIVE_IDENTITY_MISMATCH"}
        or reasons.intersection(PARSER_FAILURE_REASONS)
        or not sequence.get("central_directory_readable", False)
    ):
        conclusion = "qualification_not_established"
    else:
        conclusion = "actual_archive_sequence_fails_empirical_contract"
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "protocol_revision": PROTOCOL_REVISION,
        "scope": "actual_archive_global_dic_header_sequence_only",
        "official_manifest_count_used": False,
        "archive_identity": identity,
        "sequence_checks": sequence,
        "decision": decision,
        "stop_reason_codes": sorted(reasons),
        "allowed_conclusion": conclusion,
        "blocked_conclusions": [
            "forecast_skill", "phase_field_recovery", "material_identification",
            "fatigue_law_truth", "specimen_generalisation", "road_transfer",
        ],
    }


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise AuditError(f"refusing to overwrite: {path}")
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def _validated_output_path(path: Path, archive_path: Path,
                           run_root: Path = EXPECTED_RUN_ROOT) -> Path:
    resolved = path.resolve()
    root = run_root.resolve()
    if resolved == root or root not in resolved.parents:
        raise AuditError("output must be a strict descendant of the run root")
    if resolved == archive_path.resolve():
        raise AuditError("output aliases immutable input")
    if resolved.exists():
        raise AuditError(f"refusing to overwrite: {resolved}")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    archive = args.archive.resolve()
    output = _validated_output_path(args.output, archive)
    result = audit(archive)
    _atomic_write(output, result)
    print(result["decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
