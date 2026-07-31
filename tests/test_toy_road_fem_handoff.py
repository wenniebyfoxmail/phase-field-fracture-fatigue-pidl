from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "producer_handoffs" / "toy_to_road_independent_fem_20260731"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def test_parent_lock_is_latest_c83_c86_baseline() -> None:
    lock = load_json(HANDOFF / "PARENT_LOCK.json")
    assert lock["parent_reference_id"] == "hard5_eta0_u012_5step_20260729"
    assert lock["event"] == {"first_hit": 83, "confirmed": 86}
    assert lock["physics"]["eta"] == 0.0
    assert lock["physics"]["n_substeps"] == 5
    assert lock["mesh"]["num_elem"] == 86408
    assert lock["state_semantics_id"] == "cycle_peak_coherent_v1"
