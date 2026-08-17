#!/usr/bin/env python3
"""Create compact, hash-bound evidence from an immutable D-T2 run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
from pathlib import Path


class CompactEvidenceError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_bytes_create_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def write_json_create_new(path: Path, value: object) -> None:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    write_bytes_create_new(path, payload)


def build_compact_package(run_root: Path, analysis_root: Path,
                          destination: Path) -> dict[str, object]:
    run = run_root.resolve()
    analysis = analysis_root.resolve()
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(destination)
    destination.mkdir(parents=True, exist_ok=False)

    result_path = run / "output" / "RUN_RESULT.json"
    trace_path = run / "output" / "qualification" / "C5_STAGGER_TRACE.csv"
    iterate_path = run / "output" / "qualification" / "DT2_C5_ITERATES.mat"
    mesh_path = run / "output" / "mesh_geometry.mat"
    required = [result_path, trace_path, iterate_path, mesh_path]
    if any(not path.is_file() for path in required):
        raise CompactEvidenceError("immutable D-T2 source evidence is incomplete")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("status") != "failed" or result.get("case_id") != "T2_material_state":
        raise CompactEvidenceError("D-T2 terminal result is not the sealed T2 c5/s4 failure")
    with trace_path.open(newline="", encoding="utf-8") as stream:
        trace_rows = sum(1 for _ in csv.DictReader(stream))
    if trace_rows != 1000:
        raise CompactEvidenceError(f"D-T2 trace must contain exactly 1000 rows, found {trace_rows}")
    shards = sorted((run / "output" / "substeps").glob("cycle_*.mat"))
    if [path.name for path in shards] != [f"cycle_{cycle:04d}.mat" for cycle in range(1, 5)]:
        raise CompactEvidenceError("D-T2 must contain exactly four completed cycle shards")

    summary_path = analysis / "diagnostic_summary.json"
    tables = [analysis / name for name in (
        "iterate_geometry.csv", "process_zone.csv", "fatigue_phase_objective.csv")]
    if not summary_path.is_file() or any(not path.is_file() for path in tables):
        raise CompactEvidenceError("offline analysis evidence is incomplete")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("classification") != "NONPERIODIC_NONCONTRACTION" or summary.get("completed_rows") != 1000:
        raise CompactEvidenceError("offline analysis classification or row closure is invalid")

    for source in [summary_path, *tables]:
        shutil.copyfile(source, destination / source.name)
    source_files = [result_path, trace_path, iterate_path, mesh_path, *shards]
    bindings = {
        path.name: {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size,
                    "copied": False}
        for path in source_files
    }
    write_json_create_new(destination / "SOURCE_BINDINGS.json", bindings)
    decision = (
        "# D-T2 compact evidence decision\n\n"
        "Classification: `NONPERIODIC_NONCONTRACTION`.\n\n"
        "The original T2 remains `FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE_AT_C5_S4`. "
        "This package does not copy or modify the immutable D-T2 MAT files. "
        "`tot_en` is auxiliary only.\n"
    )
    write_bytes_create_new(destination / "DECISION.md", decision.encode("utf-8"))
    package = {
        "schema_version": "toy_road_dt2_compact_evidence_v1",
        "classification": summary["classification"],
        "completed_rows": 1000,
        "completed_cycle_shards": 4,
        "original_t2_status": "FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE_AT_C5_S4",
        "source_bindings": bindings,
        "tot_en_role": "auxiliary_only",
    }
    write_json_create_new(destination / "PACKAGE_MANIFEST.json", package)
    inventory_paths = sorted(path for path in destination.iterdir() if path.is_file())
    inventory = "".join(f"{sha256(path)}  {path.name}\n" for path in inventory_paths)
    write_bytes_create_new(destination / "SHA256SUMS.txt", inventory.encode("ascii"))
    return package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    parser.add_argument("analysis_root", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(build_compact_package(args.run_root, args.analysis_root, args.destination), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
