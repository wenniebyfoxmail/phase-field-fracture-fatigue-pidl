from __future__ import annotations

import math

import pytest

from scripts.audit_rrapinn_g4_lambda_trajectory import STEPS, validate_rows


def rows(ratios=(0.01, 0.02, 0.03)):
    return [
        {
            "raw_step": step,
            "base_loss": -1.0,
            "risk_mean_excess": 2.0,
            "lambda_times_risk": ratio,
            "contribution_ratio": ratio,
        }
        for step, ratio in zip(STEPS, ratios)
    ]


def test_frozen_three_peak_gate_passes():
    assert validate_rows(rows()) is True


def test_wrong_state_nonfinite_and_excessive_ratio_fail_closed():
    bad = rows()
    bad[0]["raw_step"] = 300
    with pytest.raises(ValueError, match="exactly"):
        validate_rows(bad)
    bad = rows()
    bad[1]["base_loss"] = math.nan
    with pytest.raises(ValueError, match="non-finite"):
        validate_rows(bad)
    with pytest.raises(ValueError, match="5 percent"):
        validate_rows(rows((0.01, 0.051, 0.02)))
