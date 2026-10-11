import csv
import hashlib
from pathlib import Path

import h5py
import numpy as np
import pytest

import SENS_tensile.build_s09_fixed_damage_holdout_packet as builder
from SENS_tensile.build_s09_fixed_damage_holdout_packet import EXPECTED_CYCLES, locked_rows, read_state
from SENS_tensile.run_s09_fixed_damage_holdout import aggregate_primary, classify, defined_ratio, worst_defined


def test_outcome_table_is_exhaustive():
    assert classify(.5, 1.1)[0] == "positive"
    assert classify(.5, 1.100001)[0] == "negative_displacement"
    assert classify(.500001, 1.1)[0] == "negative_equilibrium"
    assert classify(.500001, 1.100001)[0] == "negative_both"
    assert classify(None, 1.0)[0] == "inconclusive"
    with pytest.raises(FloatingPointError):
        classify(float("nan"), 1.0)


def test_membership_lock_rejects_wrong_index_hash(tmp_path: Path):
    path = tmp_path / "state_index.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["cycle", "substep"])
        writer.writeheader()
        for cycle in EXPECTED_CYCLES:
            writer.writerow({"cycle": cycle, "substep": 4})
    with pytest.raises(ValueError, match="identity mismatch"):
        locked_rows(path, {"states": []})


def test_membership_lock_accepts_exact_complete_fixture(tmp_path: Path, monkeypatch):
    path = tmp_path / "state_index.csv"
    fields = ["state_key", "cycle", "substep", "timing", "is_alias",
              "source_state_key", "payload_file", "payload_sha256", "converged",
              "imposed_displacement"]
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for cycle in EXPECTED_CYCLES:
            key = f"c{cycle:04d}_s04"
            writer.writerow({"state_key": key, "cycle": cycle, "substep": 4,
                             "timing": "post_history_commit", "is_alias": 0,
                             "source_state_key": key, "payload_file": f"states/{key}.mat",
                             "payload_sha256": "a" * 64, "converged": 1,
                             "imposed_displacement": .124999875})
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setitem(builder.EXPECTED_METADATA_HASHES, "state_index.csv", digest)
    lock = {"states": [{"cycle": cycle, "payload_file": f"states/c{cycle:04d}_s04.mat",
                         "payload_sha256": "a" * 64, "imposed_displacement": .124999875}
                        for cycle in EXPECTED_CYCLES]}
    assert [int(row["cycle"]) for row in locked_rows(path, lock)] == list(EXPECTED_CYCLES)


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


def test_state_reader_rejects_rounded_metadata(tmp_path: Path):
    path = tmp_path / "c0001_s04.mat"
    xy = np.array([[0., 0.], [1., 0.], [0., 1.], [1., 1.]])
    with h5py.File(path, "w") as handle:
        handle.create_dataset("d_node", data=np.zeros((1, 4)))
        handle.create_dataset("u_node", data=np.array([[0., 0., 0., 0.], [0., 0., .125, .125]]))
        meta = handle.create_group("state_metadata")
        meta.create_dataset("cycle", data=[[1.4]])
        meta.create_dataset("substep", data=[[4.]])
        meta.create_dataset("imposed_displacement", data=[[.125]])
        timing = meta.create_dataset("timing", data=np.zeros((1, 1), dtype=np.uint32))
        timing.attrs["MATLAB_class"] = np.bytes_(b"string")
        producer = meta.create_group("producer_metadata")
        producer.create_dataset("converged", data=[[1.]])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="cycle"):
        read_state(path, {"payload_sha256": digest, "cycle": "1", "imposed_displacement": ".125"},
                   xy, expected_nodes=4)


def test_ratio_definability_and_worst_tie_rule():
    assert defined_ratio(1.0, 0.0) is None
    assert defined_ratio(1.0, 2.0) == .5
    with pytest.raises(FloatingPointError):
        defined_ratio(float("inf"), 2.0)
    rows = [{"cycle": 1, "ratio": 2.0}, {"cycle": 2, "ratio": None},
            {"cycle": 3, "ratio": 2.0}]
    assert worst_defined(rows, "ratio") == {"cycle": 1, "value": 2.0,
                                             "tie_rule": "first_locked_ordinal"}


def test_primary_zero_comparator_denominators_are_inconclusive_not_failure():
    candidate = [{"cycle": 1, "E_u": 1.0, "E_f_over_affine": 1.0}]
    comparator = [{"cycle": 1, "E_u": 0.0, "E_f_over_affine": 0.0}]
    qu, qf, du, df, undefined = aggregate_primary(candidate, comparator)
    assert qu is None and qf is None and du == 0 and df == 0 and undefined == []


def test_primary_zero_affine_denominator_is_explicitly_undefined():
    candidate = [{"cycle": 1, "E_u": 1.0, "E_f_over_affine": None}]
    comparator = [{"cycle": 1, "E_u": 2.0, "E_f_over_affine": 1.0}]
    qu, qf, _, df, undefined = aggregate_primary(candidate, comparator)
    assert qu == .5 and qf is None and df is None and undefined == [("candidate", 1)]


def test_primary_rejects_nonfinite_derived_metric():
    candidate = [{"cycle": 1, "E_u": 1.0, "E_f_over_affine": float("inf")}]
    comparator = [{"cycle": 1, "E_u": 2.0, "E_f_over_affine": 1.0}]
    with pytest.raises(FloatingPointError):
        aggregate_primary(candidate, comparator)
