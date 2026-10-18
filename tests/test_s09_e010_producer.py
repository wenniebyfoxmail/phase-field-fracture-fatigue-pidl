import copy
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

import s09_e010_producer as producer
from s09_e009_four_arm import LOSS_ORDER, amplitude_auc, group_amplitude_ratio
from s09_e010_producer import (
    ArmRunResult,
    EXPECTED_E009_REFERENCE_SHA256,
    EXPECTED_PROTOCOL_CONTRACT_SHA256,
    GROWTH_CYCLES,
    HARD_CONSTRAINT_KEYS,
    NEAR_STAGNANT_CYCLES,
    _conditional_physics_axis,
    _load_e009_reference,
    _protocol_contract_sha256,
    exact_a25_replay_validity,
    run_arm_state_machine,
)
from s09_e010_runner_integration import EVALUATION_UPDATES, EXPECTED_CYCLES
from s09_e010_support_amplitude import ARM_A25, ARM_B0, ARM_B25
from s09_stage0a_p1_packet import sha256_file

PROTOCOL = ROOT / "docs/research/S09/S09-E010/experiment.md"


@pytest.fixture(autouse=True)
def reject_real_optimizer_step(monkeypatch):
    calls = []

    def reject(_self, *_args, **_kwargs):
        calls.append(True)
        raise AssertionError("producer-package test called AdamW.step")

    monkeypatch.setattr(torch.optim.AdamW, "step", reject)
    yield
    assert calls == []


def _hard_counts():
    return {name: 0 for name in HARD_CONSTRAINT_KEYS}


def _evaluation(update: int):
    rows = []
    for index, cycle in enumerate(EXPECTED_CYCLES):
        group = ("growth" if cycle in GROWTH_CYCLES else
                 "near_stagnant" if cycle in NEAR_STAGNANT_CYCLES else "other")
        predicted = 0.001 + index * 1e-5
        truth = 0.0005 + index * 2e-5
        rows.append({
            "update": update,
            "cycle": cycle,
            "group": group,
            "predicted_damage_increment_abs_mean": predicted,
            "true_damage_increment_abs_mean": truth,
            "damage_increment_mae": abs(predicted - truth),
            "false_growth": max(0.0, predicted - truth),
            "predicted_target_spatial_correlation": 0.5,
            "L_judge": 0.5,
            "atomic_losses": {name: 0.5 for name in LOSS_ORDER},
            "grouped_losses": {"L_D": 1.0, "L_U": 0.5, "L_H": 1.0, "L_P": 0.5},
            "projection_counts": {
                "damage_lower_projection_count": 0,
                "damage_upper_projection_count": 0,
                "alpha_relu_saturation_count": 0,
            },
            "hard_constraint_counts": _hard_counts(),
        })
    growth = [row for row in rows if row["group"] == "growth"]
    stagnant = [row for row in rows if row["group"] == "near_stagnant"]
    predicted = [row["predicted_damage_increment_abs_mean"] for row in rows]
    truth = [row["true_damage_increment_abs_mean"] for row in rows]
    aggregate = {
        "update": update,
        "finite": True,
        "G": float(np.mean([row["damage_increment_mae"] for row in growth])),
        "F": float(np.mean([row["false_growth"] for row in stagnant])),
        "persistence": float(np.mean([row["true_damage_increment_abs_mean"] for row in growth])),
        "L_judge": 0.5,
        "amplitude_ratio": group_amplitude_ratio(
            float(np.mean([row["predicted_damage_increment_abs_mean"] for row in growth])),
            float(np.mean([row["predicted_damage_increment_abs_mean"] for row in stagnant])),
        ),
        "amplitude_auc": amplitude_auc(
            [row["predicted_damage_increment_abs_mean"] for row in growth],
            [row["predicted_damage_increment_abs_mean"] for row in stagnant],
        ),
        "amplitude_pearson": producer._pearson(predicted, truth),
        "amplitude_spearman": producer._pearson(
            producer._average_ranks(predicted), producer._average_ranks(truth)),
        "spatial": {"primary_median": 0.5, "primary_status": "DEFINED",
                    "valid_count": 16, "valid_cycles": list(EXPECTED_CYCLES),
                    "valid_subset_median": 0.5},
        "predicted_field_pairwise_correlation": {
            "pair_count": 120, "valid_pair_count": 120, "na_pair_count": 0,
            "values": [0.2] * 120, "median": 0.2, "minimum": 0.2, "maximum": 0.2,
        },
        "hard_constraint_counts": _hard_counts(),
        "hard_constraint_violations": 0,
        **{name: 0.5 for name in LOSS_ORDER},
        "L_D": 1.0, "L_U": 0.5, "L_H": 1.0, "L_P": 0.5,
    }
    return {"aggregate": aggregate, "per_cycle": rows}


class MockAdapter:
    packet_manifest_sha256 = "packet"
    initial_state_sha256 = "initial"
    hard_constraint_counts = _hard_counts()

    def __init__(self, fail_at=None):
        self.fail_at = fail_at
        self.optimizer_steps_completed = 0

    def evaluate(self, update):
        return _evaluation(update)

    def step(self, update, cycle):
        self.optimizer_steps_completed += 1
        if update == self.fail_at:
            raise RuntimeError("post-step failure")
        return {
            "train_row": {"update": update, "cycle": cycle},
            "gradient_row": {
                "update": update,
                "cycle": cycle,
                "direction_diagnostics": {"clip_applied": False},
                "parameter_displacement_alignment": {
                    "g_D_dot_negative_delta_theta": 1.0,
                    "cosine": 0.5,
                    "displacement_norm": 0.1,
                },
            },
        }

    def save_checkpoint(self, path, update):
        path.write_bytes(f"checkpoint-{update}".encode())


def test_protocol_and_frozen_reference_identities_are_bound():
    assert _protocol_contract_sha256(PROTOCOL) == EXPECTED_PROTOCOL_CONTRACT_SHA256
    assert sha256_file(producer.E009_REFERENCE_PATH) == EXPECTED_E009_REFERENCE_SHA256


def test_state_machine_completes_exact_500_update_schedule(tmp_path):
    result = run_arm_state_machine(
        arm=ARM_B25, adapter=MockAdapter(), arm_dir=tmp_path / "B25")
    assert result.receipt["terminal_state"] == "COMPLETED"
    assert result.receipt["optimizer_steps_completed"] == 500
    assert result.receipt["evaluation_updates_present"] == list(EVALUATION_UPDATES)
    assert len((result.arm_dir / "gradient_diagnostics.jsonl").read_text().splitlines()) == 500


def test_state_machine_preserves_post_step_failure_count(tmp_path):
    result = run_arm_state_machine(
        arm=ARM_B0, adapter=MockAdapter(fail_at=17), arm_dir=tmp_path / "B0")
    assert result.receipt["terminal_state"] == "EXECUTION_FAILED"
    assert result.receipt["stop_update"] == 17
    assert result.receipt["optimizer_steps_completed"] == 17
    assert result.receipt["fully_logged_updates"] == 16


def _reference_result(tmp_path):
    reference = _load_e009_reference()
    arm_dir = tmp_path / ARM_A25
    arm_dir.mkdir()
    (arm_dir / "start_identity.json").write_text(json.dumps({
        "arm": ARM_A25, **copy.deepcopy(reference["start_identity"])
    }))
    target = reference["update500"]
    aggregate = {
        **copy.deepcopy(target["continuous"]),
        "amplitude_ratio": copy.deepcopy(target["amplitude_ratio"]),
        "amplitude_auc": copy.deepcopy(target["amplitude_auc"]),
        "spatial": copy.deepcopy(target["spatial"]),
        "predicted_field_pairwise_correlation": copy.deepcopy(
            target["predicted_field_pairwise_correlation"]),
        "hard_constraint_counts": copy.deepcopy(target["hard_constraint_counts"]),
    }
    rows = [{"cycle": int(cycle), "projection_counts": copy.deepcopy(counts)}
            for cycle, counts in target["per_cycle_projection_counts"].items()]
    return ArmRunResult(
        arm=ARM_A25,
        arm_dir=arm_dir,
        receipt={"terminal_state": "COMPLETED"},
        evaluations={500: {"aggregate": aggregate, "per_cycle": rows}},
    )


def test_exact_a25_replay_gate_passes_reference_and_fails_scalar_drift(tmp_path):
    result = _reference_result(tmp_path)
    assert exact_a25_replay_validity(result)["pass"] is True
    result.evaluations[500]["aggregate"]["G"] += 1e-6
    trace = exact_a25_replay_validity(result)
    assert trace["pass"] is False
    assert trace["clauses"]["update500_G"] is False


def test_conditional_physics_axis_reports_b25_minus_b0():
    def metrics(offset):
        return {"G": 1 + offset, "F": 2 + offset, "L_judge": 3 + offset,
                "L_D": 4 + offset, "L_U": 5 + offset, "L_H": 6 + offset,
                "L_P": 7 + offset,
                "amplitude_auc": {"wins": 18 + offset, "ties": 0,
                                  "losses": 7 - offset, "value": (18 + offset) / 25}}
    result = _conditional_physics_axis(metrics(1), metrics(0))
    assert result["differences"]["L_P"] == 1.0
    assert result["differences"]["amplitude_auc_pair_score"] == 2
