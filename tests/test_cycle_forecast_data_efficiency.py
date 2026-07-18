from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from fem_mechanism_operator import StateStatistics
from train_cycle_forecast_data_efficiency import admissible_targets, compute_prefix_statistics, input_dim, normalized_temporal_features


def test_admissible_targets_never_cross_cutoff():
    for train_end in (20, 40, 60, 67):
        for context in (1, 3, 5, 10):
            targets = admissible_targets(train_end, context)
            assert targets[0] == context + 1
            assert targets[-1] == train_end
            assert max(targets) <= train_end


def test_prefix_statistics_ignore_all_future_values():
    rng = np.random.default_rng(4)
    states = rng.normal(size=(89, 7, 4)).astype(np.float32)
    reference = compute_prefix_statistics(states, 20)
    states[20:] = 1.0e9
    changed = compute_prefix_statistics(states, 20)
    for name in ("state_mean", "state_std", "residual_mean", "residual_std"):
        assert torch.equal(getattr(reference, name), getattr(changed, name))


def test_temporal_features_use_declared_context_only():
    context = torch.arange(3 * 5 * 4, dtype=torch.float32).reshape(3, 5, 4)
    stats = StateStatistics(torch.zeros(1, 4), torch.ones(1, 4), torch.zeros(1, 4), torch.ones(1, 4))
    features = normalized_temporal_features(context, torch.zeros(5, 2), torch.zeros(5, 1), 12, stats)
    assert features.shape == (5, input_dim(3))
    # first 12 values are the oldest/current normalized levels for element 0
    assert torch.equal(features[0, :12], context[:, 0, :].reshape(-1))
    assert torch.equal(features[0, 12:20], (context[1:, 0, :] - context[:-1, 0, :]).reshape(-1))


def test_input_dimensions():
    assert input_dim(1) == 10
    assert input_dim(10) == 82
