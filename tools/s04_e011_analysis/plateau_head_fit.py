"""Fixed-feature constructive field witnesses; no training or energy minimization.

Only the final linear output head is fitted. A failed fit is not a capacity lower
bound for a network whose hidden weights may change. Smooth-damage fitting
minimizes raw-logit target error, NOT physical damage error or physical energy.
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import svd


def _array(value, name):
    """Accept NumPy or CPU/GPU torch tensors without depending on torch."""
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    out = np.asarray(value, dtype=np.float64)
    if not np.isfinite(out).all():
        raise ValueError(f"{name} contains nonfinite values")
    return out


def _features_mass(features, mass):
    h = _array(features, "features")
    if h.ndim != 2 or not h.shape[0] or not h.shape[1]:
        raise ValueError("features must be nonempty n by p")
    w = _array(mass, "mass").reshape(-1)
    if w.shape != (h.shape[0],) or np.any(w < 0) or not np.any(w > 0):
        raise ValueError("mass must have n nonnegative entries and positive sum")
    return np.column_stack((h, np.ones(h.shape[0]))), w


def _weighted_error(actual, target, mass):
    if actual.ndim == 1:
        actual, target = actual[:, None], target[:, None]
    error2 = np.sum(mass[:, None] * (actual - target)**2, axis=0)
    target2 = np.sum(mass[:, None] * target**2, axis=0)
    return dict(weighted_l2=np.sqrt(error2).tolist(),
                weighted_rel_l2=[float(np.sqrt(e/t)) if t > 0 else None
                                 for e, t in zip(error2, target2)],
                joint_weighted_l2=float(np.sqrt(error2.sum())),
                joint_weighted_rel_l2=float(np.sqrt(error2.sum()/target2.sum()))
                if target2.sum() > 0 else None,
                max_abs=float(np.max(np.abs(actual-target))))


def _fit(design, target, mass, rcond):
    """Direct weighted economy SVD; never square the condition number in Gram."""
    if not np.isfinite(rcond) or not 0 < rcond < 1:
        raise ValueError("rcond must lie strictly between zero and one")
    if target.ndim == 1:
        target = target[:, None]
    root = np.sqrt(mass)
    a = design * root[:, None]
    b = target * root[:, None]
    left, singular, right = svd(a, full_matrices=False, check_finite=True,
                               lapack_driver="gesdd")
    threshold = float(rcond*singular[0]) if len(singular) else 0.
    keep = singular > threshold
    coefficient = np.zeros((design.shape[1], target.shape[1]))
    if np.any(keep):
        coefficient = right[keep].T @ ((left[:, keep].T @ b) / singular[keep, None])
    residual = a @ coefficient - b
    normal = a.T @ residual
    rhs_norm = float(np.linalg.norm(a.T @ b))
    retained_normal = right[keep] @ normal
    report = dict(method="direct_weighted_economy_svd", rcond=float(rcond),
                  rank=int(keep.sum()), columns=int(a.shape[1]), rows=int(a.shape[0]),
                  singular_value_cutoff=threshold, singular_values=singular.tolist(),
                  retained_condition_number=float(singular[0]/singular[keep][-1])
                  if np.any(keep) else None,
                  full_column_rank=bool(keep.sum() == a.shape[1]),
                  normal_residual_l2=float(np.linalg.norm(normal)),
                  normal_residual_relative=float(np.linalg.norm(normal)/rhs_norm)
                  if rhs_norm > 0 else None,
                  retained_normal_residual_l2=float(np.linalg.norm(retained_normal)),
                  retained_normal_residual_relative=float(np.linalg.norm(retained_normal)/rhs_norm)
                  if rhs_norm > 0 else None)
    # Full normal residual may remain when small singular directions are truncated.
    return coefficient, report


def fit_uv_head(features, coords, U, theta, target_u, target_v, mass,
                *, y_bounds=(-0.5, 0.5), rcond=1e-10):
    """Fit physical UV under the original smooth boundary bubble/lift.

    Returns head with shape (2,p+1); the final column is bias. Use it as
    output_layer.weight[:2,:], output_layer.bias[:2] respectively. This helper
    models the legacy top/bottom BC branch only (no enrichment/exact-BC option).
    The design is U*(y-y0)*(yL-y)*[features,1], never divided by the bubble.
    """
    h, w = _features_mass(features, mass)
    xy = _array(coords, "coords")
    tu, tv = _array(target_u, "target_u").reshape(-1), _array(target_v, "target_v").reshape(-1)
    if xy.shape != (len(h), 2) or tu.shape != (len(h),) or tv.shape != (len(h),):
        raise ValueError("coords/targets must match n feature rows")
    y0, yl = map(float, y_bounds)
    U, theta = float(U), float(theta)
    if not np.isfinite([U, theta, y0, yl]).all() or yl <= y0:
        raise ValueError("finite load/angle and increasing y_bounds required")
    y = xy[:, 1]
    if np.any(y < y0-1e-12) or np.any(y > yl+1e-12):
        raise ValueError("coordinates are outside the specified domain")
    bubble = (y-y0)*(yl-y)
    lift = U*((y-y0)/(yl-y0))[:, None]*np.array([[np.cos(theta), np.sin(theta)]])
    target = np.column_stack((tu, tv))
    design = (U*bubble)[:, None]*h
    coefficient, report = _fit(design, target-lift, w, rcond)
    physical = design @ coefficient + lift
    boundary = (np.abs(y-y0) <= 1e-12) | (np.abs(y-yl) <= 1e-12)
    return dict(head=coefficient.T, u=physical[:, 0], v=physical[:, 1],
                fit=report, physical_error=_weighted_error(physical, target, w),
                target_boundary_mismatch_max=float(np.max(np.abs(target[boundary]-lift[boundary])))
                if np.any(boundary) else None,
                y_bounds=[y0, yl], U=U, theta=theta,
                interpretation="best retained-SVD output head in fixed features; not full-network capacity")


def fit_smooth_damage_head(features, target_d, mass, anchor, *, clip_epsilon=1e-7,
                           rcond=1e-10):
    """Construct a raw-head witness using the UNCHANGED frozen Smooth-B0 anchor.

    anchor must contain original r0, anchor_logit and positive anchor_scale.
    Exact 0/1 targets need finite-logit clipping. The returned physical damage
    is always evaluated through the original anchor. This is raw-space weighted
    LS; it is neither the minimum physical-d error nor an energy/KKT solve.
    """
    h, w = _features_mass(features, mass)
    target = _array(target_d, "target_d").reshape(-1)
    if target.shape != (len(h),) or np.any(target < 0) or np.any(target > 1):
        raise ValueError("target damage must have n entries in [0,1]")
    if not np.isfinite(clip_epsilon) or not 0 < clip_epsilon < .5:
        raise ValueError("clip_epsilon must lie strictly between zero and 0.5")
    frozen = {name: _array(anchor[name], name).reshape(-1)
              for name in ("r0", "anchor_logit", "anchor_scale")}
    if any(a.shape != (len(h),) for a in frozen.values()) or np.any(frozen["anchor_scale"] <= 0):
        raise ValueError("anchor is mesh/order locked and must have positive scales")
    clipped = np.clip(target, clip_epsilon, 1-clip_epsilon)
    logit = np.log(clipped)-np.log1p(-clipped)
    raw_target = frozen["r0"]+(logit-frozen["anchor_logit"])/frozen["anchor_scale"]
    coefficient, report = _fit(h, raw_target, w, rcond)
    raw = (h @ coefficient)[:, 0]
    mapped_logit = frozen["anchor_logit"]+frozen["anchor_scale"]*(raw-frozen["r0"])
    damage = np.empty_like(mapped_logit)
    positive = mapped_logit >= 0
    damage[positive] = 1/(1+np.exp(-mapped_logit[positive]))
    expz = np.exp(mapped_logit[~positive])
    damage[~positive] = expz/(1+expz)
    return dict(head=coefficient[:, 0], raw=raw, d=damage, fit=report,
                raw_error=_weighted_error(raw, raw_target, w),
                physical_error=_weighted_error(damage, target, w),
                clipped_target_error=_weighted_error(damage, clipped, w),
                clip_epsilon=float(clip_epsilon), clipped_nodes=int(np.count_nonzero(clipped != target)),
                target_clip_max_abs=float(np.max(np.abs(clipped-target))),
                interpretation="constructive raw-logit LS witness; not best physical damage fit, physical optimizer or capacity lower bound")
