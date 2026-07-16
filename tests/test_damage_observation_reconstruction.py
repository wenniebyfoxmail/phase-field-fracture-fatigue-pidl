from __future__ import annotations

from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from damage_observation_reconstruction import (
    at1_from_binary_core_points,
    at1_from_binary_straight_extent,
    at1_from_binned_centerline,
    at1_from_core_points,
    at1_from_line_segment,
    at1_from_raster_skeleton,
    at1_from_straight_visible_extent,
    at1_profile,
    binary_core_damage,
    notch_connected_core,
)
from run_damage_observation_equilibrium_gate import (
    build_observation_assimilated_state,
    candidate_damage_fields,
)


def line_grid() -> tuple[np.ndarray, np.ndarray]:
    points = np.array([[x, y] for y in (-0.02, -0.01, 0.0, 0.01, 0.02) for x in (-1.0, 0.0, 1.0)])
    damage = np.zeros(len(points))
    damage[np.isclose(points[:, 1], 0.0)] = 1.0
    return points, damage


def test_at1_profile_has_compact_support_and_squared_hat() -> None:
    distance = np.array([0.0, 0.01, 0.02, 0.03])
    np.testing.assert_allclose(at1_profile(distance, 0.01), [1.0, 0.25, 0.0, 0.0])


def test_binary_core_uses_only_threshold_membership() -> None:
    _, damage = line_grid()
    reconstructed = binary_core_damage(damage, 0.95)
    np.testing.assert_array_equal(reconstructed, damage)


def test_core_point_reconstruction_matches_line_distance_profile() -> None:
    points, damage = line_grid()
    reconstructed = at1_from_core_points(
        points, damage, threshold=0.95, length_scale=0.01
    )
    np.testing.assert_allclose(reconstructed, at1_profile(np.abs(points[:, 1]), 0.01))


def test_centerline_and_straight_extent_match_a_straight_crack() -> None:
    points, damage = line_grid()
    expected = at1_profile(np.abs(points[:, 1]), 0.01)
    centerline = at1_from_binned_centerline(
        points,
        damage,
        threshold=0.95,
        length_scale=0.01,
        bins=2,
        samples=200,
    )
    straight = at1_from_straight_visible_extent(
        points, damage, threshold=0.95, length_scale=0.01
    )
    np.testing.assert_allclose(centerline, expected, atol=1.0e-12)
    np.testing.assert_allclose(straight, expected, atol=1.0e-12)


def test_missing_core_is_rejected() -> None:
    points, _ = line_grid()
    try:
        at1_from_core_points(
            points, np.zeros(len(points)), threshold=0.95, length_scale=0.01
        )
    except ValueError as error:
        assert "no crack-core" in str(error)
    else:
        raise AssertionError("empty crack observation should be rejected")


def test_notch_connected_core_drops_detached_damage_component() -> None:
    points = np.array(
        [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [2.0, 0.0], [2.0, 1.0]]
    )
    cells = np.array([[0, 1, 2, 3], [1, 4, 5, 2]], dtype=np.int32)
    damage = np.array([1.0, 1.0, 0.0, 0.0, 0.0, 1.0])
    core = notch_connected_core(points, cells, damage, threshold=0.95)
    np.testing.assert_array_equal(core, [True, True, False, False, False, False])


def test_raster_skeleton_at1_uses_binary_geometry_only() -> None:
    points, damage = line_grid()
    core = damage.astype(bool)
    reconstructed, skeleton = at1_from_raster_skeleton(
        points,
        core,
        length_scale=0.01,
        resolution=0.01,
    )
    assert len(skeleton) > 0
    assert reconstructed.shape == damage.shape
    assert reconstructed.max() == 1.0
    assert np.all((reconstructed >= 0.0) & (reconstructed <= 1.0))


def test_binary_core_reconstructions_do_not_require_diffuse_damage() -> None:
    points, damage = line_grid()
    core = damage.astype(bool)
    expected = at1_profile(np.abs(points[:, 1]), 0.01)
    point_profile = at1_from_binary_core_points(
        points,
        core,
        length_scale=0.01,
    )
    straight_profile = at1_from_binary_straight_extent(
        points,
        core,
        length_scale=0.01,
    )
    np.testing.assert_allclose(point_profile, expected)
    np.testing.assert_allclose(straight_profile, expected)


def test_line_segment_is_a_valid_initial_notch_control() -> None:
    points, _ = line_grid()
    reconstructed = at1_from_line_segment(
        points,
        xmin=-1.0,
        xmax=0.0,
        y_center=0.0,
        length_scale=0.01,
    )
    expected_distance = np.sqrt(
        (points[:, 0] - np.clip(points[:, 0], -1.0, 0.0)) ** 2
        + points[:, 1] ** 2
    )
    np.testing.assert_allclose(reconstructed, at1_profile(expected_distance, 0.01))


def test_shifted_skeleton_changes_reconstructed_geometry() -> None:
    points, damage = line_grid()
    core = damage.astype(bool)
    aligned, _ = at1_from_raster_skeleton(
        points,
        core,
        length_scale=0.01,
        resolution=0.01,
    )
    shifted, shifted_skeleton = at1_from_raster_skeleton(
        points,
        core,
        length_scale=0.01,
        resolution=0.01,
        vertical_shift=0.02,
    )
    assert np.max(np.abs(aligned - shifted)) > 0.5
    assert np.isclose(np.median(shifted_skeleton[:, 1]), 0.02, atol=0.01)


def test_assimilated_state_replaces_damage_and_raw_but_retains_history() -> None:
    source = np.array(
        [
            [0.8, 12.0, 0.7, -3.0],
            [0.9, 15.0, 0.6, -4.0],
        ]
    )
    damage = np.array([0.2, 0.4])
    raw = np.array([1.0e-2, 1.0e-5])
    assimilated = build_observation_assimilated_state(source, damage, raw, 1.0e-12)
    np.testing.assert_allclose(assimilated[:, 0], damage)
    np.testing.assert_allclose(assimilated[:, 1:3], source[:, 1:3])
    np.testing.assert_allclose(assimilated[:, 3], [-2.0, -5.0])


def test_primary_skeleton_is_invariant_to_diffuse_oracle_values() -> None:
    points, damage = line_grid()
    core = damage.astype(bool)
    altered_oracle = damage.copy()
    altered_oracle[~core] = np.linspace(0.0, 0.94, np.count_nonzero(~core))
    original, _ = candidate_damage_fields(
        points,
        damage,
        core,
        core,
        length_scale=0.01,
        observation_resolution=0.01,
        negative_control_shift=0.02,
    )
    altered, _ = candidate_damage_fields(
        points,
        altered_oracle,
        core,
        core,
        length_scale=0.01,
        observation_resolution=0.01,
        negative_control_shift=0.02,
    )
    np.testing.assert_array_equal(
        original["core95_skeleton_at1"],
        altered["core95_skeleton_at1"],
    )
    assert not np.array_equal(
        original["full_damage_oracle"],
        altered["full_damage_oracle"],
    )
