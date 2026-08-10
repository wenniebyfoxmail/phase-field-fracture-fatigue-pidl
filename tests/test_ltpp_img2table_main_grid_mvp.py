from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_img2table_main_grid_mvp.py"
SPEC = importlib.util.spec_from_file_location("ltpp_img2table_main_grid", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


try:
    MODULE.line_detector()
except ModuleNotFoundError:
    pytest.skip("img2table is installed only in the frozen MVP environment", allow_module_level=True)


def test_frozen_suite_has_the_required_adversaries():
    outcomes = {name: expected for name, _image, expected in MODULE.synthetic_fixtures()}
    assert outcomes == {
        "canonical": "selected",
        "translated_scaled": "selected",
        "large_summary": "selected",
        "dense_summary": "selected",
        "repair_rectangles": "no_candidate",
        "missing_outer": "no_candidate",
        "broken_internal": "no_candidate",
        "nested_borders": "no_candidate",
        "exact_tie": "no_candidate",
        "wrong_ratio": "no_candidate",
        "no_grid": "no_candidate",
    }


def test_canonical_lattice_selects_mechanical_four_corners():
    image = MODULE.blank()
    MODULE.draw_lattice(image, (160, 220), 120, 80)
    result = MODULE.select_candidate(image)
    assert result["status"] == "CANDIDATE_SELECTED__REQUIRES_HUMAN_REVIEW"
    candidate = result["candidate"]
    assert (candidate["Nv"], candidate["Nh"], candidate["I"]) == (11, 6, 66)
    assert candidate["corners_px"]["top_left"] == [160, 220]


def test_exact_tie_fails_closed():
    image = MODULE.blank()
    MODULE.draw_lattice(image, (80, 180), 65, 43)
    MODULE.draw_lattice(image, (920, 180), 65, 43)
    result = MODULE.select_candidate(image)
    assert result["status"] == "NO_CANDIDATE__FAIL_CLOSED"
    assert result["reason"] == "exact eligible ranking tie"


def test_non_damage_only_code_path_has_no_ocr_or_public_table_extraction():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "Image.extract_tables" not in source
    assert "TableExtractor(" not in source
    assert "from img2table.ocr" not in source
    assert np.isclose(MODULE.TARGET_ASPECT, 3.048)


def test_degenerate_component_fails_closed_without_ranking_exception():
    horizontal = SimpleNamespace(x1=100, y1=100, x2=100, y2=100)
    vertical = SimpleNamespace(x1=100, y1=100, x2=100, y2=100)
    result = MODULE.evaluate_component({"horizontal": [horizontal], "vertical": [vertical], "points": [(100, 100)]})
    assert result["eligible"] is False
    assert result["reason"] == "topology;span_coverage;regularity;aspect"
    assert result["rank"][-1] == 10**18
