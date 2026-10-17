import numpy as np
import pandas as pd

from SENS_tensile.freeze_select.multi_environment import (
    active_measure_normalize,
    balanced_stack,
    forcing_correlation,
    library_diagnostics,
    shared_support_select,
)
from SENS_tensile.freeze_select.synthetic_forecast import (
    ForecastConfig,
    generate_dynamic_truth,
)
from SENS_tensile.freeze_select.synthetic_multi_environment import loso_split
from SENS_tensile.freeze_select.weak_system import WeakSystem


def _manufactured_system(seed: int, beta: np.ndarray, rows: int = 180) -> WeakSystem:
    rng = np.random.default_rng(seed)
    A = rng.normal(size=(rows, beta.size))
    A[:, 3] = 0.65 * A[:, 0] + rng.normal(scale=0.75, size=rows)
    b = np.sum(A * beta[None, :], axis=1) + rng.normal(scale=0.015, size=rows)
    metadata = pd.DataFrame(
        {
            "window_id": [f"w{seed}_{index}" for index in range(rows)],
            "trajectory_id": f"environment_{seed}",
            "split_group": [f"environment_{seed}::tb{index % 4}" for index in range(rows)],
            "test_function_id": ["quartic"] * rows,
            "stratum": ["tip" if index % 4 == 0 else "background" for index in range(rows)],
        }
    )
    return WeakSystem(A=A, b=b, term_names=tuple(f"term_{i}" for i in range(beta.size)), metadata=metadata)


def test_balanced_excitation_is_low_correlation_before_damage_selection():
    config = ForecastConfig(
        nx=8,
        ny=6,
        n_times=17,
        n_sections=8,
        cutoff_index=10,
        excitation_design="balanced_2pow3",
    )
    truth = generate_dynamic_truth(config)
    assert forcing_correlation(truth) <= 0.35
    assert truth["trajectory_id"].nunique() == 8


def test_balanced_stack_equalizes_environment_row_mass():
    beta = np.array([0.6, 0.0, -0.35, 0.0, 0.25])
    systems = [_manufactured_system(1, beta, 120), _manufactured_system(2, beta, 240)]
    stacked = balanced_stack(systems)
    assert stacked.A.shape == (360, 5)
    assert set(stacked.metadata["environment_index"]) == {0, 1}
    diagnostics = library_diagnostics(systems)
    assert diagnostics.effective_rank == 5
    assert diagnostics.max_environment_leverage < 0.60


def test_shared_support_recovers_invariant_manufactured_terms():
    beta = np.array([0.6, 0.0, -0.35, 0.0, 0.25])
    train = [_manufactured_system(seed, beta) for seed in range(4)]
    validation = _manufactured_system(99, beta)
    result = shared_support_select(train, validation, n_trials=32, seed=17)
    assert set(result.support) == {"term_0", "term_2", "term_4"}
    assert result.metrics["validation_rmse"] < result.metrics["null_validation_rmse"]


def test_loso_split_keeps_test_and_internal_validation_out_of_selection():
    for holdout in range(8):
        train, validation, test = loso_split(holdout)
        assert len(train) == 6
        assert test == holdout
        assert validation not in train
        assert test not in train
        assert validation != test


def test_active_measure_normalization_preserves_rows_and_exact_coefficients():
    beta = np.array([0.6, 0.0, -0.35, 0.0, 0.25])
    system = _manufactured_system(123, beta, rows=220)
    system.metadata["active_measure"] = np.linspace(0.01, 0.50, system.A.shape[0])
    normalized = active_measure_normalize(system)
    assert normalized.A.shape == system.A.shape
    assert normalized.b.shape == system.b.shape
    raw_fit, *_ = np.linalg.lstsq(system.A, system.b, rcond=None)
    normalized_fit, *_ = np.linalg.lstsq(normalized.A, normalized.b, rcond=None)
    assert np.allclose(raw_fit, normalized_fit, atol=0.01)
    assert np.isfinite(normalized.A).all()
    assert np.isfinite(normalized.b).all()
