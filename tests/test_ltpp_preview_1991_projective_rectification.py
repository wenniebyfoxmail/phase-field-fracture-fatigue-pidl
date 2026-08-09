from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_preview_1991_projective_rectification.py"
SPEC = importlib.util.spec_from_file_location("ltpp_twist_preview", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_intersection_recovers_crossing_of_two_nonparallel_lines():
    horizontal = MODULE.line_homogeneous(np.array([0, 10, 100, 10], dtype=float))
    vertical = MODULE.line_homogeneous(np.array([25, 0, 25, 100], dtype=float))
    assert np.allclose(MODULE.intersection(horizontal, vertical), [25, 10])


def test_draw_lattice_marks_a_large_green_center():
    image = np.full((80, 120), 255, dtype=np.uint8)
    evidence = {"vertical_lattice": {"positions_px": [40]}, "horizontal_lattice": {"positions_px": [30]}, "intersections_px": [[40, 30]]}
    rendered = MODULE.draw_lattice(image, evidence)
    assert tuple(rendered[30, 40]) == (0, 220, 0)
