import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import cv2
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_single_owner_line_annotator_server.py"
SPEC = importlib.util.spec_from_file_location("line_owner", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def record(perspective=0.0):
    rect = {"left": 10.0, "top": 10.0, "right": 1010.0, "bottom": 510.0}
    lines = {}
    for i in range(11):
        top_x = 10 + i * 100
        bottom_x = top_x + perspective * (i - 5)
        lines[f"V{i}"] = {"status": "usable", "points_source_px": [[top_x, 10], [bottom_x, 510]], "note": ""}
    for j in range(6):
        y = 510 - j * 100
        lines[f"H{j}"] = {"status": "usable", "points_source_px": [[10, y], [1010, y]], "note": ""}
    spots = {spot: {"status": "locally_visible", "note": ""} for spot in MODULE.SPOT_IDS}
    return {"automatic_rectangle_source_px": rect, "source_origin_px": [0, 0], "lines": lines, "spot_checks": spots}


def test_perfect_rectangle_derives_66_source_coordinates():
    out = MODULE.derive_and_validate(record(), (600, 1100))
    assert len(out) == 66
    assert out["G[0,0]"]["point_source_px"] == [10.0, 510.0]


def test_mild_perspective_passes():
    assert len(MODULE.derive_and_validate(record(0.4), (600, 1100))) == 66


def test_family_order_reversal_fails():
    row = record()
    row["lines"]["V4"], row["lines"]["V5"] = row["lines"]["V5"], row["lines"]["V4"]
    with pytest.raises(ValueError, match="vertical family order"):
        MODULE.derive_and_validate(row, (600, 1100))


def test_same_family_crossing_inside_rectangle_fails():
    row = record()
    row["lines"]["V0"]["points_source_px"] = [[10, 10], [210, 510]]
    row["lines"]["V1"]["points_source_px"] = [[210, 10], [10, 510]]
    with pytest.raises(ValueError, match="order|crossing"):
        MODULE.derive_and_validate(row, (600, 1100))


def test_duplicate_and_short_span_fail():
    row = record(); row["lines"]["V0"]["points_source_px"] = [[10, 10], [10, 10]]
    with pytest.raises(ValueError, match="duplicate"):
        MODULE.derive_and_validate(row, (600, 1100))
    row = record(); row["lines"]["H0"]["points_source_px"] = [[10, 510], [400, 510]]
    with pytest.raises(ValueError, match="orientation/span"):
        MODULE.derive_and_validate(row, (600, 1100))


def test_unusable_line_propagates_invalid_without_rescue():
    row = record(); row["lines"]["V3"] = {"status": "occluded", "points_source_px": [], "note": ""}
    out = MODULE.derive_and_validate(row, (600, 1100))
    assert all(out[f"G[3,{j}]"]["status"] == "invalid_derived" for j in range(6))


def test_near_parallel_and_out_of_bounds_are_invalid_derived():
    first = MODULE.normalised_line([[0, 0], [1, 1]])
    second = MODULE.normalised_line([[0, 1], [1, 2 + 1e-12]])
    assert MODULE.intersect(first, second) is None
    assert not MODULE.inside_rect((2000, 2000), record()["automatic_rectangle_source_px"])


def test_nonvisible_spot_is_not_claimed_locally_observed():
    row = record(); row["spot_checks"]["G[2,2]"]["status"] = "locally_occluded"
    out = MODULE.derive_and_validate(row, (600, 1100))
    assert out["G[2,2]"]["evidence"] == "derived_geometry__local_print_not_verified"
    assert out["G[2,2]"]["local_status"] == "locally_occluded"


def test_owner_frame_outside_automatic_suggestion_passes():
    row = record()
    row["automatic_rectangle_source_px"] = {"left": 200.0, "top": 10.0, "right": 800.0, "bottom": 510.0}
    out = MODULE.derive_and_validate(row, (600, 1100))
    assert out["G[0,0]"]["status"] == "derived_from_single_owner_lines"
    assert out["G[10,5]"]["status"] == "derived_from_single_owner_lines"


def test_automatic_rectangle_does_not_rescue_point_outside_owner_frame():
    row = record()
    row["automatic_rectangle_source_px"] = {"left": 0.0, "top": 0.0, "right": 1090.0, "bottom": 590.0}
    lines = {line_id: MODULE.normalised_line(task["points_source_px"]) for line_id, task in row["lines"].items()}
    frame = MODULE.owner_frame(lines)
    assert frame is not None
    assert MODULE.inside_rect((1050.0, 250.0), row["automatic_rectangle_source_px"])
    assert not MODULE.inside_owner_frame((1050.0, 250.0), lines, frame)


def test_nonusable_outer_line_has_no_automatic_fallback():
    row = record()
    row["lines"]["V0"] = {"status": "occluded", "points_source_px": [], "note": ""}
    out = MODULE.derive_and_validate(row, (600, 1100))
    assert out["G[0,0]"]["reason"] == "source_line_unusable"
    assert out["G[1,0]"]["reason"] == "owner_frame_unavailable"


def test_initialize_copies_complete_gate_source_with_zero_origin(tmp_path, monkeypatch):
    dates = [f"202601{day:02d}" for day in range(1, 15)]
    point_packet = tmp_path / "point_packet"
    (point_packet / "records").mkdir(parents=True)
    (point_packet / "images").mkdir()
    (point_packet / "input_receipt.json").write_text(
        json.dumps({"inputs": [{"survey_date": date} for date in dates]})
    )
    rows = []
    for index, date in enumerate(dates):
        tasks = {"G[0,0]": {"status": "unreviewed"}}
        (point_packet / "records" / f"{date}.json").write_text(json.dumps({"locked": False, "tasks": tasks}))
        source = tmp_path / f"source_{date}.png"
        image = np.full((120 + index, 240 + index), index, dtype=np.uint8)
        assert cv2.imwrite(str(source), image)
        rows.append({
            "section": "TEST",
            "survey_date": date,
            "source_path": str(source),
            "source_sha256": MODULE.sha256(source),
            "x0": 20,
            "y0": 20,
            "x1": 200,
            "y1": 100,
        })
    monkeypatch.setattr(MODULE.PACKETS, "load_rows", lambda project_root, gate_specs: (rows, [{"test": True}]))
    amendment = tmp_path / "amendment.md"
    amendment.write_text("frozen amendment")
    output = tmp_path / "full_source_packet"
    MODULE.initialize(point_packet, [(tmp_path / "gate.json", "TEST", 14)], amendment, output, tmp_path)
    first = json.loads((output / "records" / f"{dates[0]}.json").read_text())
    assert first["source_origin_px"] == [0, 0]
    assert first["source_image_size_px"] == [240, 120]
    assert MODULE.sha256(output / "images" / f"{dates[0]}.png") == rows[0]["source_sha256"]
