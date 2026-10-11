#!/usr/bin/env python3
"""Build the frozen S09-E007 U0.125 complete-trajectory packet."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np

try:
    from .build_s09_equilibrium_packet import q4_lumped_area, read_static, require_matlab_string, scalar, verify_boundary
except ImportError:  # direct script execution
    from build_s09_equilibrium_packet import q4_lumped_area, read_static, require_matlab_string, scalar, verify_boundary

EXPECTED_CYCLES = tuple(range(1, 74))
EXPECTED_INDEX_SHA256 = "3d815b4abc8e4d215b2d6ce747bbc728729d9ed41e7ff7dfe29dbb77695ad1f1"
EXPECTED_SOURCE_COMMIT = "862992a60edc7f59335365beacb5c71fc8592a7a"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def locked_rows(path: Path) -> list[dict]:
    if sha256(path) != EXPECTED_INDEX_SHA256:
        raise ValueError("state_index identity mismatch")
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    selected = [row for row in rows if int(row["substep"]) == 4]
    cycles = tuple(int(row["cycle"]) for row in selected)
    if cycles != EXPECTED_CYCLES:
        raise ValueError("required c1..c73 s4 membership is not exact and contiguous")
    if len({row["state_key"] for row in selected}) != len(EXPECTED_CYCLES):
        raise ValueError("duplicate s4 state identity")
    for cycle, row in zip(EXPECTED_CYCLES, selected):
        expected_key = f"c{cycle:04d}_s04"
        if row["state_key"] != expected_key or row["source_state_key"] != expected_key:
            raise ValueError(f"state identity mismatch for cycle {cycle}")
        if row["payload_file"] != f"states/{expected_key}.mat":
            raise ValueError(f"payload path mismatch for cycle {cycle}")
        if row["timing"] != "post_history_commit" or row["is_alias"] != "0":
            raise ValueError(f"state timing/alias mismatch for cycle {cycle}")
        if row["converged"] != "1" or len(row["payload_sha256"]) != 64:
            raise ValueError(f"producer qualification mismatch for cycle {cycle}")
    return selected


def read_state(path: Path, row: dict, xy: np.ndarray, expected_nodes: int = 86756):
    actual_hash = sha256(path)
    if actual_hash != row["payload_sha256"]:
        raise ValueError(f"payload hash mismatch: {path.name}")
    with h5py.File(path, "r") as handle:
        damage = np.asarray(handle["d_node"], dtype=np.float64).reshape(-1)
        displacement = np.asarray(handle["u_node"], dtype=np.float64).T
        cycle = int(round(scalar(handle["state_metadata/cycle"])))
        substep = int(round(scalar(handle["state_metadata/substep"])))
        load = scalar(handle["state_metadata/imposed_displacement"])
        converged = bool(round(scalar(handle["state_metadata/producer_metadata/converged"])))
        require_matlab_string(handle["state_metadata/timing"], "holdout timing")
    if cycle != int(row["cycle"]) or substep != 4 or not converged:
        raise ValueError(f"decoded state identity mismatch: {path.name}")
    if damage.shape != (expected_nodes,) or displacement.shape != (expected_nodes, 2):
        raise ValueError(f"decoded field shape mismatch: {path.name}")
    if not np.isfinite(damage).all() or not np.isfinite(displacement).all() or not np.isfinite(load):
        raise ValueError(f"nonfinite source field: {path.name}")
    if not np.isclose(load, float(row["imposed_displacement"]), atol=1e-12, rtol=0):
        raise ValueError(f"imposed displacement mismatch: {path.name}")
    verify_boundary(xy, displacement, load)
    return damage, displacement, load, actual_hash


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--static", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--states", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    args = parser.parse_args()
    manifest_path = args.out.with_suffix(".manifest.json")
    receipt_path = args.out.with_suffix(".unsealing.json")
    if any(path.exists() for path in (args.out, manifest_path, receipt_path)):
        raise FileExistsError("packet, manifest, or unsealing receipt already exists")
    rows = locked_rows(args.index)
    xy, conn, young, nu, eta = read_static(args.static)
    area = q4_lumped_area(xy, conn)
    unsealed_at = datetime.now(timezone.utc).isoformat()
    receipt = {
        "experiment_id": "S09-E007", "event": "permanent_u0125_scientific_unsealing",
        "unsealed_at_utc": unsealed_at, "source_root": args.source_root,
        "state_index_sha256": EXPECTED_INDEX_SHA256, "cycles": list(EXPECTED_CYCLES),
        "status": "started", "scientific_arrays_decoded": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    states, sources = [], []
    try:
        for row in rows:
            path = args.states / Path(row["payload_file"]).name
            values = read_state(path, row, xy)
            receipt["scientific_arrays_decoded"] = True
            states.append(values[:3])
            sources.append({"cycle": int(row["cycle"]), "file": path.name, "sha256": values[3]})
        np.savez_compressed(
            args.out, xy=xy, conn=conn, lumped_area=area,
            holdout_d=np.stack([item[0] for item in states]),
            holdout_u=np.stack([item[1] for item in states]),
            holdout_load=np.asarray([item[2] for item in states]),
            holdout_cycle=np.asarray(EXPECTED_CYCLES),
            young=np.asarray(young), nu=np.asarray(nu), eta=np.asarray(eta),
        )
        manifest = {
            "experiment_id": "S09-E007", "protocol_revision": "v2-frozen-beta025-u0125-holdout",
            "source_commit": EXPECTED_SOURCE_COMMIT, "source_root": args.source_root,
            "state_index_sha256": EXPECTED_INDEX_SHA256, "static_sha256": sha256(args.static),
            "packet_sha256": sha256(args.out), "cycles": list(EXPECTED_CYCLES),
            "nodes": len(xy), "elements": len(conn), "area": float(area.sum()),
            "material": {"young": young, "nu": nu, "eta": eta}, "sources": sources,
            "exposure_limit": "non-blind post-selection trajectory; exposure_unknown_not_cleared",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
        receipt.update(status="succeeded", packet_sha256=manifest["packet_sha256"])
    except Exception as error:
        receipt.update(status="failed", error=repr(error))
        raise
    finally:
        receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
