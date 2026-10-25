"""Projected direct-nodal damage carrier for the isolated S04-E042 arm.

The carrier keeps the standard damage-head route as a *reference base* while
giving the solver a direct nodal correction.  For an accepted history ``h``,
a frozen base reference ``b_ref``, and a fixed base constraint ``b``, it
returns

    d = h + (b(q) - b_ref) + eta.

``eta`` is a leaf :class:`torch.nn.Parameter`.  It is projected outside
autograd to the exact nodewise interval which makes ``h <= d <= 1``.  This
module deliberately contains no energy evaluation and no irreversibility
penalty.  A caller that forms a physical objective must use the direct
elastic-plus-damage helper, not ``compute_energy``.

The projection is intentionally explicit rather than hidden in ``forward``:
after any update of the network raw head or ``eta``, the solver must call
``project_eta_`` before evaluating an accepted candidate.  That keeps the
non-smooth active-set operation out of the physical-energy backward graph and
makes each projection auditable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional

import torch
from torch import nn


TensorConstraint = Callable[[torch.Tensor], torch.Tensor]


@dataclass(frozen=True)
class ProjectedDamageSnapshot:
    """The raw, base, and damage fields from one carrier forward."""

    forward_id: int
    mode: str
    raw_damage: torch.Tensor
    base_damage: Optional[torch.Tensor]
    damage: torch.Tensor


@dataclass(frozen=True)
class EtaBounds:
    """Exact interval for the direct correction at one raw-head state."""

    lower: torch.Tensor
    upper: torch.Tensor
    base_increment: torch.Tensor


@dataclass(frozen=True)
class EtaProjection:
    """Audit record returned by one no-grad eta projection."""

    eta_before: torch.Tensor
    eta_after: torch.Tensor
    lower: torch.Tensor
    upper: torch.Tensor
    clipped_to_lower: torch.Tensor
    clipped_to_upper: torch.Tensor


@dataclass(frozen=True)
class ProjectedResidual:
    """Projected-gradient residual and active-set direction classification."""

    residual: torch.Tensor
    projected_eta: torch.Tensor
    lower_active: torch.Tensor
    upper_active: torch.Tensor
    fixed: torch.Tensor
    blocked_lower: torch.Tensor
    released_lower: torch.Tensor
    blocked_upper: torch.Tensor
    released_upper: torch.Tensor


def _require_tensor(name: str, value: torch.Tensor) -> None:
    if not isinstance(value, torch.Tensor):
        raise TypeError(f"{name} must be a torch.Tensor")


def _require_same_layout(
    first: torch.Tensor,
    second: torch.Tensor,
    first_name: str,
    second_name: str,
) -> None:
    _require_tensor(first_name, first)
    _require_tensor(second_name, second)
    if first.shape != second.shape:
        raise ValueError(
            f"{first_name}.shape={tuple(first.shape)} does not match "
            f"{second_name}.shape={tuple(second.shape)}"
        )
    if first.device != second.device:
        raise ValueError(f"{first_name}.device does not match {second_name}.device")
    if first.dtype != second.dtype:
        raise ValueError(f"{first_name}.dtype does not match {second_name}.dtype")


def _require_finite(name: str, value: torch.Tensor) -> None:
    _require_tensor(name, value)
    if not bool(torch.isfinite(value).all()):
        raise FloatingPointError(f"{name} contains a non-finite value")


def _require_positive_finite_scalar(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise TypeError(f"{name} must be a positive finite scalar")
    scalar = float(value)
    if not math.isfinite(scalar) or scalar <= 0.0:
        raise ValueError(f"{name} must be a positive finite scalar")
    return scalar


def _clip_to_interval(value: torch.Tensor, lower: torch.Tensor, upper: torch.Tensor) -> torch.Tensor:
    return torch.maximum(lower, torch.minimum(upper, value))


def tri3_values(nodal: torch.Tensor, connectivity: torch.Tensor) -> torch.Tensor:
    """Return the three degree-two TRI3 values for each nodal scalar field.

    Each returned value is a convex combination of a triangle's three vertex
    values.  Consequently nodewise ``h <= d <= 1`` implies the same bounds at
    these integration points.  The runner should nevertheless record the
    direct TRI3 check as an acceptance diagnostic.
    """

    _require_tensor("nodal", nodal)
    _require_tensor("connectivity", connectivity)
    if nodal.ndim != 1:
        raise ValueError("nodal must be one-dimensional")
    if connectivity.ndim != 2 or connectivity.shape[1] != 3:
        raise ValueError("connectivity must have shape (n_elements, 3)")
    if connectivity.dtype != torch.long:
        raise ValueError("connectivity must use torch.long indices")
    if connectivity.device != nodal.device:
        raise ValueError("connectivity.device does not match nodal.device")
    if connectivity.numel() and (
        int(connectivity.min()) < 0 or int(connectivity.max()) >= len(nodal)
    ):
        raise ValueError("connectivity contains an out-of-range node index")

    vertex = nodal[connectivity]
    return torch.stack(
        (
            4.0 * vertex[:, 0] + vertex[:, 1] + vertex[:, 2],
            vertex[:, 0] + 4.0 * vertex[:, 1] + vertex[:, 2],
            vertex[:, 0] + vertex[:, 1] + 4.0 * vertex[:, 2],
        ),
        dim=1,
    ) / 6.0


class ReferenceBaseProjectedDamage(nn.Module):
    """Carry a reference base field plus a projected direct nodal correction.

    ``base_constraint`` is normally the standard alpha constraint that was in
    the field before installing this carrier.  Only ``base_reference`` is
    persisted in an accepted E042 state; a raw q reference is neither needed
    nor retained.  :meth:`from_raw_reference` is available only to capture
    the initial base reference.  When a reloaded network satisfies
    ``base(q) == base_reference``, its direct correction starts at zero and
    gives ``d == history_alpha`` bitwise for deterministic base constraints.

    This carrier exposes two deliberately separate field routes:

    ``hold_damage``
        Return a stored, detached target field.  It gives the displacement/raw
        head block no route through damage.  After that block changes the raw
        head, call :meth:`set_damage_` with the target to reconstruct ``eta``
        at the new base state.

    ``direct_damage``
        Return the reference-base expression, with the base increment detached
        and ``d / d eta == 1``.  It is the eta-block route while network
        parameters are held fixed.

    The module does not project during either route.  Optimisers can therefore
    expose an infeasible proposal to their caller, which must invoke
    :meth:`project_eta_` before that proposal is accepted or used for a
    physical-energy calculation.
    """

    def __init__(
        self,
        history_alpha: torch.Tensor,
        base_constraint: TensorConstraint,
        *,
        base_reference: torch.Tensor,
        check_finite: bool = True,
    ) -> None:
        super().__init__()
        _require_same_layout(
            history_alpha,
            base_reference,
            "history_alpha",
            "base_reference",
        )
        if not callable(base_constraint):
            raise TypeError("base_constraint must be callable")
        if check_finite:
            _require_finite("history_alpha", history_alpha)
            _require_finite("base_reference", base_reference)
        if not bool(torch.all((history_alpha >= 0) & (history_alpha <= 1))):
            raise ValueError("history_alpha must lie in [0, 1]")

        self.register_buffer("history_alpha", history_alpha.detach().clone())
        # Keep a module constraint registered if one is supplied, while plain
        # callables remain valid for the unit-level carrier contract.
        self.base_constraint = base_constraint
        self.check_finite = bool(check_finite)
        self.register_buffer("base_reference", base_reference.detach().clone())
        self.eta = nn.Parameter(torch.zeros_like(self.history_alpha))
        self.register_buffer("held_damage", self.history_alpha.detach().clone())
        self.last_forward_id = 0
        self._last_snapshot: Optional[ProjectedDamageSnapshot] = None

    @classmethod
    def from_raw_reference(
        cls,
        history_alpha: torch.Tensor,
        raw_damage_reference: torch.Tensor,
        base_constraint: TensorConstraint,
        *,
        check_finite: bool = True,
    ) -> "ReferenceBaseProjectedDamage":
        """Capture a base reference without retaining raw q in the carrier.

        This factory is for initial-state construction only.  Accepted-state
        reloads should call the main constructor with their persisted
        ``base_reference`` and independently verify that the reloaded raw head
        reproduces it.
        """

        _require_same_layout(
            history_alpha,
            raw_damage_reference,
            "history_alpha",
            "raw_damage_reference",
        )
        if not callable(base_constraint):
            raise TypeError("base_constraint must be callable")
        if check_finite:
            _require_finite("history_alpha", history_alpha)
            _require_finite("raw_damage_reference", raw_damage_reference)
        with torch.no_grad():
            base_reference = base_constraint(raw_damage_reference)
        _require_same_layout(
            base_reference,
            history_alpha,
            "base_reference",
            "history_alpha",
        )
        if check_finite:
            _require_finite("base_reference", base_reference)
        return cls(
            history_alpha,
            base_constraint,
            base_reference=base_reference,
            check_finite=check_finite,
        )

    def _evaluate_base(self, raw_damage: torch.Tensor) -> torch.Tensor:
        _require_same_layout(
            raw_damage,
            self.history_alpha,
            "raw_damage",
            "history_alpha",
        )
        base_damage = self.base_constraint(raw_damage)
        _require_same_layout(
            base_damage,
            self.history_alpha,
            "base_damage",
            "history_alpha",
        )
        if self.check_finite:
            _require_finite("raw_damage", raw_damage)
            _require_finite("base_damage", base_damage)
        return base_damage

    def _bounds_from_base(self, base_damage: torch.Tensor) -> EtaBounds:
        _require_same_layout(
            base_damage,
            self.base_reference,
            "base_damage",
            "base_reference",
        )
        increment = (base_damage - self.base_reference).detach()
        lower = -increment
        upper = (1.0 - self.history_alpha - increment).detach()
        if self.check_finite:
            _require_finite("base_increment", increment)
            _require_finite("eta_lower_bound", lower)
            _require_finite("eta_upper_bound", upper)
        if not bool(torch.all(lower <= upper)):
            raise RuntimeError("eta feasibility interval is empty")
        return EtaBounds(lower=lower, upper=upper, base_increment=increment)

    def eta_bounds(self, raw_damage: torch.Tensor) -> EtaBounds:
        """Return detached exact eta bounds at the supplied raw-head state."""

        with torch.no_grad():
            return self._bounds_from_base(self._evaluate_base(raw_damage))

    @staticmethod
    def _require_mode(mode: str) -> str:
        if mode not in ("hold_damage", "direct_damage"):
            raise ValueError("mode must be 'hold_damage' or 'direct_damage'")
        return mode

    def damage(self, raw_damage: torch.Tensor, *, mode: str) -> torch.Tensor:
        """Return damage through one explicit alternating-block route.

        ``hold_damage`` intentionally does not even evaluate the base
        constraint: the returned tensor is a detached stored target.  In
        ``direct_damage`` the base is evaluated only to calculate a detached
        offset, so raw-head parameters have no damage derivative whereas eta
        retains its unit derivative.
        """

        mode = self._require_mode(mode)
        if mode == "hold_damage":
            _require_same_layout(
                raw_damage,
                self.history_alpha,
                "raw_damage",
                "history_alpha",
            )
            if self.check_finite:
                _require_finite("raw_damage", raw_damage)
            base_damage = None
            damage = self.held_damage.detach()
        else:
            base_damage = self._evaluate_base(raw_damage)
            base_increment = (base_damage - self.base_reference).detach()
            # Group eta with the base offset so the lower-bound eta=-offset
            # gives an exact zero increment in the direct arithmetic route.
            damage = self.history_alpha + (base_increment + self.eta)
        if self.check_finite:
            _require_finite("damage", damage)
        self.last_forward_id += 1
        self._last_snapshot = ProjectedDamageSnapshot(
            forward_id=self.last_forward_id,
            mode=mode,
            raw_damage=raw_damage,
            base_damage=base_damage,
            damage=damage,
        )
        return damage

    def forward(self, raw_damage: torch.Tensor) -> torch.Tensor:
        """Default callable route for a frozen-network eta block.

        A runner should use :meth:`damage` with an explicit mode when it sets
        ``FieldComputation.alpha_constraint``.  This default remains useful
        for direct field tests and preserves ``d / d eta == 1``.
        """

        return self.damage(raw_damage, mode="direct_damage")

    def constraint_for(self, mode: str) -> TensorConstraint:
        """Return a field-compatible callable for one explicit route."""

        mode = self._require_mode(mode)

        def constraint(raw_damage: torch.Tensor) -> torch.Tensor:
            return self.damage(raw_damage, mode=mode)

        return constraint

    def latest(self) -> ProjectedDamageSnapshot:
        """Return the tensors from the latest concrete carrier forward."""

        if self._last_snapshot is None:
            raise RuntimeError("ReferenceBaseProjectedDamage has not received a raw head")
        return self._last_snapshot

    @torch.no_grad()
    def set_damage_(
        self,
        target: torch.Tensor,
        raw_damage: torch.Tensor,
    ) -> torch.Tensor:
        """Store a feasible held target and reconstruct eta at a raw-head state.

        This is the handoff between alternating blocks.  If theta/RPROP has
        changed ``q`` while damage was held, calling
        ``set_damage_(target, q)`` makes the subsequent ``direct_damage``
        route reconstruct that same target (up to ordinary floating-point
        addition) while preserving its unit eta derivative.
        """

        _require_same_layout(target, self.history_alpha, "target", "history_alpha")
        if self.check_finite:
            _require_finite("target", target)
        target_detached = target.detach()
        if not bool(torch.all(target_detached >= self.history_alpha)):
            raise ValueError("target violates the irreversible lower bound")
        if not bool(torch.all(target_detached <= 1.0)):
            raise ValueError("target exceeds the damage upper bound")
        base_damage = self._evaluate_base(raw_damage)
        base_increment = (base_damage - self.base_reference).detach()
        reconstructed_eta = target_detached - self.history_alpha - base_increment
        if self.check_finite:
            _require_finite("reconstructed_eta", reconstructed_eta)
        self.eta.copy_(reconstructed_eta)
        self.held_damage.copy_(target_detached)
        return self.eta.detach().clone()

    @torch.no_grad()
    def hold_current_damage_(self, raw_damage: torch.Tensor) -> torch.Tensor:
        """Capture the current direct field as the next detached theta target."""

        base_damage = self._evaluate_base(raw_damage)
        base_increment = (base_damage - self.base_reference).detach()
        target = (self.history_alpha + (base_increment + self.eta)).detach().clone()
        self.set_damage_(target, raw_damage)
        return target

    @torch.no_grad()
    def project_eta_(self, raw_damage: torch.Tensor) -> EtaProjection:
        """Project eta to its exact interval without adding a graph operation.

        The interval follows directly from ``h <= h + (b-b_ref) + eta <= 1``:

        ``-(b-b_ref) <= eta <= 1-h-(b-b_ref)``.
        """

        if self.check_finite:
            _require_finite("eta", self.eta)
        bounds = self._bounds_from_base(self._evaluate_base(raw_damage))
        before = self.eta.detach().clone()
        after = _clip_to_interval(before, bounds.lower, bounds.upper)
        self.eta.copy_(after)
        return EtaProjection(
            eta_before=before,
            eta_after=self.eta.detach().clone(),
            lower=bounds.lower,
            upper=bounds.upper,
            clipped_to_lower=before < bounds.lower,
            clipped_to_upper=before > bounds.upper,
        )

    def projected_residual(
        self,
        raw_damage: torch.Tensor,
        gradient: torch.Tensor,
        *,
        step_size: float = 1.0,
        metric: Optional[torch.Tensor] = None,
        active_tolerance: float = 0.0,
    ) -> ProjectedResidual:
        """Return the eta-block KKT residual at a fixed raw-head state.

        With a positive diagonal metric ``M`` the residual is

        ``(eta - Pi_[lower,upper](eta - step_size * M^{-1} grad)) / step_size``.

        It certifies stationarity only for the direct nodal eta block while the
        raw head and displacement parameters are held fixed; it is not a
        global network KKT certificate.
        """

        step = _require_positive_finite_scalar("step_size", step_size)
        tolerance = _require_positive_finite_scalar(
            "active_tolerance", active_tolerance
        ) if active_tolerance != 0.0 else 0.0
        _require_same_layout(gradient, self.eta, "gradient", "eta")
        if self.check_finite:
            _require_finite("gradient", gradient)
            _require_finite("eta", self.eta)
        if metric is None:
            scaled_gradient = gradient.detach()
        else:
            _require_same_layout(metric, self.eta, "metric", "eta")
            if self.check_finite:
                _require_finite("metric", metric)
            if not bool(torch.all(metric > 0)):
                raise ValueError("metric must be strictly positive")
            scaled_gradient = gradient.detach() / metric.detach()

        bounds = self.eta_bounds(raw_damage)
        current = self.eta.detach()
        projected = _clip_to_interval(current - step * scaled_gradient, bounds.lower, bounds.upper)
        residual = (current - projected) / step

        fixed = torch.isclose(bounds.lower, bounds.upper, rtol=0.0, atol=tolerance)
        lower_active = (~fixed) & (current <= bounds.lower + tolerance)
        upper_active = (~fixed) & (current >= bounds.upper - tolerance)
        blocked_lower = lower_active & (gradient.detach() >= 0)
        released_lower = lower_active & (gradient.detach() < 0)
        blocked_upper = upper_active & (gradient.detach() <= 0)
        released_upper = upper_active & (gradient.detach() > 0)
        return ProjectedResidual(
            residual=residual,
            projected_eta=projected,
            lower_active=lower_active,
            upper_active=upper_active,
            fixed=fixed,
            blocked_lower=blocked_lower,
            released_lower=released_lower,
            blocked_upper=blocked_upper,
            released_upper=released_upper,
        )

    @torch.no_grad()
    def feasibility_metrics(
        self,
        raw_damage: torch.Tensor,
        *,
        connectivity: Optional[torch.Tensor] = None,
    ) -> dict[str, float]:
        """Return nodewise and optional TRI3 feasibility diagnostics."""

        base_damage = self._evaluate_base(raw_damage)
        base_increment = (base_damage - self.base_reference).detach()
        # Use the exact arithmetic order of ``direct_damage``.  Otherwise a
        # diagnostic can manufacture a one-ulp pseudo-violation at a bound
        # even though the actual field route returns the bound exactly.
        damage = self.history_alpha + (base_increment + self.eta)
        if self.check_finite:
            _require_finite("eta", self.eta)
            _require_finite("damage", damage)
        lower_increment = damage - self.history_alpha
        upper_slack = 1.0 - damage
        metrics = dict(
            d_min=float(damage.min()),
            d_max=float(damage.max()),
            min_damage_increment=float(lower_increment.min()),
            min_upper_slack=float(upper_slack.min()),
            max_node_lower_violation=float(torch.clamp_min(-lower_increment, 0.0).max()),
            max_node_upper_violation=float(torch.clamp_min(-upper_slack, 0.0).max()),
        )
        if connectivity is not None:
            gp_increment = tri3_values(lower_increment, connectivity)
            gp_upper_slack = tri3_values(upper_slack, connectivity)
            metrics.update(
                min_tri3_damage_increment=float(gp_increment.min()),
                min_tri3_upper_slack=float(gp_upper_slack.min()),
                max_tri3_lower_violation=float(torch.clamp_min(-gp_increment, 0.0).max()),
                max_tri3_upper_violation=float(torch.clamp_min(-gp_upper_slack, 0.0).max()),
            )
        return metrics
