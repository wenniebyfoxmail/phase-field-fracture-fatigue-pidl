from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_frame_candidate_review_mvp_v3.py"
SPEC = importlib.util.spec_from_file_location("ltpp_frame_candidate_review_v3", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_candidate_mapping_is_exhaustive_for_frozen_answers():
    accepted = {"encloses_grid": "YES", "includes_0m_baseline": "YES", "excludes_summary": "YES", "obvious_nonphysical_range": "NO"}
    assert MODULE.candidate_verdict(accepted) == "ACCEPT"
    assert MODULE.candidate_verdict(accepted | {"encloses_grid": "NO"}) == "REJECT"
    assert MODULE.candidate_verdict(accepted | {"obvious_nonphysical_range": "YES"}) == "REJECT"
    assert MODULE.candidate_verdict(accepted | {"encloses_grid": "UNCERTAIN"}) == "UNCERTAIN"


def test_date_mapping_fails_closed_for_multiple_different_accepts():
    assert MODULE.date_verdict("ACCEPT", "REJECT", False) == "ENGINEERING_FRAME_CANDIDATE"
    assert MODULE.date_verdict("REJECT", "UNCERTAIN", False) == "NO_ACCEPTED_CANDIDATE__FAIL_CLOSED"
    assert MODULE.date_verdict("ACCEPT", "ACCEPT", False) == "AMBIGUOUS_MULTIPLE_ACCEPTED_CANDIDATES__FAIL_CLOSED"
    assert MODULE.date_verdict("ACCEPT", "ACCEPT", True) == "ENGINEERING_FRAME_CANDIDATE"


def test_synthetic_suite_covers_all_frozen_outcome_branches(tmp_path: Path):
    result = MODULE.run_synthetic(tmp_path / "synthetic")
    assert result["status"] == "SYNTHETIC_SUITE_PASSED"
    assert {row["case"] for row in result["records"]} == {case[0] for case in MODULE.synthetic_cases()}
    assert (tmp_path / "synthetic" / "manifest.sha256").exists()


def test_renderer_has_no_detector_or_registration_path():
    source = SCRIPT.read_text(encoding="utf-8").lower()
    for forbidden in ("hough", "linesegmentdetector", "identifystraightlines", "warp", "homography", "findtransform"):
        assert forbidden not in source
