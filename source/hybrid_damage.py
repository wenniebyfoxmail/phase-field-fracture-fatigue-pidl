"""Full nodal-K AT1 QP, fixed-DOF elimination and fresh final KKT audit.

Reuses historical energy assembly, never its GP-only feasible domain.
"""
from dataclasses import dataclass
import hashlib

import numpy as np
from scipy import sparse

from native_q4_damage_qp import assemble_at1_damage_qp, gauss_interpolation_matrix


@dataclass(frozen=True)
class NodalQP:
    hessian: sparse.csc_matrix
    linear: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    identity: str


def assemble_nodal_qp(kin, psi, fatigue, previous, crack, *, w1, length_scale, thickness=1.):
    lower = np.asarray(previous, dtype=float).copy()
    crack = np.asarray(crack)
    if (lower.shape != (len(kin.points),) or not np.isfinite(lower).all()
            or np.any(lower < 0) or np.any(lower > 1)
            or crack.shape != lower.shape or crack.dtype != bool):
        raise ValueError("invalid nodal lower or crack mask")
    if np.any(lower[crack] != 1):
        raise ValueError("accepted precrack must already equal one")
    old_gp = (gauss_interpolation_matrix(kin) @ lower).reshape(-1, 4)
    base = assemble_at1_damage_qp(kin, psi, fatigue, old_gp,
                                w1=w1, length_scale=length_scale, thickness=thickness)
    if base.minimum_local_eigenvalue < -1.e-10 * base.maximum_local_scale:
        raise RuntimeError("non-PSD AT1 assembly")
    upper = np.ones_like(lower)
    # Nodes already at one (including original precrack) are eliminated exactly.
    h = hashlib.sha256()
    for a in (base.hessian.data, base.hessian.indices, base.hessian.indptr,
              base.linear, lower, upper):
        h.update(np.ascontiguousarray(a).tobytes())
    return NodalQP(base.hessian, base.linear, lower, upper, h.hexdigest())


def kkt_audit(qp, damage, *, gradient_scale, bound_tolerance):
    x = np.asarray(damage, dtype=float)
    if (x.shape != qp.lower.shape or not np.isfinite(x).all()
            or not np.isfinite([gradient_scale, bound_tolerance]).all()
            or gradient_scale <= 0 or bound_tolerance <= 0):
        raise ValueError("invalid audit input or fixed scales")
    g = np.asarray(qp.hessian @ x + qp.linear)
    fixed = qp.lower == qp.upper
    lo = (x <= qp.lower + bound_tolerance) & ~fixed
    hi = (x >= qp.upper - bound_tolerance) & ~fixed
    # Near coincident bounds: projected residual disambiguates; never both masks.
    hi &= ~lo
    interior = ~(lo | hi | fixed)
    violation = np.zeros_like(g)
    violation[lo] = np.maximum(-g[lo], 0)
    violation[hi] = np.maximum(g[hi], 0)
    violation[interior] = np.abs(g[interior])
    # A fixed physical gradient scale, never a solution-dependent denominator.
    projected = x - np.clip(x - g / gradient_scale, qp.lower, qp.upper)
    primal = max(float(np.max(qp.lower - x)), float(np.max(x - qp.upper)), 0.)
    return {"operator_id": qp.identity, "primal_inf": primal,
            "kkt_scaled_inf": float(np.max(violation)) / gradient_scale,
            "kkt_l2": float(np.linalg.norm(violation)),
            "projected_inf": float(np.max(np.abs(projected)))}


def solve_nodal_qp(qp, initial, *, eps, max_iter, time_limit):
    import osqp
    if (not np.isfinite([eps, time_limit]).all() or min(eps, time_limit) <= 0
            or type(max_iter) is not int or max_iter <= 0):
        raise ValueError("invalid QP limits")
    initial = np.asarray(initial, dtype=float)
    if (initial.shape != qp.lower.shape or not np.isfinite(initial).all()
            or np.any(initial < qp.lower) or np.any(initial > qp.upper)):
        raise ValueError("QP initial guess must be feasible")
    fixed = qp.lower == qp.upper
    free = np.flatnonzero(~fixed)
    x = qp.lower.copy()
    if not len(free):
        return x, {"status": "all_fixed", "iterations": 0}
    hf = qp.hessian[free][:, free].tocsc()
    linear = qp.linear[free] + qp.hessian[free][:, fixed] @ x[fixed]
    solver = osqp.OSQP()
    solver.setup(P=hf, q=linear, A=sparse.eye(len(free), format="csc"),
                 l=qp.lower[free], u=qp.upper[free], eps_abs=eps, eps_rel=eps,
                 max_iter=max_iter, time_limit=time_limit, polishing=True, verbose=False)
    solver.warm_start(x=initial[free])
    result = solver.solve(raise_error=False)
    if result.info.status_val != 1 or result.x is None or not np.isfinite(result.x).all():
        raise RuntimeError(f"nodal QP not solved: {result.info.status}")
    raw = np.asarray(result.x)
    correction = float(np.max(np.abs(raw - np.clip(raw, qp.lower[free], qp.upper[free]))))
    if correction > eps:
        raise RuntimeError("QP bound error exceeds declared solver precision")
    # Restore exact feasibility after solver roundoff, then re-audit the ORIGINAL
    # final operator in the caller; clipping is not a convergence certificate.
    x[free] = np.clip(raw, qp.lower[free], qp.upper[free])
    return x, {"status": result.info.status, "iterations": int(result.info.iter),
               "roundoff_projection_inf": correction}
