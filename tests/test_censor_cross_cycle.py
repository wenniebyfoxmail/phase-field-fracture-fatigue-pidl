import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/censor_projection_diagnostic"))
from cross_cycle_weak_history_audit import (
    allow_cross_cycle_spatial_change,
    compare_vectors,
    norm_mass,
    summarize_local,
    validate_manifest,
    validate_output_path,
)


def test_vector_comparison_uses_difference_not_ratio_of_norms():
    mass = np.array([0.25, 0.75])
    reference = np.array([2.0e-3, -1.0e-3])
    candidate = reference.copy()
    result = compare_vectors(candidate, reference, mass, 1.0)
    assert result["mass_dual_diff"] == 0.0
    assert result["scaled_difference"] == 0.0
    assert result["status"] == "PASS"


def test_mass_dual_norm_matches_explicit_formula():
    values = np.array([2.0, 3.0])
    mass = np.array([0.5, 1.5])
    assert norm_mass(values, mass) == np.sqrt(4.0 / 0.5 + 9.0 / 1.5)


def test_vector_failure_is_retained_and_blocks_trend():
    rows = [
        {"cycle": 76, "numerical_equivalence": "PASS", "rho_u": 1.0, "box_rho_d_common_free": 1.0},
        {"cycle": 82, "numerical_equivalence": "FAIL", "rho_u": 4.0, "box_rho_d_common_free": 4.0},
        {"cycle": 83, "numerical_equivalence": "PASS", "rho_u": 5.0, "box_rho_d_common_free": 5.0},
    ]
    local, status = summarize_local(rows)
    assert status == "BLOCKED_NUMERICAL_EQUIVALENCE"
    assert local["uv"]["status"] == "NOT_EVALUABLE"
    assert "82" in local["damage"]["reason"]


def test_local_factor_three_gate_is_separate_by_channel():
    rows = [
        {"cycle": 76, "numerical_equivalence": "PASS", "rho_u": 1.0e-2, "box_rho_d_common_free": 2.0e-3},
        {"cycle": 82, "numerical_equivalence": "PASS", "rho_u": 4.0e-2, "box_rho_d_common_free": 5.0e-3},
        {"cycle": 83, "numerical_equivalence": "PASS", "rho_u": 3.1e-2, "box_rho_d_common_free": 7.0e-3},
    ]
    local, status = summarize_local(rows)
    assert status == "EVALUATED"
    assert local["uv"]["status"] == "PASS"
    assert local["damage"]["status"] == "FAIL"


def test_output_inside_inputs_is_rejected(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    with np.testing.assert_raises_regex(ValueError, "outside"):
        validate_output_path(inputs, inputs / "output")


def test_manifest_pairing_drift_is_rejected():
    manifest = {
        "protocol_revision": "20261005-r1-frozen",
        "stationarity_threshold": 1.0e-3,
        "vector_gate": 1.0e-9,
        "local_growth_gate": 3.0,
        "full_growth_gate": 3.0,
        "candidates": [],
    }
    with np.testing.assert_raises_regex(ValueError, "pairing"):
        validate_manifest(manifest)


def test_spatial_change_is_omitted_when_vector_gate_blocks_trend():
    assert allow_cross_cycle_spatial_change("EVALUATED")
    assert not allow_cross_cycle_spatial_change("BLOCKED_NUMERICAL_EQUIVALENCE")
