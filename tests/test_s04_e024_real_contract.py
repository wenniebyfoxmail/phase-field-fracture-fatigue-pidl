"""Synthetic 8000/10000 envelopes on fixed real assets. No optimizer step/training.
Declared counts/runtime/cost in temp fixtures are artificial decoder test inputs.
"""
import copy, json, sys
from pathlib import Path
import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "SENS_tensile"))
from test_s04_e023_real_contract import assemble_fixture as assemble_e023
from aggregate_s04_e024_head_tail_screen import prepare_baseline, validate_record
from run_s04_e024_head_tail_screen import (
    monitor_full_field,
    support_diagnostics,
    final_metrics,
    sha256,
    predict_in_chunks,
)
from s04_e024_head_tail import *

PROJECT = Path(__file__).resolve().parents[3]
# Dedicated worktree is .codex/worktrees/<name>, project one further level.
PROJECT = Path(__file__).resolve().parents[1].parents[2]
OLD = PROJECT / "local_archive/experiments/S04-E019/producer_execution_v1/raw"
E21 = PROJECT / "local_archive/experiments/S04-E021/producer_execution_v2/raw"
E22 = PROJECT / "local_archive/experiments/S04-E022/producer_execution_v1/raw"
E23 = PROJECT / "local_archive/experiments/S04-E023/producer_execution_v1/raw"
pytestmark = pytest.mark.skipif(
    not E23.exists(), reason="optional immutable real assets absent"
)


@pytest.fixture(scope="module")
def data():
    torch.set_num_threads(2)
    torch.set_default_dtype(torch.float64)
    s = "c20s4"
    d = prepare_baseline(
        s,
        OLD / "inputs" / f"{s}.npz",
        OLD / "backbones" / s,
        OLD / "runs" / CONTROL_LOCKS[s]["run_id"],
        E21 / "runs" / DIRECT_LOCKS[s]["run_id"],
        E22 / "runs" / LEAK_LOCKS[s]["run_id"],
        E23 / "runs" / HEAD_LOCKS[s]["run_id"],
    )
    d["direct_actual_rates"] = np.asarray(
        native_replay(), dtype="<f8"
    )  # SYNTHETIC Mac metadata only
    return {s: d}


def bind(path, rec, receipt, cp):
    torch.save(cp, path / "final_step_10000.pt")
    for n, k in [
        ("final_step_10000.pt", "checkpoint_sha256"),
        ("prediction.npz", "prediction_sha256"),
        ("monitoring.json", "monitoring_sha256"),
    ]:
        rec[k] = receipt[k] = sha256(path / n)
    (path / "metrics.json").write_text(json.dumps(rec))
    receipt["metrics_sha256"] = sha256(path / "metrics.json")
    names = [
        "final_step_10000.pt",
        "prediction.npz",
        "monitoring.json",
        "metrics.json",
        "learning_rates.npy",
        "expected_learning_rates.npy",
        "coordinate_map.json",
        "PRE_UPDATE.json",
        "head_scale.json",
        "head_gradient_preflight.json",
        "HEAD_ONLY_STAGE_ENTRY.json",
        "step_8000.pt",
    ]
    receipt["archive_file_hashes"] = {n: sha256(path / n) for n in names}
    (path / "RUN_RECEIPT.json").write_text(json.dumps(receipt))


def fixture(path, data):
    d = copy.deepcopy(data["c20s4"])
    dd = {"c20s4": d}
    rec, receipt = assemble_e023(path, dd)
    cp = torch.load(path / "final_step_10000.pt", map_location="cpu", weights_only=True)
    common = dict(
        protocol_revision=PROTOCOL_REVISION,
        stage_rule=STAGE_RULE,
        evaluation_rule=EVALUATION_RULE,
        paired_e023_control_lock=HEAD_LOCKS["c20s4"],
    )
    pre = json.loads((path / "PRE_UPDATE.json").read_text())
    pre.update(common)
    (path / "PRE_UPDATE.json").write_text(json.dumps(pre))
    prehash = sha256(path / "PRE_UPDATE.json")
    for x in (rec, receipt, cp):
        x.update(
            common,
            pre_update_sha256=prehash,
            final_training_phase="head_only",
            head_updates=10000,
            hidden_updates=8000,
            final_trainable_parameter_names=[
                "output_layer.weight",
                "output_layer.bias",
            ],
        )
    model, cal = build_candidate(
        7,
        "localized",
        rec["geometry"],
        copy.deepcopy(d["base_model"]),
        d["coordinate_mapping"],
        d["xy"],
        d["mass"],
    )
    model.load_state_dict(cp["model_state_dict"])
    opt = torch.optim.AdamW(
        model.residual.parameters(), lr=float(native_replay()[8000]), weight_decay=1e-8
    )
    opt.param_groups[0]["initial_lr"] = 0.001
    for p in model.residual.parameters():
        opt.state[p] = dict(
            step=torch.tensor(8000.0),
            exp_avg=torch.ones_like(p) * 0.01,
            exp_avg_sq=torch.ones_like(p) * 0.02,
        )
    entry = enter_head_only(model, opt, 8000)
    names = [n for n, _ in model.residual.named_parameters()]
    identity = dict(
        protocol_revision=PROTOCOL_REVISION,
        evaluation_rule=EVALUATION_RULE,
        code_commit="0" * 40,
        stage_rule=STAGE_RULE,
        state="c20s4",
        run_id=receipt["run_id"],
        completed_updates=8000,
        next_update=8001,
        pre_update_sha256=prehash,
        head_scale_sha256=rec["head_scale_sha256"],
        head_gradient_preflight_sha256=rec["head_gradient_preflight_sha256"],
    )
    snap = dict(
        **identity,
        head_updates=8000,
        hidden_updates=8000,
        model_state_dict=cpu_tree(model.state_dict()),
        optimizer_state_dict=cpu_tree(opt.state_dict()),
        optimizer_parameter_names=names,
    )
    torch.save(snap, path / "step_8000.pt")
    stage = dict(
        **identity,
        **entry,
        stage_snapshot_sha256=sha256(path / "step_8000.pt"),
        phase="head_only",
        optimizer_unchanged_across_freeze=True,
        head_updates=8000,
        hidden_updates=8000,
        sampler_prefix_sha256=d["stage_sampler_audit"]["prefix8000"],
        lr_used_update8000=native_replay()[7999],
        lr_next_update8001=native_replay()[8000],
        created_utc="2026-10-15T00:00:01.500000Z",
    )
    (path / "HEAD_ONLY_STAGE_ENTRY.json").write_text(json.dumps(stage))
    for x in (rec, receipt, cp):
        x.update(
            stage_entry_sha256=sha256(path / "HEAD_ONLY_STAGE_ENTRY.json"),
            stage_snapshot_sha256=sha256(path / "step_8000.pt"),
        )
    trace = json.loads((path / "monitoring.json").read_text())
    d["e023_trace"] = copy.deepcopy(trace)
    # Nonzero final-head fixture, not fitted and not an optimizer update.
    with torch.no_grad():
        model.residual.output_layer.weight.fill_(1e-9)
        model.residual.output_layer.bias.fill_(1e-7)
        for p in model.residual.output_layer.parameters():
            opt.state[p]["step"].fill_(10000)
            opt.state[p]["exp_avg"].fill_(0.03)
    opt.param_groups[0]["lr"] = 1e-5
    xy = torch.tensor(d["xy"])
    target = torch.tensor(d["equilibrated_uv"])
    uv = predict_in_chunks(model, xy).numpy()
    for t in trace:
        k = t["step"]
        if k > 8000:
            t.update(monitor_full_field(model, xy, target, d["mass"], d["damage"], k))
            t.update(support_diagnostics(uv, d["base_uv"], d, rec["geometry"]))
        t.update(
            training_phase="joint" if k <= 8000 else "head_only",
            head_updates=k,
            hidden_updates=min(k, 8000),
        )
    (path / "monitoring.json").write_text(json.dumps(trace))
    np.savez_compressed(path / "prediction.npz", uv=uv)
    cp.update(
        model_state_dict=cpu_tree(model.state_dict()),
        optimizer_state_dict=cpu_tree(opt.state_dict()),
        optimizer_parameter_names=names,
    )
    rec.update(
        metrics=final_metrics(d, uv),
        e023_direct_control_admission=d["head_control"],
        support_diagnostics=support_diagnostics(uv, d["base_uv"], d, rec["geometry"]),
        compute_cost=dict(
            new_optimizer_updates=10000,
            joint_updates=8000,
            head_only_updates=2000,
            head_parameter_updates=10000,
            hidden_parameter_updates=8000,
            preflight_wall_seconds=1.0,
            loop_wall_seconds=3.0,
            joint_wall_seconds=2.0,
            head_only_wall_seconds=1.0,
            peak_cuda_allocated_bytes=1,
            peak_cuda_reserved_bytes=1,
        ),
    )
    bind(path, rec, receipt, cp)
    return rec, receipt, cp, dd


@pytest.mark.parametrize(
    "mode",
    [
        None,
        "hidden_weight",
        "hidden_moment",
        "hidden_counter",
        "head_counter",
        "missing_stage",
        "wrong_next",
        "stage_time",
        "stage_prefix",
        "D",
        "phase_envelope",
        "evaluation_gate",
        "control_state",
        "cost",
        "prediction",
    ],
)
def test_strict_decoder_and_coherently_rehashed_tampering(tmp_path, data, mode):
    rec, r, cp, dd = fixture(tmp_path, data)
    if mode == "hidden_weight":
        cp["model_state_dict"]["residual.input_layer.weight"][0, 0] += 1
    if mode == "hidden_moment":
        cp["optimizer_state_dict"]["state"][0]["exp_avg"][0, 0] += 1
    if mode == "hidden_counter":
        cp["optimizer_state_dict"]["state"][0]["step"].fill_(8001)
    if mode == "head_counter":
        cp["optimizer_state_dict"]["state"][len(cp["optimizer_parameter_names"]) - 1][
            "step"
        ].fill_(9999)
    if mode == "D":
        cp["model_state_dict"]["head_scale"][0] *= 2
    if mode in ("wrong_next", "stage_time", "stage_prefix"):
        p = tmp_path / "HEAD_ONLY_STAGE_ENTRY.json"
        st = json.loads(p.read_text())
        if mode == "wrong_next":
            st["next_update"] = 8002
        if mode == "stage_time":
            st["created_utc"] = "2026-10-15T00:00:03Z"
        if mode == "stage_prefix":
            st["sampler_prefix_sha256"] = "0" * 64
        p.write_text(json.dumps(st))
        for a in (rec, r, cp):
            a["stage_entry_sha256"] = sha256(p)
    if mode == "phase_envelope":
        cp["hidden_updates"] = 10000
    if mode == "evaluation_gate":
        r["evaluation_rule"] = dict(EVALUATION_RULE, historical_001="primary")
    if mode == "control_state":
        r["paired_e023_control_lock"] = HEAD_LOCKS["c60s4"]
    if mode == "cost":
        rec["compute_cost"]["hidden_parameter_updates"] = 10000
    if mode == "prediction":
        z = np.load(tmp_path / "prediction.npz")["uv"]
        z[200, 0] += 0.001
        np.savez_compressed(tmp_path / "prediction.npz", uv=z)
    bind(tmp_path, rec, r, cp)
    if mode == "missing_stage":
        (tmp_path / "HEAD_ONLY_STAGE_ENTRY.json").unlink()
    if mode is None:
        row = validate_record(tmp_path / "metrics.json", "0" * 40, dd)
        assert row["head_updates"] == 10000 and row["hidden_updates"] == 8000
    else:
        with pytest.raises((ValueError, FileNotFoundError, AssertionError)):
            validate_record(tmp_path / "metrics.json", "0" * 40, dd)
