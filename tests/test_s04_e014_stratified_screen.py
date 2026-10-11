import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import torch


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "SENS_tensile"))
RUNNER_PATH = ROOT / "SENS_tensile" / "run_s04_e014_stratified_screen.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("s04_e014_runner", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
assert RUNNER_SPEC.loader is not None
RUNNER_SPEC.loader.exec_module(RUNNER)
AGG_PATH = ROOT / "SENS_tensile" / "aggregate_s04_e014_stratified_screen.py"
AGG_SPEC = importlib.util.spec_from_file_location("s04_e014_aggregate", AGG_PATH)
AGG = importlib.util.module_from_spec(AGG_SPEC)
assert AGG_SPEC.loader is not None
AGG_SPEC.loader.exec_module(AGG)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_fixed_sampler_identity_and_draw_order():
    damage = np.array([1.0, 0.2, 0.0, 0.0])
    mass = np.array([1.0, 2.0, 3.0, 4.0])
    strata = RUNNER.make_strata(damage, mass)
    first = RUNNER.draw_stratified(np.random.Generator(np.random.PCG64(7 + RUNNER.SAMPLE_SEED_OFFSET)), strata)
    second = RUNNER.draw_stratified(np.random.Generator(np.random.PCG64(7 + RUNNER.SAMPLE_SEED_OFFSET)), strata)
    np.testing.assert_array_equal(first[0], second[0])
    np.testing.assert_array_equal(first[1], second[1])
    assert len(first[0]) == RUNNER.N_DAMAGE
    assert len(first[1]) == RUNNER.N_BACKGROUND
    assert set(first[0]).issubset({0, 1})
    assert set(first[1]).issubset({2, 3})


def test_stratified_loss_preserves_full_mass_objective_for_stratum_means():
    active = torch.tensor([2.0, 2.0], dtype=torch.float64)
    background = torch.tensor([5.0, 5.0], dtype=torch.float64)
    got = RUNNER.stratified_loss(active, background, 0.25, 0.75)
    expected = (0.25 * 2.0 + 0.75 * 5.0) / abs(RUNNER.US) ** 2
    torch.testing.assert_close(got, torch.tensor(expected, dtype=torch.float64))


def test_protocol_is_two_state_seed7_final_only():
    assert tuple(RUNNER.EXPECTED) == ("c20s4", "c83s4")
    assert RUNNER.SEEDS == (7,)
    assert RUNNER.STEPS == 10_000
    assert RUNNER.N_DAMAGE + RUNNER.N_BACKGROUND == RUNNER.BATCH_NODES
    assert RUNNER.MONITOR_STEPS == tuple(range(0, 10_001, 1_000))


def _write_run(root, state, displacement, *, mutation=None):
    seed = 7
    run = root / f"{state}-seed7"
    run.mkdir()
    checkpoint = run / "final_step_10000.pt"
    torch.save({
        "protocol_revision": RUNNER.PROTOCOL_REVISION, "state": state, "seed": seed,
        "step": RUNNER.STEPS,
        "sampler": {
            "damage_threshold": RUNNER.DAMAGE_THRESHOLD,
            "n_damage": RUNNER.N_DAMAGE, "n_background": RUNNER.N_BACKGROUND,
            "sample_seed": seed + RUNNER.SAMPLE_SEED_OFFSET,
            "order": "damage_then_background_no_shuffle",
        },
        "model_state_dict": {},
    }, checkpoint)
    prediction = run / "prediction.npz"
    np.savez_compressed(prediction, uv=np.zeros((86_756, 2)))
    monitoring = run / "monitoring.json"
    trace = [{
        "step": step, "full_field_loss": displacement ** 2,
        "displacement_mass_rms_over_abs_Us": displacement,
        "active_contribution": displacement ** 2 * 0.9,
        "background_contribution": displacement ** 2 * 0.1,
    } for step in RUNNER.MONITOR_STEPS]
    monitoring.write_text(json.dumps(trace))
    metrics = {
        "essential_bc_max_abs_error": 0.0,
        "displacement_mass_rms_over_abs_Us": displacement,
        "strain_error_norm": 0.001, "strain_reference_norm": 1.0,
        "strain_relative_l2": 0.001, "reference_rho_u": 5e-11,
        "predicted_rho_u": 0.0005, "gate_finite": True,
        "gate_essential_bc": True, "gate_displacement_fit": displacement <= 1e-3,
        "gate_strain_fit": True, "gate_rho_u": True,
        "joint_pass": displacement <= 1e-3,
    }
    record = {
        "status": "COMPLETED", "protocol_revision": RUNNER.PROTOCOL_REVISION,
        "state": state, "seed": seed, "reference_sha256": RUNNER.EXPECTED[state],
        "reference_sha256_after": RUNNER.EXPECTED[state],
        "checkpoint_sha256": _sha(checkpoint), "prediction_sha256": _sha(prediction),
        "monitoring_sha256": _sha(monitoring), "steps": RUNNER.STEPS,
        "batch_nodes": RUNNER.BATCH_NODES, "n_damage": RUNNER.N_DAMAGE,
        "n_background": RUNNER.N_BACKGROUND, "damage_threshold": RUNNER.DAMAGE_THRESHOLD,
        "p_damage": 0.02, "p_background": 0.98, "damage_node_count": 100,
        "background_node_count": 86_656, "sample_seed": seed + RUNNER.SAMPLE_SEED_OFFSET,
        "sample_order": "damage_then_background_no_shuffle", "final_scheduler_lr": 1e-5,
        "training": True, "metrics": metrics,
    }
    metrics_path = run / "metrics.json"
    metrics_path.write_text(json.dumps(record))
    receipt = {
        "status": "COMPLETED", "run_id": run.name,
        "protocol_revision": RUNNER.PROTOCOL_REVISION, "state": state, "seed": seed,
        "producer_alias": "taobo", "hostname": "test", "code_commit": "a" * 40,
        "dirty": False, "command": "test", "gpu": "test", "cuda_visible_devices": "0",
        "output_root": f"/mnt/data2/drtao/wennie/{run.name}/out",
        "archive_root": f"/mnt/data2/drtao/pidl_archives/{run.name}",
        "log_path": f"/mnt/data2/drtao/wennie/{run.name}/run.log",
        "started_utc": "2026-10-11T00:00:00Z", "finished_utc": "2026-10-11T00:01:00Z",
        "checkpoint_sha256": _sha(checkpoint), "prediction_sha256": _sha(prediction),
        "monitoring_sha256": _sha(monitoring), "metrics_sha256": _sha(metrics_path),
        "reference_sha256": RUNNER.EXPECTED[state], "archive_status": "VERIFIED_COPY",
        "archive_file_hashes": {
            checkpoint.name: _sha(checkpoint), prediction.name: _sha(prediction),
            monitoring.name: _sha(monitoring), metrics_path.name: _sha(metrics_path),
        },
    }
    if mutation:
        mutation(record, receipt, monitoring)
        metrics_path.write_text(json.dumps(record))
        receipt["metrics_sha256"] = _sha(metrics_path)
        receipt["archive_file_hashes"][metrics_path.name] = _sha(metrics_path)
    (run / "RUN_RECEIPT.json").write_text(json.dumps(receipt))


def test_aggregate_two_state_primary_pass(tmp_path):
    _write_run(tmp_path, "c20s4", 8e-4)
    _write_run(tmp_path, "c83s4", 9e-4)
    rows, summary = AGG.aggregate(tmp_path, "a" * 40)
    assert len(rows) == 2
    assert summary["verdict"] == "STRATIFIED_SAMPLING_REPAIRS_SUPERVISED_FIT_SCREEN"


def test_aggregate_selects_full_field_polish_only_when_both_improve_by_half(tmp_path):
    _write_run(tmp_path, "c20s4", AGG.BASELINE_DISPLACEMENT["c20s4"] * 0.49)
    _write_run(tmp_path, "c83s4", AGG.BASELINE_DISPLACEMENT["c83s4"] * 0.49)
    _, summary = AGG.aggregate(tmp_path, "a" * 40)
    assert summary["verdict"] == "SAMPLING_USEFUL_BUT_INSUFFICIENT_FULL_FIELD_POLISH_NEXT"


def test_aggregate_rejects_weak_sampling_repair(tmp_path):
    _write_run(tmp_path, "c20s4", AGG.BASELINE_DISPLACEMENT["c20s4"] * 0.8)
    _write_run(tmp_path, "c83s4", AGG.BASELINE_DISPLACEMENT["c83s4"] * 0.8)
    _, summary = AGG.aggregate(tmp_path, "a" * 40)
    assert summary["verdict"] == "SAMPLING_ONLY_REPAIR_REJECTED"


@pytest.mark.parametrize("kind", ["missing", "monitor", "sampler", "nonfinite"])
def test_aggregate_fails_closed_for_incomplete_or_malformed_evidence(tmp_path, kind):
    def mutate(record, receipt, monitoring):
        if kind == "monitor":
            record["monitoring_sha256"] = "0" * 64
        elif kind == "sampler":
            record["n_damage"] -= 1
        elif kind == "nonfinite":
            record["metrics"]["predicted_rho_u"] = float("nan")
    if kind != "missing":
        _write_run(tmp_path, "c20s4", 8e-4, mutation=mutate)
        _, summary = AGG.aggregate(tmp_path, "a" * 40)
        assert summary["verdict"] == "INADMISSIBLE"
    else:
        _write_run(tmp_path, "c20s4", 8e-4)
        _, summary = AGG.aggregate(tmp_path, "a" * 40)
        assert summary["verdict"] == "INCONCLUSIVE"
