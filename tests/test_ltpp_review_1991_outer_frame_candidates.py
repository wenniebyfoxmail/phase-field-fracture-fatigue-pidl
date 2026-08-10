from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_review_1991_outer_frame_candidates.py"
SPEC = importlib.util.spec_from_file_location("ltpp_outer_frame", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_draw_polygon_marks_all_four_corners():
    image = np.full((100, 140, 3), 255, dtype=np.uint8)
    corners = np.array([[20, 20], [120, 20], [120, 80], [20, 80]], dtype=np.float32)
    MODULE.draw_polygon(image, corners, (0, 140, 255), "O")
    assert tuple(image[20, 20]) == (0, 140, 255)
    assert tuple(image[80, 120]) == (0, 140, 255)
