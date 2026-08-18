from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "source"))

from rrapinn_g4_smoke_contract import EXPECTED_STEPS, validate_completion, validate_start


def valid_start(**updates):
    values = {
        "displacement_count": 306,
        "start_raw_step": 301,
        "configured_steps": EXPECTED_STEPS,
        "configured_count": 306,
        "configured_start": 301,
        "configured_end": 305,
        "risk_intervention": "absent",
        "risk_key_present": False,
    }
    values.update(updates)
    return validate_start(**values)


def test_start_contract_accepts_only_frozen_resume_shape():
    valid_start()
    for update in (
        {"displacement_count": 307}, {"start_raw_step": 0},
        {"configured_steps": [301, 302, 303, 304, 305, 306]},
        {"configured_end": 306}, {"risk_intervention": "ME85_frozen"},
        {"risk_key_present": True},
    ):
        with pytest.raises(RuntimeError, match="execution guard"):
            valid_start(**update)


def test_completion_requires_exact_steps_and_for_else_exhaustion():
    validate_completion(actual_raw_steps=EXPECTED_STEPS, natural_exhaustion=True)
    with pytest.raises(RuntimeError, match="exactly"):
        validate_completion(actual_raw_steps=EXPECTED_STEPS + [306], natural_exhaustion=True)
    with pytest.raises(RuntimeError, match="natural"):
        validate_completion(actual_raw_steps=EXPECTED_STEPS, natural_exhaustion=False)
