import copy
import json
import sys
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

import s09_e009_runner_integration as integration
from s09_e009_four_arm import ARM_ORDER, arm_direction, atomic_losses, parameter_state_sha256
from s09_e009_runner_integration import (
    EVALUATION_UPDATES,
    EXPECTED_CYCLES,
    EXPECTED_BASE_RUNTIME_CONFIG_SHA256,
    TERMINAL_COMPLETED,
    TERMINAL_EXECUTION_FAILED,
    TERMINAL_METHOD_INAPPLICABLE,
    TOTAL_UPDATE_CAP,
    UPDATES_PER_ARM,
    _direction_with_damage_reference,
    build_no_training_integration,
    build_schedule,
    cross_arm_performance_eligible,
    validate_integration_config,
    validate_termination_receipt,
    write_no_training_receipt,
)
from s09_stage0a_p1_packet import sha256_file
from test_s09_stage0a_p1_runner import packet_fixture


INTEGRATION_CONFIG = ROOT / "docs/research/S09/S09-E009/runner_integration_config_20261017.json"


def synthetic_integration_config(tmp_path: Path, base_config: Path) -> Path:
    config = json.loads(INTEGRATION_CONFIG.read_text())
    config["source"]["base_runtime_config_sha256"] = sha256_file(base_config)
    path = tmp_path / "integration.json"
    path.write_text(json.dumps(config))
    return path


def build_bundle(tmp_path: Path, monkeypatch):
    packet, base_config, _ = packet_fixture(tmp_path)
    integration_config = synthetic_integration_config(tmp_path, base_config)
    calls = []

    def reject_step(_self, *_args, **_kwargs):
        calls.append(True)
        raise AssertionError("no-training integration called AdamW.step")

    monkeypatch.setattr(torch.optim.AdamW, "step", reject_step)
    bundle = build_no_training_integration(
        packet_dir=packet,
        base_config_path=base_config,
        integration_config_path=integration_config,
        device=torch.device("cpu"),
        synthetic_test_adapter=True,
    )
    assert calls == []
    return bundle, base_config


def test_schedule_is_exactly_500_updates_per_arm_with_frozen_checkpoints():
    schedule = build_schedule()
    assert len(schedule) == UPDATES_PER_ARM == 500
    assert TOTAL_UPDATE_CAP == len(ARM_ORDER) * len(schedule) == 2000
    assert schedule[:16] == EXPECTED_CYCLES
    assert schedule[496:] == (1, 2, 3, 4)
    assert EVALUATION_UPDATES == (0, 16, 64, 128, 256, 496, 500)


def test_no_training_build_isolates_arms_and_preserves_empty_optimizers(tmp_path: Path,
                                                                      monkeypatch):
    bundle, _ = build_bundle(tmp_path, monkeypatch)
    receipt = bundle.receipt
    assert receipt["verdict"] == "NO_TRAINING_INTEGRATION_PASS"
    assert receipt["execution_authorized"] is False
    assert receipt["optimizer_step_performed"] is False
    assert receipt["model_hashes_unchanged"] is True
    assert receipt["optimizer_states_empty_after_direction_preflight"] is True
    assert tuple(receipt["arm_order"]) == ARM_ORDER
    assert len(set(receipt["isolation"]["initial_state_sha256"].values())) == 1
    assert receipt["isolation"]["parameter_objects_disjoint"] is True
    assert receipt["isolation"]["optimizer_states_empty"] is True
    assert receipt["isolation"]["optimizer_parameters_match_arm_models"] is True
    assert all(not optimizer.state for optimizer in bundle.optimizers.values())
    assert len({id(optimizer) for optimizer in bundle.optimizers.values()}) == 4
    for left_index, left_arm in enumerate(ARM_ORDER):
        left_buffers = {buffer.data_ptr() for buffer in bundle.arm_runtimes[left_arm].model.buffers()}
        for right_arm in ARM_ORDER[left_index + 1:]:
            right_buffers = {
                buffer.data_ptr() for buffer in bundle.arm_runtimes[right_arm].model.buffers()
            }
            assert left_buffers.isdisjoint(right_buffers)
    assert all(record["clip_count_for_complete_direction"] == 1
               for record in receipt["directions"].values())
    json.dumps(receipt, allow_nan=False)


def test_runner_direction_matches_reviewed_core_for_all_64_arm_cycle_pairs(tmp_path: Path):
    packet, base_config, _ = packet_fixture(tmp_path)
    integration_config = synthetic_integration_config(tmp_path, base_config)
    bundle = build_no_training_integration(
        packet_dir=packet,
        base_config_path=base_config,
        integration_config_path=integration_config,
        device=torch.device("cpu"),
        synthetic_test_adapter=True,
    )
    for arm in ARM_ORDER:
        runtime = bundle.arm_runtimes[arm]
        before = parameter_state_sha256(runtime.model)
        for index in range(len(EXPECTED_CYCLES)):
            expected_model = copy.deepcopy(runtime.model)
            expected_runtime = copy.copy(runtime)
            expected_runtime.model = expected_model
            losses, _ = atomic_losses(expected_runtime, index=index)
            expected, expected_diagnostic = arm_direction(expected_model, losses, arm)

            losses, _ = atomic_losses(runtime, index=index)
            observed, g_d, observed_diagnostic = _direction_with_damage_reference(
                runtime.model, losses, arm)
            torch.testing.assert_close(observed, expected, rtol=0, atol=0)
            assert observed_diagnostic["layout"]["parameter_order"] == \
                expected_diagnostic["layout"]["parameter_order"]
            assert g_d.shape == observed.shape
            assert torch.isfinite(g_d).all()
        assert parameter_state_sha256(runtime.model) == before


def test_config_and_receipt_fail_closed(tmp_path: Path, monkeypatch):
    packet, base_config, _ = packet_fixture(tmp_path)
    config = json.loads(INTEGRATION_CONFIG.read_text())
    config["execution_authorized"] = True
    with pytest.raises(PermissionError, match="unauthorised"):
        validate_integration_config(config, base_config_path=base_config)

    bundle, _ = build_bundle(tmp_path / "second", monkeypatch)
    output = tmp_path / "receipt" / "no_training.json"
    write_no_training_receipt(bundle, output)
    observed = json.loads(output.read_text())
    assert observed == bundle.receipt
    with pytest.raises(ValueError, match="already exists"):
        write_no_training_receipt(bundle, output)


def test_production_config_is_bound_to_reviewed_base_bytes():
    config = json.loads(INTEGRATION_CONFIG.read_text())
    base_config = ROOT / config["source"]["base_runtime_config"]
    assert sha256_file(base_config) == EXPECTED_BASE_RUNTIME_CONFIG_SHA256
    validate_integration_config(config, base_config_path=base_config)


def test_synthetic_adapter_rejects_non_resolution_base_drift(tmp_path: Path):
    _, base_config, _ = packet_fixture(tmp_path)
    base = json.loads(base_config.read_text())
    base["model"]["hard_constraint_contract"]["peak_boundary_lifting"]["atol"] = 1.0
    base_config.write_text(json.dumps(base))
    config_path = synthetic_integration_config(tmp_path, base_config)
    config = json.loads(config_path.read_text())
    with pytest.raises(ValueError, match="non-resolution"):
        validate_integration_config(
            config,
            base_config_path=base_config,
            synthetic_test_adapter=True,
        )


def test_synthetic_adapter_verifies_trusted_reference_bytes(tmp_path: Path, monkeypatch):
    _, base_config, _ = packet_fixture(tmp_path)
    config_path = synthetic_integration_config(tmp_path, base_config)
    config = json.loads(config_path.read_text())
    trusted = json.loads(integration.TRUSTED_BASE_RUNTIME_CONFIG.read_text())
    trusted["model"]["hard_constraint_contract"]["peak_boundary_lifting"]["atol"] = 1.0
    tampered_trusted = tmp_path / "tampered_trusted.json"
    tampered_trusted.write_text(json.dumps(trusted))
    monkeypatch.setattr(integration, "TRUSTED_BASE_RUNTIME_CONFIG", tampered_trusted)
    with pytest.raises(ValueError, match="trusted base identity drift"):
        validate_integration_config(
            config,
            base_config_path=base_config,
            synthetic_test_adapter=True,
        )


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("budget", "unused_budget_transfer"), True, "budget"),
        (("source", "protocol_revision"), "v2-three-arm", "protocol revision"),
        (("producer", "resolved_environment"), {"already_resolved": True}, "producer"),
        (("producer", "alias"), "unreviewed-gpu", "producer"),
        (("producer", "forbidden_fallback"), "allowed", "producer"),
        (("producer", "remote_root"), "/tmp/other", "producer"),
    ],
)
def test_config_rejects_frozen_contract_drift(path, value, message):
    config = json.loads(INTEGRATION_CONFIG.read_text())
    config[path[0]][path[1]] = value
    base_config = ROOT / config["source"]["base_runtime_config"]
    with pytest.raises(ValueError, match=message):
        validate_integration_config(config, base_config_path=base_config)


def terminal_receipt(state: str, arm: str) -> dict:
    receipt = {
        "arm": arm,
        "terminal_state": state,
        "stop_update": 500,
        "optimizer_steps_completed": 500,
        "fully_logged_updates": 500,
        "evaluation_updates_present": list(EVALUATION_UPDATES),
        "last_valid_evaluation_update": 500,
        "reason": None,
        "update500_checkpoint_present": True,
        "finite_status": True,
        "hard_constraint_counts": {"total": 0},
        "artifacts": {
            "termination_receipt.json": "sha256",
            "checkpoint_update500.pt": "sha256-checkpoint",
        },
    }
    if state == TERMINAL_EXECUTION_FAILED:
        receipt.update({
            "stop_update": 128,
            "optimizer_steps_completed": 127,
            "fully_logged_updates": 126,
            "evaluation_updates_present": [0, 16, 64],
            "last_valid_evaluation_update": 64,
            "reason": "NONFINITE_GRADIENT",
            "update500_checkpoint_present": False,
            "finite_status": False,
            "artifacts": {"termination_receipt.json": "sha256"},
        })
    elif state == TERMINAL_METHOD_INAPPLICABLE:
        receipt.update({
            "stop_update": 64,
            "optimizer_steps_completed": 63,
            "fully_logged_updates": 63,
            "evaluation_updates_present": [0, 16],
            "last_valid_evaluation_update": 16,
            "reason": "ANCHOR_STATIONARY_OR_INAPPLICABLE",
            "update500_checkpoint_present": False,
            "artifacts": {"termination_receipt.json": "sha256"},
        })
    return receipt


@pytest.mark.parametrize(
    ("state", "arm"),
    [
        (TERMINAL_COMPLETED, ARM_ORDER[0]),
        (TERMINAL_EXECUTION_FAILED, ARM_ORDER[1]),
        (TERMINAL_METHOD_INAPPLICABLE, ARM_ORDER[2]),
    ],
)
def test_conditional_terminal_receipts_accept_declared_states(state: str, arm: str):
    validate_termination_receipt(terminal_receipt(state, arm))


def test_terminal_receipts_fail_closed_on_premature_or_fabricated_final_checkpoint():
    failed = terminal_receipt(TERMINAL_EXECUTION_FAILED, ARM_ORDER[1])
    failed["update500_checkpoint_present"] = True
    failed["artifacts"]["checkpoint_update500.pt"] = "sha256-checkpoint"
    with pytest.raises(ValueError, match="requires complete"):
        validate_termination_receipt(failed)

    inapplicable = terminal_receipt(TERMINAL_METHOD_INAPPLICABLE, ARM_ORDER[2])
    inapplicable["reason"] = "GENERIC_FAILURE"
    with pytest.raises(ValueError, match="reason drift"):
        validate_termination_receipt(inapplicable)


@pytest.mark.parametrize("state", [TERMINAL_COMPLETED, TERMINAL_METHOD_INAPPLICABLE])
def test_valid_terminal_states_reject_hard_constraint_violations(state: str):
    arm = ARM_ORDER[0] if state == TERMINAL_COMPLETED else ARM_ORDER[2]
    receipt = terminal_receipt(state, arm)
    receipt["hard_constraint_counts"]["total"] = 1
    with pytest.raises(ValueError, match="hard-constraint violations"):
        validate_termination_receipt(receipt)


def test_failed_receipt_retains_real_hard_constraint_count():
    receipt = terminal_receipt(TERMINAL_EXECUTION_FAILED, ARM_ORDER[1])
    receipt["hard_constraint_counts"]["total"] = 1
    validate_termination_receipt(receipt)


def test_terminal_receipt_links_evaluations_and_stop_location_to_completed_steps():
    impossible_evaluation = terminal_receipt(TERMINAL_EXECUTION_FAILED, ARM_ORDER[1])
    impossible_evaluation.update({
        "stop_update": 0,
        "optimizer_steps_completed": 0,
        "fully_logged_updates": 0,
        "evaluation_updates_present": [0, 500],
        "last_valid_evaluation_update": 500,
    })
    with pytest.raises(ValueError, match="evaluation update exceeds"):
        validate_termination_receipt(impossible_evaluation)

    impossible_stop = terminal_receipt(TERMINAL_EXECUTION_FAILED, ARM_ORDER[1])
    impossible_stop["stop_update"] = 1
    with pytest.raises(ValueError, match="cannot precede"):
        validate_termination_receipt(impossible_stop)


def test_late_execution_failure_preserves_existing_update500_checkpoint():
    receipt = terminal_receipt(TERMINAL_COMPLETED, ARM_ORDER[0])
    receipt["terminal_state"] = TERMINAL_EXECUTION_FAILED
    receipt["reason"] = "DECISION_FIGURE_WRITE_FAILED"
    validate_termination_receipt(receipt)


def test_cross_arm_comparison_requires_identity_and_replay_gates():
    assert cross_arm_performance_eligible(shared_identity_pass=True, replay_gate_pass=True)
    assert not cross_arm_performance_eligible(
        shared_identity_pass=False, replay_gate_pass=True)
    assert not cross_arm_performance_eligible(
        shared_identity_pass=True, replay_gate_pass=False)


def test_config_freezes_conditional_evidence_manifest():
    config = json.loads(INTEGRATION_CONFIG.read_text())
    assert config["evidence"]["required_per_arm_common"] == [
        "start_identity.json", "train_log.jsonl", "gradient_diagnostics.jsonl",
        "diagnostic_metrics.jsonl", "termination_receipt.json",
    ]
    assert config["evidence"]["required_completed_arm_only"] == [
        "checkpoint_update500.pt",
    ]
    assert config["evidence"]["terminal_states"][TERMINAL_EXECUTION_FAILED][
        "update500_checkpoint_required"] is False
    assert config["evidence"]["terminal_states"][TERMINAL_METHOD_INAPPLICABLE][
        "update500_checkpoint_required"] is False
    assert config["evidence"]["required_shared"][-4:] == [
        "decision_figure.png", "per_cycle_metrics.csv", "decision.md",
        "completion_receipt.json",
    ]
