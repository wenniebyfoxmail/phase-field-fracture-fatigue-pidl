import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_prepare_spatial_registration_v2_annotation_packets.py"
SPEC = importlib.util.spec_from_file_location("registration_packets", SCRIPT)
PACKETS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PACKETS)

CONSENSUS_SCRIPT = ROOT / "scripts" / "ltpp_consensus_spatial_registration_v2_controls.py"
CONSENSUS_SPEC = importlib.util.spec_from_file_location("registration_consensus", CONSENSUS_SCRIPT)
CONSENSUS = importlib.util.module_from_spec(CONSENSUS_SPEC)
assert CONSENSUS_SPEC.loader is not None
CONSENSUS_SPEC.loader.exec_module(CONSENSUS)


def test_fixed_candidate_universe_and_roles_are_disjoint():
    values = PACKETS.candidates()
    assert len(values) == 66
    assert len(set(values)) == 66
    assert sum(PACKETS.role_for(value) == "final_audit" for value in values) == 8
    assert sum(PACKETS.role_for(value) == "development" for value in values) == 8
    assert sum(PACKETS.role_for(value) == "fit" for value in values) == 50


def test_consensus_requires_two_usable_clicks_within_four_pixels():
    origin = {"left": 100, "top": 50}
    eligible = CONSENSUS.consensus({"status": "usable", "click_crop_px": [4, 9]}, {"status": "usable", "click_crop_px": [7, 9]}, origin, origin)
    assert eligible["status"] == "eligible"
    assert eligible["source_px"] == [105.5, 59.0]
    rejected = CONSENSUS.consensus({"status": "usable", "click_crop_px": [0, 0]}, {"status": "usable", "click_crop_px": [5, 0]}, origin, origin)
    assert rejected["status"] == "missing_or_ambiguous"
    assert rejected["reason_codes"] == ["click_distance_gt_4px"]


def test_nonusable_status_cannot_be_rescued():
    origin = {"left": 0, "top": 0}
    value = CONSENSUS.consensus({"status": "occluded", "click_crop_px": None}, {"status": "usable", "click_crop_px": [1, 1]}, origin, origin)
    assert value["status"] == "missing_or_ambiguous"
    assert value["source_px"] is None
