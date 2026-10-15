"""Nontraining contract tests: no optimizer update or training loop is run."""
import ast
import copy
import math
import sys
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "SENS_tensile"))

from s04_e020_delayed_decay import (
    CONTROL_LOCKS,
    DelayedDecaySchedule,
    update_lr,
    schedule_identity,
    check_schedule_identity,
    check_pair_identity,
    admit_control,
    check_runtime_identity,
)
from aggregate_s04_e020_delayed_decay import summarize
from aggregate_s04_e020_delayed_decay import validate_schedule_and_pair
from run_s04_e019_frozen_residual_screen import sha256


@pytest.mark.parametrize("k", [1, 2, 7999, 8000, 8001, 9000, 9999, 10000])
def test_actual_update_lr(k):
    expected = (
        1e-3
        if k <= 8000
        else 1e-5 + (1e-3 - 1e-5) * (1 + math.cos(math.pi * (k - 8000) / 2000)) / 2
    )
    assert update_lr(k) == expected


@pytest.mark.parametrize("k", [0, 10001, True, 1.0, -1])
def test_no_extra_or_ambiguous_update(k):
    with pytest.raises(ValueError):
        update_lr(k)


def test_full_schedule_without_parameter_updates():
    # Metadata-only schedule advance on fake param groups, never optimizer.step().
    opt = SimpleNamespace(param_groups=[dict(lr=0.001), dict(lr=0.001)])
    scheduler = DelayedDecaySchedule(opt)
    for k in range(1, 10001):
        scheduler.before_update(k)
        assert all(g["lr"] == update_lr(k) for g in opt.param_groups)
        scheduler.step()
    a = np.array(scheduler.used, dtype="<f8")
    assert np.all(a[:8000] == 1e-3)
    assert np.all(np.diff(a[7999:]) < 0)
    assert a[-1] == 1e-5 and scheduler.next_lr is None
    assert scheduler.get_last_lr() == [1e-5, 1e-5]
    check_schedule_identity(schedule_identity(a), a)
    with pytest.raises(ValueError):
        scheduler.step()


def test_scheduler_rejects_wrong_group_and_step():
    opt = SimpleNamespace(param_groups=[dict(lr=0.001)])
    s = DelayedDecaySchedule(opt)
    with pytest.raises(ValueError):
        s.before_update(2)
    opt.param_groups[0]["lr"] = 1e-5
    with pytest.raises(ValueError):
        s.before_update(1)


@pytest.mark.parametrize(
    "tamper", ["shift", "count", "dtype", "nan", "digest", "boolean"]
)
def test_actual_lr_evidence_fails_closed(tamper):
    a = np.array([update_lr(k) for k in range(1, 10001)], dtype="<f8")
    info = schedule_identity(a)
    if tamper == "shift":
        a = np.roll(a, 1)
    if tamper == "count":
        a = a[:-1]
    if tamper == "dtype":
        a = a.astype(np.float32)
    if tamper == "nan":
        a[100] = np.nan
    if tamper == "digest":
        info["used_lr_sha256"] = "0" * 64
    if tamper == "boolean":
        info["optimizer_then_scheduler"] = 1
    with pytest.raises(ValueError):
        check_schedule_identity(info, a)


@pytest.mark.parametrize("state", tuple(CONTROL_LOCKS))
@pytest.mark.parametrize("field", ["geometry", "backbone", "initialization", "sampler"])
def test_historical_pair_binding(state, field):
    lock = CONTROL_LOCKS[state]
    g = copy.deepcopy(lock["geometry"])
    b, i, s = (
        lock["backbone_digest"],
        lock["initial_residual_digest"],
        lock["sampler_index_sha256"],
    )
    check_pair_identity(state, g, b, i, s)
    if field == "geometry":
        g["padding"] += 0.01
    if field == "backbone":
        b = "0" * 64
    if field == "initialization":
        i = "0" * 64
    if field == "sampler":
        s = "0" * 64
    with pytest.raises(ValueError):
        check_pair_identity(state, g, b, i, s)


def test_missing_historical_asset_not_silently_skipped(tmp_path):
    with pytest.raises(FileNotFoundError):
        admit_control("c20s4", tmp_path, {}, None)


@pytest.mark.parametrize("key", list(CONTROL_LOCKS["c20s4"]["runtime"]))
def test_runtime_changes_cannot_be_called_schedule_effects(key):
    current = copy.deepcopy(CONTROL_LOCKS["c20s4"]["runtime"])
    check_runtime_identity("c20s4", current)
    current[key] = "different"
    with pytest.raises(ValueError):
        check_runtime_identity("c20s4", current)


def result_rows():
    return [
        dict(
            state=s,
            displacement_mass_rms_over_abs_Us=0.0009,
            final_damage_conditional_rms=0.005,
            base_damage=0.02,
            final_background_conditional_rms=0.0002,
            base_background=0.0003,
        )
        for s in CONTROL_LOCKS
    ]


def test_primary_and_component_are_separate():
    r = result_rows()
    assert summarize(r)["verdict"].endswith("PASS")
    r[-1]["displacement_mass_rms_over_abs_Us"] = 0.003
    a = summarize(r)
    assert a["verdict"].endswith("FAIL")
    assert a["clean_damage_progress_background_preserved"] is True
    r[0]["displacement_mass_rms_over_abs_Us"] = 0.002
    assert summarize(r)["verdict"].endswith("FAIL")


def test_missing_duplicate_and_integrity_precedence():
    r = result_rows()
    assert summarize(r[:2])["verdict"] == "INCONCLUSIVE"
    assert summarize([r[0], r[0], r[2]])["verdict"] == "INADMISSIBLE"
    assert summarize(r, errors=[{"error": "bad control"}])["verdict"] == "INADMISSIBLE"


def test_three_candidate_cli_and_single_optimizer_call_are_frozen():
    import run_s04_e020_delayed_decay as r

    assert r.ARMS == ("localized",) and r.STEPS == 10000 and r.SEEDS == (7,)
    tree = ast.parse(Path(r.__file__).read_text())
    calls = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == "optimizer"
        and n.func.attr == "step"
    ]
    assert len(calls) == 1


@pytest.mark.parametrize(
    "mutation",
    [
        None,
        "receipt_control",
        "checkpoint_schedule",
        "rates",
        "missing_rates",
        "file_hash",
    ],
)
def test_saved_schedule_and_control_envelope(tmp_path, mutation):
    rates = np.array([update_lr(k) for k in range(1, 10001)], dtype="<f8")
    np.save(tmp_path / "learning_rates.npy", rates)
    common = dict(
        **{k: v for k, v in CONTROL_LOCKS["c20s4"]["runtime"].items()},
        state="c20s4",
        paired_control_lock=CONTROL_LOCKS["c20s4"],
        lr_schedule=schedule_identity(rates),
        learning_rates_sha256=sha256(tmp_path / "learning_rates.npy")
    )
    cp, receipt = copy.deepcopy(common), copy.deepcopy(common)
    if mutation == "receipt_control":
        receipt["paired_control_lock"]["run_id"] = "wrong"
    if mutation == "checkpoint_schedule":
        cp["lr_schedule"]["actual_updates"] = 9999
    if mutation == "file_hash":
        receipt["learning_rates_sha256"] = "0" * 64
    if mutation == "rates":
        rates[-1] = rates[-2]
        np.save(tmp_path / "learning_rates.npy", rates)
    if mutation == "missing_rates":
        (tmp_path / "learning_rates.npy").unlink()
    torch.save(cp, tmp_path / "final_step_10000.pt")
    (tmp_path / "RUN_RECEIPT.json").write_text(json.dumps(receipt))
    (tmp_path / "metrics.json").write_text(json.dumps(common))
    if mutation is None:
        validate_schedule_and_pair(tmp_path / "metrics.json")
    else:
        with pytest.raises((ValueError, FileNotFoundError)):
            validate_schedule_and_pair(tmp_path / "metrics.json")
