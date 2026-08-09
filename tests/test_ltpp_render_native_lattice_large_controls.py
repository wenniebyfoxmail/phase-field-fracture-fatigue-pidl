from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_render_native_lattice_large_controls.py"
SPEC = importlib.util.spec_from_file_location("ltpp_large_lattice", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_large_renderer_places_green_center_with_black_and_white_rim():
    image = np.full((80, 120), 255, dtype=np.uint8)
    evidence = {"deskew_angle_deg": 0.0, "vertical_lattice": {"positions_px": [40]}, "horizontal_lattice": {"positions_px": [30]}, "intersections_px": [[40, 30]]}
    rendered = MODULE.render_large(image, evidence, "test")
    y = 78 + 30
    assert tuple(rendered[y, 40]) == (0, 220, 0)
    assert tuple(rendered[y, 50]) == (0, 0, 0)
    assert tuple(rendered[y, 52]) == (255, 255, 255)
