import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from SENS_tensile.run_pi_transfer_controls import (
    _physical_exact_realization,
    _toy_realization,
    _weighted_metrics,
)
from source.scaling import audit_pi_transfer


def test_f1_realizations_match_complete_declared_pi_vector():
    reference = _toy_realization(
        boundary_condition="top_bottom_ux_clamp_reverse_bc",
        material_label="test reference",
    )
    candidate = _physical_exact_realization()
    rows = audit_pi_transfer(
        reference.normalized_groups(), candidate.normalized_groups()
    )
    assert reference.w1_norm == pytest.approx(1.0)
    assert candidate.w1_norm == pytest.approx(1.0)
    assert reference.thickness_over_L == pytest.approx(1.0)
    assert candidate.thickness_over_L == pytest.approx(1.0)
    assert all(row["status"] == "matched" for row in rows)


def test_f2_bc_change_is_not_hidden_by_scalar_pi_match():
    reference = _toy_realization(
        boundary_condition="bottom_left_ux_anchor_free_lateral",
        material_label="test reference",
    )
    candidate = _toy_realization(
        boundary_condition="top_bottom_ux_clamp_reverse_bc",
        material_label="test candidate",
    )
    rows = audit_pi_transfer(
        reference.normalized_groups(), candidate.normalized_groups()
    )
    by_group = {row["group"]: row for row in rows}
    assert by_group["boundary_condition"]["status"] == "mismatched"
    assert all(
        row["status"] == "matched"
        for row in rows
        if row["category"] in {"buckingham_pi", "geometry_load_ratio"}
    )


def test_area_weighted_dimensional_round_trip_is_identity():
    reference = np.array([0.0, 0.01, 0.1, 1.0])
    weights = np.array([1.0, 2.0, 3.0, 4.0])
    w1 = _physical_exact_realization().w1_phys
    candidate = reference * w1 / w1
    metrics = _weighted_metrics(reference, candidate, weights, log_floor=1e-12)
    assert metrics["max_abs"] <= 1e-12
    assert metrics["mae"] <= 1e-13
    assert metrics["correlation"] == pytest.approx(1.0)
