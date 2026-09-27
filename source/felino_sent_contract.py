"""Frozen contract and reference checks for the Felino SENT reproduction."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


EXPECTED_REFERENCE_COLUMNS = (
    "time", "av_disp_y", "crack_area", "cycle_current", "dt",
    "max_accumulate", "max_current", "max_d", "run_time", "top_stress_yy",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_contract(path: Path) -> dict:
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("contract_version") != 1:
        raise ValueError("unsupported Felino SENT contract version")
    return contract


def validate_reference(contract: dict, *, disp_input: Path, damage_input: Path,
                       mesh: Path, reference_csv: Path) -> dict:
    paths = {
        "disp_input_sha256": disp_input,
        "damage_input_sha256": damage_input,
        "mesh_sha256": mesh,
        "reference_csv_sha256": reference_csv,
    }
    hashes = {}
    for key, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = sha256_file(path)
        expected = contract["identity"][key]
        if observed != expected:
            raise ValueError(f"{key} mismatch: expected {expected}, got {observed}")
        hashes[key] = observed

    with reference_csv.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != EXPECTED_REFERENCE_COLUMNS:
            raise ValueError(f"unexpected reference columns: {reader.fieldnames}")
        rows = list(reader)
    expected_rows = int(contract["reference"]["csv_rows_including_state0"])
    if len(rows) != expected_rows:
        raise ValueError(f"expected {expected_rows} reference rows, got {len(rows)}")
    cycles = [float(row["cycle_current"]) for row in rows]
    if cycles[0] != 0 or cycles[-1] != contract["fatigue"]["total_cycles"]:
        raise ValueError("reference cycle endpoints do not match contract")
    jump = int(contract["fatigue"]["cycle_jump"])
    if any(abs((b - a) - jump) > 1e-6 for a, b in zip(cycles, cycles[1:])):
        raise ValueError("reference cycle cadence is not the frozen cycle jump")
    return {
        "hashes": hashes,
        "rows": len(rows),
        "cycle_min": cycles[0],
        "cycle_max": cycles[-1],
        "final_crack_area": float(rows[-1]["crack_area"]),
        "final_max_d": float(rows[-1]["max_d"]),
        "final_alpha_bar_max": float(rows[-1]["max_accumulate"]),
    }


def discover_project_root(start: Path) -> Path:
    for parent in (start, *start.parents):
        if (parent / "local_archive").is_dir() and (parent / "upload code").is_dir():
            return parent
    raise FileNotFoundError("could not discover project root containing local_archive")
