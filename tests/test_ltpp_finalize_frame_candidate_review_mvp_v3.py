from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_finalize_frame_candidate_review_mvp_v3.py"
SPEC = importlib.util.spec_from_file_location("ltpp_finalize_frame_candidate_review_v3", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def raw(date: str, candidate: str, values: tuple[str, str, str, str]) -> dict[str, str]:
    return {"date": date, "candidate": candidate, "source_exists": "TRUE", **dict(zip(MODULE.FIELDS, values)), "candidate_verdict": "PENDING"}


def test_owner_confirmed_true_is_canonical_yes():
    row = MODULE.canonical_row(raw("19910610", "A", ("TRUE", "TRUE", "TRUE", "NO")))
    assert tuple(row[field] for field in MODULE.FIELDS) == ("YES", "YES", "YES", "NO")
    assert row["candidate_verdict"] == "ACCEPT"


def test_only_confirmed_no_candidate_row_can_have_no_grid_text():
    row = MODULE.canonical_row(raw("19980407", "A", ("no grid", "", "", "")))
    assert row["candidate_verdict"] == "NO_CANDIDATE"
    assert set(row) == {"date", "candidate", "source_exists", *MODULE.FIELDS, "candidate_verdict"}
    with pytest.raises(ValueError):
        MODULE.canonical_row(raw("19980407", "B", ("no grid", "", "", "")))


def test_date_rule_remains_fail_closed_for_no_accept_or_two_distinct_accepts():
    reject = raw("19910610", "A", ("NO", "YES", "YES", "NO")) | {"candidate_verdict": "REJECT"}
    accept_a = raw("19910610", "A", ("YES", "YES", "YES", "NO")) | {"candidate_verdict": "ACCEPT"}
    accept_b = raw("19910610", "B", ("YES", "YES", "YES", "NO")) | {"candidate_verdict": "ACCEPT"}
    assert MODULE.date_verdict([reject, reject | {"candidate": "B"}])[0] == "NO_ACCEPTED_CANDIDATE__FAIL_CLOSED"
    assert MODULE.date_verdict([accept_a, accept_b])[0] == "AMBIGUOUS_MULTIPLE_ACCEPTED_CANDIDATES__FAIL_CLOSED"
