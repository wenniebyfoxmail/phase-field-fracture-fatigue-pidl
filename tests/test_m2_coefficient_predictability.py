from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


SENS = Path(__file__).parents[1] / "SENS_tensile"
sys.path.insert(0, str(SENS))
import analyze_m2_coefficient_predictability as module  # noqa: E402


def test_weighted_stats_and_feature_dimension() -> None:
    cells = 25
    areas = np.linspace(1.0, 2.0, cells)
    basis = np.eye(cells)[:20]
    sqrtw = np.sqrt(areas / areas.sum())
    field = np.linspace(0.1, 1.0, cells)
    case = {
        "cycles": np.array([1]), "spec": {"umax": 0.12},
        "pidl_fields": {"damage": field[None], "history": (2 * field)[None],
                        "raw_log10": (3 * field)[None], "active": (4 * field)[None]},
    }
    means = {name: np.zeros(cells) for name in ("damage", "history", "raw_log10", "active_log10")}
    vector = module.feature_vector(case, 0, areas, sqrtw, basis, means)
    assert vector.shape == (99,)
    assert np.all(np.isfinite(vector))


def test_ridge_recovers_linear_multioutput_map() -> None:
    rng = np.random.default_rng(4)
    x = rng.normal(size=(200, 12))
    weights = rng.normal(size=(12, 5))
    y = np.einsum("ni,ik->nk", x, weights, optimize=False) + np.array([1.0, -2.0, 0.5, 0.0, 3.0])
    model = module.ridge_fit(x, y, 1.0e-6)
    prediction = module.ridge_predict(model, x)
    assert np.sqrt(np.mean((prediction - y) ** 2)) < 1.0e-6


def test_masked_coefficients_keep_minimum_norm_solution() -> None:
    areas = np.ones(3)
    sqrtw = np.sqrt(areas / areas.sum())
    basis = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    coefficients, rank = module.masked_coefficients(
        np.array([2.0, 5.0, 9.0]), np.zeros(3), sqrtw, basis, areas,
        np.array([True, False, False])
    )
    assert rank == 1
    assert np.isfinite(coefficients).all()


def test_decision_priority() -> None:
    passed = {"identified": True, "pass_upper97p5_lt_0p90": True}
    failed = {"identified": True, "pass_upper97p5_lt_0p90": False}
    unknown = {"identified": False, "pass_upper97p5_lt_0p90": False}
    assert module.decide([passed, failed, unknown]) == "negative"
    assert module.decide([passed, passed, unknown]) == "inconclusive"
    assert module.decide([passed, passed, passed]) == "supports"
