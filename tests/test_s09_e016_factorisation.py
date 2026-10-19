import csv

import numpy as np
import pytest

from scripts.analyse_s09_e016_factorisation import (
    _amplitude_scale,
    _finite_log_ratio,
    _frozen_fem_support,
    _load_a25,
    _optional_pair_score,
    _validate_saved_arrays,
    _validate_saved_csv,
    _validate_saved_json,
)
from s09_e016_factorisation import (
    EXPECTED_CYCLES,
    factorise_increment,
    numerical_readiness,
    pair_score,
    shape_metrics,
    support_contrast,
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
    assert result.clipping_analytic_upper.shape == pre.shape
    assert result.clipping_roundoff_slack.shape == pre.shape
    assert np.all(
        result.clipping_residual
        >= -result.clipping_roundoff_slack
    )
    assert np.all(
        result.clipping_residual
        <= result.clipping_analytic_upper + result.clipping_roundoff_slack
    )
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
    assert result["audit_valid"] is True
    assert result["shape_target_ready"] is True
    assert result["ready"] is True
    assert result["flags"]["zero_shape_sentinels_valid"] is True


def test_readiness_stops_when_all_fem_shape_targets_are_zero():
    weights = np.ones(2)
    nonzero = factorise_increment(np.zeros(2), np.asarray([0.1, 0.0]), weights)
    zero = factorise_increment(np.zeros(2), np.zeros(2), weights)
    fem = [zero] * len(EXPECTED_CYCLES)
    result = numerical_readiness(fem, [nonzero] * len(EXPECTED_CYCLES))
    assert result["audit_valid"] is True
    assert result["shape_target_ready"] is False
    assert result["ready"] is False
    assert result["status"] == "AUDIT_VALID_NO_FEM_SHAPE_TARGET"
    assert result["flags"]["at_least_one_fem_shape_target"] is False


def test_zero_quadrature_weight_is_rejected():
    with pytest.raises(ValueError, match="strictly positive"):
        factorise_increment(np.zeros(2), np.asarray([0.1, 0.0]), np.asarray([1.0, 0.0]))


def test_frozen_zero_and_capacity_tolerances_cannot_drift():
    values = np.asarray([0.0, 0.1])
    with pytest.raises(ValueError, match="capacity epsilon"):
        factorise_increment(values, values, np.ones(2), capacity_eps=1.0e-15)
    with pytest.raises(ValueError, match="zero tolerance"):
        factorise_increment(values, values, np.ones(2), zero_amplitude_tol=1.0e-15)


def test_optional_pair_score_ignores_cycles_outside_frozen_pairs():
    values = {cycle: float(cycle) for cycle in EXPECTED_CYCLES}
    values[2] = None
    assert _optional_pair_score(values)["available"] is True
    values[1] = None
    result = _optional_pair_score(values)
    assert result["available"] is False
    assert result["missing_cycles"] == [1]


def test_amplitude_scale_is_none_when_fem_has_no_shape_target():
    zero = factorise_increment(np.zeros(2), np.zeros(2), np.ones(2))
    assert _amplitude_scale([zero] * len(EXPECTED_CYCLES)) is None


def test_frozen_support_uses_raw_increment_before_capacity_clipping():
    raw_increment = np.asarray([2.0e-15, 0.0])
    assert np.array_equal(_frozen_fem_support(raw_increment), [True, False])


def test_inherited_bridge_uses_raw_support_and_unclipped_positive_prediction():
    pre = np.asarray([1.0, 0.0, 0.0])
    target = np.asarray([1.0 + 2.0e-15, 0.1, 0.0])
    predicted = np.asarray([1.0, 0.05, 0.03])
    value = support_contrast(
        np.maximum(predicted - pre, 0.0), target - pre, np.ones(3)
    )
    assert value == pytest.approx(-0.005)


def test_shape_cosine_is_stable_for_extreme_positive_weight_ratio():
    weights = np.asarray([1.0e-200, 1.0])
    item = factorise_increment(np.zeros(2), np.asarray([0.1, 0.0]), weights)
    metrics = shape_metrics(
        item,
        item,
        weights,
        np.asarray([[0.0, 0.0], [1.0, 0.0]]),
        np.asarray([True, False]),
    )
    assert metrics["weighted_cosine"] == pytest.approx(1.0)


def test_log_ratio_preserves_subnormal_positive_numerator():
    value = _finite_log_ratio(float(np.nextafter(0.0, 1.0)), 36.7368005696771)
    assert value == pytest.approx(-748.0438509143517)


def test_a25_loader_rejects_nonfinite_scalar_on_nonpair_cycle(tmp_path):
    path = tmp_path / "a25.csv"
    fieldnames = [
        "arm",
        "update",
        "cycle",
        "predicted_damage_increment_abs_mean",
        "true_damage_increment_abs_mean",
    ]
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for cycle in EXPECTED_CYCLES:
            writer.writerow(
                {
                    "arm": "A25_exact_e009_replay",
                    "update": 500,
                    "cycle": cycle,
                    "predicted_damage_increment_abs_mean": (
                        "nan" if cycle == 2 else "0.1"
                    ),
                    "true_damage_increment_abs_mean": "0.1",
                }
            )
    with pytest.raises(ValueError, match="invalid A25 scalar amplitude"):
        _load_a25(path)


def test_saved_csv_validation_rejects_scientific_value_mutation(tmp_path):
    path = tmp_path / "table.csv"
    rows = [{"cycle": 1, "amplitude": 0.25}]
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    _validate_saved_csv(path, rows)

    path.write_text("cycle,amplitude\n1,0.5\n")
    with pytest.raises(ValueError, match="CSV byte drift"):
        _validate_saved_csv(path, rows)


def test_saved_csv_validation_rejects_duplicate_conflicting_column(tmp_path):
    path = tmp_path / "table.csv"
    rows = [{"cycle": 1, "amplitude": 0.25}]
    path.write_bytes(b"cycle,amplitude,amplitude\r\n1,999,0.25\r\n")
    with pytest.raises(ValueError, match="CSV byte drift"):
        _validate_saved_csv(path, rows)


def test_saved_json_validation_rejects_duplicate_conflicting_key(tmp_path):
    path = tmp_path / "decision.json"
    decision = {"readiness": {"ready": True}}
    path.write_text(
        '{"readiness":{"ready":false},"readiness":{"ready":true}}\n'
    )
    with pytest.raises(ValueError, match="JSON byte drift"):
        _validate_saved_json(path, decision)


def test_saved_array_validation_rejects_missing_scientific_array(tmp_path):
    path = tmp_path / "arrays.npz"
    payload = {
        "amplitude": np.asarray([0.25]),
        "shape": np.asarray([[1.0, 0.0]]),
    }
    np.savez_compressed(path, **payload)
    _validate_saved_arrays(path, payload)

    np.savez_compressed(path, shape=payload["shape"])
    with pytest.raises(ValueError, match="saved array schema drift"):
        _validate_saved_arrays(path, payload)
