import importlib.util
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_run_spatial_registration_mvp.py"
SPEC = importlib.util.spec_from_file_location("ltpp_registration_mvp", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_frame_homography_maps_corners_to_frozen_canvas_without_flip():
    image = np.full((600, 1200, 3), 255, dtype=np.uint8)
    frame = np.float32(((100, 50), (1100, 50), (1100, 550), (100, 550)))
    warped, matrix = MODULE.warp_from_frame(image, frame)
    assert warped.shape == (500, 1524, 3)
    assert MODULE.reprojection_error_px(matrix, frame) < 1e-4
    assert MODULE.centre_jacobian_determinant(matrix, frame) > 0


def test_source_frame_rejects_reversed_corners():
    row = {"survey_date": "x", "x0": 10, "x1": 5, "y0": 1, "y1": 2}
    try:
        MODULE.source_frame(row)
    except ValueError as exc:
        assert "non-physical" in str(exc)
    else:
        raise AssertionError("reversed frame must fail")


def test_grid_overlay_preserves_canvas_shape():
    image = np.zeros((500, 1524, 3), dtype=np.uint8)
    assert MODULE.registered_grid_overlay(image).shape == image.shape
