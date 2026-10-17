import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_prepare_cross_state_registration_review_packets.py"
SPEC = importlib.util.spec_from_file_location("cross_state_registration_packets", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

SERVER_SCRIPT = ROOT / "scripts" / "ltpp_registration_control_annotator_server.py"
SERVER_SPEC = importlib.util.spec_from_file_location("registration_control_server", SERVER_SCRIPT)
SERVER_MODULE = importlib.util.module_from_spec(SERVER_SPEC)
assert SERVER_SPEC.loader is not None
SERVER_SPEC.loader.exec_module(SERVER_MODULE)


def test_candidate_inventory_and_roles_remain_frozen():
    values = MODULE.candidates()
    assert len(values) == 66
    assert len(set(values)) == 66
    assert sum(MODULE.role_for(value) == "fit" for value in values) == 50
    assert sum(MODULE.role_for(value) == "development" for value in values) == 8
    assert sum(MODULE.role_for(value) == "final_audit" for value in values) == 8


def test_automatic_window_crop_is_fixed_margin_half_open_and_clipped():
    row = {"x0": 20.2, "y0": 30.7, "x1": 180.0, "y1": 90.1}
    assert MODULE.crop_bounds(row, (120, 220)) == (0, 0, 220, 120)
    interior = {"x0": 100.2, "y0": 100.7, "x1": 300.0, "y1": 200.1}
    assert MODULE.crop_bounds(interior, (400, 500)) == (52, 52, 349, 250)


def test_blank_records_are_empty_unlocked_and_hold_status():
    record = MODULE.blank_record("A01", MODULE.candidates())
    assert record["packet_status"] == MODULE.STATUS
    assert record["locked"] is False
    assert len(record["tasks"]) == 66
    assert all(task == {"status": None, "click_crop_px": None, "note": ""} for task in record["tasks"].values())


def test_invalid_automatic_window_is_rejected():
    with pytest.raises(ValueError, match="unordered"):
        MODULE.crop_bounds({"x0": 5, "y0": 2, "x1": 4, "y1": 8}, (200, 300))


def test_annotator_server_accepts_explicit_fourteen_map_role(tmp_path):
    records = tmp_path / "records"
    records.mkdir()
    for index in range(1, 15):
        (records / f"A{index:02d}.json").write_text("{}\n", encoding="utf-8")
    assert len(SERVER_MODULE.discover_blind_ids(records, "annotator_a", 14)) == 14
    with pytest.raises(ValueError, match="exactly 8"):
        SERVER_MODULE.discover_blind_ids(records, "annotator_a", 8)
