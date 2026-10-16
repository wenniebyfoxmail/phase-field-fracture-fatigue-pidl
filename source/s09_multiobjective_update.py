"""Deterministic gradient balancing and conflict projection for S09-E008."""
from __future__ import annotations

import torch


def merge_objective_gradients(gradients, *, clip_norm: float = 1.0, eps: float = 1e-12):
    """Equalise positive norms, project conflicts in fixed cyclic order, average and clip.

    ``eps`` is a norm threshold.  Squared norms are therefore compared with
    ``eps**2``.  For an even number of positive objectives ``torch.median``
    deliberately selects the lower median; this is part of the frozen method.
    """
    if not gradients:
        raise ValueError("at least one objective gradient is required")
    grads = [torch.as_tensor(value) for value in gradients]
    shape = grads[0].shape
    if any(value.shape != shape for value in grads):
        raise ValueError("objective gradients must share a flattened shape")
    if any(not torch.isfinite(value).all() for value in grads):
        raise FloatingPointError("nonfinite objective gradient")
    if clip_norm <= 0 or eps <= 0:
        raise ValueError("clip_norm and eps must be positive")
    norms = torch.stack([value.norm() for value in grads])
    positive = norms > eps
    reference_norm = norms[positive].median() if positive.any() else norms.new_zeros(())
    balanced = [
        value * (reference_norm / norm) if norm > eps else torch.zeros_like(value)
        for value, norm in zip(grads, norms)
    ]
    immutable = [value.clone() for value in balanced]
    projected = []
    conflicts = 0
    for i, value in enumerate(balanced):
        current = value.clone()
        for offset in range(1, len(balanced)):
            other = immutable[(i + offset) % len(balanced)]
            denominator = other.dot(other)
            if denominator <= eps * eps:
                continue
            dot = current.dot(other)
            if dot < 0:
                current = current - dot / denominator * other
                conflicts += 1
        projected.append(current)
    merged = torch.stack(projected).mean(0)
    preclip = merged.norm()
    if preclip > clip_norm:
        merged = merged * (clip_norm / preclip)
    diagnostics = {
        "raw_norms": norms,
        "reference_norm": reference_norm,
        "conflict_projection_count": conflicts,
        "merged_norm_before_clip": preclip,
        "merged_norm_after_clip": merged.norm(),
        "zero_gradient_count": int((~positive).sum()),
        "norm_epsilon": eps,
        "projection_squared_norm_epsilon": eps * eps,
        "positive_norm_median": "lower_median_for_even_count",
        "averaging": "all_objective_directions_including_zero_directions",
        "order": "fixed_cyclic_immutable_balanced_references",
    }
    return merged, diagnostics
