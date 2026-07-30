from __future__ import annotations

from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from analyze_factorial_loco_results import (  # noqa: E402
    PRIMARY,
    TASKS,
    _active_log10,
    model_task_summary,
    paired,
)


def summary_rows() -> list[dict]:
    rows = []
    for heldout in ("a", "b", "c", "d"):
        for seed in (1, 2, 3):
            for family in ("markov", "tcn", "transformer"):
                for task in TASKS:
                    item = {
                        "heldout_trajectory_id": heldout,
                        "family": family,
                        "seed": seed,
                        "task": task,
                        "damage_mae": 0.1,
                        "history_log10_mae": 0.2,
                        "log10_psi_raw_mae": 0.3,
                        "own_p99_iou": 0.5,
                        "support_area_ratio": 1.0,
                    }
                    for metric, direction in PRIMARY:
                        base = 0.5
                        if family == "tcn":
                            base += -0.1 if direction == "lower" else 0.1
                        item[metric] = base
                    rows.append(item)
    return rows


def test_model_task_summary_uses_twelve_fold_seed_units() -> None:
    rows = model_task_summary(summary_rows())
    assert len(rows) == 9
    assert all(row["independent_fold_seed_units"] == 12 for row in rows)


def test_paired_intervals_reward_only_consistent_favorable_change() -> None:
    rows = paired(summary_rows())
    tcn = [row for row in rows if row["family"] == "tcn"]
    transformer = [row for row in rows if row["family"] == "transformer"]
    assert all(row["ci_excludes_zero_favorably"] for row in tcn)
    assert not any(row["ci_excludes_zero_favorably"] for row in transformer)


def test_active_field_is_derived_from_damage_and_raw_driver() -> None:
    state = np.asarray([[0.0, 0.0, 0.0, 2.0], [0.9, 0.0, 0.0, 2.0]])
    np.testing.assert_allclose(_active_log10(state), [2.0, 0.0], atol=1.0e-12)
