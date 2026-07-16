from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from damage_state_inversion import (
    amplify_damage,
    feasible_reaction_brackets,
    log_midpoint,
    parse_load_displacement_cycles,
    relative_reaction_error,
)
from damage_conditioned_equilibrium import build_q4_kinematics
from run_reaction_conditioned_damage_inversion_gate import (
    calibrate_geometry,
    solve_damage,
)


def test_parse_load_displacement_cycles_checks_repeated_step_blocks(tmp_path: Path) -> None:
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
