"""Conditional AT1 damage QP on the declared T3 nodal support.

Physical energy reproduces the *centroid* rule in compute_energy.py at
e9dc2632457f5f566db95c75b856ad96170fd0e6, with fixed displacement/fatigue:

  sum_e area_e [(1-mean(d_e))**2 psi_plus_e + psi_minus_e
          + f_e*w1/cw*(mean(d_e) + l0**2*|grad(d_e)|**2)].

The supplied area is used in both integration and the historical gradient
denominator. GP3 is used ONLY for G's irreversibility constraints, never for
the physical energy. No neural weights, L2, log objective, history update,
mesh loading, or training is implemented here. A qualified result is a
conditional physical-field reference, not the optimum of the neural problem.

OSQP is optional at import time, mandatory at solve time; there is no fallback.
Settings/API: https://osqp.org/docs/interfaces/python.html and
https://osqp.org/docs/interfaces/solver_settings.html (checked 2026-10-22).
"""

from dataclasses import dataclass
import math
import time

import numpy as np
from scipy import sparse


CERTIFICATE_TOL = 1e-7
MAX_TIME_SECONDS = 100.0
PHYSICS_ENERGY_RTOL = 1e-5
PHYSICS_GRADIENT_ATOL = 1e-6
GP3_BARYCENTRIC = np.array([[4., 1., 1.], [1., 4., 1.], [1., 1., 4.]]) / 6.


class MissingOSQPError(RuntimeError):
    """The required QP solver is unavailable; no alternate solver was used."""


@dataclass(frozen=True)
class T3DamageQP:
    H: sparse.csc_matrix
    q: np.ndarray
    const: float
    centroid: sparse.csr_matrix
    gp: sparse.csr_matrix
    local_gradients: np.ndarray

    @property
    def n_nodes(self):
        return self.q.size


@dataclass(frozen=True)
class LinearConstraints:
    A: sparse.csc_matrix
    lower: np.ndarray
    upper: np.ndarray
    mode: str


@dataclass(frozen=True)
class ReferenceResult:
    x: np.ndarray | None
    y: np.ndarray | None
    accepted: bool
    status: str
    certificate: dict
    elapsed_seconds: float
    iterations: int
    solver_version: str


def _vector(value, size, name, *, scalar=False):
    a = np.asarray(value, dtype=np.float64)
    if scalar and a.ndim == 0:
        a = np.full(size, float(a))
    if a.shape != (size,) or not np.isfinite(a).all():
        raise ValueError(f"{name} must be finite with shape ({size},)")
    return a.copy()


def _positive(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def sparse_gp_matrix(conn, n_nodes):
    """GP3 barycentric interpolation, rows ordered (element, GP0/GP1/GP2)."""
    t = np.asarray(conn)
    if (t.ndim != 2 or t.shape[1] != 3 or not len(t)
            or t.dtype.kind not in "iu" or np.any(t < 0) or np.any(t >= n_nodes)):
        raise ValueError("conn must be nonempty integer T3 connectivity")
    rows = np.repeat(np.arange(3 * len(t)), 3)
    cols = np.repeat(t, 3, axis=0).reshape(-1)
    values = np.tile(GP3_BARYCENTRIC.reshape(-1), len(t))
    return sparse.csr_matrix((values, (rows, cols)), shape=(3 * len(t), n_nodes))


def assemble_t3_damage(xy, conn, area, psi_plus, psi_minus, f, w1, cw, l0):
    """Assemble E(d)=0.5*d.T@H@d+q.T@d+const in float64.

    xy: (N,2), conn: zero-based (M,3), area: positive (M,).
    psi_plus/psi_minus are nonnegative raw strain-energy split densities (not
    signed strain, and not g(d)*psi_plus). They and f accept scalars or (M,).
    f must be in [0,1]. w1,cw,l0 are positive scalars; AT1 has cw=8/3.
    Assembly uses only these arrays and does not recompute displacement fields.
    """
    xy = np.asarray(xy, dtype=np.float64)
    conn = np.asarray(conn)
    if xy.ndim != 2 or xy.shape[1] != 2 or len(xy) < 3 or not np.isfinite(xy).all():
        raise ValueError("xy must be finite with shape (N,2), N>=3")
    gp = sparse_gp_matrix(conn, len(xy))
    conn = conn.astype(np.int64, copy=True)
    m, n = len(conn), len(xy)
    if np.any(np.diff(np.sort(conn, axis=1), axis=1) == 0):
        raise ValueError("a triangle must have three distinct nodes")
    if len(np.unique(conn)) != n:
        raise ValueError("every declared node must belong to the T3 support")
    area = _vector(area, m, "area")
    if np.any(area <= 0):
        raise ValueError("area must be positive")
    pp = _vector(psi_plus, m, "psi_plus", scalar=True)
    pm = _vector(psi_minus, m, "psi_minus", scalar=True)
    fatigue = _vector(f, m, "f", scalar=True)
    if np.any(pp < 0) or np.any(pm < 0):
        raise ValueError("psi_plus and psi_minus must be nonnegative split energies")
    if np.any(fatigue < 0) or np.any(fatigue > 1):
        raise ValueError("f must lie in [0,1]")
    w1, cw, l0 = (_positive(v, k) for v, k in [(w1, "w1"), (cw, "cw"), (l0, "l0")])
    verts = xy[conn]
    edge1, edge2 = verts[:, 1] - verts[:, 0], verts[:, 2] - verts[:, 0]
    det = edge1[:, 0] * edge2[:, 1] - edge1[:, 1] * edge2[:, 0]
    if np.any(det == 0) or not np.isfinite(det).all():
        raise ValueError("degenerate or nonfinite triangle geometry")
    # Exactly the historical 2*area denominator, including clockwise ordering.
    # Gradient sign flips for clockwise elements; its squared norm is invariant.
    bx = np.column_stack([verts[:, 1, 1] - verts[:, 2, 1],
                          verts[:, 2, 1] - verts[:, 0, 1],
                          verts[:, 0, 1] - verts[:, 1, 1]]) / (2 * area[:, None])
    by = np.column_stack([verts[:, 2, 0] - verts[:, 1, 0],
                          verts[:, 0, 0] - verts[:, 2, 0],
                          verts[:, 1, 0] - verts[:, 0, 0]]) / (2 * area[:, None])
    B = np.stack([bx, by], axis=1)
    coeff = fatigue * (w1 / cw)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        local_H = 2 * area[:, None, None] * (
            pp[:, None, None] * np.ones((3, 3)) / 9
            + (coeff * np.float64(l0)**2)[:, None, None] * np.einsum("eai,eaj->eij", B, B))
        local_q = np.repeat((area * (-2 * pp + coeff) / 3)[:, None], 3, axis=1)
        const = float(np.sum(area * (pp + pm)))
    if not (np.isfinite(local_H).all() and np.isfinite(local_q).all() and math.isfinite(const)):
        raise ValueError("nonfinite energy assembly; input scales unsupported")
    rows = np.repeat(conn, 3, axis=1).reshape(-1)
    cols = np.tile(conn, (1, 3)).reshape(-1)
    H = sparse.coo_matrix((local_H.reshape(-1), (rows, cols)), shape=(n, n)).tocsc()
    H.sum_duplicates()
    q = np.bincount(conn.reshape(-1), weights=local_q.reshape(-1), minlength=n)
    centroid = sparse.csr_matrix((np.full(3 * m, 1 / 3),
        (np.repeat(np.arange(m), 3), conn.reshape(-1))), shape=(m, n))
    if not np.isfinite(H.data).all() or not np.isfinite(q).all():
        raise ValueError("nonfinite global energy assembly")
    return T3DamageQP(H, q, const, centroid, gp, B)


def assembled_energy(qp, d):
    d = _vector(d, qp.n_nodes, "d")
    value = float(.5 * d @ (qp.H @ d) + qp.q @ d + qp.const)
    if not math.isfinite(value):
        raise ValueError("nonfinite assembled energy")
    return value


def assembled_gradient(qp, d):
    d = _vector(d, qp.n_nodes, "d")
    value = qp.H @ d + qp.q
    if not np.isfinite(value).all():
        raise ValueError("nonfinite assembled gradient")
    return value


def compare_physics_at_field(qp, d, physical_energy, physical_gradient):
    """Compare a caller's native-precision physical energy/gradient with the QP.

    The caller evaluates E_el+E_d and its nodal damage gradient using the
    frozen historical compute_energy at exactly d, fixed u/f and the same
    mesh. Exclude E_hist, neural regularization, and log transforms. This
    helper does no field/model forward, conversion, or precision promotion
    of the caller's physics. It is suitable for the initial real field check;
    a failed comparison must prevent calling this QP a qualified reference.
    """
    native_energy = float(physical_energy)
    native_gradient = _vector(physical_gradient, qp.n_nodes, "physical_gradient")
    if not math.isfinite(native_energy):
        raise ValueError("physical_energy must be finite")
    energy = assembled_energy(qp, d)
    gradient = assembled_gradient(qp, d)
    absolute = abs(energy - native_energy)
    # At exactly zero energy only exact agreement counts as relative agreement.
    relative = absolute / abs(native_energy) if native_energy else (0. if absolute == 0 else math.inf)
    gradient_error = float(np.max(np.abs(gradient - native_gradient), initial=0))
    reasons = []
    if relative > PHYSICS_ENERGY_RTOL:
        reasons.append("physical energy relative error")
    if gradient_error > PHYSICS_GRADIENT_ATOL:
        reasons.append("physical gradient maximum absolute error")
    return dict(accepted=not reasons, failure_reasons=reasons,
        qp_energy=energy, native_physical_energy=native_energy,
        energy_absolute_error=absolute, energy_relative_error=relative,
        gradient_max_absolute_error=gradient_error,
        energy_relative_tolerance=PHYSICS_ENERGY_RTOL,
        gradient_absolute_tolerance=PHYSICS_GRADIENT_ATOL)


def damage_constraints(qp, h, mode):
    """N: h<=d<=1. G: 0<=d<=1 and GP@(h-d)<=0.

    Reject a physically inadmissible nodal history for BOTH supports, even if
    averaging could hide an overshoot in G. No clipping or history repair.
    """
    h = _vector(h, qp.n_nodes, "h")
    if np.any(h < 0) or np.any(h > 1):
        raise ValueError("history h outside [0,1]; no clipping/repair is permitted")
    identity = sparse.eye(qp.n_nodes, format="csc")
    if mode == "N":
        return LinearConstraints(identity, h, np.ones(qp.n_nodes), mode)
    if mode == "G":
        A = sparse.vstack([identity, qp.gp], format="csc")
        return LinearConstraints(A, np.concatenate([np.zeros(qp.n_nodes), qp.gp @ h]),
            np.concatenate([np.ones(qp.n_nodes), np.full(qp.gp.shape[0], np.inf)]), mode)
    raise ValueError("mode must be 'G' or 'N'")


def kkt_certificate(qp, constraints, x, y):
    """Independently evaluate all linear-inequality KKT residuals, absolute 1e-7.

    OSQP's signed dual is y=lambda_upper-lambda_lower. Equal bounds allow
    either sign. Missing-side multipliers must be zero. Stationarity is in
    original unscaled physical-field coordinates. The PSD construction makes
    exact KKT sufficient for this conditional convex QP; finite tolerances
    give only the declared numerical certificate, not physical validation.
    """
    if x is None or y is None:
        return {"accepted": False, "tolerance": CERTIFICATE_TOL,
                "failure_reasons": ["missing primal or dual solution"]}
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.shape != (qp.n_nodes,) or y.shape != constraints.lower.shape:
        raise ValueError("primal/dual certificate shape mismatch")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        return {"accepted": False, "tolerance": CERTIFICATE_TOL,
                "failure_reasons": ["nonfinite primal or dual solution"]}
    A, lower, upper = constraints.A, constraints.lower, constraints.upper
    ax = A @ x
    has_lower, has_upper = np.isfinite(lower), np.isfinite(upper)
    lam_lower, lam_upper = np.maximum(-y, 0), np.maximum(y, 0)
    low_gap = ax[has_lower] - lower[has_lower]
    up_gap = upper[has_upper] - ax[has_upper]
    primal = max(0., float(np.max(-low_gap, initial=0)), float(np.max(-up_gap, initial=0)))
    dual = max(float(np.max(lam_lower[~has_lower], initial=0)),
               float(np.max(lam_upper[~has_upper], initial=0)))
    products = np.concatenate([lam_lower[has_lower] * low_gap,
                               lam_upper[has_upper] * up_gap])
    station = qp.H @ x + qp.q + A.T @ y
    if not (np.isfinite(ax).all() and np.isfinite(products).all() and np.isfinite(station).all()):
        return {"accepted": False, "tolerance": CERTIFICATE_TOL,
                "failure_reasons": ["nonfinite certificate arithmetic"]}
    residuals = dict(primal_linf=primal, dual_linf=dual,
        stationarity_linf=float(np.max(np.abs(station), initial=0)),
        complementarity_linf=float(np.max(np.abs(products), initial=0)))
    reasons = [name for name, value in residuals.items() if value > CERTIFICATE_TOL]
    return dict(accepted=not reasons, tolerance=CERTIFICATE_TOL, mode=constraints.mode,
        failure_reasons=reasons, **residuals,
        complementarity_l1=float(np.sum(np.abs(products))),
        physical_energy=assembled_energy(qp, x),
        dual_convention="y=lambda_upper-lambda_lower; lower/upper multipliers=max(-/+y,0)",
        scope="conditional centroid-T3 physical QP; no neural L2 or coupled equilibrium")


def solve_t3_damage(qp, h, mode="N", *, time_limit=MAX_TIME_SECONDS):
    """One OSQP attempt, no retry/fallback/clip; accept only solved + full KKT.

    time_limit (0,100] is a solve-call budget including setup/certification in
    the recorded wall time. OSQP enforces its internal remaining runtime cap;
    any overrun from setup/final certification invalidates acceptance. The
    caller still owns an external producer deadline for hard process control.
    """
    started = time.monotonic()
    time_limit = _positive(time_limit, "time_limit")
    if time_limit > MAX_TIME_SECONDS:
        raise ValueError("reference time_limit must not exceed 100 seconds")
    constraints = damage_constraints(qp, h, mode)
    try:
        import osqp
    except ImportError as exc:
        raise MissingOSQPError("OSQP dependency is missing; reference not computed, no fallback") from exc
    remaining = time_limit - (time.monotonic() - started)
    if remaining <= 0:
        return ReferenceResult(None, None, False, "budget_before_setup", {
            "accepted": False, "failure_reasons": ["time budget exhausted before setup"]},
            time.monotonic() - started, 0, osqp.__version__)
    solver = osqp.OSQP()
    solver.setup(P=sparse.triu(qp.H, format="csc"), q=qp.q,
        A=constraints.A, l=constraints.lower, u=constraints.upper,
        eps_abs=1e-9, eps_rel=1e-9, max_iter=200000,
        eps_prim_inf=1e-9, eps_dual_inf=1e-9,
        scaled_termination=False, check_termination=25,
        adaptive_rho=True, adaptive_rho_interval=50,
        polishing=False, warm_starting=True, verbose=False, time_limit=remaining)
    remaining = time_limit - (time.monotonic() - started)
    if remaining <= 0:
        return ReferenceResult(None, None, False, "budget_after_setup", {
            "accepted": False, "failure_reasons": ["time budget exhausted during setup"]},
            time.monotonic() - started, 0, osqp.__version__)
    solver.update_settings(time_limit=remaining)
    solver.warm_start(x=_vector(h, qp.n_nodes, "h"), y=np.zeros(constraints.A.shape[0]))
    result = solver.solve()
    cert = kkt_certificate(qp, constraints, result.x, result.y)
    status = str(result.info.status)
    reasons = list(cert["failure_reasons"])
    if status.lower() != "solved":
        reasons.append("OSQP status is not solved")
    elapsed = time.monotonic() - started
    if elapsed > time_limit:
        reasons.append("reference wall-time budget exceeded")
    cert = dict(cert, accepted=not reasons, failure_reasons=reasons,
                solver_status=status, elapsed_seconds=elapsed)
    return ReferenceResult(result.x, result.y, not reasons, status, cert, elapsed,
                           int(result.info.iter), osqp.__version__)
