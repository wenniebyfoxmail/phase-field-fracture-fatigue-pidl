# ruff: noqa: E402
from __future__ import annotations

from collections import OrderedDict
import ast
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from s09_e014_common_direction import ARM_CANDIDATE, ARM_CONTROL
from s09_e015_trust_region import (
    NONZERO_LAMBDAS,
    actual_displacement,
    classify_grid,
    interpolate_state,
    noncollapsed,
    state_label,
    tensor_bytes_sha256,
)


def _state(nonzero: bool, local: int, global_: int, ratio: float = 1.0):
    return {
        "valid": True,
        "noncollapsed": nonzero,
        "local_pairs": {"score_2W_plus_T": local},
        "global_pairs": {"score_2W_plus_T": global_},
        "metrics": {
            "G": ratio,
            "F": ratio,
            "L_P": ratio,
            "L_judge": ratio,
            "hard_constraint_violations": 0,
        },
    }


def _grid():
    return {
        state_label(arm, fraction): _state(False, 0, 0)
        for arm in (ARM_CONTROL, ARM_CANDIDATE)
        for fraction in NONZERO_LAMBDAS
    }


def test_actual_displacement_and_direct_interior_interpolation():
    base = OrderedDict(
        (
            ("weight", torch.tensor([1.0, 2.0], dtype=torch.float64)),
            ("buffer", torch.tensor([7.0], dtype=torch.float64)),
        )
    )
    endpoint = OrderedDict(
        (
            ("weight", torch.tensor([3.0, 6.0], dtype=torch.float64)),
            ("buffer", torch.tensor([7.0], dtype=torch.float64)),
        )
    )
    displacement = actual_displacement(base, endpoint, ("weight",))
    assert torch.equal(displacement, torch.tensor([2.0, 4.0], dtype=torch.float64))
    assert tensor_bytes_sha256(displacement) == tensor_bytes_sha256(
        displacement.clone()
    )
    state = interpolate_state(base, endpoint, ("weight",), 1 / 4)
    assert torch.equal(state["weight"], torch.tensor([1.5, 3.0], dtype=torch.float64))
    assert torch.equal(state["buffer"], base["buffer"])
    assert state["buffer"].data_ptr() != base["buffer"].data_ptr()
    with pytest.raises(ValueError):
        interpolate_state(base, endpoint, ("weight",), 1.0)


def test_noncollapsed_requires_every_cycle_strictly_positive():
    rows = [
        {"cycle": index, "positive_node_count": 1, "maximum_increment": 1e-30}
        for index in range(16)
    ]
    assert noncollapsed(rows)
    rows[-1]["positive_node_count"] = 0
    assert not noncollapsed(rows)


def test_classification_levels_and_same_lambda_rule():
    states = _grid()
    assert classify_grid(states)["level"] == 2
    fraction = NONZERO_LAMBDAS[0]
    states[state_label(ARM_CONTROL, fraction)] = _state(True, 20, 20)
    assert classify_grid(states)["level"] == 3
    states[state_label(ARM_CANDIDATE, fraction)] = _state(True, 21, 20)
    assert classify_grid(states)["level"] == 5
    states[state_label(ARM_CANDIDATE, fraction)]["metrics"]["G"] = 0.0
    states[state_label(ARM_CONTROL, fraction)]["metrics"]["G"] = 0.0
    assert classify_grid(states)["level"] == 4


def test_local_gain_at_different_lambda_does_not_grant_level4():
    states = _grid()
    first, second = NONZERO_LAMBDAS[:2]
    states[state_label(ARM_CONTROL, first)] = _state(True, 20, 20)
    states[state_label(ARM_CANDIDATE, second)] = _state(True, 21, 20)
    assert classify_grid(states)["level"] == 3


def test_producer_contains_no_optimizer_or_gradient_execution_calls():
    path = ROOT / "source" / "s09_e015_producer.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    banned = {"backward", "grad", "step", "zero_grad"}
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = (
                func.attr
                if isinstance(func, ast.Attribute)
                else (func.id if isinstance(func, ast.Name) else "")
            )
            if name in banned:
                calls.append((name, node.lineno))
    assert calls == []
    text = path.read_text(encoding="utf-8")
    assert "torch.optim" not in text
    assert "torch.autograd" not in text


def test_bound_config_and_protocol_hashes_match_producer_constants():
    import hashlib

    from s09_e015_producer import (
        EXPECTED_PROTOCOL_SHA256,
        EXPECTED_RUN_CONFIG_SHA256,
    )

    config = ROOT / "docs" / "research" / "S09" / "S09-E015" / "run_config.json"
    protocol = ROOT / "docs" / "research" / "S09" / "S09-E015" / "experiment.md"
    assert hashlib.sha256(config.read_bytes()).hexdigest() == EXPECTED_RUN_CONFIG_SHA256
    assert hashlib.sha256(protocol.read_bytes()).hexdigest() == EXPECTED_PROTOCOL_SHA256


def test_additive_replay_tolerance_matches_protocol():
    import s09_e015_producer as producer

    differences = []
    producer._continuous_equal(
        {"G": 0.0010000000015}, {"G": 0.001}, "evaluation", differences
    )
    assert differences == []
    differences = []
    producer._continuous_equal(
        {"G": 0.0010000000021}, {"G": 0.001}, "evaluation", differences
    )
    assert differences and differences[0]["kind"] == "continuous"


def _io_states():
    from s09_e014_common_direction import ARM_ORDER

    cycles = np.arange(16, dtype=np.int64)
    xy = np.asarray([[0.0, 0.0], [1.0, 0.0]], dtype=np.float64)
    weights = np.asarray([1.0, 1.0], dtype=np.float64)
    d_pre = np.zeros((16, 2), dtype=np.float64)
    target = np.full((16, 2), 0.2, dtype=np.float64)
    order = ["B25_step0"] + [
        state_label(arm, fraction) for arm in ARM_ORDER for fraction in NONZERO_LAMBDAS
    ]
    pairs = [
        {
            "growth_cycle": growth,
            "stagnant_cycle": stagnant,
            "margin": 0.0,
            "outcome": "tie",
        }
        for growth in (1, 58, 60, 69, 70)
        for stagnant in (3, 4, 71, 72, 73)
    ]
    states = {}
    for position, label in enumerate(order):
        arm_index = 0 if position == 0 else (position - 1) // len(NONZERO_LAMBDAS)
        fraction_index = 0 if position == 0 else (position - 1) % len(NONZERO_LAMBDAS)
        predicted = np.full((16, 2), position / 1000, dtype=np.float64)
        per_cycle = [
            {
                "update": 0 if label == "B25_step0" else 1,
                "cycle": int(cycle),
                "damage_increment_mae": 0.0,
                "false_growth": 0.0,
            }
            for cycle in cycles
        ]
        cycle_rows = [
            {
                "cycle": int(cycle),
                "weighted_mean_increment": float(position / 1000),
                "maximum_increment": float(position / 1000),
                "positive_node_count": 0 if position == 0 else 2,
                "strict_zero_increment": position == 0,
            }
            for cycle in cycles
        ]
        score_rows = [
            {
                "cycle": int(cycle),
                "global_amplitude": float(position / 1000),
                "local_support_contrast": 0.0,
            }
            for cycle in cycles
        ]
        pair_record = {
            "wins": 0,
            "ties": 25,
            "losses": 0,
            "score_2W_plus_T": 25,
            "pairs": pairs,
        }
        states[label] = {
            "arm": "shared" if position == 0 else ARM_ORDER[arm_index],
            "lambda": 0.0 if position == 0 else NONZERO_LAMBDAS[fraction_index],
            "fields": {
                "cycles": cycles,
                "xy": xy,
                "nodal_weight": weights,
                "d_pre": d_pre,
                "target_peak": target,
                "predicted_peak": predicted,
            },
            "evaluation": {
                "aggregate": {"update": per_cycle[0]["update"]},
                "per_cycle": per_cycle,
            },
            "score_rows": score_rows,
            "cycle_rows": cycle_rows,
            "metrics": {"G": 0.0, "F": 0.0, "L_P": 0.0, "L_judge": 0.0},
            "global_pairs": pair_record,
            "local_pairs": pair_record,
            "noncollapsed": position != 0,
            "valid": True,
        }
    return states, order


def test_full_writer_validator_round_trip_and_npz_shared_array_guard(
    tmp_path, monkeypatch
):
    import matplotlib.pyplot as plt
    import s09_e015_producer as producer

    states, order = _io_states()
    environment = {"hostname": "fixture"}
    source = {"training_commit": "fixture"}
    construction = {"state_count": 13}
    replay = {"valid": True}
    decision = {"classification": {"level": 3}}
    evaluations = producer._evaluation_evidence(states, order)
    for name, value in (
        ("environment.json", environment),
        ("source_identity.json", source),
        ("state_construction_audit.json", construction),
        ("endpoint_replay.json", replay),
        ("decision_metrics.json", decision),
        ("state_evaluations.json", evaluations),
    ):
        producer._write_json(tmp_path / name, value)
    state_csv = producer._render_state_cycle_csv(states, order).encode()
    pair_csv = producer._render_pair_csv(states, order).encode()
    assert b"\r\n" not in state_csv and b"\r\n" not in pair_csv
    assert len(state_csv.splitlines()) - 1 == 208
    assert len(pair_csv.splitlines()) - 1 == 325
    (tmp_path / "state_cycle_metrics.csv").write_bytes(state_csv)
    (tmp_path / "pair_metrics.csv").write_bytes(pair_csv)
    producer._write_field_archive(tmp_path / "all_state_fields.npz", states, order)
    figure_names = (
        "trust_region_decision_curves.png",
        "selected_physical_scale_fields.png",
        "selected_shape_normalised_fields.png",
    )
    for name in figure_names:
        plt.imsave(tmp_path / name, np.zeros((2, 2)), cmap="viridis")
    (tmp_path / "README_analysis.md").write_text("fixture\n")
    figure_hashes = {
        name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
        for name in figure_names
    }
    monkeypatch.setattr(producer, "_require_valid_evaluation", lambda *args: None)
    monkeypatch.setattr(
        producer, "_require_score_evaluation_alignment", lambda *args: None
    )
    monkeypatch.setattr(producer, "_validate_source_closure", lambda **kwargs: None)
    monkeypatch.setattr(producer, "_check_resources", lambda *args: None)
    hashes = producer._validate_outputs(
        tmp_path,
        states,
        order,
        decision,
        construction,
        replay,
        evaluations,
        environment,
        source,
        figure_hashes,
        tmp_path,
        "fixture",
        {},
        tmp_path / "packet_identity.json",
        deadline=1.0,
    )
    assert "state_evaluations.json" in hashes

    archive_path = tmp_path / "all_state_fields.npz"
    with np.load(archive_path, allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
    arrays["target_peak"] = np.full_like(arrays["target_peak"], np.nan)
    replacement = tmp_path / "replacement.npz"
    np.savez_compressed(replacement, **arrays)
    replacement.replace(archive_path)
    with pytest.raises(ValueError, match="target_peak"):
        producer._validate_outputs(
            tmp_path,
            states,
            order,
            decision,
            construction,
            replay,
            evaluations,
            environment,
            source,
            figure_hashes,
            tmp_path,
            "fixture",
            {},
            tmp_path / "packet_identity.json",
            deadline=1.0,
        )


def test_e015_field_collector_stops_at_10gib_before_next_cycle(monkeypatch):
    import s09_e015_producer as producer

    calls = []
    runtime = SimpleNamespace(
        model=SimpleNamespace(eval=lambda: None),
        arrays={
            "cycles": np.asarray([1, 2]),
            "d_pre": np.zeros((2, 1)),
            "d_peak": np.zeros((2, 1)),
            "xy": np.zeros((1, 2)),
            "nodal_weight": np.ones(1),
        },
    )

    def atomic(_runtime, index):
        calls.append(index)
        return {}, {"output": {"d_peak": torch.zeros(1)}}

    reserved = iter([9 * 1024**3, 11 * 1024**3])
    monkeypatch.setattr(producer, "atomic_losses", atomic)
    monkeypatch.setattr(producer.time, "time", lambda: 0.0)
    monkeypatch.setattr(torch.cuda, "max_memory_reserved", lambda: next(reserved))
    with pytest.raises(MemoryError, match="VRAM_CAP_EXCEEDED"):
        producer._collect_fields(runtime, deadline=1.0, label="fixture")
    assert calls == [0]


def test_completion_publication_checks_after_each_write(tmp_path, monkeypatch):
    import s09_e015_producer as producer

    output = tmp_path / "output"
    archive = tmp_path / "archive"
    output.mkdir()
    archive.mkdir()
    stages = []

    def guard(_deadline, stage):
        stages.append(stage)
        if stage == "completion:archive:after":
            raise TimeoutError(stage)

    monkeypatch.setattr(producer, "_check_resources", guard)
    with pytest.raises(TimeoutError, match="archive:after"):
        producer._publish_completion(
            completion={"execution_status": "SUCCEEDED"},
            output_dir=output,
            archive_dir=archive,
            deadline=1.0,
        )
    assert (archive / "completion_receipt.json").is_file()
    assert not (output / "completion_receipt.json").exists()
    assert stages == ["completion:archive:before", "completion:archive:after"]


def test_evaluate_state_injects_e015_resource_guard(monkeypatch):
    import s09_e015_producer as producer

    stages = []
    fields = {
        "cycles": np.arange(16),
        "xy": np.zeros((1, 2)),
        "nodal_weight": np.ones(1),
        "d_pre": np.zeros((16, 1)),
        "target_peak": np.ones((16, 1)),
        "predicted_peak": np.zeros((16, 1)),
    }
    monkeypatch.setattr(producer, "_collect_fields", lambda *args, **kwargs: fields)

    def evaluate(_runtime, *, update, resource_guard):
        resource_guard("cycle_1:before")
        resource_guard("cycle_1:after")
        return {"aggregate": {"update": update}, "per_cycle": [{"update": update}] * 16}

    monkeypatch.setattr(producer, "evaluate_arm", evaluate)
    monkeypatch.setattr(
        producer, "_check_resources", lambda _d, stage: stages.append(stage)
    )
    monkeypatch.setattr(producer, "_require_valid_evaluation", lambda *args: None)
    monkeypatch.setattr(
        producer,
        "_scores_from_fields",
        lambda _fields: (
            {"score_2W_plus_T": 0, "pairs": []},
            {"score_2W_plus_T": 0, "pairs": []},
            [{}] * 16,
        ),
    )
    monkeypatch.setattr(
        producer, "_require_score_evaluation_alignment", lambda *args: None
    )
    monkeypatch.setattr(
        producer,
        "_cycle_increment_rows",
        lambda _fields: [
            {"cycle": index, "positive_node_count": 0, "maximum_increment": 0.0}
            for index in range(16)
        ]
    )
    monkeypatch.setattr(producer, "noncollapsed", lambda _rows: False)
    producer._evaluate_state(SimpleNamespace(), deadline=1.0, label="fixture", update=0)
    assert stages == [
        "evaluation:fixture:cycle_1:before",
        "evaluation:fixture:cycle_1:after",
    ]


def test_startup_evidence_failure_produces_failure_receipts(tmp_path, monkeypatch):
    import s09_e015_producer as producer

    output = tmp_path / "run"
    archive = tmp_path / "archive"
    monkeypatch.setattr(producer.platform, "system", lambda: "Linux")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        producer,
        "_validate_binding",
        lambda *args: ({}, {"hostname": "GPUServer8"}),
    )
    original_write = producer._write_json
    injected = {"done": False}

    def write(path, value):
        if path.name == "source_identity.json" and not injected["done"]:
            injected["done"] = True
            raise OSError("injected startup evidence failure")
        original_write(path, value)

    monkeypatch.setattr(producer, "_write_json", write)
    with pytest.raises(OSError, match="startup evidence failure"):
        producer.run_producer(
            packet_dir=tmp_path / "packet",
            base_config=tmp_path / "base.json",
            initial_checkpoint=tmp_path / "base.pt",
            control_endpoint=tmp_path / "control.pt",
            candidate_endpoint=tmp_path / "candidate.pt",
            e014_run_dir=tmp_path / "e014",
            vector_archive=tmp_path / "vector.pt",
            e014_completion=tmp_path / "e014_completion.json",
            output_dir=output,
            archive_dir=archive,
            repo_root=tmp_path,
            expected_commit="fixture",
            run_config=tmp_path / "run_config.json",
            protocol=tmp_path / "experiment.md",
        )
    for root in (output, archive):
        failure = producer._load_json(root / "failure_receipt.json")
        assert failure["scientific_status"] == "EXECUTION_INVALID"
        assert failure["states_evaluated"] == 0
        assert failure["optimizer_steps_completed"] == 0
