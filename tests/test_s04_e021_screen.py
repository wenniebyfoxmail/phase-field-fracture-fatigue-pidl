"""Nontraining E021 contracts: metadata, envelopes, state identity and scoring."""
import ast
import copy
import json
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "SENS_tensile"))
from s04_e021_screen import (
    native_replay,
    update_lr,
    schedule_identity,
    check_schedule_identity,
    OriginalCosineSchedule,
    MetadataOnlyOptimizer,
    MAP_LOCKS,
    CONTROL_LOCKS,
    validate_coordinate_buffers,
)
from aggregate_s04_e021_coordinate_screen import validate_schedule_and_pair, summarize
from aggregate_s04_e021_coordinate_screen import validate_pre_update, PROTOCOL_REVISION
from run_s04_e019_frozen_residual_screen import sha256, build_model
from s04_e021_residual_coordinates import CoordinateResidualUV


def test_native_metadata_replay_matches_original_indexing_and_keeps_rng():
    before = torch.random.get_rng_state().clone()
    native_replay.cache_clear()
    a = np.array(native_replay(), dtype="<f8")
    assert torch.equal(before, torch.random.get_rng_state())
    closed = np.array(
        [
            1e-5 + (0.001 - 1e-5) * (1 + math.cos(math.pi * (k - 1) / 10000)) / 2
            for k in range(1, 10001)
        ]
    )
    np.testing.assert_allclose(a, closed, rtol=0, atol=1e-15)
    assert a[0] == 0.001 and a[-1] > 1e-5 and np.all(np.diff(a) < 0)
    check_schedule_identity(schedule_identity(a), a)
    with pytest.raises(RuntimeError, match="never step"):
        MetadataOnlyOptimizer().step()


def test_actual_native_schedule_alignment_without_any_parameter_update():
    opt = MetadataOnlyOptimizer()
    s = OriginalCosineSchedule(opt)
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        for k in range(1, 10001):
            s.before_update(k)
            s.step()
    assert len(observed) == 1 and "before `optimizer.step()`" in str(
        observed[0].message
    )
    np.testing.assert_array_equal(np.array(s.used), np.array(native_replay()))
    assert s.next_lr is None and s.get_last_lr() == [1e-5]
    with pytest.raises(ValueError):
        s.step()


@pytest.mark.parametrize("k", [0, 10001, True, 1.0, -1])
def test_invalid_update_index(k):
    with pytest.raises(ValueError):
        update_lr(k)


@pytest.mark.parametrize("mode", ["order", "changed_lr", "changed_epoch"])
def test_schedule_desynchronisation_stops(mode):
    opt = MetadataOnlyOptimizer()
    s = OriginalCosineSchedule(opt)
    if mode == "changed_lr":
        opt.param_groups[0]["lr"] = 0.002
    if mode == "changed_epoch":
        s.native.last_epoch = 1
    with pytest.raises(ValueError):
        s.before_update(2 if mode == "order" else 1)


@pytest.mark.parametrize(
    "mode", ["shift", "dtype", "shape", "nan", "boolean", "post_lr"]
)
def test_native_lr_evidence_tampering(mode):
    a = np.array(native_replay(), dtype="<f8")
    info = schedule_identity(a)
    if mode == "shift":
        a = np.roll(a, 1)
    if mode == "dtype":
        a = a.astype(np.float32)
    if mode == "shape":
        a = a[:-1]
    if mode == "nan":
        a[-1] = np.nan
    if mode == "boolean":
        info["optimizer_then_scheduler"] = 1
    if mode == "post_lr":
        info["post_final_scheduler_lr"] = a[-1]
    with pytest.raises(ValueError):
        check_schedule_identity(info, a)


def make_envelope(path):
    """Synthetic unit envelope only; no model/training or producer output."""
    state = "c20s4"
    a = np.array(native_replay(), dtype="<f8")
    for name in ["learning_rates.npy", "expected_learning_rates.npy"]:
        np.save(path / name, a)
    m = MAP_LOCKS[state]["mapping"]
    (path / "coordinate_map.json").write_text(json.dumps(m))
    (path / "PRE_UPDATE.json").write_text("{}")
    common = dict(
        **CONTROL_LOCKS[state]["runtime"],
        state=state,
        paired_control_lock=CONTROL_LOCKS[state],
        lr_schedule=schedule_identity(a),
        learning_rates_sha256=sha256(path / "learning_rates.npy"),
        expected_learning_rates_sha256=sha256(path / "expected_learning_rates.npy"),
        coordinate_mapping=m,
        coordinate_map_sha256=sha256(path / "coordinate_map.json"),
        pre_update_sha256=sha256(path / "PRE_UPDATE.json")
    )
    return common, copy.deepcopy(common), copy.deepcopy(common)


@pytest.mark.parametrize(
    "mode",
    [
        None,
        "receipt_map",
        "checkpoint_map",
        "map_file",
        "actual_lr",
        "expected_lr",
        "pre_file",
        "control",
        "missing",
    ],
)
def test_envelope_identity_and_file_binding(tmp_path, mode):
    record, cp, receipt = make_envelope(tmp_path)
    if mode == "receipt_map":
        receipt["coordinate_mapping"]["teacher_target_used"] = 1
    if mode == "checkpoint_map":
        cp["coordinate_mapping"]["local_center"][0] += 0.01
    if mode == "map_file":
        (tmp_path / "coordinate_map.json").write_text("{}")
    if mode in ("actual_lr", "expected_lr"):
        p = tmp_path / (
            "learning_rates.npy"
            if mode == "actual_lr"
            else "expected_learning_rates.npy"
        )
        a = np.load(p)
        a[-1] = 1e-5
        np.save(p, a)
    if mode == "pre_file":
        (tmp_path / "PRE_UPDATE.json").write_text('{"changed":true}')
    if mode == "control":
        receipt["paired_control_lock"]["run_id"] = "wrong"
    if mode == "missing":
        (tmp_path / "PRE_UPDATE.json").unlink()
    torch.save(cp, tmp_path / "final_step_10000.pt")
    (tmp_path / "RUN_RECEIPT.json").write_text(json.dumps(receipt))
    (tmp_path / "metrics.json").write_text(json.dumps(record))
    if mode is None:
        validate_schedule_and_pair(tmp_path / "metrics.json")
    else:
        with pytest.raises((ValueError, FileNotFoundError)):
            validate_schedule_and_pair(tmp_path / "metrics.json")


@pytest.mark.parametrize("state", list(MAP_LOCKS))
def test_actual_local_buffers_cannot_drift(state):
    lock = MAP_LOCKS[state]
    g = lock["physical_geometry"]
    old = build_model(7, "localized", g, torch.nn.Linear(2, 2).double())
    model = CoordinateResidualUV(old.backbone, old.residual, g, lock["mapping"])
    validate_coordinate_buffers(model, lock["mapping"])
    model.local_center[0] += 0.01
    with pytest.raises(ValueError):
        validate_coordinate_buffers(model, lock["mapping"])


def rows():
    return [
        dict(
            state=s,
            displacement_mass_rms_over_abs_Us=0.0009,
            final_damage_conditional_rms=0.005,
            final_background_conditional_rms=0.0002,
            base_damage=0.02,
            base_background=0.0003,
            control_damage=0.004,
            control_background=0.0001,
        )
        for s in CONTROL_LOCKS
    ]


def test_primary_component_and_original_control_are_independent():
    r = rows()
    v = summarize(r)
    assert v["verdict"].endswith("PASS")
    assert v["clean_damage_progress_background_preserved"] is True
    assert v["clean_damage_progress_background_preserved_vs_control"] is False
    r[-1]["displacement_mass_rms_over_abs_Us"] = 0.003
    assert summarize(r)["verdict"].endswith("FAIL")
    assert summarize(r[:2])["verdict"] == "INCONCLUSIVE"
    assert summarize([r[0], r[0], r[2]])["verdict"] == "INADMISSIBLE"
    assert summarize(r, errors=[{"error": "bad map"}])["verdict"] == "INADMISSIBLE"


def test_one_actual_optimizer_step_call_and_order():
    import run_s04_e021_coordinate_screen as runner

    tree = ast.parse(Path(runner.__file__).read_text())
    train = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "train"
    )
    calls = [
        n
        for n in ast.walk(train)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and isinstance(n.func.value, ast.Name)
    ]
    update = [
        n for n in calls if n.func.value.id == "optimizer" and n.func.attr == "step"
    ]
    assert len(update) == 1
    before = [
        n
        for n in calls
        if n.func.value.id == "scheduler" and n.func.attr == "before_update"
    ][0]
    after = [
        n for n in calls if n.func.value.id == "scheduler" and n.func.attr == "step"
    ][0]
    assert before.lineno < update[0].lineno < after.lineno
    assert (
        runner.ARMS == ("localized",) and runner.SEEDS == (7,) and runner.STEPS == 10000
    )


@pytest.mark.parametrize(
    "mode",
    [
        None,
        "counter",
        "bool_counter",
        "dirty",
        "future",
        "naive",
        "model",
        "receipt_time",
    ],
)
def test_before_update_counter_chronology_and_initial_model(tmp_path, mode):
    state = "c20s4"
    schedule = schedule_identity(native_replay())
    mapping = MAP_LOCKS[state]["mapping"]
    record = dict(
        state=state,
        reference_sha256=CONTROL_LOCKS[state]["reference_sha256"],
        coordinate_map_sha256="m",
        expected_learning_rates_sha256="l",
        lr_schedule=schedule,
        started_utc="2026-10-15T00:00:01Z",
        finished_utc="2026-10-15T00:00:02Z",
    )
    receipt = dict(
        run_id="unit-only",
        started_utc=record["started_utc"],
        finished_utc=record["finished_utc"],
    )
    data = {
        state: dict(
            base_digest="b",
            initial_residual_digest="r",
            initial_coordinate_model_digest="i",
            coordinate_mapping=mapping,
        )
    }
    pre = dict(
        protocol_revision=PROTOCOL_REVISION,
        state=state,
        seed=7,
        alpha="0.7",
        arm="localized",
        run_id="unit-only",
        code_commit="0" * 40,
        reference_sha256=record["reference_sha256"],
        backbone_digest="b",
        initial_residual_digest="r",
        initial_model_digest="i",
        coordinate_mapping=mapping,
        coordinate_map_sha256="m",
        expected_learning_rates_sha256="l",
        lr_schedule=schedule,
        runtime=CONTROL_LOCKS[state]["runtime"],
        new_optimizer_steps=0,
        dirty=False,
        created_utc="2026-10-15T00:00:00Z",
    )
    if mode == "counter":
        pre["new_optimizer_steps"] = 1
    if mode == "bool_counter":
        pre["new_optimizer_steps"] = False
    if mode == "dirty":
        pre["dirty"] = 0
    if mode == "future":
        pre["created_utc"] = "2026-10-15T00:00:03Z"
    if mode == "naive":
        pre["created_utc"] = "2026-10-15T00:00:00"
    if mode == "model":
        pre["initial_model_digest"] = "wrong"
    if mode == "receipt_time":
        receipt["started_utc"] = "2026-10-15T00:00:00Z"
    for name, value in [
        ("metrics.json", record),
        ("RUN_RECEIPT.json", receipt),
        ("PRE_UPDATE.json", pre),
    ]:
        (tmp_path / name).write_text(json.dumps(value))
    tr = [
        dict(
            step=k,
            lr_used=native_replay()[k - 1] if k else None,
            lr_next=native_replay()[k] if k < 10000 else None,
        )
        for k in range(0, 10001, 1000)
    ]
    (tmp_path / "monitoring.json").write_text(json.dumps(tr))
    if mode is None:
        validate_pre_update(tmp_path / "metrics.json", "0" * 40, data)
    else:
        with pytest.raises(ValueError):
            validate_pre_update(tmp_path / "metrics.json", "0" * 40, data)
