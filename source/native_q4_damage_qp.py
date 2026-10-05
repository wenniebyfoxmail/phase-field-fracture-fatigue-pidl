"""Sparse native-Q4 AT1 damage quadratic program.

The problem is a convex QP only while displacement, undegraded tensile
energy and fatigue degradation are frozen.  Trial fatigue is deliberately an
outer fixed-point state and must never be differentiated or refreshed inside
``assemble_at1_damage_qp``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse

from damage_conditioned_equilibrium import Q4Kinematics


@dataclass(frozen=True)
class DamageQP:
    hessian: sparse.csc_matrix
    linear: np.ndarray
    constraint: sparse.csc_matrix
    lower: np.ndarray
    upper: np.ndarray
    gp_constraint: sparse.csr_matrix
    gp_lower: np.ndarray
    constant: float


@dataclass(frozen=True)
class QPCertificate:
    stationarity_inf: float
    stationarity_scaled: float
    primal_inf: float
    dual_sign_inf: float
    complementarity_inf: float
    rho_damage: float


def gauss_interpolation_matrix(kinematics: Q4Kinematics) -> sparse.csr_matrix:
    """Return ``A`` such that ``A @ d`` is element-major Q4 GP damage."""
    n_elem = len(kinematics.cells)
    rows = np.repeat(np.arange(4 * n_elem, dtype=np.int64), 4)
    cols = np.repeat(kinematics.cells, 4, axis=0).reshape(-1)
    data = np.tile(kinematics.shape_values, (n_elem, 1)).reshape(-1)
    return sparse.coo_matrix(
        (data, (rows, cols)), shape=(4 * n_elem, len(kinematics.points))
    ).tocsr()


def _assemble_nodal_matrix(local: np.ndarray, cells: np.ndarray, n_nodes: int) -> sparse.csc_matrix:
    rows = np.repeat(cells, 4, axis=1).reshape(-1)
    cols = np.tile(cells, (1, 4)).reshape(-1)
    return sparse.coo_matrix(
        (local.reshape(-1), (rows, cols)), shape=(n_nodes, n_nodes)
    ).tocsc()


def assemble_at1_damage_qp(
    kinematics: Q4Kinematics,
    tensile_energy_gp: np.ndarray,
    fatigue_gp: np.ndarray,
    previous_damage_gp: np.ndarray,
    *,
    w1: float = 1.0,
    length_scale: float = 0.01,
    c_w: float = 8.0 / 3.0,
    thickness: float = 1.0,
) -> DamageQP:
    """Assemble the fixed-``u,f`` AT1 QP with hard GP irreversibility.

    The objective is the same native-Q4 energy used by the PIDL branch,
    excluding its soft irreversibility penalty because irreversibility is
    represented here by exact linear inequalities.
    """
    psi = np.asarray(tensile_energy_gp, dtype=np.float64)
    fatigue = np.asarray(fatigue_gp, dtype=np.float64)
    previous = np.asarray(previous_damage_gp, dtype=np.float64)
    expected = (len(kinematics.cells), 4)
    for name, value in (("tensile energy", psi), ("fatigue", fatigue),
                        ("previous GP damage", previous)):
        if value.shape != expected:
            raise ValueError(f"{name} must have shape {expected}, got {value.shape}")
        if not np.all(np.isfinite(value)):
            raise ValueError(f"{name} contains non-finite values")
    if np.any(psi < -1.0e-14):
        raise ValueError("tensile energy must be non-negative for the convex-QP contract")
    if np.any(fatigue < 0.0):
        raise ValueError("fatigue degradation must be non-negative")
    if w1 <= 0.0 or length_scale <= 0.0 or c_w <= 0.0 or thickness <= 0.0:
        raise ValueError("AT1 material and thickness coefficients must be positive")
    if np.any(previous < -1.0e-12) or np.any(previous > 1.0 + 1.0e-12):
        raise ValueError("previous GP damage is outside [0,1]")

    n_elem = len(kinematics.cells)
    n_nodes = len(kinematics.points)
    local_hessian = np.zeros((n_elem, 4, 4), dtype=np.float64)
    local_linear = np.zeros((n_elem, 4), dtype=np.float64)
    constant = 0.0
    fracture_coefficient = float(w1) / float(c_w)

    for gp in range(4):
        shape = kinematics.shape_values[gp]
        det = thickness * kinematics.det_jacobians[:, gp]
        gp_psi = np.maximum(psi[:, gp], 0.0)
        gp_fatigue = fatigue[:, gp]
        grad_x = kinematics.b_matrices[:, gp, 0, 0::2]
        grad_y = kinematics.b_matrices[:, gp, 1, 1::2]
        mass = np.einsum("i,j->ij", shape, shape)[None, :, :]
        gradient = (
            np.einsum("ei,ej->eij", grad_x, grad_x)
            + np.einsum("ei,ej->eij", grad_y, grad_y)
        )
        local_hessian += (
            (2.0 * det * gp_psi)[:, None, None] * mass
            + (2.0 * det * fracture_coefficient * length_scale**2 * gp_fatigue)
              [:, None, None] * gradient
        )
        local_linear += (
            det * (-2.0 * gp_psi + fracture_coefficient * gp_fatigue)
        )[:, None] * shape[None, :]
        constant += float(np.sum(det * gp_psi))

    hessian = _assemble_nodal_matrix(local_hessian, kinematics.cells, n_nodes)
    hessian = (0.5 * (hessian + hessian.T)).tocsc()
    linear = np.zeros(n_nodes, dtype=np.float64)
    for local in range(4):
        np.add.at(linear, kinematics.cells[:, local], local_linear[:, local])

    gp_constraint = gauss_interpolation_matrix(kinematics)
    identity = sparse.eye(n_nodes, format="csc")
    constraint = sparse.vstack((identity, gp_constraint), format="csc")
    lower = np.concatenate((np.zeros(n_nodes), previous.reshape(-1)))
    upper = np.concatenate((np.ones(n_nodes), np.full(4 * n_elem, np.inf)))
    return DamageQP(
        hessian=hessian,
        linear=linear,
        constraint=constraint,
        lower=lower,
        upper=upper,
        gp_constraint=gp_constraint,
        gp_lower=previous.reshape(-1),
        constant=constant,
    )


def validate_qp_contract(problem: DamageQP, witness: np.ndarray, tolerance: float = 1.0e-10) -> dict:
    """Check symmetry, PSD samples and feasibility before a producer solve."""
    witness = np.asarray(witness, dtype=np.float64).reshape(-1)
    n = problem.hessian.shape[0]
    if witness.shape != (n,):
        raise ValueError("QP witness has the wrong length")
    asymmetry = problem.hessian - problem.hessian.T
    symmetry_inf = 0.0 if asymmetry.nnz == 0 else float(np.max(np.abs(asymmetry.data)))
    values = problem.constraint @ witness
    lower_violation = float(np.max(np.maximum(problem.lower - values, 0.0)))
    finite_upper = np.isfinite(problem.upper)
    upper_violation = float(np.max(np.maximum(values[finite_upper] - problem.upper[finite_upper], 0.0)))
    rng = np.random.default_rng(20261005)
    minimum_rayleigh = np.inf
    for _ in range(8):
        direction = rng.standard_normal(n)
        direction /= max(float(np.linalg.norm(direction)), np.finfo(float).eps)
        minimum_rayleigh = min(minimum_rayleigh, float(direction @ (problem.hessian @ direction)))
    scale = max(float(np.max(np.abs(problem.hessian.data))), 1.0)
    report = {
        "symmetry_inf": symmetry_inf,
        "minimum_sampled_rayleigh": minimum_rayleigh,
        "witness_lower_violation": lower_violation,
        "witness_upper_violation": upper_violation,
        "feasible_witness": max(lower_violation, upper_violation) <= tolerance,
        "sampled_psd": minimum_rayleigh >= -tolerance * scale,
    }
    if symmetry_inf > tolerance * scale:
        raise RuntimeError(f"QP Hessian symmetry contract failed: {report}")
    if not report["sampled_psd"]:
        raise RuntimeError(f"QP sampled PSD contract failed: {report}")
    if not report["feasible_witness"]:
        raise RuntimeError(f"QP GP-irreversibility feasibility contract failed: {report}")
    return report


def osqp_certificate(problem: DamageQP, damage: np.ndarray, dual: np.ndarray) -> QPCertificate:
    """Return an independent KKT certificate for OSQP's ``l <= A x <= u`` form."""
    x = np.asarray(damage, dtype=np.float64).reshape(-1)
    y = np.asarray(dual, dtype=np.float64).reshape(-1)
    if x.shape != (problem.hessian.shape[0],) or y.shape != problem.lower.shape:
        raise ValueError("QP primal/dual certificate shapes do not match the problem")
    ax = np.asarray(problem.constraint @ x).reshape(-1)
    gradient = np.asarray(problem.hessian @ x + problem.linear).reshape(-1)
    dual_force = np.asarray(problem.constraint.T @ y).reshape(-1)
    stationarity = gradient + dual_force
    finite_upper = np.isfinite(problem.upper)
    primal = max(
        float(np.max(np.maximum(problem.lower - ax, 0.0))),
        float(np.max(np.maximum(ax[finite_upper] - problem.upper[finite_upper], 0.0))),
    )

    lower_slack = ax - problem.lower
    upper_slack = problem.upper - ax
    lower_multiplier = np.maximum(-y, 0.0)
    upper_multiplier = np.maximum(y, 0.0)
    upper_multiplier[~finite_upper] = 0.0
    complementarity = max(
        float(np.max(np.abs(lower_multiplier * lower_slack))),
        float(np.max(np.abs(upper_multiplier[finite_upper] * upper_slack[finite_upper]))),
    )
    active_tolerance = 1.0e-7
    inactive = (lower_slack > active_tolerance) & (
        (~finite_upper) | (upper_slack > active_tolerance)
    )
    dual_sign = float(np.max(np.abs(y[inactive]))) if np.any(inactive) else 0.0
    stationarity_inf = float(np.max(np.abs(stationarity)))
    scale = max(
        1.0,
        float(np.max(np.abs(problem.hessian @ x))),
        float(np.max(np.abs(problem.linear))),
        float(np.max(np.abs(dual_force))),
    )
    stationarity_scaled = stationarity_inf / scale
    rho = max(stationarity_scaled, primal, dual_sign, complementarity)
    return QPCertificate(
        stationarity_inf=stationarity_inf,
        stationarity_scaled=stationarity_scaled,
        primal_inf=primal,
        dual_sign_inf=dual_sign,
        complementarity_inf=complementarity,
        rho_damage=rho,
    )


def solve_with_osqp(
    problem: DamageQP,
    initial: np.ndarray,
    *,
    eps_abs: float = 1.0e-8,
    eps_rel: float = 1.0e-8,
    max_iter: int = 200_000,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Solve the QP and return primal, dual and library diagnostics."""
    try:
        import osqp
    except ImportError as exc:
        raise RuntimeError("OSQP is required for the direct native-Q4 damage solve") from exc
    solver = osqp.OSQP()
    solver.setup(
        P=problem.hessian,
        q=problem.linear,
        A=problem.constraint,
        l=problem.lower,
        u=problem.upper,
        eps_abs=eps_abs,
        eps_rel=eps_rel,
        max_iter=max_iter,
        polishing=True,
        adaptive_rho=True,
        verbose=False,
    )
    solver.warm_start(x=np.asarray(initial, dtype=np.float64))
    result = solver.solve(raise_error=False)
    if result.x is None or result.y is None:
        raise RuntimeError(f"OSQP returned no primal/dual solution: {result.info.status}")
    diagnostics = {
        "status": str(result.info.status),
        "status_val": int(result.info.status_val),
        "iterations": int(result.info.iter),
        "objective": float(result.info.obj_val),
        "primal_residual": float(result.info.prim_res),
        "dual_residual": float(result.info.dual_res),
        "run_time": float(result.info.run_time),
    }
    return np.asarray(result.x), np.asarray(result.y), diagnostics
