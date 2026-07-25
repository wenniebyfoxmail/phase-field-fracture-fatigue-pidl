"""Reference Q4 AT1 history-fatigue residual used by GRIPHFiTH.

The implementation mirrors ``pf_at1_history_fatigue.f90`` and is intended for
cross-discretisation diagnostics.  It is not a replacement FEM solver.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AT1FatigueParameters:
    gc: float
    length_scale: float
    alpha_t: float
    fatigue_power: float = 2.0
    residual_stiffness: float = 0.0
    recovery_penalty: float = 0.0
    thickness: float = 1.0


def q4_gauss_rule() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return Q4 shape values, parent derivatives, and weights at 2x2 points."""
    a = 1.0 / np.sqrt(3.0)
    points = ((-a, -a), (a, -a), (a, a), (-a, a))
    shape = []
    deriv = []
    for xi, eta in points:
        shape.append(
            0.25
            * np.asarray(
                [
                    (1.0 - xi) * (1.0 - eta),
                    (1.0 + xi) * (1.0 - eta),
                    (1.0 + xi) * (1.0 + eta),
                    (1.0 - xi) * (1.0 + eta),
                ]
            )
        )
        deriv.append(
            0.25
            * np.asarray(
                [
                    [-(1.0 - eta), 1.0 - eta, 1.0 + eta, -(1.0 + eta)],
                    [-(1.0 - xi), -(1.0 + xi), 1.0 + xi, 1.0 - xi],
                ]
            )
        )
    return np.asarray(shape), np.asarray(deriv), np.ones(4, dtype=np.float64)


def _validate(
    points: np.ndarray,
    cells: np.ndarray,
    pfield: np.ndarray,
    strain_energy_raw: np.ndarray,
    history_old: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    points = np.asarray(points, dtype=np.float64)
    cells = np.asarray(cells, dtype=np.int64)
    pfield = np.asarray(pfield, dtype=np.float64).reshape(-1)
    strain_energy_raw = np.asarray(strain_energy_raw, dtype=np.float64)
    history_old = np.asarray(history_old, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("points must have shape (n_node, 2)")
    if cells.ndim != 2 or cells.shape[1] != 4:
        raise ValueError("cells must have shape (n_elem, 4)")
    if cells.size and (cells.min() < 0 or cells.max() >= len(points)):
        raise ValueError("cells contain out-of-range node indices")
    if pfield.shape != (len(points),):
        raise ValueError("pfield length must equal n_node")
    if strain_energy_raw.shape != (len(cells), 4):
        raise ValueError("strain_energy_raw must have shape (n_elem, 4)")
    if history_old.shape != (len(cells), 4, 4):
        raise ValueError("history_old must have shape (n_elem, 4, 4)")
    for name, value in (
        ("points", points),
        ("pfield", pfield),
        ("strain_energy_raw", strain_energy_raw),
        ("history_old", history_old),
    ):
        if not np.all(np.isfinite(value)):
            raise ValueError(f"{name} contains non-finite values")
    return points, cells, pfield, strain_energy_raw, history_old


def assemble_at1_history_fatigue_residual(
    points: np.ndarray,
    cells: np.ndarray,
    pfield: np.ndarray,
    strain_energy_raw: np.ndarray,
    history_old: np.ndarray,
    parameters: AT1FatigueParameters,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Assemble nodal phase residual and updated four-channel Gauss history.

    Returns ``residual, history_new, element_residual, fatigue_degradation``.
    Connectivity is zero-based.  The history channels follow GRIPHFiTH:
    maximum raw energy, accumulated fatigue, previous degraded energy, and
    fatigue degradation.
    """
    points, cells, pfield, raw, old = _validate(
        points, cells, pfield, strain_energy_raw, history_old
    )
    if parameters.gc <= 0.0 or parameters.length_scale <= 0.0:
        raise ValueError("gc and length_scale must be positive")
    if parameters.alpha_t <= 0.0 or parameters.fatigue_power <= 0.0:
        raise ValueError("alpha_t and fatigue_power must be positive")

    shape, parent_deriv, weights = q4_gauss_rule()
    residual = np.zeros(len(points), dtype=np.float64)
    element_residual = np.zeros((len(cells), 4), dtype=np.float64)
    history_new = old.copy()
    fatigue = np.zeros((len(cells), 4), dtype=np.float64)

    for element, nodes in enumerate(cells):
        coords = points[nodes]
        damage = pfield[nodes]
        stiffness = np.zeros((4, 4), dtype=np.float64)
        rhs = np.zeros(4, dtype=np.float64)
        for gp in range(4):
            jacobian = parent_deriv[gp] @ coords
            det_j = float(np.linalg.det(jacobian))
            if not np.isfinite(det_j) or det_j <= 0.0:
                raise ValueError(f"element {element} has non-positive Jacobian")
            grad = np.linalg.solve(jacobian, parent_deriv[gp])
            n = shape[gp]
            damage_gp = float(n @ damage)
            history = max(float(old[element, gp, 0]), float(raw[element, gp]))
            degraded = (
                (1.0 - damage_gp) ** 2 + parameters.residual_stiffness
            ) * raw[element, gp]
            increment = max(degraded - old[element, gp, 2], 0.0)
            accumulated = old[element, gp, 1] + increment
            ratio = (accumulated - parameters.alpha_t) / (
                accumulated + parameters.alpha_t
            )
            fat = min(1.0, (1.0 - ratio) ** parameters.fatigue_power)
            recovery = parameters.recovery_penalty if damage_gp < 0.0 else 0.0

            history_new[element, gp] = (history, accumulated, degraded, fat)
            fatigue[element, gp] = fat
            factor = parameters.thickness * weights[gp] * det_j
            nn = np.outer(n, n)
            btb = grad.T @ grad
            stiffness += factor * (
                (2.0 * history + recovery) * nn
                + 0.75 * fat * parameters.gc * parameters.length_scale * btb
            )
            rhs += factor * (
                2.0 * history
                - 0.375 * fat * parameters.gc / parameters.length_scale
            ) * n
        local = stiffness @ damage - rhs
        element_residual[element] = local
        np.add.at(residual, nodes, local)

    if not np.all(np.isfinite(residual)):
        raise RuntimeError("assembled phase residual contains non-finite values")
    return residual, history_new, element_residual, fatigue


def residual_summary(residual: np.ndarray, free_nodes: np.ndarray | None = None) -> dict[str, float]:
    """Return scale-transparent residual norms on all or declared free nodes."""
    values = np.asarray(residual, dtype=np.float64).reshape(-1)
    if free_nodes is not None:
        values = values[np.asarray(free_nodes, dtype=np.int64).reshape(-1)]
    if not len(values):
        raise ValueError("residual selection is empty")
    return {
        "n": int(len(values)),
        "l2": float(np.linalg.norm(values)),
        "rms": float(np.sqrt(np.mean(values**2))),
        "linf": float(np.max(np.abs(values))),
    }


def assemble_at1_phase_residual_given_state(
    points: np.ndarray,
    cells: np.ndarray,
    pfield: np.ndarray,
    history_gp: np.ndarray,
    fatigue_gp: np.ndarray,
    parameters: AT1FatigueParameters,
) -> tuple[np.ndarray, np.ndarray]:
    """Assemble the static FEM phase residual for explicitly frozen H and f.

    This form is useful for cross-residual decomposition because it can hold
    the FEM history/degradation fixed while replacing only the candidate damage
    field, or replace H with the PIDL current raw driver without silently
    performing another fatigue-history update.
    """
    points = np.asarray(points, dtype=np.float64)
    cells = np.asarray(cells, dtype=np.int64)
    pfield = np.asarray(pfield, dtype=np.float64).reshape(-1)
    history_gp = np.asarray(history_gp, dtype=np.float64)
    fatigue_gp = np.asarray(fatigue_gp, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("points must have shape (n_node, 2)")
    if cells.ndim != 2 or cells.shape[1] != 4:
        raise ValueError("cells must have shape (n_elem, 4)")
    if pfield.shape != (len(points),):
        raise ValueError("pfield length must equal n_node")
    if history_gp.shape != (len(cells), 4) or fatigue_gp.shape != (len(cells), 4):
        raise ValueError("history_gp and fatigue_gp must have shape (n_elem, 4)")
    if cells.size and (cells.min() < 0 or cells.max() >= len(points)):
        raise ValueError("cells contain out-of-range node indices")
    if not all(np.all(np.isfinite(value)) for value in (points, pfield, history_gp, fatigue_gp)):
        raise ValueError("cross-residual inputs contain non-finite values")

    shape, parent_deriv, weights = q4_gauss_rule()
    residual = np.zeros(len(points), dtype=np.float64)
    element_residual = np.zeros((len(cells), 4), dtype=np.float64)
    for element, nodes in enumerate(cells):
        coords = points[nodes]
        damage = pfield[nodes]
        stiffness = np.zeros((4, 4), dtype=np.float64)
        rhs = np.zeros(4, dtype=np.float64)
        for gp in range(4):
            jacobian = parent_deriv[gp] @ coords
            det_j = float(np.linalg.det(jacobian))
            if not np.isfinite(det_j) or det_j <= 0.0:
                raise ValueError(f"element {element} has non-positive Jacobian")
            grad = np.linalg.solve(jacobian, parent_deriv[gp])
            n = shape[gp]
            damage_gp = float(n @ damage)
            recovery = parameters.recovery_penalty if damage_gp < 0.0 else 0.0
            h = history_gp[element, gp]
            fat = fatigue_gp[element, gp]
            factor = parameters.thickness * weights[gp] * det_j
            stiffness += factor * (
                (2.0 * h + recovery) * np.outer(n, n)
                + 0.75 * fat * parameters.gc * parameters.length_scale * (grad.T @ grad)
            )
            rhs += factor * (
                2.0 * h - 0.375 * fat * parameters.gc / parameters.length_scale
            ) * n
        local = stiffness @ damage - rhs
        element_residual[element] = local
        np.add.at(residual, nodes, local)
    return residual, element_residual
