from __future__ import annotations

from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from damage_conditioned_equilibrium import (
    build_q4_kinematics,
    element_to_nodal_damage,
    equilibrium_internal_force,
    plane_strain_tensors,
    sens_displacement_boundary_conditions,
    solve_amor_equilibrium,
)


def unit_quad() -> tuple[np.ndarray, np.ndarray]:
    points = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    cells = np.array([[0, 1, 2, 3]], dtype=np.int32)
    return points, cells


def two_by_two_quads() -> tuple[np.ndarray, np.ndarray]:
    points = np.array(
        [[x, y] for y in (0.0, 0.5, 1.0) for x in (0.0, 0.5, 1.0)],
        dtype=np.float64,
    )
    cells = np.array(
        [
            [0, 1, 4, 3],
            [1, 2, 5, 4],
            [3, 4, 7, 6],
            [4, 5, 8, 7],
        ],
        dtype=np.int32,
    )
    return points, cells


def test_sens_boundary_conditions_match_formal_reverse_bc() -> None:
    points, _ = unit_quad()
    dofs, values = sens_displacement_boundary_conditions(points, 0.1)
    np.testing.assert_array_equal(dofs, np.arange(8))
    np.testing.assert_allclose(values, np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0, 0.1]))


def test_q4_affine_vertical_extension_matches_plane_strain_energy() -> None:
    points, cells = unit_quad()
    kinematics = build_q4_kinematics(points, cells)
    dofs, values = sens_displacement_boundary_conditions(points, 0.1)
    result = solve_amor_equilibrium(kinematics, np.zeros(4), dofs, values)
    elasticity, _, _, _, _ = plane_strain_tensors(1.0, 0.3)
    expected = 0.5 * elasticity[1, 1] * 0.1**2
    np.testing.assert_allclose(result.tensile_energy_gauss, expected, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(result.tensile_energy_element, expected, rtol=1e-12, atol=1e-12)
    assert result.residual_norm == 0.0


def test_raw_tensile_energy_is_undegraded_under_fully_prescribed_affine_loading() -> None:
    points, cells = unit_quad()
    kinematics = build_q4_kinematics(points, cells)
    dofs, values = sens_displacement_boundary_conditions(points, 0.1)
    undamaged = solve_amor_equilibrium(kinematics, np.zeros(4), dofs, values)
    damaged = solve_amor_equilibrium(kinematics, np.full(4, 0.75), dofs, values)
    np.testing.assert_allclose(damaged.tensile_energy_gauss, undamaged.tensile_energy_gauss)


def test_top_reaction_tracks_degraded_global_stiffness() -> None:
    points, cells = unit_quad()
    kinematics = build_q4_kinematics(points, cells)
    dofs, values = sens_displacement_boundary_conditions(points, 0.1)
    undamaged = solve_amor_equilibrium(kinematics, np.zeros(4), dofs, values)
    damaged = solve_amor_equilibrium(kinematics, np.full(4, 0.75), dofs, values)
    force_undamaged = equilibrium_internal_force(
        kinematics,
        np.zeros(4),
        undamaged.displacement,
    )
    force_damaged = equilibrium_internal_force(
        kinematics,
        np.full(4, 0.75),
        damaged.displacement,
    )
    top_y = 2 * np.array([2, 3]) + 1
    bottom_y = 2 * np.array([0, 1]) + 1
    np.testing.assert_allclose(force_undamaged[top_y].sum(), -force_undamaged[bottom_y].sum())
    np.testing.assert_allclose(
        force_damaged[top_y].sum() / force_undamaged[top_y].sum(),
        (1.0 - 0.75) ** 2,
    )


def test_free_interior_equilibrium_converges_with_symmetric_lateral_contraction() -> None:
    points, cells = two_by_two_quads()
    kinematics = build_q4_kinematics(points, cells)
    dofs, values = sens_displacement_boundary_conditions(points, 0.1)
    result = solve_amor_equilibrium(kinematics, np.zeros(len(points)), dofs, values)
    displacement = result.displacement.reshape(-1, 2)
    assert result.converged
    assert result.active_set_stable
    assert result.normalized_residual <= 1.0e-10
    assert result.minimum_pivot_ratio > 1.0e-14
    np.testing.assert_allclose(displacement[4, 0], 0.0, atol=1.0e-13)
    np.testing.assert_allclose(displacement[3, 0], -displacement[5, 0], atol=1.0e-13)
    np.testing.assert_allclose(displacement[3:6, 1], 0.05, atol=1.0e-13)


def test_distorted_q4_reproduces_affine_tensile_energy() -> None:
    points = np.array([[0.0, 0.0], [1.2, 0.1], [1.0, 1.1], [-0.1, 0.9]])
    cells = np.array([[0, 1, 2, 3]], dtype=np.int32)
    kinematics = build_q4_kinematics(points, cells)
    strain = np.array([0.01, 0.02, 0.0])
    nodal_displacement = np.column_stack((strain[0] * points[:, 0], strain[1] * points[:, 1])).reshape(-1)
    dofs = np.arange(len(nodal_displacement), dtype=np.int32)
    result = solve_amor_equilibrium(
        kinematics,
        np.zeros(len(points)),
        dofs,
        nodal_displacement,
    )
    elasticity, _, _, _, _ = plane_strain_tensors(1.0, 0.3)
    expected = 0.5 * strain @ elasticity @ strain
    np.testing.assert_allclose(result.tensile_energy_gauss, expected, rtol=1e-12, atol=1e-12)


def test_rejects_underconstrained_rigid_horizontal_mode() -> None:
    points, cells = unit_quad()
    kinematics = build_q4_kinematics(points, cells)
    vertical_dofs = np.array([1, 3, 5, 7], dtype=np.int32)
    vertical_values = np.array([0.0, 0.0, 0.1, 0.1])
    try:
        solve_amor_equilibrium(
            kinematics,
            np.zeros(len(points)),
            vertical_dofs,
            vertical_values,
        )
    except RuntimeError as error:
        assert "singular" in str(error)
    else:
        raise AssertionError("underconstrained horizontal rigid mode should be rejected")


def test_element_to_nodal_damage_is_weighted_and_bounded() -> None:
    cells = np.array([[0, 1, 4, 3], [1, 2, 5, 4]], dtype=np.int32)
    projected = element_to_nodal_damage(
        np.array([0.0, 1.0]), cells, element_weights=np.array([1.0, 3.0])
    )
    np.testing.assert_allclose(projected[[0, 3]], 0.0)
    np.testing.assert_allclose(projected[[2, 5]], 1.0)
    np.testing.assert_allclose(projected[[1, 4]], 0.75)
    assert np.all((projected >= 0.0) & (projected <= 1.0))


def test_rejects_clockwise_quad() -> None:
    points, _ = unit_quad()
    clockwise = np.array([[0, 3, 2, 1]], dtype=np.int32)
    try:
        build_q4_kinematics(points, clockwise)
    except ValueError as error:
        assert "Jacobian" in str(error)
    else:
        raise AssertionError("clockwise cell should be rejected")
