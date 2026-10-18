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
from s09_e009_four_arm import (
    AnchorStationary,
    LOSS_ORDER,
    amplitude_auc,
    group_amplitude_ratio,
)
from s09_e010_producer import (
    ArmReceiptCloseError,
    ArmRunResult,
    EXPECTED_E009_REFERENCE_SHA256,
    EXPECTED_PROTOCOL_CONTRACT_SHA256,
    GROWTH_CYCLES,
    HARD_CONSTRAINT_KEYS,
    NEAR_STAGNANT_CYCLES,
    PRODUCER_EXECUTION_FILES,
    _arm_execution_failure,
    _a25_replay_failure_requires_stop,
    _conditional_physics_axis,
    _failure_completion_receipt,
    _load_e009_reference,
    _persist_exact_a25_replay_trace,
    _protocol_contract_sha256,
    _unresolved_projection,
    _verify_arm_evidence_integrity,
    exact_a25_replay_validity,
    run_arm_state_machine,
)
from s09_e010_runner_integration import (
    EVALUATION_UPDATES,
    EXPECTED_CYCLES,
    EXPECTED_PACKET_SHA256,
    validate_integration_config,
)
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


class MethodInapplicableAdapter(MockAdapter):
    def step(self, update, cycle):
        raise AnchorStationary("anchor unavailable")


def test_protocol_and_frozen_reference_identities_are_bound():
    assert _protocol_contract_sha256(PROTOCOL) == EXPECTED_PROTOCOL_CONTRACT_SHA256
    assert sha256_file(producer.E009_REFERENCE_PATH) == EXPECTED_E009_REFERENCE_SHA256
    assert "source/s09_e009_four_arm.py" in PRODUCER_EXECUTION_FILES


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


def test_resolved_projection_preserves_reviewed_packet_identity():
    config_path = (
        ROOT / "docs/research/S09/S09-E010/runner_integration_config_20261018.json"
    )
    base_path = (
        ROOT / "docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json"
    )
    projected = _unresolved_projection(json.loads(config_path.read_text()))
    assert projected["source"]["input_packet_sha256"] == EXPECTED_PACKET_SHA256
    validate_integration_config(
        projected, base_config_path=base_path, synthetic_test_adapter=False)


def test_unreadable_checkpoint_writes_failed_receipt(monkeypatch, tmp_path):
    original_sha256_file = producer.sha256_file
    original_read_bytes = Path.read_bytes

    def fail_checkpoint_sha(path):
        if Path(path).name == "checkpoint_update500.pt":
            raise OSError("checkpoint cannot be read")
        return original_sha256_file(path)

    def fail_checkpoint_fallback(path):
        if path.name == "checkpoint_update500.pt":
            raise OSError("checkpoint still cannot be read")
        return original_read_bytes(path)

    monkeypatch.setattr(producer, "sha256_file", fail_checkpoint_sha)
    monkeypatch.setattr(Path, "read_bytes", fail_checkpoint_fallback)
    result = run_arm_state_machine(
        arm=ARM_B25, adapter=MockAdapter(), arm_dir=tmp_path / "B25")
    assert result.receipt["terminal_state"] == "EXECUTION_FAILED"
    assert result.receipt["update500_checkpoint_present"] is True
    assert "checkpoint_update500.pt" in result.receipt["artifacts"]
    assert "FALLBACK_UNREADABLE_ARTIFACTS" in result.receipt["reason"]
    assert (result.arm_dir / "checkpoint_update500.pt").is_file()
    assert (result.arm_dir / "termination_receipt.json").is_file()


def test_shared_evidence_rejects_post_receipt_arm_artifact_drift(tmp_path):
    result = run_arm_state_machine(
        arm=ARM_B0, adapter=MockAdapter(), arm_dir=tmp_path / "B0")
    train_path = result.arm_dir / "train_log.jsonl"
    train_path.write_bytes(train_path.read_bytes()[:-1])
    with pytest.raises(ValueError, match="arm artifact hash drift after close"):
        _verify_arm_evidence_integrity({ARM_B0: result})


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("optimizer_steps_completed", 500.0, "invalid optimizer step count"),
        ("finite_status", 1, "finite status must be boolean"),
    ],
)
def test_shared_evidence_rejects_terminal_receipt_scalar_type_drift(
    tmp_path, field, replacement, message,
):
    result = run_arm_state_machine(
        arm=ARM_B0, adapter=MockAdapter(), arm_dir=tmp_path / "B0")
    receipt_path = result.arm_dir / "termination_receipt.json"
    mutated = json.loads(receipt_path.read_text())
    mutated[field] = replacement
    receipt_path.write_text(json.dumps(mutated, sort_keys=True))
    with pytest.raises(ValueError, match=message):
        _verify_arm_evidence_integrity({ARM_B0: result})


def test_execution_failure_stops_later_arms_but_method_inapplicable_does_not(
    tmp_path,
):
    failed = run_arm_state_machine(
        arm=ARM_B25, adapter=MockAdapter(fail_at=17), arm_dir=tmp_path / "failed")
    assert _arm_execution_failure(failed) is True
    failed.receipt["terminal_state"] = "METHOD_INAPPLICABLE"
    assert _arm_execution_failure(failed) is False


def test_a25_method_inapplicable_does_not_become_global_replay_failure(tmp_path):
    result = _reference_result(tmp_path)
    result.receipt["terminal_state"] = "METHOD_INAPPLICABLE"
    trace = exact_a25_replay_validity(result)
    assert trace["pass"] is False
    assert _a25_replay_failure_requires_stop(result, trace) is False
    result.receipt["terminal_state"] = "COMPLETED"
    assert _a25_replay_failure_requires_stop(result, trace) is True


def test_a25_method_inapplicable_allows_later_arms_and_final_method_status(
    tmp_path,
):
    results = {
        ARM_A25: run_arm_state_machine(
            arm=ARM_A25,
            adapter=MethodInapplicableAdapter(),
            arm_dir=tmp_path / ARM_A25,
        ),
        ARM_B25: run_arm_state_machine(
            arm=ARM_B25,
            adapter=MockAdapter(),
            arm_dir=tmp_path / ARM_B25,
        ),
        ARM_B0: run_arm_state_machine(
            arm=ARM_B0,
            adapter=MockAdapter(),
            arm_dir=tmp_path / ARM_B0,
        ),
    }
    trace = exact_a25_replay_validity(results[ARM_A25])
    assert trace["pass"] is False
    assert _a25_replay_failure_requires_stop(results[ARM_A25], trace) is False
    decision = producer._decision_from_results(results)
    assert tuple(results) == (ARM_A25, ARM_B25, ARM_B0)
    assert decision["status"] == "METHOD_INAPPLICABLE"
    assert decision["e010_classification"] is None


def test_terminal_receipt_write_failure_preserves_current_arm_step_count(
    monkeypatch, tmp_path,
):
    original_write = producer._write_new_json

    def fail_terminal_receipt(path, value):
        if path.name == "termination_receipt.json":
            raise OSError("receipt storage unavailable")
        return original_write(path, value)

    monkeypatch.setattr(producer, "_write_new_json", fail_terminal_receipt)
    with pytest.raises(ArmReceiptCloseError) as captured:
        run_arm_state_machine(
            arm=ARM_B0,
            adapter=MockAdapter(fail_at=17),
            arm_dir=tmp_path / "B0",
        )
    partial = captured.value.result
    assert partial.receipt["terminal_state"] == "EXECUTION_FAILED"
    assert partial.receipt["optimizer_steps_completed"] == 17
    assert partial.receipt["fully_logged_updates"] == 16
    completion = _failure_completion_receipt(
        config={"planned_run_id": "run", "source": {}},
        error=captured.value,
        start=0.0,
        arm_results={ARM_B0: partial},
        exact_a25_replay_trace=None,
    )
    assert completion["total_optimizer_steps_completed"] == 17
    assert completion["arm_receipts"][ARM_B0]["fully_logged_updates"] == 16


def test_replay_trace_is_persisted_before_failure_and_bound_to_failure_receipt(
    tmp_path,
):
    result = _reference_result(tmp_path)
    result.evaluations[500]["aggregate"]["G"] += 1e-6
    trace = exact_a25_replay_validity(result)
    assert trace["pass"] is False
    _persist_exact_a25_replay_trace(tmp_path, trace)
    stored = json.loads((tmp_path / "exact_a25_replay_trace.json").read_text())
    assert stored == trace
    result.receipt["optimizer_steps_completed"] = 500
    receipt = _failure_completion_receipt(
        config={"planned_run_id": "run", "source": {}},
        error=RuntimeError("REPLAY_VALIDITY_GATE_FAILED"),
        start=0.0,
        arm_results={ARM_A25: result},
        exact_a25_replay_trace=trace,
    )
    assert receipt["exact_a25_replay_trace"] == trace
    assert receipt["total_optimizer_steps_completed"] == 500


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
