#!/usr/bin/env python3
"""Build the one permitted S09-E007 U0.125 complete-trajectory packet."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np

try:
    from .build_s09_equilibrium_packet import q4_lumped_area, read_static, require_matlab_string, scalar, verify_boundary
except ImportError:  # direct script execution
    from build_s09_equilibrium_packet import q4_lumped_area, read_static, require_matlab_string, scalar, verify_boundary

EXPECTED_CYCLES = tuple(range(1, 74))
EXPECTED_SOURCE_ROOT = r"C:\q4runs\hard5_new_runs_u0115_u0125_20260827_v1\hard5_u0125_stage0b"
EXPECTED_SOURCE_COMMIT = "862992a60edc7f59335365beacb5c71fc8592a7a"
EXPECTED_STATIC_SHA256 = "b79a36298eabec363fb7a53fb0590db46eb949b05c05dbffb9cb5a8bc0e4b40e"
EXPECTED_METADATA_HASHES = {
    "state_index.csv": "3d815b4abc8e4d215b2d6ce747bbc728729d9ed41e7ff7dfe29dbb77695ad1f1",
    "run_summary.json": "e454fb5c46482f9a60e82ee4fb3f2988440b34544c5f03498ac9a55607e37eb2",
    "validation_receipt.json": "24a3adf4e2ae6566791e824ca3fa1dc14e3f5b04768761abbb460cd4060cd190",
    "field_inventory.csv": "323c1924b5ece2a1eaebd622bb279658c272410ca776f32cc9b0c297f7d43a17",
    "source_receipt.json": "273610cf49baae708a0be0006111c90b5ff70dc06d39f465bf88eb1fb3a39cfc",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        return
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def load_and_validate_lock(path: Path) -> dict:
    lock = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "experiment_id": "S09-E007",
        "protocol_revision": "v2-frozen-beta025-u0125-holdout",
        "source_root": EXPECTED_SOURCE_ROOT,
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "producer": "CITPC12",
        "source_dirty": False,
        "sealed": True,
    }
    for key, expected in required.items():
        if lock.get(key) != expected:
            raise ValueError(f"data lock mismatch: {key}")
    membership = lock.get("membership", {})
    observed_membership = (
        membership.get("first_cycle"), membership.get("authoritative_final_cycle"),
        tuple(membership.get("cycles", [])), membership.get("substep"), membership.get("timing"),
    )
    if observed_membership != (1, 73, EXPECTED_CYCLES, 4, "post_history_commit"):
        raise ValueError("data lock membership/timing mismatch")
    if lock.get("source_metadata") != {
        "state_index_sha256": EXPECTED_METADATA_HASHES["state_index.csv"],
        "run_summary_sha256": EXPECTED_METADATA_HASHES["run_summary.json"],
        "validation_receipt_sha256": EXPECTED_METADATA_HASHES["validation_receipt.json"],
        "field_inventory_sha256": EXPECTED_METADATA_HASHES["field_inventory.csv"],
        "source_receipt_sha256": EXPECTED_METADATA_HASHES["source_receipt.json"],
        "static_sha256": EXPECTED_STATIC_SHA256,
    }:
        raise ValueError("data lock source metadata mismatch")
    states = lock.get("states", [])
    if len(states) != 73 or tuple(item.get("cycle") for item in states) != EXPECTED_CYCLES:
        raise ValueError("data lock state inventory mismatch")
    return lock


def locked_rows(path: Path, lock: dict) -> list[dict]:
    if sha256(path) != EXPECTED_METADATA_HASHES["state_index.csv"]:
        raise ValueError("state_index identity mismatch")
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    selected = [row for row in rows if row["substep"] == "4"]
    if tuple(int(row["cycle"]) for row in selected) != EXPECTED_CYCLES:
        raise ValueError("required c1..c73 s4 membership is not exact and contiguous")
    if len({row["state_key"] for row in selected}) != 73:
        raise ValueError("duplicate s4 state identity")
    locked_states = {item["cycle"]: item for item in lock["states"]}
    for cycle, row in zip(EXPECTED_CYCLES, selected):
        expected_key = f"c{cycle:04d}_s04"
        locked = locked_states[cycle]
        checks = (
            row["state_key"] == expected_key,
            row["source_state_key"] == expected_key,
            row["payload_file"] == f"states/{expected_key}.mat",
            row["timing"] == "post_history_commit",
            row["is_alias"] == "0",
            row["converged"] == "1",
            row["payload_sha256"] == locked["payload_sha256"],
            row["payload_file"] == locked["payload_file"],
            float(row["imposed_displacement"]) == float(locked["imposed_displacement"]),
        )
        if not all(checks):
            raise ValueError(f"locked row mismatch for cycle {cycle}")
    return selected


def validate_metadata(metadata_dir: Path) -> None:
    for name, expected in EXPECTED_METADATA_HASHES.items():
        path = metadata_dir / name
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"source metadata identity mismatch: {name}")
    summary = json.loads((metadata_dir / "run_summary.json").read_text(encoding="utf-8-sig"))
    validation = json.loads((metadata_dir / "validation_receipt.json").read_text(encoding="utf-8-sig"))
    source = json.loads((metadata_dir / "source_receipt.json").read_text(encoding="utf-8-sig"))
    if not summary.get("sealed") or summary.get("cycle_count") != 73 or summary.get("provenance", {}).get("source_commit") != EXPECTED_SOURCE_COMMIT:
        raise ValueError("run summary does not establish sealed authoritative c73 stop")
    if validation.get("passed") is not True or tuple(validation.get("cycles", [])) != EXPECTED_CYCLES:
        raise ValueError("producer validation receipt mismatch")
    if source.get("source_commit") != EXPECTED_SOURCE_COMMIT or source.get("source_dirty") is not False:
        raise ValueError("source receipt mismatch")


def preflight(args, rows: list[dict], lock: dict) -> dict:
    if args.source_root != EXPECTED_SOURCE_ROOT:
        raise ValueError("source root is not the frozen CITPC12 archive")
    if args.out.suffix != ".npz":
        raise ValueError("--out must end in .npz")
    if sha256(args.static) != EXPECTED_STATIC_SHA256:
        raise ValueError("static identity mismatch")
    validate_metadata(args.metadata_dir)
    inventory = []
    for row in rows:
        path = args.states / Path(row["payload_file"]).name
        if not path.is_file():
            raise FileNotFoundError(f"missing required payload: {path.name}")
        actual = sha256(path)
        if actual != row["payload_sha256"]:
            raise ValueError(f"payload preflight hash mismatch: {path.name}")
        inventory.append({"cycle": int(row["cycle"]), "file": path.name, "sha256": actual})
    return {
        "experiment_id": "S09-E007",
        "protocol_revision": lock["protocol_revision"],
        "source_root": EXPECTED_SOURCE_ROOT,
        "source_commit": EXPECTED_SOURCE_COMMIT,
        "static_sha256": EXPECTED_STATIC_SHA256,
        "state_index_sha256": EXPECTED_METADATA_HASHES["state_index.csv"],
        "metadata_sha256": EXPECTED_METADATA_HASHES,
        "authoritative_final_cycle": 73,
        "inventory": inventory,
        "scientific_arrays_decoded": False,
    }


def exact_scalar(dataset, expected: float, label: str) -> float:
    value = scalar(dataset)
    if not np.isfinite(value) or value != expected:
        raise ValueError(f"exact scalar mismatch: {label}")
    return value


def read_state(path: Path, row: dict, xy: np.ndarray, expected_nodes: int = 86756):
    actual_hash = sha256(path)
    if actual_hash != row["payload_sha256"]:
        raise ValueError(f"payload immediate hash mismatch: {path.name}")
    with h5py.File(path, "r") as handle:
        damage = np.asarray(handle["d_node"], dtype=np.float64).reshape(-1)
        displacement = np.asarray(handle["u_node"], dtype=np.float64).T
        exact_scalar(handle["state_metadata/cycle"], float(row["cycle"]), "cycle")
        exact_scalar(handle["state_metadata/substep"], 4.0, "substep")
        load = scalar(handle["state_metadata/imposed_displacement"])
        exact_scalar(handle["state_metadata/producer_metadata/converged"], 1.0, "converged")
        require_matlab_string(handle["state_metadata/timing"], "holdout timing")
    if damage.shape != (expected_nodes,) or displacement.shape != (expected_nodes, 2):
        raise ValueError(f"decoded field shape mismatch: {path.name}")
    if not np.isfinite(damage).all() or not np.isfinite(displacement).all() or not np.isfinite(load):
        raise ValueError(f"nonfinite source field: {path.name}")
    if load != float(row["imposed_displacement"]):
        raise ValueError(f"imposed displacement mismatch: {path.name}")
    verify_boundary(xy, displacement, load)
    return damage, displacement, load, actual_hash


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--static", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--states", type=Path, required=True)
    parser.add_argument("--metadata-dir", type=Path, required=True)
    parser.add_argument("--data-lock", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    args = parser.parse_args()
    manifest_path = args.out.with_suffix(".manifest.json")
    receipt_path = args.out.with_suffix(".unsealing.json")
    preflight_path = args.out.with_suffix(".preflight.json")
    canonical_lock = Path(__file__).resolve().parents[1] / "docs/research/S09/S09-E007/data_lock.json"
    attempt_marker = canonical_lock.parent / ".packet_build_attempt.json"
    if args.data_lock.resolve() != canonical_lock.resolve():
        raise ValueError("builder requires the reviewed canonical data lock")
    if any(path.exists() for path in (args.out, manifest_path, receipt_path, preflight_path)):
        raise FileExistsError("packet evidence path already exists")
    if attempt_marker.exists():
        raise FileExistsError("the one permitted E007 packet-build attempt is already claimed")

    lock = load_and_validate_lock(args.data_lock)
    rows = locked_rows(args.index, lock)
    inventory = preflight(args, rows, lock)
    atomic_json(preflight_path, inventory, exclusive=True)
    build_attempt = {
        "experiment_id": "S09-E007", "event": "single_packet_build_attempt",
        "status": "claimed", "output": str(args.out.resolve()), "scientific_read_started": False,
    }
    atomic_json(attempt_marker, build_attempt, exclusive=True)
    receipt = {
        "experiment_id": "S09-E007",
        "event": "permanent_u0125_scientific_unsealing",
        "source_root": EXPECTED_SOURCE_ROOT,
        "state_index_sha256": EXPECTED_METADATA_HASHES["state_index.csv"],
        "cycles": list(EXPECTED_CYCLES),
        "status": "preflight_complete",
        "scientific_read_started": False,
        "validated_states": 0,
    }
    atomic_json(receipt_path, receipt, exclusive=True)
    receipt.update(
        status="scientific_read_started",
        scientific_read_started=True,
        scientific_read_started_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    atomic_json(receipt_path, receipt)
    build_attempt.update(status="scientific_read_started", scientific_read_started=True,
                         scientific_read_started_at_utc=receipt["scientific_read_started_at_utc"])
    atomic_json(attempt_marker, build_attempt)

    states = []
    try:
        xy, conn, young, nu, eta = read_static(args.static)
        area = q4_lumped_area(xy, conn)
        for row in rows:
            path = args.states / Path(row["payload_file"]).name
            values = read_state(path, row, xy)
            states.append(values[:3])
            receipt["validated_states"] = len(states)
            receipt["last_validated_cycle"] = int(row["cycle"])
            atomic_json(receipt_path, receipt)
        with args.out.open("xb") as stream:
            np.savez_compressed(
                stream, xy=xy, conn=conn, lumped_area=area,
                holdout_d=np.stack([item[0] for item in states]),
                holdout_u=np.stack([item[1] for item in states]),
                holdout_load=np.asarray([item[2] for item in states]),
                holdout_cycle=np.asarray(EXPECTED_CYCLES),
                young=np.asarray(young), nu=np.asarray(nu), eta=np.asarray(eta),
            )
        manifest = {
            **inventory,
            "packet_sha256": sha256(args.out),
            "nodes": len(xy), "elements": len(conn), "area": float(area.sum()),
            "material": {"young": young, "nu": nu, "eta": eta},
            "scientific_arrays_decoded": True,
            "source_validation": "passed_all_73",
            "exposure_limit": "non-blind post-selection trajectory; exposure_unknown_not_cleared",
        }
        atomic_json(manifest_path, manifest, exclusive=True)
        receipt.update(status="succeeded", packet_sha256=manifest["packet_sha256"])
        build_attempt.update(status="succeeded", packet_sha256=manifest["packet_sha256"])
    except BaseException as error:
        receipt.update(status="failed", error=repr(error))
        build_attempt.update(status="failed", error=repr(error), validated_states=len(states))
        raise
    finally:
        atomic_json(receipt_path, receipt)
        atomic_json(attempt_marker, build_attempt)


if __name__ == "__main__":
    main()
