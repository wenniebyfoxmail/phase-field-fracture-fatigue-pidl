from __future__ import annotations

import importlib.util
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_detect_dashed_grid_intersections.py"
SPEC = importlib.util.spec_from_file_location("ltpp_dashed_grid", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def dashed_line(image: np.ndarray, axis: str, position: int) -> None:
    if axis == "x":
        for y in range(24, image.shape[0] - 24, 12):
            image[y:y + 2, position - 1:position + 2] = 0
    else:
        for x in range(24, image.shape[1] - 24, 12):
            image[position - 1:position + 2, x:x + 2] = 0


def test_dashed_grid_lines_are_accepted_but_solid_crack_is_rejected():
    image = np.full((180, 240), 255, dtype=np.uint8)
    dashed_line(image, "x", 50)
    dashed_line(image, "x", 150)
    dashed_line(image, "y", 55)
    dashed_line(image, "y", 125)
    cv2.line(image, (105, 25), (105, 155), 0, 2)
    detected = MODULE.detect_dashed_grid(image)
    accepted_x = {row["position_px"] for row in detected["x_lines"] if row["accepted_dashed_grid_line"]}
    accepted_y = {row["position_px"] for row in detected["y_lines"] if row["accepted_dashed_grid_line"]}
    rejected_x = {row["position_px"] for row in detected["x_lines"] if "continuous_ink_run" in row["rejection_reasons"]}
    assert any(abs(point - 50) <= 2 for point in accepted_x)
    assert any(abs(point - 150) <= 2 for point in accepted_x)
    assert any(abs(point - 55) <= 2 for point in accepted_y)
    assert any(abs(point - 125) <= 2 for point in accepted_y)
    assert any(abs(point - 105) <= 2 for point in rejected_x)


def test_intersections_only_use_accepted_lines():
    image = np.full((180, 240), 255, dtype=np.uint8)
    dashed_line(image, "x", 50)
    dashed_line(image, "y", 55)
    cv2.line(image, (105, 25), (105, 155), 0, 2)
    detected = MODULE.detect_dashed_grid(image)
    assert any(abs(x - 50) <= 2 and abs(y - 55) <= 2 for x, y in detected["intersections_px"])
    assert not any(abs(x - 105) <= 2 for x, _ in detected["intersections_px"])
