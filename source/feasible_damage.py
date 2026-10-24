"""State-referenced, forward-feasible damage maps for isolated PIDL runs.

This module is deliberately opt-in.  It neither changes the historical
``NonsmoothSigmoid`` map nor owns physical history; the runner owns the
accepted-state transaction.
"""

from __future__ import annotations

import torch


class _PositiveRationalIncrement(torch.autograd.Function):
    """Forward-feasible increment with a deliberate right derivative at zero.

    PyTorch assigns ``relu'(0) = 0``.  That would make the accepted state a
    damage-gradient dead point because the runner initializes every solve at
    ``q == q_reference``.  The forward function is still exactly
    ``a max(r, 0) / (1 + a max(r, 0))``; its subgradient at the sole kink is
    defined as the positive-side derivative.  This lets the optimizer leave a
    feasible accepted state without relaxing any forward invariant.
    """

    @staticmethod
    def forward(ctx, increment: torch.Tensor, slope: float) -> torch.Tensor:
        positive_increment = torch.clamp_min(increment, 0.0)
        scaled = positive_increment * slope
        ctx.save_for_backward(positive_increment, increment)
        ctx.slope = slope
        return scaled / (1.0 + scaled)

    @staticmethod
    def backward(ctx, grad_output: torch.Tensor):
        positive_increment, increment = ctx.saved_tensors
        slope = ctx.slope
        derivative = slope / (1.0 + slope * positive_increment).square()
        # At increment == 0 choose the feasible positive-side subgradient.
        derivative = derivative * (increment >= 0.0).to(grad_output.dtype)
        return grad_output * derivative, None


class StateReferencedFeasibleDamageMap:
    """Map a raw damage increment to ``h <= d <= 1`` on a fixed node set.

    ``q_reference`` is the detached raw damage channel from the accepted
    network.  Referencing the increment, rather than the absolute raw output,
    makes the accepted state an exact fixed point at finite values.
    """

    def __init__(self, h: torch.Tensor, q_reference: torch.Tensor, slope: float = 0.25):
        if not (slope > 0.0):
            raise ValueError("slope must be positive")
        self.h = self._frozen("h", h)
        self.q_reference = self._frozen("q_reference", q_reference)
        if self.h.shape != self.q_reference.shape:
            raise ValueError("h and q_reference must have identical shapes")
        if self.h.dtype != self.q_reference.dtype or self.h.device != self.q_reference.device:
            raise ValueError("h and q_reference must share dtype and device")
        if bool((self.h < 0).any()) or bool((self.h > 1).any()):
            raise ValueError("h must lie in [0, 1]")
        self.slope = float(slope)

    @staticmethod
    def _frozen(name: str, value: torch.Tensor) -> torch.Tensor:
        if not torch.is_tensor(value):
            raise TypeError(f"{name} must be a torch.Tensor")
        if not value.is_floating_point():
            raise TypeError(f"{name} must be floating point")
        if not bool(torch.isfinite(value).all()):
            raise ValueError(f"{name} must be finite")
        return value.detach().clone()

    def __call__(self, q: torch.Tensor) -> torch.Tensor:
        if not torch.is_tensor(q) or q.shape != self.h.shape:
            raise ValueError("q must match the frozen state shape")
        if q.dtype != self.h.dtype or q.device != self.h.device:
            raise ValueError("q must share the frozen state dtype and device")
        if not bool(torch.isfinite(q).all()):
            raise FloatingPointError("raw damage q is non-finite")
        increment = q - self.q_reference
        if not bool(torch.isfinite(increment).all()):
            raise FloatingPointError("raw damage increment is non-finite")
        sigma_plus = _PositiveRationalIncrement.apply(increment, self.slope)
        if not bool(torch.isfinite(sigma_plus).all()):
            raise FloatingPointError("feasible damage increment is non-finite")
        damage = self.h + (1.0 - self.h) * sigma_plus
        if not bool(torch.isfinite(damage).all()):
            raise FloatingPointError("feasible damage is non-finite")
        return damage

    def state_dict(self) -> dict[str, object]:
        """Return the reproducibility-critical numerical reference state."""
        return {
            "kind": "state_referenced_feasible_damage_v1",
            "slope": self.slope,
            "q_reference": self.q_reference.detach().clone(),
        }
