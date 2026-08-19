from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from loading_cadence_smoke import (  # noqa: E402
    SCHEDULES,
    boundary_reactions,
    semantic_torch_hash,
    state_rows,
    validate_nested_schedules,
    write_json,
)


def test_locked_schedules_are_nested_and_halve_increment():
    validate_nested_schedules()
    assert [len(SCHEDULES[key]) for key in ("S4", "S8", "S16")] == [4, 8, 16]


def test_recovery_offset_and_peak_unload_mapping():
    for level, width in (("S4", 4), ("S8", 8), ("S16", 16)):
        rows = state_rows(level, 3)
        assert len(rows) == 1 + 3 * width
        assert rows[0]["state_label"] == "state0_recovery_post_commit"
        peak = next(row for row in rows if row["state_label"] == "c2_peak")
        unload = next(row for row in rows if row["state_label"] == "c3_unloaded")
        assert peak["raw_step"] == 1 + width + width // 2 - 1
        assert unload["raw_step"] == 3 * width


def test_boundary_traction_reaction_uniform_stress():
    nodes = np.asarray([[0., 0.], [1., 0.], [1., 1.], [0., 1.]])
    triangles = np.asarray([[0, 1, 2], [0, 2, 3]])
    result = boundary_reactions(
        nodes, triangles, np.asarray([2., 2.]), np.asarray([7., 7.]), np.asarray([0., 0.])
    )
    assert np.isclose(result["top_reaction_y"], 7.0)
    assert np.isclose(result["bottom_reaction_y"], -7.0)
    assert np.isclose(result["force_imbalance_fraction"], 0.0)


def test_receipt_json_serialization(tmp_path):
    output = tmp_path / "receipt.json"
    write_json(output, {"branch": "codex/test", "manifest": str(tmp_path / "manifest.json")})
    assert '"branch": "codex/test"' in output.read_text(encoding="utf-8")


def test_semantic_state_hash_detects_tensor_and_history_mutation(tmp_path):
    first = tmp_path / "first.pt"
    copied = tmp_path / "copied.pt"
    mutated = tmp_path / "mutated.pt"
    torch.save({"hist_alpha": torch.tensor([0.1, 0.2]), "remaining": 3}, first)
    copied.write_bytes(first.read_bytes())
    torch.save({"hist_alpha": torch.tensor([0.1, 0.3]), "remaining": 3}, mutated)
    assert semantic_torch_hash(first) == semantic_torch_hash(copied)
    assert semantic_torch_hash(first) != semantic_torch_hash(mutated)
