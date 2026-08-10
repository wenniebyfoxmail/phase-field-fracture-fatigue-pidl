from __future__ import annotations

import importlib.util
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_review_1991_solid_outer_boundary.py"
SPEC = importlib.util.spec_from_file_location("ltpp_solid_outer", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_outer_solid_rectangle_uses_enclosing_aspect_compatible_frame():
    image = np.full((300, 900), 255, dtype=np.uint8)
    cv2.rectangle(image, (80, 50), (770, 250), 0, 4)
    rectangle, details = MODULE.outer_solid_rectangle(image)
    left, top, right, bottom = rectangle
    assert abs(left - 80) <= 5 and abs(right - 770) <= 5
    assert abs(top - 50) <= 5 and abs(bottom - 250) <= 5
    assert 3.0 <= details["aspect"] <= 3.6
