from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


SENS = Path(__file__).parents[1] / "SENS_tensile"
sys.path.insert(0, str(SENS))
import analyze_raw_driver_mechanisms as module  # noqa: E402


def test_interpolate_field_exact_and_linear() -> None:
    tau = np.array([0.0, 0.5, 1.0])
    fields = np.array([[0.0, 2.0], [2.0, 4.0], [4.0, 8.0]])
    assert np.allclose(module.interpolate_field(tau, fields, 0.5), [2.0, 4.0])
    assert np.allclose(module.interpolate_field(tau, fields, 0.25), [1.0, 3.0])


def synthetic_cases():
    tau = np.array([0.0, 1.0])
    return {
        "a": {"tau": tau, "spec": {"umax": 0.1}, "residuals": {"raw_log10": np.array([[1., 2.], [3., 4.]])}},
        "b": {"tau": tau, "spec": {"umax": 0.2}, "residuals": {"raw_log10": np.array([[3., 4.], [5., 6.]])}},
    }


def test_progress_mean_uses_equal_weight_training_fields() -> None:
    cases = synthetic_cases()
    assert np.allclose(module.progress_mean(cases, ["a", "b"], 0.5), [3.0, 4.0])


def test_affine_umax_progress_mean_interpolates_and_extrapolates() -> None:
    cases = synthetic_cases()
    assert np.allclose(module.affine_umax_progress_mean(cases, ["a", "b"], 0.5, 0.15), [3.0, 4.0])
    assert np.allclose(module.affine_umax_progress_mean(cases, ["a", "b"], 0.5, 0.3), [6.0, 7.0])


def test_phase_bins_are_nonoverlapping() -> None:
    assert module.phase_bin(20, 83, 0.23) == "c1_c20"
    assert module.phase_bin(21, 83, 0.24) == "c21_c40"
    assert module.phase_bin(50, 83, 0.60) == "middle_after_c40"
    assert module.phase_bin(80, 83, 0.96) == "late_pre_event"
    assert module.phase_bin(83, 83, 1.0) == "event"


def test_training_support_arm_zeros_cells_outside_each_own_p99_support() -> None:
    cases = synthetic_cases()
    for case, active in zip(cases.values(), (
        np.array([[1., 2., 3., 4.], [4., 3., 2., 1.]]),
        np.array([[2., 3., 4., 5.], [5., 4., 3., 2.]]),
    )):
        case["residuals"]["raw_log10"] = np.pad(
            case["residuals"]["raw_log10"], ((0, 0), (0, 2)), constant_values=7.0
        )
        case["fem_fields"] = {"active": active}
    matrices = module.build_training_matrices(cases, ["a", "b"], np.ones(4))
    support = matrices["M2_support_pod"]
    assert np.count_nonzero(support[0]) == 1
    assert np.count_nonzero(support[1]) == 1
    assert support[0, 3] == 7.0
    assert support[1, 0] == 3.0


def test_decision_priority_is_identified_failure_then_unidentified() -> None:
    passing = {"arm": module.PRIMARY_ARM, "rank": 20, "identified": True,
               "pass_upper97p5_lt_0p90": True}
    failing = {**passing, "pass_upper97p5_lt_0p90": False}
    unknown = {**passing, "identified": False, "pass_upper97p5_lt_0p90": False}
    primary, verdict = module.decide([
        {**passing, "heldout": "a"}, {**failing, "heldout": "b"}, {**unknown, "heldout": "c"}
    ])
    assert len(primary) == 3
    assert verdict == "negative"
    _, verdict = module.decide([
        {**passing, "heldout": "a"}, {**passing, "heldout": "b"}, {**unknown, "heldout": "c"}
    ])
    assert verdict == "inconclusive"


def test_evaluate_summarize_decide_keeps_identified_fail_over_zero_baseline_ratio() -> None:
    rng = np.random.default_rng(41)
    cycles = np.arange(1, 22)
    tau = (cycles - 1) / (len(cycles) - 1)
    cells = 2001
    areas = np.ones(cells)
    cases = {}
    for index, (tid, umax) in enumerate((("a", 0.11), ("b", 0.12), ("c", 0.13))):
        cases[tid] = {
            "tau": tau,
            "cycles": cycles,
            "spec": {"umax": umax, "event_cycle": int(cycles[-1])},
            "residuals": {
                "raw_log10": rng.normal(index, 1.0, size=(len(cycles), cells)).astype(np.float32)
            },
            "fem_fields": {
                "active": rng.random(size=(len(cycles), cells)).astype(np.float32)
            },
        }
    per_cycle, _ = module.evaluate(cases, areas)
    for row in per_cycle:
        if row["arm"] == module.PRIMARY_ARM and row["rank"] == 20:
            row["error_ratio"] = 1.1 if row["heldout"] == "b" else 0.5
            if row["heldout"] == "c" and row["cycle"] == 1:
                row["error_ratio"] = float("nan")
    summary, _ = module.summarize(per_cycle)
    primary, verdict = module.decide(summary)
    assert len(primary) == 3
    assert verdict == "negative"
