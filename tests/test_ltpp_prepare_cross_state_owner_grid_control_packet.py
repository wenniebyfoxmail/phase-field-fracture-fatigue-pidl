import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_prepare_cross_state_owner_grid_control_packet.py"
SPEC = importlib.util.spec_from_file_location("cross_state_owner_grid", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_rectangle_corners_are_tl_tr_br_bl():
    row = {"x0": 10, "y0": 20, "x1": 110, "y1": 70}
    assert MODULE.rectangle_corners(row) == [[10, 20], [110, 20], [110, 70], [10, 70]]


def test_all_66_tasks_have_owner_review_state_and_suggestion():
    row = {"x0": 10, "y0": 20, "x1": 110, "y1": 70}
    tasks = MODULE.build_tasks(row, left=0, top=0)
    assert len(tasks) == 66
    assert set(task["status"] for task in tasks.values()) == {"unreviewed"}
    assert tasks["G[0,0]"]["reviewed_crop_px"] == [10.0, 70.0]
    assert tasks["G[10,5]"]["reviewed_crop_px"] == [110.0, 20.0]


def test_unordered_rectangle_fails_closed():
    with pytest.raises(ValueError, match="unordered"):
        MODULE.rectangle_corners({"x0": 10, "y0": 20, "x1": 9, "y1": 70})
