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
    _array_sha256,
    _qualify_full_trajectory,
    freeze_p1_from_qualified_pairs,
)
from s09_stage0a_packet import DecodedStage0AState


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


def state(cycle: int, substep: int, magnitude: float) -> DecodedStage0AState:
    return DecodedStage0AState(
        logical_cycle=cycle, logical_substep=substep,
        source_state_key=f"c{cycle:04d}_s{substep:02d}",
        u_node=np.full((5, 2), magnitude + .01, dtype=np.float64),
        d_node=np.full(5, magnitude, dtype=np.float64),
        history_gp=np.full((2, 4, 4), magnitude, dtype=np.float64),
        strain_en_undgr_gp=np.zeros((2, 4), dtype=np.float64),
        strain_en_degr_gp=np.zeros((2, 4), dtype=np.float64),
        imposed_displacement=.125, payload_sha256="0" * 64,
    )


def test_p1_adapter_requires_73_pairs_six_state_receipt_and_bound_weights():
    pairs = {cycle: (state(cycle, 0, 0.0), state(cycle, 4, (cycle - 1) / 360))
             for cycle in range(1, 74)}
    nodal = np.ones(5, dtype=np.float64)
    gp = np.ones((2, 4), dtype=np.float64)
    context = replace(S09_E008_CONTEXT, expected_nodes=5, expected_elements=2)
    weight_receipt = {
        "source_static_sha256": context.static_sha256,
        "node_order": "native", "element_order": "native",
        "gauss_point_order": "native quadrature",
        "nodal_weight_sha256": _array_sha256(nodal),
        "gp_weight_sha256": _array_sha256(gp),
        "nodal_weight_shape": [5], "gp_weight_shape": [2, 4],
    }
    receipt = {"verdict": "FULL_TRAJECTORY_HASH_QUALIFIED",
               "context_sha256": context.digest,
               "qualified_cycles": list(range(1, 74)),
               "qualified_substeps": list(range(6)),
               "unique_payload_count": 366,
               "all_payload_hashes_preflighted": True}
    result = freeze_p1_from_qualified_pairs(
        pairs_by_cycle=pairs, qualification_receipt=receipt,
        nodal_weight=nodal, gp_weight=gp, weight_receipt=weight_receipt,
        context=context)
    assert result["qualified_six_state_trajectory"] is True
    bad = dict(receipt); bad["qualified_substeps"] = [0, 1, 3, 4, 5]
    with pytest.raises(ValueError, match="six-state"):
        freeze_p1_from_qualified_pairs(
            pairs_by_cycle=pairs, qualification_receipt=bad,
            nodal_weight=nodal, gp_weight=gp, weight_receipt=weight_receipt,
            context=context)
    wrong_weights = dict(weight_receipt); wrong_weights["node_order"] = "sorted"
    with pytest.raises(ValueError, match="weight receipt"):
        freeze_p1_from_qualified_pairs(
            pairs_by_cycle=pairs, qualification_receipt=receipt,
            nodal_weight=nodal, gp_weight=gp, weight_receipt=wrong_weights,
            context=context)
