from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "SENS_tensile"
    / "analyze_hard_recovery_graph_residual_discriminator.py"
)
SPEC = importlib.util.spec_from_file_location("hard_recovery_graph_v2", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_hard_recovery_peak_mapping() -> None:
    assert MODULE.hard_recovery_peak_step(20) == 99
    assert MODULE.hard_recovery_peak_step(69) == 344
    assert MODULE.hard_recovery_peak_step(89) == 444


def test_dual_graph_uses_shared_cell_edges() -> None:
    cells = np.array(
        [
            [0, 1, 4, 3],
            [1, 2, 5, 4],
            [3, 4, 7, 6],
        ],
        dtype=np.int64,
    )
    src, dst = MODULE.build_cell_dual_edges(cells)
    directed = set(zip(src.tolist(), dst.tolist()))
    assert directed == {(0, 1), (1, 0), (0, 2), (2, 0)}


def test_overlap_projection_is_weighted_and_coverage_safe() -> None:
    projection = MODULE.ProjectionMap(
        src=np.array([0, 1, 1], dtype=np.int64),
        dst=np.array([0, 0, 1], dtype=np.int64),
        weight=np.array([1.0, 3.0, 2.0]),
        denominator=np.array([4.0, 2.0, 0.0]),
    )
    result = MODULE.project_to_fem(np.array([2.0, 6.0]), projection, n_fem=3)
    np.testing.assert_allclose(result[:2], [5.0, 6.0])
    assert np.isnan(result[2])


def test_graph_and_mlp_are_parameter_matched() -> None:
    graph = MODULE.MeshResidualNet(
        n_features=12, hidden=16, n_layers=3, dropout=0.0, use_graph=True
    )
    mlp = MODULE.MeshResidualNet(
        n_features=12, hidden=16, n_layers=3, dropout=0.0, use_graph=False
    )
    assert MODULE.model_parameter_count(graph) == MODULE.model_parameter_count(mlp)


def test_feature_transforms_are_finite() -> None:
    values = np.array([-2.0, 0.0, 3.0])
    for mode in ("linear", "log10", "log1p", "signed_log1p"):
        transformed = MODULE.transform_feature(values, mode)
        assert np.all(np.isfinite(transformed))
