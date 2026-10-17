from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from freeze_select import (  # noqa: E402
    assemble_weak_system,
    build_candidate_library,
    stability_validated_select,
    validate_frozen_snapshots,
)
from freeze_select.library import FIXED_PHYSICS_NAMES  # noqa: E402
from run_freeze_select_synthetic import TRUE_BETA, manufactured_snapshots  # noqa: E402
from run_freeze_select_from_snapshot import run as run_from_snapshot  # noqa: E402


def test_schema_preserves_claim_boundary() -> None:
    frame = manufactured_snapshots(seed=3, noise_fraction=0.0)
    report = validate_frozen_snapshots(frame, claim_class="tooling-only")
    assert report.trajectory_count == 5
    with np.testing.assert_raises_regex(ValueError, "forbids oracle/truth"):
        validate_frozen_snapshots(frame, claim_class="road-observation")


def test_known_phase_field_terms_are_not_selectable() -> None:
    frame = manufactured_snapshots(seed=3, noise_fraction=0.0)
    fixed_name = sorted(FIXED_PHYSICS_NAMES)[0]
    with np.testing.assert_raises_regex(ValueError, "Known phase-field"):
        build_candidate_library(frame, [fixed_name])


def test_stability_selection_recovers_declared_support_and_is_deterministic() -> None:
    frame = manufactured_snapshots(seed=11, noise_fraction=0.01)
    validate_frozen_snapshots(frame, claim_class="tooling-only")
    system_a = assemble_weak_system(frame, n_windows=192, seed=11)
    system_b = assemble_weak_system(frame, n_windows=192, seed=11)
    assert np.array_equal(system_a.A, system_b.A)
    assert np.array_equal(system_a.b, system_b.b)
    result_a = stability_validated_select(system_a, n_trials=48, seed=11)
    result_b = stability_validated_select(system_b, n_trials=48, seed=11)
    assert result_a.stable_support == result_b.stable_support
    assert set(result_a.stable_support) == set(TRUE_BETA)
    assert result_a.metrics["mean_holdout_improvement_vs_null"] >= 0.05
    assert result_a.trial_coefficients["holdout_groups"].str.len().gt(0).all()


def test_generic_snapshot_runner_writes_auditable_nonroad_package(tmp_path: Path) -> None:
    frame = manufactured_snapshots(seed=13, noise_fraction=0.01)
    input_csv = tmp_path / "frozen.csv"
    output_dir = tmp_path / "package"
    frame.to_csv(input_csv, index=False)
    metrics = run_from_snapshot(
        input_csv,
        output_dir,
        claim_class="tooling-only",
        seed=13,
        n_trials=16,
        n_windows=64,
    )
    assert set(metrics["stable_support"]) == set(TRUE_BETA)
    assert metrics["road_mechanism_claim_allowed"] is False
    assert {
        "decision.md",
        "manifest.json",
        "metrics.json",
        "support_summary.csv",
        "trial_coefficients.csv",
        "weak_system.csv",
    }.issubset({path.name for path in output_dir.iterdir()})
