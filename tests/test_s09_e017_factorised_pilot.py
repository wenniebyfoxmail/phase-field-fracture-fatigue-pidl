from collections import OrderedDict
import math

import pytest
import torch

import s09_e017_factorised_pilot as core
import s09_e018_real_adapter as e018

from s09_e017_factorised_pilot import (
    ACTIVE_GROUPS,
    ARM_AMPLITUDE,
    ARM_AMPLITUDE_SHAPE,
    ARM_DIRECT,
    ARM_ORDER,
    GROUP_ORDER,
    amplitude_from_residual,
    amplitude_objective,
    capacity_supported_seed,
    classify_profiles,
    decision_amplitude_error,
    decision_shape_values,
    decode_factorised_increment,
    effective_factorisation,
    freeze_gradient_scales,
    learnable_shape,
    pcgrad_merge,
    amplitude_priority_pcgrad_merge,
    reconstruction_objective,
    shape_objective,
)


def f64(values):
    return torch.tensor(values, dtype=torch.float64)


def test_mass_entry_seed_opens_every_positive_capacity_node_and_respects_tv():
    weights = f64([1.0, 2.0, 1.0, 2.0])
    pre = f64([0.0, 0.2, 1.0, 0.5])
    wbar = weights / weights.sum()
    b25 = f64([1.0 / wbar[0], 0.0, 0.0, 0.0])
    seed, uniform, record = capacity_supported_seed(b25, pre, weights)
    mask = pre < 1.0
    assert torch.all(seed[mask] > 0)
    assert seed[~mask].item() == 0.0
    assert torch.dot(wbar, seed).item() == pytest.approx(1.0)
    assert torch.dot(wbar, uniform).item() == pytest.approx(1.0)
    assert record["weighted_total_variation"] <= 1.0e-6


def test_learnable_shape_has_nonzero_mass_reallocation_sensitivity():
    weights = f64([1.0, 1.0, 1.0])
    pre = f64([0.0, 0.0, 1.0])
    b25 = f64([3.0, 0.0, 0.0])
    seed, _, _ = capacity_supported_seed(b25, pre, weights)
    logits = torch.zeros(3, dtype=torch.float64, requires_grad=True)
    shape = learnable_shape(seed, logits, pre, weights)
    shape[1].backward()
    assert shape[2].item() == 0.0
    assert logits.grad[1].item() > 0.0
    assert logits.grad[0].item() < 0.0


def test_factorised_decoder_replays_baseline_and_enforces_bounds():
    pre = f64([0.0, 0.5, 1.0])
    shape = f64([1.5, 1.5, 0.0])
    baseline = torch.tensor(0.02, dtype=torch.float64)
    amplitude = amplitude_from_residual(baseline, torch.zeros((), dtype=torch.float64))
    increment = decode_factorised_increment(pre, amplitude, shape)
    assert amplitude.item() == baseline.item()
    assert torch.all(increment >= 0)
    assert torch.all(increment <= 1.0 - pre)
    assert increment[2].item() == 0.0


def test_common_effective_factorisation_round_trips_factorised_field():
    pre = f64([0.0, 0.5, 1.0])
    weights = f64([1.0, 2.0, 1.0])
    wbar = weights / weights.sum()
    shape = f64([2.0, 1.0, 0.0])
    shape = shape / torch.dot(wbar, shape)
    amplitude = torch.tensor(0.03, dtype=torch.float64)
    increment = decode_factorised_increment(pre, amplitude, shape)
    effective_amplitude, effective_shape, valid = effective_factorisation(
        pre, increment, weights
    )
    assert valid
    assert effective_amplitude.item() == pytest.approx(amplitude.item(), rel=1e-13)
    assert torch.allclose(effective_shape, shape, rtol=1e-13, atol=1e-13)


def test_zero_effective_field_has_defined_amplitude_and_undefined_shape():
    pre = f64([0.0, 0.5])
    amplitude, shape, valid = effective_factorisation(
        pre, torch.zeros(2, dtype=torch.float64), f64([1, 1])
    )
    assert amplitude.item() == 0.0
    assert not valid
    assert torch.equal(shape, torch.zeros_like(shape))
    raw, decision = decision_shape_values((None,) * 5, predicted_shape_valid=False)
    assert raw == (None,) * 5
    assert decision == (1.0,) * 6


def test_positive_increment_cannot_underflow_to_legal_zero_event():
    tiny = torch.nextafter(f64(0.0), f64(1.0))
    with pytest.raises(ValueError, match="positive event lost"):
        effective_factorisation(f64([0.0, 0.0]), f64([tiny, 0.0]), f64([1.0, 1.0]))


def test_positive_amplitude_requires_weight_normalised_effective_shape():
    tiny = torch.nextafter(f64(0.0), f64(1.0))
    with pytest.raises(ValueError, match="weighted shape normalisation drift"):
        effective_factorisation(
            f64([0.0, 0.0]), f64([2.0 * tiny, 0.0]), f64([2.0, 1.0])
        )


def test_ordinary_tiny_positive_event_still_round_trips():
    amplitude, shape, valid = effective_factorisation(
        f64([0.0, 0.0]), f64([1.0e-300, 0.0]), f64([1.0, 1.0])
    )
    assert valid
    assert amplitude.item() > 0.0
    assert torch.dot(f64([0.5, 0.5]), shape).item() == pytest.approx(1.0)


def test_amplitude_objective_preserves_signed_reverse_pair():
    target = f64([1.0, 3.0])
    predicted_good = f64([1.0, 3.0])
    predicted_wrong = f64([3.0, 1.0])
    good, parts = amplitude_objective(predicted_good, target, 2.0, ((0, 1),))
    wrong, _ = amplitude_objective(predicted_wrong, target, 2.0, ((0, 1),))
    assert good.item() == 0.0
    assert parts["pair_contrast"].item() == 0.0
    assert wrong.item() > 0.0


def test_objective_helpers_are_finite_and_zero_at_exact_match():
    weights = f64([1.0, 2.0])
    shape = f64([3.0, 0.0])
    shape_loss, parts = shape_objective(shape, shape, weights)
    assert shape_loss.item() == pytest.approx(0.0)
    assert parts["half_l1"].item() == 0.0
    fields = f64([[0.1, 0.0], [0.0, 0.2]])
    reconstruction = reconstruction_objective(fields, fields, weights, f64([0.1, 0.2]))
    assert reconstruction.item() == 0.0


def test_objective_helpers_reject_derived_nonfinite_values():
    with pytest.raises(ValueError, match="nonfinite reconstruction objective"):
        reconstruction_objective(f64([[1.0]]), f64([[0.0]]), f64([1.0]), f64([1e-200]))
    with pytest.raises(ValueError, match="nonfinite amplitude decision error"):
        decision_amplitude_error(f64([1.0]), f64([1.0]), 1e-320)


def test_pcgrad_keeps_beta_after_scale_normalisation_and_uses_active_mean():
    gradients = OrderedDict(
        (
            ("A", f64([0.0, 2.0])),
            ("R", f64([0.0, 0.0])),
            ("P", f64([4.0, 0.0])),
        )
    )
    scales, zeros = freeze_gradient_scales(gradients)
    merged, record = pcgrad_merge(gradients, scales, seed=17, update=3)
    assert zeros == {"A": False, "R": True, "P": False}
    assert torch.allclose(merged, f64([1.0 / 12.0, 1.0 / 3.0]))
    assert record["weights"]["P"] == 0.25
    assert record["active_group_count"] == 3


def test_pcgrad_projects_conflict_and_skips_near_zero_reference():
    gradients = OrderedDict(
        (
            ("A", f64([1.0, 0.0])),
            ("S", f64([-1.0, 0.0])),
            ("R", f64([0.0, 0.0])),
            ("P", f64([0.0, 1.0])),
        )
    )
    scales, zeros = freeze_gradient_scales(gradients)
    merged, record = pcgrad_merge(gradients, scales, seed=5, update=0)
    assert zeros["R"] is True
    assert torch.isfinite(merged).all()
    assert any(
        entry["projection_applied"]
        for entries in record["projection_log"].values()
        for entry in entries
    )
    assert any(
        entry["skipped_near_zero"]
        for entries in record["projection_log"].values()
        for entry in entries
    )
    assert len(record["pairwise_geometry"]) == 6
    conflict = next(
        entry
        for entry in record["pairwise_geometry"]
        if (entry["first"], entry["second"]) == ("A", "S")
    )
    assert conflict["raw"]["conflict"] is True
    assert conflict["raw"]["cosine"] == pytest.approx(-1.0)
    assert conflict["scaled"]["conflict"] is True
    assert record["seed"] == 5
    assert record["update"] == 0
    assert set(record["projected_norms"]) == set(gradients)
    for name, gradient in gradients.items():
        assert record["raw_group_dot_merged_direction"][name] == pytest.approx(
            torch.dot(gradient, merged).item()
        )


def test_amplitude_priority_pcgrad_preserves_scaled_amplitude_descent():
    gradients = OrderedDict(
        (
            ("A", f64([2.0, 0.0, 0.0])),
            ("S", f64([-3.0, 1.0, 0.0])),
            ("R", f64([-2.0, 0.0, 1.0])),
            ("P", f64([-1.0, -1.0, 0.0])),
        )
    )
    scales, _ = freeze_gradient_scales(gradients)
    merged, record = amplitude_priority_pcgrad_merge(
        gradients, scales, seed=11, update=7
    )
    amplitude = gradients["A"] / scales["A"]
    assert torch.dot(merged, amplitude).item() >= 0.0
    assert record["merge_strategy"] == "AMPLITUDE_PRIORITY_PCG"
    assert record["amplitude_priority"]["merged_dot_scaled_amplitude"] >= 0.0
    assert torch.isfinite(merged).all()


def test_e018_priority_engine_keeps_symmetric_geometry_audit_separate():
    class TinyFactorisedModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.arm = e018.ARM_A_PRIORITY
            self.vector = torch.nn.Parameter(f64([1.0, -1.0]))

        def trainable_parameters(self):
            return [self.vector]

    model = TinyFactorisedModel()
    with e018._e018_runtime_scope():
        engine = e018.E018OptimisationEngine(model, seed=3)
        evidence, values = engine.step(
            1,
            lambda current: OrderedDict(
                A=2.0 * current.vector[0],
                S=-3.0 * current.vector[0] + current.vector[1],
                R=-2.0 * current.vector[0] + current.vector[1],
                P=-current.vector[0] - current.vector[1],
            ),
        )
    assert values.keys() == {"A", "S", "R", "P"}
    assert evidence["merge_strategy"] == "AMPLITUDE_PRIORITY_PCG"
    assert evidence["amplitude_priority"]["merged_dot_scaled_amplitude"] >= 0.0
    assert evidence["preclip_norm"] != evidence["amplitude_priority"]["preclip_norm"]


def test_gradient_geometry_overflow_fails_closed_before_clipping():
    gradients = OrderedDict(
        (name, f64([1e200, 0.0])) for name in ("A", "R", "P")
    )
    with pytest.raises(ValueError, match="nonfinite frozen gradient norm"):
        freeze_gradient_scales(gradients)
    scales = OrderedDict((name, 1.0) for name in gradients)
    with pytest.raises(ValueError, match="nonfinite PCGrad pairwise geometry"):
        pcgrad_merge(gradients, scales, seed=0, update=0)


def _errors():
    template = {
        "A": (2.0, 5.0),
        "S": (0.0, 0.8, 0.8, 0.8, 0.8, 0.8),
        "R": (2.0, 2.0),
        "P": (2.0, 2.0, 2.0, 2.0),
    }
    return OrderedDict(
        (
            arm,
            OrderedDict(
                (
                    update,
                    OrderedDict(
                        (group, tuple(values)) for group, values in template.items()
                    ),
                )
                for update in (0, 64)
            ),
        )
        for arm in ARM_ORDER
    )


def test_all_tie_is_no_separation_not_mixed_tradeoff():
    flags = classify_profiles(_errors(), execution_valid=True)
    assert flags["VALID_NO_HEAD_SEPARATION"]
    assert not flags["VALID_MIXED_TRADEOFF"]
    assert not flags["INVALID_EXECUTION"]


def test_float64_tie_comparator_uses_explicit_difference():
    right = 1.0 + 1.0e-12
    assert abs(1.0 - right) > 1.0e-12
    assert core._signs((1.0,), (right,), set()) == (-1,)
    assert core._signs((right,), (1.0,), set()) == (1,)
    adjacent = math.nextafter(1.0, math.inf)
    assert core._signs((1.0,), (adjacent,), set()) == (0,)


def test_float64_boundary_profile_does_not_create_factorisation_signal():
    errors = _errors()
    errors[ARM_DIRECT][0]["A"] = errors[ARM_DIRECT][64]["A"] = (1.0, 5.0)
    errors[ARM_AMPLITUDE][0]["A"] = errors[ARM_AMPLITUDE][64]["A"] = (1.0, 5.0)
    errors[ARM_AMPLITUDE_SHAPE][0]["A"] = (1.0 + 3.0e-12, 5.0)
    errors[ARM_AMPLITUDE_SHAPE][64]["A"] = (1.0 + 1.0e-12, 5.0)
    errors[ARM_AMPLITUDE_SHAPE][0]["S"] = (0.0, 0.8, 0.8, 0.8, 0.8, 0.8)
    errors[ARM_AMPLITUDE_SHAPE][64]["S"] = (0.0, 0.7, 0.7, 0.7, 0.7, 0.7)
    flags = classify_profiles(errors, execution_valid=True)
    assert not flags["VALID_FACTORISATION_SIGNAL"]
    assert not flags["VALID_SHAPE_OBJECTIVE_SIGNAL"]
    assert flags["VALID_NO_HEAD_SEPARATION"]


def test_classifier_rejects_missing_protected_component():
    errors = _errors()
    errors[ARM_AMPLITUDE_SHAPE][64]["P"] = (2.0, 2.0, 3.0, 2.0)
    for arm in errors:
        for update in (0, 64):
            errors[arm][update]["P"] = errors[arm][update]["P"][:2]
    with pytest.raises(ValueError, match="metric component width drift: P"):
        classify_profiles(errors, execution_valid=True)


@pytest.mark.parametrize(
    ("group", "value"),
    (("A", 0.5), ("A", -1.0), ("A", 26.0), ("S", 0.5), ("S", 17.0)),
)
def test_classifier_rejects_impossible_discrete_counts(group, value):
    errors = _errors()
    component = 1 if group == "A" else 0
    values = list(errors[ARM_DIRECT][0][group])
    values[component] = value
    errors[ARM_DIRECT][0][group] = tuple(values)
    with pytest.raises(ValueError, match="decision count"):
        classify_profiles(errors, execution_valid=True)


def test_crossed_change_gap_is_mixed_tradeoff():
    errors = _errors()
    errors[ARM_DIRECT][64]["A"] = (1.0, 4.0)
    errors[ARM_AMPLITUDE][64]["A"] = (0.5, 5.0)
    flags = classify_profiles(errors, execution_valid=True)
    assert flags["VALID_MIXED_TRADEOFF"]


def test_zero_amplitude_decision_error_is_finite():
    result = decision_amplitude_error(f64([0.0, 0.0]), f64([1.0, 3.0]), 2.0)
    assert torch.isfinite(result).all()
    assert torch.all(result > 0)


def test_invalid_execution_is_exclusive():
    flags = classify_profiles({}, execution_valid=False)
    assert flags["INVALID_EXECUTION"]
    assert sum(flags.values()) == 1


def test_f_amp_active_groups_exclude_shape():
    assert ACTIVE_GROUPS[ARM_AMPLITUDE] == ("A", "R", "P")
    assert ACTIVE_GROUPS[ARM_DIRECT] == GROUP_ORDER
    assert ACTIVE_GROUPS[ARM_AMPLITUDE_SHAPE] == GROUP_ORDER
