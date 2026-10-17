from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from freeze_select.structured_adapter import AdapterConfig  # noqa: E402
from freeze_select.synthetic_forecast import (  # noqa: E402
    ForecastConfig,
    bootstrap_adapter_ensemble,
    generate_dynamic_truth,
    sample_sparse_observations,
)
from freeze_select.uncertainty_selector import _uncertainty_weights  # noqa: E402


def test_adapter_ensemble_is_unique_and_cutoff_safe() -> None:
    config = ForecastConfig(
        nx=12,
        ny=6,
        n_times=13,
        n_sections=8,
        cutoff_index=7,
        observation_rate=0.35,
        noise_sigma=0.01,
    )
    truth = generate_dynamic_truth(config)
    observations = sample_sparse_observations(truth, config)
    members, _, hashes = bootstrap_adapter_ensemble(
        truth, observations, config, AdapterConfig(x_modes=4, y_modes=3), n_adapters=3
    )
    assert len(set(hashes)) == 3
    assert all(member["cycle"].max() <= config.cutoff_index for member in members)


def test_uncertainty_weights_never_delete_tip_rows() -> None:
    A = np.ones((3, 6, 2), dtype=float)
    b = np.vstack([np.arange(6), np.arange(6) + 0.2, np.arange(6) - 0.2])
    tip = np.array([False, True, False, True, False, True])
    weight, _ = _uncertainty_weights(A, b, np.zeros(2), tip)
    assert np.all(weight > 0.0)
    assert np.all(weight[tip] >= 0.50)
