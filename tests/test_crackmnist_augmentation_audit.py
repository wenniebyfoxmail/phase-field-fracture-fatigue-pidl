from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).parents[1] / "scripts" / "crackmnist_augmentation_audit.py"
SPEC = importlib.util.spec_from_file_location("crackmnist_augmentation_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_augmentation_severity_uses_frozen_supports_and_excludes_flip():
    augmentations = np.asarray([
        [20.0, 10.0, 10.0, 0.0],
        [20.0, 10.0, 10.0, 1.0],
        [0.0, 0.0, 0.0, 1.0],
    ])
    severity = MODULE.augmentation_severity(augmentations)
    assert np.allclose(severity, [1.0, 1.0, 0.0])


def test_fixed_effect_association_recovers_joint_coefficients():
    rng = np.random.default_rng(3)
    lineages = np.repeat(np.arange(40), 8)
    severity = rng.uniform(0.0, 1.0, size=len(lineages))
    flip = rng.integers(0, 2, size=len(lineages)).astype(float)
    intercept = np.repeat(rng.normal(size=40), 8)
    outcome = intercept + 2.5 * severity - 1.25 * flip
    result = MODULE.fixed_effect_association(
        outcome, severity, flip, lineages, bootstrap_draws=100, seed=7
    )
    assert result["design_rank"] == 2
    assert np.isclose(result["beta_severity"], 2.5)
    assert np.isclose(result["beta_vertical_flip"], -1.25)
    assert result["n_lineages"] == 40


def test_bootstrap_is_deterministic_and_lineage_clustered():
    rng = np.random.default_rng(8)
    lineages = np.repeat(np.arange(12), 8)
    severity = rng.uniform(size=len(lineages))
    flip = rng.integers(0, 2, size=len(lineages)).astype(float)
    outcome = np.repeat(np.arange(12), 8) + severity + 0.2 * flip
    first = MODULE.fixed_effect_association(
        outcome, severity, flip, lineages, bootstrap_draws=50, seed=11
    )
    second = MODULE.fixed_effect_association(
        outcome, severity, flip, lineages, bootstrap_draws=50, seed=11
    )
    assert first == second
    assert first["n_lineages"] == 12
    assert first["n_rows"] == 96


def test_lineage_contrast_uses_only_observed_extrema():
    rows = MODULE.lineage_contrasts(
        outcome=np.asarray([4.0, 2.0, 8.0, 3.0]),
        severity=np.asarray([0.4, 0.2, 0.9, 0.7]),
        lineage_ids=np.asarray([1, 1, 2, 2]),
        row_idx=np.asarray([10, 11, 20, 21]),
        tip_visible=np.asarray([True, False, True, True]),
    )
    assert rows[0]["low_row_idx"] == 11
    assert rows[0]["high_row_idx"] == 10
    assert rows[0]["high_minus_low_reconstruction_mse_z"] == 2.0
    assert rows[1]["low_row_idx"] == 21
    assert rows[1]["high_row_idx"] == 20
