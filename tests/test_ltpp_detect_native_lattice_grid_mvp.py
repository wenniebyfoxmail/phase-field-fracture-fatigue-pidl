from __future__ import annotations

import importlib.util
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_detect_native_lattice_grid_mvp.py"
SPEC = importlib.util.spec_from_file_location("ltpp_native_lattice", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_lattice_recovers_regular_pitch_despite_one_large_nonperiodic_peak():
    profile = np.zeros(700, dtype=float)
    for index in range(24, 680, 61):
        profile[index] = 10.0
    profile[410] = 100.0  # e.g. a crack / annotation peak: not periodic.
    result = MODULE.lattice_from_profile(profile, 0)
    assert abs(result["pitch_px"] - 61) <= 1
    assert len(result["positions_px"]) >= 9


def test_native_detector_recovers_two_lattice_families_from_high_resolution_grid():
    image = np.full((520, 1100), 255, dtype=np.uint8)
    for x in range(90, 1010, 65):
        for y in range(45, 470, 14):
            cv2.line(image, (x, y), (x, y + 4), 0, 2)
    for y in range(70, 470, 62):
        for x in range(65, 1035, 14):
            cv2.line(image, (x, y), (x + 4, y), 0, 2)
    cv2.line(image, (490, 80), (500, 440), 0, 3)  # non-periodic vertical crack
    detected = MODULE.detect(image)
    assert abs(detected["vertical_lattice"]["pitch_px"] - 65) <= 2
    assert abs(detected["horizontal_lattice"]["pitch_px"] - 62) <= 2
    assert len(detected["intersections_px"]) >= 50
