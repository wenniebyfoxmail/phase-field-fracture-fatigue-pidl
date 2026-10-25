"""Tolerance-aware conditional KKT diagnostics for projected eta updates.

The damage carrier owns the exact feasible interval. This module evaluates an
eta-block KKT residual at fixed network parameters and provides small,
CPU-testable helpers for a projected-gradient line search. It neither adds an
irreversibility energy nor changes the physical objective.

The raw residual has the units of the direct damage gradient:

    r_i = 0                    at a fixed degree of freedom,
    r_i = min(g_i, 0)          at the lower bound,
    r_i = max(g_i, 0)          at the upper bound,
    r_i = g_i                  in the interior.

A separate projected mapping is recorded in damage units. It uses the
lumped-mass metric only as a preconditioner, so its tolerance describes the
size of the next feasible projected eta move rather than the scale of a
metric-dependent residual.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch

from projected_damage import ReferenceBaseProjectedDamage


@dataclass(frozen=True)
class EtaKKTResidual:
    """Conditional eta-block KKT quantities at one fixed-theta state."""

    raw_gradient: torch.Tensor
    residual: torch.Tensor
    projected_mapping: torch.Tensor
    projected_eta: torch.Tensor
    lower_active: torch.Tensor
    upper_active: torch.Tensor
    fixed: torch.Tensor
    blocked_lower: torch.Tensor
    released_lower: torch.Tensor
    blocked_upper: torch.Tensor
    released_upper: torch.Tensor
    raw_gradient_l2: float
    raw_gradient_inf: float
    residual_weighted_l2: float
    residual_inf: float
    mapping_weighted_l2: float
    mapping_inf: float


def _positive_finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a positive finite scalar")
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be a positive finite scalar")
    return value


def _same_layout(name: str, value: torch.Tensor, reference: torch.Tensor) -> None:
    if not isinstance(value, torch.Tensor):
        raise TypeError(f"{name} must be a torch.Tensor")
    if value.shape != reference.shape:
        raise ValueError(f"{name}.shape does not match eta")
    if value.device != reference.device or value.dtype != reference.dtype:
        raise ValueError(f"{name} layout does not match eta")


def _finite(name: str, value: torch.Tensor) -> None:
    if not bool(torch.isfinite(value).all()):
        raise FloatingPointError(f"{name} contains a non-finite value")


def _weighted_l2(value: torch.Tensor, metric: torch.Tensor) -> float:
    metric_sum = metric.detach().sum()
    if not bool(metric_sum > 0):
        raise ValueError("metric must have positive sum")
    return float(torch.sqrt((metric.detach() * value.detach().square()).sum() / metric_sum))


def raw_eta_kkt_residual(
    carrier: ReferenceBaseProjectedDamage,
    raw_damage: torch.Tensor,
    gradient: torch.Tensor,
    *,
    metric: torch.Tensor,
    reference_step: float,
    active_tolerance: float = 0.0,
) -> EtaKKTResidual:
    """Evaluate a raw eta KKT residual and a reference projected mapping.

    The gradient is evaluated with network parameters held fixed and the
    carrier on its direct-damage route. The metric is a positive diagonal
    lumped mass used only for the reference projected mapping.
    """

    step = _positive_finite("reference_step", reference_step)
    tolerance = float(active_tolerance)
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("active_tolerance must be finite and non-negative")

    eta = carrier.eta.detach()
    _same_layout("gradient", gradient, eta)
    _same_layout("metric", metric, eta)
    _finite("gradient", gradient)
    _finite("metric", metric)
    if not bool((metric > 0).all()):
        raise ValueError("metric must be strictly positive")

    bounds = carrier.eta_bounds(raw_damage)
    current = eta
    if not bool((current >= bounds.lower - tolerance).all()):
        raise ValueError("eta is below its feasible interval")
    if not bool((current <= bounds.upper + tolerance).all()):
        raise ValueError("eta is above its feasible interval")

    raw_gradient = gradient.detach()
    fixed = torch.isclose(bounds.lower, bounds.upper, rtol=0.0, atol=tolerance)
    lower_active = (~fixed) & (current <= bounds.lower + tolerance)
    upper_active = (~fixed) & (current >= bounds.upper - tolerance)

    residual = raw_gradient.clone()
    residual = torch.where(lower_active, torch.minimum(raw_gradient, torch.zeros_like(raw_gradient)), residual)
    residual = torch.where(upper_active, torch.maximum(raw_gradient, torch.zeros_like(raw_gradient)), residual)
    residual = torch.where(fixed, torch.zeros_like(residual), residual)

    candidate = current - step * raw_gradient / metric.detach()
    projected_eta = torch.maximum(bounds.lower, torch.minimum(bounds.upper, candidate))
    projected_mapping = current - projected_eta

    blocked_lower = lower_active & (raw_gradient >= 0)
    released_lower = lower_active & (raw_gradient < 0)
    blocked_upper = upper_active & (raw_gradient <= 0)
    released_upper = upper_active & (raw_gradient > 0)
    return EtaKKTResidual(
        raw_gradient=raw_gradient,
        residual=residual,
        projected_mapping=projected_mapping,
        projected_eta=projected_eta,
        lower_active=lower_active,
        upper_active=upper_active,
        fixed=fixed,
        blocked_lower=blocked_lower,
        released_lower=released_lower,
        blocked_upper=blocked_upper,
        released_upper=released_upper,
        raw_gradient_l2=float(raw_gradient.norm()),
        raw_gradient_inf=float(raw_gradient.abs().max()),
        residual_weighted_l2=_weighted_l2(residual, metric),
        residual_inf=float(residual.abs().max()),
        mapping_weighted_l2=_weighted_l2(projected_mapping, metric),
        mapping_inf=float(projected_mapping.abs().max()),
    )


def eta_kkt_converged(
    report: EtaKKTResidual,
    *,
    gradient_inf_tolerance: float,
    mapping_inf_tolerance: float,
) -> bool:
    """Return whether a conditional eta KKT report meets both fixed thresholds."""

    return (
        report.residual_inf <= _positive_finite("gradient_inf_tolerance", gradient_inf_tolerance)
        and report.mapping_inf <= _positive_finite("mapping_inf_tolerance", mapping_inf_tolerance)
    )


def armijo_sufficient_decrease(
    *,
    trial_value: float,
    base_value: float,
    directional_derivative: float,
    armijo_c1: float,
) -> bool:
    """Check the projected-direction Armijo inequality for one finite trial."""

    c1 = _positive_finite("armijo_c1", armijo_c1)
    if c1 >= 1.0:
        raise ValueError("armijo_c1 must be less than one")
    values = (trial_value, base_value, directional_derivative)
    if not all(isinstance(value, (int, float)) and math.isfinite(float(value)) for value in values):
        return False
    if directional_derivative >= 0.0:
        return False
    return float(trial_value) <= float(base_value) + c1 * float(directional_derivative)
