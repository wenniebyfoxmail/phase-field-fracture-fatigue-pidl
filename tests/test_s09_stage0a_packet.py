import hashlib
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_stage0a_packet import (
    decode_payload,
    decode_stage0a_transitions,
    preflight_payloads,
    transition_rows,
)


def write_payload(path: Path, *, cycle: int, substep: int, load: float,
                  nodes: int = 4, elements: int = 2, dtype=np.float64):
    with h5py.File(path, "w") as handle:
        handle.create_dataset("u_node", data=np.arange(2 * nodes, dtype=dtype).reshape(2, nodes))
        handle.create_dataset("d_node", data=np.linspace(0, .5, nodes, dtype=dtype)[None])
        handle.create_dataset("history_gp", data=np.ones((4, 4, elements), dtype=dtype))
        handle.create_dataset("strain_en_undgr_gp", data=np.ones((4, elements), dtype=dtype))
        handle.create_dataset("strain_en_degr_gp", data=np.ones((4, elements), dtype=dtype) * .5)
        metadata = handle.create_group("state_metadata")
        metadata.create_dataset("cycle", data=np.array([[cycle]], dtype=np.float64))
        metadata.create_dataset("substep", data=np.array([[substep]], dtype=np.float64))
        metadata.create_dataset("imposed_displacement", data=np.array([[load]], dtype=np.float64))
        producer = metadata.create_group("producer_metadata")
        producer.create_dataset("converged", data=np.array([[1.]], dtype=np.float64))
        for name in ("state_key", "timing", "history_channel_labels"):
            dataset = metadata.create_dataset(name, data=np.zeros((1, 1), dtype=np.uint32))
            dataset.attrs["MATLAB_class"] = np.bytes_(b"string")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row(*, cycle: int, substep: int, source: str, file: str, sha: str,
        alias: bool, load: float, timing: str):
    return {
        "state_key": f"c{cycle:04d}_s{substep:02d}",
        "cycle": str(cycle),
        "substep": str(substep),
        "source_state_key": source,
        "payload_file": f"states/{file}",
        "payload_sha256": sha,
        "is_alias": "1" if alias else "0",
        "converged": "1",
        "imposed_displacement": repr(load),
        "timing": timing,
    }


def two_cycle_fixture(tmp_path: Path):
    c1_pre = tmp_path / "c0001_s00.mat"
    c1_peak = tmp_path / "c0001_s04.mat"
    c1_post = tmp_path / "c0001_s05.mat"
    c2_peak = tmp_path / "c0002_s04.mat"
    write_payload(c1_pre, cycle=1, substep=0, load=0.0)
    write_payload(c1_peak, cycle=1, substep=4, load=.125)
    write_payload(c1_post, cycle=1, substep=5, load=0.0)
    write_payload(c2_peak, cycle=2, substep=4, load=.125)
    rows = [
        row(cycle=1, substep=0, source="c0001_s00", file=c1_pre.name,
            sha=digest(c1_pre), alias=False, load=0.0, timing="pre_cycle_committed"),
        row(cycle=1, substep=4, source="c0001_s04", file=c1_peak.name,
            sha=digest(c1_peak), alias=False, load=.125, timing="post_history_commit"),
        row(cycle=1, substep=5, source="c0001_s05", file=c1_post.name,
            sha=digest(c1_post), alias=False, load=0.0, timing="post_history_commit"),
        row(cycle=2, substep=0, source="c0001_s05", file=c1_post.name,
            sha=digest(c1_post), alias=True, load=0.0, timing="pre_cycle_committed"),
        row(cycle=2, substep=4, source="c0002_s04", file=c2_peak.name,
            sha=digest(c2_peak), alias=False, load=.125, timing="post_history_commit"),
    ]
    return rows


def test_transition_rows_requires_exact_alias_identity(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    pairs = transition_rows(rows, [1, 2])
    assert pairs[1][2]["state_key"] == "c0001_s05"
    bad = [dict(value) for value in rows]
    bad[3]["payload_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="alias"):
        transition_rows(bad, [2])


def test_transition_rows_rejects_malformed_previous_s05(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    rows[2]["timing"] = "pre_cycle_committed"
    with pytest.raises(ValueError, match="previous s05"):
        transition_rows(rows, [2])


def test_preflight_hashes_all_payloads_before_decode(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    pairs = transition_rows(rows, [1, 2])
    inventory = preflight_payloads(tmp_path, pairs)
    assert len(inventory) == 4
    (tmp_path / "c0002_s04.mat").write_bytes(b"changed")
    with pytest.raises(ValueError, match="preflight hash"):
        preflight_payloads(tmp_path, pairs)


def test_preflight_rejects_payload_path_escape(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    rows[0]["payload_file"] = "../c0001_s00.mat"
    with pytest.raises(ValueError, match="payload path"):
        preflight_payloads(tmp_path, transition_rows(rows, [1]))


def test_decoder_preserves_native_support_and_alias_equality(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    decoded, receipt = decode_stage0a_transitions(
        states_dir=tmp_path, rows=rows, cycles=[1, 2],
        expected_nodes=4, expected_elements=2,
    )
    assert len(decoded) == 2
    pre, peak = decoded[1]
    assert pre.d_node.shape == (4,)
    assert pre.u_node.shape == (4, 2)
    assert pre.history_gp.shape == (2, 4, 4)
    assert peak.strain_en_undgr_gp.shape == (2, 4)
    assert receipt["preflight_completed_before_decode"] is True
    assert receipt["numerical_s05_to_s00_alias_cycles"] == [2]


def test_decoder_rejects_non_float64_without_cast(tmp_path: Path):
    path = tmp_path / "bad.mat"
    write_payload(path, cycle=1, substep=4, load=.125, dtype=np.float32)
    item = row(cycle=1, substep=4, source="c0001_s04", file=path.name,
               sha=digest(path), alias=False, load=.125, timing="post_history_commit")
    with pytest.raises(ValueError, match="stored float64"):
        decode_payload(path, item, expected_nodes=4, expected_elements=2)


def test_decoder_rejects_logical_metadata_rounding(tmp_path: Path):
    path = tmp_path / "rounded.mat"
    write_payload(path, cycle=1, substep=4, load=.125)
    with h5py.File(path, "r+") as handle:
        handle["state_metadata/cycle"][0, 0] = 1.25
    item = row(cycle=1, substep=4, source="c0001_s04", file=path.name,
               sha=digest(path), alias=False, load=.125, timing="post_history_commit")
    with pytest.raises(ValueError, match="cycle"):
        decode_payload(path, item, expected_nodes=4, expected_elements=2)
