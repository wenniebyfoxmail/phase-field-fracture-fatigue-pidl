#!/usr/bin/env python3
"""Build the frozen S09-E004 nodal packet from native-Q4 MATLAB exports."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


TRAIN_CYCLES = (1, 7, 14, 21, 28, 35, 41, 48, 55, 62, 69, 75, 82, 89, 96, 103)
DEV_CYCLES = (76, 82, 83)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_matlab_string(dataset, label: str):
    """Require MATLAB's opaque string object without pretending to decode it."""
    matlab_class = dataset.attrs.get("MATLAB_class", b"")
    if bytes(matlab_class) != b"string":
        raise ValueError(f"{label} is not a MATLAB string object")


def scalar(dataset) -> float:
    return float(np.asarray(dataset).reshape(-1)[0])


def q4_lumped_area(xy: np.ndarray, conn: np.ndarray) -> np.ndarray:
    g = 1.0 / np.sqrt(3.0)
    locations = ((g, g), (-g, g), (g, -g), (-g, -g))
    area = np.zeros(len(xy), dtype=np.float64)
    element_xy = xy[conn]
    for xi, eta in locations:
        shape = np.array(
            [(1-xi)*(1-eta), (1+xi)*(1-eta),
             (1+xi)*(1+eta), (1-xi)*(1+eta)], dtype=np.float64
        ) / 4.0
        deriv = np.array(
            [[-(1-eta), 1-eta, 1+eta, -(1+eta)],
             [-(1-xi), -(1+xi), 1+xi, 1-xi]], dtype=np.float64
        ) / 4.0
        jac = np.einsum("ij,ejk->eik", deriv, element_xy)
        det = np.linalg.det(jac)
        if np.any(det <= 0):
            raise ValueError("non-positive native-Q4 Jacobian")
        for local in range(4):
            np.add.at(area, conn[:, local], det * shape[local])
    if not np.isfinite(area).all() or np.any(area <= 0):
        raise ValueError("invalid nodal lumped area")
    return area


def read_static(path: Path):
    with h5py.File(path, "r") as handle:
        root = handle["stage0b_static"]
        xy = np.asarray(root["mesh/node_coordinates"], dtype=np.float64).T
        conn = np.asarray(root["mesh/cells_0based"], dtype=np.int64).T
        young = scalar(root["material_parameters/E"])
        nu = scalar(root["material_parameters/ni"])
        eta = scalar(root["material_parameters/res_stiff"])
    if xy.shape != (86756, 2) or conn.shape != (86408, 4):
        raise ValueError(f"unexpected native mesh {xy.shape=} {conn.shape=}")
    return xy, conn, young, nu, eta


def read_index(path: Path):
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    return {(int(row["cycle"]), int(row["substep"])): row for row in rows}


def verify_boundary(xy: np.ndarray, u: np.ndarray, load: float):
    bottom = np.isclose(xy[:, 1], xy[:, 1].min(), atol=1e-12, rtol=0)
    top = np.isclose(xy[:, 1], xy[:, 1].max(), atol=1e-12, rtol=0)
    if not np.allclose(u[bottom], 0.0, atol=1e-10, rtol=0):
        raise ValueError("bottom displacement identity failed")
    expected = np.column_stack((np.zeros(top.sum()), np.full(top.sum(), load)))
    if not np.allclose(u[top], expected, atol=1e-10, rtol=0):
        raise ValueError("top displacement identity failed")


def read_train(path: Path, row: dict, xy: np.ndarray):
    expected_hash = row["payload_sha256"]
    actual_hash = sha256(path)
    if actual_hash != expected_hash:
        raise ValueError(f"payload hash mismatch for {path.name}")
    with h5py.File(path, "r") as handle:
        d = np.asarray(handle["d_node"], dtype=np.float64).reshape(-1)
        u = np.asarray(handle["u_node"], dtype=np.float64).T
        cycle = int(round(scalar(handle["state_metadata/cycle"])))
        substep = int(round(scalar(handle["state_metadata/substep"])))
        require_matlab_string(handle["state_metadata/timing"], "train timing")
        load = scalar(handle["state_metadata/imposed_displacement"])
        effective = scalar(handle["state_metadata/effective_load_factor"])
        converged = bool(round(scalar(handle["state_metadata/producer_metadata/converged"])))
    timing = row["timing"]
    if cycle != int(row["cycle"]) or substep != 4 or timing != "post_history_commit":
        raise ValueError(f"state identity mismatch for {path.name}: {cycle=} {substep=} {timing=}")
    if not converged or not np.isclose(effective, float(row["effective_load_factor"]), atol=1e-12):
        raise ValueError(f"producer status mismatch for {path.name}")
    if d.shape != (len(xy),) or u.shape != (len(xy), 2):
        raise ValueError(f"field shape mismatch for {path.name}")
    if not np.isfinite(d).all() or not np.isfinite(u).all():
        raise ValueError(f"non-finite field in {path.name}")
    verify_boundary(xy, u, load)
    return d, u, load, cycle, actual_hash


def read_dev(path: Path, xy: np.ndarray, conn: np.ndarray):
    with h5py.File(path, "r") as handle:
        root = handle["cycle_state"]
        file_xy = np.asarray(root["node_coords"], dtype=np.float64).T
        file_conn = np.asarray(root["connectivity_q4"], dtype=np.int64).T - 1
        d = np.asarray(root["d_node"], dtype=np.float64).reshape(-1)
        u = np.asarray(root["u_node"], dtype=np.float64).T
        cycle = int(round(scalar(root["cycle"])))
        substep = int(round(scalar(root["substep"])))
        require_matlab_string(root["state_timing"], "development timing")
        load = scalar(root["umax"]) * scalar(root["effective_load_factor"])
        history_committed = bool(round(scalar(root["history_committed"])))
        damage_committed = bool(round(scalar(root["damage_committed"])))
    if cycle not in DEV_CYCLES or substep != 4 or not history_committed or not damage_committed:
        raise ValueError(f"development state identity mismatch for {path.name}")
    if not np.array_equal(file_conn, conn) or not np.allclose(file_xy, xy, atol=0, rtol=0):
        raise ValueError(f"mesh identity mismatch for {path.name}")
    if not np.isfinite(d).all() or not np.isfinite(u).all():
        raise ValueError(f"non-finite development field in {path.name}")
    verify_boundary(xy, u, load)
    return d, u, load, cycle, sha256(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--static", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--train-dir", type=Path, required=True)
    parser.add_argument("--dev", type=Path, nargs=3, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.with_suffix(".manifest.json").exists():
        raise FileExistsError("packet or manifest already exists")

    xy, conn, young, nu, eta = read_static(args.static)
    index = read_index(args.index)
    train = []
    sources = []
    for cycle in TRAIN_CYCLES:
        path = args.train_dir / f"c{cycle:04d}_s04.mat"
        values = read_train(path, index[(cycle, 4)], xy)
        train.append(values[:4])
        sources.append({"role": "train", "cycle": cycle, "path": str(path), "sha256": values[4]})
    dev = []
    for path in args.dev:
        values = read_dev(path, xy, conn)
        dev.append(values[:4])
        sources.append({"role": "development", "cycle": values[3], "path": str(path), "sha256": values[4]})
    dev.sort(key=lambda state: state[3])

    lumped_area = q4_lumped_area(xy, conn)
    np.savez_compressed(
        args.out,
        xy=xy, conn=conn, lumped_area=lumped_area,
        train_d=np.stack([x[0] for x in train]), train_u=np.stack([x[1] for x in train]),
        train_load=np.array([x[2] for x in train]), train_cycle=np.array([x[3] for x in train]),
        dev_d=np.stack([x[0] for x in dev]), dev_u=np.stack([x[1] for x in dev]),
        dev_load=np.array([x[2] for x in dev]), dev_cycle=np.array([x[3] for x in dev]),
        young=np.array(young), nu=np.array(nu), eta=np.array(eta),
    )
    manifest = {
        "experiment_id": "S09-E004",
        "protocol_revision": "v1-equilibrium-operator-prototype",
        "packet": str(args.out),
        "packet_sha256": sha256(args.out),
        "static_sha256": sha256(args.static),
        "index_sha256": sha256(args.index),
        "train_cycles": list(TRAIN_CYCLES),
        "development_cycles": list(DEV_CYCLES),
        "nodes": len(xy), "elements": len(conn), "area": float(lumped_area.sum()),
        "material": {"young": young, "nu": nu, "eta": eta},
        "sources": sources,
        "qualification_limit": (
            "Request31 reuse audit records reference_checked=false and "
            "capture_neutrality_passed=false; this packet is development evidence only."
        ),
    }
    args.out.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    )
    print(json.dumps({k: manifest[k] for k in ("packet_sha256", "nodes", "elements", "area")}))


if __name__ == "__main__":
    main()
