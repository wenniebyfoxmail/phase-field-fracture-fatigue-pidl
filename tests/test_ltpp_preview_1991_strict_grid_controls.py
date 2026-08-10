from __future__ import annotations

import importlib.util
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_preview_1991_strict_grid_controls.py"
SPEC = importlib.util.spec_from_file_location("ltpp_strict_grid", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_axis_dash_evidence_accepts_repeated_short_dashes_and_rejects_continuous_ink():
    image = np.full((120, 160), 255, dtype=np.uint8)
    for x in range(28, 132, 9):
        image[58:61, x:x + 3] = 0
    accepted = MODULE.axis_dash_evidence(image, 80, 60, "x", 60)
    assert accepted["accepted"]
    image[58:61, 58:103] = 0
    rejected = MODULE.axis_dash_evidence(image, 80, 60, "x", 60)
    assert not rejected["accepted"]


def test_strict_controls_excludes_lattice_edges():
    image = np.full((200, 300), 255, dtype=np.uint8)
    evidence = {"vertical_lattice": {"pitch_px": 50, "positions_px": [20, 250]}, "horizontal_lattice": {"pitch_px": 50, "positions_px": [20, 170]}}
    accepted, rejected = MODULE.strict_controls(image, evidence)
    assert not accepted and not rejected
