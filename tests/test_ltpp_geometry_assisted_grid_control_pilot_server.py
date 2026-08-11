import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_geometry_assisted_grid_control_pilot_server.py"
SPEC = importlib.util.spec_from_file_location("grid_pilot", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_task_order_has_all_66_points_and_starts_top_left():
    values = MODULE.task_order()
    assert len(values) == 66
    assert len(set(values)) == 66
    assert values[0] == "G[0,5]"
    assert values[-1] == "G[10,0]"


def test_development8_profile_is_exactly_the_prefrozen_identity_set():
    assert MODULE.task_order("development8") == [
        "G[5,0]", "G[5,5]", "G[0,2]", "G[0,3]",
        "G[10,2]", "G[10,3]", "G[3,1]", "G[7,4]",
    ]


def test_post1991_profile_is_the_exact_seven_date_subseries():
    assert MODULE.POST1991_DATES == (
        "19951024", "19970228", "19980407", "20010913",
        "20030514", "20071106", "20120417",
    )


def test_projective_suggestions_use_i_left_to_right_and_j_bottom_to_top():
    points = [[10, 20], [110, 20], [110, 70], [10, 70]]
    result = MODULE.suggested_source_points(points)
    np.testing.assert_allclose(result["G[0,5]"], [10, 20], atol=1e-3)
    np.testing.assert_allclose(result["G[10,5]"], [110, 20], atol=1e-3)
    np.testing.assert_allclose(result["G[0,0]"], [10, 70], atol=1e-3)
    np.testing.assert_allclose(result["G[10,0]"], [110, 70], atol=1e-3)
    np.testing.assert_allclose(result["G[2,2]"], [30, 50], atol=1e-3)


def test_crop_rule_matches_frozen_48_pixel_margin():
    points = [[100.2, 90.8], [300.1, 91], [301, 200.2], [99.8, 201]]
    assert MODULE.crop_bounds(points, (400, 500)) == (51, 42, 350, 250)
