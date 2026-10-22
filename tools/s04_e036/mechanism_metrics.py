"""Objective and parameter-geometry diagnostics, without a solver or model run.

These quantities explain one evaluated state. They do not measure a field
representation ceiling and never turn a parameter-space plateau into nodal KKT.
"""
from __future__ import annotations

import torch


def _vector(values):
    value = torch.cat([v.detach().reshape(-1).to(dtype=torch.float64) for v in values])
    if not bool(torch.isfinite(value).all()):
        raise ValueError("nonfinite gradient diagnostic")
    return value


def gradient_balance(physical, regularizer, actual_total):
    """Use identical parameter ordering and the actual differentiated total.

    The physical vector must include the log-energy scale when comparing it
    with the differentiated regularizer. A second raw-energy gradient may be
    recorded separately, but must not be substituted in this cancellation.
    """
    a, b, total = map(_vector, (physical, regularizer, actual_total))
    if a.shape != b.shape or a.shape != total.shape:
        raise ValueError("gradient supports differ")
    na, nb, nt = [float(torch.linalg.vector_norm(v)) for v in (a, b, total)]
    nonzero = a != 0
    flips = nonzero & (torch.sign(a) != torch.sign(total))
    mass = float(a.abs().sum())
    return dict(
        physical_parameter_gradient_l2=na,
        regularizer_parameter_gradient_l2=nb,
        total_parameter_gradient_l2=nt,
        physical_regularizer_cosine=None if na == 0 or nb == 0 else float(torch.dot(a, b)) / (na * nb),
        cancellation_ratio=None if na + nb == 0 else nt / (na + nb),
        physical_nonzero_coordinates=int(nonzero.sum()),
        rprop_sign_changed_coordinates=int(flips.sum()),
        rprop_sign_changed_fraction=None if not bool(nonzero.any()) else float(flips.sum()) / float(nonzero.sum()),
        physical_gradient_l1_mass_with_changed_sign=None if mass == 0 else float(a.abs()[flips].sum()) / mass,
        analytic_sum_to_actual_total_l2=float(torch.linalg.vector_norm((a + b) - total)),
        sign_policy="all exactly nonzero physical coordinates; includes cancellation to zero; diagnostic, no tolerance promotion",
    )


def parameter_geometry(state):
    """Expose the trainable-activation/weight gauge in the exact 8-layer net."""
    layers = ["input_layer"] + [f"hidden_layers.{i}" for i in range(7)]
    result = []
    for i, name in enumerate(layers):
        w, b, coefficient = [state[k].detach().to(dtype=torch.float64) for k in
                              (name + ".weight", name + ".bias", f"activations.{i}.coeff")]
        if coefficient.numel() != 1 or not all(bool(torch.isfinite(v).all()) for v in (w, b, coefficient)):
            raise ValueError("invalid trainable-activation state")
        result.append(dict(layer=name, activation_coefficient=float(coefficient),
                           weight_l2=float(torch.linalg.vector_norm(w)),
                           bias_l2=float(torch.linalg.vector_norm(b)),
                           effective_preactivation_weight_l2=float(torch.linalg.vector_norm(coefficient * w)),
                           effective_preactivation_bias_l2=float(torch.linalg.vector_norm(coefficient * b))))
    output = state["output_layer.weight"].detach().to(dtype=torch.float64)
    if not bool(torch.isfinite(output).all()):
        raise ValueError("nonfinite output weights")
    return dict(hidden_layers=result, output_weight_l2=float(torch.linalg.vector_norm(output)),
                interpretation="parameter scaling diagnostics; not a field regularity or capacity measure")


def direct_box_projection(raw_damage, lower):
    """Explicit alternative output map; never substituted into a legacy arm.

    Applying this projection to a legacy field preserves every already feasible
    field, but enlarges the composite function family. It is therefore a named
    constraint-parameterization intervention, not an optimizer-only comparison.
    The ordinary clamp derivative is used; no straight-through gradient.
    """
    if raw_damage.shape != lower.shape:
        raise ValueError("damage and immutable predecessor supports differ")
    if lower.requires_grad or not bool(torch.isfinite(lower).all()) or bool(torch.any((lower < 0) | (lower > 1))):
        raise ValueError("a finite immutable feasible predecessor is required")
    if not bool(torch.isfinite(raw_damage).all()):
        raise ValueError("nonfinite raw damage")
    upper = torch.ones_like(raw_damage)
    projected = torch.minimum(torch.maximum(raw_damage, lower), upper)
    # Collapsed intervals represent a constant field. Two min/max tie
    # derivatives otherwise leave an artificial 1/4 derivative at raw==1.
    return torch.where(lower == 1, upper, projected)


def projection_receipt(raw_damage, projected, lower):
    expected = direct_box_projection(raw_damage, lower)
    if not torch.equal(projected, expected):
        raise ValueError("projection receipt differs from actual mapping")
    delta = (projected.detach() - raw_damage.detach()).to(dtype=torch.float64)
    return dict(mapping="legacy_field_then_nodal_box_projection", derivative="ordinary_minimum_maximum_no_STE",
                raw_below_lower_nodes=int((raw_damage < lower).sum()),
                raw_above_upper_nodes=int((raw_damage > 1).sum()),
                projection_delta_l2=float(torch.linalg.vector_norm(delta)),
                projection_delta_inf=float(delta.abs().max()) if delta.numel() else 0.,
                collapsed_interval_nodes=int((lower == 1).sum()),
                changed_function_family=True)


def clipped_descent_receipt(raw_damage, lower, physical_damage_force):
    """Identify feasible nodal descent hidden by a zero projection derivative."""
    if physical_damage_force.shape != raw_damage.shape or not bool(torch.isfinite(physical_damage_force).all()):
        raise ValueError("physical damage force has invalid support or values")
    direct_box_projection(raw_damage, lower)
    mobile = lower < 1
    lower_blocked = mobile & (raw_damage < lower) & (physical_damage_force < 0)
    upper_blocked = mobile & (raw_damage > 1) & (physical_damage_force > 0)
    blocked = lower_blocked | upper_blocked
    force = physical_damage_force.detach().to(dtype=torch.float64)
    return dict(lower_tail_blocked_feasible_descent_nodes=int(lower_blocked.sum()),
                upper_tail_blocked_feasible_descent_nodes=int(upper_blocked.sum()),
                blocked_feasible_descent_force_l2=float(torch.linalg.vector_norm(force[blocked])),
                interpretation="nonzero means zero clamp derivative hides feasible nodal descent; parameter stationarity is insufficient")
