from __future__ import annotations

import importlib.util
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_review_lattice_envelope_frame_range.py"
SPEC = importlib.util.spec_from_file_location("ltpp_lattice_envelope", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_main_lattice_run_bridges_one_missing_line_but_not_many():
    positions = [10, 20, 30, 40, 60, 70, 80, 90, 100, 110]
    run = MODULE.main_lattice_run(positions, 10)
    assert run == [40, 60, 70, 80, 90, 100, 110]


def test_snap_uses_strongest_support_inside_fixed_window():
    profile = np.zeros(100, dtype=int)
    profile[53], profile[65] = 9, 20
    index, support = MODULE.snap(profile, 55, 10)
    assert (index, support) == (65, 20)


def test_render_review_draws_visible_purple_frame():
    result = {"status": "REQUIRES_HUMAN_RANGE_REVIEW", "deskew_angle_deg": 0.0, "rectangle_deskewed_px": {"left": 40, "top": 30, "right": 260, "bottom": 120}}
    review = MODULE.render_review("19910610", np.full((160, 320), 255, dtype=np.uint8), result)
    pixel = review[96 + 30, 40]
    assert int(pixel[2]) > 120 and int(pixel[1]) < 80
