import csv
import hashlib
from pathlib import Path

import h5py
import numpy as np
import pytest

import SENS_tensile.build_s09_fixed_damage_holdout_packet as builder
from SENS_tensile.build_s09_fixed_damage_holdout_packet import EXPECTED_CYCLES, locked_rows, read_state
from SENS_tensile.run_s09_fixed_damage_holdout import classify


def test_outcome_table_is_exhaustive():
    assert classify(.5, 1.1)[0] == "positive"
    assert classify(.5, 1.100001)[0] == "negative_displacement"
    assert classify(.500001, 1.1)[0] == "negative_equilibrium"
    assert classify(.500001, 1.100001)[0] == "negative_both"
    assert classify(float("nan"), 1.0)[0] == "inconclusive"


def test_membership_lock_rejects_wrong_index_hash(tmp_path: Path):
    path = tmp_path / "state_index.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["cycle", "substep"])
        writer.writeheader()
        for cycle in EXPECTED_CYCLES:
            writer.writerow({"cycle": cycle, "substep": 4})
    with pytest.raises(ValueError, match="identity mismatch"):
        locked_rows(path)


def test_membership_lock_accepts_exact_complete_fixture(tmp_path: Path, monkeypatch):
    path = tmp_path / "state_index.csv"
    fields = ["state_key", "cycle", "substep", "timing", "is_alias",
              "source_state_key", "payload_file", "payload_sha256", "converged"]
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for cycle in EXPECTED_CYCLES:
            key = f"c{cycle:04d}_s04"
            writer.writerow({"state_key": key, "cycle": cycle, "substep": 4,
                             "timing": "post_history_commit", "is_alias": 0,
                             "source_state_key": key, "payload_file": f"states/{key}.mat",
                             "payload_sha256": "a" * 64, "converged": 1})
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(builder, "EXPECTED_INDEX_SHA256", digest)
    assert [int(row["cycle"]) for row in locked_rows(path)] == list(EXPECTED_CYCLES)


def test_state_reader_checks_hash_identity_and_boundary(tmp_path: Path):
    path = tmp_path / "c0001_s04.mat"
    xy = np.array([[0., 0.], [1., 0.], [0., 1.], [1., 1.]])
    with h5py.File(path, "w") as handle:
        handle.create_dataset("d_node", data=np.array([[0., .1, .2, .3]]))
        handle.create_dataset("u_node", data=np.array([[0., 0., 0., 0.], [0., 0., .125, .125]]))
        meta = handle.create_group("state_metadata")
        meta.create_dataset("cycle", data=[[1.]])
        meta.create_dataset("substep", data=[[4.]])
        meta.create_dataset("imposed_displacement", data=[[.125]])
        timing = meta.create_dataset("timing", data=np.zeros((1, 1), dtype=np.uint32))
        timing.attrs["MATLAB_class"] = np.bytes_(b"string")
        producer = meta.create_group("producer_metadata")
        producer.create_dataset("converged", data=[[1]], dtype=np.uint8)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    row = {"payload_sha256": digest, "cycle": "1", "imposed_displacement": ".125"}
    damage, displacement, load, observed = read_state(path, row, xy, expected_nodes=4)
    assert observed == digest and load == .125
    assert damage.shape == (4,) and displacement.shape == (4, 2)
