"""Feasible damage parameterisation and objective components for S04-E040.

This module is deliberately separate from :mod:`compute_energy`: existing
standard PIDL paths retain their historical irreversibility-penalty objective.
The E040 runner imports the two helpers here to (1) make damage feasible by
construction relative to its frozen accepted state and (2) differentiate only
elastic and damage energy.  No irreversibility penalty is evaluated here.

The raw damage head is denoted ``q``.  For accepted nodal damage ``h`` and a
frozen reference head ``q_ref``, the mapping is

    t = scale * clamp_min(q - q_ref, 0)
    d = h + (1 - h) * t / (1 + t).

Thus ``d == h`` exactly in the floating-point operation sequence when
``q == q_ref``.  ``h`` and ``q_ref`` are detached inside the mapping so a
caller cannot accidentally optimise a previous accepted state.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

import torch

try:  # Support both ``source.feasible_damage`` and source-on-sys.path imports.
    from .compute_energy import gradients, strain_energy_with_split
except ImportError:  # pragma: no cover - exercised by production runner layout
    from compute_energy import gradients, strain_energy_with_split


DEFAULT_RAW_INCREMENT_SCALE = 0.25


def freeze_damage_state(
    history_alpha: torch.Tensor,
    raw_damage_reference: torch.Tensor,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Return detached clones for one physical step's frozen damage state.

    The returned tensors intentionally do not share storage with the supplied
    accepted-state tensors.  The runner must create or refresh this pair only
    when it accepts a physical step, together with its network and fatigue
    history transaction.
    """
    _require_same_tensor_layout(
        history_alpha, raw_damage_reference, "history_alpha", "raw_damage_reference"
    )
    return history_alpha.detach().clone(), raw_damage_reference.detach().clone()


def state_referenced_damage(
    raw_damage: torch.Tensor,
    history_alpha: torch.Tensor,
    raw_damage_reference: torch.Tensor,
    *,
    increment_scale: float = DEFAULT_RAW_INCREMENT_SCALE,
) -> torch.Tensor:
    """Map a raw damage head to a nodally feasible damage field.

    ``history_alpha`` and ``raw_damage_reference`` are constants for the
    duration of a physical-step solve.  The returned field follows the
    state-referenced mapping in this module's header.  Finite inputs with
    ``0 <= history_alpha <= 1`` give ``history_alpha <= d <= 1`` in floating
    point (with equality at the reference state); the runner remains
    responsible for its explicit finite and Gauss-point acceptance checks.

    ``torch.clamp_min`` is intentional.  Its derivative at zero follows the
    active/right branch in PyTorch, avoiding a ``where`` branch that can hide
    non-finite values in the inactive expression.
    """
    _require_same_tensor_layout(raw_damage, history_alpha, "raw_damage", "history_alpha")
    _require_same_tensor_layout(
        raw_damage, raw_damage_reference, "raw_damage", "raw_damage_reference"
    )
    if (
        isinstance(increment_scale, bool)
        or not isinstance(increment_scale, (float, int))
        or not math.isfinite(float(increment_scale))
        or not float(increment_scale) > 0.0
    ):
        raise ValueError("increment_scale must be a positive finite scalar")

    # These are accepted-state data, never optimisation variables.
    h = history_alpha.detach()
    q_ref = raw_damage_reference.detach()
    scale = raw_damage.new_tensor(float(increment_scale))
    t = scale * torch.clamp_min(raw_damage - q_ref, 0.0)
    bounded_increment = t / (1.0 + t)
    return h + (1.0 - h) * bounded_increment


def compute_elastic_damage_energy_per_elem(
    inp: torch.Tensor,
    u: torch.Tensor,
    v: torch.Tensor,
    alpha: torch.Tensor,
    matprop,
    pffmodel,
    area_elem: torch.Tensor,
    T_conn: Optional[torch.Tensor] = None,
    *,
    f_fatigue=1.0,
    g_stiffness_override: Optional[torch.Tensor] = None,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Return per-element elastic and damage energies without ``E_irr``.

    This mirrors the elastic and damage branches of
    :func:`compute_energy.compute_energy_per_elem`, including numerical
    gradients, fatigue degradation, and a stiffness override.  It does *not*
    accept ``hist_alpha`` and never calls ``pffmodel.irrPenalty``; therefore an
    irreversibility energy cannot enter this function's autograd graph.
    """
    strain_11, strain_22, strain_12, grad_alpha_x, grad_alpha_y = gradients(
        inp, u, v, alpha, area_elem, T_conn
    )

    if T_conn is None:
        alpha_elem = alpha
    else:
        alpha_elem = (
            alpha[T_conn[:, 0]] + alpha[T_conn[:, 1]] + alpha[T_conn[:, 2]]
        ) / 3

    damage_fn, _, c_w = pffmodel.damageFun(alpha_elem)
    elastic_density, _ = strain_energy_with_split(
        strain_11,
        strain_22,
        strain_12,
        alpha_elem,
        matprop,
        pffmodel,
        g_stiffness_override=g_stiffness_override,
    )
    elastic_energy = area_elem * elastic_density
    damage_energy = f_fatigue * (
        matprop.w1
        / c_w
        * (damage_fn + matprop.l0**2 * (grad_alpha_x**2 + grad_alpha_y**2))
    ) * area_elem
    return elastic_energy, damage_energy


def compute_elastic_damage_energy(
    inp: torch.Tensor,
    u: torch.Tensor,
    v: torch.Tensor,
    alpha: torch.Tensor,
    matprop,
    pffmodel,
    area_elem: torch.Tensor,
    T_conn: Optional[torch.Tensor] = None,
    *,
    f_fatigue=1.0,
    crack_tip_weights: Optional[torch.Tensor] = None,
    element_subset: Optional[torch.Tensor] = None,
    importance_weights: Optional[torch.Tensor] = None,
    element_mask: Optional[torch.Tensor] = None,
    g_stiffness_override: Optional[torch.Tensor] = None,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Aggregate ``E_el`` and ``E_d`` with standard ``compute_energy`` rules.

    The mask, subset/importance-sampling, and crack-tip-weight order is kept
    byte-for-byte equivalent in intent to ``compute_energy`` for its first two
    components.  The function has no irreversibility-state argument by design.
    """
    elastic_energy, damage_energy = compute_elastic_damage_energy_per_elem(
        inp,
        u,
        v,
        alpha,
        matprop,
        pffmodel,
        area_elem,
        T_conn,
        f_fatigue=f_fatigue,
        g_stiffness_override=g_stiffness_override,
    )

    if element_mask is not None:
        mask = element_mask.to(device=elastic_energy.device, dtype=elastic_energy.dtype)
        elastic_energy = elastic_energy * mask
        damage_energy = damage_energy * mask

    if element_subset is not None:
        elastic_subset = elastic_energy[element_subset]
        damage_subset = damage_energy[element_subset]
        if importance_weights is not None:
            return (
                torch.mean(importance_weights * elastic_subset),
                torch.mean(importance_weights * damage_subset),
            )
        return torch.mean(elastic_subset), torch.mean(damage_subset)

    if crack_tip_weights is not None:
        return (
            torch.sum(crack_tip_weights * elastic_energy),
            torch.sum(crack_tip_weights * damage_energy),
        )
    return torch.sum(elastic_energy), torch.sum(damage_energy)


def _require_same_tensor_layout(
    first: torch.Tensor,
    second: torch.Tensor,
    first_name: str,
    second_name: str,
) -> None:
    """Reject a silent state mismatch before a GPU optimisation starts."""
    if not isinstance(first, torch.Tensor) or not isinstance(second, torch.Tensor):
        raise TypeError(f"{first_name} and {second_name} must be torch.Tensor instances")
    if first.shape != second.shape:
        raise ValueError(
            f"{first_name}.shape={tuple(first.shape)} does not match "
            f"{second_name}.shape={tuple(second.shape)}"
        )
    if first.device != second.device:
        raise ValueError(f"{first_name}.device does not match {second_name}.device")
    if first.dtype != second.dtype:
        raise ValueError(f"{first_name}.dtype does not match {second_name}.dtype")
