import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/censor_projection_diagnostic"))
from cross_cycle_weak_history_audit import compare_vectors, norm_mass


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
