import importlib.util
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
    rows, summary = AGGREGATE.aggregate(tmp_path)
    assert rows == []
    assert len(summary["missing"]) == 12
    assert summary["verdict"] == "INCONCLUSIVE"
