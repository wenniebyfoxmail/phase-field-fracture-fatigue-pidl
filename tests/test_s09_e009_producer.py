import copy
from dataclasses import replace
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

import s09_e009_producer as producer
from s09_e009_four_arm import (
    ARM_ANCHOR_0,
    ARM_ORDER,
    ARM_REPLAY,
    AnchorStationary,
    LOSS_ORDER,
    amplitude_auc,
    group_amplitude_ratio,
)
from s09_e009_producer import (
    EXPECTED_PACKET_MANIFEST_SHA256,
    EXPECTED_PROTOCOL_CONTRACT_SHA256,
    GROWTH_CYCLES,
    HARD_CONSTRAINT_KEYS,
    NEAR_STAGNANT_CYCLES,
    REPLAY_GRADIENT_PREFIX_SHA256,
    REPLAY_REFERENCE,
    TorchArmAdapter,
    _read_gradient_summary,
    _protocol_contract_sha256,
    _replay_direction_with_legacy,
    evaluate_arm,
    replay_validity,
    resolve_producer_config,
    run_arm_state_machine,
    validate_resolved_config,
    write_shared_evidence,
)
from s09_e009_runner_integration import (
    EVALUATION_UPDATES,
    EXPECTED_CYCLES,
    _direction_with_damage_reference,
)
from s09_stage0a_p1_trainer import build_runtime
from s09_stage0a_p1_packet import canonical_json
from test_s09_stage0a_p1_runner import packet_fixture


INTEGRATION_CONFIG = (
    ROOT / "docs/research/S09/S09-E009/runner_integration_config_20261017.json"
)
BASE_CONFIG = ROOT / "docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json"
PROTOCOL = ROOT / "docs/research/S09/S09-E009/experiment.md"


@pytest.fixture(autouse=True)
def reject_real_optimizer_step(monkeypatch):
    calls = []

    def reject(_self, *_args, **_kwargs):
        calls.append(True)
        raise AssertionError("producer-package test called AdamW.step")

    monkeypatch.setattr(torch.optim.AdamW, "step", reject)
    yield calls
    assert calls == []


def _hard_counts():
    return {name: 0 for name in HARD_CONSTRAINT_KEYS}


def _evaluation(update: int, arm: str = ARM_REPLAY):
    reference = REPLAY_REFERENCE.get(update, {}) if arm == ARM_REPLAY else {}
    g = float(reference.get("G", 0.0003 if arm != ARM_REPLAY else 0.0006))
    f = float(reference.get("F", 0.0001 if arm != ARM_REPLAY else 0.0002))
    judge = float(reference.get("L_judge", 0.5 if arm != ARM_REPLAY else 0.8))
    persistence = float(reference.get("persistence", 0.0005017354462152066))
    per_cycle = []
    for index, cycle in enumerate(EXPECTED_CYCLES):
        group = (
            "growth" if cycle in GROWTH_CYCLES else
            "near_stagnant" if cycle in NEAR_STAGNANT_CYCLES else "other"
        )
        per_cycle.append({
            "update": update,
            "cycle": cycle,
            "group": group,
            "predicted_damage_increment_abs_mean": 0.01 + index * 1e-5,
            "true_damage_increment_abs_mean": persistence,
            "damage_increment_mae": g,
            "false_growth": f,
            "predicted_target_spatial_correlation": 0.5,
            "L_judge": judge,
            "atomic_losses": {name: 0.5 for name in LOSS_ORDER},
            "grouped_losses": {"L_D": 1.0, "L_U": 0.5, "L_H": 1.0, "L_P": 0.5},
            "projection_counts": {
                "damage_lower_projection_count": 0,
                "damage_upper_projection_count": 0,
                "alpha_relu_saturation_count": 0,
            },
            "hard_constraint_counts": _hard_counts(),
        })
    growth_pred = [row["predicted_damage_increment_abs_mean"] for row in per_cycle
                   if row["group"] == "growth"]
    stagnant_pred = [row["predicted_damage_increment_abs_mean"] for row in per_cycle
                     if row["group"] == "near_stagnant"]
    predicted = [row["predicted_damage_increment_abs_mean"] for row in per_cycle]
    truth = [row["true_damage_increment_abs_mean"] for row in per_cycle]
    pairwise_values = [0.2] * 120
    aggregate = {
        "update": update,
        "finite": True,
        "G": g,
        "F": f,
        "persistence": persistence,
        "L_judge": judge,
        "amplitude_ratio": group_amplitude_ratio(
            float(np.mean(growth_pred)), float(np.mean(stagnant_pred))),
        "amplitude_auc": amplitude_auc(growth_pred, stagnant_pred),
        "amplitude_pearson": producer._pearson(predicted, truth),
        "amplitude_spearman": producer._pearson(
            producer._average_ranks(predicted), producer._average_ranks(truth)),
        "spatial": {"primary_median": 0.5, "primary_status": "DEFINED",
                    "valid_count": 16, "valid_cycles": list(EXPECTED_CYCLES),
                    "valid_subset_median": 0.5},
        "predicted_field_pairwise_correlation": {
            "pair_count": 120, "valid_pair_count": 120, "na_pair_count": 0,
            "values": pairwise_values,
            "median": 0.2, "minimum": 0.2, "maximum": 0.2,
        },
        "hard_constraint_counts": _hard_counts(),
        "hard_constraint_violations": 0,
        **{name: 0.5 for name in LOSS_ORDER},
        "L_D": 1.0,
        "L_U": 0.5,
        "L_H": 1.0,
        "L_P": 0.5,
    }
    return {"aggregate": aggregate, "per_cycle": per_cycle}


class MockAdapter:
    packet_manifest_sha256 = "packet"
    initial_state_sha256 = "initial"
    hard_constraint_counts = _hard_counts()

    def __init__(self, arm: str, fail_at: int | None = None,
                 stationary_at: int | None = None):
        self.arm = arm
        self.fail_at = fail_at
        self.stationary_at = stationary_at
        self.optimizer_steps_completed = 0

    def evaluate(self, update: int):
        return _evaluation(update, self.arm)

    def step(self, update: int, cycle: int):
        if self.stationary_at == update:
            raise AnchorStationary("ANCHOR_STATIONARY_OR_INAPPLICABLE")
        self.optimizer_steps_completed += 1
        if self.fail_at == update:
            raise RuntimeError("post-step logging failure")
        diagnostic = (
            {"arm": ARM_REPLAY, "clip_count_for_complete_direction": 1,
             "layout": {"parameter_order": ["p"]},
             "exact_replay_merger": {
                 "merged_norm_before_clip": 2.0,
                 "merged_norm_after_clip": 1.0,
             }}
            if self.arm == ARM_REPLAY else
            {"arm": self.arm, "clip_count_for_complete_direction": 1,
             "clip_applied": False, "layout": {"parameter_order": ["p"]}}
        )
        return {
            "train_row": {"update": update, "cycle": cycle},
            "gradient_row": {
                "update": update,
                "cycle": cycle,
                "direction_diagnostics": diagnostic,
                "parameter_displacement_alignment": {
                    "g_D_dot_negative_delta_theta": 1.0,
                    "cosine": 0.5,
                    "displacement_norm": 0.1,
                },
            },
            "legacy_gradient_row": {"update": update, "cycle": cycle, "legacy": True},
        }

    def save_checkpoint(self, path: Path, update: int):
        path.write_bytes(f"checkpoint-{update}".encode())


def test_state_machine_completes_exact_schedule_without_adamw_step(tmp_path: Path):
    result = run_arm_state_machine(
        arm=ARM_REPLAY,
        adapter=MockAdapter(ARM_REPLAY),
        arm_dir=tmp_path / "R",
    )
    assert result.receipt["terminal_state"] == "COMPLETED"
    assert result.receipt["optimizer_steps_completed"] == 500
    assert result.receipt["fully_logged_updates"] == 500
    assert result.receipt["evaluation_updates_present"] == list(EVALUATION_UPDATES)
    assert len((result.arm_dir / "gradient_diagnostics.jsonl").read_text().splitlines()) == 500


def test_state_machine_preserves_post_step_failure_count_and_anchor_state(tmp_path: Path):
    failed = run_arm_state_machine(
        arm=ARM_REPLAY,
        adapter=MockAdapter(ARM_REPLAY, fail_at=17),
        arm_dir=tmp_path / "failed",
    )
    assert failed.receipt["terminal_state"] == "EXECUTION_FAILED"
    assert failed.receipt["stop_update"] == 17
    assert failed.receipt["optimizer_steps_completed"] == 17
    assert failed.receipt["fully_logged_updates"] == 16
    assert failed.receipt["last_valid_evaluation_update"] == 16

    stationary = run_arm_state_machine(
        arm=ARM_ANCHOR_0,
        adapter=MockAdapter(ARM_ANCHOR_0, stationary_at=17),
        arm_dir=tmp_path / "stationary",
    )
    assert stationary.receipt["terminal_state"] == "METHOD_INAPPLICABLE"
    assert stationary.receipt["optimizer_steps_completed"] == 16
    assert stationary.receipt["fully_logged_updates"] == 16


def test_failed_arm_gradient_summary_preserves_confirmed_prefix_and_tail(tmp_path: Path):
    failed = run_arm_state_machine(
        arm=ARM_REPLAY,
        adapter=MockAdapter(ARM_REPLAY, fail_at=17),
        arm_dir=tmp_path / "failed-tail",
    )
    tail = MockAdapter(ARM_REPLAY).step(17, EXPECTED_CYCLES[0])["gradient_row"]
    with (failed.arm_dir / "gradient_diagnostics.jsonl").open("ab") as stream:
        stream.write(canonical_json(tail))
    summary = _read_gradient_summary(failed)
    assert summary["summary_status"] == "CONFIRMED_PREFIX_SUMMARISED"
    assert summary["logged_updates"] == 16
    assert summary["unconfirmed_tail_line_count"] == 1
    assert summary["unconfirmed_tail_parseable_line_count"] == 1


def test_evidence_close_failure_still_writes_checkpoint_bound_receipt(tmp_path: Path,
                                                                     monkeypatch):
    def fail_hashing(*_args, **_kwargs):
        raise OSError("injected artifact hash failure")

    monkeypatch.setattr(producer, "_artifact_hashes", fail_hashing)
    result = run_arm_state_machine(
        arm=ARM_REPLAY,
        adapter=MockAdapter(ARM_REPLAY),
        arm_dir=tmp_path / "evidence-close-failure",
    )
    assert result.receipt["terminal_state"] == "EXECUTION_FAILED"
    assert result.receipt["reason"].startswith("EVIDENCE_CLOSE_FAILED")
    assert result.receipt["optimizer_steps_completed"] == 500
    assert result.receipt["fully_logged_updates"] == 500
    assert result.receipt["update500_checkpoint_present"] is True
    assert result.receipt["artifacts"]["checkpoint_update500.pt"]
    assert (result.arm_dir / "termination_receipt.json").is_file()


def test_evaluator_emits_full_fixed_support_scorecard_without_step(tmp_path: Path):
    packet, base_config, _ = packet_fixture(tmp_path)
    runtime = build_runtime(
        packet_dir=packet,
        config_path=base_config,
        device=torch.device("cpu"),
        executable=False,
    )
    observed = evaluate_arm(runtime, update=0)
    assert [row["cycle"] for row in observed["per_cycle"]] == list(EXPECTED_CYCLES)
    assert len(observed["per_cycle"]) == 16
    assert set(LOSS_ORDER).issubset(observed["aggregate"])
    assert observed["aggregate"]["hard_constraint_violations"] == 0
    json.dumps(observed, allow_nan=False)


@pytest.mark.parametrize("mutation, message", [
    (lambda record: record["aggregate"].__setitem__("amplitude_auc", {}),
     "amplitude AUC"),
    (lambda record: record["aggregate"]["amplitude_auc"].update(
        {"value": 1.0, "wins": 25, "ties": 0, "losses": 0}),
     "amplitude AUC"),
    (lambda record: record["per_cycle"][0].__setitem__(
        "predicted_target_spatial_correlation", None),
     "spatial aggregate"),
    (lambda record: record["aggregate"]["predicted_field_pairwise_correlation"]
        ["values"].pop(), "pairwise field distribution schema"),
])
def test_evaluation_validator_rejects_nested_scorecard_drift(mutation, message):
    record = _evaluation(0)
    mutation(record)
    with pytest.raises(ValueError, match=message):
        producer._validate_evaluation_record(record, 0)


def test_evaluation_validator_rejects_false_defined_zero_amplitude_ratio():
    record = _evaluation(0)
    for row in record["per_cycle"]:
        row["predicted_damage_increment_abs_mean"] = 0.0
    record["aggregate"]["amplitude_auc"] = amplitude_auc([0.0] * 5, [0.0] * 5)
    record["aggregate"]["amplitude_pearson"] = None
    record["aggregate"]["amplitude_spearman"] = None
    record["aggregate"]["amplitude_ratio"] = {"value": 1.0, "status": "DEFINED"}
    with pytest.raises(ValueError, match="amplitude ratio"):
        producer._validate_evaluation_record(record, 0)


def _losses(model: torch.nn.Module):
    p = model.weight.reshape(-1)
    return {
        "l_d": p.square().sum(),
        "l_dr": (p[0] - 0.3).square(),
        "l_u": (p[1] + 0.2).square(),
        "l_h": (p.sum() - 0.1).square(),
        "l_hr": (p[0] - p[1]).square(),
        "L_P": (2 * p[0] + p[1]).square(),
    }


def test_replay_direction_and_legacy_record_match_reviewed_runner():
    left = torch.nn.Linear(2, 1, bias=False, dtype=torch.float64)
    with torch.no_grad():
        left.weight.copy_(torch.tensor([[0.4, -0.1]], dtype=torch.float64))
    right = copy.deepcopy(left)
    observed, observed_gd, _, legacy = _replay_direction_with_legacy(left, _losses(left))
    expected, expected_gd, _ = _direction_with_damage_reference(
        right, _losses(right), ARM_REPLAY)
    torch.testing.assert_close(observed, expected, rtol=0, atol=0)
    torch.testing.assert_close(observed_gd, expected_gd, rtol=0, atol=0)
    json.dumps(legacy, allow_nan=False)


def test_replay_direction_rejects_nonfinite_combined_objective_before_autograd():
    model = torch.nn.Linear(2, 1, bias=False, dtype=torch.float64)
    base = model.weight.sum()
    losses = {name: base + 1e308 for name in LOSS_ORDER}
    with pytest.raises(FloatingPointError, match="nonfinite replay objective"):
        _replay_direction_with_legacy(model, losses)


def test_exact_constant_weighted_correlation_is_na():
    left = torch.tensor([0.1, 0.1, 0.1], dtype=torch.float64)
    right = torch.tensor([0.2, 0.2, 0.2], dtype=torch.float64)
    weight = torch.tensor([1.0, 2.0, 3.0], dtype=torch.float64)
    assert producer._weighted_correlation(left, right, weight) is None


def test_torch_adapter_rejects_hard_constraint_violation_before_step(tmp_path: Path,
                                                                     monkeypatch):
    packet, base_config, _ = packet_fixture(tmp_path)
    runtime = build_runtime(
        packet_dir=packet,
        config_path=base_config,
        device=torch.device("cpu"),
        executable=False,
    )

    class FakeOptimizer:
        def __init__(self):
            self.step_calls = 0

        def zero_grad(self, set_to_none=True):
            assert set_to_none is True

        def step(self):
            self.step_calls += 1

    fake = FakeOptimizer()
    violated = _hard_counts()
    violated["damage_irreversibility"] = 1
    monkeypatch.setattr(producer, "hard_constraint_report", lambda *_args: violated)
    adapter = TorchArmAdapter(
        arm=ARM_REPLAY,
        runtime=runtime,
        optimizer=fake,
        config_sha256="config",
    )
    before = copy.deepcopy(runtime.model.state_dict())
    with pytest.raises(ValueError, match="per-update hard-constraint"):
        adapter.step(1, EXPECTED_CYCLES[0])
    assert fake.step_calls == 0
    assert adapter.optimizer_steps_completed == 0
    assert adapter.hard_constraint_counts == violated
    for name, value in runtime.model.state_dict().items():
        torch.testing.assert_close(value, before[name], rtol=0, atol=0)


def test_state_machine_preserves_failed_update_hard_constraint_counts(tmp_path: Path):
    class HardViolationAdapter(MockAdapter):
        def step(self, update: int, cycle: int):
            self.hard_constraint_counts = _hard_counts()
            self.hard_constraint_counts["damage_irreversibility"] = 1
            raise ValueError("per-update hard-constraint violation")

    result = run_arm_state_machine(
        arm=ARM_REPLAY,
        adapter=HardViolationAdapter(ARM_REPLAY),
        arm_dir=tmp_path / "hard-violation",
    )
    assert result.receipt["terminal_state"] == "EXECUTION_FAILED"
    assert result.receipt["optimizer_steps_completed"] == 0
    assert result.receipt["fully_logged_updates"] == 0
    assert result.receipt["hard_constraint_counts"]["damage_irreversibility"] == 1


def test_real_forward_hard_constraint_failure_reaches_termination_receipt(
        tmp_path: Path, monkeypatch):
    packet, base_config, _ = packet_fixture(tmp_path)
    runtime = build_runtime(
        packet_dir=packet,
        config_path=base_config,
        device=torch.device("cpu"),
        executable=False,
    )

    class FakeOptimizer:
        def __init__(self):
            self.step_calls = 0

        def zero_grad(self, set_to_none=True):
            assert set_to_none is True

        def step(self):
            self.step_calls += 1
            raise AssertionError("hard-constraint failure reached optimizer.step")

    fake = FakeOptimizer()
    adapter = TorchArmAdapter(
        arm=ARM_REPLAY,
        runtime=runtime,
        optimizer=fake,
        config_sha256="config",
    )
    original_forward = runtime.model.forward
    calls = 0

    def violate_first_update(*args, **kwargs):
        nonlocal calls
        calls += 1
        output = original_forward(*args, **kwargs)
        if calls == len(EXPECTED_CYCLES) + 1:
            output = dict(output)
            u_peak = output["u_peak"].clone()
            boundary_index = int(torch.nonzero(
                runtime.graph["boundary"], as_tuple=False)[0])
            u_peak[boundary_index, 0] += 1.0
            output["u_peak"] = u_peak
        return output

    monkeypatch.setattr(runtime.model, "forward", violate_first_update)
    result = run_arm_state_machine(
        arm=ARM_REPLAY,
        adapter=adapter,
        arm_dir=tmp_path / "real-forward-hard-violation",
    )
    assert calls == len(EXPECTED_CYCLES) + 1
    assert fake.step_calls == 0
    assert result.receipt["terminal_state"] == "EXECUTION_FAILED"
    assert result.receipt["optimizer_steps_completed"] == 0
    assert result.receipt["fully_logged_updates"] == 0
    assert result.receipt["hard_constraint_counts"]["peak_boundary_lifting"] == 1


def test_protocol_projection_ignores_only_frontmatter_status(tmp_path: Path):
    assert _protocol_contract_sha256(PROTOCOL) == EXPECTED_PROTOCOL_CONTRACT_SHA256
    raw = PROTOCOL.read_text()
    changed_status = raw.replace("status: READY_FOR_BOUNDED_LOCAL_IMPLEMENTATION",
                                 "status: DIFFERENT_WORKFLOW_STATE", 1)
    status_path = tmp_path / "status.md"
    status_path.write_text(changed_status)
    assert _protocol_contract_sha256(status_path) == EXPECTED_PROTOCOL_CONTRACT_SHA256
    body_path = tmp_path / "body.md"
    body_path.write_text(changed_status + "\nstatus: method text must remain frozen\n")
    assert _protocol_contract_sha256(body_path) != EXPECTED_PROTOCOL_CONTRACT_SHA256


def test_resolver_binds_exact_snapshots_environment_packet_and_commit(tmp_path: Path,
                                                                      monkeypatch):
    commit = "a" * 40
    environment = {
        "hostname": "approved-host",
        "platform": "linux",
        "python": "python",
        "torch": "torch",
        "cuda": "cuda",
        "gpu": {"uuid": "gpu-uuid", "pci_bus_id": "0000:01:00.0", "name": "GPU"},
        "CUDA_VISIBLE_DEVICES": "0",
    }
    base = json.loads(BASE_CONFIG.read_text())
    arrays = {
        "cycles": np.asarray(EXPECTED_CYCLES),
        "d_pre": np.empty((16, base["data"]["native_nodes"])),
        "history_pre": np.empty((16, base["data"]["native_q4_elements"], 1, 4)),
    }
    metadata = {
        "config_sha256": producer.EXPECTED_BASE_RUNTIME_CONFIG_SHA256,
        "source_p1_verdict": "P1_CONTRACT_FROZEN",
        "source_hash_verdict": "FULL_TRAJECTORY_HASH_QUALIFIED",
        "source_decode_verdict": "FULL_TRAJECTORY_DECODE_QUALIFIED",
    }
    identity = {"manifest_sha256": EXPECTED_PACKET_MANIFEST_SHA256}
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(producer, "current_commit", lambda _root: commit)
    monkeypatch.setattr(producer, "_producer_execution_files_clean", lambda _root: True)
    monkeypatch.setattr(producer, "_environment_snapshot", lambda _visible: environment)
    monkeypatch.setattr(producer, "load_verified_packet",
                        lambda _packet: (arrays, metadata, identity))
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    staging = tmp_path / "staging"
    staging.mkdir()
    output = staging / "resolved.json"
    resolved = resolve_producer_config(
        packet_dir=tmp_path / "packet",
        integration_config_path=INTEGRATION_CONFIG,
        base_runtime_config_path=BASE_CONFIG,
        protocol_path=PROTOCOL,
        output_path=output,
        repo_root=ROOT,
        approved_producer_commit=commit,
        approved_hostname="approved-host",
        approved_gpu_name="GPU",
        approved_gpu_uuid="gpu-uuid",
        approved_gpu_pci_bus_id="0000:01:00.0",
        approved_staging_root=staging,
        authorize_execution=True,
    )
    assert output.is_file()
    assert resolved["execution_authorized"] is True
    assert resolved["source"]["training_commit"] == commit
    reread = producer._parse_strict_json_bytes(output.read_bytes())
    validate_resolved_config(
        reread,
        base_runtime_config_path=BASE_CONFIG,
        packet_manifest_sha256=EXPECTED_PACKET_MANIFEST_SHA256,
        executable=True,
    )
    unauthorised = copy.deepcopy(reread)
    unauthorised["execution_authorized"] = False
    with pytest.raises(PermissionError, match="execution is not authorised"):
        validate_resolved_config(
            unauthorised,
            base_runtime_config_path=BASE_CONFIG,
            packet_manifest_sha256=EXPECTED_PACKET_MANIFEST_SHA256,
            executable=True,
        )
    tampered = copy.deepcopy(reread)
    tampered["source"]["training_commit"] = "b" * 40
    with pytest.raises(ValueError, match="not bound"):
        validate_resolved_config(
            tampered,
            base_runtime_config_path=BASE_CONFIG,
            packet_manifest_sha256=EXPECTED_PACKET_MANIFEST_SHA256,
            executable=False,
        )


def test_public_execution_entry_rejects_caller_controlled_other_repo(tmp_path: Path):
    with pytest.raises(ValueError, match="repo root differs"):
        producer.run_producer(
            packet_dir=tmp_path / "packet",
            resolved_config_path=tmp_path / "missing.json",
            base_runtime_config_path=BASE_CONFIG,
            output_dir=tmp_path / "output",
            repo_root=tmp_path,
        )


def test_consumed_runtime_packet_identity_is_checked_before_optimizer_boundary():
    config = {"source": {"input_packet_sha256": EXPECTED_PACKET_MANIFEST_SHA256}}
    runtime = type("RuntimeFixture", (), {
        "packet_identity": {"manifest_sha256": "different-consumed-packet"}
    })()
    with pytest.raises(ValueError, match="consumed runtime packet identity"):
        producer._validated_runtime_packet_identity(runtime, config)


def test_numeric_replay_gate_does_not_fail_on_new_stream_hash_diagnostic(tmp_path: Path):
    result = run_arm_state_machine(
        arm=ARM_REPLAY,
        adapter=MockAdapter(ARM_REPLAY),
        arm_dir=tmp_path / "numeric-replay",
    )
    result = replace(result, legacy_gradient_prefix_sha256="different-new-stream-hash")
    verdict = replay_validity(result)
    assert verdict["pass"] is True
    assert verdict["new_stream_hash_matches_archived_reference"] is False
    assert "first_500_legacy_gradient_rows_sha256" not in verdict["clauses"]


def test_writer_emits_complete_decision_package_from_exact_mock_receipts(tmp_path: Path):
    results = {}
    for arm in ARM_ORDER:
        results[arm] = run_arm_state_machine(
            arm=arm,
            adapter=MockAdapter(arm),
            arm_dir=tmp_path / arm,
        )
    results[ARM_REPLAY] = replace(
        results[ARM_REPLAY],
        legacy_gradient_prefix_sha256=REPLAY_GRADIENT_PREFIX_SHA256,
    )
    (tmp_path / "config_resolved.json").write_text("{}\n")
    (tmp_path / "input_packet_identity.json").write_text("{}\n")
    (tmp_path / "environment.txt").write_text("fixture\n")
    config = json.loads(INTEGRATION_CONFIG.read_text())
    completion = write_shared_evidence(
        output_dir=tmp_path,
        config=config,
        arm_results=results,
        environment={"fixture": True},
        run_metadata={"optimizer_or_training_step_performed_by_test": False},
    )
    assert completion["total_optimizer_steps_completed"] == 2000
    assert completion["decision"]["replay_gate"]["pass"] is True
    assert completion["decision"]["cross_arm_performance_eligible"] is True
    assert set(completion["decision"]["update500_metrics"]) == set(ARM_ORDER)
    assert (tmp_path / "decision_figure.png").stat().st_size > 0
    required = set(config["evidence"]["required_shared"])
    assert required.issubset({path.name for path in tmp_path.iterdir()})


def test_execution_entrypoint_rejects_unauthorised_config_before_artifact_roots(tmp_path: Path):
    config = json.loads(INTEGRATION_CONFIG.read_text())
    config_path = tmp_path / "unresolved.json"
    config_path.write_bytes(canonical_json(config))
    packet = tmp_path / "packet"
    packet.mkdir()
    (packet / "packet_identity.json").write_text(json.dumps({"manifest_sha256": "x"}))
    with pytest.raises(ValueError, match="resolved config path differs"):
        producer.run_producer(
            packet_dir=packet,
            resolved_config_path=config_path,
            base_runtime_config_path=BASE_CONFIG,
            output_dir=tmp_path / "output",
            repo_root=ROOT,
        )
    assert not (tmp_path / "output").exists()
