"""Damage-conditioned Q4 equilibrium projection for the FEM AMOR split.

This module mirrors the displacement-side kernel in GRIPHFiTH's
``mod_equilibrium_amor``.  It is intentionally a deterministic mechanics layer,
not a learned correction.  Given nodal damage and the declared displacement
boundary conditions, it solves equilibrium and returns the undegraded tensile
energy at the four Gauss points of each quad.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import splu


@dataclass(frozen=True)
class Q4Kinematics:
    points: np.ndarray
    cells: np.ndarray
    shape_values: np.ndarray
    b_matrices: np.ndarray
    det_jacobians: np.ndarray
    element_dofs: np.ndarray
    assembly_rows: np.ndarray
    assembly_cols: np.ndarray


@dataclass(frozen=True)
class EquilibriumResult:
    displacement: np.ndarray
    tensile_energy_gauss: np.ndarray
    tensile_energy_element: np.ndarray
    converged: bool
    iterations: int
    relative_update: float
    sign_changes: int
    negative_trace_fraction: float
    residual_norm: float
    normalized_residual: float
    minimum_pivot_ratio: float


def plane_strain_tensors(youngs_modulus: float, poisson_ratio: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """Return C, volumetric/deviatoric projectors, bulk modulus and shear modulus."""
    shear = youngs_modulus / (2.0 * (1.0 + poisson_ratio))
    bulk = youngs_modulus / (3.0 * (1.0 - 2.0 * poisson_ratio))
    i_vol = np.array(
        [[1.0, 1.0, 0.0], [1.0, 1.0, 0.0], [0.0, 0.0, 0.0]], dtype=np.float64
    )
    i_dev = np.array(
        [
            [2.0 / 3.0, -1.0 / 3.0, 0.0],
            [-1.0 / 3.0, 2.0 / 3.0, 0.0],
            [0.0, 0.0, 0.5],
        ],
        dtype=np.float64,
    )
    elasticity = bulk * i_vol + 2.0 * shear * i_dev
    return elasticity, i_vol, i_dev, bulk, shear


def build_q4_kinematics(points: np.ndarray, cells: np.ndarray) -> Q4Kinematics:
    """Precompute Q4 shape functions, B matrices and sparse assembly indices."""
    points = np.asarray(points, dtype=np.float64)
    cells = np.asarray(cells, dtype=np.int32)
    if points.ndim != 2 or points.shape[1] < 2:
        raise ValueError("points must have shape [node, >=2]")
    if cells.ndim != 2 or cells.shape[1] != 4:
        raise ValueError("cells must be four-node quads")
    if cells.min() < 0 or cells.max() >= len(points):
        raise ValueError("cell connectivity references an invalid node")

    gauss = 1.0 / np.sqrt(3.0)
    locations = np.array(
        [[-gauss, -gauss], [gauss, -gauss], [gauss, gauss], [-gauss, gauss]],
        dtype=np.float64,
    )
    shape_values = np.empty((4, 4), dtype=np.float64)
    b_matrices = np.empty((len(cells), 4, 3, 8), dtype=np.float64)
    det_jacobians = np.empty((len(cells), 4), dtype=np.float64)
    element_coordinates = points[cells, :2]

    for gp, (xi, eta) in enumerate(locations):
        shape_values[gp] = 0.25 * np.array(
            [
                (1.0 - xi) * (1.0 - eta),
                (1.0 + xi) * (1.0 - eta),
                (1.0 + xi) * (1.0 + eta),
                (1.0 - xi) * (1.0 + eta),
            ]
        )
        derivatives = 0.25 * np.array(
            [
                [-(1.0 - eta), 1.0 - eta, 1.0 + eta, -(1.0 + eta)],
                [-(1.0 - xi), -(1.0 + xi), 1.0 + xi, 1.0 - xi],
            ],
            dtype=np.float64,
        )
        jacobian = np.einsum("ij,ejk->eik", derivatives, element_coordinates)
        determinant = np.linalg.det(jacobian)
        if np.any(determinant <= 0.0):
            bad = np.flatnonzero(determinant <= 0.0)[:5]
            raise ValueError(f"non-positive Q4 Jacobian at elements {bad.tolist()}")
        inverse = np.linalg.inv(jacobian)
        global_derivatives = np.einsum("eij,jk->eik", inverse, derivatives)
        b = np.zeros((len(cells), 3, 8), dtype=np.float64)
        b[:, 0, 0::2] = global_derivatives[:, 0, :]
        b[:, 1, 1::2] = global_derivatives[:, 1, :]
        b[:, 2, 0::2] = global_derivatives[:, 1, :]
        b[:, 2, 1::2] = global_derivatives[:, 0, :]
        b_matrices[:, gp] = b
        det_jacobians[:, gp] = determinant

    element_dofs = np.empty((len(cells), 8), dtype=np.int32)
    element_dofs[:, 0::2] = 2 * cells
    element_dofs[:, 1::2] = 2 * cells + 1
    assembly_rows = np.repeat(element_dofs, 8, axis=1).reshape(-1)
    assembly_cols = np.tile(element_dofs, (1, 8)).reshape(-1)
    return Q4Kinematics(
        points=points[:, :2],
        cells=cells,
        shape_values=shape_values,
        b_matrices=b_matrices,
        det_jacobians=det_jacobians,
        element_dofs=element_dofs,
        assembly_rows=assembly_rows,
        assembly_cols=assembly_cols,
    )


def sens_displacement_boundary_conditions(
    points: np.ndarray,
    peak_displacement: float,
    tolerance: float = 1.0e-10,
) -> tuple[np.ndarray, np.ndarray]:
    """Return the reverse-BC constraints used by the formal SENS FEM baseline.

    The matched baseline fixes horizontal displacement on both the top and
    bottom edges, fixes vertical displacement on the bottom edge, and
    prescribes vertical displacement on the top edge.
    """
    points = np.asarray(points, dtype=np.float64)
    ymin = float(points[:, 1].min())
    ymax = float(points[:, 1].max())
    bottom = np.flatnonzero(np.isclose(points[:, 1], ymin, atol=tolerance, rtol=0.0))
    top = np.flatnonzero(np.isclose(points[:, 1], ymax, atol=tolerance, rtol=0.0))
    if not len(bottom) or not len(top):
        raise ValueError("could not identify top and bottom boundary nodes")
    dofs = np.concatenate((2 * bottom, 2 * top, 2 * bottom + 1, 2 * top + 1))
    values = np.concatenate(
        (
            np.zeros(len(bottom) + len(top) + len(bottom), dtype=np.float64),
            np.full(len(top), peak_displacement, dtype=np.float64),
        )
    )
    order = np.argsort(dofs)
    dofs = dofs[order]
    values = values[order]
    if len(np.unique(dofs)) != len(dofs):
        raise ValueError("duplicate prescribed displacement dofs")
    return dofs.astype(np.int32), values


def element_to_nodal_damage(
    element_damage: np.ndarray,
    cells: np.ndarray,
    element_weights: np.ndarray | None = None,
) -> np.ndarray:
    """Project element damage to nodes with optional element-area weighting."""
    element_damage = np.asarray(element_damage, dtype=np.float64).reshape(-1)
    cells = np.asarray(cells, dtype=np.int64)
    if len(element_damage) != len(cells):
        raise ValueError("element damage and connectivity lengths differ")
    weights = np.ones(len(cells), dtype=np.float64) if element_weights is None else np.asarray(element_weights, dtype=np.float64)
    if weights.shape != (len(cells),) or np.any(weights <= 0.0):
        raise ValueError("element weights must be positive and match the elements")
    node_count = int(cells.max()) + 1
    numerator = np.zeros(node_count, dtype=np.float64)
    denominator = np.zeros(node_count, dtype=np.float64)
    for local in range(4):
        np.add.at(numerator, cells[:, local], weights * element_damage)
        np.add.at(denominator, cells[:, local], weights)
    if np.any(denominator == 0.0):
        raise ValueError("projection left unused nodes")
    return np.clip(numerator / denominator, 0.0, 1.0)


def _element_state(displacement: np.ndarray, kinematics: Q4Kinematics) -> np.ndarray:
    return displacement[kinematics.element_dofs]


def _trace_signs(displacement: np.ndarray, kinematics: Q4Kinematics) -> np.ndarray:
    element_displacement = _element_state(displacement, kinematics)
    strains = np.einsum("egij,ej->egi", kinematics.b_matrices, element_displacement)
    return strains[:, :, 0] + strains[:, :, 1] >= 0.0


def assemble_amor_stiffness(
    kinematics: Q4Kinematics,
    nodal_damage: np.ndarray,
    displacement: np.ndarray,
    *,
    youngs_modulus: float = 1.0,
    poisson_ratio: float = 0.3,
    residual_stiffness: float = 0.0,
    thickness: float = 1.0,
) -> sparse.csr_matrix:
    """Assemble the tangent stiffness used by the GRIPHFiTH AMOR kernel."""
    nodal_damage = np.clip(np.asarray(nodal_damage, dtype=np.float64).reshape(-1), 0.0, 1.0)
    if len(nodal_damage) != len(kinematics.points):
        raise ValueError("nodal damage length does not match the mesh")
    if residual_stiffness < 0.0:
        raise ValueError("residual stiffness must be non-negative")
    elasticity, i_vol, i_dev, bulk, shear = plane_strain_tensors(youngs_modulus, poisson_ratio)
    signs = _trace_signs(displacement, kinematics)
    element_damage = nodal_damage[kinematics.cells]
    element_stiffness = np.zeros((len(kinematics.cells), 8, 8), dtype=np.float64)
    for gp in range(4):
        b = kinematics.b_matrices[:, gp]
        damage_gp = np.einsum(
            "ei,i->e", element_damage, kinematics.shape_values[gp], optimize=False
        )
        degradation = (1.0 - damage_gp) ** 2 + residual_stiffness
        positive = signs[:, gp]
        constitutive = np.empty((len(b), 3, 3), dtype=np.float64)
        constitutive[positive] = degradation[positive, None, None] * elasticity
        constitutive[~positive] = (
            bulk * i_vol[None, :, :]
            + degradation[~positive, None, None] * (2.0 * shear * i_dev)[None, :, :]
        )
        cb = np.einsum("eab,ebj->eaj", constitutive, b)
        contribution = np.einsum("eai,eaj->eij", b, cb)
        contribution *= (thickness * kinematics.det_jacobians[:, gp])[:, None, None]
        element_stiffness += contribution
    size = 2 * len(kinematics.points)
    matrix = sparse.coo_matrix(
        (element_stiffness.reshape(-1), (kinematics.assembly_rows, kinematics.assembly_cols)),
        shape=(size, size),
    )
    return matrix.tocsr()


def tensile_energy(
    kinematics: Q4Kinematics,
    displacement: np.ndarray,
    *,
    youngs_modulus: float = 1.0,
    poisson_ratio: float = 0.3,
) -> tuple[np.ndarray, np.ndarray]:
    """Return undegraded AMOR tensile energy at Gauss points and per element."""
    elasticity, _, i_dev, _, shear = plane_strain_tensors(youngs_modulus, poisson_ratio)
    element_displacement = _element_state(displacement, kinematics)
    strains = np.einsum("egij,ej->egi", kinematics.b_matrices, element_displacement)
    positive = strains[:, :, 0] + strains[:, :, 1] >= 0.0
    energy = np.empty((len(kinematics.cells), 4), dtype=np.float64)
    deviatoric = 2.0 * shear * i_dev
    for gp in range(4):
        strain = strains[:, gp]
        constitutive = np.empty((len(strain), 3, 3), dtype=np.float64)
        constitutive[positive[:, gp]] = elasticity
        constitutive[~positive[:, gp]] = deviatoric
        stress_plus = np.einsum("eij,ej->ei", constitutive, strain)
        energy[:, gp] = 0.5 * np.einsum("ei,ei->e", strain, stress_plus)
    return energy, energy.mean(axis=1)


def equilibrium_internal_force(
    kinematics: Q4Kinematics,
    nodal_damage: np.ndarray,
    displacement: np.ndarray,
    *,
    youngs_modulus: float = 1.0,
    poisson_ratio: float = 0.3,
    residual_stiffness: float = 0.0,
    thickness: float = 1.0,
) -> np.ndarray:
    """Return the converged nodal internal-force vector ``K(d, u) u``."""
    displacement = np.asarray(displacement, dtype=np.float64).reshape(-1)
    if displacement.shape != (2 * len(kinematics.points),):
        raise ValueError("displacement length does not match the mesh")
    matrix = assemble_amor_stiffness(
        kinematics,
        nodal_damage,
        displacement,
        youngs_modulus=youngs_modulus,
        poisson_ratio=poisson_ratio,
        residual_stiffness=residual_stiffness,
        thickness=thickness,
    )
    force = np.asarray(matrix @ displacement).reshape(-1)
    if not np.all(np.isfinite(force)):
        raise RuntimeError("equilibrium internal force contains non-finite values")
    return force


def solve_amor_equilibrium(
    kinematics: Q4Kinematics,
    nodal_damage: np.ndarray,
    prescribed_dofs: np.ndarray,
    prescribed_values: np.ndarray,
    *,
    youngs_modulus: float = 1.0,
    poisson_ratio: float = 0.3,
    residual_stiffness: float = 0.0,
    thickness: float = 1.0,
    max_iterations: int = 25,
    tolerance: float = 1.0e-9,
    residual_tolerance: float = 1.0e-8,
    minimum_pivot_ratio: float = 1.0e-14,
) -> EquilibriumResult:
    """Solve the piecewise-linear AMOR equilibrium problem by active-set updates.

    A finite displacement vector is not sufficient for acceptance.  The trace
    active set must stabilize, the free-DOF equilibrium residual must pass a
    relative gate, and each sparse factorization must retain a finite pivot
    ratio above ``minimum_pivot_ratio``.
    """
    prescribed_dofs = np.asarray(prescribed_dofs, dtype=np.int32).reshape(-1)
    prescribed_values = np.asarray(prescribed_values, dtype=np.float64).reshape(-1)
    if prescribed_dofs.shape != prescribed_values.shape:
        raise ValueError("prescribed dofs and values must have matching shapes")
    if len(np.unique(prescribed_dofs)) != len(prescribed_dofs):
        raise ValueError("prescribed dofs must be unique")
    if max_iterations < 1:
        raise ValueError("max_iterations must be positive")
    if tolerance <= 0.0 or residual_tolerance <= 0.0:
        raise ValueError("equilibrium tolerances must be positive")
    if minimum_pivot_ratio <= 0.0:
        raise ValueError("minimum_pivot_ratio must be positive")
    size = 2 * len(kinematics.points)
    if np.any(prescribed_dofs < 0) or np.any(prescribed_dofs >= size):
        raise ValueError("prescribed dof outside displacement vector")
    free_mask = np.ones(size, dtype=bool)
    free_mask[prescribed_dofs] = False
    free = np.flatnonzero(free_mask)

    displacement = np.zeros(size, dtype=np.float64)
    displacement[prescribed_dofs] = prescribed_values
    ymin = float(kinematics.points[:, 1].min())
    ymax = float(kinematics.points[:, 1].max())
    span = max(ymax - ymin, np.finfo(float).eps)
    peak = float(np.max(np.abs(prescribed_values)))
    displacement[1::2] = peak * (kinematics.points[:, 1] - ymin) / span
    displacement[prescribed_dofs] = prescribed_values

    relative_update = np.inf
    sign_changes = -1
    smallest_pivot_ratio = 1.0
    converged = False
    matrix: sparse.csr_matrix | None = None
    for iteration in range(1, max_iterations + 1):
        previous = displacement.copy()
        matrix = assemble_amor_stiffness(
            kinematics,
            nodal_damage,
            displacement,
            youngs_modulus=youngs_modulus,
            poisson_ratio=poisson_ratio,
            residual_stiffness=residual_stiffness,
            thickness=thickness,
        )
        if not np.all(np.isfinite(matrix.data)):
            raise RuntimeError("equilibrium stiffness contains non-finite entries")
        if len(free):
            free_matrix = matrix[free][:, free].tocsc()
            rhs = -matrix[free][:, prescribed_dofs] @ prescribed_values
            try:
                factor = splu(free_matrix)
            except RuntimeError as error:
                raise RuntimeError("equilibrium stiffness is singular") from error
            pivots = np.abs(factor.U.diagonal())
            pivot_ratio = float(pivots.min() / max(float(pivots.max()), np.finfo(float).eps))
            if not np.isfinite(pivot_ratio) or pivot_ratio < minimum_pivot_ratio:
                raise RuntimeError(
                    "equilibrium stiffness is numerically near-singular: "
                    f"pivot ratio {pivot_ratio:.3e}"
                )
            smallest_pivot_ratio = min(smallest_pivot_ratio, pivot_ratio)
            solution = factor.solve(np.asarray(rhs).reshape(-1))
            if not np.all(np.isfinite(solution)):
                raise RuntimeError("equilibrium solve returned non-finite displacements")
            displacement[free] = solution
        displacement[prescribed_dofs] = prescribed_values
        denominator = max(float(np.linalg.norm(displacement)), np.finfo(float).eps)
        relative_update = float(np.linalg.norm(displacement - previous) / denominator)
        old_sign = _trace_signs(previous, kinematics)
        new_sign = _trace_signs(displacement, kinematics)
        sign_changes = int(np.count_nonzero(old_sign != new_sign))
        if relative_update <= tolerance and sign_changes == 0:
            converged = True
            break
    if not converged:
        raise RuntimeError(
            "AMOR active set did not converge: "
            f"iterations={max_iterations}, relative_update={relative_update:.3e}, "
            f"sign_changes={sign_changes}"
        )

    matrix = assemble_amor_stiffness(
        kinematics,
        nodal_damage,
        displacement,
        youngs_modulus=youngs_modulus,
        poisson_ratio=poisson_ratio,
        residual_stiffness=residual_stiffness,
        thickness=thickness,
    )
    if not np.all(np.isfinite(matrix.data)):
        raise RuntimeError("final equilibrium stiffness contains non-finite entries")
    residual = matrix @ displacement
    residual_norm = float(np.linalg.norm(residual[free])) if len(free) else 0.0
    if len(free):
        internal_free = matrix[free][:, free] @ displacement[free]
        prescribed_free = matrix[free][:, prescribed_dofs] @ prescribed_values
        residual_scale = max(
            float(np.linalg.norm(internal_free) + np.linalg.norm(prescribed_free)),
            np.finfo(float).eps,
        )
        normalized_residual = residual_norm / residual_scale
    else:
        normalized_residual = 0.0
    if not np.isfinite(normalized_residual) or normalized_residual > residual_tolerance:
        raise RuntimeError(
            "equilibrium free residual failed: "
            f"normalized={normalized_residual:.3e}, tolerance={residual_tolerance:.3e}"
        )
    energy_gp, energy_element = tensile_energy(
        kinematics,
        displacement,
        youngs_modulus=youngs_modulus,
        poisson_ratio=poisson_ratio,
    )
    negative_fraction = float(np.mean(~_trace_signs(displacement, kinematics)))
    return EquilibriumResult(
        displacement=displacement,
        tensile_energy_gauss=energy_gp,
        tensile_energy_element=energy_element,
        converged=converged,
        iterations=iteration,
        relative_update=relative_update,
        sign_changes=sign_changes,
        negative_trace_fraction=negative_fraction,
        residual_norm=residual_norm,
        normalized_residual=normalized_residual,
        minimum_pivot_ratio=smallest_pivot_ratio,
    )
