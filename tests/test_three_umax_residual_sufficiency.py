from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


RUNNER = Path(__file__).parents[1] / "SENS_tensile" / "analyze_three_umax_residual_sufficiency.py"
SPEC = importlib.util.spec_from_file_location("residual_sufficiency", RUNNER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_weighted_quantile_and_support_metrics() -> None:
    areas = np.array([1.0, 1.0, 2.0, 6.0])
    reference = np.array([0.0, 1.0, 2.0, 3.0])
    candidate = np.array([0.0, 1.0, 2.5, 3.5])
    assert MODULE.weighted_quantile(reference, areas, 0.5) == 3.0
    metrics = MODULE.support_metrics(reference, candidate, areas, 0.5)
    assert metrics["threshold"] == 3.0
    assert metrics["iou_absolute"] == 1.0
    assert metrics["absolute_area_ratio"] == 1.0


def test_pod_basis_uses_total_training_energy() -> None:
    train = np.array(
        [
            [1.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0],
            [0.0, 0.5, 0.0],
            [0.0, -0.5, 0.0],
        ],
        dtype=np.float32,
    )
    mean, sqrtw, basis, singular, total_energy = MODULE.pod_basis(
        train, np.ones(3), max_rank=1
    )
    assert basis.shape == (1, 3)
    assert np.allclose(mean, 0.0)
    assert np.isclose(total_energy, 2.5 / 3.0)
    assert np.isclose(float(singular[0] ** 2 / total_energy), 0.8)
    reconstruction, effective_rank = MODULE.oracle_projection(
        train[0], mean, sqrtw, basis, np.ones(3), None
    )
    assert effective_rank == 1
    baseline = np.sqrt(np.mean(train[0] ** 2))
    error = np.sqrt(np.mean((train[0] - reconstruction) ** 2))
    assert error / baseline < 1.0e-6


def test_pod_basis_is_stable_for_ill_conditioned_low_rank_data() -> None:
    rng = np.random.default_rng(3)
    left = rng.normal(size=(40, 3))
    right = rng.normal(size=(3, 25))
    train = left @ np.diag([1.0, 1.0e-6, 1.0e-10]) @ right
    _, _, basis, _, _ = MODULE.pod_basis(train, np.linspace(1.0, 2.0, 25), max_rank=20)
    assert 1 <= len(basis) <= 3
    assert np.max(np.abs(basis @ basis.T - np.eye(len(basis)))) < 1.0e-10


def test_pod_basis_rejects_zero_energy() -> None:
    with np.testing.assert_raises_regex(ValueError, "zero energy"):
        MODULE.pod_basis(np.ones((25, 8)), np.ones(8), max_rank=20)


def test_masked_oracle_optimizes_the_masked_metric() -> None:
    train = np.array([[1.0, 0.0, 1.0], [-1.0, 0.0, -1.0], [0.5, 0.0, 0.5]])
    areas = np.ones(3)
    mean, sqrtw, basis, _, _ = MODULE.pod_basis(train, areas, max_rank=1)
    residual = np.array([2.0, 100.0, 2.0])
    mask = np.array([True, False, True])
    _, error, ratio, effective_rank = MODULE.oracle_error_ratio(
        residual, mean, sqrtw, basis, areas, mask
    )
    assert effective_rank == 1
    assert error < 1.0e-12
    assert ratio < 1.0e-12


def test_masked_oracle_keeps_defined_residual_when_coefficients_are_nonunique() -> None:
    mean = np.zeros(3)
    areas = np.ones(3)
    sqrtw = np.sqrt(areas / areas.sum())
    basis = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    residual = np.array([2.0, 5.0, 9.0])
    mask = np.array([True, False, False])
    _, error, ratio, effective_rank = MODULE.oracle_error_ratio(
        residual, mean, sqrtw, basis, areas, mask
    )
    assert effective_rank == 1
    assert error < 1.0e-12
    assert ratio < 1.0e-12


def test_moving_block_bootstrap_is_deterministic() -> None:
    values = np.linspace(0.1, 0.9, 40)
    first = MODULE.moving_block_upper(values, seed=17)
    second = MODULE.moving_block_upper(values, seed=17)
    assert first == second
    assert np.isclose(first[0], 0.5)
    assert first[1] >= first[0]


def test_moving_block_bootstrap_preserves_nonfinite_as_unidentified() -> None:
    values = np.linspace(0.1, 0.9, 40)
    values[10] = np.nan
    assert all(np.isnan(value) for value in MODULE.moving_block_upper(values, seed=17))


def test_phase_label_keeps_c1_c20_as_early() -> None:
    assert MODULE.phase_label(1, 59) == "early_c1_c20"
    assert MODULE.phase_label(20, 59) == "early_c1_c20"
    assert MODULE.phase_label(59, 59) == "event"


def test_runtime_status_priority_keeps_identified_failure_over_unidentified() -> None:
    assert MODULE.status_priority(["FAIL", "UNIDENTIFIED", "PASS"]) == "FAIL"
    assert MODULE.status_priority(["UNIDENTIFIED", "PASS"]) == "UNIDENTIFIED"
    assert MODULE.status_priority(["PASS", "PASS"]) == "PASS"


def test_full_oracle_long_vector_is_finite_under_strict_numpy_errors() -> None:
    cells = 86408
    residual = np.linspace(-1.0, 1.0, cells)
    mean = np.zeros(cells)
    areas = np.linspace(1.0, 2.0, cells)
    sqrtw = np.sqrt(areas / areas.sum())
    basis = np.zeros((20, cells))
    basis[np.arange(20), np.arange(20)] = 1.0
    with np.errstate(all="raise"):
        reconstructed, effective_rank = MODULE.oracle_projection(
            residual, mean, sqrtw, basis, areas, None
        )
    assert effective_rank == 20
    assert np.all(np.isfinite(reconstructed))
