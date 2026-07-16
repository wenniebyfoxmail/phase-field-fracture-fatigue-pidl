from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from damage_state_inversion import (  # noqa: E402
    amplify_damage,
    feasible_reaction_brackets,
    log_midpoint,
    merge_irreversible_damage,
    parse_load_displacement_cycles,
    relative_reaction_error,
)
from damage_conditioned_equilibrium import build_q4_kinematics  # noqa: E402
from run_reaction_conditioned_damage_inversion_gate import (  # noqa: E402
    calibrate_geometry,
    solve_damage,
)
from run_historical_damage_assimilation_gate import (  # noqa: E402
    DAMAGE_INPUT_TOLERANCE,
    FIXED_BETA_GRID,
    PRIOR_CYCLE,
    absolute_p99_support,
    clip_damage_with_tolerance,
    gate_pass,
)


def test_parse_load_displacement_cycles_checks_repeated_step_blocks(
    tmp_path: Path,
) -> None:
    path = tmp_path / "load.out"
    path.write_text(
        "step u_x F_x u_y F_y\n"
        "1 0 0 0.05 2.0\n"
        "2 0 0 0.10 4.0\n"
        "1 0 0 0.05 1.5\n"
        "2 0 0 0.10 3.0\n",
        encoding="utf-8",
    )
    cycles = parse_load_displacement_cycles(path, steps_per_cycle=2)
    assert [cycle.cycle for cycle in cycles] == [1, 2]
    np.testing.assert_array_equal(cycles[1].step, [1, 2])
    np.testing.assert_allclose(cycles[1].uy, [0.05, 0.10])
    np.testing.assert_allclose(cycles[1].fy, [1.5, 3.0])


def test_amplify_damage_preserves_zero_one_and_geometry() -> None:
    base = np.array([0.0, 0.25, 0.5, 1.0])
    np.testing.assert_allclose(amplify_damage(base, 1.0), base)
    stronger = amplify_damage(base, 2.0)
    np.testing.assert_allclose(stronger, [0.0, 0.4375, 0.75, 1.0])
    assert np.all(stronger[base > 0.0] >= base[base > 0.0])
    np.testing.assert_array_equal(stronger > 0.0, base > 0.0)


def test_merge_irreversible_damage_takes_pointwise_max_after_amplification() -> None:
    prior = np.array([0.8, 0.1, 0.0, 1.0])
    profile = np.array([0.2, 0.5, 0.75, 0.0])
    merged = merge_irreversible_damage(prior, profile, beta=2.0)
    np.testing.assert_allclose(merged, [0.8, 0.75, 0.9375, 1.0])
    assert np.all(merged >= prior)


def test_merge_irreversible_damage_is_pure_and_beta_one_is_exact_merge() -> None:
    prior = np.array([[0.1, 0.7], [0.4, 0.0]])
    profile = np.array([[0.5, 0.2], [0.4, 1.0]])
    prior_before = prior.copy()
    profile_before = profile.copy()
    merged = merge_irreversible_damage(prior, profile, beta=1.0)
    np.testing.assert_allclose(merged, np.maximum(prior, profile))
    np.testing.assert_array_equal(prior, prior_before)
    np.testing.assert_array_equal(profile, profile_before)
    assert not np.shares_memory(merged, prior)
    assert not np.shares_memory(merged, profile)


def test_merge_irreversible_damage_rejects_invalid_fields() -> None:
    with np.testing.assert_raises_regex(ValueError, "matching shapes"):
        merge_irreversible_damage(np.zeros(2), np.zeros(3), 1.0)
    with np.testing.assert_raises_regex(ValueError, "prior damage"):
        merge_irreversible_damage(np.array([0.0, np.nan]), np.zeros(2), 1.0)
    with np.testing.assert_raises_regex(ValueError, "base damage"):
        merge_irreversible_damage(np.zeros(2), np.array([0.0, 1.1]), 1.0)
    with np.testing.assert_raises_regex(ValueError, "beta"):
        merge_irreversible_damage(np.zeros(2), np.zeros(2), 0.0)


def test_historical_gate_locks_c84_and_probe_bracket_in_fixed_grid() -> None:
    assert PRIOR_CYCLE == 84
    assert np.any(np.isclose(FIXED_BETA_GRID, 2.0))
    assert np.any(np.isclose(FIXED_BETA_GRID, 2.5))
    assert np.all(np.diff(FIXED_BETA_GRID) > 0.0)


def test_historical_gate_clips_only_small_fem_damage_undershoot() -> None:
    raw = np.array([-7.86e-5, 0.25, 1.0 + 0.5 * DAMAGE_INPUT_TOLERANCE])
    clipped = clip_damage_with_tolerance(raw, label="synthetic FEM")
    np.testing.assert_allclose(clipped, [0.0, 0.25, 1.0])

    with np.testing.assert_raises_regex(ValueError, "outside the allowed"):
        clip_damage_with_tolerance(
            np.array([-1.01 * DAMAGE_INPUT_TOLERANCE, 0.5]),
            label="invalid FEM",
        )


def test_absolute_p99_support_and_locked_gate_are_target_thresholded() -> None:
    target = np.array([0.0, 1.0, 2.0, 3.0])
    areas = np.ones(4)
    iou, ratio, threshold = absolute_p99_support(target, target, areas)
    assert threshold == 3.0
    assert iou == 1.0
    assert ratio == 1.0
    assert gate_pass(0.30, 0.90, 0.70, 0.50)
    assert not gate_pass(0.30001, 0.90, 0.70, 0.50)


def test_reaction_brackets_do_not_cross_a_failed_candidate() -> None:
    beta = np.array([1.0, 2.0, 3.0, 4.0])
    reaction = np.array([4.0, 2.0, np.nan, 0.25])
    feasible = np.array([True, True, False, True])
    assert feasible_reaction_brackets(beta, reaction, 1.0, feasible) == []
    reaction[2] = 0.5
    feasible[2] = True
    assert feasible_reaction_brackets(beta, reaction, 1.0, feasible) == [(2.0, 3.0)]


def test_relative_error_and_log_midpoint() -> None:
    assert np.isclose(relative_reaction_error(9.8, 10.0), 0.02)
    assert np.isclose(log_midpoint(2.0, 8.0), 4.0)


def test_log_bisection_recovers_a_known_reaction_amplitude() -> None:
    points = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    cells = np.array([[0, 1, 2, 3]], dtype=np.int32)
    kinematics = build_q4_kinematics(points, cells)
    base = np.full(len(points), 0.5)
    args = SimpleNamespace(
        peak_displacement=0.1,
        youngs_modulus=1.0,
        poisson_ratio=0.3,
        residual_stiffness=0.0,
        max_equilibrium_iterations=25,
        equilibrium_tolerance=1.0e-9,
        equilibrium_residual_tolerance=1.0e-8,
        minimum_pivot_ratio=1.0e-14,
        bisection_iterations=20,
        reaction_relative_tolerance=0.02,
        maximum_final_bracket_factor=1.25,
    )
    target_damage = amplify_damage(base, 2.5)
    _, observed, _, _ = solve_damage(kinematics, target_damage, 0.1, args)
    status, rows = calibrate_geometry(
        "synthetic",
        base,
        observed,
        np.array([1.0, 2.0, 3.0, 4.0]),
        kinematics,
        args,
    )
    assert status["identifiable"]
    assert abs(float(status["beta"]) - 2.5) < 0.01
    assert float(status["relative_reaction_error"]) < 0.002
    assert len(rows) > 4
