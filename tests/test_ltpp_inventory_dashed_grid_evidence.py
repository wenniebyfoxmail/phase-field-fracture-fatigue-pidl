from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_inventory_dashed_grid_evidence.py"
SPEC = importlib.util.spec_from_file_location("ltpp_dashed_grid_inventory", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_coverage_requires_two_distinct_positions():
    assert MODULE.coverage([], 100) == 0.0
    assert MODULE.coverage([20], 100) == 0.0
    assert MODULE.coverage([20, 80], 100) == 60 / 99


def test_contact_sheet_has_two_columns_and_four_rows():
    import numpy as np

    panel = np.full((20, 30, 3), 255, dtype=np.uint8)
    sheet = MODULE.contact_sheet([(str(index), panel) for index in range(8)])
    assert sheet.shape == (4 * (26 + 289), 2 * 762, 3)
