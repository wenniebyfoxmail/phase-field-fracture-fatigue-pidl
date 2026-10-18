"""Opt-in SENT crack-line and initial-field alignment on ordered native nodes.

Frozen buffers are part of the representation, not optimizer parameters.
This module neither trains nor updates any history. It deliberately retains
the legacy soft tails: a hard crack line is not hard box/irreversibility.
"""
import torch
from torch import nn


class NodalDamageAlignment(nn.Module):
    def __init__(self, coordinates, *, mode, initial_damage=None,
                 raw_reference=None, expected_crack_mask=None):
        super().__init__()
        if mode not in {"hard_line", "fem_initial"}:
            raise ValueError("mode must be hard_line or fem_initial")
        xy = coordinates.detach().clone()
        if (xy.ndim != 2 or xy.shape[1] != 2 or not xy.is_floating_point()
                or not bool(torch.isfinite(xy).all())):
            raise ValueError("finite ordered [N,2] coordinates required")
        tol = 1e-12
        mask = ((xy[:, 0] >= -.5-tol) & (xy[:, 0] <= tol)
                & (xy[:, 1].abs() <= tol))
        if not bool(mask.any()):
            raise ValueError("no SENT precrack line nodes")
        if expected_crack_mask is not None:
            expected = torch.as_tensor(expected_crack_mask, device=xy.device)
            if expected.dtype != torch.bool or not torch.equal(mask, expected):
                raise ValueError("FEM fixed damage DOFs do not match SENT crack line")
        self.mode = mode
        self.register_buffer("coordinates", xy)
        self.register_buffer("crack_mask", mask)
        if mode == "fem_initial":
            if initial_damage is None or raw_reference is None:
                raise ValueError("fem_initial requires initial damage and frozen raw origin")
            d0 = self._vector(initial_damage, xy, "initial damage")
            r0 = self._vector(raw_reference, xy, "raw reference")
            if bool(((d0 < 0) | (d0 > 1)).any()) or not bool((d0[mask] == 1).all()):
                raise ValueError("FEM initial field must be in [0,1], with crack line exactly 1")
            self.register_buffer("initial_damage", d0)
            self.register_buffer("raw_reference", r0)
            self.register_buffer("anchor_raw", 4*d0-2)
        elif initial_damage is not None or raw_reference is not None:
            raise ValueError("hard_line does not accept an initial-field anchor")

    @staticmethod
    def _vector(value, coordinates, label):
        result = torch.as_tensor(value, device=coordinates.device,
                                 dtype=coordinates.dtype).detach().clone()
        if result.shape != (len(coordinates),) or not bool(torch.isfinite(result).all()):
            raise ValueError(f"finite same-node {label} required")
        return result

    def get_extra_state(self):
        return {"schema": "sent_nodal_damage_alignment_v1", "mode": self.mode}

    def set_extra_state(self, state):
        if state != self.get_extra_state():
            raise ValueError("incompatible nodal damage mapping checkpoint")

    def forward(self, coordinates, raw_alpha, legacy_map):
        if (coordinates.requires_grad or coordinates.dtype != self.coordinates.dtype
                or coordinates.device != self.coordinates.device
                or not torch.equal(coordinates, self.coordinates)):
            raise ValueError("alignment requires the identical ordered native nodes; no arbitrary probes")
        if (raw_alpha.shape != (len(coordinates),) or raw_alpha.dtype != coordinates.dtype
                or raw_alpha.device != coordinates.device
                or not bool(torch.isfinite(raw_alpha).all())):
            raise ValueError("finite same-node raw damage required")
        if (getattr(legacy_map, "support", None) != 2.
                or getattr(legacy_map, "coeff", None) != 1e-3):
            raise ValueError("alignment is scoped to the legacy nonsmooth damage map")
        if self.mode == "hard_line":
            damage = legacy_map(raw_alpha)
        else:
            # Parenthesized delta is exactly zero at the frozen network origin.
            # Subtracting the mapped anchor makes the initial field exact in
            # the declared tensor dtype, without an inverse-map roundoff drift.
            shifted = self.anchor_raw + (raw_alpha-self.raw_reference)
            damage = self.initial_damage + (legacy_map(shifted)-legacy_map(self.anchor_raw))
        return torch.where(self.crack_mask, torch.ones_like(damage), damage)

    def initial_history(self, original_history):
        """Create an arm's input once; never call this after optimization steps."""
        history = self._vector(original_history, self.coordinates, "input history")
        if self.mode == "fem_initial":
            return self.initial_damage.detach().clone()
        return torch.where(self.crack_mask, torch.ones_like(history), history)
