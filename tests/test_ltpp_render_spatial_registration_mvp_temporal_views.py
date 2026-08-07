import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_render_spatial_registration_mvp_temporal_views.py"
SPEC = importlib.util.spec_from_file_location("ltpp_temporal_views", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_pair_views_preserve_shape_and_compute_absolute_difference():
    earlier = np.zeros((3, 4, 3), dtype=np.uint8)
    later = np.full((3, 4, 3), 100, dtype=np.uint8)
    blend, difference = MODULE.pair_views(earlier, later)
    assert blend.shape == earlier.shape
    assert difference.shape == earlier.shape
    assert int(blend[0, 0, 0]) == 50
    assert int(difference[0, 0, 0]) == 100


def test_pair_views_reject_mismatched_shapes():
    try:
        MODULE.pair_views(np.zeros((3, 4, 3), dtype=np.uint8), np.zeros((4, 4, 3), dtype=np.uint8))
    except ValueError as exc:
        assert "same-size" in str(exc)
    else:
        raise AssertionError("mismatched inputs must fail")
