import importlib.util
from pathlib import Path
import sys

import numpy as np


MODULE_PATH = Path(__file__).parents[1] / "SENS_tensile" / "analyze_hard5_umax_trajectory_reaudit.py"
SPEC = importlib.util.spec_from_file_location("umax_reaudit", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_active_driver_uses_eta_zero_degradation():
    damage = np.array([0.0, 0.5, 1.0])
    raw = np.array([2.0, 2.0, 2.0])
    np.testing.assert_allclose(np.square(1.0 - damage) * raw, [2.0, 0.5, 0.0])


def test_support_metrics_separate_amplitude_and_location():
    reference = np.arange(100, dtype=float)
    candidate = np.roll(reference, 1)
    areas = np.ones(100)
    centroids = np.column_stack([np.arange(100), np.zeros(100)])
    metrics = MODULE.support_metrics(reference, candidate, areas, centroids)
    assert metrics["absolute_area_ratio"] == 1.0
    assert metrics["own_area_ratio"] == 1.0
    assert metrics["absolute_iou"] == 0.0
    assert metrics["own_p99_iou"] == 0.0


def test_identical_state_comparison_is_exact():
    values = np.linspace(0.0, 1.0, 100)
    state = {
        "damage": values,
        "history": values,
        "fatigue": values,
        "raw": values,
        "degradation": values,
        "active": values,
    }
    areas = np.ones(100)
    centroids = np.column_stack([values, values])
    metrics = MODULE.compare_states(state, state, areas, centroids)
    assert metrics["damage_mae"] == 0.0
    assert metrics["active_log_mae"] == 0.0
    assert metrics["absolute_iou"] == 1.0
    assert metrics["own_p99_iou"] == 1.0
