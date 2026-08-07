import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_run_exploratory_grid_registration_mvp.py"
SPEC = importlib.util.spec_from_file_location("ltpp_exploratory_grid_mvp", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_diagonal_model_maps_synthetic_grid_exactly():
    source = np.array(((10, 20), (20, 20), (10, 40), (20, 40)), dtype=float)
    target = np.array(((0, 0), (100, 0), (0, 100), (100, 100)), dtype=float)
    matrix = MODULE.fit_diagonal(source, target)
    assert np.max(np.abs(MODULE.apply(matrix, source) - target)) < 1e-10


def test_controls_have_66_points_and_keep_v2_reservations_out_of_fit_and_dev():
    image = np.full((500, 1524, 3), 255, dtype=np.uint8)
    rows = MODULE.controls(image)
    assert len(rows) == 66
    assert sum(row["role"] == "reserved_v2_excluded" for row in rows) == 16
    assert sum(row["role"] == "development" for row in rows) == 8
    assert sum(row["role"] == "fit" for row in rows) == 42


def test_development_points_do_not_overlap_v2_reserved_points():
    assert not MODULE.DEVELOPMENT & MODULE.V2_RESERVED
