from collections import OrderedDict
import json
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from s09_e011_ranking_objective import (
    AMPLITUDE_NORMALISER,
    ARM_CONTROL,
    ARM_RANK,
    OBJECTIVE_ORDER,
    PAIR_ORDER,
    PRIMARY_PAIR_SCORE_GAIN,
    classify_e011,
    pair_mean_objectives,
    pair_schedule,
    ranking_direction,
    ranking_loss,
    weighted_amplitude,
)
import s09_e011_producer as producer
from s09_e011_producer import ArmRunResult, _adamw_displacement
from s09_stage0a_p1_packet import canonical_json, sha256_file
from s09_stage0a_p1_trainer import assign_merged_gradient


EVALUATION_FIXTURE = (
    Path(__file__).parent / "fixtures/s09_e011_evaluation_update500.json"
)


def test_pair_schedule_is_fixed_complete_and_repeated_twenty_times():
    schedule = pair_schedule()
    assert len(PAIR_ORDER) == 25
    assert len(schedule) == 500
    assert schedule[:25] == PAIR_ORDER
    assert schedule[-25:] == PAIR_ORDER
    assert all(schedule.count(pair) == 20 for pair in PAIR_ORDER)


def test_ranking_loss_descent_increases_growth_minus_stagnant_margin():
    growth = torch.tensor(2.0e-6, dtype=torch.float64, requires_grad=True)
    stagnant = torch.tensor(3.0e-6, dtype=torch.float64, requires_grad=True)
    loss, record = ranking_loss(growth, stagnant)
    dg, ds = torch.autograd.grad(loss, (growth, stagnant))
    margin_change_under_descent = float((-dg) - (-ds))
    assert record["physical_margin"] == pytest.approx(-1.0e-6)
    assert record["normalised_margin"] == pytest.approx(-1.0e-6 / AMPLITUDE_NORMALISER)
    assert margin_change_under_descent > 0


def test_weighted_amplitude_uses_damage_increment_and_weights():
    peak = torch.tensor([0.1, 0.4], dtype=torch.float64)
    pre = torch.tensor([0.0, 0.2], dtype=torch.float64)
    weight = torch.tensor([1.0, 3.0], dtype=torch.float64)
    assert weighted_amplitude(peak, pre, weight).item() == pytest.approx(0.175)


def _objectives(model):
    p = next(model.parameters()).reshape(-1)
    left = OrderedDict(
        (name, (index + 1.0) * (p.square().sum() + 0.1 * p.sum()))
        for index, name in enumerate(OBJECTIVE_ORDER[:-1])
    )
    right = OrderedDict(
        (name, (index + 0.5) * ((p - 0.2).square().sum() + 0.2 * p.sum()))
        for index, name in enumerate(OBJECTIVE_ORDER[:-1])
    )
    rank = (p[0] - 2.0 * p[1]).square() + 0.25 * p[2]
    return pair_mean_objectives(left, right, rank)


def test_ranking_arm_changes_only_the_single_rank_component():
    model_control = torch.nn.Linear(3, 1, bias=False, dtype=torch.float64)
    model_rank = torch.nn.Linear(3, 1, bias=False, dtype=torch.float64)
    state = {"weight": torch.tensor([[0.2, -0.3, 0.4]], dtype=torch.float64)}
    model_control.load_state_dict(state)
    model_rank.load_state_dict(state)
    control, control_record, _ = ranking_direction(
        model_control, _objectives(model_control), ARM_CONTROL
    )
    ranked, rank_record, _ = ranking_direction(
        model_rank, _objectives(model_rank), ARM_RANK
    )
    assert control_record["rank_coefficient"] == 0.0
    assert rank_record["rank_coefficient"] == 4096.0
    assert rank_record["rank"]["raw_norm"] > 0
    assert not torch.equal(control, ranked)
    assert torch.isfinite(control).all() and torch.isfinite(ranked).all()
    assert control.norm() <= 1.0 + 1e-12
    assert ranked.norm() <= 1.0 + 1e-12


def _metric(wins, ties, losses, **overrides):
    result = {
        "amplitude_auc": {
            "wins": wins,
            "ties": ties,
            "losses": losses,
            "value": (wins + 0.5 * ties) / 25,
        },
        "G": 1.0,
        "F": 1.0,
        "L_P": 1.0,
        "L_judge": 1.0,
    }
    result.update(overrides)
    return result


def test_classifier_uses_one_net_pair_as_exploratory_primary():
    result = classify_e011(
        control=_metric(17, 0, 8),
        ranking=_metric(18, 0, 7),
        validity=True,
    )
    assert PRIMARY_PAIR_SCORE_GAIN == 2
    assert result["primary"]["delta_pair_score"] == 2
    assert result["status"] == "OBJECTIVE_REPAIR_SIGNAL"


def test_classifier_preserves_primary_miss_and_component_ratios():
    result = classify_e011(
        control=_metric(17, 0, 8),
        ranking=_metric(17, 0, 8, F=0.5),
        validity=True,
    )
    assert result["status"] == "NO_REALISED_RANKING_REPAIR"
    assert result["primary"]["passed"] is False
    assert result["protected_ratios"]["F"]["value"] == pytest.approx(0.5)


def test_invalid_result_is_not_scored():
    assert classify_e011(
        control=_metric(17, 0, 8), ranking=_metric(18, 0, 7), validity=False
    ) == {"status": "EXECUTION_INVALID", "validity": False}


def test_analytic_next_adamw_displacement_matches_real_cloned_step():
    model = torch.nn.Linear(3, 1, bias=True, dtype=torch.float64)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=3e-4, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.0
    )
    first = sum(parameter.square().sum() for parameter in model.parameters())
    first.backward()
    optimizer.step()
    clone = torch.nn.Linear(3, 1, bias=True, dtype=torch.float64)
    clone.load_state_dict(model.state_dict())
    clone_optimizer = torch.optim.AdamW(
        clone.parameters(), lr=3e-4, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.0
    )
    clone_optimizer.load_state_dict(optimizer.state_dict())
    names = [name for name, _ in clone.named_parameters()]
    direction = torch.linspace(
        -0.4, 0.7, sum(parameter.numel() for parameter in clone.parameters()),
        dtype=torch.float64,
    )
    predicted = _adamw_displacement(clone, clone_optimizer, direction, names)
    before = torch.cat([parameter.detach().reshape(-1) for parameter in clone.parameters()])
    assign_merged_gradient(clone, direction, names)
    clone_optimizer.step()
    after = torch.cat([parameter.detach().reshape(-1) for parameter in clone.parameters()])
    assert torch.allclose(after - before, predicted, atol=1e-15, rtol=1e-12)


def test_clean_gate_includes_inherited_e009_dependency(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"],
                   cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    path = tmp_path / "source/s09_e009_four_arm.py"
    path.parent.mkdir()
    path.write_text("value = 1\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
    assert producer._execution_files_clean(tmp_path)
    path.write_text("value = 2\n")
    assert not producer._execution_files_clean(tmp_path)


def test_wall_deadline_is_checked_at_close_boundaries():
    with pytest.raises(TimeoutError, match="WALL_TIME_CAP_REACHED:after_evidence"):
        producer._check_deadline(time.time() - 1.0, "after_evidence")


def test_optimizer_step_is_refused_when_direction_crosses_deadline():
    class CountingOptimizer:
        def __init__(self):
            self.steps = 0

        def step(self):
            self.steps += 1

    optimizer = CountingOptimizer()
    with pytest.raises(TimeoutError, match="update_1_pre_step"):
        producer._optimizer_step_before_deadline(
            optimizer, time.time() - 1.0, "control:update_1_pre_step")
    assert optimizer.steps == 0


def test_evaluation_is_registered_only_after_jsonl_flush():
    class FailingStream:
        def write(self, value):
            raise OSError("diagnostic disk unavailable")

        def flush(self):
            raise AssertionError("flush cannot follow failed write")

    evaluations = {}
    with pytest.raises(OSError, match="diagnostic disk unavailable"):
        producer._append_durable_evaluation(
            FailingStream(), evaluations, 16, {"aggregate": {}, "per_cycle": []})
    assert evaluations == {}


def test_checkpoint_cleanup_failure_is_returned_instead_of_escaping():
    class FailingPath:
        def unlink(self, *, missing_ok):
            assert missing_ok is True
            raise PermissionError("arm directory read-only")

    observed = producer._cleanup_partial_checkpoint(FailingPath())
    assert observed == (
        "CHECKPOINT_CLEANUP_FAILED: PermissionError: arm directory read-only"
    )


def test_canonical_evaluation_round_trip_passes_inherited_validator(tmp_path):
    raw = json.loads(EVALUATION_FIXTURE.read_text(encoding="utf-8"))
    ordered = producer._restore_evaluation_key_order(raw)
    producer._validate_evaluation_record(ordered, 500)

    path = tmp_path / "diagnostic_metrics.jsonl"
    durable = {}
    with path.open("wb") as stream:
        producer._append_durable_evaluation(stream, durable, 500, ordered)
    assert list(durable) == [500]

    reloaded = producer._read_jsonl(path)
    assert len(reloaded) == 1
    restored = producer._restore_evaluation_key_order(reloaded[0])
    producer._validate_evaluation_record(restored, 500)


def test_evaluation_order_restore_rejects_unknown_named_metric():
    raw = json.loads(EVALUATION_FIXTURE.read_text(encoding="utf-8"))
    raw["per_cycle"][0]["atomic_losses"]["unexpected"] = 0.0
    with pytest.raises(ValueError, match="atomic losses membership drift"):
        producer._restore_evaluation_key_order(raw)


def test_required_figures_replay_checkpoints_and_match_recorded_amplitudes(
    tmp_path, monkeypatch,
):
    cycles = np.arange(1, 17, dtype=np.int64)
    xy = np.asarray([[0., 0.], [1., 0.], [1., 1.], [0., 1.]])
    weights = np.ones(4)
    common = {
        "cycles": cycles,
        "xy": xy,
        "nodal_weight": weights,
        "d_pre": np.zeros((16, 4)),
        "target_peak": np.full((16, 4), 0.3),
    }
    peaks = {ARM_CONTROL: 0.1, ARM_RANK: 0.2}
    runtimes = {}
    results = {}
    for arm in (ARM_CONTROL, ARM_RANK):
        model = torch.nn.Linear(1, 1, bias=False, dtype=torch.float64)
        runtime = SimpleNamespace(model=model, arm=arm)
        runtimes[arm] = runtime
        arm_dir = tmp_path / arm
        arm_dir.mkdir()
        torch.save({
            "model": model.state_dict(), "optimizer": {}, "update": 500,
            "arm": arm, "source_run": producer.RUN_ID,
        }, arm_dir / "checkpoint_update500.pt")
        rows = [
            {"cycle": int(cycle),
             "predicted_damage_increment_abs_mean": peaks[arm],
             "true_damage_increment_abs_mean": 0.3}
            for cycle in cycles
        ]
        results[arm] = ArmRunResult(
            arm, arm_dir, {}, {500: {"per_cycle": rows}})

    def collect(runtime):
        return {
            **common,
            "predicted_peak": np.full((16, 4), peaks[runtime.arm]),
        }

    monkeypatch.setattr(producer, "_collect_fields", collect)
    artifacts = producer._write_required_figures(
        output=tmp_path, results=results, runtimes=runtimes,
        deadline=time.time() + 60,
    )
    assert set(artifacts) == {
        "field_arrays_update500.npz", "amplitude_trajectory.png",
        "delta_d_fields_all_cycles.png",
    }
    assert all((tmp_path / name).stat().st_size > 0 for name in artifacts)


def _synthetic_completed_arm(tmp_path: Path) -> ArmRunResult:
    arm = ARM_CONTROL
    arm_dir = tmp_path / arm
    arm_dir.mkdir()
    (arm_dir / "start_identity.json").write_bytes(canonical_json({
        "arm": arm, "updates_per_arm": 500,
        "pair_schedule": [list(pair) for pair in pair_schedule()],
    }))
    with (arm_dir / "train_log.jsonl").open("wb") as stream:
        for update in range(1, 501):
            stream.write(canonical_json({"update": update}))
    with (arm_dir / "gradient_diagnostics.jsonl").open("wb") as stream:
        for update in range(1, 501):
            stream.write(canonical_json({"update": update}))
    with (arm_dir / "diagnostic_metrics.jsonl").open("wb") as stream:
        template = json.loads(EVALUATION_FIXTURE.read_text(encoding="utf-8"))
        for update in producer.EVALUATION_UPDATES:
            record = json.loads(json.dumps(template))
            record["aggregate"]["update"] = update
            for row in record["per_cycle"]:
                row["update"] = update
            stream.write(canonical_json(record))
    torch.save({"model": {}, "optimizer": {}, "update": 500, "arm": arm,
                "source_run": producer.RUN_ID},
               arm_dir / "checkpoint_update500.pt")
    names = {
        "start_identity.json", "train_log.jsonl", "gradient_diagnostics.jsonl",
        "diagnostic_metrics.jsonl", "checkpoint_update500.pt",
    }
    receipt = {
        "arm": arm, "terminal_state": "COMPLETED",
        "optimizer_steps_completed": 500, "fully_logged_updates": 500,
        "evaluation_updates_present": list(producer.EVALUATION_UPDATES),
        "last_valid_evaluation_update": 500, "reason": None,
        "update500_checkpoint_present": True, "finite": True,
        "hard_constraint_violations": 0,
        "artifacts": {name: sha256_file(arm_dir / name) for name in names},
    }
    (arm_dir / "termination_receipt.json").write_bytes(canonical_json(receipt))
    return ArmRunResult(arm, arm_dir, receipt, {})


def test_shared_close_rejects_post_receipt_artifact_tamper(tmp_path, monkeypatch):
    result = _synthetic_completed_arm(tmp_path)
    monkeypatch.setattr(producer, "_validate_evaluation_record",
                        lambda record, update: None)
    validated = producer._validate_arm_on_disk(result)
    assert list(validated.evaluations) == list(producer.EVALUATION_UPDATES)
    with (result.arm_dir / "train_log.jsonl").open("ab") as stream:
        stream.write(json.dumps({"update": 501}).encode() + b"\n")
    with pytest.raises(ValueError, match="artifact hash drift"):
        producer._validate_arm_on_disk(result)


def test_shared_close_rejects_float_step_count_even_if_memory_matches(
    tmp_path, monkeypatch,
):
    result = _synthetic_completed_arm(tmp_path)
    result.receipt["optimizer_steps_completed"] = 500.0
    receipt_path = result.arm_dir / "termination_receipt.json"
    receipt_path.write_bytes(canonical_json(result.receipt))
    monkeypatch.setattr(producer, "_validate_evaluation_record",
                        lambda record, update: None)
    with pytest.raises(ValueError, match="invalid completed receipt"):
        producer._validate_arm_on_disk(result)
