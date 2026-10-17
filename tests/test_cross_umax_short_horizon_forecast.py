from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np


PATH = Path(__file__).parents[1] / "SENS_tensile" / "run_cross_umax_short_horizon_forecast.py"
SPEC = importlib.util.spec_from_file_location("short_forecast", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_projection_preserves_irreversible_state() -> None:
    previous = np.array([[0.4, -2.0, 0.8, -3.0]])
    candidate = np.array([[0.2, -3.0, 0.9, 20.0]])
    result = MODULE.project(candidate, previous)
    assert result[0, 0] == 0.4
    assert result[0, 1] == -2.0
    assert result[0, 2] == 0.8
    assert result[0, 3] == 8.0


def test_weighted_support_metrics_are_exact_for_identical_fields() -> None:
    state = np.column_stack(
        [np.linspace(0.0, 0.8, 100), np.zeros(100), np.ones(100), np.linspace(-4.0, 1.0, 100)]
    )
    result = MODULE.metrics(state, state, np.ones(100))
    assert result["damage_mae"] == 0.0
    assert result["absolute_p99_iou"] == 1.0
    assert result["own_p99_iou"] == 1.0
    assert result["support_area_ratio"] == 1.0


def test_stiffness_features_use_only_present_and_past() -> None:
    case = MODULE.Case("toy", 0.1, 5, np.zeros((5, 2, 4)), np.array([10.0, 9.0, 8.0, 1.0, 100.0]))
    first = MODULE.stiffness_features(case, 2)
    case.stiffness[3:] = -999.0
    second = MODULE.stiffness_features(case, 2)
    np.testing.assert_allclose(first, second)


def test_constant_columns_are_kept_inert() -> None:
    state = np.zeros((22, 3, 4), dtype=float)
    state[:, :, 1] = -2.0
    state[:, :, 2] = 1.0
    state[:, :, 3] = -3.0
    case = MODULE.Case("toy", 0.1, 22, state, np.linspace(10.0, 8.0, 22))
    _, scale, _, _ = MODULE.equal_trajectory_moments([case], False)
    assert scale[0] == 1.0  # Umax is constant within one ensemble member.
