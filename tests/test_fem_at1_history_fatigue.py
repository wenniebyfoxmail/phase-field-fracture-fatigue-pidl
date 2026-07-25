import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "source"))

from fem_at1_history_fatigue import (
    AT1FatigueParameters,
    assemble_at1_history_fatigue_residual,
    assemble_at1_phase_residual_given_state,
    q4_gauss_rule,
    residual_summary,
)


def unit_square():
    points = np.asarray([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    return points, np.asarray([[0, 1, 2, 3]])


def test_q4_partition_of_unity_and_derivatives():
    shape, deriv, weights = q4_gauss_rule()
    np.testing.assert_allclose(shape.sum(axis=1), 1.0)
    np.testing.assert_allclose(deriv.sum(axis=2), 0.0, atol=1.0e-15)
    np.testing.assert_allclose(weights, 1.0)


def test_zero_driver_has_at1_nucleation_residual():
    points, cells = unit_square()
    params = AT1FatigueParameters(gc=2.0, length_scale=0.5, alpha_t=1.0)
    residual, history, element, fatigue = assemble_at1_history_fatigue_residual(
        points,
        cells,
        np.zeros(4),
        np.zeros((1, 4)),
        np.zeros((1, 4, 4)),
        params,
    )
    # Integral N_i dOmega = 1/4 on a unit square.
    expected = 0.375 * params.gc / params.length_scale * 0.25
    np.testing.assert_allclose(residual, expected)
    np.testing.assert_allclose(element[0], expected)
    np.testing.assert_allclose(history[:, :, :3], 0.0)
    np.testing.assert_allclose(history[:, :, 3], 1.0)
    np.testing.assert_allclose(fatigue, 1.0)


def test_history_update_matches_fortran_semantics():
    points, cells = unit_square()
    old = np.zeros((1, 4, 4))
    old[:, :, 0] = 0.2
    old[:, :, 1] = 0.1
    old[:, :, 2] = 0.05
    raw = np.full((1, 4), 0.3)
    params = AT1FatigueParameters(gc=1.0, length_scale=0.1, alpha_t=0.5)
    _, new, _, _ = assemble_at1_history_fatigue_residual(
        points, cells, np.full(4, 0.25), raw, old, params
    )
    np.testing.assert_allclose(new[:, :, 0], 0.3)
    degraded = 0.75**2 * 0.3
    np.testing.assert_allclose(new[:, :, 1], 0.1 + degraded - 0.05)
    np.testing.assert_allclose(new[:, :, 2], degraded)
    assert np.all((new[:, :, 3] > 0.0) & (new[:, :, 3] <= 1.0))


def test_rejects_missing_exact_mesh_geometry():
    points, cells = unit_square()
    cells[0, 3] = 10
    with pytest.raises(ValueError, match="out-of-range"):
        assemble_at1_history_fatigue_residual(
            points,
            cells,
            np.zeros(4),
            np.zeros((1, 4)),
            np.zeros((1, 4, 4)),
            AT1FatigueParameters(gc=1.0, length_scale=0.1, alpha_t=0.5),
        )


def test_residual_summary_supports_free_node_subset():
    assert residual_summary(np.asarray([1.0, -2.0, 4.0]), [0, 1]) == {
        "n": 2,
        "l2": pytest.approx(np.sqrt(5.0)),
        "rms": pytest.approx(np.sqrt(2.5)),
        "linf": 2.0,
    }


def test_frozen_state_residual_matches_full_assembly_state():
    points, cells = unit_square()
    pfield = np.full(4, 0.2)
    raw = np.full((1, 4), 0.3)
    old = np.zeros((1, 4, 4))
    params = AT1FatigueParameters(gc=1.0, length_scale=0.1, alpha_t=0.5)
    full, new, _, _ = assemble_at1_history_fatigue_residual(
        points, cells, pfield, raw, old, params
    )
    frozen, _ = assemble_at1_phase_residual_given_state(
        points, cells, pfield, new[:, :, 0], new[:, :, 3], params
    )
    np.testing.assert_allclose(frozen, full)
