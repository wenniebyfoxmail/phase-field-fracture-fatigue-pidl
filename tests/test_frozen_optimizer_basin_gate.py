import importlib.util
from pathlib import Path
import sys

import numpy as np


SCRIPT = Path(__file__).parents[1] / "SENS_tensile" / "run_frozen_optimizer_basin_gate.py"
SPEC = importlib.util.spec_from_file_location("frozen_basin_gate", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_peak_step_respects_recovery_offset():
    settings = {
        "recovery_step_offset": "1",
        "explicit_cycle_factors": "[0.25, 0.5, 0.75, 1.0, 0.0]",
        "umax": "0.12",
    }
    assert MODULE.peak_step(1, settings) == 4
    assert MODULE.peak_step(76, settings) == 379
    assert MODULE.peak_step(89, settings) == 444
    assert MODULE.step_displacement(444, settings) == 0.12


def test_overlap_projection_is_area_weighted():
    projection = {
        "src": np.asarray([0, 1, 1]),
        "dst": np.asarray([0, 0, 1]),
        "weight": np.asarray([0.25, 0.75, 1.0]),
        "overlap_area": np.asarray([1.0, 1.0]),
    }
    out = MODULE.project_to_fem(np.asarray([2.0, 6.0]), projection)
    np.testing.assert_allclose(out, [5.0, 6.0])


def test_support_metrics_penalize_diffuse_absolute_support():
    reference = np.zeros(100)
    reference[-1] = 10.0
    prediction = np.full(100, 10.0)
    metrics = MODULE.support_metrics(prediction, reference, np.ones(100))
    assert metrics["active_support_area_ratio"] > 10.0
    assert metrics["active_absolute_p99_iou"] < 0.1


def test_parameter_perturbation_is_deterministic():
    import torch

    first = torch.nn.Linear(2, 3)
    second = torch.nn.Linear(2, 3)
    second.load_state_dict(first.state_dict())
    MODULE.perturb_parameters(first, 1.0e-3, 7)
    MODULE.perturb_parameters(second, 1.0e-3, 7)
    for left, right in zip(first.parameters(), second.parameters()):
        torch.testing.assert_close(left, right)
