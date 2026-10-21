"""Experimental constraint kernels; no training, history mutation or solver.

Sign convention: c <= 0, multiplier >= 0. PHR terms are added OUTSIDE the
logarithm of positive physical energy. Quadrature weights and multipliers
are fixed during primal differentiation. This module is not wired into PIDL.
"""

import math

import torch


def _finite_result(value):
    if not bool(torch.isfinite(value).all()):
        raise ValueError("constraint arithmetic produced a nonfinite intermediate/result")
    return value


def _positive_scalar(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def _same_vectors(*vectors):
    first = vectors[0]
    if not isinstance(first, torch.Tensor) or first.ndim != 1 or first.numel() == 0:
        raise ValueError("inputs must be nonempty one-dimensional tensors")
    for value in vectors:
        if not isinstance(value, torch.Tensor) or not value.is_floating_point():
            raise ValueError("inputs must be floating tensors")
        if value.shape != first.shape or value.dtype != first.dtype or value.device != first.device:
            raise ValueError("shape, dtype and device must match; no implicit broadcasting")
        if not bool(torch.isfinite(value).all()):
            raise ValueError("inputs must be finite")


def phr_inequality_term(constraint, multiplier, rho, weights):
    """Weighted Powell-Hestenes-Rockafellar term for c <= 0.

    sum_i w_i ([lambda_i + rho*c_i]_+^2 - lambda_i^2)/(2*rho).
    Weights are explicit: choosing their support/normalisation is part of the
    caller's protocol. A small value alone is not a feasibility/KKT certificate.
    """
    _same_vectors(constraint, multiplier, weights)
    rho = _positive_scalar(rho, "rho")
    if multiplier.requires_grad or weights.requires_grad:
        raise ValueError("dual variables and weights must be fixed in the primal step")
    if bool((multiplier < 0).any()) or bool((weights <= 0).any()):
        raise ValueError("multipliers must be nonnegative and weights positive")
    shifted = torch.relu(_finite_result(multiplier + rho * constraint))
    _finite_result(weights * shifted)  # explicit d(term)/dc; finite loss is insufficient
    terms = _finite_result((shifted.square() - multiplier.square()) / (2 * rho))
    return _finite_result(torch.sum(weights * terms))


def update_inequality_multiplier(constraint, multiplier, rho):
    """Detached dual update; call only after the defined inner-solve decision.

    A finite number of updates is not exact constraint enforcement. This helper
    deliberately provides no outer loop, retry policy or acceptance decision.
    """
    _same_vectors(constraint, multiplier)
    rho = _positive_scalar(rho, "rho")
    if bool((multiplier < 0).any()):
        raise ValueError("multipliers must be nonnegative")
    return torch.relu(_finite_result(multiplier.detach() + rho * constraint.detach()))


def box_projected_gradient(field, gradient, lower, upper, step=1.0):
    """(d - projection_[lower,upper](d-step*g))/step, on declared DOFs.

    gradient is the derivative in FIELD coordinates, not a network gradient.
    Scaling/metric and step must be fixed for cross-state comparisons. For a
    box, zero certifies first-order constrained stationarity, not a global
    minimum of a nonconvex coupled objective. Equal bounds are fixed DOFs.
    General GP inequalities require their own constraint Jacobian/KKT test.
    """
    _same_vectors(field, gradient, lower, upper)
    step = _positive_scalar(step, "step")
    if bool((lower > upper).any()):
        raise ValueError("inconsistent bounds; do not silently clip old history")
    trial = _finite_result(field - step * gradient)
    projected = torch.maximum(lower, torch.minimum(upper, trial))
    return _finite_result((field - projected) / step)
