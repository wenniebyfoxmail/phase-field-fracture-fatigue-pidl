import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_evaluate_geometry_assisted_development8_mvp.py"
SPEC = importlib.util.spec_from_file_location("development8_eval", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_exact_physical_coordinates_follow_frozen_convention():
    assert MODULE.physical_coordinate("G[5,0]") == (7.62, 0.0)
    np.testing.assert_allclose(MODULE.physical_coordinate("G[7,4]"), (10.668, 4.0), atol=1e-12)


def test_source_to_physical_corner_mapping_and_internal_point():
    source = [[10, 20], [110, 20], [110, 70], [10, 70]]
    matrix = MODULE.source_to_physical_matrix(source)
    np.testing.assert_allclose(MODULE.transform_point(matrix, [10, 20]), [0, 5], atol=1e-5)
    np.testing.assert_allclose(MODULE.transform_point(matrix, [60, 45]), [7.62, 2.5], atol=1e-5)


def test_metrics_use_linear_p95():
    value = MODULE.metrics([0, 1, 2, 3, 4, 5, 6, 7])
    assert value["median_error_m"] == 3.5
    assert value["p95_error_m"] == np.quantile(np.arange(8), 0.95, method="linear")
    assert value["maximum_error_m"] == 7.0
