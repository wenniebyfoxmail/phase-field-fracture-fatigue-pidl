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
RUNNER_PATH = ROOT / "SENS_tensile" / "run_s04_e018_global_local_screen.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("s04_e018_runner", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
assert RUNNER_SPEC.loader is not None
RUNNER_SPEC.loader.exec_module(RUNNER)
AGG_PATH = ROOT / "SENS_tensile" / "aggregate_s04_e018_global_local_screen.py"
AGG_SPEC = importlib.util.spec_from_file_location("s04_e018_aggregate", AGG_PATH)
AGG = importlib.util.module_from_spec(AGG_SPEC)
assert AGG_SPEC.loader is not None
AGG_SPEC.loader.exec_module(AGG)


@pytest.fixture(autouse=True)
def synthetic_reference(monkeypatch):
    def load(state,path):
        mass=np.empty(86_756)
        mass[:100]=.02/100; mass[100:]=.98/(86_756-100)
        damage=np.zeros(86_756); damage[:100]=.5
        return {"conn":np.array([[i,i+1,101+i,100+i] for i in range(99)]),"xy":np.column_stack((np.linspace(-.5,.5,86_756),np.zeros(86_756))),"mass":mass,"damage":damage,"equilibrated_uv":np.zeros((86_756,2))}
    monkeypatch.setattr(AGG,"validate_reference",load)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("alpha", list(RUNNER.ALLOCATIONS))
def test_fixed_sampler_identity_and_draw_order(alpha):
    damage = np.array([1.0, 0.2, 0.0, 0.0])
    mass = np.array([1.0, 2.0, 3.0, 4.0])
    strata = RUNNER.make_strata(damage, mass)
    first = RUNNER.draw_stratified(np.random.Generator(np.random.PCG64(7 + RUNNER.SAMPLE_SEED_OFFSET)), strata, alpha)
    second = RUNNER.draw_stratified(np.random.Generator(np.random.PCG64(7 + RUNNER.SAMPLE_SEED_OFFSET)), strata, alpha)
    np.testing.assert_array_equal(first[0], second[0])
    np.testing.assert_array_equal(first[1], second[1])
    assert len(first[0]) == RUNNER.ALLOCATIONS[alpha][0]
    assert len(first[1]) == RUNNER.ALLOCATIONS[alpha][1]
    assert set(first[0]).issubset({0, 1})
    assert set(first[1]).issubset({2, 3})


def test_stratified_loss_preserves_full_mass_objective_for_stratum_means():
    active = torch.tensor([2.0, 2.0], dtype=torch.float64)
    background = torch.tensor([5.0, 5.0], dtype=torch.float64)
    got = RUNNER.stratified_loss(active, background, 0.25, 0.75)
    expected = (0.25 * 2.0 + 0.75 * 5.0) / abs(RUNNER.US) ** 2
    torch.testing.assert_close(got, torch.tensor(expected, dtype=torch.float64))


def test_protocol_is_two_state_seed7_final_only():
    assert tuple(RUNNER.EXPECTED) == ("c20s4", "c60s4", "c83s4")
    assert RUNNER.SEEDS == (7,)
    assert RUNNER.STEPS == 10_000
    assert all(sum(pair) == RUNNER.BATCH_NODES for pair in RUNNER.ALLOCATIONS.values())
    assert RUNNER.MONITOR_STEPS == tuple(range(0, 10_001, 1_000))


def _write_run(root, state, displacement, *, alpha="0.7", arm="localized", mutation=None):
    seed = 7
    run = root / f"{state}-seed7-{arm}"
    run.mkdir()
    checkpoint = run / "final_step_10000.pt"
    data=AGG.validate_reference(state,root)
    geometry=RUNNER.anchor_component_geometry(data["xy"],data["damage"],data["conn"],data["mass"])
    torch.save({
        "protocol_revision": RUNNER.PROTOCOL_REVISION, "state": state, "seed": seed, "alpha": alpha, "arm": arm,
        "step": RUNNER.STEPS,
        "sampler": {
            "damage_threshold": RUNNER.DAMAGE_THRESHOLD,
            "n_damage": RUNNER.ALLOCATIONS[alpha][0], "n_background": RUNNER.ALLOCATIONS[alpha][1],
            "sample_seed": seed + RUNNER.SAMPLE_SEED_OFFSET,
            "order": "damage_then_background_no_shuffle",
        },
        "geometry":geometry, "parameter_count":RUNNER.PARAMETER_COUNT,
        "model_state_dict":RUNNER.build_model(7,arm,geometry).state_dict(),
    }, checkpoint)
    prediction = run / "prediction.npz"
    uv = np.zeros((86_756,2)); uv[:,0] = displacement * RUNNER.US
    np.savez_compressed(prediction, uv=uv)
    monitoring = run / "monitoring.json"
    trace = [{
        "step": step, "full_field_loss": displacement ** 2,
        "displacement_mass_rms_over_abs_Us": displacement,
        "active_contribution": displacement ** 2 * 0.02,
        "background_contribution": displacement ** 2 * 0.98,
        "p_damage": .02, "p_background": .98,
        "damage_conditional_rms_over_abs_Us": displacement,
        "background_conditional_rms_over_abs_Us": displacement,
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
        "state": state, "seed": seed, "alpha": alpha, "arm": arm, "reference_sha256": RUNNER.EXPECTED[state],
        "reference_sha256_after": RUNNER.EXPECTED[state],
        "checkpoint_sha256": _sha(checkpoint), "prediction_sha256": _sha(prediction),
        "monitoring_sha256": _sha(monitoring), "steps": RUNNER.STEPS,
        "batch_nodes": RUNNER.BATCH_NODES, "n_damage": RUNNER.ALLOCATIONS[alpha][0],
        "n_background": RUNNER.ALLOCATIONS[alpha][1], "damage_threshold": RUNNER.DAMAGE_THRESHOLD,
        "p_damage": 0.02, "p_background": 0.98, "damage_node_count": 100,
        "background_node_count": 86_656, "sample_seed": seed + RUNNER.SAMPLE_SEED_OFFSET,
        "sample_order": "damage_then_background_no_shuffle", "final_scheduler_lr": 1e-5,
        "training": True, "metrics": metrics,
        "geometry":geometry, "parameter_count":RUNNER.PARAMETER_COUNT,
    }
    metrics_path = run / "metrics.json"
    metrics_path.write_text(json.dumps(record))
    receipt = {
        "status": "COMPLETED", "run_id": run.name,
        "protocol_revision": RUNNER.PROTOCOL_REVISION, "state": state, "seed": seed, "alpha": alpha, "arm": arm,
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


def _matrix(root, candidate=.0008, control=.0012):
    for state in RUNNER.EXPECTED:
        _write_run(root,state,candidate,arm="localized")
        _write_run(root,state,control,arm="control")


def test_primary_pass_matched_localization_comparison(tmp_path):
    _matrix(tmp_path)
    rows,summary=AGG.aggregate(tmp_path,"a"*40)
    assert len(rows)==6
    assert summary["verdict"]=="GLOBAL_LOCAL_THREE_STATE_UV_FIT_SCREEN_PASS"
    assert summary["localization_helps_all_three"]


def test_component_improvement_cannot_rescue_primary_fail(tmp_path):
    _matrix(tmp_path,candidate=.003,control=.005)
    _,summary=AGG.aggregate(tmp_path,"a"*40)
    assert summary["verdict"]=="GLOBAL_LOCAL_THREE_STATE_UV_FIT_SCREEN_FAIL"
    assert summary["localization_helps_all_three"]


def test_geometry_mutation_is_inadmissible(tmp_path):
    def mutation(record,receipt,monitoring): record["geometry"]["padding"]=.03
    _write_run(tmp_path,"c20s4",.0008,mutation=mutation)
    _,summary=AGG.aggregate(tmp_path,"a"*40)
    assert summary["verdict"]=="INADMISSIBLE"


def test_missing_arm_prevents_primary_claim(tmp_path):
    _write_run(tmp_path,"c20s4",.0008)
    _,summary=AGG.aggregate(tmp_path,"a"*40)
    assert summary["verdict"]=="INCONCLUSIVE"


def test_saved_prediction_disagreement_is_inadmissible(tmp_path):
    def mutation(record,receipt,monitoring):
        prediction=monitoring.parent/"prediction.npz"
        np.savez_compressed(prediction,uv=np.ones((86_756,2)))
        record["prediction_sha256"]=_sha(prediction)
        receipt["prediction_sha256"]=_sha(prediction)
        receipt["archive_file_hashes"][prediction.name]=_sha(prediction)
    _write_run(tmp_path,"c20s4",.0008,mutation=mutation)
    _,summary=AGG.aggregate(tmp_path,"a"*40)
    assert summary["verdict"]=="INADMISSIBLE"
