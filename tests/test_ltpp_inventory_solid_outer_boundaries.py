from __future__ import annotations

import importlib.util
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_inventory_solid_outer_boundaries.py"
SPEC = importlib.util.spec_from_file_location("ltpp_outer_inventory", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_render_review_marks_all_outer_corners_in_orange():
    image = np.full((300, 900), 255, dtype=np.uint8)
    rendered = MODULE.render_review("19910610", image, (80, 50, 770, 250))
    assert rendered.shape == (395, 900, 3)
    # BGR orange has a high red channel and a low blue channel at the O1 marker.
    pixel = rendered[95 + 50, 80]
    assert int(pixel[2]) > 200 and int(pixel[0]) < 50


def test_sidecar_explicitly_excludes_registration_claims():
    text = MODULE.sidecar("19910610", True)
    assert "not a crop" in text
    assert "does not qualify 2-D registration" in text


def test_no_candidate_review_has_no_invented_frame():
    image = np.full((300, 900), 255, dtype=np.uint8)
    rendered = MODULE.render_no_candidate_review("19980407", image, "no candidate")
    assert np.all(rendered[95:] == 255)


def test_contact_sheet_has_eight_fixed_cells():
    review = np.full((100, 200, 3), 255, dtype=np.uint8)
    sheet = MODULE.contact_sheet([(str(index), review) for index in range(8)])
    assert sheet.shape == (1920, 2200, 3)
