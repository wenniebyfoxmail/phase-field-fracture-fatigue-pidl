import hashlib
import importlib.util
import json
from pathlib import Path

from PIL import Image


SCRIPT = Path(__file__).parents[1] / "scripts" / "ltpp_owner_corner_annotator_server.py"
SPEC = importlib.util.spec_from_file_location("corner_server", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_validate_points_accepts_clockwise_outer_rectangle():
    assert MODULE.validate_points([[10, 10], [190, 12], [188, 90], [11, 88]], 200, 100, True) is None


def test_validate_points_rejects_wrong_order_and_small_shape():
    assert "order" in MODULE.validate_points([[10, 10], [11, 88], [188, 90], [190, 12]], 200, 100, True)
    assert "small" in MODULE.validate_points([[80, 40], [120, 40], [120, 60], [80, 60]], 200, 100, True)


def test_initialize_packet_freezes_eight_images(tmp_path):
    source = tmp_path / "source"
    hashes = {}
    for index, date in enumerate(MODULE.EXPECTED_DATES):
        folder = source / date
        folder.mkdir(parents=True)
        path = folder / "segment_0_50_white.png"
        Image.new("RGB", (200 + index, 100), "white").save(path)
        hashes[date] = hashlib.sha256(path.read_bytes()).hexdigest()
    packet = tmp_path / "packet"
    MODULE.initialize_packet(source, packet, hashes)
    receipt = json.loads((packet / "packet.json").read_text())
    assert receipt["status"] == MODULE.STATUS_INCOMPLETE
    assert len(receipt["inputs"]) == 8
    assert all((packet / "records" / f"{date}.json").is_file() for date in MODULE.EXPECTED_DATES)
    try:
        MODULE.initialize_packet(source, packet, hashes)
    except ValueError as error:
        assert "overwrite" in str(error)
    else:
        raise AssertionError("existing packet must not be overwritten")


def test_finalize_requires_all_dates_locked(tmp_path):
    (tmp_path / "records").mkdir()
    for date in MODULE.EXPECTED_DATES:
        record = MODULE.initial_record(date, "0" * 64, 200, 100)
        (tmp_path / "records" / f"{date}.json").write_text(json.dumps(record))
    assert MODULE.finalize_if_complete(tmp_path) is False
