import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_prepare_owner_carrier_spatial_registration_v2_packets.py"
SPEC = importlib.util.spec_from_file_location("owner_carrier_packets", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_candidate_inventory_and_roles_remain_frozen():
    values = MODULE.candidates()
    assert len(values) == 66
    assert len(set(values)) == 66
    assert sum(MODULE.role_for(value) == "fit" for value in values) == 50
    assert sum(MODULE.role_for(value) == "development" for value in values) == 8
    assert sum(MODULE.role_for(value) == "final_audit" for value in values) == 8


def test_owner_crop_is_fixed_margin_half_open_and_clipped():
    points = [[20.2, 30.7], [180.0, 31.0], [179.8, 90.1], [19.7, 89.9]]
    assert MODULE.crop_bounds(points, (120, 220)) == (0, 0, 220, 120)
    interior = [[100.2, 100.7], [300.0, 101.0], [299.8, 200.1], [99.7, 199.9]]
    assert MODULE.crop_bounds(interior, (400, 500)) == (51, 52, 349, 250)


def test_blank_records_are_empty_unlocked_and_hold_status():
    record = MODULE.blank_record("A01", MODULE.candidates())
    assert record["packet_status"] == MODULE.STATUS
    assert record["locked"] is False
    assert len(record["tasks"]) == 66
    assert all(task == {"status": None, "click_crop_px": None, "note": ""} for task in record["tasks"].values())


def test_invalid_owner_point_inventory_is_rejected():
    with pytest.raises(ValueError, match="exactly four"):
        MODULE.crop_bounds([[1, 2]], (200, 300))
