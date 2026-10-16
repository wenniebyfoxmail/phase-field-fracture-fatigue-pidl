import csv
import hashlib
import sys
from dataclasses import replace
from pathlib import Path

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_stage0a_capability import (
    S09_E008_CONTEXT,
    _derive_native_weights,
    _qualify_decode_and_freeze,
    _qualify_full_trajectory,
)


FIELDNAMES = ["state_key", "cycle", "substep", "timing", "is_alias",
              "source_state_key", "payload_file", "payload_sha256",
              "nominal_load_factor", "imposed_displacement", "converged"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_qualified_fixture(tmp_path: Path):
    states = tmp_path / "states"; states.mkdir()
    static_dir = tmp_path / "static"; static_dir.mkdir()
    static = static_dir / "native_q4_mesh_dofs_quadrature.mat"
    static.write_bytes(b"synthetic-static")
    physical = {}
    rows = []
    loads = (0.0, .25, .5, .75, 1.0, 0.0)
    for cycle in range(1, 74):
        for substep, load in enumerate(loads):
            key = f"c{cycle:04d}_s{substep:02d}"
            alias = substep == 0 and cycle > 1
            source = f"c{cycle - 1:04d}_s05" if alias else key
            if source not in physical:
                path = states / f"{source}.mat"
                path.write_bytes(source.encode())
                physical[source] = (path.name, sha(path))
            filename, digest = physical[source]
            rows.append({
                "state_key": key, "cycle": str(cycle), "substep": str(substep),
                "timing": "pre_cycle_committed" if substep == 0 else "post_history_commit",
                "is_alias": "1" if alias else "0", "source_state_key": source,
                "payload_file": f"states/{filename}", "payload_sha256": digest,
                "nominal_load_factor": repr(load), "imposed_displacement": repr(load),
                "converged": "1",
            })
    index = tmp_path / "state_index.csv"
    with index.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader(); writer.writerows(rows)
    context = replace(S09_E008_CONTEXT, state_index_sha256=sha(index),
                      static_sha256=sha(static), expected_nodes=3,
                      expected_elements=2)
    return context, rows


def write_static(path: Path):
    g = 1 / np.sqrt(3)
    locations = ((g, g), (-g, g), (g, -g), (-g, -g))
    nxi, dndxi = [], []
    for xi, eta in locations:
        nxi.append([.25*(1-xi)*(1-eta), .25*(1+xi)*(1-eta),
                    .25*(1+xi)*(1+eta), .25*(1-xi)*(1+eta)])
        dndxi.append([
            [-.25*(1-eta), .25*(1-eta), .25*(1+eta), -.25*(1+eta)],
            [-.25*(1-xi), -.25*(1+xi), .25*(1+xi), .25*(1-xi)],
        ])
    xy = np.array([[0,0], [1,0], [1,1], [0,1], [2,0], [2,1]], dtype=np.float64)
    conn = np.array([[0,1,2,3], [1,4,5,2]], dtype=np.int64)
    nxi = np.asarray(nxi).T
    dndxi = np.asarray(dndxi).transpose(1, 2, 0)
    with h5py.File(path, "w") as handle:
        root = handle.create_group("stage0b_static")
        mesh = root.create_group("mesh")
        mesh.create_dataset("node_coordinates", data=xy.T)
        mesh.create_dataset("cells_0based", data=conn.T)
        quadrature = root.create_group("quadrature")
        quadrature.create_dataset("gauss_W", data=np.ones((1, 4), dtype=np.float64))
        quadrature.create_dataset("Nxi", data=nxi.T)
        quadrature.create_dataset("dNdxi", data=dndxi.transpose(2, 1, 0))
        geometry = root.create_group("geometry")
        geometry.create_dataset("t", data=np.array([[1.]], dtype=np.float64))


def write_state(path: Path, *, cycle: int, substep: int, magnitude: float,
                bad_float32: bool = False):
    dtype = np.float32 if bad_float32 else np.float64
    nodes, elements = 6, 2
    u = np.ones((2, nodes), dtype=dtype) * np.array([[.01], [.1]], dtype=dtype)
    d = np.full((1, nodes), magnitude, dtype=dtype)
    decoded_history = np.ones((elements, 4, 4), dtype=dtype) * magnitude
    history = decoded_history.transpose(2, 1, 0)
    with h5py.File(path, "w") as handle:
        handle.create_dataset("u_node", data=u)
        handle.create_dataset("d_node", data=d)
        handle.create_dataset("history_gp", data=history)
        handle.create_dataset("strain_en_undgr_gp", data=np.zeros((4, elements), dtype=dtype))
        handle.create_dataset("strain_en_degr_gp", data=np.zeros((4, elements), dtype=dtype))
        meta = handle.create_group("state_metadata")
        meta.create_dataset("cycle", data=np.array([[cycle]], dtype=np.float64))
        meta.create_dataset("substep", data=np.array([[substep]], dtype=np.float64))
        imposed = (0.0, .031249875, .062499875, .093749875, .124999875, 0.0)[substep]
        meta.create_dataset("imposed_displacement", data=np.array([[imposed]], dtype=np.float64))
        producer = meta.create_group("producer_metadata")
        converged = producer.create_dataset(
            "converged", data=np.array([[1]], dtype=np.uint8))
        converged.attrs["MATLAB_class"] = np.bytes_(b"logical")
        converged.attrs["MATLAB_int_decode"] = np.uint8(1)
        for name in ("state_key", "timing", "history_channel_labels"):
            dataset = meta.create_dataset(name, data=np.zeros((1, 1), dtype=np.uint32))
            dataset.attrs["MATLAB_class"] = np.bytes_(b"string")


def make_decodable_fixture(tmp_path: Path, *, corrupt_key: str | None = None):
    states = tmp_path / "states"; states.mkdir()
    static_dir = tmp_path / "static"; static_dir.mkdir()
    static = static_dir / "native_q4_mesh_dofs_quadrature.mat"
    write_static(static)
    physical = {}
    rows = []
    loads = (0.0, .25, .5, .75, 1.0, 0.0)
    imposed = (0.0, .031249875, .062499875, .093749875, .124999875, 0.0)
    for cycle in range(1, 74):
        for substep, load in enumerate(loads):
            key = f"c{cycle:04d}_s{substep:02d}"
            alias = substep == 0 and cycle > 1
            source = f"c{cycle - 1:04d}_s05" if alias else key
            if source not in physical:
                source_cycle = int(source[1:5]); source_step = int(source[-2:])
                magnitude = (source_cycle - 1) / 360 if source_step == 4 else 0.0
                path = states / f"{source}.mat"
                write_state(path, cycle=source_cycle, substep=source_step,
                            magnitude=magnitude, bad_float32=source == corrupt_key)
                physical[source] = (path.name, sha(path))
            filename, digest = physical[source]
            rows.append({
                "state_key": key, "cycle": str(cycle), "substep": str(substep),
                "timing": "pre_cycle_committed" if substep == 0 else "post_history_commit",
                "is_alias": "1" if alias else "0", "source_state_key": source,
                "payload_file": f"states/{filename}", "payload_sha256": digest,
                "nominal_load_factor": repr(load), "imposed_displacement": repr(imposed[substep]),
                "converged": "1",
            })
    index = tmp_path / "state_index.csv"
    with index.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader(); writer.writerows(rows)
    context = replace(S09_E008_CONTEXT, state_index_sha256=sha(index),
                      static_sha256=sha(static), expected_nodes=6,
                      expected_elements=2)
    return context


def test_full_trajectory_qualification_binds_all_six_states_and_payloads(tmp_path: Path):
    context, _ = make_qualified_fixture(tmp_path)
    rows, receipt = _qualify_full_trajectory(run_root=tmp_path, context=context)
    assert len(rows) == 438
    assert len(receipt["unique_payload_inventory"]) == 366
    assert receipt["qualified_substeps"] == list(range(6))
    assert receipt["hdf5_open_count"] == 0


def test_full_trajectory_rejects_missing_s02_before_payload_decode(tmp_path: Path):
    context, rows = make_qualified_fixture(tmp_path)
    rows = [row for row in rows if row["state_key"] != "c0001_s02"]
    index = tmp_path / "state_index.csv"
    with index.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader(); writer.writerows(rows)
    context = replace(context, state_index_sha256=sha(index))
    with pytest.raises(ValueError, match="438 logical"):
        _qualify_full_trajectory(run_root=tmp_path, context=context)


def test_controlled_route_derives_weights_decodes_all_six_states_and_freezes(tmp_path: Path):
    context = make_decodable_fixture(tmp_path)
    result, hash_receipt, decode_receipt = _qualify_decode_and_freeze(
        run_root=tmp_path, context=context)
    assert result["verdict"] == "P1_CONTRACT_FROZEN"
    assert result["qualified_six_state_trajectory"] is True
    assert result["native_weight_receipt"]["source_static_sha256"] == context.static_sha256
    assert hash_receipt["unique_payload_count"] == 366
    assert decode_receipt["decoded_physical_payload_count"] == 366
    assert decode_receipt["decoded_logical_state_count"] == 438
    assert set(decode_receipt["decoded_substeps"]) == set(range(6))


def test_native_weights_are_derived_from_static_geometry_and_order(tmp_path: Path):
    context = make_decodable_fixture(tmp_path)
    nodal, gp, receipt = _derive_native_weights(
        tmp_path / "static" / context.static_filename, context)
    np.testing.assert_allclose(gp, np.full((2, 4), .25), rtol=0, atol=1e-15)
    np.testing.assert_allclose(nodal, [.25, .5, .5, .25, .25, .25],
                               rtol=0, atol=1e-15)
    assert receipt["nodal_weight_sha256"] == hashlib.sha256(
        np.ascontiguousarray(nodal).tobytes()).hexdigest()


@pytest.mark.parametrize("stored", [
    np.array([[2.5, 5.0]], dtype=np.float64),
    np.array([[2.5, np.nan]], dtype=np.float64),
    np.empty((0, 0), dtype=np.float64),
])
def test_native_weight_derivation_rejects_non_scalar_thickness(tmp_path: Path, stored):
    context = make_decodable_fixture(tmp_path)
    static = tmp_path / "static" / context.static_filename
    with h5py.File(static, "r+") as handle:
        del handle["stage0b_static/geometry/t"]
        handle["stage0b_static/geometry"].create_dataset("t", data=stored)
    context = replace(context, static_sha256=sha(static))
    with pytest.raises(ValueError, match="one finite scalar"):
        _derive_native_weights(static, context)


def test_controlled_route_rejects_hash_valid_bad_intermediate_support(tmp_path: Path):
    context = make_decodable_fixture(tmp_path, corrupt_key="c0001_s02")
    with pytest.raises(ValueError, match="stored float64"):
        _qualify_decode_and_freeze(run_root=tmp_path, context=context)


@pytest.mark.parametrize("bad_load", [0.75, float("nan")])
def test_controlled_route_rejects_logical_alias_load_mismatch(tmp_path: Path, bad_load):
    context = make_decodable_fixture(tmp_path)
    index = tmp_path / "state_index.csv"
    with index.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    next(row for row in rows if row["state_key"] == "c0002_s00")[
        "imposed_displacement"] = repr(bad_load)
    with index.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader(); writer.writerows(rows)
    context = replace(context, state_index_sha256=sha(index))
    with pytest.raises(ValueError, match="logical-to-physical load mismatch: c0002_s00"):
        _qualify_decode_and_freeze(run_root=tmp_path, context=context)
