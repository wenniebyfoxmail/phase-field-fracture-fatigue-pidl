from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).parents[1] / "scripts" / "crackmnist_mechanics_cv.py"
SPEC = importlib.util.spec_from_file_location("crackmnist_mechanics_cv", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_energy_coordinate_shape_and_finiteness():
    rng = np.random.default_rng(1)
    images = rng.normal(size=(3, 2, 28, 28)).astype(np.float32)
    coordinates = MODULE.energy_coordinates(images)
    assert coordinates.shape == (3, 2)
    assert np.isfinite(coordinates).all()
    assert ((coordinates >= 0) & (coordinates <= 27)).all()


def test_ridge_shortcut_exact_linear_recovery():
    rng = np.random.default_rng(2)
    x = rng.normal(size=(100, 4))
    y = np.column_stack([x[:, 0] + 2 * x[:, 1], x[:, 2], 3 * x[:, 3]])
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    z = (x - mean) / scale
    design = np.column_stack([np.ones(len(x)), z])
    coef = np.linalg.solve(design.T @ design + np.diag([0, 1e-9, 1e-9, 1e-9, 1e-9]), design.T @ y)
    model = MODULE.RidgeShortcut(mean, scale, coef)
    assert np.max(np.abs(model.predict(x) - y)) < 1e-7


def test_model_forward_contract():
    import torch
    model = MODULE.build_model()
    heatmap, sif = model(torch.zeros(2, 2, 28, 28))
    assert heatmap.shape == (2, 784)
    assert sif.shape == (2, 3)


def test_failure_auroc_direction():
    confidence = np.asarray([0.9, 0.8, 0.2, 0.1])
    failure = np.asarray([False, False, True, True])
    assert MODULE.failure_auroc(confidence, failure) == 1.0


def test_prediction_set_stats_weights_lineages_equally():
    probability = np.zeros((3, 784), dtype=np.float64)
    probability[:, 0] = [0.9, 0.9, 0.1]
    probability[:, 1] = 1 - probability[:, 0]
    target = np.asarray([0, 0, 0])
    coverage, _ = MODULE.prediction_set_stats(
        probability, target, 0.5, np.asarray([10, 10, 11])
    )
    assert coverage == 0.5
