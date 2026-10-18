# ruff: noqa: E402

import copy
import json
import sys
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e009_four_arm import ARM_ANCHOR_25, arm_direction as e009_arm_direction
from s09_e010_runner_integration import (
    EVALUATION_UPDATES,
    EXPECTED_BASE_RUNTIME_CONFIG_SHA256,
    EXPECTED_CYCLES,
    TERMINAL_COMPLETED,
    TERMINAL_EXECUTION_FAILED,
    TERMINAL_METHOD_INAPPLICABLE,
    TOTAL_UPDATE_CAP,
    UPDATES_PER_ARM,
    _direction_with_damage_reference,
    _losses_and_additions,
    build_no_training_integration,
    build_schedule,
    cross_arm_performance_eligible,
    validate_integration_config,
    validate_termination_receipt,
    write_no_training_receipt,
)
from s09_e010_support_amplitude import (
    ARM_A25,
    ARM_ORDER,
    three_arm_direction,
)
from s09_e009_four_arm import parameter_state_sha256
from s09_stage0a_p1_packet import sha256_file
from test_s09_stage0a_p1_runner import packet_fixture


INTEGRATION_CONFIG = (
    ROOT / "docs/research/S09/S09-E010/runner_integration_config_20261018.json"
)


def synthetic_integration_config(tmp_path: Path, base_config: Path) -> Path:
    config = json.loads(INTEGRATION_CONFIG.read_text())
    config["source"]["base_runtime_config_sha256"] = sha256_file(base_config)
    path = tmp_path / "integration.json"
    path.write_text(json.dumps(config))
    return path


def build_bundle(tmp_path: Path, monkeypatch):
    packet, base_config, _ = packet_fixture(tmp_path)
    config = synthetic_integration_config(tmp_path, base_config)
    calls = []

    def reject_step(_self, *_args, **_kwargs):
        calls.append(True)
        raise AssertionError("no-training integration called AdamW.step")

    monkeypatch.setattr(torch.optim.AdamW, "step", reject_step)
    bundle = build_no_training_integration(
        packet_dir=packet,
        base_config_path=base_config,
        integration_config_path=config,
        device=torch.device("cpu"),
        synthetic_test_adapter=True,
    )
    assert calls == []
    return bundle, base_config


def test_schedule_and_budget_are_exactly_three_by_500():
    schedule = build_schedule()
    assert len(schedule) == UPDATES_PER_ARM == 500
    assert TOTAL_UPDATE_CAP == len(ARM_ORDER) * len(schedule) == 1500
    assert schedule[:16] == EXPECTED_CYCLES
    assert schedule[496:] == (1, 2, 3, 4)
    assert EVALUATION_UPDATES == (0, 16, 64, 128, 256, 496, 500)


def test_no_training_build_isolates_three_arms_and_never_steps(tmp_path, monkeypatch):
    bundle, _ = build_bundle(tmp_path, monkeypatch)
    receipt = bundle.receipt
    assert receipt["verdict"] == "NO_TRAINING_INTEGRATION_PASS"
    assert receipt["execution_authorized"] is False
    assert receipt["optimizer_step_performed"] is False
    assert receipt["model_hashes_unchanged"] is True
    assert receipt["optimizer_states_empty_after_direction_preflight"] is True
    assert tuple(receipt["arm_order"]) == ARM_ORDER
    assert len(set(receipt["isolation"]["initial_state_sha256"].values())) == 1
    assert receipt["isolation"]["parameter_and_buffer_objects_disjoint"] is True
    assert receipt["isolation"]["optimizer_states_empty"] is True
    assert receipt["isolation"]["optimizer_parameters_match_arm_models"] is True
    assert len({id(optimizer) for optimizer in bundle.optimizers.values()}) == 3
    assert all(not optimizer.state for optimizer in bundle.optimizers.values())
    assert all(
        record["clip_count_for_complete_direction"] == 1
        for record in receipt["directions"].values()
    )
    assert receipt["directions"][ARM_A25]["exact_e009_a25_replay"] is True
    json.dumps(receipt, allow_nan=False)


def test_runner_directions_match_reviewed_core_for_all_48_arm_cycle_pairs(tmp_path):
    packet, base_config, _ = packet_fixture(tmp_path)
    config = synthetic_integration_config(tmp_path, base_config)
    bundle = build_no_training_integration(
        packet_dir=packet,
        base_config_path=base_config,
        integration_config_path=config,
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
            atomic_expected, additions_expected, _ = _losses_and_additions(
                expected_runtime, index
            )
            if arm == ARM_A25:
                expected, expected_record = e009_arm_direction(
                    expected_model, atomic_expected, ARM_ANCHOR_25
                )
            else:
                expected, expected_record = three_arm_direction(
                    expected_model, atomic_expected, additions_expected, arm
                )

            atomic, additions, _ = _losses_and_additions(runtime, index)
            observed, g_d, observed_record = _direction_with_damage_reference(
                runtime.model, atomic, additions, arm
            )
            torch.testing.assert_close(observed, expected, rtol=0, atol=0)
            assert (
                observed_record["layout"]["parameter_order"]
                == expected_record["layout"]["parameter_order"]
            )
            assert g_d.shape == observed.shape and torch.isfinite(g_d).all()
            runtime.model.zero_grad(set_to_none=True)
        assert parameter_state_sha256(runtime.model) == before


def test_config_is_bound_and_fails_closed_on_leakage_or_budget_drift(tmp_path):
    config = json.loads(INTEGRATION_CONFIG.read_text())
    base = ROOT / config["source"]["base_runtime_config"]
    assert sha256_file(base) == EXPECTED_BASE_RUNTIME_CONFIG_SHA256
    validate_integration_config(config, base_config_path=base)

    config["data"]["target_derived_inference_fields"] = ["support_mask"]
    with pytest.raises(ValueError, match="leakage"):
        validate_integration_config(config, base_config_path=base)
    config = json.loads(INTEGRATION_CONFIG.read_text())
    config["budget"]["total_update_cap"] = 2000
    with pytest.raises(ValueError, match="budget"):
        validate_integration_config(config, base_config_path=base)


def test_config_rejects_execution_authorisation_and_receipt_write_is_one_shot(
    tmp_path, monkeypatch
):
    packet, base_config, _ = packet_fixture(tmp_path / "fixture")
    config_path = synthetic_integration_config(tmp_path, base_config)
    config = json.loads(config_path.read_text())
    config["execution_authorized"] = True
    with pytest.raises(PermissionError, match="unauthorised"):
        validate_integration_config(
            config, base_config_path=base_config, synthetic_test_adapter=True
        )

    bundle, _ = build_bundle(tmp_path / "bundle", monkeypatch)
    output = tmp_path / "receipt.json"
    write_no_training_receipt(bundle, output)
    assert json.loads(output.read_text()) == bundle.receipt
    with pytest.raises(ValueError, match="already exists"):
        write_no_training_receipt(bundle, output)


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
        "artifacts": {"checkpoint_update500.pt": "sha256"},
    }
    if state == TERMINAL_EXECUTION_FAILED:
        receipt.update(
            stop_update=128,
            optimizer_steps_completed=127,
            fully_logged_updates=126,
            evaluation_updates_present=[0, 16, 64],
            last_valid_evaluation_update=64,
            reason="NONFINITE_GRADIENT",
            update500_checkpoint_present=False,
            finite_status=False,
            artifacts={},
        )
    elif state == TERMINAL_METHOD_INAPPLICABLE:
        receipt.update(
            stop_update=64,
            optimizer_steps_completed=63,
            fully_logged_updates=63,
            evaluation_updates_present=[0, 16],
            last_valid_evaluation_update=16,
            reason="ANCHOR_STATIONARY_OR_INAPPLICABLE",
            update500_checkpoint_present=False,
            artifacts={},
        )
    return receipt


@pytest.mark.parametrize(
    ("state", "arm"),
    [
        (TERMINAL_COMPLETED, ARM_ORDER[0]),
        (TERMINAL_EXECUTION_FAILED, ARM_ORDER[1]),
        (TERMINAL_METHOD_INAPPLICABLE, ARM_ORDER[2]),
    ],
)
def test_terminal_receipt_states(state, arm):
    validate_termination_receipt(terminal_receipt(state, arm))


def test_terminal_receipt_rejects_fabricated_final_checkpoint():
    receipt = terminal_receipt(TERMINAL_EXECUTION_FAILED, ARM_ORDER[1])
    receipt["update500_checkpoint_present"] = True
    receipt["artifacts"]["checkpoint_update500.pt"] = "sha256"
    with pytest.raises(ValueError, match="requires complete"):
        validate_termination_receipt(receipt)


def test_cross_arm_claim_requires_both_identity_and_exact_replay():
    assert cross_arm_performance_eligible(
        shared_identity_pass=True, exact_a25_replay_pass=True
    )
    assert not cross_arm_performance_eligible(
        shared_identity_pass=True, exact_a25_replay_pass=False
    )
    assert not cross_arm_performance_eligible(
        shared_identity_pass=False, exact_a25_replay_pass=True
    )
