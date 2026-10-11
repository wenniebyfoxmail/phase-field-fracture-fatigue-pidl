from __future__ import annotations

from pathlib import Path
import sys

import numpy as np


MODULE_DIR = Path(__file__).parents[1] / "tools" / "s04_e011_analysis"
sys.path.insert(0, str(MODULE_DIR))
import run_multicycle_fixed_damage_equilibrium as MODULE  # noqa: E402


def test_q4_and_paired_t3_geometry_integrate_unit_square() -> None:
    points = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    q4 = MODULE.build_q4(points, np.array([[0, 1, 2, 3]]))
    t3 = MODULE.build_t3(points, np.array([[0, 1, 2], [0, 2, 3]]))
    assert np.isclose(q4.weights.sum(), 1.0)
    assert np.isclose(t3.weights.sum(), 1.0)
    assert np.allclose(q4.shape.sum(axis=1), 1.0)
    assert np.allclose(t3.shape.sum(axis=1), 1.0)


def test_affine_strain_patch_is_topology_invariant() -> None:
    points = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    q4 = MODULE.build_q4(points, np.array([[0, 1, 2, 3]]))
    t3 = MODULE.build_t3(points, np.array([[0, 1, 2], [0, 2, 3]]))
    # u=2x+3y, v=-x+4y gives [eps_xx, eps_yy, gamma_xy]=[2,4,2].
    u = np.empty(2 * len(points))
    u[0::2] = 2 * points[:, 0] + 3 * points[:, 1]
    u[1::2] = -points[:, 0] + 4 * points[:, 1]
    expected = np.array([2.0, 4.0, 2.0])
    for kin in (q4, t3):
        strain = np.einsum("egij,ej->egi", kin.b, u[kin.dofs])
        assert np.allclose(strain, expected)
