#!/usr/bin/env python3
"""Value-blinded capability audit for Zenodo record 11945905.

The audit reads ZIP metadata and nodemap headers only.  It never loads DIC field
arrays and never writes per-episode crack-length, force, displacement, strain,
or potential values to its output.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


EXPECTED_RECORD_ID = 11945905
EXPECTED_CONCEPT_ID = "11945904"
EXPECTED_ARCHIVE_NAME = "multiscale_digital_image_correlation.zip"
EXPECTED_SIZE = 1_248_078_255
EXPECTED_MD5 = "e671b804e29401e70043bc1e17f66dd1"
DEFAULT_HORIZONS = (1_000, 2_000, 5_000, 10_000, 20_000, 50_000,
                    100_000, 200_000, 500_000, 1_000_000)


ALIASES = {
    "cycles": ("cycles", "cycle", "numberofcycles", "loadcycles"),
    "force": ("force", "kraft"),
    "displacement": ("displacement", "actuatordisplacement", "weg"),
    "potential": ("potential", "voltage", "dcpdpotential"),
    "cracklength": ("cracklength", "cracklenght", "risslaenge", "risslange"),
    "dms_1": ("dms1", "backfacestrain1", "strainbackface1"),
    "dms_2": ("dms2", "backfacestrain2", "strainbackface2"),
}


def _normalise_key(value: str) -> str:
    value = value.lower().replace("ä", "a").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", "", value)


def _canonical_key(raw_key: str) -> str | None:
    norm = _normalise_key(raw_key)
    for canonical, aliases in ALIASES.items():
        if any(norm == alias or norm.startswith(alias) for alias in aliases):
            return canonical
    return None


def _first_number(value: str) -> float | None:
    match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", value)
    if not match:
        return None
    parsed = float(match.group(0))
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


def _read_header(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> dict[str, float | None]:
    values: dict[str, float | None] = {}
    with archive.open(info, "r") as raw:
        text = io.TextIOWrapper(raw, encoding="windows-1252", errors="replace")
        for line in text:
            if not line.startswith("#"):
                break
            match = re.match(r"^\s*#\s*([^:#]+?)\s*:\s*(.*?)\s*$", line)
            if not match:
                continue
            canonical = _canonical_key(match.group(1))
            if canonical and canonical not in values:
                values[canonical] = _first_number(match.group(2))
    return values


def _read_json_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> Any:
    with archive.open(info, "r") as raw:
        return json.load(io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace"))


def _read_csv_schema_and_cycles(
    archive: zipfile.ZipFile, info: zipfile.ZipInfo
) -> tuple[list[str], int, int, set[float]]:
    with archive.open(info, "r") as raw:
        decoded = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace")
        sample = decoded.read(8192)
        decoded.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(decoded, dialect=dialect)
        columns = reader.fieldnames or []
        cycle_column = next(
            (column for column in columns if _canonical_key(column) == "cycles"), None
        )
        rows = 0
        missing_cycle = 0
        cycles: set[float] = set()
        for row in reader:
            rows += 1
            if cycle_column is None:
                missing_cycle += 1
                continue
            value = _first_number(row.get(cycle_column, ""))
            if value is None:
                missing_cycle += 1
            else:
                cycles.add(value)
        return columns, rows, missing_cycle, cycles


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


def _horizon_support(cycles: list[float], horizons: Iterable[int]) -> list[dict[str, Any]]:
    ordered = sorted(set(cycles))
    results = []
    for horizon in horizons:
        tolerance = max(100.0, 0.05 * horizon)
        eligible_origins = 0
        pair_count = 0
        for index, origin in enumerate(ordered[:-1]):
            matches = [
                target for target in ordered[index + 1 :]
                if abs((target - origin) - horizon) <= tolerance
            ]
            if matches:
                eligible_origins += 1
                pair_count += len(matches)
        results.append({
            "horizon_cycles": horizon,
            "tolerance_cycles": tolerance,
            "eligible_distinct_origins": eligible_origins,
            "eligible_origin_target_pairs": pair_count,
        })
    return results


def _official_metadata_audit(payload: dict[str, Any]) -> dict[str, Any]:
    files = payload.get("files") or []
    archive_entry = next((item for item in files if item.get("key") == EXPECTED_ARCHIVE_NAME), None)
    metadata = payload.get("metadata") or {}
    description = metadata.get("description") or ""
    license_field = metadata.get("license") or {}
    if isinstance(license_field, dict):
        license_id = license_field.get("id")
    else:
        license_id = license_field
    return {
        "record_id_matches": payload.get("id") == EXPECTED_RECORD_ID,
        "concept_record_matches": str(payload.get("conceptrecid")) == EXPECTED_CONCEPT_ID,
        "doi_matches": metadata.get("doi") == "10.5281/zenodo.11945905",
        "license_id": license_id,
        "cc_by_4_0": license_id == "cc-by-4.0",
        "archive_entry_present": archive_entry is not None,
        "archive_size_matches": bool(archive_entry and archive_entry.get("size") == EXPECTED_SIZE),
        "archive_checksum_matches": bool(
            archive_entry and archive_entry.get("checksum") == f"md5:{EXPECTED_MD5}"
        ),
        "dcpd_declared_by_record": "direct current potential drop" in description.lower(),
        "global_nodemap_count_declared_797": "797" in description,
        "event_trigger_declared": "every 0.5 mm of crack extension" in description,
    }


def audit(api_metadata: Path, archive_path: Path, horizons: tuple[int, ...]) -> dict[str, Any]:
    payload = json.loads(api_metadata.read_text(encoding="utf-8"))
    official = _official_metadata_audit(payload)

    archive_size = archive_path.stat().st_size
    archive_md5 = _md5(archive_path)
    identity = {
        "archive_name": archive_path.name,
        "archive_size_bytes": archive_size,
        "expected_size_bytes": EXPECTED_SIZE,
        "size_matches": archive_size == EXPECTED_SIZE,
        "archive_md5": archive_md5,
        "expected_md5": EXPECTED_MD5,
        "md5_matches": archive_md5 == EXPECTED_MD5,
    }
    if not all((identity["size_matches"], identity["md5_matches"])):
        return {
            "schema_version": 1,
            "experiment_id": "S03-E003",
            "protocol_revision": "v1",
            "value_blinded": True,
            "identity": identity,
            "official_metadata": official,
            "decision": "BLOCKED_DATASET_IDENTITY",
            "stop_reasons": ["archive size or checksum mismatch"],
        }

    with zipfile.ZipFile(archive_path, "r") as archive:
        infos = archive.infolist()
        unsafe = [info.filename for info in infos if not _safe_member(info.filename)]
        names_lower = {info.filename.lower(): info for info in infos}
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
        mapping_infos = [
            info for info in infos
            if info.filename.lower().endswith("local_2d_microscopic_coordinates_by_nodemaps.csv")
        ]
        dictionary_infos = [
            info for info in infos
            if info.filename.lower().endswith("_metadata_dictionary.json")
        ]

        dictionary_status = []
        for info in dictionary_infos:
            parsed = _read_json_member(archive, info)
            dictionary_status.append({
                "basename": PurePosixPath(info.filename).name,
                "json_type": type(parsed).__name__,
                "top_level_entry_count": len(parsed) if hasattr(parsed, "__len__") else None,
            })

        field_presence: Counter[str] = Counter()
        field_missing: Counter[str] = Counter()
        episodes: dict[float, list[dict[str, float | None]]] = defaultdict(list)
        unparsed_cycle = 0
        for info in global_nodes:
            header = _read_header(archive, info)
            for field in ALIASES:
                if field in header and header[field] is not None:
                    field_presence[field] += 1
                else:
                    field_missing[field] += 1
            cycle = header.get("cycles")
            if cycle is None:
                unparsed_cycle += 1
            else:
                episodes[cycle].append(header)

        cycles = sorted(episodes)
        cycle_gaps = [b - a for a, b in zip(cycles, cycles[1:]) if b > a]
        frames_per_episode = [len(rows) for rows in episodes.values()]
        force_states_per_episode = [
            len({row["force"] for row in rows if row.get("force") is not None})
            for rows in episodes.values()
        ]
        cracklength_inconsistency_episodes = sum(
            1 for rows in episodes.values()
            if len({row["cracklength"] for row in rows if row.get("cracklength") is not None}) > 1
        )

        mapping_summary: dict[str, Any]
        local_cycles: set[float] = set()
        if len(mapping_infos) == 1:
            columns, rows, missing_cycle, local_cycles = _read_csv_schema_and_cycles(
                archive, mapping_infos[0]
            )
            mapping_summary = {
                "mapping_file_count": 1,
                "columns": columns,
                "row_count": rows,
                "missing_cycle_rows": missing_cycle,
                "unique_mapped_cycle_count": len(local_cycles),
            }
        else:
            mapping_summary = {
                "mapping_file_count": len(mapping_infos),
                "columns": [],
                "row_count": 0,
                "missing_cycle_rows": None,
                "unique_mapped_cycle_count": 0,
            }

        support = _horizon_support(cycles, horizons)
        structure = {
            "total_member_count": len(infos),
            "unsafe_member_count": len(unsafe),
            "global_nodemap_count": len(global_nodes),
            "global_connection_count": len(global_connections),
            "local_nodemap_count": len(local_nodes),
            "metadata_dictionary_count": len(dictionary_infos),
            "metadata_dictionaries": dictionary_status,
        }
        chronology = {
            "distinct_global_acquisition_episode_count": len(episodes),
            "unparsed_global_cycle_header_count": unparsed_cycle,
            "frames_per_episode": _quantiles([float(value) for value in frames_per_episode]),
            "distinct_force_states_per_episode": _quantiles(
                [float(value) for value in force_states_per_episode]
            ),
            "positive_cycle_gap_cycles": _quantiles(cycle_gaps),
            "candidate_fixed_horizon_support": support,
        }
        fields = {
            "required_field_present_counts": dict(sorted(field_presence.items())),
            "required_field_missing_counts": dict(sorted(field_missing.items())),
            "episodes_with_nonidentical_cracklength_across_same_cycle":
                cracklength_inconsistency_episodes,
            "note": "No per-episode metadata values or DIC field arrays are emitted.",
        }
        synchronization = {
            "local_mapping": mapping_summary,
            "global_unique_cycle_count": len(set(cycles)),
            "global_local_cycle_overlap_count": len(set(cycles) & local_cycles),
            "local_cycles_absent_from_global_count": len(local_cycles - set(cycles)),
        }

    strict_checks = {
        "official_identity": all(
            official[key] for key in (
                "record_id_matches", "concept_record_matches", "doi_matches",
                "cc_by_4_0", "archive_entry_present", "archive_size_matches",
                "archive_checksum_matches",
            )
        ),
        "archive_identity": identity["size_matches"] and identity["md5_matches"],
        "safe_paths": structure["unsafe_member_count"] == 0,
        "documented_global_assets": (
            structure["global_nodemap_count"] == 797
            and structure["global_connection_count"] == 797
        ),
        "metadata_dictionaries_present": structure["metadata_dictionary_count"] >= 2,
        "global_cycle_mapping_complete": chronology["unparsed_global_cycle_header_count"] == 0,
        "required_headers_complete": all(
            fields["required_field_missing_counts"].get(field, len(global_nodes)) == 0
            for field in ALIASES
        ),
        "single_local_mapping_file": mapping_summary["mapping_file_count"] == 1,
        "local_cycle_mapping_complete": mapping_summary["missing_cycle_rows"] == 0,
        "direct_target_method_declared": official["dcpd_declared_by_record"],
        "nonzero_fixed_horizon_support": any(
            item["eligible_distinct_origins"] > 0 for item in support
        ),
        "value_blind_output_contract": True,
    }
    stop_reasons = [name for name, passed in strict_checks.items() if not passed]
    decision = (
        "QUALIFIED_FOR_FORECAST_PROTOCOL_DESIGN"
        if not stop_reasons else "BLOCKED_DATASET_CAPABILITY"
    )
    return {
        "schema_version": 1,
        "experiment_id": "S03-E003",
        "protocol_revision": "v1",
        "value_blinded": True,
        "identity": identity,
        "official_metadata": official,
        "archive_structure": structure,
        "chronology": chronology,
        "header_schema_and_missingness": fields,
        "synchronization": synchronization,
        "strict_checks": strict_checks,
        "decision": decision,
        "stop_reasons": stop_reasons,
        "blocked_conclusions": [
            "forecast performance", "uncertainty calibration", "phase-field recovery",
            "material-property identification", "cross-specimen generalisation",
            "road transfer", "deployment",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-metadata", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--candidate-horizons",
        type=int,
        nargs="+",
        default=list(DEFAULT_HORIZONS),
        help="Physical-cycle horizons used only for support counts, not model selection.",
    )
    args = parser.parse_args()
    result = audit(args.api_metadata, args.archive, tuple(args.candidate_horizons))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": result["decision"],
        "stop_reasons": result.get("stop_reasons", []),
        "output": str(args.output),
    }, sort_keys=True))
    return 0 if result["decision"] == "QUALIFIED_FOR_FORECAST_PROTOCOL_DESIGN" else 2


if __name__ == "__main__":
    sys.exit(main())

