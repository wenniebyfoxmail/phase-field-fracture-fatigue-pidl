import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "mnroad_single_owner_crack_annotator_server.py"
SPEC = importlib.util.spec_from_file_location("mnroad_annotator", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def tiny_jpeg(width=20, height=30):
    # SOI + SOF0 is enough for the dependency-free dimension reader and packet tests.
    return b"\xff\xd8\xff\xc0\x00\x11\x08" + height.to_bytes(2, "big") + width.to_bytes(2, "big") + b"\x03" + b"\x01\x11\x00" * 3 + b"\xff\xd9"


def packet(tmp_path):
    render = tmp_path / "render"
    for date in MODULE.DATES:
        folder = render / date
        folder.mkdir(parents=True)
        for page in range(1, 11):
            (folder / f"page-{page:02d}.jpg").write_bytes(tiny_jpeg())
    output = tmp_path / "packet"
    MODULE.prepare_packet(render, output)
    return output


def feature():
    return {
        "type": "Feature", "geometry": {"type": "LineString", "coordinates": [[1, 2], [3, 4]]},
        "properties": {"segment_id": "S1", "lane": "Driving", "distress_class": "NWP", "severity": "L", "sealed": "no", "mark_owner_date": "current", "confidence": "high", "note": "", "crack_id": "", "change_type": ""},
    }


def test_prepare_has_70_primary_and_14_concealed_repeats(tmp_path):
    output = packet(tmp_path)
    manifest = json.loads((output / "manifest.json").read_text())
    private = json.loads((output / "private_repeat_key.json").read_text())["tasks"]
    assert len(manifest["tasks"]) == 84
    assert sum(not row["is_repeat"] for row in private.values()) == 70
    assert sum(row["is_repeat"] for row in private.values()) == 14
    assert all("is_repeat" not in row and "primary_task_id" not in row for row in manifest["tasks"])
    assert len(list((output / "images").glob("*.jpg"))) == 70
    first = json.loads(next((output / "records").glob("*.geojson")).read_text())
    assert first["no_target_confirmed"] is False


def test_repeat_selection_is_deterministic(tmp_path):
    first = packet(tmp_path / "a")
    second = packet(tmp_path / "b")
    key_a = json.loads((first / "private_repeat_key.json").read_text())
    key_b = json.loads((second / "private_repeat_key.json").read_text())
    assert key_a["tasks"] == key_b["tasks"]


def test_landscape_rotation_follows_source_scan_direction():
    assert MODULE.landscape_rotation_degrees("2017-03-20") == -90
    assert MODULE.landscape_rotation_degrees("2018-03-14") == 90
    assert MODULE.landscape_rotation_degrees("2018-04-27") == 90
    assert MODULE.landscape_rotation_degrees("2018-08-23") == 90
    assert MODULE.landscape_rotation_degrees("2019-03-22") == -90


def test_server_links_each_task_to_previous_same_station(tmp_path):
    output = packet(tmp_path)
    server = MODULE.Server(("127.0.0.1", 0), output)
    try:
        assert server.by_id["M0001"]["previous_task_id"] is None
        assert server.by_id["M0011"]["previous_task_id"] == "M0001"
        assert server.by_id["M0042"]["previous_task_id"] == "M0032"
        assert server.by_id["M0042"]["previous_survey_date"] == "2018-08-23"
    finally:
        server.server_close()


def test_phase_two_navigation_can_exclude_concealed_repeats(tmp_path):
    output = packet(tmp_path)
    server = MODULE.Server(("127.0.0.1", 0), output)
    try:
        primary = [row for row in server.tasks if not row["is_concealed_repeat"]]
        repeats = [row for row in server.tasks if row["is_concealed_repeat"]]
        assert len(primary) == 70
        assert len(repeats) == 14
    finally:
        server.server_close()


def test_cross_time_owner_reference_must_match_previous_task(tmp_path):
    output = packet(tmp_path)
    server = MODULE.Server(("127.0.0.1", 0), output)
    try:
        row = json.loads((output / "records" / "M0042.geojson").read_text())
        row["features"] = [feature()]
        props = row["features"][0]["properties"]
        props.update(
            mark_owner_date="earlier",
            owner_reference_task_id="M0032",
            owner_reference_survey_date="2018-08-23",
            temporal_confirmation="same_station_prior_map",
        )
        MODULE.validate_record(row, server.by_id["M0042"], 1)
        props["owner_reference_task_id"] = "M0031"
        with pytest.raises(ValueError, match="previous same-station"):
            MODULE.validate_record(row, server.by_id["M0042"], 1)
    finally:
        server.server_close()


def test_phase_one_rejects_identity_and_phase_two_requires_it(tmp_path):
    output = packet(tmp_path)
    row = json.loads(next((output / "records").glob("*.geojson")).read_text())
    expected = {"task_id": row["task_id"], "survey_date": row["survey_date"]}
    row["features"] = [feature()]
    MODULE.validate_record(row, expected, 1)
    row["features"][0]["properties"]["crack_id"] = "C001"
    with pytest.raises(ValueError, match="phase 1"):
        MODULE.validate_record(row, expected, 1)
    row["features"][0]["properties"]["change_type"] = "persistent"
    MODULE.validate_record(row, expected, 2)


def test_invalid_geometry_and_lane_are_rejected(tmp_path):
    output = packet(tmp_path)
    row = json.loads(next((output / "records").glob("*.geojson")).read_text())
    expected = {"task_id": row["task_id"], "survey_date": row["survey_date"]}
    row["features"] = [feature()]
    row["features"][0]["geometry"]["coordinates"] = [[1, 2]]
    with pytest.raises(ValueError, match="at least two"):
        MODULE.validate_record(row, expected, 1)
    row["features"][0] = feature(); row["features"][0]["properties"]["lane"] = "unknown_lane"
    with pytest.raises(ValueError, match="lane"):
        MODULE.validate_record(row, expected, 1)


def test_empty_confirmation_cannot_coexist_with_feature(tmp_path):
    output = packet(tmp_path)
    row = json.loads(next((output / "records").glob("*.geojson")).read_text())
    expected = {"task_id": row["task_id"], "survey_date": row["survey_date"]}
    row["features"] = [feature()]
    row["no_target_confirmed"] = True
    with pytest.raises(ValueError, match="confirmed empty"):
        MODULE.validate_record(row, expected, 1)


def test_export_omits_repeats_from_primary_geojson(tmp_path):
    output = packet(tmp_path)
    key = json.loads((output / "private_repeat_key.json").read_text())["tasks"]
    repeat = next(task for task, row in key.items() if row["is_repeat"])
    primary = key[repeat]["primary_task_id"]
    for task in (primary, repeat):
        path = output / "records" / f"{task}.geojson"
        row = json.loads(path.read_text()); row["features"] = [feature()]; MODULE.atomic_json(path, row)
    target = tmp_path / "export"
    summary = MODULE.export_packet(output, target, pixels_per_foot=1.0)
    primary_geojson = json.loads((target / "mnroad_22d2016_primary.geojson").read_text())
    assert len(primary_geojson["features"]) == 1
    assert summary["mean_repeat_total_length_agreement"] == 1.0
    assert summary["median_repeat_symmetric_distance_ft"] == 0.0
    assert summary["completion"]["qc_ready"] is False
    assert summary["repeat_gate"]["crack_id_length_agreement_at_least_0_8"] is None


def test_symmetric_distance_and_crack_id_agreement():
    a, b = feature(), feature()
    a["properties"]["crack_id"] = b["properties"]["crack_id"] = "C001"
    assert MODULE.symmetric_vector_distance([a], [b], 1.0) == 0.0
    assert MODULE.crack_id_length_agreement([a], [b], 1.0) == 1.0
    b["geometry"]["coordinates"] = [[1, 3], [3, 5]]
    assert 0.7 < MODULE.symmetric_vector_distance([a], [b], 1.0) < 1.1
