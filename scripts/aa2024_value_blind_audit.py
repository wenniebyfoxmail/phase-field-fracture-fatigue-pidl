#!/usr/bin/env python3
"""Value-blinded capability audit for Zenodo record 11945905.

The audit reads ZIP metadata and nodemap headers only.  It never loads DIC field
arrays and never writes per-episode crack-length, force, displacement, strain,
or potential values to its output.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import io
import json
import math
import os
import re
import stat
import statistics
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


EXPECTED_RECORD_ID = 11945905
EXPECTED_CONCEPT_ID = "11945904"
EXPECTED_ARCHIVE_NAME = "multiscale_digital_image_correlation.zip"
EXPECTED_SIZE = 1_248_078_255
EXPECTED_MD5 = "e671b804e29401e70043bc1e17f66dd1"
DEFAULT_HORIZONS = (1_000, 2_000, 5_000, 10_000, 20_000, 50_000,
                    100_000, 200_000, 500_000, 1_000_000)
MAX_HEADER_BYTES = 64 * 1024
MAX_DICTIONARY_BYTES = 2 * 1024 * 1024
MAX_MAPPING_BYTES = 16 * 1024 * 1024
MIN_CALIBRATION_ORIGINS = 12
MIN_DEVELOPMENT_ORIGINS = 6
MIN_SEALED_ORIGINS = 8


ALIASES = {
    "cycles": ("cycles", "cycle", "numberofcycles", "loadcycles"),
    "force": ("force", "kraft"),
    "displacement": ("displacement", "actuatordisplacement", "weg"),
    "potential": ("potential", "voltage", "dcpdpotential"),
    "cracklength": ("cracklength", "cracklenght", "risslaenge", "risslange"),
    "dms_1": ("dms1", "backfacestrain1", "strainbackface1"),
    "dms_2": ("dms2", "backfacestrain2", "strainbackface2"),
}

LOCAL_FILE_KEYS = ("nodemap", "nodemapfile", "nodemapfilename", "filename", "file")
MISSING_TOKENS = {"", "none", "nan", "na", "n/a", "null", "missing", "-"}
EXACT_DICTIONARIES = {
    "higher_level_metadata_dictionary.json",
    "timestep_level_metadata_dictionary.json",
}


@dataclass(frozen=True)
class IdentityLock:
    record_id: int = EXPECTED_RECORD_ID
    concept_id: str = EXPECTED_CONCEPT_ID
    doi: str = "10.5281/zenodo.11945905"
    archive_name: str = EXPECTED_ARCHIVE_NAME
    archive_size: int = EXPECTED_SIZE
    archive_md5: str = EXPECTED_MD5
    expected_global_nodemaps: int = 797
    expected_global_connections: int = 797


class AuditFormatError(ValueError):
    """Raised when released metadata cannot be interpreted unambiguously."""


def _normalise_key(value: str) -> str:
    value = value.lower().replace("ä", "a").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", "", value)


def _canonical_key(raw_key: str) -> str | None:
    norm = _normalise_key(raw_key)
    for canonical, aliases in ALIASES.items():
        if norm in aliases:
            return canonical
    return None


def _strict_number(value: str | None) -> float | None:
    if value is None:
        return None
    stripped = value.strip()
    if stripped.lower() in MISSING_TOKENS or "," in stripped:
        return None
    match = re.fullmatch(
        r"\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
        r"(?:\s+[A-Za-z%µμ/²^0-9._-]+)?\s*",
        stripped,
    )
    if not match:
        return None
    parsed = float(match.group(1))
    return parsed if math.isfinite(parsed) else None


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and "\\" not in name


def _timestep_id(name: str) -> int | None:
    stem = PurePosixPath(name).stem
    match = re.search(r"(?:^|_)(\d+)$", stem)
    return int(match.group(1)) if match else None


def _read_header(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> dict[str, float | None]:
    values: dict[str, float | None] = {}
    with archive.open(info, "r") as raw:
        payload = raw.read(MAX_HEADER_BYTES + 1)
    if len(payload) > MAX_HEADER_BYTES:
        raise AuditFormatError(f"header exceeds {MAX_HEADER_BYTES} bytes")
    saw_data = False
    for line in payload.decode("windows-1252", errors="replace").splitlines():
        stripped = line.lstrip()
        if not stripped.startswith("#"):
            if stripped:
                saw_data = True
            break
        match = re.match(r"^\s*#\s*([^:#]+?)\s*:\s*(.*?)\s*$", line)
        if not match:
            continue
        canonical = _canonical_key(match.group(1))
        if canonical:
            if canonical in values:
                raise AuditFormatError(f"duplicate header field: {canonical}")
            values[canonical] = _strict_number(match.group(2))
    if not saw_data:
        raise AuditFormatError("header terminator/data row not found within bound")
    return values


def _read_json_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> Any:
    if info.file_size > MAX_DICTIONARY_BYTES:
        raise AuditFormatError("metadata dictionary exceeds bounded size")
    with archive.open(info, "r") as raw:
        return json.load(io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace"))


def _read_local_mapping(
    archive: zipfile.ZipFile, info: zipfile.ZipInfo
) -> dict[str, Any]:
    if info.file_size > MAX_MAPPING_BYTES:
        raise AuditFormatError("local mapping exceeds bounded size")
    with archive.open(info, "r") as raw:
        payload = raw.read(MAX_MAPPING_BYTES + 1)
    if len(payload) > MAX_MAPPING_BYTES:
        raise AuditFormatError("local mapping exceeds bounded read")
    text = payload.decode("utf-8-sig", errors="replace")
    sample = text[:8192]
    if not sample.strip():
        raise AuditFormatError("empty local mapping")
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error as exc:
        raise AuditFormatError("unresolved local mapping delimiter") from exc
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    columns = reader.fieldnames or []
    normalized_columns = [_normalise_key(column) for column in columns]
    if len(normalized_columns) != len(set(normalized_columns)):
        raise AuditFormatError("duplicate local mapping columns")
    cycle_column = next(
        (column for column in columns if _canonical_key(column) == "cycles"), None
    )
    file_column = next(
        (column for column in columns if _normalise_key(column) in LOCAL_FILE_KEYS), None
    )
    if cycle_column is None or file_column is None:
        raise AuditFormatError("local mapping requires exact cycle and nodemap-file columns")
    mappings: dict[str, float] = {}
    duplicate_file_rows = 0
    malformed_rows = 0
    missing_cycle = 0
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            malformed_rows += 1
            continue
        basename = PurePosixPath((row.get(file_column) or "").strip()).name
        cycle = _strict_number(row.get(cycle_column))
        if not basename or cycle is None or cycle < 0 or not cycle.is_integer():
            missing_cycle += 1
            continue
        if basename in mappings:
            duplicate_file_rows += 1
            continue
        mappings[basename] = cycle
    canonical_columns = sorted(
        {canonical for column in columns if (canonical := _canonical_key(column))}
    )
    canonical_columns.append("nodemap_file")
    return {
        "row_count": sum(1 for line in text.splitlines()[1:] if line.strip()),
        "canonical_columns": sorted(set(canonical_columns)),
        "unknown_column_count": sum(
            1 for column in columns
            if _canonical_key(column) is None and _normalise_key(column) not in LOCAL_FILE_KEYS
        ),
        "missing_or_invalid_cycle_rows": missing_cycle,
        "malformed_row_count": malformed_rows,
        "duplicate_file_row_count": duplicate_file_rows,
        "mappings": mappings,
    }


def _quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "q25": None, "median": None, "q75": None, "max": None}
    ordered = sorted(values)
    if len(ordered) == 1:
        q25 = median = q75 = ordered[0]
    else:
        qs = statistics.quantiles(ordered, n=4, method="inclusive")
        q25, median, q75 = qs
    return {
        "min": ordered[0],
        "q25": q25,
        "median": median,
        "q75": q75,
        "max": ordered[-1],
    }


def _segment(cycle: float, minimum: float, maximum: float) -> str:
    if maximum <= minimum:
        return "calibration"
    fraction = (cycle - minimum) / (maximum - minimum)
    if fraction < 0.60:
        return "calibration"
    if fraction < 0.80:
        return "development"
    return "sealed"


def _select_target(
    ordered: list[float], origin: float, horizon: int, tolerance: float
) -> float | None:
    desired = origin + horizon
    position = bisect.bisect_left(ordered, desired)
    candidates = []
    for index in (position - 1, position):
        if 0 <= index < len(ordered) and ordered[index] > origin:
            candidates.append(ordered[index])
    if not candidates:
        return None
    target = min(candidates, key=lambda value: (abs(value - desired), value))
    return target if abs(target - desired) <= tolerance else None


def _horizon_support(cycles: list[float], horizons: Iterable[int]) -> list[dict[str, Any]]:
    """Count one causally selected direct target per origin within each partition."""
    ordered = sorted(set(cycles))
    if not ordered:
        return []
    minimum, maximum = ordered[0], ordered[-1]
    results = []
    for horizon in horizons:
        tolerance = max(100.0, 0.05 * horizon)
        segment_pairs: dict[str, list[tuple[float, float]]] = {
            "calibration": [], "development": [], "sealed": []
        }
        exact_pairs = 0
        for origin in ordered[:-1]:
            target = _select_target(ordered, origin, horizon, tolerance)
            if target is None:
                continue
            origin_segment = _segment(origin, minimum, maximum)
            target_segment = _segment(target, minimum, maximum)
            if origin_segment != target_segment:
                continue
            segment_pairs[origin_segment].append((origin, target))
            if target - origin == horizon:
                exact_pairs += 1
        summary: dict[str, Any] = {
            "horizon_cycles": horizon,
            "tolerance_cycles": tolerance,
            "exact_cycle_pair_count": exact_pairs,
        }
        for name, pairs in segment_pairs.items():
            target_counts = Counter(target for _, target in pairs)
            summary[name] = {
                "eligible_distinct_origins": len({origin for origin, _ in pairs}),
                "unique_target_episode_count": len(target_counts),
                "maximum_target_reuse": max(target_counts.values(), default=0),
            }
        summary["meets_minimum_information"] = (
            summary["calibration"]["eligible_distinct_origins"] >= MIN_CALIBRATION_ORIGINS
            and summary["development"]["eligible_distinct_origins"] >= MIN_DEVELOPMENT_ORIGINS
            and summary["sealed"]["eligible_distinct_origins"] >= MIN_SEALED_ORIGINS
            and summary["sealed"]["unique_target_episode_count"] >= MIN_SEALED_ORIGINS
            and summary["sealed"]["maximum_target_reuse"] <= 1
        )
        results.append(summary)
    return results


def _official_metadata_audit(payload: dict[str, Any], lock: IdentityLock) -> dict[str, Any]:
    files = payload.get("files") or []
    archive_entry = next((item for item in files if item.get("key") == lock.archive_name), None)
    metadata = payload.get("metadata") or {}
    description = metadata.get("description") or ""
    license_field = metadata.get("license") or {}
    if isinstance(license_field, dict):
        license_id = license_field.get("id")
    else:
        license_id = license_field
    return {
        "record_id_matches": payload.get("id") == lock.record_id,
        "concept_record_matches": str(payload.get("conceptrecid")) == lock.concept_id,
        "doi_matches": metadata.get("doi") == lock.doi,
        "license_id": license_id,
        "cc_by_4_0": license_id == "cc-by-4.0",
        "archive_entry_present": archive_entry is not None,
        "archive_size_matches": bool(archive_entry and archive_entry.get("size") == lock.archive_size),
        "archive_checksum_matches": bool(
            archive_entry and archive_entry.get("checksum") == f"md5:{lock.archive_md5}"
        ),
        "dcpd_declared_by_record": "direct current potential drop" in description.lower(),
        "global_nodemap_count_declared_797": "797" in description,
        "event_trigger_declared": "every 0.5 mm of crack extension" in description,
    }


def _official_identity_passes(official: dict[str, Any]) -> bool:
    return all(
        official[key] for key in (
            "record_id_matches", "concept_record_matches", "doi_matches",
            "cc_by_4_0", "archive_entry_present", "archive_size_matches",
            "archive_checksum_matches",
        )
    )


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def _validate_manifest(infos: list[zipfile.ZipInfo]) -> dict[str, Any]:
    files = [info for info in infos if not info.is_dir()]
    names = [info.filename for info in files]
    lowered = [name.casefold() for name in names]
    unsafe = [name for name in names if not _safe_member(name)]
    encrypted = [info.filename for info in files if info.flag_bits & 0x1]
    symlinks = [info.filename for info in files if _is_symlink(info)]
    duplicate_exact = len(names) - len(set(names))
    duplicate_casefold = len(lowered) - len(set(lowered))
    dictionary_basenames = Counter(
        PurePosixPath(info.filename).name.lower()
        for info in files if info.filename.lower().endswith(".json")
    )
    mapping = [
        info for info in files
        if PurePosixPath(info.filename).name.lower()
        == "local_2d_microscopic_coordinates_by_nodemaps.csv"
    ]
    failures = []
    if unsafe:
        failures.append("unsafe_member_paths")
    if encrypted:
        failures.append("encrypted_members")
    if symlinks:
        failures.append("symlink_members")
    if duplicate_exact:
        failures.append("duplicate_member_names")
    if duplicate_casefold:
        failures.append("case_colliding_member_names")
    if any(dictionary_basenames[name] != 1 for name in EXACT_DICTIONARIES):
        failures.append("exact_metadata_dictionaries_missing")
    if len(mapping) != 1:
        failures.append("local_mapping_identity_ambiguous")
    return {
        "safe": not failures,
        "failures": failures,
        "file_count": len(files),
        "mapping_infos": mapping,
    }


def _base_result(identity: dict[str, Any], official: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "experiment_id": "S03-E003",
        "protocol_revision": "v1",
        "value_blinded": True,
        "identity": identity,
        "official_metadata": official,
        "blocked_conclusions": [
            "forecast performance", "uncertainty calibration", "phase-field recovery",
            "material-property identification", "cross-specimen generalisation",
            "road transfer", "deployment",
        ],
    }


def _blocked(
    identity: dict[str, Any], official: dict[str, Any], decision: str, reasons: list[str]
) -> dict[str, Any]:
    result = _base_result(identity, official)
    result.update({"decision": decision, "stop_reasons": reasons})
    return result


def audit(
    api_metadata: Path,
    archive_path: Path,
    horizons: tuple[int, ...],
    lock: IdentityLock = IdentityLock(),
) -> dict[str, Any]:
    payload = json.loads(api_metadata.read_text(encoding="utf-8"))
    official = _official_metadata_audit(payload, lock)
    archive_size = archive_path.stat().st_size
    archive_md5 = _md5(archive_path)
    identity = {
        "archive_name_matches": archive_path.name == lock.archive_name,
        "archive_size_bytes": archive_size,
        "expected_size_bytes": lock.archive_size,
        "size_matches": archive_size == lock.archive_size,
        "archive_md5": archive_md5,
        "expected_md5": lock.archive_md5,
        "md5_matches": archive_md5 == lock.archive_md5,
    }
    if not _official_identity_passes(official) or not all(
        (identity["archive_name_matches"], identity["size_matches"], identity["md5_matches"])
    ):
        return _blocked(
            identity, official, "BLOCKED_DATASET_IDENTITY",
            ["official record or archive identity mismatch"],
        )

    with zipfile.ZipFile(archive_path, "r") as archive:
        infos = archive.infolist()
        manifest = _validate_manifest(infos)
        if not manifest["safe"]:
            return _blocked(
                identity, official, "BLOCKED_ARCHIVE_MANIFEST", manifest["failures"]
            )

        global_nodes = [
            info for info in infos
            if "/global_3d_dic/nodemaps/" in f"/{info.filename.lower()}" and not info.is_dir()
        ]
        global_connections = [
            info for info in infos
            if "/global_3d_dic/connections/" in f"/{info.filename.lower()}" and not info.is_dir()
        ]
        local_nodes = [
            info for info in infos
            if "/local_2d_dic/" in f"/{info.filename.lower()}"
            and "/nodemaps/" in f"/{info.filename.lower()}" and not info.is_dir()
        ]
        dictionary_infos = {
            PurePosixPath(info.filename).name.lower(): info for info in infos
            if PurePosixPath(info.filename).name.lower() in EXACT_DICTIONARIES
        }
        dictionary_status = []
        dictionary_schema_valid = True
        for name in sorted(EXACT_DICTIONARIES):
            parsed = _read_json_member(archive, dictionary_infos[name])
            valid = isinstance(parsed, dict) and len(parsed) > 0
            dictionary_schema_valid &= valid
            dictionary_status.append({
                "basename": name,
                "json_type": type(parsed).__name__,
                "top_level_entry_count": len(parsed) if hasattr(parsed, "__len__") else None,
                "nonempty_structured_json": valid,
            })

        node_timesteps = [_timestep_id(info.filename) for info in global_nodes]
        connection_timesteps = [_timestep_id(info.filename) for info in global_connections]
        timestep_identity_valid = (
            None not in node_timesteps
            and None not in connection_timesteps
            and len(node_timesteps) == len(set(node_timesteps))
            and len(connection_timesteps) == len(set(connection_timesteps))
            and set(node_timesteps) == set(connection_timesteps)
        )

        field_presence: Counter[str] = Counter({field: 0 for field in ALIASES})
        field_missing: Counter[str] = Counter({field: 0 for field in ALIASES})
        parsed_by_timestep: dict[int, dict[str, float | None]] = {}
        header_parse_error_count = 0
        invalid_cycle_count = 0
        for info, timestep in zip(global_nodes, node_timesteps):
            try:
                header = _read_header(archive, info)
            except (AuditFormatError, UnicodeError):
                header_parse_error_count += 1
                continue
            for field in ALIASES:
                if header.get(field) is not None:
                    field_presence[field] += 1
                else:
                    field_missing[field] += 1
            cycle = header.get("cycles")
            if cycle is None or cycle < 0 or not cycle.is_integer():
                invalid_cycle_count += 1
                continue
            if timestep is not None:
                parsed_by_timestep[timestep] = header

        ordered_timestep_rows = sorted(parsed_by_timestep.items())
        ordered_cycles = [int(row["cycles"]) for _, row in ordered_timestep_rows]
        cycle_reset_count = sum(
            1 for previous, current in zip(ordered_cycles, ordered_cycles[1:])
            if current < previous
        )
        parsed_cycle_groups: dict[int, list[dict[str, float | None]]] = defaultdict(list)
        for _, header in ordered_timestep_rows:
            parsed_cycle_groups[int(header["cycles"])].append(header)

        target_valid_cycles = []
        inconsistent_target_groups = 0
        missing_target_groups = 0
        for cycle, rows in parsed_cycle_groups.items():
            crack_values = [row.get("cracklength") for row in rows]
            potential_values = [row.get("potential") for row in rows]
            if any(value is None for value in crack_values + potential_values):
                missing_target_groups += 1
                continue
            first = float(crack_values[0])
            if not all(math.isclose(float(value), first, rel_tol=1e-9, abs_tol=1e-9)
                       for value in crack_values[1:]):
                inconsistent_target_groups += 1
                continue
            target_valid_cycles.append(float(cycle))

        mapping_info = manifest["mapping_infos"][0]
        try:
            local_mapping = _read_local_mapping(archive, mapping_info)
        except AuditFormatError as exc:
            return _blocked(
                identity, official, "BLOCKED_DATASET_CAPABILITY",
                [f"local_mapping_format:{type(exc).__name__}"],
            )
        mappings: dict[str, float] = local_mapping.pop("mappings")
        local_basenames = [PurePosixPath(info.filename).name for info in local_nodes]
        local_case_unique = len(local_basenames) == len(set(name.casefold() for name in local_basenames))
        local_set = set(local_basenames)
        mapped_set = set(mappings)
        unmapped_local_files = local_set - mapped_set
        orphan_mapping_rows = mapped_set - local_set
        local_header_cycle_conflicts = 0
        local_header_parse_errors = 0
        for info in local_nodes:
            basename = PurePosixPath(info.filename).name
            try:
                header = _read_header(archive, info)
            except (AuditFormatError, UnicodeError):
                local_header_parse_errors += 1
                continue
            header_cycle = header.get("cycles")
            mapped_cycle = mappings.get(basename)
            if header_cycle is not None and mapped_cycle is not None and header_cycle != mapped_cycle:
                local_header_cycle_conflicts += 1
        local_cycles = set(mappings.values())
        global_cycles = set(float(cycle) for cycle in parsed_cycle_groups)

        cycles = sorted(parsed_cycle_groups)
        cycle_gaps = [float(b - a) for a, b in zip(cycles, cycles[1:]) if b > a]
        frames_per_group = [len(rows) for rows in parsed_cycle_groups.values()]
        force_states_per_group = [
            len({row["force"] for row in rows if row.get("force") is not None})
            for rows in parsed_cycle_groups.values()
        ]
        support = _horizon_support(target_valid_cycles, horizons)

    structure = {
        "total_member_count": len(infos),
        "global_nodemap_count": len(global_nodes),
        "global_connection_count": len(global_connections),
        "local_nodemap_count": len(local_nodes),
        "metadata_dictionaries": dictionary_status,
    }
    chronology = {
        "identity_label": "distinct parsed physical-cycle groups",
        "distinct_parsed_cycle_group_count": len(parsed_cycle_groups),
        "unique_global_timestep_count": len(set(value for value in node_timesteps if value is not None)),
        "header_parse_error_count": header_parse_error_count,
        "invalid_cycle_count": invalid_cycle_count,
        "cycle_reset_count_by_timestep": cycle_reset_count,
        "frames_per_cycle_group": _quantiles([float(value) for value in frames_per_group]),
        "distinct_force_states_per_cycle_group": _quantiles(
            [float(value) for value in force_states_per_group]
        ),
        "positive_cycle_gap_cycles": _quantiles(cycle_gaps),
        "candidate_fixed_horizon_support": support,
        "minimum_information_rule": {
            "calibration_origins": MIN_CALIBRATION_ORIGINS,
            "development_origins": MIN_DEVELOPMENT_ORIGINS,
            "sealed_origins_and_unique_targets": MIN_SEALED_ORIGINS,
            "maximum_sealed_target_reuse": 1,
            "partition_rule": "physical-cycle-span 60/20/20; crossing pairs purged",
        },
    }
    fields = {
        "required_field_present_counts": dict(sorted(field_presence.items())),
        "required_field_missing_counts": dict(sorted(field_missing.items())),
        "target_valid_cycle_group_count": len(target_valid_cycles),
        "missing_direct_target_cycle_group_count": missing_target_groups,
        "inconsistent_same_cycle_target_group_count": inconsistent_target_groups,
        "note": "No per-episode metadata values or DIC field arrays are emitted.",
    }
    synchronization = {
        "local_mapping": local_mapping,
        "unmapped_local_nodemap_count": len(unmapped_local_files),
        "orphan_mapping_row_count": len(orphan_mapping_rows),
        "local_header_cycle_conflict_count": local_header_cycle_conflicts,
        "local_header_parse_error_count": local_header_parse_errors,
        "global_local_cycle_overlap_count": len(global_cycles & local_cycles),
        "local_cycles_absent_from_global_count": len(local_cycles - global_cycles),
    }
    required_headers_complete = bool(global_nodes) and all(
        field_presence[field] + field_missing[field] == len(global_nodes)
        and field_missing[field] == 0
        for field in ALIASES
    )
    capability_checks = {
        "official_identity": _official_identity_passes(official),
        "archive_identity": identity["size_matches"] and identity["md5_matches"],
        "safe_unique_manifest": manifest["safe"],
        "documented_global_assets": (
            len(global_nodes) == lock.expected_global_nodemaps
            and len(global_connections) == lock.expected_global_connections
        ),
        "dictionary_schemas": dictionary_schema_valid,
        "timestep_and_connection_identity": timestep_identity_valid,
        "global_header_parsing": header_parse_error_count == 0,
        "integer_nonnegative_cycles": invalid_cycle_count == 0,
        "monotone_cycle_counter_by_timestep": cycle_reset_count == 0,
        "required_headers_complete": required_headers_complete,
        "direct_target_method_declared": official["dcpd_declared_by_record"],
        "direct_targets_consistent": (
            missing_target_groups == 0 and inconsistent_target_groups == 0
            and len(target_valid_cycles) == len(parsed_cycle_groups) > 0
        ),
        "local_file_identity_unique": local_case_unique,
        "local_mapping_rows_valid": all(
            local_mapping[key] == 0 for key in (
                "missing_or_invalid_cycle_rows", "malformed_row_count",
                "duplicate_file_row_count",
            )
        ),
        "local_mapping_file_join_complete": not unmapped_local_files and not orphan_mapping_rows,
        "local_header_mapping_consistent": local_header_cycle_conflicts == 0,
        "local_header_parsing": local_header_parse_errors == 0,
        "global_local_synchronization": (
            bool(global_cycles & local_cycles) and not (local_cycles - global_cycles)
        ),
    }
    capability_failures = [name for name, passed in capability_checks.items() if not passed]
    resolution_passes = any(item["meets_minimum_information"] for item in support)
    if capability_failures:
        decision = "BLOCKED_DATASET_CAPABILITY"
        stop_reasons = capability_failures
    elif not resolution_passes:
        decision = "BLOCKED_EVALUATION_RESOLUTION"
        stop_reasons = ["no candidate horizon meets the frozen minimum-information rule"]
    else:
        decision = "QUALIFIED_FOR_FORECAST_PROTOCOL_DESIGN"
        stop_reasons = []
    result = _base_result(identity, official)
    result.update({
        "archive_structure": structure,
        "chronology": chronology,
        "header_schema_and_missingness": fields,
        "synchronization": synchronization,
        "strict_checks": capability_checks,
        "decision": decision,
        "stop_reasons": stop_reasons,
    })
    _assert_redacted_output(result)
    return result


def _assert_redacted_output(result: dict[str, Any]) -> None:
    rendered = json.dumps(result, sort_keys=True).lower()
    forbidden_keys = ("per_episode", "cracklength_values", "field_array", "raw_columns")
    if any(key in rendered for key in forbidden_keys):
        raise AuditFormatError("output firewall rejected a forbidden result key")


def _validated_output_path(
    output: Path, allowed_root: Path, inputs: tuple[Path, ...]
) -> Path:
    root = allowed_root.resolve()
    target = output.resolve(strict=False)
    if target != root and root not in target.parents:
        raise AuditFormatError("output must be inside the declared audit root")
    for source in inputs:
        resolved_source = source.resolve()
        if target == resolved_source:
            raise AuditFormatError("output collides with immutable input")
        if output.exists() and source.exists() and os.path.samefile(output, source):
            raise AuditFormatError("output aliases immutable input")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.parent.resolve() != target.parent:
        raise AuditFormatError("output parent contains a symlink alias")
    return target


def _atomic_json_write(path: Path, result: dict[str, Any]) -> None:
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-metadata", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allowed-output-root", type=Path, required=True)
    parser.add_argument(
        "--candidate-horizons",
        type=int,
        nargs="+",
        default=list(DEFAULT_HORIZONS),
        help="Physical-cycle horizons used only for support counts, not model selection.",
    )
    args = parser.parse_args()
    output = _validated_output_path(
        args.output, args.allowed_output_root, (args.api_metadata, args.archive)
    )
    result = audit(args.api_metadata, args.archive, tuple(args.candidate_horizons))
    _atomic_json_write(output, result)
    print(json.dumps({
        "decision": result["decision"],
        "stop_reasons": result.get("stop_reasons", []),
        "output": str(output),
    }, sort_keys=True))
    return 0 if result["decision"] == "QUALIFIED_FOR_FORECAST_PROTOCOL_DESIGN" else 2


if __name__ == "__main__":
    sys.exit(main())
