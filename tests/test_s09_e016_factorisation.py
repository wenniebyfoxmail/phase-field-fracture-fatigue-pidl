import numpy as np
import pytest

from s09_e016_factorisation import (
    EXPECTED_CYCLES,
    factorise_increment,
    numerical_readiness,
    pair_score,
    shape_metrics,
)


def test_roundtrip_including_saturated_and_zero_capacity_nodes():
    pre = np.asarray([0.0, 0.2, 1.0, 1.0 - 5e-13])
    peak = np.asarray([1.0, 0.6, 1.0, 1.0])
    weights = np.asarray([1.0, 2.0, 3.0, 4.0])
    result = factorise_increment(pre, peak, weights)
    assert result.shape_valid
    assert result.saturated_fraction_count == 2
    assert result.masked_capacity_positive_count == 0
    assert result.maximum_roundtrip_error <= 1e-12
    assert result.maximum_roundtrip_relative_error <= 64 * np.finfo(float).eps
    assert np.dot(weights / weights.sum(), result.shape) == pytest.approx(1.0)


def test_zero_event_uses_undefined_all_zero_shape():
    pre = np.asarray([0.1, 0.5, 1.0])
    result = factorise_increment(pre, pre.copy(), np.ones(3))
    assert result.amplitude == 0.0
    assert result.shape_valid is False
    assert np.array_equal(result.shape, np.zeros(3))
    assert np.array_equal(result.reconstructed_increment, np.zeros(3))


def test_small_positive_capacity_event_is_not_discarded():
    pre = np.asarray([1.0 - 2.0**-40])
    peak = np.asarray([1.0 - 2.0**-41])
    result = factorise_increment(pre, peak, np.ones(1))
    assert result.increment[0] > 0.0
    assert result.amplitude > 0.0
    assert result.shape_valid is True


def test_mixed_scale_positive_events_round_trip_with_relative_contract():
    peak = np.concatenate([np.logspace(-300, -1, 302), np.asarray([1.0])])
    result = factorise_increment(np.zeros_like(peak), peak, np.ones_like(peak))
    assert result.positive_node_count == peak.size
    assert result.shape_valid is True
    assert result.maximum_roundtrip_relative_error <= 64 * np.finfo(float).eps
    assert result.clipping_bound_valid is True


def test_material_irreversibility_violation_is_not_silently_clipped():
    with pytest.raises(ValueError, match="irreversibility"):
        factorise_increment(np.asarray([0.5]), np.asarray([0.4]), np.asarray([1.0]))


def test_shape_metrics_distinguish_same_amplitude_different_location():
    weights = np.ones(4)
    pre = np.zeros(4)
    reference = factorise_increment(pre, np.asarray([0.2, 0.0, 0.0, 0.0]), weights)
    candidate = factorise_increment(pre, np.asarray([0.0, 0.2, 0.0, 0.0]), weights)
    metrics = shape_metrics(
        reference,
        candidate,
        weights,
        np.asarray([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=float),
        np.asarray([True, False, False, False]),
    )
    assert metrics["weighted_half_l1"] == pytest.approx(1.0)
    assert metrics["weighted_cosine"] == pytest.approx(0.0)
    assert metrics["target_support_capture"] == pytest.approx(0.0)
    assert metrics["background_spill"] == pytest.approx(1.0)
    assert metrics["centroid_offset"] == pytest.approx(1.0)


def test_pair_score_uses_frozen_25_pairs():
    values = {cycle: float(cycle in (1, 58, 60, 69, 70)) for cycle in EXPECTED_CYCLES}
    score = pair_score(values)
    assert score["wins"] == 25
    assert score["ties"] == 0
    assert score["losses"] == 0
    assert score["score_2W_plus_T"] == 50


def test_readiness_allows_zero_b25_shape_as_explicit_missing_baseline_metric():
    weights = np.ones(2)
    nonzero = factorise_increment(np.zeros(2), np.asarray([0.1, 0.0]), weights)
    zero = factorise_increment(np.zeros(2), np.zeros(2), weights)
    fem = [nonzero] * len(EXPECTED_CYCLES)
    b25 = [zero] * len(EXPECTED_CYCLES)
    result = numerical_readiness(fem, b25)
    assert result["ready"] is True
    assert result["flags"]["zero_shape_sentinels_valid"] is True


def test_readiness_stops_when_all_fem_shape_targets_are_zero():
    weights = np.ones(2)
    nonzero = factorise_increment(np.zeros(2), np.asarray([0.1, 0.0]), weights)
    zero = factorise_increment(np.zeros(2), np.zeros(2), weights)
    fem = [zero] * len(EXPECTED_CYCLES)
    result = numerical_readiness(fem, [nonzero] * len(EXPECTED_CYCLES))
    assert result["ready"] is False
    assert result["flags"]["at_least_one_fem_shape_target"] is False


def test_zero_quadrature_weight_is_rejected():
    with pytest.raises(ValueError, match="strictly positive"):
        factorise_increment(np.zeros(2), np.asarray([0.1, 0.0]), np.asarray([1.0, 0.0]))
