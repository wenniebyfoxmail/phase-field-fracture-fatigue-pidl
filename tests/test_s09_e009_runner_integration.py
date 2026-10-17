import copy
import json
import sys
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e009_four_arm import ARM_ORDER, arm_direction, atomic_losses, parameter_state_sha256
from s09_e009_runner_integration import (
    EVALUATION_UPDATES,
    EXPECTED_CYCLES,
    TOTAL_UPDATE_CAP,
    UPDATES_PER_ARM,
    _direction_with_damage_reference,
    build_no_training_integration,
    build_schedule,
    validate_integration_config,
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
    assert all(record["clip_count_for_complete_direction"] == 1
               for record in receipt["directions"].values())
    json.dumps(receipt, allow_nan=False)


@pytest.mark.parametrize("arm", ARM_ORDER)
def test_runner_direction_matches_reviewed_core_exactly(tmp_path: Path, arm: str):
    packet, base_config, _ = packet_fixture(tmp_path)
    integration_config = synthetic_integration_config(tmp_path, base_config)
    bundle = build_no_training_integration(
        packet_dir=packet,
        base_config_path=base_config,
        integration_config_path=integration_config,
        device=torch.device("cpu"),
    )
    runtime = bundle.arm_runtimes[arm]
    expected_model = copy.deepcopy(runtime.model)
    expected_runtime = copy.copy(runtime)
    expected_runtime.model = expected_model
    losses, _ = atomic_losses(expected_runtime, index=0)
    expected, expected_diagnostic = arm_direction(expected_model, losses, arm)

    before = parameter_state_sha256(runtime.model)
    losses, _ = atomic_losses(runtime, index=0)
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


def test_config_freezes_complete_evidence_manifest():
    config = json.loads(INTEGRATION_CONFIG.read_text())
    assert config["evidence"]["required_per_arm"] == [
        "start_identity.json", "train_log.jsonl", "gradient_diagnostics.jsonl",
        "diagnostic_metrics.jsonl", "checkpoint_update500.pt", "termination_receipt.json",
    ]
    assert config["evidence"]["required_shared"][-4:] == [
        "decision_figure.png", "per_cycle_metrics.csv", "decision.md",
        "completion_receipt.json",
    ]
