import importlib.util
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import torch


RUNNER = Path(__file__).parents[1] / "SENS_tensile" / "run_s04_e013_stage1_supervised.py"
SPEC = importlib.util.spec_from_file_location("s04_e013_stage1", RUNNER)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

AGGREGATE_PATH = Path(__file__).parents[1] / "SENS_tensile" / "aggregate_s04_e013_stage1.py"
AGGREGATE_SPEC = importlib.util.spec_from_file_location("s04_e013_stage1_aggregate", AGGREGATE_PATH)
AGGREGATE = importlib.util.module_from_spec(AGGREGATE_SPEC)
assert AGGREGATE_SPEC.loader is not None
AGGREGATE_SPEC.loader.exec_module(AGGREGATE)


def test_coordinate_normalization_uses_locked_global_bounds_for_subsets():
    xy = torch.tensor([[0.0, 0.0], [0.25, -0.25]], dtype=torch.float64)
    got = MODULE.normalize_xy(xy)
    torch.testing.assert_close(got, torch.tensor([[0.0, 0.0], [0.5, -0.5]], dtype=torch.float64))


def test_sens_ansatz_imposes_exact_boundary_conditions():
    xy = torch.tensor(
        [[-0.5, -0.5], [0.0, -0.5], [0.5, 0.5], [0.0, 0.5], [0.2, 0.0]],
        dtype=torch.float64,
    )
    raw = torch.tensor(
        [[3.0, -2.0], [1.0, 4.0], [-7.0, 8.0], [2.0, -5.0], [0.4, -0.2]],
        dtype=torch.float64,
    )
    uv = MODULE.apply_sens_bc(raw, xy)
    torch.testing.assert_close(uv[:2], torch.zeros((2, 2), dtype=torch.float64), rtol=0, atol=0)
    torch.testing.assert_close(uv[2:, 0][:2], torch.zeros(2, dtype=torch.float64), rtol=0, atol=0)
    torch.testing.assert_close(
        uv[2:, 1][:2], torch.full((2,), MODULE.US, dtype=torch.float64), rtol=0, atol=0
    )


def test_sens_ansatz_uses_locked_global_bounds_for_interior_minibatch():
    xy = torch.tensor([[0.0, -0.25], [0.0, 0.25]], dtype=torch.float64)
    raw = torch.zeros((2, 2), dtype=torch.float64)
    uv = MODULE.apply_sens_bc(raw, xy)
    torch.testing.assert_close(
        uv[:, 1], torch.tensor([0.25 * MODULE.US, 0.75 * MODULE.US], dtype=torch.float64),
        rtol=0, atol=1e-18,
    )


def test_native_q4_strain_reproduces_affine_engineering_strain():
    xy = np.array([[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]])
    conn = np.array([[0, 1, 2, 3]], dtype=np.int64)
    # u=2x+3y, v=-x+4y -> [eps_xx, eps_yy, gamma_xy] = [2,4,2]
    uv = np.column_stack((2 * xy[:, 0] + 3 * xy[:, 1], -xy[:, 0] + 4 * xy[:, 1]))
    strain = MODULE.q4_strain(xy, conn, uv)
    np.testing.assert_allclose(strain, np.broadcast_to([2.0, 4.0, 2.0], strain.shape), atol=1e-14)


def test_model_initialization_is_repeatable_and_float64():
    first = MODULE.build_model(7)
    second = MODULE.build_model(7)
    for (name_a, value_a), (name_b, value_b) in zip(first.state_dict().items(), second.state_dict().items()):
        assert name_a == name_b
        assert value_a.dtype == torch.float64
        torch.testing.assert_close(value_a, value_b, rtol=0, atol=0)
    coefficients = [p for name, p in first.named_parameters() if name.endswith("coeff")]
    assert len(coefficients) == 8
    assert all(float(value.detach()) == 1.0 for value in coefficients)


def test_formal_train_rejects_non_cuda_before_loop(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    args = type("Args", (), {"device": "cuda"})()
    with pytest.raises(RuntimeError, match="requires --device cuda"):
        MODULE.train(args, {})


def test_contract_has_fixed_matrix_and_final_only_checkpoint():
    assert tuple(MODULE.EXPECTED) == ("c20s4", "c60s4", "c82s4", "c83s4")
    assert MODULE.SEEDS == (1, 7, 19)
    assert MODULE.STEPS == 10_000
    assert MODULE.BATCH_NODES == 16_384


def test_aggregator_marks_missing_matrix_inconclusive(tmp_path):
    rows, summary = AGGREGATE.aggregate(tmp_path, "a" * 40)
    assert rows == []
    assert len(summary["missing"]) == 12
    assert summary["verdict"] == "INCONCLUSIVE"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_run(root, state, seed, *, pass_gate=True, mutation=None, suffix=""):
    run = root / f"{state}-seed{seed}{suffix}"
    run.mkdir()
    checkpoint = run / "final_step_10000.pt"
    torch.save({
        "protocol_revision": MODULE.PROTOCOL_REVISION,
        "state": state,
        "seed": seed,
        "step": MODULE.STEPS,
        "model_state_dict": {},
    }, checkpoint)
    prediction = run / "prediction.npz"
    np.savez_compressed(prediction, uv=np.zeros((86_756, 2)))
    value = 5e-4 if pass_gate else 2e-3
    metrics = {
        "essential_bc_max_abs_error": 0.0,
        "displacement_mass_rms_over_abs_Us": value,
        "strain_error_norm": value,
        "strain_reference_norm": 1.0,
        "strain_relative_l2": value,
        "reference_rho_u": 5e-11,
        "predicted_rho_u": value,
        "gate_finite": True,
        "gate_essential_bc": True,
        "gate_displacement_fit": pass_gate,
        "gate_strain_fit": True,
        "gate_rho_u": pass_gate,
        "joint_pass": pass_gate,
    }
    record = {
        "status": "COMPLETED", "protocol_revision": MODULE.PROTOCOL_REVISION,
        "state": state, "seed": seed, "reference_sha256": MODULE.EXPECTED[state],
        "reference_sha256_after": MODULE.EXPECTED[state], "checkpoint_sha256": _sha(checkpoint),
        "prediction_sha256": _sha(prediction), "steps": MODULE.STEPS,
        "batch_nodes": MODULE.BATCH_NODES, "final_scheduler_lr": 1e-5,
        "training": True, "metrics": metrics,
    }
    metrics_path = run / "metrics.json"
    metrics_path.write_text(json.dumps(record))
    receipt = {
        "status": "COMPLETED", "run_id": run.name,
        "protocol_revision": MODULE.PROTOCOL_REVISION, "state": state, "seed": seed,
        "producer_alias": "taobo", "hostname": "test-host", "code_commit": "a" * 40,
        "dirty": False, "command": "formal command", "gpu": "test-gpu",
        "cuda_visible_devices": "0",
        "output_root": f"/mnt/data2/drtao/wennie/{run.name}/output",
        "archive_root": f"/mnt/data2/drtao/pidl_archives/{run.name}",
        "log_path": f"/mnt/data2/drtao/wennie/{run.name}/run.log",
        "started_utc": "2026-10-08T00:00:00+00:00",
        "finished_utc": "2026-10-08T00:01:00+00:00",
        "checkpoint_sha256": record["checkpoint_sha256"],
        "prediction_sha256": record["prediction_sha256"],
        "metrics_sha256": _sha(metrics_path),
        "reference_sha256": MODULE.EXPECTED[state],
        "archive_status": "VERIFIED_COPY",
        "archive_file_hashes": {
            checkpoint.name: record["checkpoint_sha256"],
            prediction.name: record["prediction_sha256"],
            metrics_path.name: _sha(metrics_path),
        },
    }
    if mutation:
        mutation(record, receipt, checkpoint, prediction)
    metrics_path.write_text(json.dumps(record))
    receipt["metrics_sha256"] = _sha(metrics_path)
    receipt["archive_file_hashes"][metrics_path.name] = _sha(metrics_path)
    (run / "RUN_RECEIPT.json").write_text(json.dumps(receipt))
    return run


def _write_matrix(root, *, failing_pair=None):
    for state in MODULE.EXPECTED:
        for seed in MODULE.SEEDS:
            _write_run(root, state, seed, pass_gate=(state, seed) != failing_pair)


def test_aggregator_accepts_complete_recomputed_12_of_12_pass(tmp_path):
    _write_matrix(tmp_path)
    rows, summary = AGGREGATE.aggregate(tmp_path, "a" * 40)
    assert len(rows) == 12
    assert summary["verdict"] == "SUPERVISED_CAPACITY_PASS"


def test_aggregator_reports_complete_valid_scientific_failure(tmp_path):
    _write_matrix(tmp_path, failing_pair=("c60s4", 7))
    _, summary = AGGREGATE.aggregate(tmp_path, "a" * 40)
    assert summary["verdict"] == "SUPERVISED_CAPACITY_FAIL_FIXED_PROCEDURE"
    assert summary["joint_passes"] == 11


@pytest.mark.parametrize(
    "kind", ["joint", "nonfinite", "checkpoint", "prediction", "receipt", "steps", "reference"]
)
def test_aggregator_marks_malformed_evidence_inadmissible(tmp_path, kind):
    def mutate(record, receipt, checkpoint, prediction):
        if kind == "joint":
            record["metrics"]["joint_pass"] = "false"
        elif kind == "nonfinite":
            record["metrics"]["predicted_rho_u"] = float("nan")
        elif kind == "checkpoint":
            checkpoint.unlink()
        elif kind == "prediction":
            prediction.unlink()
        elif kind == "receipt":
            receipt["code_commit"] = "b" * 40
        elif kind == "steps":
            record["steps"] = 9999
        elif kind == "reference":
            record["reference_sha256_after"] = "0" * 64
    _write_run(tmp_path, "c20s4", 1, mutation=mutate)
    _, summary = AGGREGATE.aggregate(tmp_path, "a" * 40)
    assert summary["verdict"] == "INADMISSIBLE"
    assert summary["integrity_errors"]


def test_aggregator_marks_duplicate_pair_inadmissible(tmp_path):
    _write_run(tmp_path, "c20s4", 1)
    _write_run(tmp_path, "c20s4", 1, suffix="-duplicate")
    _, summary = AGGREGATE.aggregate(tmp_path, "a" * 40)
    assert summary["verdict"] == "INADMISSIBLE"
