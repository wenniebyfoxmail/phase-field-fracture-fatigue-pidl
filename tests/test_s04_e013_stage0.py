from pathlib import Path
import sys

import pytest
import torch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "SENS_tensile"))

import export_s04_e013_paired_eta0 as exporter
from export_s04_e013_paired_eta0 import (
    mapped_step,
    registered_states,
    validate_event_evidence,
    validate_model_checkpoint_damage,
)


def test_recovery_offset_mapping_is_exact():
    assert mapped_step(20, 2) == 97
    assert mapped_step(20, 4) == 99
    assert mapped_step(20, 5) == 100
    assert mapped_step(60, 2) == 297
    assert mapped_step(60, 4) == 299
    assert mapped_step(60, 5) == 300
    assert mapped_step(82, 2) == 407
    assert mapped_step(82, 4) == 409
    assert mapped_step(82, 5) == 410
    assert mapped_step(83, 2) == 412
    assert mapped_step(83, 4) == 414
    assert mapped_step(83, 5) == 415


def test_registered_matrix_and_own_event_are_complete():
    states = registered_states()
    matrix = [state for state in states if state.comparison_class == "same_cycle"]
    event = [state for state in states if state.comparison_class == "own_event_first_detect"]
    assert len(matrix) == 12
    assert {(s.cycle, s.substep) for s in matrix} == {
        (cycle, substep) for cycle in (20, 60, 82, 83) for substep in (2, 4, 5)
    }
    assert len(event) == 1
    assert (event[0].cycle, event[0].substep, event[0].step) == (85, 4, 424)


def test_model_checkpoint_timing_mismatch_fails_closed():
    accepted = torch.zeros(4)
    with pytest.raises(AssertionError, match="model/checkpoint damage mismatch"):
        validate_model_checkpoint_damage(
            torch.tensor([0.0, 0.0, 0.0, 1e-4]), accepted, step=409,
        )


def test_event_confirmation_metadata_mismatch_fails_closed(tmp_path, monkeypatch):
    best = tmp_path / "best_models"
    best.mkdir()
    checkpoints = {}
    for step in range(423, 428):
        path = best / f"checkpoint_step_{step}.pt"
        path.write_bytes(b"locked-placeholder")
        damage = torch.tensor([0.0, 0.0, 0.96, 0.97, 0.98]) if step >= 424 else torch.zeros(5)
        checkpoints[path] = {
            "mesh_state_signature": exporter.EXPECTED_SIGNATURE,
            "mesh_connectivity_arity": 4,
            "history_storage": "q4_gp4",
            "damage_history_storage": "previous_accepted_nodal",
            "history_driver_mode": "current_active",
            "hist_fat": torch.zeros((86408, 4)),
            "psi_plus_prev": torch.zeros((86408, 4)),
            "hist_alpha": damage,
            "_frac_detected": step >= 424,
            "_frac_cycle": 424 if step >= 424 else None,
            "_frac_confirm_remaining": 0 if step == 423 else 427 - step,
        }
    checkpoints[best / "checkpoint_step_426.pt"]["_frac_confirm_remaining"] = 0
    monkeypatch.setattr(exporter, "safe_torch_load", lambda path, device: checkpoints[path])
    nodes = torch.tensor([[0.49, 0.0]] * 5)
    with pytest.raises(AssertionError, match="confirmation metadata mismatch"):
        validate_event_evidence(tmp_path, nodes, torch.device("cpu"))
