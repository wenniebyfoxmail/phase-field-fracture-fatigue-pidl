from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_outer_boundary_intersection_topology_mvp_v2.py"
SPEC = importlib.util.spec_from_file_location("ltpp_outer_boundary_topology_v2", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


try:
    MODULE.PRIMITIVES.line_detector()
except ModuleNotFoundError:
    pytest.skip("img2table is installed only in the frozen MVP environment", allow_module_level=True)


def test_frozen_suite_lists_every_required_visual_adversary():
    outcomes = {name: expected for name, _image, expected in MODULE.fixtures()}
    assert outcomes == {
        "fragmented_canonical": "selected",
        "translated_scaled": "selected",
        "page_border_plus_road": "selected",
        "summary_box": "selected",
        "dense_summary": "selected",
        "underline": "selected",
        "crack_like_lines": "selected",
        "repair_rectangles_only": "no",
        "no_crossings": "no",
        "missing_side": "no",
        "wrong_aspect": "no",
        "perspective_quadrilateral": "no",
        "near_axis_crack_like_line": "selected",
        "gap_inside_threshold": "selected",
        "gap_outside_threshold": "no",
        "remote_intersection_corner": "no",
        "crossings_one_region": "no",
        "crossings_two_quartiles": "no",
        "exact_tie": "no",
        "same_frame": "selected",
        "no_rectangle": "no",
    }


def test_all_frozen_numeric_boundary_checks_pass():
    checks = {row["check"]: row["pass"] for row in MODULE.threshold_checks()}
    assert len(checks) == 21
    assert all(checks.values())


def test_boundary_inequality_semantics_are_closed_and_exact():
    assert MODULE.aspect_eligible(MODULE.ASPECT_RANGE[0])
    assert MODULE.aspect_eligible(MODULE.ASPECT_RANGE[1])
    assert not MODULE.aspect_eligible(np.nextafter(MODULE.ASPECT_RANGE[0], 0))
    assert not MODULE.aspect_eligible(np.nextafter(MODULE.ASPECT_RANGE[1], np.inf))
    assert MODULE.merge_intervals([(0, 10), (22, 30)], 12) == ((0, 30),)
    assert MODULE.merge_intervals([(0, 10), (23, 30)], 12) == ((0, 10), (23, 30))


def test_no_ocr_no_crack_and_no_crop_path_is_available():
    source = SCRIPT.read_text(encoding="utf-8").lower()
    for forbidden in ("extract_tables", "tableextractor", "img2table.ocr", "cv2.hough", "linesegmentdetector", "crop("):
        assert forbidden not in source


def test_exact_tie_fails_closed():
    image = MODULE.canvas()
    MODULE.frame(image, (80, 220), 65, 43)
    MODULE.frame(image, (920, 220), 65, 43)
    result = MODULE.select(image)
    assert result["status"] == "NO_CANDIDATE__FAIL_CLOSED"
    assert result["reason"] == "exact eligible ranking tie"
