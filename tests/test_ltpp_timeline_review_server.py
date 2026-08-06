import importlib.util
import json
import threading
from http import HTTPStatus
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_timeline_review_server.py"
SPEC = importlib.util.spec_from_file_location("ltpp_timeline_review_server", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
PACKET = ROOT.parent / "local_archive" / "real_road_acquisition" / "ltpp_geoforecast_blind_vectorization_v1_20260805"


def test_catalog_is_complete_and_chronological():
    catalog = MODULE.load_catalog(PACKET)
    assert len(catalog["states"]) == 37
    assert sorted(catalog["sections"]) == ["06-1253", "06-2041", "06-2647", "06-8149", "06-8150", "06-8201"]
    states = catalog["sections"]["06-1253"]
    assert [row["survey_date"] for row in states] == sorted(row["survey_date"] for row in states)
    assert states[0]["survey_date"] == "1991-06-10"
    assert states[-1]["survey_date"] == "2012-04-17"
    assert states[-1]["after_out_of_study"] is True
    assert states[-1]["primary_blind_id"] == "P014"
    assert states[-1]["secondary_blind_id"] == "S016"


def test_server_is_read_only_and_returns_four_layer_state():
    server = MODULE.TimelineServer(("127.0.0.1", 0), PACKET, "06-1253")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        timeline = json.load(urllib.request.urlopen(base + "/api/timeline?section=06-1253"))
        assert len(timeline) == 8
        key = urllib.parse.quote(timeline[0]["asset_key"], safe="")
        state = json.load(urllib.request.urlopen(base + "/api/state/" + key))
        assert state["primary_label"]["properties"]["locked"] is True
        assert state["secondary_label"]["properties"]["locked"] is True
        assert state["final_label"]["properties"]["adjudicated"] is True
        request = urllib.request.Request(base + "/api/state/" + key, data=b"{}", method="POST")
        try:
            urllib.request.urlopen(request)
            raise AssertionError("POST unexpectedly succeeded")
        except urllib.error.HTTPError as exc:
            assert exc.code == HTTPStatus.METHOD_NOT_ALLOWED
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
