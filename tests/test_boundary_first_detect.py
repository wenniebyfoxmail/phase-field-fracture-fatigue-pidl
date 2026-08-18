from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "source"))

from boundary_first_detect import (
    map_raw_step,
    observe_boundary,
    record_boundary_observation,
    write_right_censor_receipt,
    g4_archive_stop_decision,
)


DISPLACEMENTS = [0.03, 0.06, 0.09, 0.12, 0.0]


def test_frozen_hard5_raw_step_mapping():
    assert map_raw_step(300, displacements=DISPLACEMENTS) == {
        "physical_cycle": 60, "substep_index": 4, "substep_displacement": 0.0,
    }
    for step, cycle in [(379, 76), (409, 82), (444, 89)]:
        mapped = map_raw_step(step, displacements=DISPLACEMENTS)
        assert mapped == {
            "physical_cycle": cycle,
            "substep_index": 3,
            "substep_displacement": 0.12,
        }


def test_boundary_only_receipt_is_first_trigger_and_immutable(tmp_path: Path):
    coords = np.asarray([[0.49, -0.1], [0.49, 0.0], [0.49, 0.1], [0.0, 0.0]])
    damage = np.asarray([0.96, 0.97, 0.98, 1.0])
    observation = observe_boundary(
        409, damage, coords, displacements=DISPLACEMENTS
    )
    assert observation["triggered"] is True
    trace = tmp_path / "trace.jsonl"
    receipt = tmp_path / "first.json"
    first = record_boundary_observation(trace, receipt, observation)
    later = dict(observation, raw_step=444, physical_cycle=89)
    second = record_boundary_observation(trace, receipt, later)
    assert first == second
    assert json.loads(receipt.read_text())["raw_step"] == 409
    assert len(trace.read_text().splitlines()) == 2


def test_energy_like_damage_away_from_boundary_cannot_trigger():
    coords = np.asarray([[0.49, 0.0], [0.0, 0.0], [0.1, 0.0], [0.2, 0.0]])
    damage = np.asarray([0.2, 1.0, 1.0, 1.0])
    observation = observe_boundary(
        379, damage, coords, displacements=DISPLACEMENTS
    )
    assert observation["triggered"] is False
    assert observation["qualifying_nodes"] == 0


def test_right_censor_receipt_is_explicit_and_non_overwriting(tmp_path: Path):
    path = tmp_path / "right_censor.json"
    payload = write_right_censor_receipt(
        path, physical_cycle=92, last_raw_step=460
    )
    assert payload["boundary_triggered"] is False
    assert json.loads(path.read_text())["last_raw_step"] == 460
    with np.testing.assert_raises(FileExistsError):
        write_right_censor_receipt(path, physical_cycle=92, last_raw_step=460)


def test_g4_stop_state_machine_covers_early_boundary_energy_only_and_censor():
    common = {
        "hard_stop_raw_step": 460,
        "minimum_archive_raw_step": 409,
        "boundary_receipt_enabled": True,
    }
    assert g4_archive_stop_decision(
        raw_step=400, boundary_receipt_exists=True, fracture_confirmed=True, **common
    ) == "continue"
    assert g4_archive_stop_decision(
        raw_step=409, boundary_receipt_exists=True, fracture_confirmed=True, **common
    ) == "fracture_confirmed"
    assert g4_archive_stop_decision(
        raw_step=409, boundary_receipt_exists=False, fracture_confirmed=True, **common
    ) == "continue"
    assert g4_archive_stop_decision(
        raw_step=460, boundary_receipt_exists=False, fracture_confirmed=True, **common
    ) == "right_censor"
